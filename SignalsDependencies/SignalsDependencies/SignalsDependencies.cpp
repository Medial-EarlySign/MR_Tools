// SignalsDependencies.cpp : Defines the entry point for the console application.
//

#include <vector>
#include "MedUtils/MedUtils/MedRegistry.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "MedProcessTools/MedProcessTools/MedSamples.h"
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "Logger/Logger/Logger.h"
#include "Cmd_Args.h"
#include "RegistryHelper.h"
#include <random>
#include <algorithm>
#include <cstring>
#include <unordered_map>
#include <fenv.h>
#ifndef  __unix__
#pragma float_control( except, on )
#endif

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

using namespace std;

int count_legal_rows(const  map<float, vector<int>> &m, int minimal_balls) {
	int res = 0;
	for (auto it = m.begin(); it != m.end(); ++it)
	{
		int ind = 0;
		bool all_good = true;
		while (all_good && ind < it->second.size()) {
			all_good = it->second[ind] >= minimal_balls;
			++ind;
		}
		res += int(all_good);
	}
	return res;
}


void read_registry(MedRepository &dataManager, const ProgramArgs &args, vector<MedRegistryRecord> &registry_records) {
	ifstream testFile(args.registry_path);
	if (!args.registry_path.empty() && testFile.good()) { //load from file
		MLOG("Reading registry from %s\n", args.registry_path.c_str());
		MedRegistry reg;
		vector<int> pids;
		vector<int> readSignals;
		reg.read_text_file(args.registry_path);
		registry_records.swap(reg.registry_records);

		testFile.close();
	}
	else {
		MedPidRepository rep;
		MedRegistryCodesList registry;
		registry.init_from_string(args.registry_init_cmd);
		vector<int> empty_vec;
		vector<string> sigs;
		registry.get_registry_creation_codes(sigs);
		vector<string> physical_signal;
		medial::repository::prepare_repository(rep, sigs, physical_signal);
		if (rep.read_all(args.global_rep, empty_vec, sigs) < 0)
			MTHROW_AND_ERR("can't read repositoty\n");

		registry.create_registry(rep);
		registry_records.swap(registry.registry_records);
		medial::print::print_reg_stats(registry_records);
	}

	//Filter TRAIN==1 if true
	if (args.registry_filter_train) {
		int before_cnt = (int)registry_records.size();
		MedRegistry reg_obj;
		reg_obj.registry_records.swap(registry_records);
		keep_only_train(args.global_rep, reg_obj, registry_records, dataManager);
		MLOG("Filtering TRAIN==1, registry had %d records, after filter has %d records\n",
			before_cnt, (int)registry_records.size());
	}

	if (!args.registry_save.empty()) {
		MedRegistry reg;
		reg.registry_records = registry_records;
		reg.write_text_file(args.registry_save);
	}

	medial::print::print_reg_stats(registry_records);
}

