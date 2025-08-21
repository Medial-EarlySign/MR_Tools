#!/bin/bash

base_folder=`realpath ${0%/*}/..`
block_proc=40815

mkdir -p ${base_folder}/repository_data_final
is_run=`ps -e | grep ${block_proc} | wc -l`
echo "Start running. blocking proces is ${is_run} running"

while [ $is_run -ne "0" ]; do
	sleep 3
	#echo "still running"
	is_run=`ps -e | grep ${block_proc} | wc -l`   
done

echo "start copy on $base_folder"
#ssh -t node-01 "sudo rsync -u -h --progress ${base_folder}/repository_data_final/* /home/Repositories/THIN/thin_jun2017" & 
ssh -t node-02 "sudo rsync -u -h --progress ${base_folder}/repository_data_final/* /home/Repositories/THIN/thin_jun2017" &
ssh -t node-03 "sudo rsync -u -h --progress ${base_folder}/repository_data_final/* /home/Repositories/THIN/thin_jun2017" &
ssh -t node-04 "sudo rsync -u -h --progress ${base_folder}/repository_data_final/* /home/Repositories/THIN/thin_jun2017" &
ssh -t node-01 "sudo rsync -u -h --progress ${base_folder}/repository_data_final/* /home/Repositories/THIN/thin_jun2017"
#sudo cp ${base_folder}/repository_data_final/thin_rep_TRAIN.* /home/Repositories/THIN/thin_jun2017
#sudo cp ${base_folder}/repository_data_final/thin_rep__pids__* /home/Repositories/THIN/thin_jun2017
#echo "finished!" 
echo "All Done."
