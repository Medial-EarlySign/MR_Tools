#include "RegistryHelper.h"
#include <fstream>
#include <iostream>
#include <ctime>
#include <cmath>
#include <algorithm>
#include <fstream>
#include <unordered_set>
#include <random>
#include <unordered_map>
#include <boost/math/distributions/chi_squared.hpp>
#include <regex>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#define MAX_LOG 10000000
static vector<double> log_table(MAX_LOG);

void keep_only_train(const string &rep_path, const MedRegistry &regRecords
	, vector<MedRegistryRecord> &only_train, MedRepository &rep) {
	vector<int> reg_pids;
	regRecords.get_pids(reg_pids);
	vector<string> signal_names = { "TRAIN" };
	if (rep.read_all(rep_path, reg_pids, signal_names) < 0)
		MTHROW_AND_ERR("Unable to read repository.\n");
	MedDictionarySections rep_dict = rep.dict;
	int trn_code = rep.sigs.sid("TRAIN");
	only_train.reserve(int(regRecords.registry_records.size() * 0.71));
	for (size_t i = 0; i < regRecords.registry_records.size(); ++i) {
		int trn_val = medial::repository::get_value(rep, regRecords.registry_records[i].pid, trn_code);
		if (trn_val == 1)
			only_train.push_back(regRecords.registry_records[i]);
	}
}

inline double fast_log(int n) {
	if (n < log_table.size())
		return log_table[n];
	else
		return log(n);
}

inline double binomial_choose(int n, int k) {
	if (log_table.back() == 0) {
		//init array - if empty:
		MLOG_D("init log_table\n");
		for (int i = 2; i < log_table.size(); ++i)
			log_table[i] = log(i);
		MLOG_D("Done init\n");
	}

	int i;
	double b;
	assert(n >= 0 && k >= 0 && k <= n);

	if (0 == k || n == k) return 0;
	//if (k > n) return 0; //impossible

	if (k > (n - k)) k = n - k;
	if (1 == k) return fast_log(n);

	//	if (n <= 54 && k <= 54) 
		//	return bctable[(((n - 3) * (n - 3)) >> 2) + (k - 2)];

		/* Last resort: actually calculate */
	b = 0;
	for (i = 1; i <= k; ++i) {
		b += fast_log(n - (k - i));
		if (b < 0) return -1; /* Overflow */
		b -= fast_log(i);
	}
	return b;
}

inline double exact_fisher(int v0, int v1, int v2, int v3) {
	double res = binomial_choose(v0 + v1, v1) + binomial_choose(v2 + v3, v3) -
		binomial_choose(v0 + v1 + v2 + v3, v1 + v3);
	//if (res < 0)
	//	return NAN;
	return exp(res);
}

double gender_calc_fisher(const map<float, vector<int>> &gender_sorted, float fisher_band) {
	double regScore = 1;
	if (gender_sorted.empty())
		return regScore;
	regScore = 0;
	for (auto i = gender_sorted.begin(); i != gender_sorted.end(); ++i) { //iterate over age bins
		const vector<int> &probs = i->second; //the forth numbers
		double pr = 0;
		vector<int> R(2);
		//vector<double> C(2);

		//C[0] = probs[0] + probs[2]; //how much controls
		//C[1] = probs[1] + probs[1 + 2]; //how much cases
		R[0] = probs[0] + probs[1]; //how much no signal
		R[1] = probs[2] + probs[3]; //how much signal exists
		//fix R[0], R[1] as constant and calc
		vector<int> min_buffers = { int(probs[1] - fisher_band * R[0]) , int(probs[3] - fisher_band * R[1]) };
		vector<int> max_buffers = { int(probs[1] + fisher_band * R[0]) , int(probs[3] + fisher_band * R[1]) };
		for (size_t j = 0; j < 2; ++j) {
			if (min_buffers[j] < 0)
				min_buffers[j] = 0;
			if (max_buffers[j] > R[j])
				max_buffers[j] = R[j];
		}

		for (int k1 = min_buffers[0]; k1 <= max_buffers[0]; ++k1)
		{
			for (int k2 = min_buffers[1]; k2 <= max_buffers[1]; ++k2)
			{
				//calc exact fisher in CI of +-fisher_band change
				pr += exact_fisher(R[0] - k1, k1, R[1] - k2, k2);
			}
		}

		pr /= (max_buffers[0] - min_buffers[0] + 1);
		//update regScore:
		regScore += log(pr);
	}
	regScore = exp(regScore / gender_sorted.size());
	return regScore;
}

