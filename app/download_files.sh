#!/bin/bash

base_url="http://10.0.0.40:8080/ld_files"
target_dir="/app/ld_files"

mkdir -p "$target_dir"

files=(
    "data_maf0.01_rs_ref.tar.gz"
    "AFR.tar.gz"
    "AMR.tar.gz"
    "EAS.tar.gz"
    "EUR.tar.gz"
    "SAS.tar.gz"
    "afl2.tar.gz"
)

for f in "${files[@]}"; do
  wget -nv -P "$target_dir" "$base_url/$f"
  tar -xzvf "$target_dir/$f" -C "$target_dir"
  rm -f "$target_dir/$f"
done
