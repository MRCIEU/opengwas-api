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

    # TODO update with new gwas2vcf + args
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
            OutputDir=BaseDir + "/" + StudyId
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
        gwas2vcf:66fb44438fb5b42dc88830e5f7497e26231684da \
        python /app/main.py \
        --data ${SumStatsFile} \
        --id ${StudyId} \
        --json ${ParamFile} \
        --ref ${RefGenomeFile} \
        --out ${VcfFileOutPath} \
        --rm_chr_prefix \
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
        gwas_processing:305e3e5133a19b87ab0031488e01588f76ee1be0 \
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
        gwas_processing:305e3e5133a19b87ab0031488e01588f76ee1be0 \
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
    String OutputDir
    File VcfFileIn
    File VcfFileInIdx
    File RefData
    File RefDataIdx

    command <<<
        set -e

        docker run \
        --rm \
        -v ${MountDir}:${MountDir} \
        --cpus="1" \
        mrbase-report-module:0675b0846bc3be6997dd77c6cd194d2311f7090f \
        Rscript render_gwas_report.R \
        ${VcfFileIn} \
        --output_dir ${OutputDir} \
        --n_cores 1
    >>>

    output {
        File ReportFile = "${OutputDir}/report.html"
        File MetaJsonFile = "${OutputDir}/metadata.json"
        File QcMetricsJsonFile = "${OutputDir}/qc_metrics.json"
    }

}
