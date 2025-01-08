from resources.globals import Globals

db = Globals.mysql

class DBSNP(db.Model):
    __tablename__ = 'dbsnp'

    id = db.Column(db.BigInteger, primary_key=True)
    chr_id = db.Column(db.SmallInteger, nullable=False)
    pos = db.Column(db.Integer, nullable=False)
    rsid = db.Column(db.BigInteger, nullable=False)
