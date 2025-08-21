#!/bin/bash

#NOT NEEDED Anymore - run just laod_all.py - it will be done inside

work_dir=/server/Temp/Ido/ahd
signal_regex=38DE[\.]
signal_target_name=CHADS2

#signal_regex=38DE[0]
#signal_target_name=CHADS2_VASC

pushd ${thin_etl}

python -c "from signal_full_api import *;loadSpecificSignal('${signal_regex}', 1)"
#cat $work_dir/NonNumeric/signals_38DE\[.0\].txt | awk '{print $1"\t"$3"\t"$6"\tFromCol2\t'${signal_target_name}'_NunNumeric"}' > $work_dir/Common/${signal_target_name}_NunNumeric
#python -c "from signal_full_api import *;addMissingSignals()"
#python -c "from signal_full_api import *;commitSignal('{signal_regex}','${signal_target_name}')"
#python -c "from signal_full_api import *;unite_signals('${signal_target_name}')"

#Configure Signal units in server.py

#python -c "from signal_full_api import *;fixSignal('${signal_target_name}')"

popd
