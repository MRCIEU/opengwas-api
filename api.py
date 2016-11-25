import os
import json
import urllib
import PySQLPool
import subprocess
import re
import tempfile
import uuid
import csv
import string
from optparse import *
from flask import *
from werkzeug import secure_filename
import logging


"""

Constants

"""

OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='
USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='
UPLOAD_FOLDER = '/tmp/'
ALLOWED_EXTENSIONS = set(['txt'])
MAX_FILE_SIZE = 16 * 1024 * 1024

LOG_FILE = "../logs/mrbaseapi.log"
CENTRAL_DB = "../conf_files/central.json"
UCSC_DB = "../conf_files/ucsc.json"
ORIGINAL_DB = "../conf_files/original.json"

"""

Setup logging

"""


if not os.path.exists(LOG_FILE):
    open('file', 'w').close() 

logging.basicConfig(filename=LOG_FILE,level=logging.DEBUG)



"""

Initialise app

"""


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
#app.debug = True


"""

CONNECT TO DATABASES

Two MR-Base databases - original server much be connected through tunnel
                      - central server goes through SSL

UCSC - This may not be required anymore

----

The following code tests the MR-Base database connection

dbConnection = PySQLPool.getNewConnection(**mrbase_config)
SQL   = "describe study;"
query = PySQLPool.getNewQuery(dbConnection)
query.Query(SQL)
json.dumps(query.record)


"""


with open(CENTRAL_DB) as f:
    mrbase_config = json.load(f)

# with open(ORIGINAL_DB) as f:
    # mrbase_config = json.load(f)

with open(UCSC_DB) as f:
    ucsc_config = json.load(f)


dbConnection = PySQLPool.getNewConnection(**mrbase_config)
ucscConnection = PySQLPool.getNewConnection(**ucsc_config)


"""

General functions

"""


def check_filename(strg, search=re.compile(r'[^a-z0-9.]').search):
    return not bool(search(strg))

def clean_snp_string(snpstring):
    # Function to clean snp string of bad characters
    snpstring = snpstring.encode("ascii")
    transtable = string.maketrans('','')
    rsidallowed = "rs,0123456789" # Remove all characters except these (including white space)
    cleansnp = transtable.translate(transtable,rsidallowed)
    return snpstring.translate(transtable,cleansnp)

def clean_outcome_string(outcomestring):
    # Function to clean outcome string of bad characters
    outcomestring = outcomestring.encode("ascii")
    transtable = string.maketrans('','')
    rsidallowed = ",0123456789" # Allow numeric IDs and commas only
    cleansnp = transtable.translate(transtable,rsidallowed)
    return outcomestring.translate(transtable,cleansnp)

def joinarg(field):
    field_text = ""
    if field == "outcomes":
        field_text = clean_outcome_string(request.args.get(field))
    elif field == "snps":
        field_text = clean_snp_string(request.args.get(field))
    #else: field_text = request.args.get(field) # Unsafe
    return ",".join([ "'" + x + "'" for x in field_text.split(",") ])

def joinarray(array):
    return ",".join([ "'" + str(x) + "'" for x in array])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


"""

Authentication functions

"""


def get_user_email(token):
    url = OAUTH2_URL + token
    response = urllib.urlopen(url)
    data = json.loads(response.read())
    if "email" in data:
        return data['email']
    else:
        return "NULL"

def check_access_token(token):
    url = OAUTH2_URL + token
    response = urllib.urlopen(url)
    data = json.loads(response.read())
    if "email" in data:
        if check_email(data['email']):
            return "internal"
        else:
            return "conditional"
    else:
        return "public"


def token_query(token):
    user_email = get_user_email(token)
    logging.info("getting credentials for "+user_email)
    query =  """(c.id IN (select d.id from study_copy d, memberships m, permissions p
                    WHERE m.uid = "{0}"
                    AND p.gid = m.gid
                    AND d.id = p.study_id
        		)
        	    OR c.id IN (select d.id from study_copy d, permissions p
                    WHERE p.gid = 1
                    AND d.id = p.study_id
        		))""".format(user_email)
    return query



