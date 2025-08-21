#include "CommonLib/common_header.h"
#include <boost/program_options.hpp>
namespace po = boost::program_options;

using namespace std;

typedef programParamStrType predictParamStrType;


// Function headers
int getCommandParams(int argc,char **argv,predictParamStrType *paramStruct);
void openFiles(predictParamStrType *paramStruct);
void params2Stderr(predictParamStrType& ps) ;
void checkParams(predictParamStrType& ps) ;

int read_params(FILE *fp, int mftrs, int *nftrs, double *means_for_completion, double *sdvs_for_completion, cleaner& cln, double **bin_bnds, double **eqsized_bin_bnds, int *nbins) ;
