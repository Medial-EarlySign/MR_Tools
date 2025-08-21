#define _CRT_SECURE_NO_WARNINGS

#include "Flow.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/MedPidRepository.h"
#include "MedUtils/MedUtils/MedGenUtils.h"
#include "MedStat/MedStat/MedStat.h"
#include "boost/date_time/gregorian/gregorian.hpp"
#include "MedAlgo/MedAlgo/BinSplitOptimizer.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include "MedStat/MedStat/MedCleaner.h"
#include <omp.h>
#include <chrono>

#include "Logger/Logger/Logger.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
extern MedLogger global_logger;

class cleaning_stats {
public:
	int total_count = 0;
	int total_count_non_zero = 0;
	int total_count_after_clean = 0;
	int pids_filtered_from = 0; //pids that passed filter without filtering
	int total_pids = 0;
	int total_filtered_non_zero = 0; //pids that pass filter without filtering or zero count

};

// old implementation funcs
void collect_values(MedRepository &rep, string &sig_name, vector<float> &vals, int gender, int age_min, int age_max, int date_min, int date_max, int month);
int describe_signal_general(MedRepository &rep, string &sig_name, int age_min, int age_max, int date_min, int date_max);
int describe_signal_stratify(MedRepository &rep, string &sig_name, int age_min, int age_max, int date_min, int date_max);
void collect_values(MedRepository &rep, string &sig_name, vector<float> &vals, int gender, int age_min, int age_max, int date_min, int date_max);


//=============================================================================================================================
int collect_values_mhs(MedRepository &rep, int sid, int gender, int age_min, int age_max, int date_min, int date_max, vector<float> &vals)
{
	vals.clear();
	if (rep.sigs.Sid2Info[sid].type != T_DateVal) {
		MERR("collect_values() ERROR: supporting only SDateVal format params\n");
		return -1;
	}

	string sname = rep.sigs.name(sid);
	vector<int> pids;
	rep.get_pids_with_sig(sname, pids);

	int g_sid = rep.sigs.sid("GENDER");
	int b_sid = rep.sigs.sid("BYEAR");

	for (auto pid : pids) {
		int p_gender = medial::repository::get_value(rep, pid, g_sid);
		int p_byear = medial::repository::get_value(rep, pid, b_sid);
		if (p_gender < 0 || p_byear < 0) continue;

		UniversalSigVec sdv;
		rep.uget(pid, sid, sdv);

		if (sdv.len > 0) {
			if (!(gender&p_gender)) continue;

			for (int i = 0; i < sdv.len; i++) {

				if (age_min > 0) {
					int age = (int)get_age(sdv.Time(i), p_byear);
					if (age < age_min || age >= age_max) continue;
				}

				if ((date_min > 0 && sdv.Time(i) < date_min) || sdv.Time(i) >= date_max) continue;

				vals.push_back(sdv.Val(i));
			}
		}
	}

	return 0;
}

//===============================================================================================================================
int FlowSigStat::get_stats_mhs(MedRepository &rep, string &sig_name)
{
	// making sure needed sigs from rep are loaded
	vector<string> sigs = { "GENDER","BYEAR" };
	sigs.push_back(sig_name);
	if (rep.load(sigs) < 0) {
		MERR("FlowSigStat::get_stats ERROR: can't load sigs for rep %s\n", rep.config_fname.c_str());
		return -1;
	}

	sname = sig_name;
	sid = rep.sigs.sid(sname);

	// for each slicing option we first create a vector of values and then get the stats for it

	// gender slices

	return 0;
}



//=============================================================================
// Print basic statistics on a signal in an mhs or thin like repository -
// That is a repository with dates/values for signals, and given GENDER and BYEAR
int describe_mhs_thin(string &rep_fname, string &sig_name)
{
	MERR("describe_mhs_thin() is not implemented in FLow !!!\n");
	return -1;
}

//-------------------------------------------------------------------------
// Currently using old code, to be replaced with better infrastructure in the future
int flow_describe_sig(string &rep_fname, string &sig_name, int age_min, int age_max, int date_min, int date_max)
{
	int rc = 0;

	MedRepository rep;

	// making sure needed sigs from rep are loaded
	vector<string> sigs = { "GENDER","BYEAR" };
	sigs.push_back(sig_name);
	vector<int> pids;
	if (rep.read_all(rep_fname, pids, sigs) < 0) {
		MERR("FlowSigStat::get_stats ERROR: can't load sigs for rep %s\n", rep.config_fname.c_str());
		return -1;
	}

	rc = describe_signal_general(rep, sig_name, age_min, age_max, date_min, date_max);
	rc += describe_signal_stratify(rep, sig_name, age_min, age_max, date_min, date_max);

	return rc;
}

int flow_describe_all(string &rep_fname, string signals_fname, int age_min, int age_max, int date_min, int date_max)
{
	MedRepository rep;

	ifstream inf(signals_fname);
	if (!inf) {
		fprintf(stderr, "can't open file %s for read\n", signals_fname.c_str());
		throw exception();
	}
	fprintf(stderr, "reading from: %s\n", signals_fname.c_str());

	string curr_line;
	vector<string> sigs;
	while (getline(inf, curr_line)) {
		if (curr_line[curr_line.size() - 1] == '\r')
			curr_line.erase(curr_line.size() - 1);
		sigs.push_back(curr_line);
	}
	fprintf(stderr, "age_min: %d, age_max: %d, date_min: %d, date_max: %d\n", age_min, age_max, date_min, date_max);
	fprintf(stderr, "read %d lines from: %s\n", (int)sigs.size(), signals_fname.c_str());
	inf.close();

	vector<int> pids;
	vector<string> basic_sigs = { "BYEAR", "GENDER", "TRAIN" };
	vector<string> signals;
	signals.insert(signals.end(), basic_sigs.begin(), basic_sigs.end());
	signals.insert(signals.end(), sigs.begin(), sigs.end());

	if (rep.read_all(rep_fname, pids, signals) < 0) {
		MERR("can't load sigs for rep %s\n", rep.config_fname.c_str());
		return -1;
	}

	MOUT("signal,gender,age_min,age_max,total,cleaned,non-zeros,mean,std,q1,q2,q3\n");
	for (string sig_name : sigs) {
		for (int gender : {0, 1, 2}) {
			vector<float> samples;
			collect_values(rep, sig_name, samples, gender, age_min, age_max, date_min, date_max);
			MedCleaner c_samples;
			c_samples.get_cleaning_params(samples);
			//c_samples.get_limits_iteratively(samples);

			c_samples.clear(samples);
			c_samples.calculate(samples);
			MOUT("%s,%d,%d,%d,%d,%d,%d,%6.2f,%6.2f,%6.2f,%6.2f,%6.2f\n", sig_name.c_str(), gender, age_min, age_max, samples.size(), c_samples.n, c_samples.n - c_samples.nzeros,
				c_samples.mean, c_samples.sdv, c_samples.q1, c_samples.median, c_samples.q3);
		}
	}

	return 0;
}
//================================================================================================================
//================================================================================================================
//================================================================================================================
//================================================================================================================
//================================================================================================================
//============== Some old ugly code to be replaced with better FlowSigStat infrastructure ========================
//================================================================================================================
//================================================================================================================
//================================================================================================================
//================================================================================================================
//================================================================================================================

