import uuid

from queries import cql_queries


def get_existing_org_by_id_or_domain(id_name='', id_value=None, domain=None):
    return cql_queries.get_org_by_id_or_domain(id_name, id_value, domain)


def get_or_add_org(provider=None, domain=None, new_org=None):
    existing_org = get_existing_org_by_id_or_domain(domain=domain)
    if provider == 'MS':
        if existing_org:
            # A domain name may be 'verified' by another tenant if deleted by the current tenant
            # https://learn.microsoft.com/en-us/entra/identity/users/domains-manage#best-practices-for-domain-hygiene
            if existing_org['ms_id'] == new_org['id']:  # Always update org properties using MS data source
                cql_queries.set_org_properties_from_ms(existing_org['uuid'], new_org['id'], new_org['displayName'], new_org['verifiedDomains'])
            else:
                raise Exception("The domain {} was verified by an existing organisation, of which the Microsoft organization.id {} is different from the new one {}. Please contact us.".format(domain, existing_org['ms_id'], new_org['id']))
            return existing_org
        else:
            cql_queries.add_org_ms(new_org['id'], new_org['displayName'], new_org['verifiedDomains'])
            return get_existing_org_by_id_or_domain('ms_id', new_org['id'])
    elif provider == 'GH':
        if existing_org:  # Always update org properties using GitHub repo data source
            cql_queries.set_org_properties_from_github(existing_org['uuid'], new_org['gh_name'], new_org['gh_domains'])
            return existing_org
        elif new_org:
            org_uuid = str(uuid.uuid3(uuid.NAMESPACE_URL, domain))
            cql_queries.add_org_github(org_uuid, new_org['gh_name'], new_org['gh_domains'])
            return get_existing_org_by_id_or_domain(id_name='uuid', id_value=org_uuid)
        else:
            return None
