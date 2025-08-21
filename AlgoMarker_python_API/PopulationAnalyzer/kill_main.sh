#!/bin/bash
MAIN_P=$(ps -ef | grep "ui.py" | grep -v "grep" | awk '{print $2}')
ps -ef | grep "python" | grep -v "grep" | awk -v ppid=${MAIN_P} '$3==ppid' | awk '{print $2}'| xargs -L1 kill -KILL
kill -KILL ${MAIN_P}

lsof -i tcp:3764 | awk '$2!="PID"{print $2}' | sort | uniq | xargs -L1 kill -KILL