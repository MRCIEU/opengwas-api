from resources.globals import Globals

db = Globals.mysql

class Proxies(db.Model):
    # Table name could be:
    # proxies_afr
    # proxies_amr
    # proxies_eas
    # proxies_eur
    # proxies_sas

    __abstract__ = True

    id = db.Column(db.BigInteger, primary_key=True)
    rsid_a = db.Column(db.BigInteger, nullable=False)
    rsid_b = db.Column(db.BigInteger, nullable=False)
    maf_a = db.Column(db.Float, nullable=False)
    maf_b = db.Column(db.Float, nullable=False)
    r2 = db.Column(db.Float, nullable=False)
    distance = db.Column(db.BigInteger, nullable=False)
    allele_a1 = db.Column(db.String(1), nullable=False)
    allele_a2 = db.Column(db.String(1), nullable=False)
    allele_b1 = db.Column(db.String(1), nullable=False)
    allele_b2 = db.Column(db.String(1), nullable=False)
    palindromic = db.Column(db.SmallInteger, nullable=False)

_proxies_models_cache = {}

def get_proxies_model(table_name: str):
    if table_name in _proxies_models_cache:
        return _proxies_models_cache[table_name]
    model = type(f"Proxies_{table_name}", (Proxies,), {'__tablename__': table_name})
    _proxies_models_cache[table_name] = model
    return model
