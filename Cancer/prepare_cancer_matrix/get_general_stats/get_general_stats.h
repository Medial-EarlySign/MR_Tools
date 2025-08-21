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

#define BUFFER_SIZE    4096
#define MAX_STRING_LEN 1024
#define REGISTRY_NFIELDS  19
#define REGISTRY_CANCER_FIELD 14
#define REGISTRY_DATE_FIELD 5
#define REGISTRY_ID_FIELD 0
#define NCRC_TYPES 5

char gender_names[2][MAX_STRING_LEN] = {"Male","Female"} ;

// Tests
#define NTESTS 12
double resolutions[NTESTS] = {10,20,1,10,5,0.1,10,10,10,10,10} ;
char test_names[NTESTS][MAX_STRING_LEN] = {"Hemoglobin","Hematocrit","RBC","MCV","MCH","MCHC_M","Platelets","Eosinophils","Neutrophils","Lymphocytes","Monocytes","Basophils"} ;
int test_codes[2][NTESTS] = {{50223,50224,5041,50225,50226,50227,50229,50230,50237,50238,50239,50241},{4,5,1,6,7,8,10,11,16,20,17,18}} ;
double internal_factor[2] = {0.8,1.0} ;

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
int read_demography(char *file_name, map<int,dem>& demography) ;
int read_cbcs(char *file_name, cbcs_data& cbcs, int data_type) ;


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