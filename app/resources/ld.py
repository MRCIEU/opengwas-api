from resources.globals import *
import uuid
import time
import logging
from resources.globals import Globals

def plink_clumping_rs(upload_folder, rsid, pval, p1, p2, r2, kb):
    try:
        start = time.time()
        filename = os.path.join(upload_folder, str(uuid.uuid4()))

        with open(filename, "w") as tfile:
            tfile.write("SNP P\n")

            for i in range(len(rsid)):
                tfile.write(str(rsid[i]) + " " + str(pval[i]) + "\n")

        command = "{0} " \
                  " --bfile {1} " \
                  " --clump {2} " \
                  " --clump-p1 {3} " \
                  " --clump-p2 {4} " \
                  " --clump-r2 {5} " \
                  " --clump-kb {6} " \
                  " --out {7}".format(Globals.PLINK, Globals.LD_REF, filename, p1, p2, r2, kb, filename)

        logging.debug(command)
        os.system(command)

        filename_c = filename + ".clumped"
        f = open(filename_c, "r")
        f.readline()
        words = f.read().split("\n")
        f.close()

        logging.debug("matching clumps to original query")
        out = []
        for x in words:
            if x is not '':
                out.append([y for y in rsid if y == x.split()[2]][0])
        logging.debug("done match")
        end = time.time()
        t = round((end - start), 4)
        logging.debug('clumping: took ' + str(t) + ' seconds')
    finally:
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if
         f.startswith(os.path.basename(filename))]
    return out


def plink_ldsquare_rs(upload_folder, snps):
    try:
        out = {}
        fn = str(uuid.uuid4())
        filename = os.path.join(upload_folder, fn + "_recode")
        filenameb = os.path.join(upload_folder, fn + "_recode.bim")
        filenamek = os.path.join(upload_folder, fn + "_recode.keep")
        filenameka = os.path.join(upload_folder, fn + "_recode.keep.a")
        tfile = open(filename, "w")
        # tfile.write("SNP P\n")
        for i in range(len(snps)):
            tfile.write(str(snps[i]) + "\n")

        tfile.close()

        # Find which SNPs are present
        logging.debug("Finding which snps are available")
        # cmd = "fgrep -wf " + filename + " ./ld_files/data_maf0.01_rs.bim > " + filenameb
        cmd = "{0} " \
              "--bfile {1} " \
              " --extract {2} " \
              " --make-just-bim " \
              " --out {3}".format(Globals.PLINK, Globals.LD_REF, filename, filename)
        logging.debug(cmd)
        os.system(cmd)
        cmd = "cut -d ' ' -f 1 " + filenameb + " > " + filenamek
        logging.debug(cmd)
        os.system(cmd)
        cmd = "awk '{OFS=\"\"; print $2, \"_\", $5, \"_\", $6 }' " + filenameb + " > " + filenameka
        logging.debug(cmd)
        os.system(cmd)
        logging.debug("found")
        command = "{0} " \
                  "--bfile {1} " \
                  " --extract {2} " \
                  " --r square " \
                  " --out {3}".format(Globals.PLINK, Globals.LD_REF, filenamek, filename)

        logging.debug(command)
        os.system(command)
        filename_c = filename + ".ld"
        if not os.path.isfile(filename_c):
            logging.debug("no file found")
            [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]
            return {'snplist': '', 'matrix': []}


        f = open(filenameka, "r")
        out["snplist"] = list(filter(None, f.read().split("\n")))
        f.close()

        mat = []
        f = open(filename_c, "r")
        for line in open(filename_c, "r").readlines():
            mat.append(line.strip("\n").split("\t"))
        f.close()
        out["matrix"] = mat
    finally:
        # print(upload_folder)
        logging.debug("finished")
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

    #print(str(out))

    return out