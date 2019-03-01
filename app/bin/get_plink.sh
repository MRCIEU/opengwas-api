#!/bin/bash

wget http://s3.amazonaws.com/plink1-assets/plink_linux_x86_64_20190215.zip
unzip plink_linux_x86_64_20190215.zip
mv plink plink_Linux
rm LICENSE plink_*zip prettify* toy.*

wget http://s3.amazonaws.com/plink1-assets/plink_mac_20190215.zip
unzip plink_mac_20190215.zip
mv plink plink_Darwin
rm LICENSE plink_*zip prettify* toy.*

wget http://s3.amazonaws.com/plink1-assets/plink_win64_20190215.zip
unzip plink_win64_20190215.zip
mv plink.exe plink_Windows
rm LICENSE plink_*zip prettify* toy.*
