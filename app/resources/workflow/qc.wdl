version 1.0

workflow qc {
    input {
        String StudyId
        Int? Cases
        Int? Controls
        String OCIObjectStoragePAR = "/data/oci_object_storage_par_url.txt"
        String MountDir = "/data"
        String BaseDir = "/data/igd"
        String SumStatsFilename
        File RefGenomeFile="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.fasta"
        File RefGenomeFileIdx="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.fasta.fai"
        File RefGenomeFileDict="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.dict"
        File DbSnpVcfFile="/data/dbsnp/released/2019-09-11/data/dbsnp.v153.b37.vcf.gz"
        File DbSnpVcfFileIdx="/data/dbsnp/released/2019-09-11/data/dbsnp.v153.b37.vcf.gz.tbi"
        File AfVcfFile="/data/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.gz"
        File AfVcfFileIdx="/data/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.gz.tbi"
        File RefData = "/data/ref/1kg_v3_nomult.bcf"
        File RefDataIdx = "/data/ref/1kg_v3_nomult.bcf.csi"
    }

    call download {
        input:
            StudyId=StudyId,
            OCIObjectStoragePAR=OCIObjectStoragePAR,
            BaseDir=BaseDir,
            SumStatsFilename=SumStatsFilename
    }
    call vcf {
        input:
            MountDir=MountDir,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + ".vcf.gz",
            SumStatsFile=download.SumStatsFile,
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx,
            ParamFile=download.JSONDataFile,
            DbSnpVcfFile=DbSnpVcfFile,
            DbSnpVcfFileIdx=DbSnpVcfFileIdx,
            StudyId=StudyId,
            Cases=Cases,
            Controls=Controls
    }
    call clumping {
        input:
            MountDir=MountDir,
            ClumpFilePath=BaseDir + "/" + StudyId + "/clump.txt",
            VcfFileIn=vcf.VcfFile,
            VcfFileInIdx=vcf.VcfFileIdx
    }
    call ldsc {
        input:
            MountDir=MountDir,
            LdscFilePath=BaseDir + "/" + StudyId + "/ldsc.txt",
            VcfFileIn=vcf.VcfFile,
            VcfFileInIdx=vcf.VcfFileIdx
    }
    call report {
        input:
            MountDir=MountDir,
            VcfFileIn=vcf.VcfFile,
            VcfFileInIdx=vcf.VcfFileIdx,
            RefData=RefData,
            RefDataIdx=RefDataIdx,
            StudyId=StudyId,
            LdscFileIn=ldsc.LdscFile,
            ClumpFileIn=clumping.ClumpFile,
            MetaJsonIn=BaseDir + "/" + StudyId + "/" + StudyId + ".json",
            OutDirPath=BaseDir + "/" + StudyId
    }
    call upload_report {
        input:
            StudyId=StudyId,
            OCIObjectStoragePAR=OCIObjectStoragePAR,
            BaseDir=BaseDir,
            ReportFileIn=report.ReportFile
    }

}

task download {
    input {
        String OCIObjectStoragePAR
        String StudyId
        String BaseDir
        String SumStatsFilename
    }

    command <<<
        set -e
        source ~{OCIObjectStoragePAR}
        rm -rf ~{BaseDir}/~{StudyId}
        mkdir -p ~{BaseDir}/~{StudyId}
        cd ~{BaseDir}/~{StudyId}
        wget ${OCI_PAR_URL_UPLOAD}~{StudyId}/~{StudyId}.json
        wget ${OCI_PAR_URL_UPLOAD}~{StudyId}/~{StudyId}_analyst.json
        wget ${OCI_PAR_URL_UPLOAD}~{StudyId}/~{StudyId}_labels.json
        wget ${OCI_PAR_URL_UPLOAD}~{StudyId}/~{StudyId}_data.json
        wget ${OCI_PAR_URL_UPLOAD}~{StudyId}/~{StudyId}_wdl.json
        wget ${OCI_PAR_URL_UPLOAD}~{StudyId}/~{SumStatsFilename}
    >>>

    output {
        File JSONDataFile = "~{BaseDir}/~{StudyId}/~{StudyId}_data.json"
        File SumStatsFile = "~{BaseDir}/~{StudyId}/~{SumStatsFilename}"
    }

}

