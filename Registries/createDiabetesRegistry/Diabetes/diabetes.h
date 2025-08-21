#pragma once

#include <vector>
#include <SerializableObject/SerializableObject/SerializableObject.h>
#include <MedProcessTools/MedProcessTools/MedSamples.h>
#include <InfraMed/InfraMed/InfraMed.h>
#include <MedDescribe/MedDescribe/MedDescribe.h>
#include <boost/program_options.hpp>
#include <vector>
#include <map>
#include <Logger/Logger/Logger.h>
#include <fstream>
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

using namespace std;
namespace po = boost::program_options;

// needed prototypes
string printVec(const vector<string> &node_header, const vector<float> &node_value);


//================================================================================================================================
// easy registries wrapper (mainly for serializations)
//================================================================================================================================
template <class T> class Registry : public SerializableObject {
public:
	vector<T> reg;
	ADD_CLASS_NAME(Registry<T>)
	ADD_SERIALIZATION_FUNCS(reg)
};

//=================================================================================================
// Diabetes Registry
//=================================================================================================
class DiabetesRegRec : public SerializableObject {
public:

	int pid = 0;

	// glucose
	vector<int> glu_first_date_above = { 0,0,0,0 }; // first date >=100 >=126 >=150 >=200
	int glu_first_date = 0, glu_last_date = 0, glu_nvals = 0;

	// hba1c
	vector<int> hba1c_first_date_above = { 0,0,0,0 }; // first date >=5.7 >=6.5  >=7.0 >= 8.0
	int hba1c_first_date = 0, hba1c_last_date = 0, hba1c_nvals = 0;

	// drugs
	int first_drugs_date = 0;
	string first_drugs_code = "0";
	int n_drug_records = 0;
	int n_drug_days = 0;

	// read codes
	int first_read_code_date = 0;
	//int first_read_code_name = 0;
	string first_read_code_name = "";
	int n_rc_records = 0;

	// glu/hba1c/drugs 2Y range decision
	vector<int> ghd_healthy = { 0,0 };		// from - to: healthy
	vector<int> ghd_pre = { 0,0 };			// from - to: pre
	vector<int> ghd_diabetic = { 0,0 };		// from - to : diabetic

	// adding read code
	vector<int> rc_healthy = { 0,0 };		// from - to: healthy
	vector<int> rc_pre = { 0,0 };			// from - to: pre
	vector<int> rc_diabetic = { 0,0 };		// from - to: diabetic
	int rc_ignore_censor_bit = 0;

	// general censor
	int censor = 0;


	void print();
	void print_short();

	ADD_CLASS_NAME(DiabetesRegRec)
	ADD_SERIALIZATION_FUNCS(pid, glu_first_date_above, glu_first_date, glu_last_date, glu_nvals,
		hba1c_first_date_above, hba1c_first_date, hba1c_last_date, hba1c_nvals,
		first_drugs_date,first_drugs_code, n_drug_records, n_drug_days, first_read_code_date, first_read_code_name, n_rc_records,
		ghd_healthy, ghd_pre, ghd_diabetic, rc_healthy, rc_pre, rc_diabetic, rc_ignore_censor_bit, censor)

};

//================================================================================================================================
// CKD and overall RENAL DISEASE - registry
//================================================================================================================================
struct CKDRegRec2 : public SerializableObject {
	int pid = 0;
	int ckd_date = 0; // see definition in function 
	int rc_ckd_date = 0; // see definition in function (ckd with rc)
	vector<int> creatinine_first_above ={ 0, 0, 0, 0 }; // first >=1.2,1.4,2.0,3.0 (M) >= 1.0,1.2,2.0,3.0 (F)
	vector<int> creatinine_from_to ={ 0, 0 };			// creatinine dates span
	vector<int> urine_first_above ={ 0, 0 };			// first urine test in medium, first in severe
	vector<int> urine_from_to ={ 0, 0 };				// urine dates span
	vector<int> first_rc ={ 0, 0, 0 };					// rc for ckd, dialisys, transplant
	vector<int> egfr_state_first ={ 0, 0, 0, 0, 0 };	// first date egfr state is 1,2,3,4,5
	vector<int> ckd_state_first ={ 0, 0, 0, 0, 0 };		// first date egfr state is 0,1,2,3,4
	int suspected_dt = 0;								// suspected_dt (dialysis or transplant)
	int n_tests = 0;									// number of creatinine + urine tests
	int censor = 0;										// 2 - not enough tests , 0 - OK

