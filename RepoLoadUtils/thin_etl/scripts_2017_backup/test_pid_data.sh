#!/bin/bash

head -n 10000 /server/Data/THIN1701/THINDB1701/medical.a6641 | grep "^0001" | awk 'BEGIN {FS=""} {if ( ($30=="R" || $30=="S") && ($23==3 || $23==4)) {print $0} }'

head -n 10000 /server/Data/THIN1701/THINDB1701/ahd.a6641 | grep "^0001" | awk 'BEGIN {FS=""} { if ($23=="Y" && ($102==3 || $102==4) && $36==" ") {print $0} } ' | wc -l
