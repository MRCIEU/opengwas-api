from resources._neo4j import get_db
from queries.trait_description_node import TraitDescriptionNode


# TODO parameter validation
class StudyNode:

    def __init__(self, study_id, pmid, year, trait, trait_description, category, population,
                 access=None, author=None,
                 consortium=None, filename=None,
                 mr=None,
                 ncase=None, ncontrol=None, note=None, nsnp=None, path=None, priority=None,
                 sample_size=None, sd=None, sex=None, status=None, unit=None):

        self.study_id = int(study_id)
        self.pmid = int(pmid)
        self.year = int(year)
        self.trait = str(trait)
        self.trait_description = str(trait_description).lower()
        self.category = str(category).lower()

        self.access = access
        self.author = author
        self.consortium = consortium
        self.filename = filename
        self.mr = mr
        self.ncase = ncase
        self.ncontrol = ncontrol
        self.note = note
        self.nsnp = nsnp
        self.path = path
        self.population = population
        self.priority = priority
        self.sample_size = sample_size
        self.sd = sd
        self.sex = sex
        self.status = status
        self.unit = unit

        # check year is somewhat valid
        if self.year < 1950 or self.year > 2050:
            raise ValueError("The study year was invalid {}".format(year))

        # check description is valid
        trait_description_node = TraitDescriptionNode(self.trait_description)
        if len(trait_description_node.get()) == 0:
            raise ValueError("Invalid trait description provided: {}".format(trait_description))

        if self.category != 'disease' and self.category != 'non-disease':
            raise ValueError("Category must be: disease or non-disease. You provided: {}".format(category))

    def create(self):
        tx = get_db()
        tx.run("MERGE (n:Study {study_id:{study_id}}) "
               "SET n.access={access} "
               "SET n.author={author} "
               "SET n.category={category} "
               "SET n.consortium={consortium} "
               "SET n.filename={filename} "
               "SET n.mr={mr} "
               "SET n.ncase={ncase} "
               "SET n.ncontrol={ncontrol} "
               "SET n.note={note} "
               "SET n.nsnp={nsnp} "
               "SET n.path={path} "
               "SET n.pmid={pmid} "
               "SET n.population={population} "
               "SET n.priority={priority} "
               "SET n.sample_size={sample_size} "
               "SET n.sd={sd} "
               "SET n.sex={sex} "
               "SET n.status={status} "
               "SET n.subcategory={subcategory} "
               "SET n.trait={trait} "
               "SET n.unit={unit} "
               "SET n.year={year} ",
               {
                   "study_id": self.study_id,
                   "access": self.access,
                   "author": self.author,
                   "category": self.category,
                   "consortium": self.consortium,
                   "filename": self.filename,
                   "mr": self.mr,
                   "ncase": self.ncase,
                   "ncontrol": self.ncontrol,
                   "note": self.note,
                   "nsnp": self.nsnp,
                   "path": self.path,
                   "pmid": self.pmid,
                   "population": self.population,
                   "priority": self.priority,
                   "sample_size": self.sample_size,
                   "sd": self.sd,
                   "sex": self.sex,
                   "status": self.status,
                   "subcategory": self.subcategory,
                   "trait": self.trait,
                   "unit": self.unit,
                   "year": self.year
               })

    def get(self):
        tx = get_db()
        results = tx.run(
            "MATCH (n:Study {study_id:{study_id}}) "
            "RETURN n as study;", {
                "study_id": self.study_id
            }
        )
        result = results.single()
        return self.__deserialize(result['study'])

    @staticmethod
    def __deserialize(node):
        n = StudyNode(node['study_id'])
        for key in node['study_id']:
            setattr(n, key, node['study_id'][key])
        return n