	void print() {
		fprintf(stdout, "CKDReg2 pid %d :: ckd %d rc_ckd %d creat first %d %d %d %d creat %d - %d egfr %d %d %d %d %d ckd_state_first %d %d %d %d %d urine first %d %d urine %d - %d rc %d %d %d suspect_dt %d n_tests %d censor %d\n",
			pid, ckd_date, rc_ckd_date,
			creatinine_first_above[0], creatinine_first_above[1], creatinine_first_above[2], creatinine_first_above[3],
			creatinine_from_to[0], creatinine_from_to[1],
			egfr_state_first[0], egfr_state_first[1], egfr_state_first[2], egfr_state_first[3], egfr_state_first[4],
			ckd_state_first[0], ckd_state_first[1], ckd_state_first[2], ckd_state_first[3], ckd_state_first[4],
			urine_first_above[0], urine_first_above[1],
			urine_from_to[0], urine_from_to[1],
			first_rc[0], first_rc[1], first_rc[2],
			suspected_dt, n_tests, censor);
	}

	void print_short() {
		fprintf(stdout, "CKDReg2 pid %d :: rc_ckd %d censor %d\n", pid, rc_ckd_date, censor);
	}

	ADD_CLASS_NAME(CKDRegRec2)
	ADD_SERIALIZATION_FUNCS(pid, ckd_date, rc_ckd_date, creatinine_first_above, creatinine_from_to,
							urine_first_above, urine_from_to, first_rc, egfr_state_first, ckd_state_first, suspected_dt, n_tests, censor)
};

//================================================================================================================================
// Hypertension Registry
//================================================================================================================================
struct HypertensionRegRec : public SerializableObject {

	int pid = 0;
	int above_mode = 0;			// mode 0: either D or S bp are too big , mode 1: D and S bp are too big
	int first_rc_date = 0;
	int n_rc_recs = 0;
	int first_drug_date = 0;
	int n_drug_records = 0;
	int n_drug_days = 0;
	vector<int> first_bp_above = { 0,0,0 }; // first bp date above 140/90 , 160/100 , 180/100
	int n_bp = 0;
	int bp_first_date = 0;
	int bp_last_date = 0;
	int first_2nd_bad_bp_date = 0; // first bad (>140/90) bp 
	int hypertension_date = 0;
	int censor = 0;

	void print() {
		fprintf(stdout, "HypertensionRegRec pid %d :: mode %d BP %d %d %d n_bp %d bad_bp %d from-to %d %d :: rc %d n_rc %d :: drug %d n_d %d d_days %d :: hyper_date %d :: censor %d\n",
			pid, above_mode, first_bp_above[0], first_bp_above[1], first_bp_above[2], n_bp, first_2nd_bad_bp_date, bp_first_date, bp_last_date,
			first_rc_date, n_rc_recs, first_drug_date, n_drug_records, n_drug_days, hypertension_date, censor);
	}

	void print_short() {
		fprintf(stdout, "HyperRec pid %d :: hyper_date %d censor %d\n", pid, hypertension_date, censor);
	}

	ADD_CLASS_NAME(HypertensionRegRec)
	ADD_SERIALIZATION_FUNCS(pid, above_mode, first_rc_date, first_drug_date, first_bp_above, n_bp, first_2nd_bad_bp_date, hypertension_date, censor)
};

//================================================================================================================================
// Read Code based Registry
//================================================================================================================================
struct RCRegRec : public SerializableObject {
	int pid = 0;
	int first_rc = 0;
	int n_tests = 0;
	int censored = 0; // censored are those that had less than 5 read code 

	void print() {
		fprintf(stdout, "RCRegRec: pid %d first_rc %d n_tests %d censored %d\n", pid, first_rc, n_tests, censored);
	}

	ADD_CLASS_NAME(RCRegRec)
	ADD_SERIALIZATION_FUNCS(pid, first_rc, censored)
};

//=======================================================================================================================
// stat and annual stats related
//=======================================================================================================================
enum StatType {
	n_healthy = 0,
	n_pre = 1,
	n_diab = 2,
	n_pre2d = 3,
	n_h2p = 4,
	n_h2d = 5
};


//...................................................................................................
struct DiabetesStat {
	int n_healthy = 0;
	int n_pre = 0;
	int n_diab = 0;
	int n_pre2d = 0;
	int n_h2p = 0;
	int n_h2d = 0;

