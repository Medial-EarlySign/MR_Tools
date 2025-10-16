#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR SILENCE_RUN_OUTPUT_FILES_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

if [ ! "${SILENCE_RUN_OUTPUT_FILES_PATH}" = "GENERATE" ]; then
	mkdir -p ${WORK_DIR}/outputs
	cat ${SILENCE_RUN_OUTPUT_FILES_PATH} | awk -F"\t" 'NR>1 {if ($NF=="") {$NF="<OK>"} c[$NF]+=1; n+=1} END { for (m in c) {print m "\t" c[m] "\t" int(c[m]/n*10000)/100.0 }}' | sort -S50% -t $'\t' -g -r -k2 > ${WORK_DIR}/outputs/messages.tsv

	echo "Please refer to ${WORK_DIR}/outputs/messages.tsv"
else
	echo "No output files from AlgoMarker - skips"
fi
