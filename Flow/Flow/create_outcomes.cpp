//
// containing a few examples to create outcomes
//

#include "Flow.h"
#include "Logger/Logger/Logger.h"
#include "MedUtils/MedUtils/MedGenUtils.h"
#include "MedFeat/MedFeat/MedOutcome.h"
#include <MedStat/MedStat/MedPerformance.h>
#include <MedUtils/MedUtils/MedGlobalRNG.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string.hpp>


#include <random>
#include <algorithm>

using namespace std;
using namespace boost;

//-------------------------------------------------------------------------------------------------------------------
struct SigOutcomeParams {
	string sig_name;
	int ncateg;			// 0 for regression, >1 for classification
	int gender_mask;
	int train_mask;
	float bound1;
	float bound2;
	float min_age;
	float max_age;
	int direction; // 1 risk_above , -1 risk_below
	int outcome_days;
	int sampling_days;
	int nsamp;	// take nsamp samples per pid if possible (for outcome cases)
	int min_date;
	int max_date;
	int ntimes;				// ntimes above bound2 to become a case positive
	int ntimes_in_arow;     // ntimes in a row above bound2 to become a case positive
	// regression related
	int from_days;
	int to_days;
	float min_val;
	float max_val;
	vector<string> clock_sigs;	// defining the relavant points in time for prediction (example clock_sigs=Creatinine|Hemoglobin|Glucose )

	string mode;

	SigOutcomeParams() {
		mode = "with_gap"; sig_name = ""; gender_mask = 3; train_mask = 1; bound1 = 0; bound2 = 0; min_age = 0; max_age = 200;
		direction = 1; outcome_days = 730; sampling_days = 365; nsamp = 5; min_date = 19900101; max_date = 20200101;
		ntimes = 1; ntimes_in_arow = 1; ncateg = 2; min_val = -1; from_days = -1;
	}
	void init_from_string(const string &in_params);
};


//-------------------------------------------------------------------------------------------------------------------
struct SigFilterElement {
	// input
	string sig_name;
	int history_flag;
	int last1_flag;
	float min_val;
	float max_val;
	string diabetes_group;

	// helpers
	int sid;

	SigFilterElement() { sig_name = ""; history_flag = 0; last1_flag = 0; min_val = -99999; max_val = 999999; diabetes_group = ""; sid = -1; }

	void init_from_string(const string &in_s);
};

struct SigFilterParams {
	vector<SigFilterElement> filters;
	vector<string>	sigs;

	void init_from_string(const string &in_s);
};

//-------------------------------------------------------------------------------------------------------------------
//===================================================================================================================
void SigFilterElement::init_from_string(const string &in_s)
{
	// typical examples:
	// sig=BMI,last1,30,999
	// sig=No_Diabetes // or Pre_Diabetes, or Diabetic // These are for diabetes groups
	vector<string> fields;
	split(fields, in_s, boost::is_any_of(",;:="));

	if (fields.size() == 5) {
		sig_name = fields[1];
		if (fields[2] == "last1") last1_flag = 1;
		if (fields[2] == "hist" || fields[2] == "history") history_flag = 1;
		min_val = stof(fields[3]);
		max_val = stof(fields[4]);
	}

	if (fields.size() == 2) {
		if (fields[1] == "No_Diabetes" || fields[1] == "Pre_Diabetes" || fields[1] == "Diabetes")
		{
			diabetes_group = fields[1]; sig_name = "Diagnosis";
		}
	}
}

//===================================================================================================================
void SigFilterParams::init_from_string(const string &in_s)
{
	vector<string> fields;
	split(fields, in_s, boost::is_any_of(";"));

	for (auto &s : fields) {
		SigFilterElement sfe;
		sfe.init_from_string(s);
		filters.push_back(sfe);
		sigs.push_back(sfe.sig_name);
	}

	std::sort(sigs.begin(), sigs.end());
	unordered_set<string> res(sigs.begin(), sigs.end());
	sigs.clear();
	sigs.insert(sigs.begin(), res.begin(), res.end());
}