	vector<float> node_value;
	vector<string> node_header;

	void print() { MOUT("DiabetesStat:: [%s] :: H: %7d P: %7d D: %7d P2D: %6d H2P: %6d H2D: %6d\n", printVec(node_header, node_value).c_str(), n_healthy, n_pre, n_diab, n_pre2d, n_h2p, n_h2d); }
	void print_csv_header() { MOUT("stat_bucket,healthy,pre,diabetic,pre2d,h2p,h2d\n"); }
	void print_csv() { MOUT("[%s],%d,%d,%d,%d,%d,%d\n", printVec(node_header, node_value).c_str(), n_healthy, n_pre, n_diab, n_pre2d, n_h2p, n_h2d); }
};

//...................................................................................................
struct DiabNephStat {
	int n_no_ckd = 0;
	int n_ckd = 0;
	int n_new_ckd = 0;
};


//================================================================================================================================
// Functions to work with
//================================================================================================================================

//--------------------------------
// Diabetes funcs
//--------------------------------
// general diabetes registry
int get_all_diabetes_reg(const string &rep_name, vector<string> drugs_names, vector<string> read_codes, vector<int> &pid_list, string diag_sig, string params, Registry<DiabetesRegRec> &dr);
int get_diabetes_range_reg(const string &rep_name, const string &f_dreg, const string &f_out);

//--------------------------------
// CKD funcs
//--------------------------------
int get_all_ckd_reg_fixed_thin(const string &rep_name, vector<string> read_codes_fnames, vector<int> &pid_list, string params, Registry<CKDRegRec2> &creg);

//--------------------------------
// Hypertension funcs
//--------------------------------
int get_all_hypertension_reg(const string &rep_name, vector<string> drugs_names, vector<string> read_codes, vector<int> &pid_list, Registry<HypertensionRegRec> &HR);

//--------------------------------
// RC Reg funcs
//--------------------------------
int get_all_rc_reg(const string &rep_name, string read_codes_fname, vector<int> &pid_list, Registry<RCRegRec> &creg);
int create_diabetic_complication_cohort_file(const string name, const string &diab_reg_file, const string &rc_reg_file, const string &fcohort_out);


//---------------------------------------
// Diabetic and general Nephropathy funcs
//---------------------------------------
int create_diabetic_nephropathy_cohort_file(const string &diab_reg_file, const string &ckd_reg_file, const string &fcohort_out, int ckd_state_level);
int create_nephropathy_cohort_file(const string &ckd_reg_file, const string &fcohort_out, int ckd_state_level);


//--------------------------------
// Stat funcs
//--------------------------------

// annual stats for diabetes
int get_yearly_diabetes_stats(const string &f_dreg);
int get_full_diabetes_stats(const string &f_dreg, const string &stat_args, const string &rep, int age_bin);
typedef void(*fieldValueFunction)(const DiabetesRegRec &, map<vector<float>, vector<StatType>> &);

// annual diabetic nephropathy stats
int get_annual_dneph_stats(const string &diab_reg_fname, const string &ckd_reg_fname);

//--------------------------------
// Signal creation funcs
//--------------------------------
int get_proteinuria_thin(const string &rep_fname, const string &fout);


//--------------------------------
// Utils funcs
//--------------------------------
string printVec(const vector<string> &node_header, const vector<float> &node_value);
int read_RC_from_file(const string &fname, vector<string> &RC_list);


//===================================
// Joining the MedSerialize Wagon
//===================================
MEDSERIALIZE_SUPPORT(DiabetesRegRec);
MEDSERIALIZE_SUPPORT(CKDRegRec2);
MEDSERIALIZE_SUPPORT(HypertensionRegRec);
MEDSERIALIZE_SUPPORT(RCRegRec);
MEDSERIALIZE_SUPPORT(Registry<DiabetesRegRec>);
MEDSERIALIZE_SUPPORT(Registry<CKDRegRec2>);
MEDSERIALIZE_SUPPORT(Registry<HypertensionRegRec>);
MEDSERIALIZE_SUPPORT(Registry<RCRegRec>);


//=======================================================================================
// templated functions
//=======================================================================================
template <class T> int print_reg(string fname, string print_mode) {
	Registry<T> Reg;
	if (Reg.read_from_file(fname) < 0) return -1;
	if (print_mode == "full")
		for (auto &r : Reg.reg) r.print();
	else
		for (auto &r : Reg.reg) r.print_short();
	return 0;
}