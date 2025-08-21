#!/bin/bash
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
CURR_PT=${2}
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...