// 
// collect values according to
// gender - 0: both 1: male 2: female
// age_min,age_max - age group
// date_min,date_max - dates to take from
//
//........................................................................................................................................
void collect_values(MedRepository &rep, string &sig_name, vector<float> &vals, int gender, int age_min, int age_max, int date_min, int date_max)
{
	UniversalSigVec sdv;
	int sid = rep.sigs.Name2Sid[sig_name];
	int byear_id = rep.sigs.Name2Sid["BYEAR"];
	int gender_id = rep.sigs.Name2Sid["GENDER"];
	int train_id = rep.sigs.Name2Sid["TRAIN"];

	for (int i = 0; i < rep.index.pids.size(); i++) {

		rep.uget(rep.index.pids[i], sid, sdv);
		if (sdv.len == 0) continue;
		int len = sdv.len;
		int sdv_i = 0;

		int byear = medial::repository::get_value(rep, rep.index.pids[i], byear_id);
		int gender_val = medial::repository::get_value(rep, rep.index.pids[i], gender_id);
		int train_val = medial::repository::get_value(rep, rep.index.pids[i], train_id);
		if (train_val < 0) {
			train_val = 1;
			MERR("NO TRAIN for pid %d\n", rep.index.pids[i]);
		}

		if (byear > 0 && gender_val > 0 && train_val > 0 && (train_val != 2) && (gender == GENDER_BOTH || gender == gender_val)) {
			//if ((sdv = (SDateVal *)rep.get(rep.index.pids[i], sig_name, len)) != NULL) {
			if (1) { //(sdv = (SDateVal *)rep.get(rep.index.pids[i], sig_name, len)) != NULL) {
				while (len > 0 && sdv.Time(sdv_i) < date_min) { ++sdv_i; --len; }
				while (len > 0 && sdv.Time(len - 1) > date_max) { --len; }
				while (len > 0 && get_age(sdv.Time(sdv_i), byear) < age_min) { ++sdv_i; --len; }
				while (len > 0 && get_age(sdv.Time(len - 1), byear) > age_max) { --len; }
				if (len > 0) {
					int k = rand_N(len);
					float age = get_age(sdv.Time(k), byear);
					if (age >= age_min && age <= age_max) {
						vals.push_back(sdv.Val(k));
					}
				}
			}
		}
	}
	//MLOG("Collected %d values for sig %s ages %f-%f date %d-%d\n", (int)vals.size(), sig_name.c_str(), min_age, max_age, date_min, date_max);
}

//====================================================================================
int describe_signal_general(MedRepository &rep, string &sig_name, int age_min, int age_max, int date_min, int date_max)
{
	// count values
	int n_tot[3] = { 0,0,0 };
	int n_with_sig[3] = { 0,0,0 };
	int nvals_all[3] = { 0,0,0 };
	int nvals_diff_days[3] = { 0,0,0 };
	long long dist_between[3] = { 0,0,0 };
	int n_dist_between[3] = { 1,1,1 };
	int i, j, lend;
	int gender;
	vector<int> age_groups[3];
	age_groups[0].assign(200, 0);
	age_groups[1].assign(200, 0);
	age_groups[2].assign(200, 0);

	int byear_id = rep.sigs.Name2Sid["BYEAR"];
	int gender_id = rep.sigs.Name2Sid["GENDER"];


	MLOG("Describe general : going over %d pids\n", rep.index.pids.size());
	for (i = 0; i < rep.index.pids.size(); i++) {
		gender = medial::repository::get_value(rep, rep.index.pids[i], gender_id);
		if (gender < 0) {
			MLOG("pid %d , gender is missing\n", rep.index.pids[i]);
			continue;
		}
		if (gender > 2) {
			MLOG("pid %d , gender is unknown\n", rep.index.pids[i]);
			continue;
		}
		n_tot[0]++;
		n_tot[gender]++;

		UniversalSigVec sdv;
		rep.uget(rep.index.pids[i], sig_name, sdv);
		//MLOG("###i=%d pid %d len %d\n", i, rep.index.pids[i], len);
		if (sdv.len == 0) continue;
		//MLOG("i=%d pid %d\n", i, rep.index.pids[i]);
		int byear = medial::repository::get_value(rep, rep.index.pids[i], byear_id);
		if (byear < 0) {
			MLOG("pid %d , byear is missing\n", rep.index.pids[i]);
		}

		nvals_all[0] += sdv.len;
		nvals_all[gender] += sdv.len;
		lend = 0;

		for (j = 0; j < sdv.len; j++) {
			if (j == 0)
				lend++;
			else if (sdv.Time(j - 1) != sdv.Time(j)) {
				lend++;
				int d = date_to_days(sdv.Time(j)) - date_to_days(sdv.Time(j - 1));
				dist_between[0] += d;
				n_dist_between[0]++;
				dist_between[gender] += d;
				n_dist_between[gender]++;
			}
			int age = (int)get_age(sdv.Time(j), byear);
			//			if (age < 35) age = 35;
			if (age < 0) age = 0;
			if (age > 89) age = 89;
			//			age = (age-35)/5;
			age_groups[0][age]++;
			age_groups[gender][age]++;
		}
		nvals_diff_days[0] += lend;
		nvals_diff_days[gender] += lend;
		if (sdv.len > 0) {
			n_with_sig[0]++;
			n_with_sig[gender]++;
		}


	}

	MLOG("Describe general : After loop on %d pids\n", rep.index.pids.size());
	for (j = 0; j < 3; j++) {
		string pop;
		if (j == 0) pop = "All";
		if (j == 1) pop = "Males";
		if (j == 2) pop = "Females";
		MOUT("%s :: %s :: With Values :: %6d / %6d = %5.2f :: %6d / %6d = %5.2f\n",
			sig_name.c_str(),
			pop.c_str(),
			n_with_sig[j], n_tot[j], (float)n_with_sig[j] / (float)n_tot[j],
			n_with_sig[j], n_with_sig[0], (float)n_with_sig[j] / (float)n_with_sig[0]);
	}

	MOUT("%s :: General :: No. of Values :: All %6d Male %6d Female %6d\n", sig_name.c_str(), nvals_all[0], nvals_all[1], nvals_all[2]);
	MOUT("%s :: General :: No. of different days Values :: All %6d Male %6d Female %6d\n", sig_name.c_str(), nvals_diff_days[0], nvals_diff_days[1], nvals_diff_days[2]);
	MOUT("%s :: General :: Avg #values per person (all) :: All %5.2f Male %5.2f Female %5.2f\n", sig_name.c_str(),
		(float)nvals_diff_days[0] / (float)n_tot[0],
		(float)nvals_diff_days[1] / (float)n_tot[1],
		(float)nvals_diff_days[2] / (float)n_tot[2]);
	MOUT("%s :: General :: Avg #values per person (>0)  :: All %5.2f Male %5.2f Female %5.2f\n", sig_name.c_str(),
		(float)nvals_diff_days[0] / (float)n_with_sig[0],
		(float)nvals_diff_days[1] / (float)n_with_sig[1],
		(float)nvals_diff_days[2] / (float)n_with_sig[2]);
	MOUT("%s :: General :: Avg dist between tests       :: All %6.1f Male %6.1f Female %6.1f\n", sig_name.c_str(),
		(float)dist_between[0] / (float)n_dist_between[0],
		(float)dist_between[1] / (float)n_dist_between[1],
		(float)dist_between[2] / (float)n_dist_between[2]);

	for (j = 0; j < 3; j++) {
		for (i = age_min; i <= age_max; i += 5) {
			string pop;
			if (j == 0) pop = "All";
			else if (j == 1) pop = "Males";
			else pop = "Females";

			MOUT("%s :: Counts :: Age Group %2d - %2d :: %s :: %6d %5.3f\n",
				sig_name.c_str(), i, i + 5,
				pop.c_str(),
				age_groups[j][i], (float)age_groups[j][i] / (float)nvals_all[j]
			);
		}
	}

	for (i = age_min; i < age_max; i += 5) {
		vector<float> samples;
		samples.clear();
		collect_values(rep, sig_name, samples, 0, i, i + 5, date_min, date_max);
		MedCleaner c_samples;
		c_samples.min_trim = 0;
		c_samples.get_cleaning_params(samples);
		c_samples.clear(samples);
		c_samples.calculate(samples);

		char prefix[300];
		snprintf(prefix, sizeof(prefix),
			"%s :: Stats :: Age Group %2d - %2d :: All :: ", sig_name.c_str(), i, i + 5);
		c_samples.print_short(prefix);
	}



	// Collecting data to compute distribution
	vector<float> samples;
	vector<float> p(6);
	p[0] = (float)0.001; p[1] = (float)0.01; p[2] = (float)0.05; p[3] = (float)0.95; p[4] = (float)0.99; p[5] = (float)0.999;
	vector<float> q(5);
	q[0] = (float)0.001; q[1] = (float)0.25; q[2] = (float)0.50; q[3] = (float)0.75;
	vector<float> pvals(6);
	MedCleaner c_samples;
	string prefix;
	for (i = 0; i < 3; i++) {
		samples.clear();
		collect_values(rep, sig_name, samples, i, age_min, age_max, date_min, date_max);
		MLOG("Collected %d samples for %s\n", samples.size(), sig_name.c_str());
		for (int k = 0; k < (int)samples.size(); k += (int)samples.size() / 5) MLOG("%f ", samples[k]);
		MLOG("\n");
		c_samples.min_trim = 0;
		c_samples.get_cleaning_params(samples);
		float outliers = (float)c_samples.clear(samples) / (float)samples.size();
		c_samples.calculate(samples);

		if (i == 0) prefix = sig_name + " :: General :: All     ::";
		if (i == 1) prefix = sig_name + " :: General :: Males   ::";
		if (i == 2) prefix = sig_name + " :: General :: Females ::";

		MOUT("%s outliers ratio %f\n", prefix.c_str(), outliers);
		c_samples.print_short(prefix);

		medial::stats::get_percentiles(samples, p, pvals, 1);
		MOUT("%s distribution 0.001,0.01,0.05 :: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f\n", prefix.c_str(), pvals[0], pvals[1], pvals[2], pvals[3], pvals[4], pvals[5]);

		medial::stats::get_percentiles(samples, q, pvals, 1);
		MOUT("%s quartiles :: %6.2f %6.2f %6.2f %6.2f \n", prefix.c_str(), pvals[0], pvals[1], pvals[2], pvals[3]);
	}

	samples.clear();
	collect_values(rep, sig_name, samples, 0, age_min, age_max, date_min, date_max);
	vector<float> res;
	vector<int> counts;
	float r = medial::stats::get_best_rounding(samples, res, counts);
	//	float r = get_best_rounding(samples);
	int sumi = 0;
	for (int n : counts)
		sumi += n;
	for (int j = 0; j < res.size(); j++)
		MOUT("%s :: Rounding :: %5.2f r %5.2f pct\n", sig_name.c_str(), res[j], 1.0*counts[j] / sumi);
	MOUT("%s :: Rounding :: most popular rounding for vals: %5.2f\n", sig_name.c_str(), r);


	return 0;
}

