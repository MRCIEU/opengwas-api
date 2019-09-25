workflow elastic {

    # TODO update dynamically when ready to deploy
    String EsIndex = "bcftest"

    # TODO check which host we are using
    String Host = "ieu-db-interface.epi.bris.ac.uk"
    String Port = 9200

    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/igd"
    File VcfFile=BaseDir + "/" + StudyId + "/" + StudyId + "_data.vcf.gz"
    File VcfFileIdx=BaseDir + "/" + StudyId + "/" + StudyId + "_data.vcf.gz.tbi"
    File ClumpFile=BaseDir + "/" + StudyId + "/clump.txt"

    call insert {
        input:
            MountDir=MountDir,
            VcfFile=VcfFile,
            VcfFileIdx=VcfFileIdx,
            StudyId=StudyId,
            ClumpFile=ClumpFile,
            EsIndex=EsIndex,
            Host=Host,
            Port=Port
    }

}

task insert {

    String MountDir
    File VcfFile
    File VcfFileIdx
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
        bgc-elasticsearch:3358ebb02f274f32a38ba30716446b013fe4a1e7 \
        python add-gwas.py \
        -m index_data \
        -f ${VcfFile} \
        -g ${StudyId} \
        -i ${EsIndex} \
        -h ${Host} \
        -p ${Port} \
        -t ${ClumpFile}
    >>>

}