void calc_fisher_scores(const map<float, map<float, vector<int>>> &male_stats,
	const map<float, map<float, vector<int>>> &female_stats,
	vector<int> &all_signal_values, vector<int> &signal_indexes,
	vector<double> &valCnts, vector<double> &posCnts,
	vector<double> &lift, vector<double> &scores,
	vector<double> &p_values, vector<double> &pos_ratio, float fisher_band) {
	unordered_set<int> all_vals;
	for (auto i = male_stats.begin(); i != male_stats.end(); ++i)
		all_vals.insert((int)i->first);
	for (auto i = female_stats.begin(); i != female_stats.end(); ++i)
		all_vals.insert((int)i->first);
	all_signal_values.insert(all_signal_values.end(), all_vals.begin(), all_vals.end());
	signal_indexes.resize(all_signal_values.size());
	for (size_t i = 0; i < signal_indexes.size(); ++i)
		signal_indexes[i] = (int)i;
	posCnts.resize(all_signal_values.size());
	valCnts.resize(all_signal_values.size());
	lift.resize(all_signal_values.size());
	scores.resize(all_signal_values.size());
	p_values.resize(all_signal_values.size());
	pos_ratio.resize(all_signal_values.size());

	MedProgress progress("calc_fisher_scores", (int)signal_indexes.size(), 15, 1);
#pragma omp parallel for schedule(dynamic,1)
	for (int i = 0; i < signal_indexes.size(); ++i)
	{
		int index = signal_indexes[i];
		float signalVal = all_signal_values[index];
		//check fisher for this value:
		double regScore1 = 1, regScore2 = 1;
		double totCnt = 0;
		double weighted_lift = 0;

		if (male_stats.find(signalVal) != male_stats.end())
			for (auto jt = male_stats.at(signalVal).begin(); jt != male_stats.at(signalVal).end(); ++jt) {
				totCnt += jt->second[2] + jt->second[3];
				//posCnts[signalVal] += jt->second[1 + 0] + jt->second[1 + 2];
#pragma omp critical
				posCnts[index] += jt->second[1 + 2];
				if (jt->second[1 + 0] > 0)
					weighted_lift += jt->second[1 + 2] / (jt->second[1 + 0]) * (jt->second[1 + 0] + jt->second[0 + 0]);
			}
		if (female_stats.find(signalVal) != female_stats.end())
			for (auto jt = female_stats.at(signalVal).begin(); jt != female_stats.at(signalVal).end(); ++jt) {
				totCnt += jt->second[2] + jt->second[3];
				//posCnts[signalVal] += jt->second[1 + 0] + jt->second[1 + 2];
#pragma omp critical
				posCnts[index] += jt->second[1 + 2];
				if (jt->second[1 + 0] > 0)
					weighted_lift += jt->second[1 + 2] / (jt->second[1 + 0]) * (jt->second[1 + 0] + jt->second[0 + 0]);
			}
		if (totCnt == 0)
			continue;

#pragma omp critical
		{
			valCnts[index] = totCnt; //for signal apeareance
			lift[index] = weighted_lift / totCnt;
		}

		if (male_stats.find(signalVal) != male_stats.end())
			regScore1 = gender_calc_fisher(male_stats.at(signalVal), fisher_band); //Males
		if (female_stats.find(signalVal) != female_stats.end())
			regScore2 = gender_calc_fisher(female_stats.at(signalVal), fisher_band); //Females

#pragma omp critical
		{
			scores[index] = (float)(regScore1 * regScore2);
			if (male_stats.find(signalVal) != male_stats.end() && female_stats.find(signalVal) != female_stats.end())
				scores[index] = sqrt(scores[index]);
		}

		progress.update();


	}

	for (size_t i = 0; i < p_values.size(); ++i) {
		p_values[i] = scores[i];
		scores[i] = 1 - scores[i];
	}
}

