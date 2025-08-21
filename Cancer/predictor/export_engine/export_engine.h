#include "CommonLib/common_header.h"
#include <boost/program_options.hpp>
#include "QRF/QRF/QRF.h"

namespace po = boost::program_options;
using namespace std;

typedef struct{// This structures hold the interpreted params of the command line
	string methodString;
	map <string, int> methodMap ;
	string internalMethod ;
	string setUpFileName ;
	FILE *setUpFile ;
	string EngineDirectory ;
	bool combined ;
	string engineVersion;
} exportParamStrType ;


#define N_FILE_NAMES 3
#define N_FILE_SUFFICES 3
#define MAX_BUF_SIZE 1024
#define MAX_N_SPECIFC_FILE_NAMES 2

class params {
public:
	double min_orig_data;
	double min, max;
	double avg, std;
} ;

char common_file_names[N_FILE_NAMES][MAX_STRING_LEN] = {"Features","Extra","Shift"} ;
char common_file_suffices[N_FILE_SUFFICES][MAX_STRING_LEN] = {"Completion","Outliers","Model"} ;
char specific_file_names[][MAX_N_SPECIFC_FILE_NAMES][MAX_STRING_LEN] = {{},{},{},{},{},{},{},{},{},{},{"menIncidence","womenIncidence"},{}} ;
int specific_nfiles[] = {0,0,0,0,0,0,0,0,0,0,2,0} ;

// Function headers
int getCommandParams(int argc,char **argv,exportParamStrType *paramStruct);
void params2Stderr(exportParamStrType& ps) ;
void openFiles(exportParamStrType *paramStruct);
int read_instructions(exportParamStrType& ps, map<string,string>& file_names) ;
int read_features(string& file_name, map<string, pair<int,int> >& features) ;
void copy(const string& from, const string& dir, const char * to) ;
void unzip_file(const string& from, const string& dir, const char * to) ;
int create_params_file(map<string,string>& file_names,  map<string, pair<int,int> >& features, bool combined, string& dir) ;
int read_params(string& fname, map<int,params>& parameters) ;
int create_model_files(map<string,string>& file_names, const string& gender, string& dir, string& method, int index, string& internal) ;
int create_rfgbm_model_files(unsigned char *model, const string& gender, string& dir) ;
int create_double_matched_model_files(unsigned char *model, const string& gender, string& dir, map<string,string>& file_names, string& internal) ;
int get_incidence(string &in, string& dir, const string& out) ;
int write_blob(char *out_file_name, unsigned char *model, int from, int size) ;
int write_engine_version(string& version, string &dir);
int get_and_write_rf(unsigned char *model, char *out_file_name, int *size);
int get_and_write_qrf(unsigned char *model, char *out_file_name, int *size);