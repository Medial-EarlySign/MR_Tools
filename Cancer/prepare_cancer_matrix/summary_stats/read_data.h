#ifndef __READ_DATA__
#define __READ_DATA__

#include <vector>
#include <map>

// constanst

#define BUFFER_SIZE    4096
#define MAX_STRING_LEN 1024

#define REGISTRY_ID_FIELD 0
#define REGISTRY_STAGE_FIELD 4
#define REGISTRY_DATE_FIELD 5
#define REGISTRY_CANCER_FIELD 14
#define REGISTRY_NFIELDS  19

const int MAX_CBC_CODE_NUM = 30;
const int MAX_AGE_BIN = 30;

typedef enum {
	MALE = 0,
	FEMALE,
	GENDERS_NUM
} gender_t;

// Files

static char reg_filename_pattern[] = "registry.csv";
static char dem_filename_pattern[] = "demographics.txt";
static char censor_filename_pattern[] = "censor.status";
static char cbc_codes_filename_pattern[] = "test_codes.csv";
static char cbc_filename_pattern_txt[] = "cbc.txt";
static char cbc_filename_pattern_bin[] = "cbc.bin";
static char param_filename_pattern[] = "params.csv";
static char reference_age_filename[] = "control.age_distribution_by_bins.bin";
static char reference_cbc_filename[] = "control.cbc_value_summary.bin";
static char output_last_filename[] = "last.txt";
extern char output_last_full_filename[MAX_STRING_LEN];
static char output_log_filename[] = "log.txt";
extern char output_log_full_filename[MAX_STRING_LEN];
static char output_comparison_filename[] = "comparison.txt";
extern char output_full_comparison_filename[MAX_STRING_LEN];

static char input_filename_patten[] = "%s/input/%s/%s";
static char refernece_filename_patten[] = "%s/reference/%s";
static char xls_template_pattern[] = "%s/templates/SummaryStatsTemplate.xls";
static char output_filename_patten[] = "%s/output/%s";
static char xls_output_filename_pattern[] = "%s/output/%s";
static char xls_output_filename[] = "summary_stats.xls";


// data structures

static const char gender_names[GENDERS_NUM][MAX_STRING_LEN] = {"Male","Female"} ;

inline int gender2number( char gender ) 
{
	return gender == 'M' ? 0 : 1;
}

// classes

typedef int id_type;
typedef int date_t;
typedef int stage_t;
typedef int cbc_code_id_type;

typedef enum {
	CANCER_TYPE_CRC = 0,
	CANCER_TYPE_CRC_RECCURENCE,
	CANCER_TYPE_NON_CRC,
	CANCER_TYPE_NON_CRC_RECCURENCE,
	CANCER_TYPE_COLON,
	CANCER_TYPE_COLON_RECCURENCE,
	CANCER_TYPE_RECTUM,
	CANCER_TYPE_RECTUM_RECCURENCE
} cancer_type_t;

typedef struct {
	stage_t stage;
	int days_since_1900;
} registry_entry_t;

typedef std::map<id_type, registry_entry_t> cancer_specific_type_registry_t;
typedef std::map<cancer_type_t, cancer_specific_type_registry_t> registry_t;

typedef struct demography_entry {
	int byear ;
	char gender ;
} demography_entry_t;
typedef std::map<id_type, demography_entry_t> demography_t;

typedef struct  {
	date_t date ;
	int stat ;
	int reason ;
	bool in_censor;
	int in_censor_reason;
} censor_entry_t;
typedef std::map<id_type, censor_entry_t> censor_t;

typedef struct {
	int serial_num;
	std::string name;
	double resolution;
	double min_outlier[GENDERS_NUM];
	double max_outlier[GENDERS_NUM];
	int red_flag;
} cbc_code_t;

class cbc_codes_t {
public:
	std::map<cbc_code_id_type , cbc_code_t> codes;
	std::map<std::string, cbc_code_id_type> code_name_to_code_id;
	std::string text;
	int write (char *path) ;
} ;

typedef std::map<id_type, std::map<date_t, std::map<cbc_code_id_type, double>>> cbc_t;

typedef std::map<id_type, std::vector<date_t>> cbc_dates_t;

typedef struct {
	cbc_dates_t dates;
	int cbc_mode_year;
	int cbc_min_day;
	int cbc_max_day;
} cbc_dates_ex_t;

typedef std::map<std::string, int> params_t;

typedef struct {
	demography_t demography;
	censor_t censor;
	registry_t registry;
	cbc_codes_t cbc_codes;
	cbc_t cbc;
	cbc_dates_ex_t cbc_dates_ex;
	params_t params;
	std::string source;
	int index;
	std::map<int, std::map<int, int>> cnt_born_in_censor_for_year[GENDERS_NUM];
	std::map<int , std::map<int, int>> cnt_crc_born_sick_year[GENDERS_NUM];
	std::map<int , std::map<int, int>> cnt_colon_born_sick_year[GENDERS_NUM];
	std::map<int , std::map<int, int>> cnt_rectum_born_sick_year[GENDERS_NUM];
} data_set_t;

// tools 

//bool is_in_censor(int id, int min_day, int max_day, censor_t& censor);

// functions

int read_demography(char *file_name, demography_t& demography, censor_t& censor);
int read_registry (char *file_name, registry_t& registry);
int read_censor(char *file_name ,censor_t& censor);
int read_cbc_codes(char *file_name, cbc_codes_t& cbc_codes);
int read_cbc_codes(char *file_name, cbc_codes_t& cbc_codes);
int read_cbcs_txt(char *file_name, cbc_codes_t& cbc_codes, cbc_t& cbc);
int convert_cbc_to_cbc_dates( cbc_t &cbc, cbc_dates_ex_t& cbc_dates_ex, cbc_codes_t& cbc_codes );
int read_params(char *file_name, params_t& params);
int write_params( data_set_t &ds, char *path );

int read_data_set( const char* path, const  char* source, data_set_t& ds, int index );

/*			Sorting						*/
struct int_compare {
    bool operator()(const int& a, const int& b) {               
		return (a < b) ;
    }
} ;

struct panel_compare {
	bool operator() (const std::pair<std::vector<int>,int>&  a,
		             const std::pair<std::vector<int>,int>&  b) {
		return (a.second > b.second) ;
	}
} ;

#endif /* __READ_DATA__ */