from queries.unique_node import UniqueNode


class Study(UniqueNode):

    def __init__(self, uid, pmid, year, filename, path, mr, trait, sample_size, unit, priority, author, note=None,
                 ncase=None, ncontrol=None, nsnp=None, sd=None, consortium=None, covariates=None,
                 beta_transformation=None):
        super().__init__(uid)

        self._pmid = pmid
        self._year = year
        self._filename = filename
        self._path = path
        self._mr = mr
        self._trait = trait
        self._sample_size = sample_size
        self._unit = unit
        self._priority = priority
        self._author = author
        self._note = note
        self._ncase = ncase
        self._ncontrol = ncontrol
        self._nsnp = nsnp
        self._sd = sd
        self._consortium = consortium
        self._covariates = covariates
        self._beta_transformation = beta_transformation

    # required fields

    @property
    def pmid(self):
        return self._pmid

    @pmid.setter
    def pmid(self, pmid):
        self._pmid = int(pmid)

    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, year):
        if int(year) < 1990 or int(year) > 2040:
            raise ValueError("The study year is incorrect, you provided: {}".format(year))
        self._year = int(year)

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename):
        self._filename = str(filename)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = str(path)

    @property
    def mr(self):
        return self._mr

    @mr.setter
    def mr(self, mr):
        if int(mr) < 0 or int(mr) > 1:
            raise ValueError("The mr field must be 0 or 1, you provided: {}".format(mr))
        self._mr = int(mr)

    @property
    def trait(self):
        return self._trait

    @trait.setter
    def trait(self, trait):
        self._trait = str(trait)

    @property
    def sample_size(self):
        return self._sample_size

    @sample_size.setter
    def sample_size(self, sample_size):
        self._sample_size = int(sample_size)

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, unit):
        self._unit = str(unit)

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, priority):
        self._priority = int(priority)

    @property
    def author(self):
        return self._author

    @author.setter
    def author(self, author):
        self._author = str(author)

    # optional fields

    @property
    def note(self):
        return self._note

    @note.setter
    def note(self, note):
        if note is not None:
            self._note = str(note)

    @property
    def ncase(self):
        return self._ncase

    @ncase.setter
    def ncase(self, ncase):
        if ncase is not None:
            self._ncase = int(ncase)

    @property
    def ncontrol(self):
        return self._ncontrol

    @ncontrol.setter
    def ncontrol(self, ncontrol):
        if ncontrol is not None:
            self._ncontrol = int(ncontrol)

    @property
    def nsnp(self):
        return self._nsnp

    @nsnp.setter
    def nsnp(self, nsnp):
        if nsnp is not None:
            self._nsnp = int(nsnp)

    @property
    def sd(self):
        return self._sd

    @sd.setter
    def sd(self, sd):
        if sd is not None:
            self._sd = float(sd)

    @property
    def consortium(self):
        return self._consortium

    @consortium.setter
    def consortium(self, consortium):
        if consortium is not None:
            self._consortium = str(consortium)

    @property
    def covariates(self):
        return self._covariates

    @covariates.setter
    def covariates(self, value):
        if value is not None:
            self._covariates = str(value)

    @property
    def beta_transformation(self):
        return self._beta_transformation

    @beta_transformation.setter
    def beta_transformation(self, value):
        if value is not None:
            self._beta_transformation = str(value)
