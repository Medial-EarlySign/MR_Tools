#ifndef _COMMON_HEADER_H_
#define _COMMON_HEADER_H_

// General Include Files
#include "stdlib.h"
#include "stdio.h"
#include "string.h"
#include "math.h"
#include <assert.h>

#include <vector> 
#include <map>
#include <set>
#include <algorithm> 
#include <string>
#include <sstream> 
#include <iostream> 

#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>

// Medial Include File
#include "zlib/zlib/zlib.h"
#include "gbm/gbm/gbm_utils.h"
#include "classifiers/classifiers/classifiers.h"
#include "data_handler/data_handler/data_handler.h"
#include "ROCR/ROCR/ROCR.h"
#include "medial_utilities/medial_utilities/medial_utilities.h"
#include "medial_utilities/medial_utilities/globalRNG.h"
#include "QRF/QRF/QRF.h"
#include "InfraMed/InfraMed/InfraMed.h"

using namespace std ;
using namespace boost ;

//#define BIN_WITH_PSA

// Basic files
#define STT_FILE "W:/CancerData/AncillaryFiles/Censor"
#define REG_FILE "W:/CancerData/AncillaryFiles/Registry.mrf"
#define DEM_FILE "W:/CancerData/AncillaryFiles/Demographics" 
#define GRP_FILE "W:/CancerData/AncillaryFiles/Groups" 

// Input Data Info
#define MAXLINES (12000000)
#define MAXCOLS (60)

#define ID_COL 0 
#define DATE_COL 1
#define BDATE_COL 2
#define AGE_COL 3
#define GENDER_COL 4
#define STATUS_COL 5
#define STATUS_DATE_COL 6
#define CANCER_COL 7
#define CANCER_DATE_COL 8
#define TEST_COL 9
#ifdef BIN_WITH_PSA
#define NBIOCHEM 14
#else
#define NBASIC_BIOCHEM 13 // Biochemistry that is considered in clipping counts
#define NBIOCHEM (NBASIC_BIOCHEM+7)
#endif
#define NCBC  20
#define NRED 10

#define NTESTS ((NCBC) + (NBIOCHEM))

#define BMI_COL (TEST_COL + NTESTS)
#define BMI_NCOLS 2 

#define SMX_COL (TEST_COL + NTESTS + BMI_NCOLS)
#define SMX_NCOLS 3
#define QTY_SMX_COL (TEST_COL + NTESTS + BMI_NCOLS + SMX_NCOLS)
#define QTY_SMX_NCOLS 2


#define EXTRA_COL (TEST_COL + NTESTS + BMI_NCOLS + SMX_NCOLS + QTY_SMX_NCOLS)
#define NEXTRA (MAXCOLS - EXTRA_COL)

#define SIGMA_FOR_SPEC_SMOOTHING 0.15
#define MAX_Z_FOR_SPEC_SMOOTHING 3

#define CNT_FOR_MIN_VAL 10
#define CLEANING_EPS 0.001

typedef double *linearLinesType ;
typedef 	double  (*matrixLinesType)[MAXCOLS];

typedef	union{
	double alignDummy[MAXCOLS]; /* make sure the structure is completed by spares*/
	struct {
		double id;
		double date;
		double birthDate;
		double dummyAge;
		double gender;
		double status;
		double statusDate;
		double cancer;
		double cancerDate;
		
		double rbc,wbc,mpv,hgb,hcrt,mcv,mch,mchc,rdw,plt,eos,neutPerc,monPerc,eosPerc,basPerc,neut,mon,bas,lymphPerc,lympH;
		
#ifdef BIN_WITH_PSA
		double alb,ca,chol,creat,hdl,ldl,k,na,tg,urea,uric,cl,ferittin,psa;
#else
		double alb,ca,chol,creat,hdl,ldl,k,na,tg,urea,uric,cl,ferittin;
#endif
		
		double bmi;
		double smoking[SMX_NCOLS];
		double qtySmoking[QTY_SMX_NCOLS];
		double originFlag;

		// few spares here up to MAX COLS
	};
	// in the next struct, most components are just place holders for consistency with the previous struct
	struct {
		double id_2;
		double date_2;
		double birthDate_2;
		double dummyAge_2;
		double gender_2;
		double status_2;
		double statusDate_2;
		double cancer_2;
		double cancerDate_2;
		
		double cbc[NCBC];
		double biochem[NBIOCHEM]; 

		double bmi_2;
		double smoking_2[SMX_NCOLS];
		double qtySmoking_2[QTY_SMX_NCOLS];
		double originFlag_2;

		// few spares here up to MAX COLS
	};
} structuredLine;


/*
The 3 above pointer types can be casted to each other so you can use line[y+x*MAXCOLS]
or line[x][y] or line[x].chol or line[x].cbc[4]
*/

// translation of the names for signal retieving from repository
// at this time we do not use continuous signals (bmi smoking etc.)
//we ignore the PSA FLAG.


typedef struct{// This structures hold the interpreted params of the command line
			   // and also the file descriptors for the i/o files.
		  	   // it holds parameters for learn, full_cv and predict . Each uses only part of the fields.
	
	// Common Variables
	string binFileName ; 
	gzFile binFile ;
	string logFileName;
	FILE  *logFile ;
	string predictorFileName;
	gzFile predictorFile ;
	string completionParamsFileName ;
	gzFile completionParamsFile ;
	string outliersParamsFileName;
	FILE  *outliersParamsFile ;

	string featuresSelectString;
	string extraFeaturesString ;
	string methodString;
	map <string, int> methodMap ;

	bool use_completions; // flag to use precomputed linear models from file (in completionParamsFile)
	bool only_completions; // flag to stop after creating completion files.

	// Predict/CV
	int autoCompletionFlag ;
	string predictOutFileName;
	FILE *predictOutFile;
	string incFileName ;// incedence by age
	FILE *incFile ;
	string ftrsOutFileName;
	FILE *ftrsOutFile;
	int noise_direction ;
	double noise_level ;
	string noisy_ftrs ;
	string header_info ;
	int history_pattern ;
	int max_history_days ;

	// Learn/CV
	int nfold, nbins, seed;
	int startPeriod, endPeriod, cancerDate;	
	int sp_nfold ;
	int sp_start_period, sp_end_period ;
	bool useReg; // fill cancer status and date in lines matrix based on a registry file
	string regFileName;
	FILE *regFile;
	string regGroupsFileName;
	FILE *regGruoupsFile;
	int regGroupNum;

	// Matching
	string matching_field,matching_res ;
	string model_prior_field,external_prior_field;
	double matching_w ;

	// Two Stages
	int ts_nfold ; // Learning
	bool two_stages ; // Prediction

	// Complex methods
	string internal_method ;
	string external_method ;

	// Parameters file
	string extraParamsFileName ;
	FILE *extraParamsFile ;

	// Threading
	int nthreads ;

} programParamStrType;


