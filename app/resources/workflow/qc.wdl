workflow qc {

    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/igd"
    File RefGenomeFile="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.fasta"
    File RefGenomeFileIdx="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.fasta.fai"
    File RefGenomeFileDict="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.dict"
    File DbSnpVcfFile="/data/dbsnp/released/2019-09-02/dbsnp.v153.b37.vcf.gz"
    File DbSnpVcfFileIdx="/data/dbsnp/released/2019-09-02/dbsnp.v153.b37.vcf.gz.tbi"
    File AfVcfFile="/data/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.gz"
    File AfVcfFileIdx="/data/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.gz.tbi"

    # TODO remove
    File RefData = "/data/ref/1kg_v3_nomult.bcf"
    File RefDataIdx = "/data/ref/1kg_v3_nomult.bcf.csi"

    call vcf {
        input:
            MountDir=MountDir,
            VcfFilePath=BaseDir + "/" + StudyId + "/" + StudyId + "_harm.vcf.gz",
            SumStatsFile=BaseDir + "/" + StudyId + "/raw/upload.txt.gz",
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx,
            ParamFile=BaseDir + "/" + StudyId + "/raw/upload.json",
            StudyId=StudyId
    }
    call combine_multiallelics {
        input:
            MountDir=MountDir,
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx,
            VcfFile=vcf.VcfFile,
            VcfFileIdx=vcf.VcfFileIdx,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + "_norm.vcf.gz"
    }
    call annotate_dbsnp {
        input:
            MountDir=MountDir,
            VcfFile=combine_multiallelics.VcfFile,
            VcfFileIdx=combine_multiallelics.VcfFileIdx,
            DbSnpVcfFile=DbSnpVcfFile,
            DbSnpVcfFileIdx=DbSnpVcfFileIdx,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + "_dbsnp.vcf.gz"
    }
    call annotate_af {
        input:
            MountDir=MountDir,
            VcfFile=annotate_dbsnp.VcfFile,
            VcfFileIdx=annotate_dbsnp.VcfFile,
            AfVcfFile=AfVcfFile,
            AfVcfFileIdx=AfVcfFileIdx,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + "_1kg.vcf.gz"
    }
    call validate {
        input:
            MountDir=MountDir,
            VcfFile=annotate_af.VcfFile,
            VcfFileIdx=annotate_af.VcfFile,
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx
    }
    call clumping {
        input:
            MountDir=MountDir,
            ClumpFilePath=BaseDir + "/" + StudyId + "/clump.txt",
            VcfFile=annotate_af.VcfFile,
            VcfFileIdx=annotate_af.VcfFileIdx
    }
    call ldsc {
        input:
            MountDir=MountDir,
            LdscFilePath=BaseDir + "/" + StudyId + "/ldsc.txt",
            VcfFile=annotate_af.VcfFile,
            VcfFileIdx=annotate_af.VcfFileIdx
    }
    call report {
        input:
            MountDir=MountDir,
            VcfFile=annotate_af.VcfFile,
            VcfFileIdx=annotate_af.VcfFileIdx,
            RefData=RefData,
            RefDataIdx=RefDataIdx,
            OutputDir=BaseDir + "/" + StudyId
    }

}

# TODO support fixed sample size

task vcf {

    String MountDir
    String VcfFilePath
    File SumStatsFile
    File RefGenomeFile
    File RefGenomeFileIdx
    File ParamFile
    String StudyId

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_harmonisation:05de97b2879619b81884eb6739c0fa4861be951d \
        python /app/main.py \
        --data ${SumStatsFile} \
        --id ${StudyId} \
        --json ${ParamFile} \
        --ref ${RefGenomeFile} \
        --out ${VcfFilePath} \
        --rm_chr_prefix
    >>>

    output {
        File VcfFile = "${VcfFilePath}"
        File VcfFileIdx = "${VcfFilePath}.tbi"
    }

}

task combine_multiallelics {

    String MountDir
    File VcfFile
    File VcfFileIdx
    File RefGenomeFile
    File RefGenomeFileIdx
    String VcfFileNormPath

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
        -o ${VcfFileNormPath}
    >>>

    output {
        File VcfFileNorm = "${VcfFileNormPath}"
        File VcfFileNormIdx = "${VcfFileNormPath}.tbi"
    }

}

task annotate_dbsnp {

    String MountDir
    File VcfFile
    File VcfFileIdx
    File DbSnpVcfFile
    File DbSnpVcfFileIdx
    String VcfFileAnnoPath


    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools annotate \
        -a ${DbSnpVcfFile} \
        -c ID ${VcfFile} \
        -o ${VcfFileAnnoPath} \
        -O z

    >>>

    output {
        File VcfFileAnnoPath = "${VcfFileAnnoPath}"
        File VcfFileAnnoPathIdx = "${VcfFileAnnoPath}.tbi"
    }

}

task annotate_af {

    String MountDir
    File VcfFile
    File VcfFileIdx
    File PopFreqVcfFile
    File PopFreqVcfFileIdx
    String VcfFileAnnoPath


    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools annotate \
        -a ${PopFreqVcfFile} \
        -c ID ${VcfFile} \
        -o ${VcfFileAnnoPath} \
        -O z

    >>>

    output {
        File VcfFileAnnoPath = "${VcfFileAnnoPath}"
        File VcfFileAnnoPathIdx = "${VcfFileAnnoPath}.tbi"
    }

}

task validate {

    String MountDir
    File VcfFile
    File VcfFileIdx
    File RefGenomeFile
    File RefGenomeFileIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        broadinstitute/gatk:4.1.3.0 \
        ValidateVariants \
        --validation-type-to-exclude ALLELES \
        -V ${VcfFile} \
        -R ${RefGenomeFile}

    >>>

}

task clumping {

    String MountDir
    String ClumpFilePath
    File VcfFile
    File VcfFileIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_processing:f6444c2339a8e6a88013d1ac559004450bf862be \
        clump.py \
        --bcf ${VcfFile} \
        --out ${ClumpFilePath}
    >>>

    output {
        File ClumpFile = "${ClumpFilePath}"
    }

}

task ldsc {

    String MountDir
    String LdscFilePath
    File VcfFile
    File VcfFileIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_processing:f6444c2339a8e6a88013d1ac559004450bf862be \
        ldsc.py \
        --bcf ${VcfFile} \
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
    File VcfFile
    File VcfFileIdx
    File RefData
    File RefDataIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        mrbase-report-module:1ef1d2e07852d5f758609dccbebbc3eef7c279ea \
        render_gwas_report.R \
        ${VcfFile} \
        --output_dir ${OutputDir} \
        --n_cores 1
    >>>

    output {
        File ReportFile = "${OutputDir}/report.html"
        File MetaJsonFile = "${OutputDir}/metadata.json"
        File QcMetricsJsonFile = "${OutputDir}/qc_metrics.json"
    }

}
