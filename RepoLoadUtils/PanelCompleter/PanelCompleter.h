#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "Logger/Logger/Logger.h"
#include "InfraMed/InfraMed/Utils.h"
#include "MedUtils/MedUtils/MedMedical.h"
#include <stdio.h>

#include <stdlib.h>
#include <stdarg.h>
#include <cmath>
#include <boost/algorithm/string.hpp>
#include <boost/program_options.hpp>

using namespace std ;
namespace po = boost::program_options;

#define STRING_LEN 128

char panel[][STRING_LEN] = {"RBC","WBC","Hematocrit","Hemoglobin","MCV","MCH","MCHC-M","Eosinophils#","Eosinophils%","Neutrophils#","Neutrophils%",
	"Lymphocytes#","Lymphocytes%","Monocytes#","Monocytes%","Basophils#","Basophils%", "MPV", "Platelets_Hematocrit", "Platelets",
	"HDL_over_LDL", "LDL_over_HDL", "Cholesterol_over_HDL", "HDL_over_Cholesterol", "HDL_over_nonHDL",
	"NonHDLCholesterol", "LDL", "HDL", "Cholesterol", "Triglycerides",
	"Bicarbonate", "Cl", "Na", "Creatinine", "eGFR_MDRD", "eGFR_CKD_EPI", "Height", "Weight", "BMI"} ;
int panel_size = sizeof(panel)/STRING_LEN ;

int read_run_params(int argc,char **argv, po::variables_map& vm) ;
int process_id(MedRepository& rep, int id, map<string,float>& res, map<string, float>& fac, FILE *out_fp, FILE *err_fp, FILE *exist_fp, map<string,int>& completions, map<string,int>& mismatches, map<string,int>& matches)  ;
int triplet_complete(int id, int date, map<string,float>& cur_panel, float factor, const string& xname, const string& yname, const string& zname, const string& type,
					 map<string,float>& res, map<string, float>& fac, map<string,int>& completions, map<string,int>& mismatches, map<string,int>& matches, map<string,int>& attempted, FILE *out_fp, FILE *err_fp)  ;
int read_resolutions(string file_name,map<string, string>& thin_to_medial, map<string,float>& res, map<string, float>& fac) ;
int read_resolutions_new(string file_name, map<string, float>& res, map<string, float>& fac);