typedef struct {
	int nftrs;
	int nrows;
	double *x;
	double *y;
	double *w;
	int *idnums;
	int *flags;
	int *dates;
	int *censor;
	
	int print_x() {
		for(int i = 0; i < nrows; ++i) {
			for (int j = 0; j < nftrs; ++j) {
				fprintf(stderr, "[%d, %d] %f\n", i, j, x[i * nftrs + j]);
			}
		}

		return(0);
	}

} xy_data;

//Generative Model Structure
typedef struct {
	map<vector<int>, int> npos ;
	map<vector<int>, int> nneg ;
	vector<double> resolutions ;
} gen_model ;


// GBM Parameters
#define CRC_GBM_SHRINKAGE 0.1
#define CRC_GBM_BAG_P 0.25
#define CRC_GBM_NTREES 110
#define CRC_GBM_DEPTH 6
#define CRC_GBM_TAKE_ALL_POS true
#define CRC_GBM_MIN_OBS_IN_NODE 10

#define LUNG_GBM_SHRINKAGE 0.18
#define LUNG_GBM_BAG_P 1
#define LUNG_GBM_NTREES 85
#define LUNG_GBM_DEPTH 5
#define LUNG_GBM_TAKE_ALL_POS true
#define LUNG_GBM_MIN_OBS_IN_NODE 10

// General macros
#define SRANDSEED   987654 
#define EPS 0.000001

// Feature Extractions macros
#define MIN_AGE 40
#define MAX_AGE 108

#define FIRST_CBC_DATE 20030101
#define CBC_PER_YEAR 1.5
#define MAX_CNTS 20

#define MINMAX_GAP 730

#define MAX_FTRS 1000
#define BLOCK_LINES 100000

#define MAX_W 5.0

// Weighting
#define DUP_SIZE 50

// Outliers
#define MAX_SDVS 7
#define CLEANING_NITER 10
#define CLEANING_CENTRAL_P 0.66
#define CLEANING_STD_FACTOR 2.0

#define MAX_SDVS_FOR_NBRS 5
#define MAX_SDVS_FOR_CLPS 7
#define MAX_SDVS_FOR_RMVL 14

// Random Forest
#define RF_POS_FACTOR 1.0 
#define RF_FACTOR 2.0 
#define MIN_SAMP_NEG 400

// Test Validity
#define MAX_MISSING_TESTS 12

#define MISSING_VAL -65536
#define MAX_CLIPPED 2
#define NREQ_TEST_NUM 5
#define MIN_LAB_AGE 18

// Normalization
#define NMONTHS (12*10)

// Completion (bins_lm_models)
#define MINIMAL_NUM_PER_AGE 100

// RfGBM Combination
#define COMBINATION_BOUND (0.05)

// Age Matching
#define MAX_YEAR 5000
#define MATCHING_W 0.01 
#define R_NSTEP 1000
#define NBINS_2S 20

// RandomForest
//extern int RF_NTREES;
#define RF_NTREES 1000
#define R_DATA_FILE "R_DataFile"
#define R_CV_SCRIPT "R_FullCV.r"
#define R_PRD_FILE "R_PredsFile"

// QRF
#define QRF_NTREES  1000
#define QRF_NTRY	-1
#define QRF_MAXQ    500
#define QRF_LEARN_NTHREADS 8
#define QRF_PREDICT_NTHREADS 8
#define QRF_MODE QRF_MODE_QRF

// Posterior Probs
#define AGE_GROUP_RES 5
#define SCORE_RES 0.01
#define SCORE_NVALUES 400
#define KERNEL_RANGE 40
#define UPPER_SCORE_P_BOUND 0.00005
#define LOWER_SCORE_P_BOUND 0.00001
#define AGE_DEP_RESOLUTION 100

// Classes
class score {
public:
	int date ;
	int days ;
	int value ;
} ;

class cancer {
public:
	int days ;
	int index ;
} ;

class reg_entry {
public:
	int    date;
	double type;
} ;

class demographics {
public:
	int byear ;
	char gender ;
} ;

typedef struct {
	double pred ;
	double label ;
} prediction ;


// Structures 
// Generalized Learner - All learning information
typedef struct {
	// For GBM
	gbm_parameters *gbm_params ;
	// For Ensemble of GBM
	int gbm_ens_size ;
	// For RF
	char rf_file_name[MAX_STRING_LEN] ;
	int rf_ntrees ;
	// For Cross Validation (Required for combining)
	int nfold ;
	int seed ;
	// For Bound-based combination
	double combination_bound ;
	// For GBM-based combination
	gbm_parameters *comb_gbm_params ;
	// For matching
	map<string,int> field_cols ;
	vector<int> matching_col ;
	vector<double> matching_res ;
	double matching_w ;
	// For P(Score)
	int get_score_probs ;
	int sp_nfold ;
	int sp_start_period, sp_end_period ;
	map<string,vector<cancer> > registry ;
	FILE * incFile;
	// For two-stages
	int ts_nfold ;
	// Complex methods
	string internal_method ;
	string external_method ;
	// For QRF
	int qrf_ntrees;
	int qrf_ntry;
	int qrf_max_quant;
	// Threading
	int nthreads ;
} generalized_learner_info_t ;