void runTillFilter(MedRepository &dataManager, const ProgramArgs &args,
	map<float, map<float, vector<int>>> &males, map<float, map<float, vector<int>>> &females) {
	ifstream test_stats(args.global_stats_path);
	if (!args.global_stats_path.empty() && !args.global_override && test_stats.good()) {
		medial::contingency_tables::read_stats(args.global_stats_path, males, females);
		if (args.filter_gender != 3) {
			if (args.filter_gender == GENDER_MALE) {
				MLOG("Filter female stats - using only males\n");
				females.clear();
			}
			else if (args.filter_gender == GENDER_FEMALE) {
				MLOG("Filter male stats - using only females\n");
				males.clear();
			}
			else
				MTHROW_AND_ERR("Error in filter_gender(%d) - must be in [1-3]. Males is 1st bit, females 2nd bit\n",
					args.filter_gender);
		}
		return;
	}

	vector<MedRegistryRecord> registry_records;
	read_registry(dataManager, args, registry_records);
	if (args.sub_sample_pids > 0) {
		unordered_set<int> seen_p;
		for (size_t i = 0; i < registry_records.size(); ++i)
			seen_p.insert(registry_records[i].pid);
		int pid_cnt = (int)seen_p.size();
		if (pid_cnt <= args.sub_sample_pids)
			MLOG("Subsample ignored. has %d pids, subsample is set to %d\n", pid_cnt, args.sub_sample_pids);
		else {
			MLOG("Subsampling - has %d pids, subsample is set to %d\n", pid_cnt, args.sub_sample_pids);
			vector<int> all_pids(seen_p.begin(), seen_p.end());
			sort(all_pids.begin(), all_pids.end());
			random_device rd;
			mt19937 gen(rd());
			uniform_int_distribution<> sel_pids(0, (int)all_pids.size() - 1);
			unordered_set<int> sel_p;
			for (size_t i = 0; i < args.sub_sample_pids; ++i)
			{
				int sel = sel_pids(gen);
				while (sel_p.find(all_pids[sel]) != sel_p.end())
					sel = sel_pids(gen);
				sel_p.insert(all_pids[sel]);
			}

			//use sel_p to filter pids from registry_records:
			vector<MedRegistryRecord> registry_records_sub;
			for (size_t i = 0; i < registry_records.size(); ++i)
				if (sel_p.find(registry_records[i].pid) != sel_p.end())
					registry_records_sub.push_back(registry_records[i]);
			registry_records = move(registry_records_sub);
		}
	}

	string debug_out = "";
	unordered_set<int> debug_vals;
	if (args.output_debug) {
		debug_out = args.output_full_path;
		debug_vals.insert((int)args.output_value);
	}
	MedRegistry censor_reg;
	if (!args.censoring_registry_path.empty()) {
		censor_reg.read_text_file(args.censoring_registry_path);
	}
	else if (!args.censoring_registry_args.empty()) {
		MedModel empty_model;
		MedRegistry *temp = MedRegistry::create_registry_full(args.censoring_registry_type,
			args.censoring_registry_args, args.global_rep, empty_model);
		censor_reg.registry_records.swap(temp->registry_records);
		delete temp;
	}
	MedLabels reg_labeler(args.labeling_params);
	reg_labeler.prepare_from_registry(registry_records, &censor_reg.registry_records);

	char buffer[500];
	snprintf(buffer, sizeof(buffer), "start_age=%d;end_age=%d;age_bin=%d",
		(int)args.filter_min_age, (int)args.filter_max_age, args.global_age_bin);
	string sample_args = string(buffer);

	MedSamplingStrategy *sampler = MedSamplingStrategy::make_sampler("age", sample_args);

	string signal_hir = args.test_hierarchy; //can be "" or "None" to skip filter by regex. otherwise it's regex filter
	if (args.test_hierarchy == "None")
		signal_hir = "";

	reg_labeler.calc_signal_stats(args.global_rep, args.test_main_signal, signal_hir,
		args.global_age_bin, *sampler, args.inc_labeling_params, males, females, debug_out, debug_vals);
	delete sampler;

	MLOG("creating statistic table with size %d in males and %d in females\n",
		(int)males.size(), (int)females.size());
	ifstream testF(args.global_stats_path);
	if (!args.global_stats_path.empty() && (args.global_override || !testF.good()))
		medial::contingency_tables::write_stats(args.global_stats_path, males, females);
}

