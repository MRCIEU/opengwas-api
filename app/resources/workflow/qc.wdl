workflow qc {

    String StudyId
    Int? Cases
    Int? Controls
    String MountDir = "/data"
    String BaseDir = "/data/igd"
    File RefGenomeFile="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.fasta"
    File RefGenomeFileIdx="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.fasta.fai"
    File RefGenomeFileDict="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.dict"
    File DbSnpVcfFile="/data/dbsnp/released/2019-09-11/data/dbsnp.v153.b37.vcf.gz"
    File DbSnpVcfFileIdx="/data/dbsnp/released/2019-09-11/data/dbsnp.v153.b37.vcf.gz.tbi"
    File AfVcfFile="/data/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.gz"
    File AfVcfFileIdx="/data/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.gz.tbi"

    # TODO remove
    File RefData = "/data/ref/1kg_v3_nomult.bcf"
    File RefDataIdx = "/data/ref/1kg_v3_nomult.bcf.csi"

    call vcf {
        input:
            MountDir=MountDir,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + "_harm.vcf.gz",
            SumStatsFile=BaseDir + "/" + StudyId + "/raw/upload.txt.gz",
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx,
            ParamFile=BaseDir + "/" + StudyId + "/raw/upload.json",
            StudyId=StudyId,
            Cases=Cases,
            Controls=Controls
    }
    call combine_multiallelics {
        input:
            MountDir=MountDir,
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx,
            VcfFileIn=vcf.VcfFile,
            VcfFileInIdx=vcf.VcfFileIdx,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + "_norm.vcf.gz"
    }
    call annotate_dbsnp {
        input:
            MountDir=MountDir,
            VcfFileIn=combine_multiallelics.VcfFile,
            VcfFileInIdx=combine_multiallelics.VcfFileIdx,
            DbSnpVcfFile=DbSnpVcfFile,
            DbSnpVcfFileIdx=DbSnpVcfFileIdx,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + "_dbsnp.vcf.gz"
    }
    call annotate_af {
        input:
            MountDir=MountDir,
            VcfFileIn=annotate_dbsnp.VcfFile,
            VcfFileInIdx=annotate_dbsnp.VcfFileIdx,
            AfVcfFile=AfVcfFile,
            AfVcfFileIdx=AfVcfFileIdx,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + "_data.vcf.gz"
    }
    call validate {
        input:
            MountDir=MountDir,
            VcfFileIn=annotate_af.VcfFile,
            VcfFileInIdx=annotate_af.VcfFileIdx,
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx,
            RefGenomeFileDict=RefGenomeFileDict
    }
    call clumping {
        input:
            MountDir=MountDir,
            ClumpFilePath=BaseDir + "/" + StudyId + "/clump.txt",
            VcfFileIn=annotate_af.VcfFile,
            VcfFileInIdx=annotate_af.VcfFileIdx
    }
    call ldsc {
        input:
            MountDir=MountDir,
            LdscFilePath=BaseDir + "/" + StudyId + "/ldsc.txt",
            VcfFileIn=annotate_af.VcfFile,
            VcfFileInIdx=annotate_af.VcfFileIdx
    }
    #call report {
    #    input:
    #        MountDir=MountDir,
    #        VcfFileIn=annotate_af.VcfFile,
    #        VcfFileInIdx=annotate_af.VcfFileIdx,
    #        RefData=RefData,
    #        RefDataIdx=RefDataIdx,
    #        OutputDir=BaseDir + "/" + StudyId
    #}

}

task vcf {

    String MountDir
    String VcfFileOutPath
    File SumStatsFile
    File RefGenomeFile
    File RefGenomeFileIdx
    File ParamFile
    String StudyId
    Int? Cases
    Int? Controls

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas2vcf:66fb44438fb5b42dc88830e5f7497e26231684da \
        python /app/main.py \
        --data ${SumStatsFile} \
        --id ${StudyId} \
        --json ${ParamFile} \
        --ref ${RefGenomeFile} \
        --out ${VcfFileOutPath} \
        --rm_chr_prefix \
        ${"--cohort_cases" + Cases} \
        ${"--cohort_controls" + Controls}
    >>>

    output {
        File VcfFile = "${VcfFileOutPath}"
        File VcfFileIdx = "${VcfFileOutPath}.tbi"
    }

}

