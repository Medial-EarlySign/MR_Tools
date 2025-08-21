#pragma once

// Header File for Full Cross Validation

#include "CommonLib/common_header.h"
#include <boost/program_options.hpp>

namespace po = boost::program_options;

typedef programParamStrType fullCVParamStrType;

// I/O handling functions headers
int getCommandParams(int argc,char **argv,fullCVParamStrType *paramStruct);
void openFiles(fullCVParamStrType *paramStruct);
void params2Stderr(fullCVParamStrType& paramStruct);
void checkParams(fullCVParamStrType& ps) ;
	