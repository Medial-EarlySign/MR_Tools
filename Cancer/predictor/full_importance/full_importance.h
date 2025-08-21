#include "CommonLib/common_header.h"
#include "condor_runner/condor_runner/condor_runner.h"
#include "data_handler/data_handler/data_handler.h"
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

#define NFTRS NCBC
#define SIG_DIFF 2.0

/* Structures */

struct compare_abs {
    bool operator()(const pair<int, double>& left, const pair<int, double>& right) {
                return (fabs(left.second) > fabs(right.second)) ;
    }
} ;

class measure {
public:
	string age_range ;
	string time_window ;
	string measure_name ;
	double random_value ;
} ;

/* Functions */
int read_run_params(int argc,char **argv, po::variables_map& vm) ;

void get_corrs(double *in, int nrows, int ncols, int *ftrs, double corrs[NFTRS][NFTRS]) ;
void get_combinations(double corrs[NFTRS][NFTRS],vector<int> combinations[NFTRS][NFTRS][2], char names[NFTRS][NFTRS][MAX_STRING_LEN]) ;
int get_predictors(vector<vector<int> >& combinations_list, string& path, string& prefix, char *smethod, int nfold, char *work_dir, int seed, string& features_template, string& learn_config) ;
int get_predictions(vector<vector<int> >& combinations_list, string& path, string& prefix, char *smethod, int nfold, char *work_dir, int seed, string& features_template, string& predict_config) ;
int get_performances(vector<vector<int> >& combinations_list, char *work_dir, int nfold, string& analyze_config) ;
void read_measures(char *measures_file, vector<measure>& measures) ;
void get_measure_values(vector<vector<int> >& combinations_list,char *work_dir, vector<measure>& measures, double *measure_values) ;
void summarize_measure_values(vector<int> combinations[NFTRS][NFTRS][2], char names[NFTRS][NFTRS][MAX_STRING_LEN], map<vector<int>,int>& combinations_hash, vector<measure>& measures, double *measure_values, char *output_file) ;
void set_features (vector<int>& list, string& feature_template, string& features) ;
int start_here(char *stage) ;
int read_runner_params(string& file_name, map<string,string>& params) ;