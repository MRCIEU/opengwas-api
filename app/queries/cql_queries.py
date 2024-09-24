import time
import uuid
from collections import defaultdict
from typing import List
from neo4j.debug import watch

from queries.user_node import User
from queries.gwas_info_node import GwasInfo
from queries.added_by_rel import AddedByRel
from queries.quality_control_rel import QualityControlRel
from queries.access_to_rel import AccessToRel
from queries.member_of_rel import MemberOfRel
from queries.member_of_org_rel import MemberOfOrgRel
from queries.group_node import Group
from queries.org_node import Org
from resources.globals import Globals
from resources.neo4j import Neo4j
from schemas.gwas_info_node_schema import GwasInfoNodeSchema

"""Return all available GWAS summary datasets"""


def get_batches():
    res = []
    for r in Neo4j.get_db().run("MATCH (n:Batches) return n"):
        res.append(r['n'].__dict__['_properties'])
    return res


def update_batches_stats():
    batches = defaultdict(int)
    tx = Neo4j.get_db()
    for gi in tx.run("MATCH (gi:GwasInfo) RETURN gi.id").data():
        batches['-'.join(gi['gi.id'].split('-', 2)[:2])] += 1
    for batch, size in batches.items():
        tx.run("MERGE (b:Batches {id: $id}) SET b.count = $count",
               id=batch,
               count=size
        )
    result = tx.run("MATCH (b:Batches) RETURN b")
    return [r['b'].__dict__['_properties'] for r in result]


def get_all_gwas_as_admin(return_subset_properties=[]):
    result = {}
    tx = Neo4j.get_db()
    if return_subset_properties:
        # https://neo4j.com/docs/python-manual/current/query-advanced/#_dynamic_values_in_property_keys_relationship_types_and_labels
        properties = ",".join(["." + p.replace("\\u0060", "`").replace("`", "``") for p in return_subset_properties])
        results = tx.run(
            f"MATCH (gi:GwasInfo) RETURN distinct(gi.id) as id, gi{{{properties}}};"
        )
        for r in results:
            result[r['id']] = GwasInfo(r['gi'])
    else:
        results = tx.run(
            "MATCH (gi:GwasInfo) RETURN distinct(gi) as gi;"
        )
        for r in results:
            result[r['gi']['id']] = GwasInfo(r['gi'])

    return result


def get_all_gwas_for_user(uid):
    group_names = get_groups_for_user(uid)
    res = {}
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo)-[:DID_QC {data_passed:True}]->(:User) WHERE g.name IN $group_names RETURN distinct(gi) as gi;",
        group_names=list(group_names)
    )
    for result in results:
        res[result['gi']['id']] = GwasInfo(result['gi'])

    return res


def get_all_gwas_ids_for_user(uid):
    recs = []
    group_names = get_groups_for_user(uid)

    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo)-[:DID_QC {data_passed:True}]->(:User) WHERE g.name IN $group_names RETURN distinct(gi.id) as id;",
        group_names=list(group_names)
    )

    for result in results:
        recs.append(result['id'])

    return recs


def get_gwas_for_user(uid, gwasid, datapass=True):
    group_names = get_groups_for_user(uid)
    schema = GwasInfoNodeSchema()

    tx = Neo4j.get_db()

    if datapass:
        results = tx.run(
            "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo {id:$gwasid})-[:DID_QC {data_passed:True}]->(:User) WHERE g.name IN $group_names RETURN distinct(gi);",
            group_names=list(group_names),
            gwasid=gwasid
        )
    else:
        results = tx.run(
            "MATCH (g:Group)-[:ACCESS_TO]->(gi:GwasInfo {id:$gwasid}) WHERE g.name IN $group_names RETURN distinct(gi);",
            group_names=list(group_names),
            gwasid=gwasid
        )

    result = results.single()
    if result is None:
        raise LookupError("GwasInfo ID $gwasid does not exist or you do not have the required access".format(gwasid=gwasid))

    return schema.load(GwasInfo(result['gi']))


def get_gwas_added_by_user(uid):
    res = {}
    tx = Neo4j.get_db()

    results = tx.run(
        "MATCH (gi:GwasInfo)-[r:ADDED_BY]->(u:User {uid:$uid}) WHERE gi.id=~'ieu-b-.*' RETURN distinct(gi) as gi, r LIMIT 100;",
        uid=uid
    )

    for result in results:
        res[result['gi']['id']] = {
            'gwasinfo': GwasInfo(result['gi']),
            'added_by': AddedByRel(result['r'])
        }

    return res


