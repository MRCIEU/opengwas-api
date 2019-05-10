workflow upload {

    # TODO add to globals
    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/bgc"
    String RefGenomeFile="/data/ref/human_g1k_v37.fasta"
    String RefGenomeFileIdx="/data/ref/human_g1k_v37.fasta.fai"
    File RefData = "/data/ref/1kg_v3_nomult.bcf"
    File RefDataIdx = "/data/ref/1kg_v3_nomult.bcf.csi"
    String EsIndex = "bcftest"
    String Host = "ieu-db-interface.epi.bris.ac.uk"
    String Port = 9200

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
    call elastic {
        input:
            MountDir=MountDir,
            BcfFile=bcf.BcfFile,
            BcfFileIdx=bcf.BcfFileIdx,
            StudyId=StudyId,
            ClumpFile=clumping.ClumpFile,
            EsIndex=EsIndex,
            Host=Host,
            Port=Port
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
        --out ${BcfFilePath}
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

task elastic {

    String MountDir
    File BcfFile
    File BcfFileIdx
    String StudyId
    File ClumpFile
    String EsIndex
    String Host
    String Port

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        bgc-elasticsearch_wdl:latest \
        python add-gwas.py \
        -m index_data \
        -f ${BcfFile} \
        -g ${StudyId} \
        -i ${EsIndex} \
        -h ${Host} \
        -p ${Port} \
        -t ${ClumpFile}
    >>>

}