//=================================================================================================
int describe_signal_stratify(MedRepository &rep, string &sig_name, int age_min, int age_max, int date_min, int date_max)
{

	int i;
	vector<float> samples;
	MedCleaner c_samples;
	string prefix;
	// describe vales over years/months
	for (i = 0; i < 3; i++) {
		for (int y = date_min / 10000; y <= date_max / 10000; y++) {
			samples.clear();
			collect_values(rep, sig_name, samples, i, age_min, age_max, y * 10000, (y + 1) * 10000);
			c_samples.min_trim = 0;
			c_samples.get_cleaning_params(samples);
			c_samples.clear(samples);
			c_samples.calculate(samples);

			string year = to_string(y);
			if (i == 0) prefix = sig_name + " :: Stats year :: " + year + " :: All ::";
			if (i == 1) prefix = sig_name + " :: Stats year :: " + year + " :: Males   ::";
			if (i == 2) prefix = sig_name + " :: Stats year :: " + year + " :: Females ::";

			c_samples.print_short(prefix);
		}
	}

	for (i = 0; i < 1; i++) {
		for (int m = 1; m <= 12; m++) {
			samples.clear();
			collect_values(rep, sig_name, samples, i, age_min, age_max, date_min, date_max, m);
			c_samples.min_trim = 0;
			c_samples.get_cleaning_params(samples);
			c_samples.clear(samples);
			c_samples.calculate(samples);

			string month = to_string(m);
			if (i == 0) prefix = sig_name + " :: Stats month " + month + " :: All ::";
			if (i == 1) prefix = sig_name + " :: Stats month " + month + " :: Males   ::";
			if (i == 2) prefix = sig_name + " :: Stats month " + month + " :: Females ::";

			c_samples.print_short(prefix);
		}
	}
	return 0;
}


//........................................................................................................................................
void collect_values(MedRepository &rep, string &sig_name, vector<float> &vals, int gender, int age_min, int age_max, int date_min, int date_max, int month)
{
	UniversalSigVec sdv;
	int sid = rep.sigs.Name2Sid[sig_name];
	int byear_id = rep.sigs.Name2Sid["BYEAR"];
	int gender_id = rep.sigs.Name2Sid["GENDER"];
	int train_id = rep.sigs.Name2Sid["TRAIN"];

	for (int i = 0; i < rep.index.pids.size(); i++) {

		rep.uget(rep.index.pids[i], sid, sdv);
		if (sdv.len == 0) continue;

		int gender_val = medial::repository::get_value(rep, rep.index.pids[i], gender_id);
		int byear = medial::repository::get_value(rep, rep.index.pids[i], byear_id);
		int train_val = medial::repository::get_value(rep, rep.index.pids[i], train_id);
		if (train_val < 0)
			train_val = 2;
		int len = sdv.len;
		int sdv_i = 0;

		if (byear > 0 && gender_val > 0 && train_val > 0 && (train_val != 2) && (gender == GENDER_BOTH || gender == gender_val)) {
			//			if ((sdv = (SDateVal *)rep.get(rep.index.pids[i], sig_name, len)) != NULL) {
			if (1) { //(sdv = (SDateVal *)rep.get(rep.index.pids[i], sig_name, len)) != NULL) {
				while (len > 0 && sdv.Time(sdv_i) < date_min) { ++sdv_i; --len; }
				while (len > 0 && sdv.Time(len - 1) > date_max) { --len; }
				if (sdv.len > 0) {
					int k = rand_N(len);
					// choose first one in right month
					while (k < len) {
						int m = (int)((sdv.Time(k) % 10000) / 100);
						if (m == month) break;
						k++;
					}
					if (k < len) {
						float age = get_age(sdv.Time(k), byear);
						if (age >= age_min && age <= age_max)
							vals.push_back(sdv.Val(k));
					}
				}
			}
		}
	}
}

float MISSING_VALUE = -9999.0;


void FilterAges(vector<float> &pidData, vector<float> &ages, float minAge, float maxAge) {
	vector<float> newDataX;
	vector<float> newDataY;
	for (size_t i = 0; i < ages.size(); ++i)
	{
		if (ages[i] >= minAge && ages[i] <= maxAge) {
			newDataY.push_back(ages[i]);
			newDataX.push_back(pidData[i]);
		}
	}
	ages = newDataY;
	pidData = newDataX;
}