"""

Query functions

"""


def query_summary_stats(token, snps, outcomes):
    access_query = token_query(token)
    query = PySQLPool.getNewQuery(dbConnection)
    SQL   = """SELECT a.effect_allele, a.other_allele, a.effect_allelel_freq, a.beta, a.se, a.p, a.n, b.name, c.*
            FROM assoc a, snp b, study_copy c
            WHERE a.snp=b.id AND a.study=c.id
            AND {0}
            AND a.study IN ({1})
            AND b.name IN ({2})
            ORDER BY a.study;""".format(access_query, outcomes, snps)
    logging.info("performing summary stats query")
    query.Query(SQL)
    logging.info("done summary stats query")
    return query.record


def get_snp_positions(snps):
    snps = ",".join([ "'" + x + "'" for x in snps ])
    ucscquery = PySQLPool.getNewQuery(ucscConnection)
    chr = ",".join([ "'chr" + str(x) + "'" for x in range(1,24)])
    SQL = "SELECT chrom, chromEnd, name " \
    "FROM snp144 " \
    "WHERE name in ({0}) " \
    "AND chrom in ({1});".format(snps, chr)
    ucscquery.Query(SQL)
    return ucscquery.record



def plink_clumping_rs(fn, upload_folder, ress, snp_col, pval_col, p1, p2, r2, kb):

    try:
        filename = upload_folder + fn + "_recode"
        tfile = open(filename, "w")
        tfile.write("SNP P\n")
        for i in xrange(len(ress)):
            tfile.write(str(ress[i].get(snp_col)) + " " + str(ress[i].get(pval_col)) + "\n")

        tfile.close()
        command =   "../ld_files/plink1.90 " \
                    "--bfile ../ld_files/data_maf0.01_rs " \
                    " --clump {0} " \
                    " --clump-p1 {1} " \
                    " --clump-p2 {2} " \
                    " --clump-r2 {3} " \
                    " --clump-kb {4} " \
                    " --out {5}".format(filename, p1, p2, r2, kb, filename)

        logging.info(command)
        os.system(command)

        filename_c = filename + ".clumped"
        f = open(filename_c, "r")
        f.readline()
        words = f.read().split("\n")
        f.close()

        logging.info("matching clumps to original query")
        out = []
        for x in words:
            if x is not '':
                out.append([y for y in ress if y.get(snp_col) == x.split()[2]][0])
        logging.info("done match")
    finally:
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

    return out




def plink_clumping(fn, upload_folder, cp, ress, snp_col, pval_col, p1, p2, r2, kb):
    filename = upload_folder + fn + "_recode"
    try:
        tfile = open(filename, "w")
        tfile.write("SNP P\n")
        for i in xrange(len(ress)):
            y = [d.get('chrom') + ":" + str(d.get('chromEnd')) for d in cp if d.get('name') == ress[i].get(snp_col)]
            if len(y) != 0:
                y = y[0]
                ress[i]['chrpos'] = y
                tfile.write(y + " " + str(ress[i].get(pval_col)) + "\n")
        tfile.close()

        command =   "../ld_files/plink1.90 " \
                    "--bfile ../ld_files/data_maf0.01 " \
                    " --clump {0} " \
                    " --clump-p1 {1} " \
                    " --clump-p2 {2} " \
                    " --clump-r2 {3} " \
                    " --clump-kb {4} " \
                    " --out {5}".format(filename, p1, p2, r2, kb, filename)

        logging.info(command)
        os.system(command)

        filename_c = filename + ".clumped"
        f = open(filename_c, "r")
        f.readline()
        words = f.read().split("\n")
        f.close()

        out = []
        for x in words:
            if x is not '':
                out.append([y for y in ress if y.get('chrpos') == x.split()[2]][0])

    finally:
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

    return out



