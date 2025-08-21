#!/bin/bash
#cat /server/Temp/Thin_2017_Loading/outputs/missing_2017.txt | awk '{print "cp /server/Data/THIN1601/THINDB1601/ahd."$1" /server/Data/THIN1701/THINDB1701"}' | xargs -L1 sudo 
cat /server/Temp/Thin_2017_Loading/outputs/missing_2017.txt | awk '{print "rm -f /server/Data/THIN1701/THINDB1701/ahd."$1}' | xargs -L1 sudo
