#ifndef __REGISTRY_HELPER__
#define __REGISTRY_HELPER__
#include <string>
#include <vector>
#include <map>
#include "InfraMed/InfraMed/InfraMed.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include "Cmd_Args.h"

using namespace std;

void keep_only_train(const string &rep_path, const MedRegistry &regRecords
	, vector<MedRegistryRecord> &only_train, MedRepository &rep);

void filterAge(map<float, map<float, vector<int>>> &dict, int min_age, int max_age);

void print_gender(const map<float, vector<int>> &gender_stats, const string &genderName,
	stat_test stat_type, int smooth_balls, float at_least, int minimal_count, float filter_fisher_smooth);

void calc_fisher_scores(const map<float, map<float, vector<int>>> &male_stats,
	const map<float, map<float, vector<int>>> &female_stats,
	vector<int> &all_signal_values, vector<int> &signal_indexes,
	vector<double> &valCnts, vector<double> &posCnts,
	vector<double> &lift, vector<double> &scores,
	vector<double> &p_values, vector<double> &pos_ratio, float fisher_band);

void print_top(MedRepository &dataManager, int sectionId, const string &signalHirerchyType,
	const vector<int> &signal_indexes, const vector<int> &signal_values,
	const vector<double> &total_cnts, const vector<double> &pos_cnts, const vector<double> &lift,
	const vector<double> &scores, const vector<double> &p_values, const vector<double> &pos_ratio,
	const vector<int> &dof, const string &hir_filter = "", bool use_fixed_lift = false);

#endif // !__REGISTRY_HELPER__