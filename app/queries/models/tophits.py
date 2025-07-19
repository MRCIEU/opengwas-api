from resources.globals import Globals

db = Globals.mysql

class Tophits(db.Model):
    # Table name could be:
    # tophits_5e-8_10000_0.001
    # tophits_1e-5_1000_0.8

    __abstract__ = True

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

_tophits_models_cache = {}

def get_tophits_model(table_name: str):
    if table_name in _tophits_models_cache:
        return _tophits_models_cache[table_name]
    model = type(f"Tophits_{table_name}", (Tophits,), {'__tablename__': table_name})
    _tophits_models_cache[table_name] = model
    return model
