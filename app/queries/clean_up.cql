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

