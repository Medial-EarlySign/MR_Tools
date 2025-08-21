#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

echo "Loading Repository"

#First - let's load Repository if not loaded yet:
mkdir -p ${WORK_DIR}
mkdir -p ${WORK_DIR}/rep
#mkdir -p ${WORK_DIR}/rep/data
mkdir -p ${WORK_DIR}/tmp

REP_P=${REPOSITORY_PATH%/*}
REP_NAME=$(echo ${REPOSITORY_PATH##*/} | egrep "\.repository$" | awk '{gsub(".repository","", $1);print $1}')

if [ ! -f ${WORK_DIR}/rep/loading_done ] || [ $OVERRIDE -gt 0 ]; then
    ln -f -s ${REP_P}/dicts ${WORK_DIR}/rep/dicts
	
	if [ -d "${REP_P}/data" ]; then
		ln -f -s ${REP_P}/data ${WORK_DIR}/rep/data
		ln -f -s ${REPOSITORY_PATH} ${WORK_DIR}/rep/test.repository
	else #no data dir - old repo structure:
		ln -f -s ${REP_P} ${WORK_DIR}/rep/data
		cp ${REPOSITORY_PATH} ${WORK_DIR}/rep/test.repository
		#Edit and add prefix with "data/"
		sed -i 's|^PREFIX\t|PREFIX\tdata/|g' ${WORK_DIR}/rep/test.repository
	fi
    
    
    ln -f -s ${REP_P}/${REP_NAME}.signals ${WORK_DIR}/rep/
    ln -f -s ${REP_P}/${REP_NAME}.signals ${WORK_DIR}/rep/test.signals
      
	echo "Loaded done" > ${WORK_DIR}/rep/loading_done
fi