void filterAge_gender(map<float, vector<int>> &dict, int min_age, int max_age) {
	map<float, vector<int>> res;
	for (auto it = dict.begin(); it != dict.end(); ++it)
	{
		if (it->first >= min_age && it->first <= max_age) {
			res[it->first] = it->second;
		}
	}
	dict = res;
}

void filterAge(map<float, map<float, vector<int>>> &dict, int min_age, int max_age) {
	map<float, map<float, vector<int>>> res;
	for (auto it = dict.begin(); it != dict.end(); ++it)
	{
		filterAge_gender(it->second, min_age, max_age);
		if (it->second.size() != 0)
			res[it->first] = it->second;
	}
	dict.swap(res);
}

template<class T> string print_obj(T obj, string format) {
	//return to_string((round(num * 1000) / 1000));
	char res[50];
	snprintf(res, sizeof(res), format.c_str(), obj);
	return string(res);
}

void print_gender(const map<float, vector<int>> &gender_stats, const string &genderName,
	stat_test stat_type, int smooth_balls, float at_least, int minimal_count, float filter_fisher_smooth) {

	cout << "Stats for " << genderName << endl;
	cout << "              [" << "NO_SIG&REG_FALSE, NO_SIG&REG_TRUE, SIG&REG_FALSE, SIG&REG_TRUE]" << endl;

	for (auto it = gender_stats.begin(); it != gender_stats.end(); ++it)
	{
		double row_stats = 0;
		double ratio_0 = 0, ratio_1 = 0, ratio_all = 0;
		if (it->second[0] + it->second[1] > 0)
			ratio_0 = it->second[1] / float(it->second[0] + it->second[1]);
		if (it->second[2] + it->second[3] > 0)
			ratio_1 = it->second[3] / float(it->second[2] + it->second[3]);
		ratio_all = (it->second[1] + it->second[3]) / float(it->second[2] + it->second[3] + it->second[0] + it->second[1]);

		//vector<pair<float, vector<int>>> stats = { pair<float, vector<int>>(it->first, it->second) };
		map<float, vector<int>> stats = { { it->first, it->second } };
		string output_res = "score";
		bool is_ok;
		switch (stat_type)
		{
		case stat_test::chi_square:
			row_stats = medial::contingency_tables::calc_chi_square_dist(stats,
				smooth_balls, at_least, minimal_count);
			break;
		case stat_test::fisher:
			output_res = "pvalue";
			row_stats = gender_calc_fisher(stats, filter_fisher_smooth);
			break;
		case stat_test::mcnemar:
			row_stats = medial::contingency_tables::calc_mcnemar_square_dist(stats);
			break;
		case stat_test::cmh:
			row_stats = medial::contingency_tables::calc_cmh_square_dist(&stats, NULL, is_ok);
			break;
		default:
			MTHROW_AND_ERR("unsupported statstical_test - %d\n", (int)stat_type);
		}

		cout << "Age_Bin: " << it->first << ": [" << it->second[0];
		for (size_t i = 1; i < it->second.size(); ++i)
			cout << ", " << print_obj(print_obj(it->second[i], "%d").c_str(), "%10s");

		cout << "] " << output_res << "= " << print_obj(print_obj(row_stats, "%2.5f").c_str(), "%10s") << " [" << print_obj(print_obj(100 * ratio_0, "%2.3f%%").c_str(), "%7s")
			<< ", " << print_obj(print_obj(100 * ratio_1, "%2.3f%%").c_str(), "%7s") << "] " << "indep_ratio=" << print_obj(100 * ratio_all, "%02.3f%%") << endl;
	}
	cout << endl;
}

