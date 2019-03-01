import subprocess
import os


class Harmonisation:
    def launch_reference_panel_harmonisation(self):
        # TODO
        raise NotImplemented

    @staticmethod
    def launch_genome_harmonisation(id, gwas_file, chr_col, pos_col, snp_col, ea_col, oa_col, eaf_col, beta_col, se_col,
                                    pval_col, ncontrol_col, ncase_col, delimiter, header, gzipped):

        if

        process = [
            "docker",
            "run",
            "-o", None,
            "-g", gwas_file,
        ]
        subprocess.run(process, capture_output=True)
