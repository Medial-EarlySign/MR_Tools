#include <time.h>

#include "stdlib.h"
#include "stdio.h"
#include "string.h"
#include "math.h"
#include <assert.h>

#include <map>
#include <vector>
#include <string>
#include <algorithm>

using namespace std ;

#define DATA_TYPE 1 // 0 = Maccabi ; 1 = Thin; 2 = MedMining

#define BUFFER_SIZE    4096
#define MAX_STRING_LEN 1024
#define REGISTRY_NFIELDS  19
#define REGISTRY_CANCER_FIELD 14
#define REGISTRY_DATE_FIELD 5
#define REGISTRY_ID_FIELD 0
#define NCRC_TYPES 5

// Files
char reg_files[3][MAX_STRING_LEN] = {"\\\\server\\Data\\macabi5\\medialpopulationcancerstages.csv","Thin.Registry", "MedMining.Registry"} ;
char censor_files[3][MAX_STRING_LEN] = {"\\\\server\\Data\\macabi5\\id.status","Thin.Censor", "MedMining.Censor"} ;
char dem_files[3][MAX_STRING_LEN] = {"Maccabi.Demographics.txt","Thin.Demographics.txt", "MedMining.Demographics"} ;
char cbc_files[3][MAX_STRING_LEN] = {"InternalMaccabi.Data.txt","Thin.Data.txt", "MedMining.CBC_Matrix"} ;

// Cancer
char crc_types[NCRC_TYPES][MAX_STRING_LEN] = {"Digestive Organs,Digestive Organs,Colon","Digestive Organs,Digestive Organs,Rectum","cancer,crc,colon",												
											  "cancer,crc,rectum","cancer,crc,rectum;colon"} ;

char gender_names[2][MAX_STRING_LEN] = {"Male","Female"} ;

// Tests
/*
#define NTESTS 12
double resolutions[NTESTS] = {10,20,1,10,5,0.1,10,10,10,10,10} ;
char test_names[NTESTS][MAX_STRING_LEN] = {"Hemoglobin","Hematocrit","RBC","MCV","MCH","MCHC_M","Platelets","Eosinophils","Neutrophils","Lymphocytes","Monocytes","Basophils"} ;
int test_codes[2][NTESTS] = {{50223,50224,5041,50225,50226,50227,50229,50230,50237,50238,50239,50241},{4,5,1,6,7,8,10,11,16,20,17,18}} ;
double internal_factor[2] = {0.8,1.0} ;
*/

#define NTESTS 20
double resolutions[NTESTS] = {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1} ;
char test_names[NTESTS][MAX_STRING_LEN] = {"RBC","WBC","MPV","Hemoglobin","Hematocrit","MCV","MCH","MCHC_M","RDW","Platelts","Eos#","Neu%","Mon%","Eos%","Bas%",
									       "Neu#","Mon#","Bas#","Lym%","Lym#"} ;
int test_codes[3][NTESTS] = {{5041,5048,50221,50223,50224,50225,50226,50227,50228,50229,50230,50232,50234,50235,50236,50237,50239,50241,50233,50238},
						     {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20}, {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20} } ;
double internal_factor[3] = {0.8,1.0, 1.0} ;

// Classes
/*          Status class				*/
class status {
public:
	int date ;
	int stat ;
	int reason ;
} ;

/*			Registry class				*/
class reg_entry {
public:
	int date ;
	int type ;
} ;

/*			Demography class				*/
class dem {
public:
	int byear ;
	char gender ;
} ;

/*			CBCS							*/
typedef map<int,map<int, map<int, double> > > cbcs_data ;


/*			Date handling data			*/
int days2month[] = {0,31,59,90,120,151,181,212,243,273,304,334} ;

/*			Function Declarations		*/
int get_days(int date) ;
int read_registry (char *file, map<int,reg_entry>& registry) ;
int read_censor(char *file_name, map<int,status>& status) ;
int read_demography(char *file_name, map<int,dem>& demography) ;
int read_cbcs(char *file_name, cbcs_data& cbcs) ;


/*			Sorting						*/
/*			Comparison for int sort	*/
struct int_compare {
    bool operator()(const int& a, const int& b) {               
		return (a < b) ;
    }
} ;

struct panel_compare {
	bool operator() (const pair<vector<int>,int>&  a, const pair<vector<int>,int>&  b) {
		return (a.second > b.second) ;
	}
} ;