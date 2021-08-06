workflow elastic {
    String Host
    String Port

    String StudyId
    String EsIndex
    String MountDir = "/data"
    String BaseDir = "/data/igd"
    File VcfFile=BaseDir + "/" + StudyId + "/" + StudyId + ".vcf.gz"
    File VcfFileIdx=BaseDir + "/" + StudyId + "/" + StudyId + ".vcf.gz.tbi"
    File ClumpFile=BaseDir + "/" + StudyId + "/clump.txt"
    String ElasticCompleteFilePath=BaseDir + "/" + StudyId + "/ElasticComplete.txt"
    
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
            EsIndex=EsIndex,
            ClumpFile=ClumpFile,
            Host=Host,
            Port=Port
    }
    call ready_for_rsync {
        input:
            ElasticCompleteFilePath=ElasticCompleteFilePath
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
        igd-elasticsearch:a34eb18f2a0bd215b6d7632fec77c7b16dcf737e \
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

task ready_for_rsync {

    String ElasticCompleteFilePath
    
    command <<<
        touch ${ElasticCompleteFilePath}
    >>>
    
    output {
        File complete = "${ElasticCompleteFilePath}"
    }
}