float NormalizeData(map<float, float> &data) {
	float totSum = 0;
	for (auto it = data.begin(); it != data.end(); ++it)
	{
		totSum += it->second;
	}
	for (auto it = data.begin(); it != data.end(); ++it)
	{
		data[it->first] = it->second / totSum;
	}
	return totSum;
}

template<class T> void UnionVector(vector<T> &src, const vector<T> &target) {
	src.insert(src.end(), target.begin(), target.end());
}

void FilterSmallFreq(map<float, float> &hist, float th = 0.00005) {
	map<float, float> newHist;
	for (auto it = hist.begin(); it != hist.end(); ++it)
	{
		if (it->second >= th) {
			newHist[it->first] = it->second;
		}
	}
	hist = newHist;
}

int print_regualr_rep(MedRepository &rep, const string &rep_fname, const vector<int> &pids, const vector<string> &sigs, int limit_count) {
	if (rep.read_all(rep_fname, pids, sigs) < 0) {
		MERR("flow_output_sig_raw can't load sigs for rep %s\n", rep.config_fname.c_str());
		return -1;
	}
	vector<int> sig_ids(sigs.size());
	for (size_t i = 0; i < sig_ids.size(); ++i)
		sig_ids[i] = rep.sigs.sid(sigs[i]);
	cout << "pid" << '\t' << "signal_name" << '\t' << "description_name" << '\t' << "description_value"
		<< "\t..." << '\n';
	for (int i = 0; i < rep.pids.size(); i++)
	{
		int pid = rep.pids[i];
		for (int k = 0; k < sig_ids.size(); ++k)
		{
			UniversalSigVec usv;
			rep.uget(pid, sig_ids[k], usv);
			vector<pair<vector<string>, vector<string>>> prtintable_usv;
			rep.convert_pid_sigs(usv, prtintable_usv, sigs[k], sig_ids[k], limit_count);
			rep.print_pid_sig(pid, sigs[k], prtintable_usv);
		}
	}
	return 0;
}

