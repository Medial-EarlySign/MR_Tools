#!/bin/sh

SERVER_APP=$MR_ROOT/Tools/AllTools/Linux/Release/SimpleHttpServer
JAVASCRIPT_DIR=$MR_ROOT/Libs/Internal/MedPlotly/JavaScript

ADDRESS=192.168.1.224

BASIC_CONFIG=$MR_ROOT/Libs/Internal/MedPlotly/MedPlotly/BasicConfig.txt

# SimpleHttpServer --rep /nas1/Work/Users/Avi/SLU/repository3/slu.repository --plotly_config /nas1/UsersData/avi/MR/Libs/Internal/MedPlotly/MedPlotly/SLUConfig.txt --address 192.168.1.224 --port 8193
SLU_REP=/nas1/Work/Users/Avi/SLU/repository3/slu.repository
SLU_CONFIG=$MR_ROOT/Libs/Internal/MedPlotly/MedPlotly/SLUConfig.txt
SLU_PORT=8193

#THIN_REP=/home/Repositories/THIN/thin_jun2017/thin.repository
THIN_REP=/home/Repositories/THIN/thin_2018/thin.repository
THIN_CONFIG=$BASIC_CONFIG
THIN_PORT=8194

MHS_REP=/home/Repositories/MHS/build_Feb2016_Mode_3/maccabi.repository
MHS_CONFIG=$MR_ROOT/Libs/Internal/MedPlotly/MedPlotly/MHSConfig.txt
MHS_PORT=8195

KP_REP=/nas1/Work/CancerData/Repositories/KP/kp.repository
KP_CONFIG=$MR_ROOT/Libs/Internal/MedPlotly/MedPlotly/KPConfig.txt
KP_PORT=8196

#Command Line: Linux/Release/SimpleHttpServer --rep /nas1/Work/CancerData/Repositories/Rambam/rambam_aug2018/rambam.repository --plotly_config /nas1/UsersData/avi/MR/Libs/Internal/MedPlotly/MedPlotly/RambamConfig.txt --port 8193

RAMBAM_REP=/nas1/Work/CancerData/Repositories/Rambam/rambam_nov2018_fixed/rambam.repository
RAMBAM_CONFIG=$MR_ROOT/Libs/Internal/MedPlotly/MedPlotly/RambamConfig.txt
RAMBAM_PORT=8198

MIMIC3_REP=/nas1/Work/CancerData/Repositories/MIMIC/Mimic3/mimic3.repository
MIMIC3_CONFIG=$MR_ROOT/Libs/Internal/MedPlotly/MedPlotly/MimicConfig.txt
MIMIC3_PORT=8199

KPNW_REP=/nas1/Work/CancerData/Repositories/KPNW/kpnw_jun19/kpnw.repository
KPNW_CONFIG=$MR_ROOT/Libs/Internal/MedPlotly/MedPlotly/KPNWConfig.txt
KPNW_PORT=8200
KPNW_DEFAULT=formKPNW.html

KPNW_DM_REP=/nas1/Work/CancerData/Repositories/KPNW/kpnw_diabetes/kpnw.repository
KPNW_DM_CONFIG=$MR_ROOT/Libs/Internal/MedPlotly/MedPlotly/KPNWConfig_DM.txt
KPNW_DM_PORT=8201


echo "================================="
echo "Bringing up all http data viewers"
echo "================================="

while true
do

# thin
THIN_S=`ps -ef | grep SimpleHttpServer | grep "thin.repository" | grep -v grep`
if [ -z "$THIN_S" ] 
then
	echo "NO THIN viewer up -> bringing it up"
	$SERVER_APP --rep $THIN_REP --server_dir $JAVASCRIPT_DIR --plotly_config $THIN_CONFIG --address $ADDRESS --port $THIN_PORT &
fi

# MHS
MHS_S=`ps -ef | grep SimpleHttpServer | grep "maccabi.repository" | grep -v grep`
if [ -z "$MHS_S" ] 
then
	echo "NO Maccabi viewer up -> bringing it up"
	$SERVER_APP --rep $MHS_REP --server_dir $JAVASCRIPT_DIR --plotly_config $MHS_CONFIG --address $ADDRESS --port $MHS_PORT --index_page formMHS.html &
fi

# KPNW
KPNW_S=`ps -ef | grep SimpleHttpServer | grep "kpnw_jun19" | grep -v grep`
if [ -z "$KPNW_S" ]
then
        echo "NO KPNW viewer up -> bringing it up"
        $SERVER_APP --rep $KPNW_REP --server_dir $JAVASCRIPT_DIR --plotly_config $KPNW_CONFIG --address $ADDRESS --port $KPNW_PORT --index_page $KPNW_DEFAULT  &
fi

# KPNW
KPNW_DM_S=`ps -ef | grep SimpleHttpServer | grep "kpnw_diabetes" | grep -v grep`
if [ -z "$KPNW_DM_S" ]
then
        echo "NO KPNW viewer up -> bringing it up"
        $SERVER_APP --rep $KPNW_DM_REP --server_dir $JAVASCRIPT_DIR --plotly_config $KPNW_DM_CONFIG --address $ADDRESS --port $KPNW_DM_PORT &
fi


# kp
KP_S=`ps -ef | grep SimpleHttpServer | grep "kp.repository" | grep -v grep`
if [ -z "$KP_S" ] 
then
	echo "NO KP viewer up -> bringing it up"
	$SERVER_APP --rep $KP_REP --server_dir $JAVASCRIPT_DIR --plotly_config $KP_CONFIG --address $ADDRESS --port $KP_PORT &
fi

# rambam
RAMBAM_S=`ps -ef | grep SimpleHttpServer | grep "rambam.repository" | grep -v grep`
if [ -z "$RAMBAM_S" ] 
then
	echo "NO RAMBAM viewer up -> bringing it up"
	$SERVER_APP --rep $RAMBAM_REP --server_dir $JAVASCRIPT_DIR --plotly_config $RAMBAM_CONFIG --address $ADDRESS --port $RAMBAM_PORT --index_page formRambam.html &
fi

# mimic3
MIMIC3_S=`ps -ef | grep SimpleHttpServer | grep "mimic3.repository" | grep -v grep`
if [ -z "$MIMIC3_S" ] 
then
	echo "NO MIMIC3 viewer up -> bringing it up"
	$SERVER_APP --rep $MIMIC3_REP --server_dir $JAVASCRIPT_DIR --plotly_config $MIMIC3_CONFIG --address $ADDRESS --port $MIMIC3_PORT --index_page formMimic.html &
fi


# slu
SLU_S=`ps -ef | grep SimpleHttpServer | grep "slu.repository" | grep -v grep`
if [ -z "$SLU_S" ]
then
        echo "NO SLU viewer up -> bringing it up"
        $SERVER_APP --rep $SLU_REP --server_dir $JAVASCRIPT_DIR --plotly_config $SLU_CONFIG --address $ADDRESS --port $SLU_PORT --index_page formSLU.html &
fi


#echo "1"
sleep 1
done
