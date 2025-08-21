#!/bin/bash

ls -1 SpecialSignals | awk '{print " -n 1 /server/Temp/Thin_2017_Loading/SpecialSignals/"$1}'  | xargs -L1 head | awk '{print $2}' > outputs/special_signal_names.txt
