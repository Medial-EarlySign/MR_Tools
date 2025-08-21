#ifndef _ANALYZE_SCORES_H_
#define _ANALYZE_SCORES_H_

#define BUFFER_SIZE    4096
#define MAX_STRING_LEN 1024
#define REGISTRY_NFIELDS  8 
#define MHS_REGISTRY_NFIELDS 19
#define MHS_REGISTRY_CANCER_FIELD 14 
#define MHS_REGISTRY_DATE_FIELD 5
#define MHS_REGISTRY_ID_FIELD 0

#define EXTRA_PARAMS_MAX_FIELDS 3
#define DEF_CANCER_DIR 2

#define DATA_FILE_NAME "Results"

#ifdef _WIN32
#define R_EXEC "\\\\nas1\\Work\\Applications\\R\\R-latest\\bin\\x64\\R CMD BATCH --silent --no-timing"
#else
#define R_EXEC "R CMD BATCH --silent --no-timing"
#endif

#define N_AGE_SEGS 10
#define MAX_STATUS_YEAR 2006

#define AUTOSIM_NGAPS 16
#define AUTOSIM_GAP 90

#define CUT_NGAPS 8
#define CUT_GAP 90

#define NRANDOM 10000000
#define MAX_YEAR 10000

#define DEF_FIRST_DATE 20010101
#define DEF_PERIOD 365

#define COX_MATRIX_NAME "COX_Matrix"
#define COX_SCRIPT_FILE "COX_Script.R" 
#define COX_STDOUT_FILE "COX_Script.out"

#define OXFORD_NFIELDS 8

#include "stdlib.h"
#include "stdio.h"
#include "math.h"
#include <assert.h>
#include <time.h>

#include <map>
#include <vector>
#include <string>
#include <algorithm>
#include <fstream>
#include <set>
#include <thread>
#include <random>
#include "medial_utilities/medial_utilities/globalRNG.h"
#include "medial_utilities/medial_utilities/medial_utilities.h"
#include <boost/random/mersenne_twister.hpp>
#include <boost/random/uniform_int_distribution.hpp>
#include <boost/program_options.hpp>

using namespace std ;
namespace po = boost::program_options;

/*          Status class				*/
class status {
public:
	int days ;
	int stat ;
	int reason ;
} ;

/*			Scores class				*/
class score_entry {
public:
	string id;
	int date, days  ;
	double score ;
	int bin ;
	int eqsize_bin ;
	int year ;
} ;

/*			Statistics class			*/
class all_stats {
public:
	int n,p ;
	vector<int> tp ;
	vector<int> fp ;
	vector<double> scores ;

	double corr ;
	double theta,q1,q2 ;
} ;

/*			Thresholds					*/
typedef pair<pair<int,int>,pair<int,int> > cross_section ;
class target_bound {
public:
	double score ;
	double spec ;
	double sens ;
} ;

class target_bound_autosim {
public:
	double score ;
	double spec ;
	double sens ;
	double earlysens1 ;
	double earlysens2 ;
	double earlysens3 ;
} ;



/*			AutoSim Score				*/
class autosim_score {
public:
	double score ;
	int gap ; // how much time before the cancer registry date, given in 90 days units (e.g. 2 = the score was given between 30 and 60 days before the cancer registration date)
	int id ; // patient id
} ;

/*			Periodic AutoSim Score		*/
class periodic_autosim_score {
public:
	double score ;
	int gap ;
	int id ;
	int iperiod ;
} ;

/*          A reservoir of random numbers for reducing randomization       */
class quick_random {
public:
	quick_random() : vec(NRANDOM), irand(0), vec_size(NRANDOM) {
		for (int i=0; i<vec_size; i++) vec[i] = (0.0 + globalRNG::rand30())/(1 << 30) ;
	}

	quick_random(int _vec_size) : vec(_vec_size), irand(0), vec_size(_vec_size) {
		for (int i=0; i<vec_size; i++) vec[i] = (0.0 + globalRNG::rand30())/(1 << 30) ;
	}

	double random(); 

private:
	vector<double> vec;
	int irand;
	int vec_size ;

	void shuffle();
} ;

typedef map<cross_section,vector<target_bound> > thresholds ;
typedef map<pair<int,int>,vector<target_bound_autosim> > thresholds_autosim ;
typedef vector<pair<int,int> > periods ;

// All input data
class input_data {
public:
	map<string, periods> remove_list ;
	map<string, periods> include_list ;
	map<string,vector<score_entry> > all_scores ;
	map<string,int> cancer_directions ;
	map<int,double> incidence_rate ;
	map<string,vector<pair<int,int> > > registry ;
	map<string, int> byears ;
	map<string, status> censor ;
	
	string run_id ;

	vector<pair<int,int> > time_windows ;
	vector<pair<int,int> > age_ranges ;
	int last_date,first_date ;
	int age_seg_num ;
	int max_status_year ;

	thresholds bnds ;
	thresholds_autosim bnds_autosim ;
} ;

