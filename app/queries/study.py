from resources._neo4j import get_db


# TODO parameter validation
class Study:

    def __init__(self, sid, pmid, year, trait, trait_description, category,
                 access=None, author=None,
                 consortium=None, filename=None,
                 mr=None,
                 ncase=None, ncontrol=None, note=None, nsnp=None, path=None, population=None, priority=None,
                 sample_size=None, sd=None, sex=None, status=None, subcategory=None, unit=None):

        self.sid = int(sid)
        self.pmid = int(pmid)
        self.year = int(year)
        self.trait = str(trait)
        self.trait_description = str(trait_description).lower()
        self.category = category  # TODO check

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
        self.subcategory = subcategory
        self.unit = unit

        if self.year < 1950 or self.year > 2050:
            raise ValueError("The study year was invalid {}".format(year))

        if self.trait_description != 'continuous' and \
                self.trait_description != 'binary' and \
                self.trait_description != 'ordinal':
            raise ValueError(
                "Description must be: continuous, binary or ordinal. You provided: {}".format(trait_description))

    def create(self):
        tx = get_db()
        tx.run("MERGE (n:Study {sid:{sid}}) "
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
                   "sid": self.sid,
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
            "MATCH (n:Study {sid:{sid}}) "
            "RETURN n as study;", {
                "sid": self.sid
            }
        )
        result = results.single()
        return self.__deserialize(result['study'])

    @staticmethod
    def __deserialize(node):
        n = Study(node['sid'])
        for key in node['sid']:
            setattr(n, key, node['sid'][key])
        return n
