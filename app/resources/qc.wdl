workflow qc {

    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/bgc"
    File RefGenomeFile="/data/ref/human_g1k_v37.fasta"
    File RefGenomeFileIdx="/data/ref/human_g1k_v37.fasta.fai"
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
            BcfFile=bcf.BcfFile,
            BcfFileIdx=bcf.BcfFileIdx
    }
    call ldsc {
        input:
            MountDir=MountDir,
            LdscFilePath=BaseDir + "/" + StudyId + "/ldsc.txt",
            BcfFile=bcf.BcfFile,
            BcfFileIdx=bcf.BcfFileIdx
    }
    call report {
        input:
            MountDir=MountDir,
            BcfFile=bcf.BcfFile,
            BcfFileIdx=bcf.BcfFileIdx,
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
        gwas_harmonisation_wdl:latest \
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
        gwas_processing_wdl:latest \
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
        mrbase-report_wdl:latest \
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