void runFilterToResults(MedRepository &dataManager, const ProgramArgs &args,
	map<float, map<float, vector<int>>> &males, map<float, map<float, vector<int>>> &females) {
	if (args.output_value > 0) {
		filterAge(males, (int)args.filter_min_age, (int)args.filter_max_age);
		filterAge(females, (int)args.filter_min_age, (int)args.filter_max_age);
		MLOG("After Filter Age [%d - %d] have %d keys in males and %d keys in females\n",
			int(args.filter_min_age), int(args.filter_max_age), (int)males.size(), (int)females.size());
		MLOG("using %s statistical test\n", args.stat_test_type.c_str());
		MLOG("Test Signal:%d - %s\n\n", int(args.output_value),
			dataManager.dict.name(dataManager.dict.section_id(args.test_main_signal), (int)args.output_value).c_str());
		print_gender(males[args.output_value], "Males", args.filter_stats_test,
			args.filter_chi_smooth, args.filter_chi_at_least, args.filter_chi_minimal,
			args.filter_fisher_smooth);
		print_gender(females[args.output_value], "Females", args.filter_stats_test,
			args.filter_chi_smooth, args.filter_chi_at_least, args.filter_chi_minimal,
			args.filter_fisher_smooth);
	}
	else {
		if (dataManager.dict.SectionName2Id.find(args.test_main_signal) == dataManager.dict.SectionName2Id.end())
			MWARN("Warnning!! Test Lookup Section Name %s wasn't found. using default section\n", args.test_main_signal.c_str());
		int sectionId = dataManager.dict.section_id(args.test_main_signal);
		MLOG("using %s statistical test\n", args.stat_test_type.c_str());

		//Step 2 - Filtering
		filterAge(males, (int)args.filter_min_age, (int)args.filter_max_age);
		filterAge(females, (int)args.filter_min_age, (int)args.filter_max_age);
		MLOG("After Filter Age [%d - %d] have %d keys in males and %d keys in females\n",
			int(args.filter_min_age), int(args.filter_max_age), (int)males.size(), (int)females.size());

		vector<int> all_signal_values;
		vector<int> signal_indexes;
		vector<double> total_cnts, pos_cnts, lift, scores, p_values, pos_ratio;
		switch (args.filter_stats_test)
		{
		case stat_test::chi_square:
			medial::contingency_tables::calc_chi_scores(males, females, all_signal_values
				, signal_indexes, total_cnts, pos_cnts, lift, scores,
				p_values, pos_ratio, args.filter_chi_smooth, args.filter_chi_at_least,
				args.filter_chi_minimal);
			break;
		case stat_test::fisher:
			calc_fisher_scores(males, females, all_signal_values
				, signal_indexes, total_cnts, pos_cnts, lift, scores,
				p_values, pos_ratio, args.filter_fisher_smooth);
			break;
		case stat_test::mcnemar:
			medial::contingency_tables::calc_mcnemar_scores(males, females, all_signal_values
				, signal_indexes, total_cnts, pos_cnts, lift, scores,
				p_values, pos_ratio);
			break;
		case stat_test::cmh:
			medial::contingency_tables::calc_cmh_scores(males, females, all_signal_values
				, signal_indexes, total_cnts, pos_cnts, lift, scores,
				p_values, pos_ratio);
			break;
		default:
			MTHROW_AND_ERR("unsupported statstical_test - %s\n", args.stat_test_type.c_str());
		}
		MLOG("creating scores vector with size %d\n", (int)signal_indexes.size());
		unordered_map<int, double> code_cnts;
		for (size_t i = 0; i < all_signal_values.size(); ++i)
			code_cnts[all_signal_values[i]] = total_cnts[i];

		//Filter - total counts and p_value
		medial::contingency_tables::FilterRange(signal_indexes, total_cnts, args.filter_total_cnt, INT_MAX); //at least 1000 counts for signal
		MLOG("After total filter has %d signal values\n", (int)signal_indexes.size());
		medial::contingency_tables::FilterRange(signal_indexes, pos_cnts, args.filter_positive_cnt, INT_MAX); //at least 50 counts for signal with registry
		MLOG("After positive filter has %d signal values\n", (int)signal_indexes.size());
		medial::contingency_tables::FilterRange(signal_indexes, pos_ratio, args.filter_min_ppv, 1); //filter mean ratio
		MLOG("After positive ratio filter has %d signal values\n", (int)signal_indexes.size());
		//Filter - hirarchy:
		if (args.test_hierarchy != "None") {
			medial::contingency_tables::filterHirarchy(dataManager.dict.dict(sectionId)->Member2Sets, dataManager.dict.dict(sectionId)->Set2Members,
				signal_indexes, all_signal_values, p_values, total_cnts, lift, code_cnts, args.filter_child_pval_diff, args.filter_child_lift_ratio,
				args.filter_child_count_ratio, args.filter_child_removed_ratio);
			MLOG("After Hirarchy filter has %d signal values\n", (int)signal_indexes.size());
		}
		vector<int> filter_tops(signal_indexes), filter_bottoms(signal_indexes);
		medial::contingency_tables::FilterRange(filter_tops, lift, args.filter_positive_lift, INT_MAX);
		medial::contingency_tables::FilterRange(filter_bottoms, lift, -1, args.filter_negative_lift);
		//join both results from up and down filters on the lift:
		signal_indexes.swap(filter_tops);
		signal_indexes.insert(signal_indexes.end(), filter_bottoms.begin(), filter_bottoms.end());
		MLOG("After lifts has %d signal values\n", (int)signal_indexes.size());
		medial::contingency_tables::FilterFDR(signal_indexes, scores, p_values, lift, args.filter_pval_fdr);
		MLOG("AfterFDR has %d signal values\n", (int)signal_indexes.size());

		vector<int> dof(all_signal_values.size());
		for (int index : signal_indexes) {
			dof[index] = -1;
			if (males.find(all_signal_values[index]) != males.end())
				dof[index] += count_legal_rows(males[all_signal_values[index]], args.filter_stats_test == stat_test::chi_square ? args.filter_chi_minimal : 0);
			if (females.find(all_signal_values[index]) != females.end())
				dof[index] += count_legal_rows(females[all_signal_values[index]], args.filter_stats_test == stat_test::chi_square ? args.filter_chi_minimal : 0);
		}

		//print results
		print_top(dataManager, sectionId, args.test_main_signal, signal_indexes, all_signal_values,
			total_cnts, pos_cnts, lift, scores, p_values, pos_ratio, dof, args.test_hierarchy, false);
	}
}

