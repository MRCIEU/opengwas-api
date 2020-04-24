workflow elastic {
    String Host = "140.238.83.192"
    String Port = 9200

    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/igd"
    File VcfFile=BaseDir + "/" + StudyId + "/" + StudyId + "_data.vcf.gz"
    File VcfFileIdx=BaseDir + "/" + StudyId + "/" + StudyId + "_data.vcf.gz.tbi"
    File ClumpFile=BaseDir + "/" + StudyId + "/clump.txt"
    
    call get_index_from_study {
        input:
            StudyId=StudyId
    }
    call insert {
        input:
            MountDir=MountDir,
            VcfFile=VcfFile,
            VcfFileIdx=VcfFileIdx,
            StudyId=StudyId,
            EsIndex=get_index_from_study.index_name,
            ClumpFile=ClumpFile,
            Host=Host,
            Port=Port
    }

}

task get_index_from_study {
    String StudyId
    
    command <<<
        set -e
        awk -F"-" '{print $1"-"$2}' <<< ${StudyId}
    >>>
    
    output {
        Array[String] values = read_lines(stdout())
        String index_name = values[0]
    }
}

task insert {

    String MountDir
    File VcfFile
    File VcfFileIdx
    String StudyId
    String EsIndex
    File ClumpFile
    String Host
    String Port

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        igd-elasticsearch:670f82529cc466f9003d53f1f14d2c2582abc7c6 \
        python add-gwas.py \
        -m index_data \
        -f ${VcfFile} \
        -g ${StudyId} \
        -i ${EsIndex} \
        -e ${Host} \
        -p ${Port} \
        -t ${ClumpFile}
    >>>

}