task vcf {
    input {
        String MountDir
        String VcfFileOutPath
        File SumStatsFile
        File RefGenomeFile
        File RefGenomeFileIdx
        File DbSnpVcfFile
        File DbSnpVcfFileIdx
        File ParamFile
        String StudyId
        Int? Cases
        Int? Controls
    }

    command <<<
        set -e

        docker run \
        --rm \
        -v ~{MountDir}:~{MountDir} \
        --cpus="1" \
        gwas2vcf:11726ff26b7305f93fb62e5d16233ca269a29dff \
        python /app/main.py \
        --data ~{SumStatsFile} \
        --id ~{StudyId} \
        --json ~{ParamFile} \
        --ref ~{RefGenomeFile} \
        --dbsnp ~{DbSnpVcfFile} \
        --out ~{VcfFileOutPath} \
        --alias alias.txt \
        ~{"--cohort_cases " + Cases} \
        ~{"--cohort_controls " + Controls}
    >>>

    output {
        File VcfFile = "~{VcfFileOutPath}"
        File VcfFileIdx = "~{VcfFileOutPath}.tbi"
    }

}

task clumping {
    input {
        String MountDir
        String ClumpFilePath
        File VcfFileIn
        File VcfFileInIdx
    }

    command <<<
        set -e

        docker run \
        --rm \
        -v ~{MountDir}:~{MountDir} \
        --cpus="1" \
        gwas_processing:7a81309ef7de99d862a1ca8ece783e46d7000558 \
        clump.py \
        --bcf ~{VcfFileIn} \
        --out ~{ClumpFilePath}
    >>>

    output {
        File ClumpFile = "~{ClumpFilePath}"
    }

}

task ldsc {
    input {
        String MountDir
        String LdscFilePath
        File VcfFileIn
        File VcfFileInIdx
    }

    command <<<
        set -e

        docker run \
        --rm \
        -v ~{MountDir}:~{MountDir} \
        --cpus="1" \
        gwas_processing:7a81309ef7de99d862a1ca8ece783e46d7000558 \
        ldsc.py \
        --bcf ~{VcfFileIn} \
        --out ~{LdscFilePath}
    >>>

    output {
        File LdscFile = "~{LdscFilePath}.log"
    }
    runtime {
        continueOnReturnCode: [0, 125]
    }

}

task report {
    input {
        String MountDir
        File VcfFileIn
        File VcfFileInIdx
        File RefData
        File RefDataIdx
        String StudyId
        File LdscFileIn
        File ClumpFileIn
        File MetaJsonIn
        String OutDirPath
    }

    command <<<
        set -e

        docker run \
        --rm \
        -v ~{MountDir}:~{MountDir} \
        --cpus="1" \
        mrbase-report-module:74213fc57b76fa0a22f81100135ccf96c6b92ae9 \
        Rscript render_gwas_report.R \
        --n_cores 1 \
        --refdata ~{RefData} \
        --output_dir ~{OutDirPath} \
        ~{VcfFileIn}

        # delete output folder
        rm -rf ~{OutDirPath}/intermediate
    >>>

    output {
        File ReportFile = "~{BaseDir}/~{StudyId}/~{StudyId}_report.html"
    }
}

task upload_report {
    input {
        String OCIObjectStoragePAR
        String BaseDir
        String StudyId
        File ReportFileIn
    }

    command <<<
        set -e
        source ~{OCIObjectStoragePAR}
        cd ~{BaseDir}/~{StudyId}
        curl -X PUT --data-binary '@~{StudyId}_report.html' ${OCI_PAR_URL_UPLOAD}~{StudyId}/~{StudyId}_report.html
    >>>

    output {
        String UploadDone = StudyId
    }
}
