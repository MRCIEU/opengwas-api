import uuid
import time
import os.path
import logging

from resources.globals import Globals

logger = logging.getLogger('debug-log')


def execute_command(command):
    if os.environ.get('ENV') == 'production':
        command = '({}) > /dev/null 2>&1'.format(command)
    os.system(command)


def plink_clumping_rs(upload_folder, rsid, pval, p1, p2, r2, kb, pop="EUR"):
    try:
        start = time.time()
        filename = os.path.join(upload_folder, str(uuid.uuid4()))

        with open(filename, "w") as tfile:
            tfile.write("SNP P\n")

            for i in range(len(rsid)):
                tfile.write(str(rsid[i]) + " " + str(pval[i]) + "\n")

        command = "{0}" \
                  " --silent" \
                  " --bfile {1}" \
                  " --clump {2}" \
                  " --clump-p1 {3}" \
                  " --clump-p2 {4}" \
                  " --clump-r2 {5}" \
                  " --clump-kb {6}" \
                  " --out {7}".format(Globals.PLINK, Globals.LD_REF[pop], filename, p1, p2, r2, kb, filename)

        logger.debug(command)
        execute_command(command)

        filename_c = filename + ".clumped"
        words = []
        if os.path.exists(filename_c):
            f = open(filename_c, "r")
            f.readline()
            words = f.read().split("\n")
            f.close()

        logger.debug("matching clumps to original query")
        out = []
        for x in words:
            if x != '':
                out.append(x.split()[2])
                # out.append([y for y in rsid if y == x.split()[2]][0])
        logger.debug("done match")
        end = time.time()
        t = round((end - start), 4)
        logger.debug('clumping: took ' + str(t) + ' seconds')
    finally:
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if
         f.startswith(os.path.basename(filename))]
    return out


def plink_ldsquare_rs(upload_folder, snps, pop='EUR'):
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
        logger.debug("Finding which snps are available")
        # cmd = "fgrep -wf " + filename + " ./ld_files/data_maf0.01_rs.bim > " + filenameb
        cmd = "{0}" \
              " --silent" \
              " --bfile {1}" \
              " --extract {2}" \
              " --make-just-bim" \
              " --out {3}".format(Globals.PLINK, Globals.LD_REF[pop], filename, filename)
        logger.debug(cmd)
        execute_command(cmd)
        cmd = "cut -d ' ' -f 1 " + filenameb + " > " + filenamek
        logger.debug(cmd)
        execute_command(cmd)
        cmd = "awk '{OFS=\"\"; print $2, \"_\", $5, \"_\", $6 }' " + filenameb + " > " + filenameka
        logger.debug(cmd)
        execute_command(cmd)
        logger.debug("found")
        command = "{0}" \
                  " --silent" \
                  " --bfile {1}" \
                  " --extract {2}" \
                  " --r square" \
                  " --out {3}".format(Globals.PLINK, Globals.LD_REF[pop], filenamek, filename)

        logger.debug(command)
        execute_command(command)
        filename_c = filename + ".ld"
        if not os.path.isfile(filename_c):
            logger.debug("no file found")
            [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]
            return {'snplist': [], 'matrix': []}

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
        logger.debug("finished")
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

    # print(str(out))

    return out


def ld_ref_lookup(upload_folder, snps, pop='EUR'):
    try:
        fn = str(uuid.uuid4())
        filename = os.path.join(upload_folder, fn + "_snplist")
        filename_out = os.path.join(upload_folder, fn + "_snplist.present")
        tfile = open(filename, "w")
        for i in range(len(snps)):
            tfile.write(str(snps[i]) + "\n")
        tfile.close()
        cmd = "fgrep -wf {0} {1}.bim | awk '{{print $2}}' > {2}".format(filename, Globals.LD_REF[pop], filename_out)
        logger.debug(cmd)
        execute_command(cmd)
        with open(filename_out, "r") as f:
            snplist = list(filter(None, f.read().split("\n")))

    finally:
        [os.remove(os.path.join(upload_folder, f)) for f in os.listdir(upload_folder) if f.startswith(fn)]

    return snplist
