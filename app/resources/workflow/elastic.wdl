workflow elastic {

    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/igd"
    File BcfFile = BaseDir + "/" + StudyId + "/" + StudyId + "_data.vcf.gz"
    File BcfFileIdx = BaseDir + "/" + StudyId + "/" + StudyId + "_data.vcf.gz"
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
        bgc-elasticsearch:c182e62734e62bc152cd9d11061b4bc583c6347a \
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
