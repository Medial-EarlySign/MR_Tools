#!/bin/bash
$MR_ROOT/Projects/Shared/SignalsDependencies/Linux/Release/SignalsDependencies --global_config $MR_ROOT/Projects/Shared/SignalsDependencies/SignalsDependencies/Examples/configs/linux_procedures.cfg
#we can override some parameters in the config file in cmd. for adding "--filter_min_ppv 0.05" to the above command