def get_proxies(snps, chr):
    proxy_dat = []
    for i in range(len(snps)):
        fn = LD_FILES + chr[i]
        snp = snps[i]
        dat = [{'targets':snp, 'proxies': snp, 'tallele1': '', 'tallele2': '', 'pallele1': '', 'pallele2': ''}]
        logging.info(snp)
        flag=0
        with open(fn, "r") as f:
            alllines = f.readlines()
            for l in alllines:
                l = l.split()
                if l[2] == snp:
                    flag=1
                    alleles=[x[0] for x in l[6].split("/")]
                    palleles=[x[-1] for x in l[6].split("/")]
                    dat.append({'targets':snp,
                        'proxies':l[5],
                        'allele1':alleles[0],
                        'allele2':alleles[1],
                        'pallele1':palleles[0],
                        'pallele2':palleles[1]}
                    )
                elif flag == 1:
                    break
        proxy_dat.append(dat)
    return proxy_dat


def get_proxies_mysql(snps, rsq, palindromes, maf_threshold):
    logging.info("obtaining LD proxies")
    pquery = PySQLPool.getNewQuery(dbConnection)
    if palindromes == "0":
        pal = 'AND palindromic = 0'
    else:
        pal = "AND ( ( pmaf < " + str(maf_threshold) + " AND palindromic = 1 ) OR palindromic = 0)"
    SQL = "SELECT * " \
    "FROM proxies " \
    "WHERE target in ({0}) " \
    "AND rsq >= {1} {2};".format(",".join([ "'" + x + "'" for x in snps ]), rsq, pal)
    logging.info("performing proxy query")
    pquery.Query(SQL)
    logging.info("done proxy query")
    res = pquery.record
    proxy_dat = []
    logging.info("matching proxy SNPs")
    for i in range(len(snps)):
        snp = snps[i]
        dat = [{'targets':snp, 'proxies': snp, 'tallele1': '', 'tallele2': '', 'pallele1': '', 'pallele2': '', 'pal': ''}]
        for l in res:
            if l.get('target') == snp:
                dat.append({
                    'targets':snp,
                    'proxies':l.get('proxy'),
                    'tallele1':l.get('tallele1'),
                    'tallele2':l.get('tallele2'),
                    'pallele1':l.get('pallele1'),
                    'pallele2':l.get('pallele2'),
                    'pal':l.get('palindromic')}
                )
        proxy_dat.append(dat)
    logging.info("done proxy matching")
    return proxy_dat


def extract_proxies_from_query(outcomes, snps, proxy_dat, proxy_query, maf_threshold, align_alleles):
    logging.info("entering extract_proxies_from_query")
    matched_proxies = []
    proxy_query_copy = [a.get('name') for a in proxy_query]
    for i in range(len(outcomes)):
        logging.info("matching proxies to query snps for " + str(i))
        for j in range(len(snps)):
            flag=0
            for k in range(len(proxy_dat[j])):
                if flag == 1:
                    break
                for l in range(len(proxy_query)):
                    if (proxy_query[l].get('name') == proxy_dat[j][k].get('proxies')) and (str(proxy_query[l].get('id')) == outcomes[i]):
                        y = dict(proxy_query[l])
                        y['target_snp'] = snps[j]
                        y['proxy_snp'] = proxy_query[l].get('name')
                        if(snps[j] == proxy_query[l].get('name')):
                            y['proxy'] = False
                            y['target_a1'] = None
                            y['target_a2'] = None
                            y['proxy_a1'] = None
                            y['proxy_a2'] = None
                            matched_proxies.append(y.copy())
                            flag = 1
                        else:
                            if align_alleles == "1":
                                al = proxy_alleles(proxy_query[l], proxy_dat[j][k], maf_threshold)
                                logging.info(al)
                                if al == "straight":
                                    y['proxy'] = True
                                    y['effect_allele'] = proxy_dat[j][k].get('tallele1')
                                    y['other_allele'] = proxy_dat[j][k].get('tallele2')
                                    y['target_a1'] = proxy_dat[j][k].get('tallele1')
                                    y['target_a2'] = proxy_dat[j][k].get('tallele2')
                                    y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
                                    y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
                                    y['name'] = snps[j]
                                    matched_proxies.append(y.copy())
                                    flag = 1
                                    # print "straight", i, j, k, l
                                    break
                                if al == "switch":
                                    y['proxy'] = True
                                    y['effect_allele'] = proxy_dat[j][k].get('tallele2')
                                    y['other_allele'] = proxy_dat[j][k].get('tallele1')
                                    y['target_a1'] = proxy_dat[j][k].get('tallele1')
                                    y['target_a2'] = proxy_dat[j][k].get('tallele2')
                                    y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
                                    y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
                                    y['name'] = snps[j]
                                    matched_proxies.append(y.copy())
                                    flag = 1
                                    # print "switch", i, j, k, l
                                    break
                                if al == "skip":
                                    logging.info("skip")
                            else:
                                y['proxy'] = True
                                y['target_a1'] = proxy_dat[j][k].get('tallele1')
                                y['target_a2'] = proxy_dat[j][k].get('tallele2')
                                y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
                                y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
                                y['name'] = snps[j]
                                matched_proxies.append(dict(y))
                                flag = 1
                                # print "unaligned", i, j, k, l
                                break
    return matched_proxies



