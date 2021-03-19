workflow qc {

    String StudyId
    Int? Cases
    Int? Controls
    String MountDir = "/data"
    String BaseDir = "/data/igd"
    File RefGenomeFile="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.fasta"
    File RefGenomeFileIdx="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.fasta.fai"
    File RefGenomeFileDict="/data/reference_genomes/released/2019-08-30/data/2.8/b37/human_g1k_v37.dict"
    File DbSnpVcfFile="/data/dbsnp/released/2019-09-11/data/dbsnp.v153.b37.vcf.gz"
    File DbSnpVcfFileIdx="/data/dbsnp/released/2019-09-11/data/dbsnp.v153.b37.vcf.gz.tbi"
    File AfVcfFile="/data/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.gz"
    File AfVcfFileIdx="/data/1kg/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.vcf.gz.tbi"
    File RefData = "/data/ref/1kg_v3_nomult.bcf"
    File RefDataIdx = "/data/ref/1kg_v3_nomult.bcf.csi"

    call vcf {
        input:
            MountDir=MountDir,
            VcfFileOutPath=BaseDir + "/" + StudyId + "/" + StudyId + ".vcf.gz",
            SumStatsFile=BaseDir + "/" + StudyId + "/upload.txt.gz",
            RefGenomeFile=RefGenomeFile,
            RefGenomeFileIdx=RefGenomeFileIdx,
            ParamFile=BaseDir + "/" + StudyId + "/" + StudyId + "_data.json",
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

}

task vcf {

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

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas2vcf:11726ff26b7305f93fb62e5d16233ca269a29dff \
        python /app/main.py \
        --data ${SumStatsFile} \
        --id ${StudyId} \
        --json ${ParamFile} \
        --ref ${RefGenomeFile} \
        --dbsnp ${DbSnpVcfFile} \
        --out ${VcfFileOutPath} \
        --alias alias.txt \
        ${"--cohort_cases " + Cases} \
        ${"--cohort_controls " + Controls}
    >>>

    output {
        File VcfFile = "${VcfFileOutPath}"
        File VcfFileIdx = "${VcfFileOutPath}.tbi"
    }

}

task clumping {

    String MountDir
    String ClumpFilePath
    File VcfFileIn
    File VcfFileInIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_processing:7a81309ef7de99d862a1ca8ece783e46d7000558 \
        clump.py \
        --bcf ${VcfFileIn} \
        --out ${ClumpFilePath}
    >>>

    output {
        File ClumpFile = "${ClumpFilePath}"
    }

}

task ldsc {

    String MountDir
    String LdscFilePath
    File VcfFileIn
    File VcfFileInIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        gwas_processing:7a81309ef7de99d862a1ca8ece783e46d7000558 \
        ldsc.py \
        --bcf ${VcfFileIn} \
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
    File VcfFileIn
    File VcfFileInIdx
    File RefData
    File RefDataIdx
    String StudyId
    File LdscFileIn
    File ClumpFileIn
    File MetaJsonIn
    String OutDirPath

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        mrbase-report-module:21ac8afc52b29b6ce5911662e834002ade1d4ea0 \
        Rscript render_gwas_report.R \
        --n_cores 1 \
        --refdata ${RefData} \
        --output_dir ${OutDirPath} \
        ${VcfFileIn}

        # delete output folder
        rm -rf ${OutDirPath}/intermediate
    >>>

}