def get_added_by_state_of_all_draft_gwas():
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (gi:GwasInfo)-[r:ADDED_BY]->(u:User) WHERE r.state IS NOT NULL RETURN gi.id, PROPERTIES(r).state as state;"
    )

    return {r['gi.id']: r['state'] for r in results.data()}


def set_added_by_state_of_any_gwas(gwas_id, state=None):
    tx = Neo4j.get_db()

    # state will be removed when it is None
    result = tx.run(
        "MATCH (gi:GwasInfo {id: $gwas_id})-[r:ADDED_BY]->(u:User) SET r.state=$state RETURN gi, r, u;",
        gwas_id=gwas_id,
        state=state
    ).single()

    return result


def count_draft_gwas_of_user(uid):
    tx = Neo4j.get_db()

    # state will be removed when it is None
    result = tx.run(
        "MATCH (gi:GwasInfo)-[r:ADDED_BY]->(u:User {uid: $uid}) WHERE r.state IS NOT NULL RETURN count(gi) as `count`;",
        uid=uid
    ).single()

    return result.data()['count']


def add_new_gwas(user_email, gwas_info_dict, group_names=frozenset(['public']), gwas_id=None):
    if gwas_id is not None:
        try:
            GwasInfo.get_node(str(gwas_id))
            raise ValueError("Identifier has already been taken")
        except LookupError:
            # check node does not already exist
            gwas_info_dict['id'] = str(gwas_id)
    else:
        existing_gwas_ids = search_duplicate_gwas(gwas_info_dict['trait'], gwas_info_dict['author'], gwas_info_dict['year'])
        if len(existing_gwas_ids) > 0:
            raise Exception("It looks like we already have similar studies: " + ', '.join(existing_gwas_ids))
        # get new id
        gwas_info_dict['id'] = str(GwasInfo.get_next_numeric_id())

    # populate nodes
    gwas_info_node = GwasInfo(gwas_info_dict)
    added_by_rel = AddedByRel({'epoch': int(time.time()), 'state': 0})
    access_to_rel = AccessToRel()

    # persist or update
    gwas_info_node.create_node(gwas_info_dict['id'])
    added_by_rel.create_rel(gwas_info_node, User.get_node(user_email))

    # add grps
    for group_name in group_names:
        group_node = Group.get_node(group_name)
        access_to_rel.create_rel(group_node, gwas_info_node)

    return gwas_info_dict['id']


def search_duplicate_gwas(trait, author, year):
    tx = Neo4j.get_db()
    result = tx.run(
        "MATCH (gi:GwasInfo) WHERE (gi.trait=~$trait AND gi.author=~$author) OR (gi.trait=~$trait AND gi.year=~$year) RETURN gi;",
        trait='.*{}.*'.format(trait),
        author='.*{}.*'.format(author),
        year='.*{}.*'.format(year)
    )
    return [r['gi']['id'] for r in result.data()]


def edit_existing_gwas(gwas_id, gwas_info_dict):
    try:
        GwasInfo.get_node(str(gwas_id))
    except LookupError:
        raise ValueError("Identifier does not exist")

    gwas_info_dict['id'] = str(gwas_id)

    # populate nodes
    # gwas_info_dict['priority'] = 0
    gwas_info_node = GwasInfo(gwas_info_dict)
    gwas_info_node.edit_node(gwas_info_dict['id'])

    # update grps
    if gwas_info_dict['group_name'] is not None:
        delete_groups(gwas_id)
        group_node = Group.get_node(gwas_info_dict['group_name'])
        access_to_rel = AccessToRel()
        access_to_rel.create_rel(group_node, gwas_info_node)

    return gwas_info_dict['id']


def count_gwas_by_group():
    result = {}
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (gi:GwasInfo) RETURN gi.group_name as group, count(gi) as count;",
    )

    for r in results:
        result[r['group']] = r['count']

    return result


