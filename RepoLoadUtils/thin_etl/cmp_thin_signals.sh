#!/bin/bash

ls -1 /server/Temp/Ido/ahd/Common > /server/Temp/Thin_2017_Loading/outputs/all_signals.txt

cat /server/Temp/Thin_2017_Loading/outputs/all_signals.txt | paste.pl - 0 /server/UsersData/alon/MR/Tools/RepoLoadUtils/thin_etl/config_2017/thin_signals_to_united.txt 0 1 | subtract.pl /server/Temp/Thin_2017_Loading/outputs/all_signals.txt 0 - 0