int flow_output_pids_sigs_print_raw(const string &rep_fname, const string &pids_args,
	const string &sigs_arg, int limit_count, const string &model_rep_processors,
	const int time, const string &f_samples) {
	MedPidRepository rep;
	vector<int> pids;
	vector<string> tokens;
	if (!f_samples.empty()) {
		MedSamples smps;
		smps.read_from_file(f_samples);
		smps.get_ids(pids);
	}
	else {
		if (!pids_args.empty()) {
			boost::split(tokens, pids_args, boost::is_any_of(",;"));
			pids.resize(tokens.size());
			for (size_t i = 0; i < tokens.size(); ++i)
				pids[i] = stoi(tokens[i]);
		}
	}
	vector<string> sigs;
	boost::split(sigs, sigs_arg, boost::is_any_of(",;"));
	if (sigs.empty())
		MTHROW_AND_ERR("Error: Must provide at least one signal in pids_sigs_print_raw\n");


	if (model_rep_processors.empty())
		return print_regualr_rep(rep, rep_fname, pids, sigs, limit_count);
	else {
		if (rep.init(rep_fname) < 0)
			MTHROW_AND_ERR("Error unable to read repository %s\n", rep_fname.c_str());

		vector<int> signalCodes(sigs.size());
		vector<int> signals_init_dyn;
		MedModel model_with_rep_processor;
		if (boost::ends_with(model_rep_processors, ".json")) {
			MLOG("Read json model [%s] and run learn\n", model_rep_processors.c_str());
			model_with_rep_processor.init_from_json_file(model_rep_processors);

			vector<string> physical_signal;
			vector<string> sig_names_use = medial::repository::prepare_repository(rep, sigs, physical_signal, &model_with_rep_processor.rep_processors);
			if (rep.read_all(rep_fname, pids, physical_signal) < 0)
				MTHROW_AND_ERR("Can't read repo %s\n", rep_fname.c_str());
			medial::repository::prepare_repository(rep, sigs, physical_signal, &model_with_rep_processor.rep_processors); //prepare again after reading
			
			signals_init_dyn.resize(sig_names_use.size());
			for (size_t i = 0; i < sig_names_use.size(); ++i) {
				signals_init_dyn[i] = rep.sigs.sid(sig_names_use[i]);
				if (signals_init_dyn[i] < 0)
					MTHROW_AND_ERR("Error can't find signal %s\n", sig_names_use[i].c_str());
			}
		}
		else {
			MLOG("Read binary model [%s] and run apply\n", model_rep_processors.c_str());
			model_with_rep_processor.read_from_file(model_rep_processors);

			model_with_rep_processor.init_model_for_apply(rep, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_GENERATORS);
			unordered_set<string> req_sigs;
			vector<string> rsigs;
			model_with_rep_processor.get_required_signal_names(req_sigs);
			for (auto &s : req_sigs) rsigs.push_back(s);

			if (rep.read_all(rep_fname, pids, rsigs) < 0)
				MTHROW_AND_ERR("Can't read repo %s\n", rep_fname.c_str());

			signals_init_dyn.resize(req_sigs.size());
			for (size_t i = 0; i < rsigs.size(); ++i) {
				signals_init_dyn[i] = rep.sigs.sid(rsigs[i]);
				if (signals_init_dyn[i] < 0)
					MTHROW_AND_ERR("Error can't find signal %s\n", rsigs[i].c_str());

			}
		}

		for (size_t i = 0; i < sigs.size(); ++i) {
			signalCodes[i] = rep.sigs.sid(sigs[i]);
			if (signalCodes[i] < 0)
				MTHROW_AND_ERR("Error can't find signal %s\n", sigs[i].c_str());
		}

		int N_tot_threads = omp_get_max_threads();
		vector<PidDynamicRec> idRec(N_tot_threads);

		vector<vector<vector<pair<vector<string>, vector<string>>>>> pid_result(rep.pids.size());
		for (size_t i = 0; i < pid_result.size(); ++i)
			pid_result[i].resize(sigs.size());

		MedProgress progress("Print", (int)rep.pids.size(), 15, 50);

#pragma omp parallel for schedule(dynamic,1)
		for (int i = 0; i < rep.pids.size(); ++i)
		{
			int n_th = omp_get_thread_num();
			if (idRec[n_th].init_from_rep(std::addressof(rep), rep.pids[i], signals_init_dyn, 1) < 0)
				MTHROW_AND_ERR("Unable to read repository\n");

			vector<int> time_pnt = { time };
			vector<vector<float>> attr;
			for (unsigned int i = 0; i < model_with_rep_processor.rep_processors.size(); ++i)
				model_with_rep_processor.rep_processors[i]->apply(idRec[n_th], time_pnt, attr);

			//print for pid all requested sigs
			for (size_t k = 0; k < sigs.size(); ++k) {
				UniversalSigVec usv;
				idRec[n_th].uget(signalCodes[k], idRec[n_th].get_n_versions() - 1, usv);

				rep.convert_pid_sigs(usv, pid_result[i][k], sigs[k], signalCodes[k], limit_count);
			}
			progress.update();
		}
		//now without threading - print:
		cout << "pid" << '\t' << "signal_name" << '\t' << "description_name" << '\t' << "description_value"
			<< "\t..." << '\n';
		for (int i = 0; i < rep.pids.size(); ++i)
			for (size_t k = 0; k < sigs.size(); ++k)
				rep.print_pid_sig(rep.pids[i], sigs[k], pid_result[i][k]);

		cout.flush();
	}
	return 0;
}
int flow_output_sig(string &rep_fname, string &sig_name, string &outputFrmt, int age_min, int age_max,
	int gender_filt, int maxPids, int sampleCnt, bool normalize, float filterRate, const string &bin_method, string& output_fname)
{
	int rc = 0;
	vector<int> pids;
	MedRepository rep;

	if (!(outputFrmt == "html" || outputFrmt == "csv" || outputFrmt == "raw")) {
		MERR("FlowSigOutput::output_sig ERROR: ilegal output format %s, please use html,csv or raw.\n", outputFrmt.data());
		return -1;
	}
	// making sure needed sigs from rep are loaded
	vector<string> sigs = { "GENDER","BDATE" };
	sigs.push_back(sig_name);
	if (rep.read_all(rep_fname, pids, sigs) < 0) {
		MERR("FlowSigOutput::get_stats ERROR: can't load sigs for rep %s\n", rep.config_fname.c_str());
		return -1;
	}
	pids = rep.pids;


	vector<float> xData;
	vector<float> yData;
	vector<int> pids_order;

	time_t start = time(NULL);
	double duration;
	int i = 0;
	//int iDone = 0;
	int mark_done = 0;

	int sig_id = rep.sigs.sid(sig_name);
	int gender_sig = rep.sigs.sid("GENDER");
	int bdate_sig = rep.sigs.sid("BDATE");
	if (sig_id < 0)
		MTHROW_AND_ERR("Error - can't find signal %s\n", sig_name.c_str());
	if (bdate_sig < 0 || gender_sig < 0)
		MTHROW_AND_ERR("Error - can't find signal BDATE or GEDNER\n");
	bool sigOnlyVal = rep.sigs.Sid2Info[sig_id].n_time_channels == 0;

	random_device rd;
	vector<mt19937> random_gens(omp_get_max_threads());
	for (size_t i = 0; i < random_gens.size(); ++i)
		random_gens[i] = mt19937(rd());

	//#pragma omp parallel for
	for (int ii = 0; ii < pids.size(); ++ii)
	{
		if (mark_done != 0)
			continue;
		int pid = pids[ii];
		if (gender_filt > 0) {
			int gender = medial::repository::get_value(rep, pid, gender_sig);
			if (gender != gender_filt)
				continue; // filter gender
		}
		int BDate = medial::repository::get_value(rep, pid, bdate_sig);
		mt19937 &gen = random_gens[omp_get_thread_num()];

		//vector<SDateVal> patientFile = RepoReadSignal(rep, sig_name, pid);
		int insertCount = 0;
		UniversalSigVec us;
		vector<float> sampleCandi;
		rep.uget(pid, sig_id, us);
		int age;
		if (sigOnlyVal) {
#pragma omp critical 
			for (size_t k = 0; k < us.len; ++k)
				xData.push_back(us.Val((int)k));
			insertCount = us.len;
		}
		else {
			if (sampleCnt == 0) {
				for (int k = 0; k < us.len; ++k) {
					age = (int)medial::repository::DateDiff(BDate, us.Time(k));
					if (age >= age_min && age <= age_max) {
#pragma omp critical
						xData.push_back(us.Val(k));
						++insertCount;
					}
				}
			}
			else {
				for (int k = 0; k < us.len; ++k) {
					age = (int)medial::repository::DateDiff((int)BDate, us.Time(k));
					if (age >= age_min && age <= age_max)
						sampleCandi.push_back(us.Val(k));
				}
			}
		}

		if (!sigOnlyVal && sampleCnt > 0 && !sampleCandi.empty()) {
			uniform_int_distribution<> dis(0, (int)sampleCandi.size() - 1);
			insertCount = sampleCnt;
#pragma omp critical 
			for (size_t i = 0; i < sampleCnt; ++i)
				xData.push_back(sampleCandi[dis(gen)]);
		}

#pragma omp critical 
		{
			//UnionVector(xData, pidData);

			if (outputFrmt == "raw") {
				for (size_t i = 0; i < insertCount; ++i)
					pids_order.push_back(pid);
			}

			if (insertCount > 0) {
				++i;
			}
			else if (sigOnlyVal) {
				xData.push_back(MISSING_VALUE);
				//yData.push_back();
			}
			//++iDone;
		}
		//if (iDone % 500000 == 0)
		//	MLOG("Done Proccesing %d/%d (%2.3f%%) \n", iDone, pids.size(), (float)100.0 * (float)iDone / pids.size());
		if (maxPids > 0 && i >= maxPids) {
			mark_done = 1;
		}
	}
	duration = difftime(time(NULL), start);
	MLOG("Read %d Data Points with in %2.2f seconds\n", xData.size(), duration);
	if (mark_done < 0) {
		return -1;
	}

	string signalName = sig_name;

	vector<float> signalData = xData;
	try
	{
		BinSettings bin_s;
		bin_s.init_from_string(bin_method);
		medial::process::split_feature_to_bins(bin_s, signalData, {}, signalData);
	}
	catch (const std::exception &err)
	{
		MERR("Bin Split Error %s\n", err.what());
		return -1;
	}



	if (outputFrmt == "raw") {
		if (!sigOnlyVal) {
			MERR("Signal [%s] is not type without time channels - not supported\n", sig_name.c_str());
			return -1;
		}
		//prints from pids, signalData
		ofstream fw(output_fname);
		fw << "pid\t" << sig_name << endl;
		for (size_t i = 0; i < pids_order.size(); ++i)
			fw << pids_order[i] << "\t" << signalData[i] << endl;
		fw.close();
		return rc;
	}

	map<float, float> hist = BuildHist(signalData);
	if (normalize) {
		NormalizeData(hist);
	}
	FilterSmallFreq(hist, filterRate);
	vector<map<float, float>> graphData = { hist };
	replace(signalName.begin(), signalName.end(), '#', 'H');
	replace(signalName.begin(), signalName.end(), '%', 'P');

	if (outputFrmt == "html") {
		createHtmlGraph(output_fname, graphData, signalName, sig_name, "Prob", { "data" });
		return rc;
	}

	string csvData = createCsvFile(hist);
	MOUT("%s", csvData.c_str());

	return rc;
}

void clone_cleaners(vector<RepProcessor *> &target, const vector<RepProcessor *> &source) {
	target.resize(source.size());
	for (size_t i = 0; i < target.size(); ++i)
	{
		target[i] = RepProcessor::make_processor(source[i]->processor_type);
		vector<unsigned char> blob;
		source[i]->serialize_vec(blob);
		target[i]->deserialize_vec(blob);
	}
}

void filter_in(vector<int> &v, const vector<int> &v2) {
	unordered_set<int> v2_s(v2.begin(), v2.end());
	vector<int> final_v;
	final_v.reserve(min(v.size(), v2_s.size()));
	for (size_t i = 0; i < v.size(); ++i)
		if (v2_s.find(v[i]) != v2_s.end())
			final_v.push_back(v[i]);
	v.swap(final_v);
}

bool get_changes(const UniversalSigVec &usv_no_cleaning, const UniversalSigVec& usv_cleaning, int val_channel,
	cleaning_stats &stats, bool show_all_changes) {
	stats.total_count += usv_no_cleaning.len;
	stats.total_count_after_clean += usv_cleaning.len;
	++stats.total_pids;
	stats.pids_filtered_from += int(usv_no_cleaning.len != usv_cleaning.len);
	int non_zeros = 0;
	for (int i = 0; i < usv_no_cleaning.len; ++i)
		non_zeros += int(usv_no_cleaning.Val(i, val_channel) > 0);
	stats.total_count_non_zero += non_zeros;
	stats.total_filtered_non_zero += int(usv_cleaning.len >= non_zeros); //if filtered zeros ignore

	bool has_filtering = usv_cleaning.len < non_zeros;
	bool has_filtering_of_zeros = show_all_changes && usv_cleaning.len != usv_no_cleaning.len;
	//bool has_filtering_of_zeros = show_all_changes; //just always show

	return has_filtering || has_filtering_of_zeros; //filtered from zeros
}

