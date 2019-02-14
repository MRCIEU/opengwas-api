//indexes
CREATE CONSTRAINT ON (n:GwasInfo) ASSERT n.id IS UNIQUE;
CREATE CONSTRAINT ON (n:Group) ASSERT n.gid IS UNIQUE;
CREATE CONSTRAINT ON (n:User) ASSERT n.uid IS UNIQUE;

//study nodes
using periodic commit 1000 LOAD CSV from 'file:///study_e.tsv' as row FIELDTERMINATOR '\t' WITH row, coalesce(row[6],"NA") as note_data, coalesce(row[9],"NA") as sub_data merge (s:Study{id:row[0], pmid:row[1], year:row[2], filename:row[3], path:row[4], mr:row[5], note:note_data, trait:row[7], category:row[8], subcategory:sub_data, population:row[10], sex:row[11],   ncase:row[12], ncontrol:row[13], sample_size:row[14], nsnp:row[15], unit:row[16], sd:row[17], priority:row[18], author:row[19], consortium:row[20], access:row[21]}) return s;

//test study
using periodic commit 1000 LOAD CSV from 'file:///study_test.tsv' as row FIELDTERMINATOR '\t' WITH row, coalesce(row[6],"NA") as note_data, coalesce(row[9],"NA") as sub_data merge (s:Study{id:row[0], pmid:row[1], year:row[2], filename:row[3], path:row[4], mr:row[5], note:note_data, trait:row[7], category:row[8], subcategory:sub_data, population:row[10], sex:row[11], ncase:row[12], ncontrol:row[13], sample_size:row[14], nsnp:row[15], unit:row[16], sd:row[17], priority:row[18], author:row[19], consortium:row[20], access:row[21]}) return s;

//add a status property to study nodes
match (s:Study) set s.status = 'Available'

//group nodes
using periodic commit 10000 LOAD CSV from 'file:///groups.tsv' as row FIELDTERMINATOR '\t' merge (g:Group{gid:toInteger(row[0]),name:row[1]}) return g;

//user nodes
using periodic commit 10000 LOAD CSV from 'file:///memberships.tsv' as row FIELDTERMINATOR '\t' merge (u:User{uid:row[0]}) return u;

//user to group
using periodic commit 10000 LOAD CSV from 'file:///memberships.tsv' as row FIELDTERMINATOR '\t' match (u:User{uid:row[0]}) match (g:Group{gid:toInteger(row[1])}) merge (u)-[:MEMBER_OF]->(g) return u,g;

//group to study
using periodic commit 10000 LOAD CSV from 'file:///permissions_e.tsv' as row FIELDTERMINATOR '\t' match (g:Group{gid:toInteger(row[0])}) match (s:Study{id:row[1]}) merge (g)-[:ACCESS_TO]->(s) return g,s;


// set property types
MATCH (n:Study)
SET n.id = toString(n.id)
SET n.pmid = toInt(n.pmid)
SET n.year = toInt(n.year)
SET n.filename = toString(n.filename)
SET n.path = toString(n.path)
SET n.mr = toInt(n.mr)
SET n.note = toString(n.note)
SET n.trait = toString(n.trait)
SET n.trait_description = toString(n.trait_description)
SET n.category = toString(n.category)
SET n.subcategory = toString(n.subcategory)
SET n.population = toString(n.population)
SET n.sex = toString(n.sex)
SET n.ncase = toInt(n.ncase)
SET n.ncontrol = toInt(n.ncontrol)
SET n.sample_size = toInt(n.sample_size)
SET n.nsnp = toInt(n.nsnp)
SET n.unit = toString(n.unit)
SET n.sd = toFloat(n.sd)
SET n.priority = toInt(n.priority)
SET n.author = toString(n.author)
SET n.consortium = toString(n.consortium)
SET n.access = toString(n.access)
SET n.study_design = toString(n.study_design)
SET n.covariates = toString(n.covariates)
SET n.beta_transformation = toString(n.beta_transformation)
SET n.imputation_panel = toString(n.imputation_panel)
SET n.build = toString(n.build);

MATCH (n:User)
SET n.uid = toString(n.uid);

MATCH (n:Group)
SET n.gid = toInt(n.gid)
SET n.name = toString(n.name);

// clean study year prop
MATCH (n:Study) WHERE n.year = 0 REMOVE n.year;
MATCH (n:Study) WHERE n.access = "public" SET n.access = "Public";
MATCH (n:Study) WHERE n.note = "NULL" REMOVE n.note;
MATCH (n:Study) WHERE n.sex = "NULL" REMOVE n.sex;
MATCH (n:Study) WHERE n.sex = "sex" REMOVE n.sex;
MATCH (n:Study) WHERE n.sex = "Males and females" SET n.sex = "Males and Females";
MATCH (n:Study) WHERE n.subcategory = "NULL" REMOVE n.subcategory;
MATCH (n:Study) WHERE n.subcategory = "Test" REMOVE n.subcategory;

// rename study to gwasinfo
MATCH (n:Study) SET n:GwasInfo REMOVE n:Study;

//delete duplicate field
MATCH (n:GwasInfo) REMOVE n.access;

// add retrospective quality control
MATCH (u:User {uid:"ml18692@bristol.ac.uk"})
MATCH (g:GwasInfo) WHERE NOT (g)-[:DID_QC]->(:User)
CREATE (g)-[:DID_QC {epoch:1549379289.720649, comment:"historic", data_passed:True}]->(u)

// add me to all studies for testing
CREATE (n:Group {gid:999, name:"Test"})

MATCH (gi:GwasInfo)
MATCH (gr:Group {gid:999})
CREATE (gi)<-[:ACCESS_TO]-(gr)

MATCH (n:User {uid:"ml18692@bristol.ac.uk"})
MATCH (gr:Group {gid:999})
CREATE (n)-[:MEMBER_OF]->(gr)

//set all users to non-admin
MATCH (u:User) SET u.admin = False

//set admins TODO
MATCH (u:User {uid:"baird.denis@gmail.com"}) SET u.admin = True
MATCH (u:User {uid:"g.hemani@bristol.ac.uk"}) SET u.admin = True
MATCH (u:User {uid:"matt.lyon@bristol.ac.uk"}) SET u.admin = True