task combine_multiallelics {

    String MountDir
    File VcfFileIn
    File VcfFileInIdx
    File RefGenomeFile
    File RefGenomeFileIdx
    String VcfFileOutPath

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools norm \
        -f ${RefGenomeFile} \
        -m +any \
        -O z \
        -o ${VcfFileOutPath} \
        ${VcfFileIn}

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools index \
        -t \
        ${VcfFileOutPath}

    >>>

    output {
        File VcfFile = "${VcfFileOutPath}"
        File VcfFileIdx = "${VcfFileOutPath}.tbi"
    }

}

task annotate_dbsnp {

    String MountDir
    File VcfFileIn
    File VcfFileInIdx
    File DbSnpVcfFile
    File DbSnpVcfFileIdx
    String VcfFileOutPath


    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools annotate \
        -a ${DbSnpVcfFile} \
        -c ID \
        -o ${VcfFileOutPath} \
        -O z \
        ${VcfFileIn}

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools index \
        -t \
        ${VcfFileOutPath}

    >>>

    output {
        File VcfFile = "${VcfFileOutPath}"
        File VcfFileIdx = "${VcfFileOutPath}.tbi"
    }

}

task annotate_af {

    String MountDir
    File VcfFileIn
    File VcfFileInIdx
    File AfVcfFile
    File AfVcfFileIdx
    String VcfFileOutPath


    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools annotate \
        -a ${AfVcfFile} \
        -c AF,EAS_AF,EUR_AF,AFR_AF,AMR_AF,SAS_AF \
        -o ${VcfFileOutPath} \
        -O z \
        ${VcfFileIn}

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools index \
        -t \
        ${VcfFileOutPath}

    >>>

    output {
        File VcfFile = "${VcfFileOutPath}"
        File VcfFileIdx = "${VcfFileOutPath}.tbi"
    }

}

task validate {

    String MountDir
    File VcfFileIn
    File VcfFileInIdx
    File RefGenomeFile
    File RefGenomeFileIdx
    File RefGenomeFileDict

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        broadinstitute/gatk:4.1.3.0 \
        gatk ValidateVariants \
        --validation-type-to-exclude ALLELES \
        -V ${VcfFileIn} \
        -R ${RefGenomeFile}

    >>>

}

task clumping {

    String MountDir
    String ClumpFilePath
    File VcfFileIn
    File VcfFileInIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_processing:305e3e5133a19b87ab0031488e01588f76ee1be0 \
        clump.py \
        --bcf ${VcfFileIn} \
        --out ${ClumpFilePath}
    >>>

    output {
        File ClumpFile = "${ClumpFilePath}"
    }

}

task ldsc {

    String MountDir
    String LdscFilePath
    File VcfFileIn
    File VcfFileInIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_processing:305e3e5133a19b87ab0031488e01588f76ee1be0 \
        ldsc.py \
        --bcf ${VcfFileIn} \
        --out ${LdscFilePath}
    >>>

    output {
        File LdscFile = "${LdscFilePath}.log"
    }
    runtime {
        continueOnReturnCode: [0, 125]
    }

}

task report {

    String MountDir
    String OutputDir
    File VcfFileIn
    File VcfFileInIdx
    File RefData
    File RefDataIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        mrbase-report-module:177aa4b3170d984c704384cc47309162edc4fbe9 \
        Rscript render_gwas_report.R \
        ${VcfFileIn} \
        --output_dir ${OutputDir} \
        --n_cores 1
    >>>

    output {
        File ReportFile = "${OutputDir}/report.html"
        File MetaJsonFile = "${OutputDir}/metadata.json"
        File QcMetricsJsonFile = "${OutputDir}/qc_metrics.json"
    }

}
