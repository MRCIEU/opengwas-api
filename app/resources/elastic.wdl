workflow elastic {

    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/bgc"
    File BcfFile = BaseDir + "/" + StudyId + "/" + StudyId + ".bcf"
    File BcfFileIdx = BaseDir + "/" + StudyId + "/" + StudyId + ".bcf.csi"
    File ClumpFile=BaseDir + "/" + StudyId + "/clump.txt"
    String EsIndex = "bcftest"
    String Host = "ieu-db-interface.epi.bris.ac.uk"
    String Port = 9200

    call insert {
        input:
            MountDir=MountDir,
            BcfFile=BcfFile,
            BcfFileIdx=BcfFileIdx,
            StudyId=StudyId,
            ClumpFile=ClumpFile,
            EsIndex=EsIndex,
            Host=Host,
            Port=Port
    }

}

task insert {

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