def create_or_update_user_and_membership(email, tier, source, names=[], org=None, user_org_info=None, group_names=frozenset(['public'])):
    email = email.strip().lower()
    uuid_str = str(uuid.uuid3(Globals.USER_UUID_NAMESPACE, email))
    if len(names) > 0:  # [first_name, last_name]
        u = User(uid=email, uuid=uuid_str, first_name=names[0], last_name=names[1], tier=tier, source=source)
    else:
        u = User(uid=email, uuid=uuid_str, tier=tier, source=source)
    u.create_node()

    user = get_user_by_email(email)
    if not user:
        raise Exception("Failed to create or update user information.")

    if tier == 'ORG':
        existing_org, membership = get_org_and_membership_from_user(email)
        if not existing_org or existing_org['uuid'] != org['uuid']:
            o = Org.get_node(org['uuid'])
            if user_org_info:
                MemberOfOrgRel({'job_title': user_org_info['jobTitle'], 'department': user_org_info['department']}).create_rel(u, o)
            else:
                MemberOfOrgRel().create_rel(u, o)
    else:
        delete_membership_of_user(email)

    for group_name in group_names:
        g = Group.get_node(group_name)
        MemberOfRel().create_rel(u, g)

    return user.data()['u']


def add_group_to_user(email, group_name):
    member_of_rel = MemberOfRel()
    u = User.get_node(email)
    g = Group.get_node(group_name)
    member_of_rel.create_rel(u, g)


def delete_gwas(gwas_id):
    GwasInfo.delete_node(gwas_id)


def delete_groups(gwasid):
    tx = Neo4j.get_db()
    tx.run(
        "MATCH (gi:GwasInfo {id:$gwasid})-[rel]-(g:Group) "
        "DELETE rel;",
        gwasid=gwasid
    )


""" Returns list of group identifiers for a given user email (will accept None) """


def get_groups_for_user(uid):
    if uid is None:
        return {'public'}

    names = set()
    names.add('public')

    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (:User {uid:'" + uid + "'})-[:MEMBER_OF]->(g:Group) RETURN g.name as name;",
        uid=str(uid)
    )
    for result in results:
        names.add(result['name'])

    return names


""" Get GwasInfo from list of studies given user permission"""


def get_permitted_studies(uid, gwas_info_ids: list):
    assert isinstance(gwas_info_ids, list)
    gwas_info_ids_str = []
    for i in gwas_info_ids:
        gwas_info_ids_str.append(str(i))
    schema = GwasInfoNodeSchema()
    group_names = get_groups_for_user(uid)
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (g:Group)-[:ACCESS_TO]->(s:GwasInfo)-[:DID_QC {data_passed:True}]->(:User) WHERE g.name IN $group_names AND s.id IN $sid RETURN distinct(s) as s;",
        group_names=list(group_names), sid=gwas_info_ids_str
    )
    res = {}
    for result in results:
        res[result['s']['id']] = schema.load(result['s'])
    return res


def add_quality_control(user_email, gwas_info_id, data_passed, comment=None):
    u = User.get_node(user_email)
    g = GwasInfo.get_node(gwas_info_id)
    r = QualityControlRel(epoch=time.time(), data_passed=data_passed, comment=comment)

    # create QC rel
    r.create_rel(g, u)


def delete_quality_control(gwas_info_id):
    tx = Neo4j.get_db()
    tx.run(
        "MATCH (gi:GwasInfo {id:$gwas_id})-[r:DID_QC]->(:User) DELETE r;",
        gwas_id=str(gwas_info_id)
    )


def check_user_is_admin(uid):
    try:
        u = User.get_node(uid)
    except LookupError:
        raise PermissionError("The token must resolve to a valid user")
    if 'admin' not in u:
        raise PermissionError("You must be an admin to complete this function")
    if u['admin'] is not True:
        raise PermissionError("You must be an admin to complete this function")


def check_user_is_developer(uid):
    try:
        u = get_groups_for_user(uid)
    except LookupError:
        raise PermissionError("The token must resolve to a valid user")
    if 'developer' not in u:
        raise PermissionError("You must be a developer to complete this function")


def check_gwasinfo_is_added_by_user(gwas_id, uid):
    tx = Neo4j.get_db()
    result = tx.run(
        "MATCH (gi:GwasInfo {id: $gwas_id})-[r:ADDED_BY]->(u:User {uid: $uid}) RETURN PROPERTIES(r) as r;",
        gwas_id=gwas_id,
        uid=uid
    ).data()

    if len(result) == 0:
        raise PermissionError("Dataset does not exist or you are not the person who added it")

    return result[0]['r']['state']


