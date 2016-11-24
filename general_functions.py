import re
import os

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