void print_top(MedRepository &dataManager, int sectionId, const string &signalHirerchyType,
	const vector<int> &signal_indexes, const vector<int> &signal_values,
	const vector<double> &total_cnts, const vector<double> &pos_cnts, const vector<double> &lift,
	const vector<double> &scores, const vector<double> &p_values, const vector<double> &pos_ratio,
	const vector<int> &dof, const string &hir_filter, bool use_fixed_lift) {
	if (signal_indexes.empty())
		return;
	regex reg_pat;
	if (!hir_filter.empty())
		reg_pat = regex(hir_filter);
	//updown:
	bool warning_shown = false;
	int direction = +1;
	int startInd = 0;
	int endInd = (int)signal_indexes.size() - 1;
	MLOG("Signal Chi-Square scores (%d results):\n", (int)signal_indexes.size());

	vector<double> fixed_lift(lift); //for sorting
	if (use_fixed_lift)
		for (int index : signal_indexes)
			if (fixed_lift[index] < 1 && fixed_lift[index] > 0)
				fixed_lift[index] = 1 / fixed_lift[index];

	//sort by p_value, lift:
	vector<int> indexes_order(signal_indexes.size());
	vector<pair<int, vector<double>>> sort_pars(signal_indexes.size());
	for (size_t i = 0; i < signal_indexes.size(); ++i)
	{
		sort_pars[i].first = (int)signal_indexes[i];
		sort_pars[i].second.resize(3);
		sort_pars[i].second[0] = p_values[signal_indexes[i]];
		if (use_fixed_lift)
			sort_pars[i].second[1] = -fixed_lift[signal_indexes[i]];
		else
			sort_pars[i].second[1] = -lift[signal_indexes[i]];
		sort_pars[i].second[2] = -scores[signal_indexes[i]];
	}
	sort(sort_pars.begin(), sort_pars.end(), [](pair<int, vector<double>> a, pair<int, vector<double>> b) {
		int pos = 0;
		while (pos < a.second.size() &&
			a.second[pos] == b.second[pos])
			++pos;
		if (pos >= a.second.size())
			return false;
		return b.second[pos] > a.second[pos];
	});
	for (size_t i = 0; i < sort_pars.size(); ++i)
		indexes_order[i] = sort_pars[i].first;

	int ii = 1;
	cout << "Index\t" << "Signal_Value\t" << "Chi-Square_Score\t" << "pValue\t" << "dof\t"
		<< "Count_allBins\t" << "Positives_allBins\t" << "LiftProb_allBins\t" << "Signal_Name" << endl;
	for (int i = startInd; i <= endInd; i += direction)
	{
		int index = indexes_order[i];
		double pval = p_values[index];
		double score = scores[index];
		int paramVal = signal_values[index];

		string sigName = dataManager.dict.name(sectionId, paramVal);
		vector<string> all_sigNames = dataManager.dict.dicts[sectionId].Id2Names[paramVal];
		vector<string> after_filter;
		string additional = "";
		if (hir_filter.empty() || hir_filter == "None")
			additional = medial::signal_hierarchy::filter_code_hierarchy(all_sigNames, signalHirerchyType);
		else {
			for (size_t i = 0; i < all_sigNames.size(); ++i)
				if (regex_match(all_sigNames[i], reg_pat))
					after_filter.push_back(all_sigNames[i]);
			if (!warning_shown && after_filter.size() > 1) {
				warning_shown = true;
				MWARN("Warning :you have multiple hierarchy for signal.\n"
					"Please prepare unique hierarchy dict and reffer to it in the repository\n"
					"Example code \"%s\" for value=%d has %d matches\n",
					sigName.c_str(), paramVal, (int)after_filter.size());
			}
			if (!after_filter.empty())
				additional = after_filter.front();
		}

		if (additional.empty())
			additional = sigName;
		sigName += "\t" + additional;

		cout << "StatRow: " << ii << "\t" << paramVal << "\t" << score << "\t" << pval << "\t" << dof[index]
			<< "\t" << int(total_cnts[index]) << "\t" << int(pos_cnts[index]) << "\t" << print_obj(lift[index], "%1.4f")
			<< "\t" << sigName << endl;
		++ii;
	}
}
