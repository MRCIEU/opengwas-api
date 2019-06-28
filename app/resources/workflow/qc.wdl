workflow qc {

    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/bgc"
    File RefGenomeFile="/data/ref/human_g1k_v37.fasta"
    File RefGenomeFileIdx="/data/ref/human_g1k_v37.fasta.fai"
    File RefGenomeFileDict="/data/ref/human_g1k_v37.dict"
    File RefData = "/data/ref/1kg_v3_nomult.bcf"
    File RefDataIdx = "/data/ref/1kg_v3_nomult.bcf.csi"

    call bcf {
        input:
            MountDir=MountDir,
            BcfFilePath=BaseDir + "/" + StudyId + "/data.bcf",
            SumStatsFile=BaseDir + "/" + StudyId + "/raw/upload.txt.gz",
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx,
            ParamFile=BaseDir + "/" + StudyId + "/raw/upload.json",
            StudyId=StudyId
    }
    call clumping {
        input:
            MountDir=MountDir,
            ClumpFilePath=BaseDir + "/" + StudyId + "/clump.txt",
            BcfFile=bcf.BcfFileAnno,
            BcfFileIdx=bcf.BcfFileAnnoIdx
    }
    call ldsc {
        input:
            MountDir=MountDir,
            LdscFilePath=BaseDir + "/" + StudyId + "/ldsc.txt",
            BcfFile=bcf.BcfFileAnno,
            BcfFileIdx=bcf.BcfFileAnnoIdx
    }
    call report {
        input:
            MountDir=MountDir,
            BcfFile=bcf.BcfFileAnno,
            BcfFileIdx=bcf.BcfFileAnnoIdx,
            RefData=RefData,
            RefDataIdx=RefDataIdx,
            OutputDir=BaseDir + "/" + StudyId
    }

}

task bcf {

    String MountDir
    String BcfFilePath
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
        gwas_harmonisation:b596286b6cc206d9b7296b2b919f2020cf3158cd \
        python /app/main.py \
        --data ${SumStatsFile} \
        --id ${StudyId} \
        --json ${ParamFile} \
        --ref ${RefGenomeFile} \
        --out ${BcfFilePath} \
        --rm_chr_prefix
    >>>

    output {
        File BcfFile = "${BcfFilePath}"
        File BcfFileIdx = "${BcfFilePath}.csi"
    }

}

task annotate {

    String MountDir
    File BcfFile
    File BcfFileIdx
    File RefData
    File RefDataIdx
    String BcfFileAnnoPath


    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        halllab/bcftools:v1.9 \
        bcftools annotate \
        -a ${RefData} \
        -c ID ${BcfFile} \
        -o ${BcfFileAnnoPath} \
       -O b

    >>>

    output {
        File BcfFileAnno = "${BcfFileAnnoPath}"
        File BcfFileAnnoIdx = "${BcfFileAnnoPath}.csi"
    }

}

task clumping {

    String MountDir
    String ClumpFilePath
    File BcfFile
    File BcfFileIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_processing:d9cefe5d1ed36e53c648fac69fe35a0d1d7afac6 \
        clump.py \
        --bcf ${BcfFile} \
        --out ${ClumpFilePath}
    >>>

    output {
        File ClumpFile = "${ClumpFilePath}"
    }

}

task ldsc {

    String MountDir
    String LdscFilePath
    File BcfFile
    File BcfFileIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_processing_wdl:latest \
        ldsc.py \
        --bcf ${BcfFile} \
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
    File BcfFile
    File BcfFileIdx
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
        ${BcfFile} \
        --output_dir ${OutputDir} \
        --refdata ${RefData} \
        --n_cores 1
    >>>

    output {
        File ReportFile = "${OutputDir}/report.html"
        File MetaJsonFile = "${OutputDir}/metadata.json"
        File QcMetricsJsonFile = "${OutputDir}/qc_metrics.json"
    }

}
