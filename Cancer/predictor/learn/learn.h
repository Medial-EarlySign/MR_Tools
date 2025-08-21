#include "CommonLib/common_header.h"
#include <boost/program_options.hpp>

#include "stdlib.h"
#include "stdio.h"
#include "string.h"
#include "math.h"
#include <assert.h>
#include <time.h>

#include <map>
#include <vector>
#include <string>
#include <algorithm>
#include <fstream>
#include <set>
using namespace std;
namespace po = boost::program_options;

typedef programParamStrType learnParamStrType;

// Function headers
int getCommandParams(int argc,char **argv,learnParamStrType *paramStruct);
void openFiles(learnParamStrType *paramStruct);
void params2Stderr(learnParamStrType& paramStruct);
void checkParams(learnParamStrType& paramStruct) ;
