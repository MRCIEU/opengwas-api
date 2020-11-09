workflow elastic {
    String Host = "140.238.83.192"
    String Port = 9200

    String StudyId
    String MountDir = "/data"
    String BaseDir = "/data/igd"
    File VcfFile=BaseDir + "/" + StudyId + "/" + StudyId + ".vcf.gz"
    File VcfFileIdx=BaseDir + "/" + StudyId + "/" + StudyId + ".vcf.gz.tbi"
    File ClumpFile=BaseDir + "/" + StudyId + "/clump.txt"
    File ElasticCompleteFile=BaseDir + "/" + StudyId + "/ElasticComplete.txt"
    
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
            EsIndex="ieu-b-1",
            ClumpFile=ClumpFile,
            Host=Host,
            Port=Port
    }
    call ready_for_rsync {
        input:
            ElasticCompleteFile=ElasticCompleteFile
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
        igd-elasticsearch:2adda12c992aa884ca3ac0ef74fced9a0dc745f3 \
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

    File ElasticCompleteFile
    
    command <<<
        touch ${ElasticCompleteFile}
    >>>
    
    output {
        File complete = "ElasticComplete.txt"
    }
}