// Flags for running
class running_flags {
public:
	bool all_fpr;
	bool raw_only;
	bool auto_sim_raw;
	bool inc_from_pred;
	bool mhs_reg_format;
	bool simple_reg_format; // pid,event_date
	bool read_reg_from_scores;
	bool use_last ;
} ;

// Output files
class out_fps {
public:
	FILE *raw_fout ;
	FILE *sim_raw_fout ;
	FILE *info_fout ;
	FILE *fout;	
	FILE *autosim_fout ;
	FILE *periodic_autosim_fout ;	
	FILE *periodic_cuts_fout ;
} ;

// Working arrays
class work_space {
public:
	int *days, *dates, *years ;
	double *scores ; 
	int *id_starts, *id_nums, *types, *ages;
	int *gaps; // gaps in days between score and the cancer registration date
	int *time_to_cancer ;

	vector<string> idstrs ;
} ;


/* Access working points */
int get_fpr_points_num(bool all_fpr) ;
double *get_fpr_points(bool all_fpr) ;
int get_sens_points_num() ;
double *get_sens_points() ;
int get_score_points_num();
double *get_score_points();
int get_sim_fpr_points_num() ;
double *get_sim_fpr_points() ;

/*			Function Declarations		*/
// Utilities
int check_nbin_types_value(const int val);
void sample_ids(int *sampled_ids, int nids, quick_random& qrand) ;
template<typename T> void shuffle_vector(vector<T>& input, quick_random& qrand);
int allocate_data(input_data& indata, work_space& work) ;

// Reading
int read_all_input_data(po::variables_map& vm, bool inc_from_pred, bool mhs_reg_format, bool simple_reg_format, bool read_reg_from_scores, input_data& indata) ;
int read_all_input_data_for_oxford(po::variables_map& vm, input_data& indata);

int read_scores(const char *file_name, map<string, vector<score_entry> >& scores, string& run_id, int nbin_types, map<string, periods>& include_list, map<string, periods>& remove_list,
	bool read_reg_from_scores, map<string, vector<pair<int, int> > >& registry, map<string, status>& censor, string pred_col);

int in_list(map<string,periods>& remove_list, string id, int date) ;
int read_cancer_directions(const char *file_name, map<string,int>& cancer_directions) ;
int read_cancer_registry(const char *file_name, map<string,int>& cancer_directions , map<string,vector<pair<int,int> > >& registry ) ;
int read_mhs_cancer_registry(const char *file_name, map<string,int>& cancer_directions , map<string,vector<pair<int,int> > >& registry ) ;

int read_extra_params(const char *file_name, vector<pair<int,int> >& time_windows, vector<pair<int, int> >& age_ranges, int *first_date, int *last_date, int *age_seg_num, int *max_status_year) ;
int read_extra_params(const char *file_name, vector<pair<int,int> >& initialization_dates, vector<pair<int,int> >& age_ranges, int *last_date, int *max_status_year);
int read_extra_params_for_oxford(const char *file_name, vector<pair<int, int> >& time_windows, vector<pair<int, int> >& age_ranges, int *age_seg_num);

int read_bnds(const char *file_name, thresholds& bnds , thresholds_autosim& bnds_autosim ) ;
int read_byears(const char *byear_file, map<string,int>& byears) ;
int read_censor(const char *file_name, map<string,status>& censor) ;
int read_remove(const char *file_name, map<string,int>& censor) ;
int read_list(const char *file_name, map<string,periods>& list) ;
int read_list_from_scores(const char *file_name, int nbin_types, map<string,periods>& list, bool read_reg_from_scores, map<string, vector<pair<int, int> > >& registry, map<string, status>& censor, string pred_col) ;
int read_probs(const char *file_name, map<int,double>& incidence_rate) ; 
int read_oxford_input(const char *file_name, string& req_gender, input_data& indata);
int getOxfordDate(char *sdate);

// Writing
int open_output_files(const char *out_file, running_flags& flags, char *param_names, int nestimates, char *autosim_param_names, int autosim_nestimates, out_fps& fouts) ;
void print_bootstrap_output(vector<vector<double> >& estimates, vector<double>& obs, int nestimates, int nbootstrap, vector<vector<bool> >& valid, vector<bool>& valid_obs, FILE *fp) ;

// Collecting Scores
int collect_all_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date, int first_date, 
					   pair<int,int> &time_window, pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor,
					   vector<string>& idstrs, int *dates, int *days, int *years, double *scores, int *ages, int *id_starts, int *id_nums, int *types, int *nids, int *checksum) ;

int collect_all_autosim_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date, int first_date, 
							   pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor,
							   vector<string>& idstrs, int *dates, int *days, int *years, double *scores, int *gaps, int *id_starts, int *id_nums, int *types, int *nids, int *checksum ) ;

int collect_periodic_autosim_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date, int first_date, 
							   pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor,
							   vector<string>& idstrs, int *dates, int *days, int *years, double *scores, int *gaps, int *id_starts, int *id_nums, int *types, int *nids, 
							   int period, int *nperiods, int *checksum ) ;