//===================================================================================================================
// returns 1: passed filter , 0: should be filtered
int single_filter_pid_date(MedRepository &rep, SigFilterElement &sfe, int pid, int date)
{
	if (sfe.sig_name != "Diagnosis") {
		int len;
		SDateVal *sdv = rep.get_before_date(pid, sfe.sig_name, date + 1, len);
		if (len == 0) return 0; // without any information we filter the time point.
		if (sfe.last1_flag && (sdv[len - 1].val < sfe.min_val || sdv[len - 1].val >= sfe.max_val)) return 0;
		if (sfe.history_flag) {
			for (int i = 0; i < len; i++)
				if (sdv[i].val < sfe.min_val || sdv[i].val >= sfe.max_val) return 0;
		}
	}
	else {
		if (sfe.diabetes_group != "") {
			UniversalSigVec sdv;
			rep.uget(pid, sfe.sig_name, sdv);

			int last_h = 0, first_pre = 0, first_diabetic = 0;
			for (int i = 0; i < sdv.len; i++) {
				if ((int)sdv.Val(i) == rep.dict.id(rep.dict.section_id("Diagnosis"), "Last_No_Diabetes")) last_h = sdv.Time(i);
				if ((int)sdv.Val(i) == rep.dict.id(rep.dict.section_id("Diagnosis"), "Pre_Diabetes")) first_pre = sdv.Time(i);
				if ((int)sdv.Val(i) == rep.dict.id(rep.dict.section_id("Diagnosis"), "Diabetes")) first_diabetic = sdv.Time(i);
			}

			if (sfe.diabetes_group == "No_Diabetes" && date > last_h) return 0;
			if (sfe.diabetes_group == "Pre_Diabetes") {
				if (date >= first_pre && (first_diabetic == 0 || date < first_diabetic))
					return 1;
				else
					return 0;
			}
			if (sfe.diabetes_group == "Diabetes" && (first_diabetic == 0 || date < first_diabetic)) return 0;

		}
	}

	return 1;
}

// OLD CODE NOT NEEDED
#if 0
//===================================================================================================================
int filter_med_outcome(MedRepository &rep, SigFilterParams &sfp, MedOutcome &mout_in, MedOutcome &mout_filtered)
{
	mout_filtered = mout_in;
	mout_filtered.out.clear();

	for (auto &orec : mout_in.out) {
		int keep = 1;
		//MLOG("orec: pid %d date %d categ %d\n", orec.pid, orec.date, (int)orec.categ);
		for (auto &sfe : sfp.filters) {
			int rc = single_filter_pid_date(rep, sfe, orec.pid, orec.date);
			//MLOG("orec: pid %d date %d categ %d   sfe: %s %s rc: %d \n", orec.pid, orec.date, (int)orec.categ, sfe.sig_name.c_str(), sfe.diabetes_group.c_str(), rc);
			if (rc == 0) {
				keep = 0;
				break;
			}
		}
		if (keep)
			mout_filtered.out.push_back(orec);
	}

	return 0;
}
#endif

//===================================================================================================================
int sdv_get_test_and_outcome(SDateVal *&sdv, int &len, SigOutcomeParams &sop, int &i_mid, int &i_high)
{
	i_high = -1;
	i_mid = -1;
	if (sop.direction > 0)
		for (int i = 0; i < len; i++) {
			if (sdv[i].val >= sop.bound1 && i_mid < 0) i_mid = i;
			if (i < len - sop.ntimes_in_arow) {
				int n_crossed = 0;
				for (int j = 0; j < sop.ntimes_in_arow; j++)
					if (sdv[i + j].val >= sop.bound2) n_crossed++;
				if (n_crossed == sop.ntimes_in_arow) {
					i_high = i;
					break;
				}
			}
		}
	else
		for (int i = 0; i < len; i++) {
			if (sdv[i].val <= sop.bound1 && i_mid < 0) i_mid = i;
			if (i < len - sop.ntimes_in_arow) {
				int n_crossed = 0;
				for (int j = 0; j < sop.ntimes_in_arow; j++)
					if (sdv[i + j].val <= sop.bound2) n_crossed++;
				if (n_crossed == sop.ntimes_in_arow) {
					i_high = i;
					break;
				}
			}
		}

	return 0;

}

//===================================================================================================================
int sdv_shrink_from_date(SDateVal *&sdv, int &len, int test_date, int min_days, int max_days)
{
	if (len == 0)
		return 0;

	int orig_len = len;
	SDateVal *orig_sdv = sdv;

	int test_days = date_to_days(test_date);

	// testing from below
	for (int i = 0; i < orig_len; i++) {
		int date = orig_sdv[i].date;
		int days = test_days - date_to_days(date);
		if (days < min_days || days > max_days) {
			sdv++;
			len--;
		}
		else
			break;
	}

	// testing from above
	if (len > 0) {
		orig_len = len;
		orig_sdv = sdv;
		for (int i = orig_len - 1; i >= 0; i--) {
			int date = orig_sdv[i].date;
			int days = test_days - date_to_days(date);
			if (days < min_days || days > max_days)
				len--;
			else
				break;
		}

	}

	return len;
}

