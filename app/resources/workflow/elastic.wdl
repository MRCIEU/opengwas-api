version 1.0

workflow elastic {
    input {
        String Host
        String Port

        String StudyId
        String OCIObjectStoragePAR = "/data/oci_object_storage_par_url.txt"
        String EsIndex
        String MountDir = "/data"
        String BaseDir = "/data/igd"
        File VcfFile=BaseDir + "/" + StudyId + "/" + StudyId + ".vcf.gz"
        File VcfFileIdx=BaseDir + "/" + StudyId + "/" + StudyId + ".vcf.gz.tbi"
        File ClumpFile=BaseDir + "/" + StudyId + "/clump.txt"
        String ElasticCompleteFilePath=BaseDir + "/" + StudyId + "/ElasticComplete.txt"
    }

    call upload {
        input:
            StudyId=StudyId,
            OCIObjectStoragePAR=OCIObjectStoragePAR,
            BaseDir=BaseDir
    }
    call get_index_from_study {
        input:
            UploadDone=upload.UploadDone,
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

task upload {
    input {
        String OCIObjectStoragePAR
        String BaseDir
        String StudyId
    }

    command <<<
        set -e
        source ~{OCIObjectStoragePAR}
        cd ~{BaseDir}/~{StudyId}
        curl -X PUT --data-binary '@~{StudyId}.json' ${OCI_PAR_URL_DATA}~{StudyId}/~{StudyId}.json
        curl -X PUT --data-binary '@~{StudyId}_analyst.json' ${OCI_PAR_URL_DATA}~{StudyId}/~{StudyId}_analyst.json
        curl -X PUT --data-binary '@~{StudyId}_labels.json' ${OCI_PAR_URL_DATA}~{StudyId}/~{StudyId}_labels.json
        curl -X PUT --data-binary '@~{StudyId}_data.json' ${OCI_PAR_URL_DATA}~{StudyId}/~{StudyId}_data.json
        curl -X PUT --data-binary '@~{StudyId}_wdl.json' ${OCI_PAR_URL_DATA}~{StudyId}/~{StudyId}_wdl.json
        curl -X PUT --data-binary '@clump.txt' ${OCI_PAR_URL_DATA}~{StudyId}/clump.txt
        curl -X PUT --data-binary '@~{StudyId}.vcf.gz' ${OCI_PAR_URL_DATA}~{StudyId}/~{StudyId}.vcf.gz
        curl -X PUT --data-binary '@~{StudyId}.vcf.gz.tbi' ${OCI_PAR_URL_DATA}~{StudyId}/~{StudyId}.vcf.gz.tbi
    >>>

    output {
        String UploadDone = StudyId
    }
}

task get_index_from_study {
    input {
        String UploadDone
        String StudyId
    }
    
    command <<<
        set -e
        awk -F"-" '{print $1"-"$2}' <<< ~{StudyId}
    >>>
    
    output {
        Array[String] values = read_lines(stdout())
        String index_name = values[0]
    }
}

task insert {
    input {
        String MountDir
        File VcfFile
        File VcfFileIdx
        String StudyId
        String EsIndex
        File ClumpFile
        String Host
        String Port
    }

    command <<<
        set -e

        docker run \
        --rm \
        -v ~{MountDir}:~{MountDir} \
        --cpus="1" \
        igd-elasticsearch:latest \
        python add-gwas.py \
        -m index_data \
        -f ~{VcfFile} \
        -g ~{StudyId} \
        -i ~{EsIndex} \
        -e ~{Host} \
        -p ~{Port} \
        -t ~{ClumpFile}
    >>>

}

task ready_for_rsync {
    input {
        String ElasticCompleteFilePath
    }
    
    command <<<
        touch ~{ElasticCompleteFilePath}
    >>>
    
    output {
        File complete = "~{ElasticCompleteFilePath}"
    }
}