def get_todo_quality_control():
    res = {}
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (gi:GwasInfo)-[r:ADDED_BY]->(u:User) WHERE r.state IS NOT NULL RETURN gi, PROPERTIES(r) as r, u;"
    )
    for result in results:
        gi = GwasInfo(result['gi'])
        u = User(result['u'])
        res[gi['id']] = {
            'gwasinfo': gi,
            'added_by': result['r'],
            'user': {k: u[k] for k in ['uid', 'first_name', 'last_name']}
        }

    return res


def get_user_by_email(email):
    tx = Neo4j.get_db()
    result = tx.run(
        "MATCH (u:User {uid: $email}) RETURN u;",
        email=str(email)
    ).single()
    return result


def get_user_by_uuid(uuid):
    tx = Neo4j.get_db()
    result = tx.run(
        "MATCH (u:User {uuid: $uuid}) RETURN u;",
        uuid=str(uuid)
    ).single()
    return result


def get_user_by_emails(emails: List[str]):
    tx = Neo4j.get_db()
    results = tx.run(
        "MATCH (u:User) OPTIONAL MATCH (u)-[r:MEMBER_OF_ORG]->(o:Org) WHERE u.uid IN $emails RETURN u, PROPERTIES(r) as r, o;",
        emails=emails
    )
    return {result['u']['uid']: {
        'user': result['u'],
        'org_membership': result['r'],
        'org': result['o']
    } for result in results.data()}


def count_users(jwt_timestamp):
    result = {
        'by_source': {},
        'by_tier': {},
        'has_valid_token': 0
    }
    tx = Neo4j.get_db()

    results = tx.run(
        "MATCH (u:User) RETURN u.source as source, count(u) as count;"
    )
    for r in results:
        result['by_source'][r['source']] = r['count']
    result['by_source']['NONE'] = result['by_source'][None]
    del result['by_source'][None]

    results = tx.run(
        "MATCH (u:User) RETURN u.tier as tier, count(u) as count;"
    )
    for r in results:
        result['by_tier'][r['tier']] = r['count']
    result['by_tier']['NONE'] = result['by_tier'][None]
    del result['by_tier'][None]

    result['has_valid_token'] = tx.run(
        "MATCH (u:User) WHERE u.jwt_timestamp >= $timestamp RETURN count(u) as count;",
        timestamp=jwt_timestamp
    ).single()['count']

    return result


def count_orgs():
    return Neo4j.get_db().run(
        "MATCH (o:Org) RETURN count(o) as count;"
    ).single()['count']


def set_user_jwt_timestamp(email, timestamp):
    User().set_jwt_timestamp(email, timestamp)


def set_user_names(email, first_name, last_name):
    User().set_names(email, first_name, last_name)


def add_org_ms(ms_id, ms_name, ms_domains):
    o = Org(uuid=ms_id)
    o.create_node()
    set_org_properties_from_ms(ms_id, ms_id, ms_name, ms_domains)


def set_org_properties_from_ms(uuid, ms_id, ms_name, ms_domains):
    Org().set_properties_from_ms(uuid, ms_id, ms_name, ms_domains)


def add_org_github(uuid, gh_name, gh_domains):
    o = Org(uuid=uuid)
    o.create_node()
    set_org_properties_from_github(uuid, gh_name, gh_domains)


def set_org_properties_from_github(uuid, gh_name, gh_domains):
    Org().set_properties_from_github(uuid, gh_name, gh_domains)


def get_org_by_id_or_domain(id_name=None, id_value=None, domain=None):
    tx = Neo4j.get_db()
    result = []

    if id_name:
        result = tx.run(
            "MATCH (o:Org {" + id_name + ": $id_value}) RETURN o;",
            id_value=id_value
        ).data()
    elif domain:
        result = tx.run(
            "MATCH (o:Org) WHERE any(d in o.ms_domains WHERE d=$domain) OR any(d in o.gh_domains WHERE d=$domain) RETURN o;",
            domain=domain
        ).data()

    return result[0]['o'] if result else []


def get_org_and_membership_from_user(uid):
    tx = Neo4j.get_db()
    result = tx.run(
        "MATCH (u:User {uid: $uid})-[r:MEMBER_OF_ORG]->(o:Org) RETURN PROPERTIES(r) as r, o;",
        uid=uid
    ).single()

    if not result:
        return None, None

    result = result.data()

    return result['o'], result['r']


def delete_membership_of_user(uid):
    tx = Neo4j.get_db()
    tx.run(
        "MATCH (u:User {uid: $uid})-[r:MEMBER_OF_ORG]->(:Org) DELETE r;",
        uid=uid
    )