//===================================================================================================================
int sdv_shrink(SDateVal *&sdv, int &len, int byear, float min_age, float max_age, int min_date, int max_date)
{
	if (len == 0)
		return 0;

	if (len == 1) { // since we need at least one future test to "prove" we are either positive or control, we need at least 2 samples
		len = 0;
		return 0;
	}

	int orig_len = len;
	SDateVal *orig_sdv = sdv;

	//MLOG("len %d byear %d min_age %f max_age %f min_date %d max_date %d\n", len, byear, min_age, max_age, min_date, max_date);
	// testing from below
	for (int i = 0; i < orig_len; i++) {
		int date = orig_sdv[i].date;
		float age = get_age(orig_sdv[i].date, byear);
		if (age < min_age || age > max_age || date < min_date || date > max_date) {
			sdv++;
			len--;
		}
		else
			break;
	}

	//MLOG("len = %d\n", len);
	// testing from above
	if (len > 0) {
		orig_len = len;
		orig_sdv = sdv;
		for (int i = orig_len - 1; i >= 0; i--) {
			int date = orig_sdv[i].date;
			float age = get_age(orig_sdv[i].date, byear);
			if (age < min_age || age > max_age || date < min_date || date > max_date)
				len--;
			else
				break;
		}

	}

	return len;
}

//===================================================================================================================
int sdv_sampler(SDateVal *sdv, int len, int days_spread, int max_samples, vector<int> &inds)
{
	inds.clear();
	if (len == 0)
		return 0;

	// all sampling groups start at day 0 of date_to_days
	vector<int> groups(len + 1);
	for (int i = 0; i < len; i++)
		groups[i] = date_to_days(sdv[i].date) / days_spread;

	groups[len] = groups[len - 1] + 1; // artificial last group to make sure we hangle all cases

	// choose one random index to each group
	int prev_group = -1;
	int group_size = 0;
	for (int i = 0; i <= len; i++) {
		if (prev_group >= 0 && groups[i] != prev_group) {
			// choose a random index
			//MLOG("prev_group %d group_size %d i %d len %d first date %d last date %d\n", prev_group, group_size, i, len ,sdv[i-group_size].date, sdv[i-1].date);
			int r_ind = rand_N(group_size);
			inds.push_back(i - 1 - r_ind);
			group_size = 0;
		}
		group_size++;
		prev_group = groups[i];
	}

	if (inds.size() > max_samples) {
		shuffle(inds.begin(), inds.end(), globalRNG::get_engine());
		inds.resize(max_samples);
		sort(inds.begin(), inds.end());
	}

	return 0;
}

//===================================================================================================================
void SigOutcomeParams::init_from_string(const string &in_params)
{
	vector<string> fields;
	split(fields, in_params, boost::is_any_of(",;:="));

	for (int i = 0; i < fields.size(); i++) {

		if (fields[i] == "sig") { i++; sig_name = fields[i]; }
		if (fields[i] == "gender") { i++; gender_mask = stoi(fields[i]); }
		if (fields[i] == "train") { i++; train_mask = stoi(fields[i]); }
		if (fields[i] == "bound1") { i++; bound1 = stof(fields[i]); }
		if (fields[i] == "bound2") { i++; bound2 = stof(fields[i]); }
		if (fields[i] == "min_age") { i++; min_age = stof(fields[i]); }
		if (fields[i] == "max_age") { i++; max_age = stof(fields[i]); }
		if (fields[i] == "risk_above") { direction = 1; }
		if (fields[i] == "risk_below") { direction = -1; }
		if (fields[i] == "outcome_days") { i++; outcome_days = stoi(fields[i]); }
		if (fields[i] == "sampling_days") { i++; sampling_days = stoi(fields[i]); }
		if (fields[i] == "min_date") { i++; min_date = stoi(fields[i]); }
		if (fields[i] == "max_date") { i++; max_date = stoi(fields[i]); }
		if (fields[i] == "nsamp") { i++; nsamp = stoi(fields[i]); }
		if (fields[i] == "ntimes") { i++; ntimes = stoi(fields[i]); }
		if (fields[i] == "ntimes_in_arow") { i++; ntimes_in_arow = stoi(fields[i]); }
		if (fields[i] == "mode") { i++; mode = fields[i]; }
		if (fields[i] == "ncateg") { i++; ncateg = stoi(fields[i]); }
		if (fields[i] == "from_days") { i++; from_days = stoi(fields[i]); }
		if (fields[i] == "to_days") { i++; to_days = stoi(fields[i]); }
		if (fields[i] == "min_val") { i++; min_val = stof(fields[i]); }
		if (fields[i] == "max_val") { i++; max_val = stof(fields[i]); }
		if (fields[i] == "clock_sigs") {
			i++;
			split(clock_sigs, fields[i], boost::is_any_of("|"));
		}


	}

}