int collect_periodic_cuts_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date, int first_date, 
							   pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor,
							   vector<string>& idstrs, int *dates, int *days, int *years, double *scores, int *time_to_cancer, int *id_starts, int *id_nums, int *types, int *nids, 
							   int period, int gap, int *nperiods, int *checksum ) ;
							  
int collect_all_binary_autosim_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date,
					   pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor, vector<string>& idstrs, int *types, int *gaps, int *nids, int *checksum) ;

// Initial analysis of parameters
void get_autosim_parameters(int *ids, int *types, int *id_starts, int *id_nums, int nids, double *all_scores, int *all_gaps, vector<double>& parameters, vector<bool>& valid, quick_random& qrand , double extra_fpr) ;
void get_periodic_autosim_parameters(int *ids, int *types, int *id_starts, int *id_nums, int nids, double *all_scores, int *all_time_to_cancer, int *all_days, vector<double>& parameters, quick_random& qrand ,
									double extra_fpr, int first_day, int period, int nperiods,int tot_autosim_nestimates, int autosim_nestimates, vector<bool>& valid) ;

void get_periodic_cuts_parameters(int *ids, int *types, int *id_starts, int *id_nums, int nids, double *all_scores, int *all_gaps, int *all_days, vector<double>& parameters, quick_random& qrand ,
									double extra_fpr, int first_day, int period, int nperiods, int tot_autosim_nestimates, int autosim_nestimates, vector<bool>& valid) ;

int get_binary_autosim_parameters(int *ids, int *types, int nids, int *gaps, vector<double>& estimate) ;


void get_stats(vector<double>& pos, vector<double>& neg, all_stats& stats) ;
void get_minimal_stats(vector<double>& pos, vector<double>& neg, all_stats& stats) ;

// Bootstrapping
int get_bootstrap_scores(double *scores, int *types, int *id_starts, int *id_nums, int nids, vector<double>& pos_scores, vector<double>& neg_scores, quick_random& qrand, int take_all) ;
int get_autosim_scores(int *gaps, double *scores, int *types, int *id_starts, int *id_nums, int nids, vector<double>& pos_scores, vector<double>& neg_scores, quick_random& qrand ,vector<double>& earlysens1pos_scores,
					   vector<double>& earlysens2pos_scores,vector<double>& earlysens3pos_scores, int take_all ) ;
double max_vector (vector<double>& vec); 
int max_vector_int (vector<int>& vec);
int get_bootstrap_stats(double *scores, int *ages, int *types, int *id_starts, int *id_nums, int nids, all_stats& stats, map<int,double>& incidence_rate, double *incidence, bool use_last, quick_random& qrand, int take_all) ;
int get_binary_bootstrap_stats(double *scores, int *ages, int *types, int *id_starts, int *id_nums, int nids, int stats[2][2], map<int,double>& incidence_rate, double *incidence, bool use_last, quick_random& qrand, int take_all)  ;
void get_bootstrap_performance(vector<double>& pos_scores, vector<double>& neg_scores, vector<target_bound>& bnd, vector<double>& estimates) ;
void get_bootstrap_performance_autosim(vector<double>& pos_scores,vector<double>& earlysens1pos_scores ,vector<double>&  earlysens2pos_scores,vector<double>& earlysens3pos_scores, vector<double>& neg_scores, vector<target_bound_autosim>& bnds, vector<double>& estimates);
void get_bootstrap_estimate(all_stats& stats,vector<double>& estimate, double incidence, double extra_fpr, double extra_sens, bool all_fpr, vector<bool>& valid) ;
void get_binary_bootstrap_estimate(int stats[2][2],vector<double>& estimate, double incidence) ;

void print_raw_and_info(vector<string>& idstrs, int *dates, double *scores, int *types, int *id_starts, int *id_nums, int nids, quick_random& qrand, FILE *fp_raw, FILE *fp_info, char *prefix, bool use_last);

// Cox Model
int create_matrix_for_cox(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date,
						  pair<int,int> &initialization_date, pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor, char *matrix_file) ;
int perform_cox_analysis(char *matrix_file, const char *out_dir)  ;

// Comparions
/*			Comparison for doubles sort	*/
struct rev_double_compare {
    bool operator()(const double& a, const double& b) {               
		return (b < a) ;
    }
} ;

/*			Comparison for integers qsort */
int int_compare (const void *a, const void *b) ;

/*			Compare for pairs sort */
struct rev_compare_pairs {
    bool operator()(const pair<int, double>& left, const pair<int, double>& right) {
                return (right.second < left.second) ;
    }
} ;

/*			Compare for autosim scores */
struct rev_compare_autosim_scores {
    bool operator()(const autosim_score& left, const autosim_score& right) {
                return (right.score < left.score) ;
    }
} ;

struct rev_compare_periodic_autosim_scores {
    bool operator()(const periodic_autosim_score& left, const periodic_autosim_score& right) {
                return (right.score < left.score) ;
    }
} ;

#endif