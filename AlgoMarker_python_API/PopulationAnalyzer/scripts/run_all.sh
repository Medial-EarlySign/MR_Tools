#!/bin/bash
BASE_DIR=${0%/*}
${BASE_DIR}/configs/GastroFlag.40_90.py
${BASE_DIR}/configs/GastroFlag.45_75.py
${BASE_DIR}/configs/GastroFlag.50_75.py
${BASE_DIR}/configs/LGIFlag.40_90.py
${BASE_DIR}/configs/LGIFlag.45_75.py
${BASE_DIR}/configs/LGIFlag.50_75.py
${BASE_DIR}/configs/LungFlag.ES_THIN.py
${BASE_DIR}/configs/LungFlag.USPSTF_KPSC.py

${BASE_DIR}/unite_reports.py
