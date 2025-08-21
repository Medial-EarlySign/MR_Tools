#!/bin/bash
#sudo doxygen Doxyfile 2>&1 | egrep -v "External|QGDict|Please use a more specific name by including|Eigen::|VowpalWabbit|dmlc::|xgboost::|rabit::" > documentation_creation.log

cd ${0%/*}
sudo mkdir -p ~/html/tools
( cat Doxyfile ; echo "OUTPUT_DIRECTORY=/server/Linux/$USER/html/tools" ) | sudo doxygen - 2>&1 | egrep -v "External|QGDict|Please use a more specific name by including|Eigen::|VowpalWabbit|dmlc::|xgboost::|rabit::" > documentation_creation_user.log