def flip(x):
    if x == "A":
        return "T"
    if x == "T":
        return "A"
    if x == "G":
        return "C"
    if x == "C":
        return "G"


def allele_check(x):
    if x is None:
        return x
    x = x.upper()
    if x == "A":
        return x
    if x == "T":
        return x
    if x == "G":
        return x
    if x == "C":
        return x
    return None


def proxy_alleles(pq, pd, maf_threshold):
    mallele1 = allele_check(pq.get('effect_allele'))
    mallele2 = allele_check(pq.get('other_allele'))
    tallele1 = pd.get('tallele1')
    tallele2 = pd.get('tallele2')
    pallele1 = pd.get('pallele1')
    pallele2 = pd.get('pallele2')
    if mallele1 is None:
        return "no allele"
    pal = pd.get('pal')
    eaf = pq.get('effect_allelel_freq')
    if pal == "0":
        if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)):
            return "straight"
        if (mallele1 == pallele2 and mallele2 == pallele1) or (mallele1 == flip(pallele2) and mallele2 == flip(pallele1)):
            return "switch"
        if (mallele1 == pallele1 and mallele2 == None) or (mallele1 == flip(pallele1) and mallele2 == None):
            return "straight"
        if (mallele1 == pallele2 and mallele2 == None) or (mallele1 == flip(pallele2) and mallele2 == None):
            return "switch"
        return "skip"
    if pal == "1":
        if eaf == None:
            return "skip"
        if eaf < maf_threshold:
            if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == pallele1 and mallele2 == None):
                return "straight"
            if (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)) or (mallele1 == flip(pallele1) and mallele2 == None):
                return "switch"
        if eaf > 1 - maf_threshold:
            if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == pallele1 and mallele2 == None):
                return "switch"
            if (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)) or (mallele1 == flip(pallele1) and mallele2 == None):
                return "straight"
        return "skip"



"""

Methods

"""

@app.route("/")
def hello():
    logging.info("INCOMING")
    return "Welcome to the MR-Base API. This was automatically deployed."


@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('upload'))
    return """
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    <p>%s</p>
    """ % "<br>".join(os.listdir(app.config['UPLOAD_FOLDER'],))


@app.route("/check_token", methods=[ 'GET' ])
def check_token():
    a = request.args.get('access_token')
    logging.info(a)
    if not request.args.get('access_token'):
        return json.dumps(-1)
    if request.args.get('access_token'):
        return json.dumps(check_access_token(request.args.get('access_token')))
    else:
        return json.dumps(-1)