void write_examples(int pid, const string &sig_name, const UniversalSigVec &usv_no_cleaning,
	const UniversalSigVec& usv_cleaning, int val_channel, ostream &fw) {
	string sig = sig_name;
	if (val_channel > 0)
		sig += "_ch_" + to_string(val_channel);
	int clean_iter = 0;
	for (int i = 0; i < usv_no_cleaning.len; ++i)
	{
		while (clean_iter < usv_cleaning.len && usv_cleaning.Time(clean_iter) < usv_no_cleaning.Time(i))
			++clean_iter;
		string sim_text = "";
		if (clean_iter < usv_cleaning.len && (usv_no_cleaning.Time(i) == usv_cleaning.Time(clean_iter)
			&& usv_no_cleaning.Val(i, val_channel) == usv_cleaning.Val(clean_iter, val_channel)))
			++clean_iter;
		else
			sim_text = "\t[REMOVED]";

		fw << "EXAMPLE\tpid\t" << pid << "\tSignal\t" << sig << "\tTime\t" << usv_no_cleaning.Time(i)
			<< "\tValue\t" << usv_no_cleaning.Val(i, val_channel) << sim_text
			<< "\n";
	}
	//additions:

	for (int i = 0; i < usv_cleaning.len; ++i)
	{
		string sim_text = "\t[ADDED]";
		int curr_time = usv_cleaning.Time(i);
		float curr_val = usv_cleaning.Val(i, val_channel);
		clean_iter = 0; //start over again
		while (clean_iter < usv_no_cleaning.len && usv_no_cleaning.Time(clean_iter) < curr_time)
			++clean_iter;
		while (clean_iter < usv_no_cleaning.len && usv_no_cleaning.Time(clean_iter) == curr_time) {
			if (usv_no_cleaning.Val(clean_iter, val_channel) == curr_val) {
				sim_text = ""; //found - not added
				break;
			}
			++clean_iter;
		}

		if (!sim_text.empty())
			fw << "EXAMPLE\tpid\t" << pid << "\tSignal\t" << sig << "\tTime\t" << usv_cleaning.Time(i)
			<< "\tValue\t" << usv_cleaning.Val(i, val_channel) << sim_text
			<< "\n";
	}

}

void print_sig_stats(const string &sig_name, int val_channel, const cleaning_stats &stats, ostream &fw) {
	string sig = sig_name;
	if (val_channel > 0)
		sig += "_ch_" + to_string(val_channel);
	//pids_filtered_from ;
	if (stats.total_count > 0) {
		fw << "STATS\t" << sig << "\tTOTAL_CNT\t" << stats.total_count << "\tTOTAL_CNT_NON_ZERO\t" << stats.total_count_non_zero
			<< "\tTOTAL_CLEANED\t" << stats.total_count_after_clean << "\tCLEAN_PERCENTAGE\t" <<
			100.0*(float(stats.total_count - stats.total_count_after_clean) / stats.total_count) << "%";
		if (stats.total_count_non_zero > 0) {
			fw << "\tCLEAN_NON_ZERO_PERCENTAGE\t" <<
				100.0*(float(stats.total_count_non_zero - stats.total_count_after_clean) / stats.total_count_non_zero) << "%";
		}
		fw << "\tTOTAL_PIDS\t" << stats.total_pids << "\tPIDS_FILTERED\t" << stats.pids_filtered_from
			<< "\tPIDS_FILTERED_NON_ZEROS\t" << stats.total_pids - stats.total_filtered_non_zero;
		if (stats.total_pids > 0) {
			fw << "\tPIDS_FILTER_PERCENTAGE\t" << 100.0*(float(stats.pids_filtered_from) / stats.total_pids)
				<< "%\tPIDS_FILTER_PERCENTAGE\t" << 100.0*(float(stats.total_pids - stats.total_filtered_non_zero) / stats.total_pids) << "%";
		}
		fw << "\n";
	}
}