// Generalized Predictor - All prediction information
typedef struct {
	// Method
	string method ;
	// Matching information
	map<string,int> field_cols ;
	vector<int> external_prior_cols,model_prior_cols ;
	FILE *incFile ;
	// Flags 
	bool two_stages ;
	// Complex methods
	string internal_method ;
	string external_method ;
	// Threading
	int nthreads ;
	// Output
	FILE *ftrsFile;
} generalized_predictor_info_t ;

// Feature Flags - which features to use
typedef struct {
	int gender ;
	int age ;
	int bmi ;
	int smx ;
	int qty_smx;
	int biochems[NBIOCHEM] ; 
	int cbcs[NCBC] ;
	int cnts ;
	int minmax ;
	int binary_history ;
	int extra[NEXTRA] ;
}  feature_flags ;

// Combination - standard combination of RF (scores1) and GBM (scores2)
typedef struct {
	double bound,bound_score ;
	int n1,n2 ;
	double *in_score1,*out_score1 ;
	double *in_score2,*out_score2 ;
} combination_params ;

// Completion - Age dependent linear model
typedef struct {
	double *bs ;
	double *means ;
	double *sdvs ;
	double *ymeans ;
	double age_means[MAX_AGE+1] ;
	double sdv ;
} bins_lm_model ;

// RfGBM - RandomForest + GBM + Combination
typedef struct {
	random_forest rf ;
	full_gbm_learn_info_t gbm ;
	combination_params comb ;

} rfgbm_info_t ;

// Learning Parameters for RfGBM
typedef struct {
	int seed ;
	int nfold ; 
	gbm_parameters *gbm_params ;
	double combination_bound ;
	char rf_file_name[MAX_STRING_LEN] ;
	int rf_ntrees;
} rfgbm_learning_params ;

// RfGBM2 - RandomForest + GBM + Combination by GBM
typedef struct {
	random_forest rf ;
	full_gbm_learn_info_t gbm ;
	full_gbm_learn_info_t comb_gbm ;

} rfgbm2_info_t ;

// Learning Parameters for RfGBM2
typedef struct {
	int seed ;
	int nfold ; 
	gbm_parameters *gbm_params ;
	gbm_parameters *comb_gbm_params ;
	char rf_file_name[MAX_STRING_LEN] ;
	int rf_ntrees;
} rfgbm2_learning_params ;

typedef struct {
	double min ;
	double score_res ;
	map<int,double> probs[2] ;
	double min_preds[2] ;
	double max_preds[2] ;
} score_probs_info ;


typedef vector< pair<double , double>> pred_to_spec_info_t ;


// Cleaner
typedef struct {
	double *data_min, *data_max ;
	double *ftrs_min, *ftrs_max ;
	double *data_avg, *data_std ;
	double *min_orig_data ;
	int ndata, nftrs ;
	int mode ;
} cleaner ;


// Functions
/************************************************************************************************************************************************************************************/
// bins_lm_models : A set of linear models for evaluating values of CBC+BIOCHEM parameters at a time-point according to values of same parameter at other time-points.
//					The model to use is determined by the available data

// Build and use models to predict value according to PAST values only: used for completing missing current values
int get_past_model(double lines[], int nlines, int col, bins_lm_model *model, int npatients, int ncols, float missing_val) ;
double get_value_from_past_model(double lines[], int col , int first, int last, int *days, int day, int ncols, bins_lm_model *model, double *x, float missing_val, int no_random) ;
// Build models to predict value according to ALL values (past and future): used for interpolating values the past
int get_all_model(double lines[], int nlines, int col, bins_lm_model *model, int npatients, int ncols, float missing_val) ;
double get_value_from_all_model(double lines[], int col , int first, int last, int *days, int day, int ncols, bins_lm_model *model, double *x, float missing_val, int no_random) ;
// An envelope for building PAST + ALL models (optionally writing to file)
int build_bins_lm_models(double *lines, int nlines,int ncols, feature_flags *fflags, bins_lm_model *all_models, int npatients, float missing_val, gzFile fprms = NULL) ;
int build_bins_lm_models(double *lines, int nlines,int ncols, feature_flags *fflags, bins_lm_model *past_models, bins_lm_model *all_models, int npatients, float missing_val, gzFile fprms = NULL) ;
// Write bins_lm_model
int write_bins_lm_model (bins_lm_model *model, int cnt1, int cnt2, gzFile fp) ;
// Read PAST + ALL models from file
int read_init_params(gzFile fprms, bins_lm_model *all_models, int *cbc_flags,int *biochem_flags) ;
int read_init_params(gzFile fprms, bins_lm_model *past_models, bins_lm_model *all_models, int *cbc_flags,int *biochem_flags) ;
// Functions for new version of completion
double get_default_value(double lines[], int col , int first, int last, int uselast, int *days, int day, int ncols, bins_lm_model *model, double *x) ;
double get_value_from_all_model_no_current(double lines[], int col , int first, int last, int uselast, int *days, int day, int ncols, bins_lm_model *model, double *x, float missing_val) ;
// Utilities
int get_max_periods() ;

/************************************************************************************************************************************************************************************/
// Combining RF and GBM predictions - 
// Standard combination method - Order predictinos of RF (in_preds1) and GBM (in_preds1) from highest to lowest . If in top bound_p part of RF predictions, output prediction is the corresponding
//								 RF ranking (95-100), otherwise, take the GBM ranking (transformed to the range 0-95, where 0 is the lowest, 95 the highest)
// Calculate combination params
int get_combination_params(double *in_preds1, double *in_preds2, int nrows, double bound_p, combination_params *comb_params) ;
// Calculate combination params and write to file
int combine_predictions(double *in_preds1, double *in_preds2, int nrows, double bound_p, char *fname) ;
// Calculate combination params and combined-predictions using FILTERED data (same filtering as for learning), optinally writing to a file
int combine_predictions(double *in_preds1, double *in_preds2, int *ids, int *dates, int *flags, int *censor, double *labels, double *out_preds, int nrows, double bound_p, char *fname=NULL) ;
// Calculate combination params and combined-prediction (optionally writing params to file textually)
int combine_predictions(double *in_preds1, double *in_preds2, double *out_preds, int nrows, double bound_p, char *fname=NULL) ;
// Write combination params to file (textually)
int write_combination_params(char *fname, combination_params *comb_params) ;
// Read combination params from file (textually)
int read_combination_params(char *fname, combination_params *comb_params) ;
// Combine predictions
void combine_predictions(double *in_preds1, double *in_preds2, double *out_preds, int nrows, combination_params *comb_params) ;
// Read combination params and combine predictions
int combine_predictions(double *in_preds1, double *in_preds2, double *out_preds, int nrows, char *fname) ;
// Serialization
size_t get_combination_params_size(combination_params *comb_params) ;
int serialize(combination_params *comb_params, unsigned char *comb_data) ;
int deserialize(unsigned char *comb_data, combination_params *comb_params) ;
// Clearing combination-params object
void clear_combination_params (combination_params *comb_params) ;