@app.route("/get_studies", methods=[ 'GET' ])
def get_studies():
    logging.info("\n\n\nRequesting study table")
    access_query = token_query(request.args.get('access_token'))
    query = PySQLPool.getNewQuery(dbConnection)
    SQL   = "SELECT * FROM study_copy c WHERE c.id NOT IN (1000000) AND" + access_query + ";"
    query.Query(SQL)
    return json.dumps(query.record, ensure_ascii=False)


@app.route("/get_effects", methods=[ 'GET' ])
def get_effects():
    if not request.args.get('outcomes') or not request.args.get('snps'):
        return json.dumps([])

    outcomes = joinarg('outcomes')
    snps     = joinarg('snps')
    return json.dumps(query_summary_stats(request.args.get('access_token'), snps, outcomes))


@app.route("/get_status", methods=[ 'GET' ])
def get_status():
    SQL   = "SELECT COUNT(*) FROM study_copy;"
    query = PySQLPool.getNewQuery(dbConnection)
    query.Query(SQL)
    return json.dumps(query.record)




@app.route("/extract_instruments", methods=[ 'GET' ])
def extract_instruments():
    if not request.args.get('outcomes'):
        return json.dumps([])

    if not request.args.get('pval'):
        pval = 5e-8
    else:
        pval = float(request.args.get('pval'))
    if not request.args.get('clump'):
        logging.info("no clump argument")
        clump = "yes"
    elif request.args.get('clump') == "no" or request.args.get('clump') == "No":
        clump = request.args.get('clump')
    else: clump = "yes"
    if not request.args.get('p1'):
        p1 = pval
    else:
        p1 = float(request.args.get('p1'))
    if not request.args.get('p2'):
        p2 = pval
    else:
        p2 = float(request.args.get('p2'))
    if not request.args.get('r2'):
        r2 = 0.1
    else:
        r2 = float(request.args.get('r2'))
    if not request.args.get('kb'):
        kb = 5000
    else:
        kb = int(request.args.get('kb'))

    if p1 > p2:
        p2 = p1

    outcomes = joinarg('outcomes')

    logging.info("\n\n\nobtaining instruments for "+outcomes)
    logging.info("clumping = "+clump)

    access_query = token_query(request.args.get('access_token'))
    query = PySQLPool.getNewQuery(dbConnection)

    SQL = "SELECT a.effect_allele, a.other_allele, a.effect_allelel_freq, a.beta, a.se, a.p, a.n, b.name, c.* " \
        "FROM assoc a, snp b, study_copy c " \
        "WHERE a.snp=b.id AND a.study=c.id " \
        "AND a.study IN ({0}) " \
        "AND a.p <= {1} " \
        "AND {2}" \
        "ORDER BY a.study;".format(outcomes, pval, access_query)
    logging.info("querying database...")
    query.Query(SQL)
    res = query.record
    logging.info("done. found "+str(len(res))+" hits")

    if query.affectedRows == 0L:
        return json.dumps([])

    if clump =="yes" and query.affectedRows != 0L:
        found_outcomes = set([x.get('id') for x in res])
        all_out = []
        for outcome in found_outcomes:
            logging.info("clumping results for "+str(outcome))
            ress = [x for x in res if x.get('id') == outcome]
            snps = set([x.get('name') for x in res if x.get('id') == outcome])

            # print "getting position"
            # cp = get_snp_positions(snps)
            # print "got position"

            fn = str(uuid.uuid4())
            # out = plink_clumping(fn, UPLOAD_FOLDER, cp, ress, "name", "p", p1, p2, r2, kb)
            out = plink_clumping_rs(fn, UPLOAD_FOLDER, ress, "name", "p", p1, p2, r2, kb)
            all_out = all_out + out

        return json.dumps(all_out, ensure_ascii=False)

    return json.dumps(res, ensure_ascii=False)


