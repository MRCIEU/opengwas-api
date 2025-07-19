from resources.globals import Globals

db = Globals.mysql

class PheWAS(db.Model):
    __tablename__ = 'phewas'

    id = db.Column(db.BigInteger, primary_key=True)
    gwas_id_n = db.Column(db.Integer)
    snp_id = db.Column(db.String(255))
    chr_id = db.Column(db.SmallInteger, nullable=False)
    pos = db.Column(db.Integer, nullable=False)
    ea = db.Column(db.String(255))
    nea = db.Column(db.String(255))
    eaf = db.Column(db.Float)
    beta = db.Column(db.Float)
    se = db.Column(db.Float)
    lp = db.Column(db.Float)
    ss = db.Column(db.String(255))