void test_rep_processors(const string &rep_fname, const string &before_cleaners_path, const string &cleaners_path,
	const vector<string> &all_sigs, const string &output_example_file, int seed, int max_examples,
	const vector<int> &given_pids, bool show_all_changes) {
	ofstream fw;
	ostream *p_stream = &cout;
	if (!(output_example_file.empty() || output_example_file == "stdout" || output_example_file == "-")) {
		fw.open(output_example_file);
		if (!fw.good())
			MTHROW_AND_ERR("Can't open file for writing\n");
		p_stream = &fw;
	}

	vector<int> pids = given_pids;

	MedPidRepository rep_before, rep_cleaned;
	int N_tot_threads = omp_get_max_threads();
	vector<PidDynamicRec> idRec_after(N_tot_threads), idRec_before(N_tot_threads);

	if (rep_before.init(rep_fname) < 0)
		MTHROW_AND_ERR("Error unable to read repository %s\n", rep_fname.c_str());
	if (rep_cleaned.init(rep_fname) < 0)
		MTHROW_AND_ERR("Error unable to read repository %s\n", rep_fname.c_str());
	MedModel model_with_rep_processor, before_model;
	model_with_rep_processor.init_from_json_file(cleaners_path);
	model_with_rep_processor.collect_and_add_virtual_signals(rep_cleaned);
	random_device rd;
	mt19937 rand_gen(rd());
	if (seed > 0)
		rand_gen = mt19937(seed);

	if (!before_cleaners_path.empty()) {
		before_model.init_from_json_file(before_cleaners_path);
		before_model.collect_and_add_virtual_signals(rep_before);
	}

	for (int sig_idx = 0; sig_idx < all_sigs.size(); ++sig_idx)
	{
		const string &sig = all_sigs[sig_idx];

		vector<string> sigs = { sig };
		int sig_id = rep_before.sigs.sid(sig);
		if (sig_id < 0) {
			MWARN("Warning Unknown signal %s\n", sig.c_str());
			continue;
		}
		int val_channels_cnt = rep_before.sigs.Sid2Info[sig_id].n_val_channels;
		vector<cleaning_stats> cln_stats(val_channels_cnt);
		MLOG("Testing Cleaner on %s[%d / %zu]\n", sig.c_str(), sig_idx + 1, all_sigs.size());

		vector<int> final_sigs_to_read_before;
		vector<RepProcessor *> cleaners_before;
		if (before_cleaners_path.empty()) {
			if (rep_before.read_all(rep_fname, pids, sigs) < 0)
				MTHROW_AND_ERR("can't load sigs for rep %s\n", rep_before.config_fname.c_str());
		}
		else {
			vector<string> physical_signal_before;

			clone_cleaners(cleaners_before, before_model.rep_processors);

			vector<string> sig_names_use = medial::repository::prepare_repository(rep_before, sigs, physical_signal_before, &cleaners_before);
			final_sigs_to_read_before.resize(sig_names_use.size());
			for (size_t i = 0; i < sig_names_use.size(); ++i) {
				int sid = rep_before.sigs.sid(sig_names_use[i]);
				if (sid < 0)
					MTHROW_AND_ERR("Error in Couldn't find signal \"%s\" in repository or virtual\n",
						sig_names_use[i].c_str());
				final_sigs_to_read_before[i] = sid;
			}
			if (rep_before.read_all(rep_fname, pids, physical_signal_before) < 0)
				MTHROW_AND_ERR("Can't read repo %s\n", rep_fname.c_str());
			medial::repository::prepare_repository(rep_cleaned, sigs, physical_signal_before, &cleaners_before);

		}


		vector<string> physical_signal;
		vector<RepProcessor *> cleaners;
		clone_cleaners(cleaners, model_with_rep_processor.rep_processors);

		vector<string> sig_names_use = medial::repository::prepare_repository(rep_cleaned, sigs, physical_signal, &cleaners);
		vector<int> final_sigs_to_read(sig_names_use.size());
		for (size_t i = 0; i < sig_names_use.size(); ++i) {
			int sid = rep_before.sigs.sid(sig_names_use[i]);
			if (sid < 0)
				MTHROW_AND_ERR("Error in Couldn't find signal \"%s\" in repository or virtual\n",
					sig_names_use[i].c_str());
			final_sigs_to_read[i] = sid;
		}
		if (rep_cleaned.read_all(rep_fname, pids, physical_signal) < 0)
			MTHROW_AND_ERR("Can't read repo %s\n", rep_fname.c_str());
		medial::repository::prepare_repository(rep_cleaned, sigs, physical_signal, &cleaners);

		vector<int> pids_o = rep_cleaned.pids;
		filter_in(pids_o, rep_before.pids);

		shuffle(pids_o.begin(), pids_o.end(), rand_gen);
		int wrote_examples = 0;
		MedProgress progress("Print_Cleaners", (int)pids_o.size(), 15, 100);
#pragma omp parallel for schedule(dynamic,1)
		for (int i = 0; i < pids_o.size(); i++)
		{
			int pid = pids_o[i];
			int n_th = omp_get_thread_num();

			UniversalSigVec usv_no_cleaning, usv_cleaning;
			if (before_cleaners_path.empty())
				rep_before.uget(pid, sig_id, usv_no_cleaning);
			else {
				if (idRec_before[n_th].init_from_rep(std::addressof(rep_before), pid, final_sigs_to_read_before, 1) < 0)
					MTHROW_AND_ERR("Unable to read repository\n");
				vector<int> time_pnt_before = { INT_MAX };
				vector<vector<float>> attr_before;
				for (unsigned int i = 0; i < cleaners_before.size(); ++i)
					cleaners_before[i]->apply(idRec_before[n_th], time_pnt_before, attr_before);
				idRec_before[n_th].uget(sig_id, idRec_before[n_th].get_n_versions() - 1, usv_no_cleaning);
			}

			if (idRec_after[n_th].init_from_rep(std::addressof(rep_cleaned), pid, final_sigs_to_read, 1) < 0)
				MTHROW_AND_ERR("Unable to read repository\n");
			vector<int> time_pnt = { INT_MAX };
			vector<vector<float>> attr;
			for (unsigned int i = 0; i < cleaners.size(); ++i)
				cleaners[i]->apply(idRec_after[n_th], time_pnt, attr);
			idRec_after[n_th].uget(sig_id, idRec_after[n_th].get_n_versions() - 1, usv_cleaning);

			//test changes between usv_no_cleaning, usv_cleaning
#pragma omp critical
			for (int ch = 0; ch < val_channels_cnt; ++ch) {
				bool has_changes = get_changes(usv_no_cleaning, usv_cleaning, ch, cln_stats[ch], show_all_changes); //removed non zeros
				has_changes = has_changes || usv_cleaning.len > usv_no_cleaning.len; //added records
				//write example to file:
				if (has_changes && (wrote_examples < max_examples || max_examples == 0)) {
					write_examples(pid, sig, usv_no_cleaning, usv_cleaning, ch, *p_stream);
					++wrote_examples;
				}
				//udpate stats per channel
			}

			progress.update();
		}

		for (int ch = 0; ch < cln_stats.size(); ++ch)
			print_sig_stats(sig, ch, cln_stats[ch], *p_stream);
		//run cleaner - print stats:
		p_stream->flush();

		for (size_t i = 0; i < cleaners.size(); ++i)
			delete cleaners[i];
	}

	if (fw.is_open())
		fw.close();
}

void pretty_print_tree(const vector<vector<string>> &paths, bool top) {
	//print tree graph. top==true means the traverse is backward

	string dir = "upward";
	string dir_mark = "<=";
	if (!top) {
		dir = "downward";
		dir_mark = "=>";
	}
	//simple print of all paths:

	//print format for dpeth k to k+1 print prev => next
	int max_depth = 0; //al are at least of size 1
	for (size_t i = 0; i < paths.size(); ++i)
		if (paths[i].size() > max_depth)
			max_depth = (int)paths[i].size();

	//print path size 1:
	if (paths.size() == 1 && paths[0].size() == 1) {
		MLOG("No paths for %s - %s\n", paths[0][0].c_str(), dir.c_str());
		return;
	}
	else
		MLOG("Has %zu paths - %s\n", paths.size(), dir.c_str());

	unordered_set<string> seen_move;
	for (int depth = 0; depth <= max_depth; ++depth)
	{
		//print form depth to depth+1:
		int path_num = 1;
		for (const vector<string> &p : paths)
		{
			if (p.size() <= depth + 1) {
				++path_num;
				continue; //finished path!. p.size() should can access depth + 1
			}
			char buffer[5000];
			snprintf(buffer, sizeof(buffer), "%s %s %s",
				p[depth].c_str(), dir_mark.c_str(), p[depth + 1].c_str());

			string move = string(buffer);
			if (seen_move.find(move) == seen_move.end()) {
				MLOG("PATH %d :: DEPTH %d :: %s\n",
					path_num, depth + 1, move.c_str());
				seen_move.insert(move);
			}
			++path_num;
		}
	}
}

void get_names(const vector<vector<int>> &ids, int sectionId, MedDictionarySections dict,
	vector<vector<string>> &names) {
	names.resize(ids.size());
	for (size_t i = 0; i < ids.size(); ++i)
	{
		names[i].resize(ids[i].size());
		for (size_t j = 0; j < ids[i].size(); ++j) {
			int id = ids[i][j];
			if (id > 0)
				names[i][j] = dict.name(sectionId, id);
			else {
				if (id == -2)
					names[i][j] = "**ALREADY_EXPENDED_ELSEWHERE**";
				else if (id == -1)
					names[i][j] = "**UNKNOWN_ID**";
				else
					MTHROW_AND_ERR("Error unknow id %d\n", id);
			}
		}
	}

}

