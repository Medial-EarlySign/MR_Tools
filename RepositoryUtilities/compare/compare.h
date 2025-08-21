#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "InfraMed/InfraMed/Utils.h"

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

#include <boost/program_options.hpp>
#include <boost/algorithm/string/trim_all.hpp>
#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string/replace.hpp>
#include <unordered_set>

using namespace std ;
namespace po = boost::program_options;

#define MIN_HGB_PER_DAY 10
#define MISSING_VAL -99.0
#define EPSILON 1e-4
#define MAX_ZEROS_IN_PANEL 3

// Signals to check
char signalsToCheck[][256] = {"RBC","WBC","MPV","Hemoglobin","Hematocrit","MCV","MCH","MCHC-M","RDW","Platelets","Eosinophils#","Neutrophils%","Lymphocytes%","Monocytes%","Eosinophils%","Basophils%","Neutrophils#",
	"Lymphocytes#","Monocytes#","Basophils#","Albumin","Ca","Cl","Cholesterol","Creatinine","HDL","LDL","K+","Na","Triglycerides","Urea","Uric_Acid","Ferritin","BMI"} ;
int nSignalsToCheck = sizeof(signalsToCheck)/256 ;

struct medCounter {
	long long total ;
	map<pair<string,string>,long long> counts ;
} ;

struct allInfo {
	string origRepName,newRepName ;
	bool skipRegistry,skipSignals ;
	bool skipCounts ;

	int origMaxByear ;
	int origHgFirstDate,origHgLastDate ;

	FILE *reportFile ;
	FILE *logFile ;

	vector<int> commonIds ;

}  ;

// Read running parameters
int read_run_params(int argc,char **argv,  allInfo& info) ;

// Compare repositories
int compareRep(MedRepository& origRep,MedRepository& newRep, allInfo& info) ;

void compareIdsList(MedRepository& origRep,MedRepository& newRep, allInfo& info) ;
void compareDemographics(MedRepository& origRep,MedRepository& newRep, allInfo& info) ;
void compareRegistry(MedRepository& origRep,MedRepository& newRep, allInfo& info) ;
void compareSignals(MedRepository& origRep,MedRepository& newRep, allInfo& info) ;
void compareCounts(MedRepository& origRep,MedRepository& newRep, allInfo& info) ;
int checkNewId(MedRepository& rep, int id, allInfo& info) ;
void examineOrig(MedRepository& rep, allInfo& info) ;
void newRepTests(MedRepository& rep, allInfo& info)  ;