@app.route("/get_effects_from_file", methods=[ 'GET' ])
def get_effects_from_file():
    logging.info("\n\n\nExtracting effects based on file uploads")
    if not request.args.get('outcomefile') or not request.args.get('snpfile'):
        return json.dumps([])
    if not check_filename(request.args.get('outcomefile')) or not check_filename(request.args.get('snpfile')):
        return json.dumps([])
    if not request.args.get('proxies'):
        logging.info("not getting proxies by default")
        proxies = '0'
    else:
        proxies = request.args.get('proxies')

    if not request.args.get('rsq'):
        rsq = 0.8
    else:
        rsq = float(request.args.get('rsq'))
    if not request.args.get('align_alleles'):
        align_alleles = '1'
    else:
        align_alleles = '0'
    if not request.args.get('palindromes'):
        palindromes = '1'
    else:
        palindromes = '0'
    if not request.args.get('maf_threshold'):
        maf_threshold = 0.3
    else:
        maf_threshold = float(request.args.get('maf_threshold'))

    snpfile     = UPLOAD_FOLDER + os.path.basename(request.args.get('snpfile'))
    outcomefile = UPLOAD_FOLDER + os.path.basename(request.args.get('outcomefile'))

    with open(snpfile) as f:
        snps = f.readlines()
        snps = [x.strip("\n") for x in snps]
    os.remove(snpfile)

    with open(outcomefile) as f:
        outcomes = f.readlines()
        outcomes = [x.strip("\n") for x in outcomes]
    os.remove(outcomefile)

    logging.info("extracting data for "+str(len(snps))+" SNP(s) in "+str(len(outcomes))+" outcome(s)")

    if proxies == '0':
        logging.info("not using LD proxies")
        snps = ",".join([ "'" + x.strip("\n") + "'" for x in snps])
        outcomes = ",".join([ "'" + x.strip("\n") + "'" for x in outcomes])
        return json.dumps(query_summary_stats(request.args.get('access_token'), snps, outcomes), ensure_ascii=False)
    else:
        logging.info("using LD proxies")
        # cp = get_snp_positions(snps)
        # snps = [x.get('name') for x in cp]
        # chr = [x.get('chrom').replace("chr", "eur") + ".ld" for x in cp]
        proxy_dat = get_proxies_mysql(snps, rsq, palindromes, maf_threshold)
        proxies = [x.get('proxies') for x in [item for sublist in proxy_dat for item in sublist]]
        # proxy_query = query_summary_stats(request.args.get('access_token'), joinarray(proxies), joinarray(outcomes))
        proxy_query = query_summary_stats(request.args.get('access_token'), joinarray(proxies), joinarray(outcomes))
        res = extract_proxies_from_query(outcomes, snps, proxy_dat, proxy_query, maf_threshold, align_alleles)
        return json.dumps(res, ensure_ascii=False)





@app.route("/clump", methods=[ 'GET' ])
def clump():
    if not request.args.get('snpfile'):
        return json.dumps([])
    if not check_filename(request.args.get('snpfile')):
        return json.dumps([])
    if not request.args.get('p1'):
        p1 = 1
    else:
        p1 = int(request.args.get('p1'))
    if not request.args.get('p2'):
        p2 = 1
    else:
        p2 = int(request.args.get('p2'))
    if not request.args.get('r2'):
        r2 = 0.1
    else:
        r2 = float(request.args.get('r2'))
    if not request.args.get('kb'):
        kb = 5000
    else:
        kb = int(request.args.get('kb'))


    fn = os.path.basename(request.args.get('snpfile'))
    snpfile = UPLOAD_FOLDER + fn

    ress = []
    f = open(snpfile, "r")
    reader = csv.DictReader(f, delimiter=" ")
    for row in reader:
        ress.append(row)

    f.close()

    # snps = [x.get('SNP') for x in ress]
    # cp = get_snp_positions(snps)

    # out = plink_clumping(fn, UPLOAD_FOLDER, cp, ress, "SNP", "P", p1, p2, r2, kb)
    out = plink_clumping_rs(fn, UPLOAD_FOLDER, ress, "SNP", "P", p1, p2, r2, kb)
    return json.dumps(out, ensure_ascii=False)

@app.route("/test_api_server", methods=[ 'GET' ])
def test_api_server():
    return "API server alive!!!!??"