void print_parents_sons(MedDictionarySections dict, const string &signal, const string &signal_value) {
	int sectionId = 0;
	if (dict.SectionName2Id.find(signal) == dict.SectionName2Id.end())
		MTHROW_AND_ERR("signal not suppoted %s. please select dictionary section: \n",
			signal.c_str());
	sectionId = dict.SectionName2Id.at(signal);

	int curr_id = dict.id(sectionId, signal_value);
	if (curr_id < 0)
		MTHROW_AND_ERR("Can't find code %s in signal %s\n", signal_value.c_str(), signal.c_str());
	int depth = 100;

	vector<vector<int>> parents = { { curr_id } }; //full paths - init to 1 path with 1 current node
	unordered_set<int> expend_id;
	for (size_t k = 1; k < depth; ++k) {
		//do k to k+1
		vector<int> tmp_par;
		bool did_something = false;
		vector<vector<int>> updated_parents;
		for (const vector<int> &path : parents)
		{
			if (path.size() < k) {
				updated_parents.push_back(path);
				continue; //already reached root
			}
			int par = path.back();
			if (par < 0) {
				updated_parents.push_back(path);
				continue; //skip reached already expended root or not existed
			}
			if (expend_id.find(par) != expend_id.end()) {
				//add parent and don't expend - ANYMORE, mark as expended elsewhere
				vector<int> path_dup = path;
				path_dup.push_back(-2);  // mark -2 as reached to already expended!
				updated_parents.push_back(path_dup);
				continue;
			}

			expend_id.insert(par);
			dict.get_member_sets(sectionId, par, tmp_par);

			//create all parents path that came from par - dupliace path with all options to insert into new_layer.
			bool real_did = false;
			for (int par_code : tmp_par)
			{
				if (par_code == par)
					continue;
				real_did = true;
				vector<int> path_dup = path; //add all to parents instead of path - update updated_parents
				path_dup.push_back(par_code);
				updated_parents.push_back(move(path_dup));
			}
			if (real_did)
				did_something = true;
			else
				updated_parents.push_back(path);
		}
		parents = move(updated_parents);
		if (!did_something)
			break; //no more parents to loop up
	}

	expend_id.clear();
	vector<vector<int>> sons = { { curr_id } };
	for (size_t k = 1; k < depth; ++k) {
		//do k to k+1
		vector<int> tmp_par;
		bool did_something = false;
		vector<vector<int>> updated_sons;
		for (const vector<int> &path : sons)
		{
			if (path.size() < k) {
				updated_sons.push_back(path);
				continue; //already reached root
			}
			int par = path.back();
			if (par < 0) {
				updated_sons.push_back(path);
				continue; //skip reached already expended root or not existed
			}
			if (expend_id.find(par) != expend_id.end()) {
				//add parent and don't expend - ANYMORE, mark as expended elsewhere
				vector<int> path_dup = path;
				path_dup.push_back(-2);  // mark -2 as reached to already expended!
				updated_sons.push_back(path_dup);
				continue;
			}

			expend_id.insert(par);
			dict.get_set_members(sectionId, par, tmp_par);

			//create all parents path that came from par - dupliace path with all options to insert into new_layer.
			bool real_did = false;
			for (int son_code : tmp_par)
			{
				if (son_code == par)
					continue;
				real_did = true;
				vector<int> path_dup = path; //add all to parents instead of path - update updated_parents
				path_dup.push_back(son_code);
				updated_sons.push_back(move(path_dup));
			}
			if (real_did)
				did_something = true;
			else
				updated_sons.push_back(path);

		}
		sons = move(updated_sons);
		if (!did_something)
			break; //no more parents to loop up
	}

	vector<vector<string>> parents_with_names(parents.size()), sons_with_names(sons.size());
	get_names(parents, sectionId, dict, parents_with_names);
	get_names(sons, sectionId, dict, sons_with_names);

	//pretty print parents_with_names, sons_with_names:
	pretty_print_tree(parents_with_names, true);
	pretty_print_tree(sons_with_names, false);
}

void show_category_info(const string &rep_fname, const string &signal, const string &signal_value) {
	if (rep_fname.empty())
		MTHROW_AND_ERR("Please pass rep\n");

	MedRepository rep;
	if (rep.init(rep_fname) < 0)
		MTHROW_AND_ERR("Error can't read rep %s\n", rep_fname.c_str());

	print_parents_sons(rep.dict, signal, signal_value);
}

void get_sons_flat(MedDictionarySections dict, const string &signal,
	const vector<string> &signal_values, vector<string> &names, int limit_depth,
	bool shrink, bool allow_diff_lut) {

	unordered_set<int> full_set;
	for (const string &sig_val : signal_values) {
		vector<int> all_sons;
		medial::signal_hierarchy::sons_code_hierarchy_recursive(dict, signal, sig_val, all_sons, limit_depth);
		full_set.insert(all_sons.begin(), all_sons.end());
	}
	//Get names:
	int section_id = dict.section_id(signal);
	vector<char> lut, lut2;
	dict.prep_sets_lookup_table(section_id, signal_values, lut);

	if (shrink) {
		//take each code - extract it's parent. check if all child of parent exits. if so, remove all those childs
		//do recursive
		int max_id = dict.dict(section_id)->Id2Name.rbegin()->first;
		vector<char> full_set_e(max_id + 1);
		for (int id : full_set)
			full_set_e[id] = 1;

		bool has_change = true;
		while (has_change) {
			has_change = false;

			vector<char> seen_code_parent(max_id + 1);

			for (int code : full_set)
			{
				if (full_set_e[code] == 0) //child was already removed and included in parent
					continue;

				//extract parents:
				vector<int> parent_ids;
				dict.get_member_sets(section_id, code, parent_ids);

				for (int parent : parent_ids)
				{
					if (seen_code_parent[parent])
						continue; //no need to test again. already was done in this round
					seen_code_parent[parent] = 1;

					//get all childrens:
					vector<int> child_list;
					dict.get_set_members(section_id, parent, child_list);
					bool all_exists = (!child_list.empty() && (child_list.size() > 1 || !child_list[parent])) || allow_diff_lut;
					for (int child : child_list)
					{
						all_exists = lut[child] > 0;
						if (!all_exists)
							break;
					}

					if (all_exists) {
						//remove all childrens and add parent instead. mark we have changes.
						for (int child : child_list)
							full_set_e[child] = 0;
						full_set_e[parent] = 1;
						has_change = true;
					}
					else {
						if (allow_diff_lut) {
							//test if parent exists and that's enough:
							if (full_set_e[parent])
								full_set_e[code] = 0;
						}
					}
				}
			}

			//regenerate full_set from full_set_e:
			full_set.clear();
			for (int i = 0; i < full_set_e.size(); ++i)
				if (full_set_e[i])
					full_set.insert(i);
		}

	}

	for (int code : full_set)
		names.push_back(dict.name(section_id, code));
	sort(names.begin(), names.end());

	//test:
	dict.prep_sets_lookup_table(section_id, names, lut2);
	vector<char> full_set_vec(lut.size());
	for (int id : full_set)
		full_set_vec[id] = 1;
	//compare lut to full_set_vec
	if (!shrink)
		for (int i = 0; i < full_set_vec.size(); ++i)
		{
			bool is_ok = ((full_set_vec[i] && lut[i]) ||
				(!full_set_vec[i] && !lut[i]));
			if (!is_ok)
				MWARN("Bug in code %d. lut exists=%d \n", i, (int)lut[i]);
		}

	for (int i = 0; i < lut.size(); ++i)
	{
		bool is_ok = ((lut2[i] && lut[i]) ||
			(!lut2[i] && !lut[i]));
		if (!is_ok)
			MWARN("Bug in code %d. lut exists=%d \n", i, (int)lut[i]);
	}

}

void flat_list(const string &rep_fname, const string &signal, const string &signal_codes,
	int limit_depth, bool shrink, bool allow_diff_lut) {
	if (rep_fname.empty())
		MTHROW_AND_ERR("Please pass rep\n");

	MedRepository rep;
	if (rep.init(rep_fname) < 0)
		MTHROW_AND_ERR("Error can't read rep %s\n", rep_fname.c_str());
	vector<string> all_codes, all_flat;
	medial::io::read_codes_file(signal_codes, all_codes);

	get_sons_flat(rep.dict, signal, all_codes, all_flat, limit_depth, shrink, allow_diff_lut);

	for (const string & res : all_flat)
		MLOG("%s\n", res.c_str());
}