static void _get_parents(int codeGroup, vector<int> &parents, bool has_regex, const regex &reg_pat,
	int max_depth, int max_parents, const map<int, vector<int>> &_member2Sets, const map<int, vector<string>> &categoryId_to_name) {
	vector<int> last_parents = { codeGroup };
	if (last_parents.front() < 0)
		return; //no parents
	parents = {};

	for (size_t k = 0; k < max_depth; ++k) {
		vector<int> new_layer;
		for (int par : last_parents)
			if (_member2Sets.find(par) != _member2Sets.end()) {
				new_layer.insert(new_layer.end(), _member2Sets.at(par).begin(), _member2Sets.at(par).end());
				parents.insert(parents.end(), _member2Sets.at(par).begin(), _member2Sets.at(par).end()); //aggregate all parents
			}
		if (parents.size() >= max_parents)
			break;
		new_layer.swap(last_parents);
		if (last_parents.empty())
			break; //no more parents to loop up
	}

	if (has_regex) {
		vector<int> filtered_p;
		filtered_p.reserve(parents.size());
		for (int code : parents)
		{
			if (categoryId_to_name.find(code) == categoryId_to_name.end())
				MTHROW_AND_ERR("CategoryDependencyGenerator::post_learn_from_samples - code %d wasn't found in dict\n", code);
			const vector<string> &names = categoryId_to_name.at(code);
			int nm_idx = 0;
			bool pass_regex_filter = false;
			while (!pass_regex_filter && nm_idx < names.size())
			{
				pass_regex_filter = regex_match(names[nm_idx], reg_pat);
				++nm_idx;
			}
			if (pass_regex_filter)
				filtered_p.push_back(code);
		}
		parents.swap(filtered_p);
	}
}

void runFullInspection(MedRepository &dataManager, const ProgramArgs &args) {
	ofstream output_file(args.output_full_path);
	output_file << "PID\t" << "Gender\t" << "Age\t" << "Date\t" << "Signal_Value" << endl;
	output_file << "# This file contain records for specifc signal value for all patients" << endl;
	int testSignals = dataManager.sigs.sid(args.test_main_signal);
	if (testSignals == -1)
		MTHROW_AND_ERR("Unknown Main Test Signal %s\n", args.test_main_signal.c_str());

	int secId = dataManager.dict.section_id(args.test_main_signal);
	if (secId == -1)
		MTHROW_AND_ERR("Unknown Main Test Signal %s - no section id. maybe not categorical?\n", args.test_main_signal.c_str());
	time_t start = time(NULL);
	double duration;
	vector<MedRegistryRecord> signal_final;
	regex reg_empty;
#pragma omp parallel for schedule(dynamic,1)
	for (int i = 0; i < dataManager.pids.size(); ++i)
	{
		UniversalSigVec sig;
		dataManager.uget(dataManager.pids[i], testSignals, sig);
		MedRegistryRecord rec;
		rec.pid = dataManager.pids[i];

		for (int k = 0; k < sig.len; ++k)
		{
			vector<int> all_vals;
			rec.start_date = sig.Time(k);
			_get_parents(sig.Val(k), all_vals, false, reg_empty, 50, 500, dataManager.dict.dict(secId)->Member2Sets,
				dataManager.dict.dict(secId)->Id2Names);
			all_vals.push_back(sig.Val(k));
			for (size_t kk = 0; kk < all_vals.size(); ++kk)
			{
				if (all_vals[kk] == args.output_value)
#pragma omp critical 
					signal_final.push_back(rec);
			}

		}
	}
	dataManager.clear();

	MLOG("Fetched %d records.\n", (int)signal_final.size());

	start = time(NULL);
	int ln = 1;
	for (MedRegistryRecord sigRec : signal_final) {
		if (ln % 1000000 == 0) {
			ln = 0;
			output_file << sigRec.pid << "\t" << sigRec.start_date << "\t" << sigRec.registry_value << endl;
		}
		else
			output_file << sigRec.pid << "\t" << sigRec.start_date << "\t" << sigRec.registry_value << "\n";

		++ln;
	}

	duration = (int)difftime(time(NULL), start);
	MLOG("Finished Writing in %d seconds\n", (int)duration);
	output_file.close();
}

int main(int argc, char *argv[])
{
#if defined(__unix__)
	//feenableexcept(FE_DIVBYZERO | FE_INVALID | FE_OVERFLOW);
#endif
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0) {
		return -1;
	}
	if (!args.global_rep.empty())
		medial::repository::set_global_time_unit(args.global_rep);

	MedRepository dataManager;

	map<float, map<float, vector<int>>> males, females;
	if (args.output_value > 0 && !args.output_full_path.empty() && args.output_debug == 0) {
		if (dataManager.init(args.global_rep) < 0)
			MTHROW_AND_ERR("Error reading repository %s\n", args.global_rep.c_str());
		runFullInspection(dataManager, args);
		return 0;
	}

	runTillFilter(dataManager, args, males, females);
	if (dataManager.dict.read_state == 0 && dataManager.init(args.global_rep) < 0)  //after creating data - need to prepare dataManager
		MTHROW_AND_ERR("Error reading repository %s\n", args.global_rep.c_str());

	//continue Filter and results
	runFilterToResults(dataManager, args, males, females);

	return 0;
}

