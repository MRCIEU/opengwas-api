from flask_restful import Api, Resource, reqparse, abort
from _globals import *
from _logger import *
import uuid
import time


class Clump(Resource):
	def post(self):
		parser = reqparse.RequestParser()
		parser.add_argument('access_token', required=False, type=str, default='NULL')
		parser.add_argument('rsid', type=str, required=False, action='append', default=[])
		parser.add_argument('pval', type=float, required=False, action='append', default=[])
		parser.add_argument('p1', type=float, required=False, default=5e-8, location='json')
		parser.add_argument('r2', type=float, required=False, default=0.001, location='json')
		parser.add_argument('kb', type=int, required=False, default=5000, location='json')
		args = parser.parse_args()
		try:
			out = plink_clumping_rs(TMP_FOLDER, args['rsid'], args['pval'], args['p1'], args['p1'], args['r2'], args['kb'])
		except:
			abort(503)
		return out, 200

def plink_clumping_rs(upload_folder, rsid, pval, p1, p2, r2, kb):

	try:
		start = time.time()
		filename = os.path.join(upload_folder, str(uuid.uuid4()))
		tfile = open(filename, "w")
		tfile.write("SNP P\n")
		for i in xrange(len(rsid)):
			tfile.write(str(rsid[i]) + " " + str(pval[i]) + "\n")

		tfile.close()
		command =   "{0} " \
					" --bfile {1} " \
					" --clump {2} " \
					" --clump-p1 {3} " \
					" --clump-p2 {4} " \
					" --clump-r2 {5} " \
					" --clump-kb {6} " \
					" --out {7}".format(PLINK, LD_REF, filename, p1, p2, r2, kb, filename)

		logger2.debug(command)
		os.system(command)

		filename_c = filename + ".clumped"
		f = open(filename_c, "r")
		f.readline()
		words = f.read().split("\n")
		f.close()

		logger2.debug("matching clumps to original query")
		out = []
		for x in words:
			if x is not '':
				out.append([y for y in rsid if y == x.split()[2]][0])
		logger2.debug("done match")
		end = time.time()
		t=round((end - start), 4)
		logger2.debug('clumping: took '+str(t)+' seconds')
	finally:
		[os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(os.path.basename(filename))]
	return out

# @app.route("/ld", methods=[ 'GET' ])
# def ld():
#     logger.info('ld')
#     if not request.args.get('snpfile'):
#         return json.dumps([])
#     if not check_filename(request.args.get('snpfile')):
#         return json.dumps([])

#     fn = os.path.basename(request.args.get('snpfile'))
#     snpfile = UPLOAD_FOLDER + fn

#     with open(snpfile) as f:
#         snps = f.readlines()
#         snps = [x.strip("\n") for x in snps]
#     os.remove(snpfile)

#     out = plink_ldsquare_rs(fn, UPLOAD_FOLDER, snps)
#     return json.dumps(out, ensure_ascii=False)


class LdMatrix(Resource):
	def post(self):
		parser = reqparse.RequestParser()
		parser.add_argument('rsid', required=False, type=str, action='append', default=[])
		parser.add_argument('p1', type=float, required=False, default=5e-8, location='json')
		parser.add_argument('r2', type=float, required=False, default=0.001, location='json')
		parser.add_argument('kb', type=int, required=False, default=5000, location='json')
		args = parser.parse_args()
		try:
			out = plink_ldsquare_rs(TMP_FOLDER, args['rsid'])
		except:
			abort(503)
		return out, 200



def plink_ldsquare_rs(upload_folder, snps):

    try:
    	fn = str(uuid.uuid4())
        filename = os.path.join(upload_folder, fn + "_recode")
        filenameb = os.path.join(upload_folder, fn + "_recode.bim")
        filenamek = os.path.join(upload_folder, fn + "_recode.keep")
        filenameka = os.path.join(upload_folder, fn + "_recode.keep.a")
        tfile = open(filename, "w")
        # tfile.write("SNP P\n")
        for i in xrange(len(snps)):
            tfile.write(str(snps[i]) + "\n")

        tfile.close()

        # Find which SNPs are present
        logger2.debug("Finding which snps are available")
        # cmd = "fgrep -wf " + filename + " ./ld_files/data_maf0.01_rs.bim > " + filenameb
        cmd =   "{0} " \
                "--bfile {1} " \
                " --extract {2} " \
                " --make-just-bim " \
                " --out {3}".format(PLINK, LD_REF, filename, filename)
        logger2.debug(cmd)
        os.system(cmd)
        cmd = "cut -d ' ' -f 1 " + filenameb + " > " + filenamek
        logger2.debug(cmd)
        os.system(cmd)
        cmd = "awk '{OFS=\"\"; print $2, \"_\", $5, \"_\", $6 }' " + filenameb + " > " + filenameka
        logger2.debug(cmd)
        os.system(cmd)
        logger2.debug("found")
        command =   "{0} " \
                    "--bfile {1} " \
                    " --extract {2} " \
                    " --r square " \
                    " --out {3}".format(PLINK, LD_REF, filenamek, filename)

        logger2.debug(command)
        os.system(command)
        filename_c = filename + ".ld"
        if not os.path.isfile(filename_c):
             logger2.debug("no file found")
             [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]
             return ['NA']

        mat = []
        f = open(filenameka, "r")
        mat.append(filter(None, f.read().split("\n")))
        f.close()

        f = open(filename_c, "r")
        for line in open(filename_c, "r").readlines():
            mat.append(line.strip("\n").split("\t"))
        f.close()

    finally:
    	# logger2.debug("finished")
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

    return mat
