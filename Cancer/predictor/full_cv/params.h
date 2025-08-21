#ifndef _PARAMS_H_
#define _PARAMS_H_

#define _CRT_SECURE_NO_WARNINGS

#define INPUT_FILE "C:\\Data\\ColonCancer\\men_matrix_full.bin"
#define MOMENTS_FILE "C:\\cygwin\\home\\yaron\\ColonCancer\\Data\\cbc_moments"

#define SRANDSEED   987654 // 123456
#define NFOLD 10
#define NSHUFFLES 1

#define MAXLINES 4000000 // 2550000
#define MAXCOLS 60

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
#define NBIOCHEM 12
#define NCBC  20
#define NRED 10

int reds[NCBC+NBIOCHEM+1] = {1,0,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0} ;

#define NTESTS ((NCBC) + (NBIOCHEM) + 1)


#define BMI_COL (TEST_COL + NTESTS)
#define BMI_NCOLS 2 
#define SMX_COL (TEST_COL + NTESTS + BMI_NCOLS)
#define SMX_NCOLS 3
#define ORIGIN_FLAG_COL (TEST_COL + NTESTS + BMI_NCOLS+SMX_NCOLS)

#define MIN_PRE_DISCOVERY_DAYS (30) 
#define MAX_PRE_DISCOVERY_DAYS (730)
#define REG_LAST_DATE 20091231
#define MIN_AGE 40
#define MAX_AGE 108
#define INF 1e13
#define EPS 0.000001

#define PERIOD1 730 
#define PERIOD2_MIN 730 
#define PERIOD2_MAX 1460 

#define FIRST_CBC_DATE 20030101

#define NRAND 500

int period_min[] = {0,500,1000} ;
int period_max[] = {500,1000,1500} ;
int nperiods = 3 ;

#define CBC_PER_YEAR 1.5

#define NEG_PROB 1.0
#define ORDER 2

int gaps[] = {180*3, 180*6} ;
int ngaps = 2 ; 

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


#define MINMAX_GAP 730

char test_names[][MAX_STRING_LEN] = {"RBC","WBC","MPV","Hemog","Hemat","MCV","MCH","MCHC","RDW","Plat","Eos#","Neut%","Mon%","Eos%","Bas%","Neut#","Mon#","Bas$"} ;

#define MAX_SDVS 7
#define DUP_SIZE 50
#define MAX_FTRS 1000

#define NPREC 5
double precs[NPREC] = {0.01, 0.02, 0.03, 0.05, 0.1} ;
#define RES 200 

#define MAX_W 5.0
#define MAX_DIST 365*4

#define RF_POS_FACTOR 1.0 
#define RF_FACTOR 2.0 
#define MIN_SAMP_NEG 400
#define KNN_K 50
#define KNN_TYPE 1

#define MAX_MISSING_TESTS 12
#define MISSING_VAL -65536

#define FIRST_YEAR 2003
#define NMONTHS (12*10)

#define MAX_CNTS 20

#define MAX_CLIPPED 2
#define AGE_DEP_RESOLUTION 100

#define AGE_IN_BINNED_MODELS 0

#define NREQ_TEST_NUM 5
int req_sets[NREQ_TEST_NUM] = {0,3,4,6,7} ;

// Features definition
typedef struct {
	int gender ;
	int age ;
	int bmi ;
	int smx ;
	int biochems[NBIOCHEM] ; 
	int cbcs[NCBC] ;
	int cnts ;
	int ferritin ;
	int minmax ;
	int binary_history ;
}  feature_flags ;

// Linear Models
typedef struct {
	double *bs ;
	double *means ;
	double *sdvs ;
	double *ymeans ;
	double age_means[MAX_AGE+1] ;
	double sdv ;
} bins_lm_model ;

int past_periods[] = {30,30*3,30*6,30*10,30*15,30*21,30*28,30*360 } ;
int npast_periods = sizeof(past_periods)/sizeof(int);
double past_rf = 0.99 ; 

int min_period = -(30*18) ;
int max_period = 30*9999 ;

int all_periods[] = {-(30*9),-(30*4),-30,30,30*4,30*9,30*18,30*360} ;
int nall_periods =  sizeof(all_periods)/sizeof(int) ;
double all_rf = 0.99 ;

double panel_rf = 0.99 ;

// Patterns for selecting subsets of history
int bgn_date_ptrn_segs[] = {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1};
int end_date_ptrn_segs[] = {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1};
int max_date_ptrn_segs = 10;
int num_date_ptrn_segs = 0;

#define AGE_GROUP_SIZE 6000
#define MINIMAL_NUM_PER_AGE 100

#endif