// Alternative combination metod - using GBM
// Learn GBM predictor for combination and write to file
int gbm_combine_predictions(double *x, int ncols, int nrows, int *ids, int *dates, int *flags, double *y, char *fname) ;
// Learn GBM predictor for combination, apply, and write to file
int gbm_combine_predictions(double *x, int ncols, int nrows, int *ids, int *dates, int *flags, double *y, double *preds, char *fname) ;
// Read gbm combination params from file and apply
int final_gbm_predict(double *x, double *preds, int nrows, int ncols, char *fname) ;

/************************************************************************************************************************************************************************************/
// RFGBM functions - learning a random-forest, a GBM model and combination-params
// Learn the RfGBM predictor.
int learn_rfgbm_predictor(xy_data *xy, rfgbm_learning_params *learning_params, rfgbm_info_t *rfgbm_info) ;
int learn_rfgbm_predictor(xy_data *xy, rfgbm_learning_params *learning_params, rfgbm_info_t *rfgbm_info, vector<int>& matching_col, vector<double>& matching_res, double matching_w) ;
// Learn the RfGBM predictor and serialize. 
int learn_rfgbm_predictor(xy_data *xy, rfgbm_learning_params *learning_params, unsigned char **rfgbm_data) ;
int learn_rfgbm_predictor(xy_data *xy, rfgbm_learning_params *learning_params, unsigned char **rfgbm_data, vector<int>& matching_col, vector<double>& matching_res, double matching_w) ;
// Learn combination-params for RfGBM using cross validation.
int learn_combination_params(xy_data *xy, rfgbm_learning_params *learning_params, combination_params *comb_params, int matching_col, double matching_res, double matching_w) ;
// Predict using an RfGBM object
int predict_rfgbm(double *x,int nrows, int ncols, rfgbm_info_t *rfgbm_info, double *preds) ;
// Predict using a serialized RfGBM object
int rfgbm_predict(double *x, double *preds, int nrows, int ncols, unsigned char *model) ;
// RfGBM cross validation - Filter learning set, learn and predict on test-set.
int get_rfgbm_predictions(xy_data *xy1, rfgbm_learning_params *rfgbm_params, xy_data *xy2 ,double *preds) ;
int get_rfgbm_predictions(xy_data *xy1, rfgbm_learning_params *rfgbm_params, xy_data *xy2 ,double *preds, vector<int>& matching_col, vector<double>& matching_res, double matching_w) ;
// Serialization
size_t get_rfgbm_size(rfgbm_info_t *rfgbm_info) ;
int serialize(rfgbm_info_t *rfgbm_info, unsigned char *rfgbm_data) ;
int deserialize(unsigned char *rfgbm_data, rfgbm_info_t *rfgbm_info) ;
// Cleaning
void clear_rfgbm_struct(rfgbm_info_t *rfgbm_info) ;

/************************************************************************************************************************************************************************************/
// RFGBM2 functions - learning a random-forest, a GBM model and combination GBM
// Learn the RfGBM predictor.
int learn_rfgbm2_predictor(xy_data *xy, rfgbm2_learning_params *learning_params, rfgbm2_info_t *rfgbm_info, vector<int>& matching_col, vector<double>& matching_res, double matching_w) ;
int learn_rfgbm2_predictor(xy_data *xy, rfgbm2_learning_params *learning_params, rfgbm2_info_t *rfgbm_info) ;
// Learn the RfGBM predictor and serialize. 
int learn_rfgbm2_predictor(xy_data *xy, rfgbm2_learning_params *learning_params, unsigned char **rfgbm_data) ;
int learn_rfgbm2_predictor(xy_data *xy, rfgbm2_learning_params *learning_params, unsigned char **rfgbm_data, vector<int>& matching_col, vector<double>& matching_res, double matching_w) ;
// Learn combination-params for RfGBM using cross validation.
int learn_combination_gbm(xy_data *xy, rfgbm2_learning_params *learning_params, full_gbm_ens_learn_info_t *comb_gbm, vector<int>& matching_col, vector<double>& matching_res) ;
int get_combination_gbm(double *rf_preds, double *gbm_preds, double *labels, int npreds, gbm_parameters *gbm_params, full_gbm_learn_info_t *comb_gbm) ;
// Predict using an RfGBM object
int predict_rfgbm2(double *x,int nrows, int ncols, rfgbm2_info_t *rfgbm_info, double *preds) ;
// Predict using a serialized RfGBM object
int rfgbm2_predict(double *x, double *preds, int nrows, int ncols, unsigned char *model) ;
// RfGBM cross validation - Filter learning set, learn and predict on test-set.
int get_rfgbm2_predictions(xy_data *xy1, rfgbm2_learning_params *rfgbm_params, xy_data *xy2 ,double *preds) ;
int get_rfgbm2_predictions(xy_data *xy1, rfgbm2_learning_params *rfgbm_params, xy_data *xy2 ,double *preds, vector<int>& matching_col, vector<double>& matching_res, double matching_w) ;
// Serialization
size_t get_rfgbm2_size(rfgbm2_info_t *rfgbm_info) ;
int serialize(rfgbm2_info_t *rfgbm_info, unsigned char *rfgbm_data) ;
int deserialize(unsigned char *rfgbm_data, rfgbm2_info_t *rfgbm_info) ;
// Cleaning
void clear_rfgbm2_struct(rfgbm2_info_t *rfgbm_info) ;

/************************************************************************************************************************************************************************************/
// Random Forest
// Local Stratified RandomForest learning - each forest is built based on sampling nneg+npos samples with repetitions.
// Stratified learning of RandomForest and writing to binary file
int R_learn_classification_strat(double *tx, double *y, int nrows, int ncols, int nneg, int npos, char *ftree, int ntrees) ;
// Stratified learning of RandomForest and writing to a binary defualt file
int R_learn_classification_strat(double *tx, double *y, int nrows, int ncols, int nneg, int npos, int ntrees) ;
// Learn a RandomForest predictor using the stratified learning, and write to a binary file
int learn_rf_predictor(double *x1, double *y1, int nrows1, int ncols, char *ftree, int ntrees) ;
// Learn a RandomForest predictor using the stratified learning, and write to a default binary file
int learn_rf_predictor(double *x, double *y, int nrows, int ncols, int ntrees) ;
// Learn a RandomForest predictor using the stratified learning, and serialize, using the given file in the process
int learn_rf_predictor(double *x, double *y, int nrows, int ncols, char *file_name, unsigned char **model, int ntrees) ;
// Learn a RandomForest predictor using the stratified learning, and serialize, using the default file in the process
int learn_rf_predictor(double *x, double *y, int nrows, int ncols, unsigned char **model, int ntrees) ;
// RandomForest cross validation - learn on trainig-set and predict on test-set.
int get_rf_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, int ntrees) ;

/************************************************************************************************************************************************************************************/
// QRF
int learn_qrf_predictor(double *x, double *y, int nrows, int ncols, unsigned char **model, int ntrees, int ntry, int maxq, int nthreads) ;
int get_qrf_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, int ntrees, int ntry, int maxq, int nthreads);

/************************************************************************************************************************************************************************************/
// GBM - Envelope functions for GBM library
// Read GBM learning parameters from file
int read_gbm_params(char *file, gbm_parameters *gbm_params) ;
// Set GBM learning parameters according to type
int set_gbm_parameters (char *type, gbm_parameters *gbm_params) ;
// Learn a GBM predictor and write to a file, given by name (textually). when weights are not given, they are set to 1.0
int learn_gbm_predictor(double *x, double *y, double *w, int nrows, int ncols, char *fname, gbm_parameters *gbm_params) ;
int learn_gbm_predictor(double *x, double *y, int nrows, int ncols, char *fname, gbm_parameters *gbm_params) ;
// Learn a GBM predictor and write to a file, giben by a file handler (textually). when weights are not given, they are set to 1.0
int learn_gbm_predictor(double *x, double *y, double *w, int nrows, int ncols, FILE *fp, gbm_parameters *gbm_params) ;
int learn_gbm_predictor(double *x, double *y, int nrows, int ncols, FILE *fp, gbm_parameters *gbm_params) ;
// Learn a GBM predictor and serialize. when weights are not given, they are set to 1.0
int learn_gbm_predictor(double *x, double *y, double *w, int nrows, int ncols, unsigned char **model, gbm_parameters *gbm_params) ;
int learn_gbm_predictor(double *x, double *y, int nrows, int ncols, unsigned char **model, gbm_parameters *gbm_params) ;
// Read a GBM predictor from a file (textually) and apply
int gbm_predict(double *x, double *preds, int nrows, int ncols, char *fname) ;
// Deserialize a GBM model and apply
int gbm_predict(double *x, double *preds, int nrows, int ncols, unsigned char *model) ;
// GBM cross validation -learn on trainig-set and predict on test-set. when weights are not given, they are set to 1.0
int get_gbm_predictions(double *x1, double *y1, double *w1, int nrows1, double *x2, int nrows2, int ncols, double *preds, gbm_parameters *gbm_params) ;
int get_gbm_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, gbm_parameters *gbm_params) ;

/************************************************************************************************************************************************************************************/
// LS - Envelope functions for LeastSquare linear model functions in Classifiers library
// Learn a weighted least-squares linear model
int learn_ls(double *x1, double *y1, double *w1, int nrows1, int ncols, double *b, double *norm) ;
// Learn a least-squares linear model
int learn_ls(double *x1, double *y1, int nrows1, int ncols, double *b, double *norm, int pos_duplicity) ;
// Learn a least-squares linear model and write to file
int learn_ls(double *x1, double *y1, int nrows1, int ncols, char *fname, int pos_duplicity) ;
// Learn a least-squares linear model and serialize
int learn_ls(double *x1, double *y1, int nrows1, int ncols, unsigned char **model, int pos_duplicity) ;
// Linear model prediction from file
int ls_predict_from_file(double *x, double *preds, int nrows, int ncols, char *fname) ;
// Linear model prediction from model
int ls_predict_from_model(double *x, double *preds, int nrows, int ncols, unsigned char *model) ;
// LS cross validation -learn on trainig-set and predict on test-set.
int get_ls_predictions(double *x1, double *y1, double *w1, int nrows1, double *x2, int nrows2, int ncols, double *preds, int pos_duplicity) ;
int get_ls_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, int pos_duplicity) ;

/************************************************************************************************************************************************************************************/
// EnsGBM - an ensemble of gbm predictors
// Learn a GBM ensemble and write to a file (textually).
int learn_gbm_ens_predictor(double *x, double *y, int nrows, int ncols, char *fname, gbm_parameters *gbm_params, int ens_size) ;
// Learn a GBM ensemble and serialize.
int learn_gbm_ens_predictor(double *x, double *y, int nrows, int ncols, unsigned char **model, gbm_parameters *gbm_params, int ens_size) ;
// Read a GBM ensemble from file and predict
int gbm_ens_predict(double *x, double *preds, int nrows, int ncols, char *fname) ;
// Deserialize a GBM ensemble model and predict
int gbm_ens_predict(double *x, double *preds, int nrows, int ncols, unsigned char *model) ;
// EnsGBM cross validation -learn on trainig-set and predict on test-set.
int get_gbm_ens_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, gbm_parameters *gbm_params, int ens_size) ;

/************************************************************************************************************************************************************************************/
// Handle dependent (calucludated) variables (MCV,MCH,MCHC,WBC,White Line Percents)
// Rounding to a given precision (1/accuracy)
double round(double in, int accuracy) ;
// Complete calculated values in a given line when missing (marked by the value given in missing)
int complete_dependent(double *line, double missing)  ;
// Complete calculated values in a matrix when missing (marked by the value given in missing)
int complete_dependent (double *lines, int nlines, int ncols, double missing = -1.0) ;
// Complete calculated values in a (partialy log-)transofrmed matrix when missing (marked by the value given in missing)
int complete_dependent_transformed(double *lines, int nlines, int ncols, cleaner& cln, double missing);
// Replace calculated values with 'missing' in a given line
int remove_dependent(double *line, double missing) ;
// Replace calculated values with 'missing' in a matrix
int remove_dependent (double *lines, int nlines, int ncols, double missing = -1.0) ;

/************************************************************************************************************************************************************************************/
// Perform initial transformations on data
void perform_initial_trnasformations(double *lines, int nlines, cleaner& cln, int ncols, double missing = -1.0) ;
int get_orig_min_values(double *lines, int nlines, cleaner& cln, int ncols, double missing = -1.0) ;

/************************************************************************************************************************************************************************************/
// Transform a features-information string to features-flag structure
int get_feature_flags(char *info, feature_flags *fflags) ;

/************************************************************************************************************************************************************************************/
// FEATURE DEPENDENT FUNCTIONS - TO BE CHANGED WHEN CHANGING FEATURES STRUCTURE
// Count number of features according to features-flag structure
int get_nftrs(feature_flags *fflags) ;
// adjust clipping mask according to features-flag structure
void adjust_mask(feature_flags *fflags , bool *mask) ;
// Identify location of fields in feautres vector
void get_all_cols(feature_flags *fflags, map<string,int>& cols) ;
// Create a features vector for line 'iline'.
int get_x_line(double lines[], int iline, int first, int ncols, int *days, int *countable, bins_lm_model *all_models, double *tempx, int *cnts, feature_flags *fflags,
			   int nftrs, double *x, float missing_val, int no_random) ;
// Get features for a given parameter
void get_features(double *lines, int *days, int first, int iline, int icol, int ncols, double *x, int *iftr, bins_lm_model *all_model, double *tempx, float missing_val, int no_random) ;
// Filter a line with too many outliers
int clip_and_filter_x_line(double *line, feature_flags *fflags, double *min, double *max, float missing_val) ;
// Adjust clipping parameters for extra considerations
void update_clipping_params(double *min, double *max, feature_flags& fflags, int square) ;

/************************************************************************************************************************************************************************************/
// Create matrices for learning/test/cross-vlidation
int get_x_and_y(int prediction,matrixLinesType lines, int nlines,
		   bins_lm_model *all_models, const programParamStrType& ps,xy_data xy,  
		   int last_pos_day,feature_flags *fflags, int take_all_flag, int filter_flag, 
		   cleaner& cln, int date_ptrn_opt, int max_history_days_opt, int apply_age_filter) ;
// Create learning matrix
int get_xy(matrixLinesType lines, int nlines, programParamStrType& ps,xy_data *xy,int last_pos_day, feature_flags *fflags, int take_all_flag, int cln_mode) ;
// Create test matrix ; minx=maxx=NULL to avoid outliers checking
int get_x_matrix(matrixLinesType lines, int nlines,programParamStrType& ps, xy_data *xy, feature_flags *fflags, int mftrs, int filter_flag, cleaner& cln, int apply_age_filter) ;
// Check validity of sample - all required test must appead
int is_valid_sample(double *line, feature_flags *fflags, int *req_tests, int nreq_tests, float missing_val) ;
// Filter set of CBCs according to output of filter_x_line (checking clippings)
void filter_x_lines_by_age(double lines[], int *days, int *countable, int *nlines, int ncols) ;
// Filter set of CBCs according to output of filter_x_line (checking clippings)
void clip_and_filter_x_lines(double lines[], int *days, int *countable, int *nlines, int ncols, feature_flags *fflags, cleaner& cln, float missing_val) ;
// Check if dates meet the requested pattern and select the relevant dates
int check_date_ptrn(int *days, int num_dates, int num_date_ptrn_segs, int *bgn_date_ptrn_segs, int *end_date_ptrn_segs, int *date_ptrn_inds, int max_history_days_opt) ;
// Get MinMax values
void get_global_values(double lines[], int col , int first, int last, int ncols, double *out, int *days, float missing_val) ;
// Get values for completion when not using the bins_lm_model
void get_test_values(double lines[], int col, int first, int last, int *days, int *gaps, int ngaps, int ncols, double *x, int *iftr, int nftrs) ;
double get_weighted_test_value(double lines[], int col , int first, int last, int *days, int day, int ncols, int *nvals, float missing_val) ;
// Utilities
int get_cnt_nperiods() ;

/************************************************************************************************************************************************************************************/
// Envelopes for learning predicting and cross validation
// Initialize predicting struct
int init_predictor_info( programParamStrType &ps,feature_flags *fflags, generalized_predictor_info_t &predictor_info) ;
// Learn a model according to method and serialize
int learn_predictor(xy_data *xy,string method, generalized_learner_info_t *learning_info, unsigned char **model) ;
// nfold cross-validation using a model according to method
int get_predictions(xy_data *xy, string method, generalized_learner_info_t *learning_info, int nfold, double *preds) ;
int get_predictions(xy_data *xy, string method, generalized_learner_info_t *learning_info, int nfold, map<pair<int,int>, double>& preds_hash) ;
int get_predictions(xy_data *xy, string method, generalized_learner_info_t *learning_info, int nfold, double *preds, int *dates, int *ids, int *flags, int *censor, double *labels) ;
int get_predictions(xy_data *xy, string method, generalized_learner_info_t *learning_info, int nfold, double *preds, int *dates, int *ids, int *flags, int *censor, double *labels , map<pair<int,int>, int>& ranks_hash, int rank_limit); 

// Predictions
int predict(double *x, int nrows, int ncols, generalized_predictor_info_t& predict_info, unsigned char *model, double *preds)  ;

/************************************************************************************************************************************************************************************/
// Data cleaning and preprocessing
// Convert feature flags structure to boolean vector
vector<bool> featureFlagsAsBoolVecForClipping(feature_flags& fflags) ;
// Set off unused features in column mask before first call to get_clipping_params
int adjustColMaskByFeatureFlags(bool* col_mask, feature_flags fflags) ; 
// Clear data by considering mean and standard deviation on central part of vectors
int get_clipping_params_central(double *xtable, int npatient, int nvar, double missing, double *min, double *max, double central_p, double std_factor, double max_std, bool *colon_mask) ;
int get_clipping_params_iterative(double *_xtable, int npatient, int nvar, double missing, double *min, double *max, int niter, double max_std, bool colon_mask[]) ;
int get_clipping_params_central(xy_data *xy, double central_p, double std_factor, double max_std, double missing, double **min, double **max, bool *colon_mask) ;
int get_clipping_params_iterative(xy_data *xy, int niter, double max_std, double missing, double **min, double **max, bool *colon_mask) ;

int get_cleaning_moments(xy_data *xy, int niter, double max_std, double missing, double **avg, double **std, bool *colon_mask) ;
int get_cleaning_moments(double *_xtable, int npatient, int nvar, double missing, double *avg, double *std, int niter, double max_std, bool colon_mask[]) ;
int get_cleaning_minmax(double *avg, double *std, double *min_orig_data, double max_std, double **min, double **max, int nftrs, bool colon_mask[]) ;
void clean_from_moments(xy_data *xy, double *avg, double *std, double *min, double *max, double missing, double max_sdvs_for_clps, double max_sdvs_for_nbrs) ;
void cln_from_moments(double *x, int nftrs, int from, int to, double *avg, double *std, double *min, double *max, double missing, double max_sdvs_for_clps, double max_sdvs_for_nbrs, map<int,pair<int,int> >& ftrs_counter, 
					 vector<int>& lines_counters) ;

// Update Clipping params for extra considerations
void update_clipping_params(double *min, double *max, bool *colon_mask) ;
// Take squares of all features if 'take_squares' is on
int take_squares(xy_data *xy) ;
// Trim outliers based on minx and maxx
int clear_data_from_bounds(xy_data *xy, double missing, double *minx, double *maxx) ;
// Take squares of all features if 'take_squares' is on, and then trim outliers based on minx and maxx, filtering lines that have too many clippings
int process_and_filter_data(double *x, double **nx, int *nrows, int *nftrs, double *avg, double *std, double max_std, int take_squares, int *idnums, int *dates, FILE *flog) ;
// Calculated mean and standard deviations
void get_mean_values(xy_data *xy, double *means, double *sdvs) ;
// Replace missing values with mean values purturbed according to standard-deviation
void replace_with_approx_mean_values(xy_data *xy, double *means, double *sdvs) ;

/************************************************************************************************************************************************************************************/
// Processing of features matrices
// Take only flagged samples
void take_flagged(xy_data *xy);

// Take last "npos" samples from labeled (positive) patients and sample from unlableled (negative) ones to create same calender-years distributions
int take_samples(xy_data *xy, int npos)  ;
// Filter learning set - take only patients labeled as 0/1 and only last "npos" flagged sample of each patient
int filter_learning_set(xy_data *xy, xy_data *fxy, int npos) ;
int filter_learning_set_rank_score(xy_data *xy , int *rank_scores , int rank_limit);
// Prepare indices for Learning Set : Take only y = 1 or 0, only flagged. Take only last for y=1 and sample y=0 according to time.
int get_learning_indices(int *ids, int *dates, int *flags, double *y, int nrows, int **indices) ;
// Filter learning set according to 'get_learning_indices'
int prepare_learning_set(double *inx, double *iny, double *inw, int *inids, int *indates, int *flags, double **x, double **y, double **w, int **ids, int **dates, int nftrs, int inrows) ;
// Split data set to x2 (+ accompanying vectors) (between start and end according to order) and x1 (the rest)
int get_split_data(xy_data *xy, int npatients, xy_data *xy1, xy_data *xy2, int *order, int start, int end) ;

/************************************************************************************************************************************************************************************/
// Age Pairing
// Get optimal crc/non-crc ratio for pairing
double get_pairing_ratio(map<int,int>& hist1, map<int,int>& hist2, int nkeys, double w) ;
// Create a matched set
int get_paired_matrix(xy_data *in, int col, double res, double matching_w, xy_data *out) ;
int get_paired_matrix(xy_data *in, vector<int>& cols, vector<double>& resolutions, double matching_w, xy_data *out)  ;
// Match set according to value of column 'age-col' in x, if age-col is -1, no matching is done.
int adjust_learning_set(xy_data *xy, vector<int>& matching_col, vector<double>& matching_res, double matching_w, xy_data *nxy) ;

/************************************************************************************************************************************************************************************/
// Handling partial dependency separately
// Calculate optimal age-dependet factors to probs. Optimizing log likelihood, considering GBM's preds (probability = exp(2*preds)/(1+exp(2*preds)), and requiring non-decreasing factors
void optimize_age_dependence(double *labels, double *preds, int *ages, int n, double *factors) ;
// Read age factors from file and apply to probs
int age_factor(double *probs, double *x, int nrows, int age_col, char *fname) ;
// Create a registry structure from the original data
void get_registry_from_lines(double *lines, int nlines, int ncols, map<string,vector<cancer> >& registry) ;
// Calculate P(Score) for cases (start-to-end days prior to registry) and controls
int get_score_probs(double *preds, int *dates, int *ids , int npreds, int start, int end, const map<string,vector<cancer> >& registry, score_probs_info& score_probs) ;
// Smoth P(Score)
void smooth_probabilities(map<int,double>& prob) ; 
// Read P(Score)
int read_score_probs(char *fname, map<int,double> *probs, int ntypes, double *def_probs, double *min_score, double *score_res, int *min_scores, int *max_scores) ;
// Calculate Posterior probabilities based on score + age.
void get_posteriors(double *preds, double *ages, int npreds, vector<double>& age_probs, score_probs_info &score_probs) ;
void get_posteriors(double *preds, double *ext_probs, int npreds, score_probs_info &score_probs) ;
// Read Age-dependent priors
void hash_to_vector(map<int, double>& probs_hash, vector<int>& ages, vector<double>& probs) ;
int read_age_dep(FILE *age_dep_fp, vector<double>& probs) ;
// Learn an age-matched model + scores probability
int learn_predictor_and_score_probs(xy_data *xy, string method,generalized_learner_info_t *learning_info, unsigned char **model) ;
int learn_two_stages_predictor(xy_data *xy, string method,generalized_learner_info_t *learning_info, unsigned char **model) ;
int learn_predictor_and_score_probs_ranks(xy_data *xy, string method, generalized_learner_info_t *learning_info, unsigned char **model , int *ranks);

int twosteps_predict(double *x, double *preds, int nrows, int ncols, string internal_method, unsigned char *model,string external_method );

// Predict using a model + scores probability
// (De)Serialization of score_probs_info
size_t get_size (score_probs_info *score_probs) ;
int serialize (score_probs_info *score_probs, unsigned char *model) ;
int deserialize(unsigned char *model, score_probs_info *score_probs) ;
int write_score_probs (score_probs_info *score_probs, char *file_name) ;

// Mapping from Prediction to Specificity
size_t get_size (pred_to_spec_info_t *pred_to_spec);
int serialize (pred_to_spec_info_t *pred_to_spec, unsigned char *model);
int deserialize(unsigned char *model, pred_to_spec_info_t *pred_to_spec);
int write_pred_to_spec (pred_to_spec_info_t *pred_to_spec, char *file_name) ;

// Predict
int predict_and_get_posterior(xy_data *xy, int age_col, generalized_predictor_info_t& pred_info, unsigned char *model, FILE *incFile, double *preds) ;
int predict(xy_data *xy,generalized_predictor_info_t& predict_info, unsigned char *model, double *preds) ;
// Get Prediction using separated model: GBM on age-paired-GBM-prediction + Original data
int get_paired_and_age_predictions(xy_data *xy1, xy_data *xy2, double *preds, gbm_parameters *gbm_params, int age_col) ;
int get_cv_gbm_predictions(xy_data *xy, double *preds , int nfold, gbm_parameters *gbm_params, int age_col) ;

/************************************************************************************************************************************************************************************/
// More Common Functions
// Reading Data
int read_file(FILE *fin, double *lines) ;
int read_file(double lines[][MAXCOLS], char *file_name) ;
int readInputLines(gzFile binFile, linearLinesType *lines); // includes lines allocation
int processVirtualbinFile(gzFile binFile, linearLinesType *lines); // includes lines allocation
/************************************************************************************************************************************************************************************/
// Utilities
int month_id(int month) ;
int get_cols(string fields, map<string,int>& cols_map, vector<int> &cols) ;

/************************************************************************************************************************************************************************************/
// Cross Validation
// Calculate statistics for CV outputs
int get_all_stats(double *labels, double *predictions, int nsamples, int nbins, int resolution, int *bins, int *eqsize_bins) ;
/************************************************************************************************************************************************************************************/
// Comparison
struct compare_pairs {
    bool operator()(const pair<int, double>& left, const pair<int, double>& right) {
                return (left.second > right.second) ;
    }
} ;

struct compare_pairs_by_idx {
    bool operator()(const pair<int, double>& left, const pair<int, double>& right) {
                return (left.first < right.first) ;
    }
} ;

struct rev_compare_pairs {
    bool operator()(const pair<int, double>& left, const pair<int, double>& right) {
                return (right.second < left.second) ;
    }
} ;


struct rev_double_compare {
    bool operator()(const double& a, const double& b) {               
		return (b < a) ;
    }
} ;


/************************************************************************************************************************************************************************************/
// Learner-related functions (for learn  + full_cv) ;
int init_learner_info(programParamStrType& ps, gbm_parameters *gbm_params, feature_flags *fflags, double *lines, int nlines, int ncols, generalized_learner_info_t& learn_info) ;

/************************************************************************************************************************************************************************************/
// Noise Related Function
double get_noise_size(double *lines, int nlines, int ncols, int icol) ;
int add_noise_to_data(double *lines, int nlines, int ncols, double noise_level, int noise_direction, const char *noisy_ftrs) ;

/************************************************************************************************************************************************************************************/
// Generative Models : P(Outcome|Income)
void get_gen_model(xy_data *xy,  generalized_learner_info_t *learning_info, gen_model *model) ;
size_t get_size (gen_model *model) ;
int serialize (gen_model *model, unsigned char *model_data) ;
int deserialize(unsigned char *model_data, gen_model *model) ;
int read_generative_model(FILE *fp, gen_model *model) ;
int get_probs_from_generative_model(vector<vector<double> >& keys, gen_model *model, double *probs) ;
int get_probs_from_incidence(vector<vector<double> >& keys, gen_model *model, double *probs)  ;
/************************************************************************************************************************************************************************************/
// General Purpose Function
// Print Outliers and Completion parameters
void handleOutliersParams(FILE *fileDes, double *means_for_completion, double *sdvs_for_completion, cleaner& cln) ;

// Init methods map
void init_methods_map (map <string, int>& methodMap) ;
// Handle xy_data
void clear_xy(xy_data *xy) ;
void init_xy(xy_data *xy) ;
int copy_xy(xy_data *dest, xy_data *orig) ;
int allocate_xy(xy_data *xy) ;

/************************************************************************************************************************************************************************************/
// New Method
int learn_double_matched_predictor(xy_data *xy, generalized_learner_info_t *learning_info, unsigned char **model) ;
int double_matched_predict(double *x, double *preds, int nrows, int ncols, generalized_predictor_info_t& pred_info, unsigned char *model) ;
double get_spec_from_prob(double prob, vector<pair<double,double> >& pred_to_spec) ;
double get_spec_from_prob_gaussian_kernel(double prob, vector<pair<double,double> >& pred_to_spec) ;

/************************************************************************************************************************************************************************************/
// Learning parameters
int set_parameters(FILE *fp) ;
int set_gaps (vector<string>& fields) ;

/************************************************************************************************************************************************************************************/
// Virtual BinFile
int buildBinFromRepository(MedRepository &repository, map<int, set<int>>&idList, string groups, matrixLinesType *linesM);

#endif

