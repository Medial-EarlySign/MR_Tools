#!/bin/bash
cat all_config_file-list.txt | awk ' {print " /server/UsersData/alon/MR/Tools/RepoLoadUtils/thin_etl/"$1" /server/UsersData/alon/MR/Tools/RepoLoadUtils/thin_etl/config_2017"}'  | xargs -L1 cp
