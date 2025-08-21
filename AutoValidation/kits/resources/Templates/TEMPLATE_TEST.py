#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['REPOSITORY_PATH', 'WORK_DIR'] # Required parameters
DEPENDS=[] # List of dependent tests
# End Edit

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources')) 
from lib.PY_Helper import *

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below: