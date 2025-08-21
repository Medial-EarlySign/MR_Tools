#!/bin/bash

base_rep=/home/Repositories/THIN/thin_mar2017
new_rep=${0%/*}/..

#creating files
grep SIGNAL ${new_rep}/rep_configs/thin.signals | awk '{print $2}' > ${new_rep}/outputs/thin_new.signals
grep SIGNAL ${base_rep}/thin.signals | awk '{print $2}' > ${new_rep}/outputs/thin_old.signals
ls -l --block-size 1 ${base_rep} | awk '{print $9"\t"$5}' > ${new_rep}/outputs/old_sizes.txt
ls -l --block-size 1 ${new_rep}/repository_data_final/ | awk '{print $9"\t"$5}' > ${new_rep}/outputs/new_sizes.txt

#running tests
echo "check missing signals in new repository compared to configuarion of repository thin.signals"
ls --block-size 1 -l ${new_rep}/repository_data_final/*.data | awk '{print $9"\t"$5}' | awk '{gsub("_percent_", "%",$1); gsub(/.+thin_rep_/, "", $1); print $1}' | egrep -o "^[^\.]+" | subtract.pl ${new_rep}/outputs/thin_new.signals 0 - 0
echo "check singals that are smaller than old repository"
paste.pl ${new_rep}/outputs/old_sizes.txt 0 ${new_rep}/outputs/new_sizes.txt 0 1 | awk '$3 < $2 && substr($1, length($1)-4)==".data"' 
echo "check for missing signals in new repository compared to old one"
subtract.pl ${new_rep}/outputs/old_sizes.txt 0 ${new_rep}/outputs/new_sizes.txt 0
