#include "Cmd_Args.h"
#include <MedStat/MedStat/MedBootstrap.h>
#include <MedProcessTools/MedProcessTools/ExplainWrapper.h>

class metric_val {
public:
	string metric_name = "";
	float value = MED_MAT_MISSING_VALUE;
	float lower_ci = MED_MAT_MISSING_VALUE;
	float upper_ci = MED_MAT_MISSING_VALUE;
	string str() const {
		stringstream buff;
		if (value != MED_MAT_MISSING_VALUE)
			buff << value;
		else
			buff << "EMPTY";
		buff << "\t";
		if (lower_ci != MED_MAT_MISSING_VALUE)
			buff << lower_ci;
		else
			buff << "EMPTY";
		buff << "\t";
		if (upper_ci != MED_MAT_MISSING_VALUE)
			buff << upper_ci;
		else
			buff << "EMPTY";
		return buff.str();
	}
};

map<string, metric_val> extract_measurements(const map<string, float> &res, const string &regex) {
	map<string, metric_val> ret;
	//Aggregate with confidence intervals
	boost::regex reg_pat(regex);
	for (auto & it : res)
	{
		bool found = boost::regex_search(it.first, reg_pat);
		if (!found)
			continue;
		string metric_name = it.first;
		if (boost::ends_with(it.first, "_Mean")) {
			metric_name = boost::replace_last_copy(metric_name, "_Mean", "");
			ret[metric_name].value = it.second;
		}
		else if (boost::ends_with(it.first, "_CI.Lower.95")) {
			metric_name = boost::replace_last_copy(metric_name, "_CI.Lower.95", "");
			ret[metric_name].lower_ci = it.second;
		}
		else if (boost::ends_with(it.first, "_CI.Upper.95")) {
			metric_name = boost::replace_last_copy(metric_name, "_CI.Upper.95", "");
			ret[metric_name].upper_ci = it.second;
		}
		else if (boost::ends_with(it.first, "_Obs")) {
			continue;
		}
		else if (boost::ends_with(it.first, "_Std")) {
			continue;
		}
		else
			continue;
		ret[metric_name].metric_name = metric_name;

	}

	return ret;
}

void filter_sig_time_win(MedPidRepository &rep, const MedSamples &samples, const vector<string> &signal,
	int time_win, MedSamples &res, bool any = true) {
	vector<MedSample> smps, filters_smps;
	samples.export_to_sample_vec(smps);
	filters_smps.reserve(smps.size());
	//Filter smps - 
	vector<UniversalSigVec> usvs(signal.size());
	vector<int> sids(signal.size());
	for (size_t i = 0; i < signal.size(); ++i) {
		sids[i] = rep.sigs.sid(signal[i]);
		if (sids[i] < 0)
			MTHROW_AND_ERR("Error - can't find signal %s\n", signal[i].c_str());
	}
	for (size_t i = 0; i < smps.size(); ++i)
	{
		int time_limit_end = smps[i].time;
		int time_limit_start = med_time_converter.add_subtruct_days(smps[i].time, -time_win);
		vector<bool> exists_vec(signal.size());
		for (size_t j = 0; j < signal.size(); ++j)
		{
			UniversalSigVec &usv = usvs[j];
			rep.uget(smps[i].id, sids[j], usv);
			for (int k = 0; k < usv.len; ++k)
			{
				if (usv.Time(k) > time_limit_end)
					break;
				if (usv.Time(k) < time_limit_start)
					continue;
				exists_vec[j] = true;
				break;
			}
		}

		bool exists = false;
		if (any) {
			for (size_t j = 0; j < exists_vec.size() && !exists; ++j)
				exists = exists_vec[j];

		}
		else { //all
			exists = true;
			for (size_t j = 0; j < exists_vec.size() && exists; ++j)
				exists = exists_vec[j];
		}
		if (exists)
			filters_smps.push_back(smps[i]);
	}

	res.import_from_sample_vec(filters_smps);
	res.sort_by_id_date();
}

unordered_map<string, string> read_group_to_sigal(const string &file_path) {
	ifstream file_r(file_path);
	if (!file_r.good())
		MTHROW_AND_ERR("Error Can't read %s\n", file_path.c_str());
	string line;
	unordered_map<string, string> res;
	while (getline(file_r, line)) {
		mes_trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("Error - bad file format in line:\n%s\nExpecting 2 tokens tab delimeted in file %s\n",
				line.c_str(), file_path.c_str());
		mes_trim(tokens[0]);
		mes_trim(tokens[1]);
		res[tokens[0]] = tokens[1];
	}
	file_r.close();
	return res;
}

void write_header(const map<string, metric_val> &res, ofstream &fw) {
	fw << "Test_description" << "\t" << "#samples";
	fw << "\t" << "#unique_patients" << "\t" << "#controls" << "\t" << "#cases";
	for (const auto &it : res) {
		const metric_val &m_v = it.second;
		fw << "\t" << m_v.metric_name << "_Mean\t" << m_v.metric_name << "_Lower\t"
			<< m_v.metric_name << "_Upper";
	}
	fw << endl;

}
void write_file(const map<string, metric_val> &res, const string &prefix, int sz,
	int num_pids, int num_controls, int num_cases, ofstream &fw) {
	fw << prefix << "\t" << sz;
	fw << "\t" << num_pids << "\t" << num_controls << "\t" << num_cases;
	for (const auto &it : res) {
		const metric_val &m_v = it.second;
		fw << "\t" << m_v.str();
	}

	fw << endl;
}

void add_history_limit(MedModel &model, const vector<string> &sigsToDelete) {
	vector<RepProcessor*> cleaningRepProcess;
	for (auto & sig : sigsToDelete)
	{
		string params = "delete_sig=1;signal=" + sig;
		RepProcessor* deleteRepProcess = RepProcessor::make_processor("history_limit", params);
		cleaningRepProcess.push_back(deleteRepProcess);
	}

	model.rep_processors.insert(model.rep_processors.begin(), cleaningRepProcess.begin(), cleaningRepProcess.end());
}
void delete_history_limit(MedModel &model, int add_cnt) {
	int end_id = (int)model.rep_processors.size() - add_cnt;
	assert(end_id >= 0);
	for (size_t i = 0; i < add_cnt; ++i)
		delete model.rep_processors[i];
	//move the rest to the 
	for (size_t i = 0; i < end_id; ++i)
		model.rep_processors[i] = model.rep_processors[i + add_cnt];

	//resize - to remove last:
	model.rep_processors.resize(end_id);
}

void fetch_diff(const map<string, metric_val> &res_with, const map<string, metric_val> &res_without,
	map<string, metric_val> &res_diff) {
	for (auto &it : res_with)
	{
		if (res_without.find(it.first) == res_without.end())
			MTHROW_AND_ERR("Error metric %s wasn't found in without\n", it.first.c_str());
		const metric_val &with_m = it.second;
		const metric_val &without_m = res_without.at(it.first);
		metric_val &res_m = res_diff[it.first]; //edit res_m
		if (with_m.value != MED_MAT_MISSING_VALUE && without_m.value != MED_MAT_MISSING_VALUE)
			res_m.value = (with_m.value - without_m.value);

	}
}

void extract_samples_stats(MedSamples &samples, int &num_samples,
	int &num_pids, int &num_controls, int &num_cases) {
	num_pids = (int)samples.idSamples.size();
	num_controls = 0;
	num_cases = 0;
	num_samples = 0;
	for (size_t i = 0; i < num_pids; ++i)
	{
		for (size_t j = 0; j < samples.idSamples[i].samples.size(); ++j)
		{
			if (samples.idSamples[i].samples[j].outcome > 0)
				++num_cases;
			else
				++num_controls;
		}
		num_samples += (int)samples.idSamples[i].samples.size();
	}
}

int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return 1;
	MedSamples samples;
	MedModel model;
	MedPidRepository rep;
	if (samples.read_from_file(args.samples) < 0)
		MTHROW_AND_ERR("Error - can't read samples %s\n", args.samples.c_str());
	if (model.read_from_file(args.model_path) < 0)
		MTHROW_AND_ERR("Error - can't read model %s\n", args.model_path.c_str());
	MedBootstrap bt;
	if (!args.bt_args.empty())
		bt.init_from_string(args.bt_args);
	if (rep.init(args.rep) < 0)
		MTHROW_AND_ERR("Error - can't read repository %s\n", args.rep.c_str());

	if (!args.bt_filter_cohort.empty())
		MedBootstrap::filter_bootstrap_cohort(args.rep, args.bt_filter_json, samples, args.bt_filter_cohort);
	if (samples.idSamples.size() == 0)
		MTHROW_AND_ERR("Error samples is empty after filtering\n");
	MLOG("After bootstrap filtering left with %d samples\n", samples.nSamples());
	medial::process::down_sample(samples, args.down_sample_max_count);

	map<string, vector<float>> empty;
	//Fetch groups for processings:
	vector<string> features;
	features = model.predictor->model_features;
	vector<vector<int>> grp2ind; ///< for each "index" matched group_names, name of group and vector of "features" indexes.
	vector<string> group_names;
	ExplainProcessings::read_feature_grouping(args.features_groups, features, grp2ind, group_names);

	unordered_map<string, string> group2signal;
	if (!args.group2signal.empty())
		group2signal = read_group_to_sigal(args.group2signal);
	unordered_set<string> skip_list_set(args.skip_list.begin(), args.skip_list.end());
	//Test all signals exists in rep
	model.fit_for_repository(rep);
	unordered_set<string> needed_sigs;
	model.get_required_signal_names(needed_sigs);

	map<string, string> final_grp_set;
	for (size_t i = 0; i < group_names.size(); ++i)
	{
		const string &group_name = group_names[i];
		if (skip_list_set.find(group_name) != skip_list_set.end())
			continue;
		string signal_name = group_name;
		if (group2signal.find(group_name) != group2signal.end())
			signal_name = group2signal.at(group_name);
		vector<string> all_sigs;
		boost::split(all_sigs, signal_name, boost::is_any_of(","));
		for (size_t j = 0; j < all_sigs.size(); ++j)
		{
			int sid = rep.sigs.sid(all_sigs[j]);
			if (sid <= 0)
				MTHROW_AND_ERR("Error - unknown signal %s for group %s in repository, please map this group to known signal using group2signal argument\n",
					all_sigs[j].c_str(), group_name.c_str());
			needed_sigs.insert(all_sigs[j]);
		}

		if (final_grp_set.find(signal_name) != final_grp_set.end())
			final_grp_set[signal_name] = signal_name;
		else
			final_grp_set[signal_name] = group_name;
	}
	vector<string> final_group_list;
	for (auto &it : final_grp_set)
		final_group_list.push_back(it.second);

	vector<string> rep_sigs(needed_sigs.begin(), needed_sigs.end());
	vector<int> pids;
	samples.get_ids(pids);
	if (rep.read_all(args.rep, pids, rep_sigs) < 0)
		MTHROW_AND_ERR("Error - can't read repository %s\n", args.rep.c_str());

	ofstream file_w(args.output);
	if (!file_w.good())
		MTHROW_AND_ERR("Error, can't open file %s for write\n", args.output.c_str());

	//calc performance in full cohort as refernece
	int pred_size;
	int samples_size, unique_ids, num_controls, num_cases;
	if (samples.get_predictions_size(pred_size) < 0)
		MTHROW_AND_ERR("Error has variable length of preds\n");
	if (pred_size > 0) {
		map<string, float> res_general = bt.bootstrap(samples, empty).at("All");
		map<string, metric_val> res_general_m = extract_measurements(res_general, args.measure_regex);
		write_header(res_general_m, file_w);

		extract_samples_stats(samples, samples_size, unique_ids, num_controls, num_cases);

		write_file(res_general_m, "General cohort", samples_size, unique_ids, num_controls, num_cases, file_w);
	}
	else {
		MWARN("INFO:: no predictions in samples file. Will not print performance in full current cohort\n");
	}
	//calc in any sub cohort (after eliminating the feature). 
	// select signal => time window
		//print cohort size, Selected measurements with data as input, without signal as input, calc diff.
	MedProgress progress("Analyze_Group_Importance", (int)final_group_list.size(), 30, 1);
	for (size_t i = 0; i < final_group_list.size(); ++i)
	{
		const string &group_name = final_group_list[i];


		const vector<int> &feature_idx = grp2ind[i];
		string signal_name = group_name;
		if (group2signal.find(group_name) != group2signal.end())
			signal_name = group2signal.at(group_name);
		vector<string> all_sig_names;
		boost::split(all_sig_names, signal_name, boost::is_any_of(","));
		for (size_t j = 0; j < args.time_windows.size(); ++j)
		{
			int time_win = args.time_windows[j];
			MLOG("Analyzing group %s (with signal %s) with %zu features for time window %d...\n",
				group_name.c_str(), signal_name.c_str(), feature_idx.size(), time_win);
			//1. Filter cohort -> all_sig_names in time window exists
			MedSamples filtered;
			if (args.no_filtering_of_existence)
				filtered = samples;
			else
				filter_sig_time_win(rep, samples, all_sig_names, time_win, filtered);
			extract_samples_stats(filtered, samples_size, unique_ids, num_controls, num_cases);
			if (samples_size <= args.min_group_analyze_size) {
				MLOG("WARN signal %s is too small to analyze in time window %d. There are only %d records\n",
					signal_name.c_str(), time_win, samples_size);
				continue;
			}
			//2. Apply model on filtered
			model.apply(rep, filtered);
			//3. measure performace
			map<string, float> pref_with_signal = bt.bootstrap(filtered, empty).at("All");
			//4. Apply model on filtered with history limit
			add_history_limit(model, all_sig_names);
			model.apply(rep, filtered);
			//return model to original:
			delete_history_limit(model, (int)all_sig_names.size());
			//5. measure performace on history limit
			map<string, float> pref_without_signal = bt.bootstrap(filtered, empty).at("All");
			//6. Check If need to write header
			if (pred_size <= 0) {
				map<string, metric_val> temp_meas = extract_measurements(pref_with_signal, args.measure_regex);
				write_header(temp_meas, file_w);
				pred_size = 1; //mark as written header
			}
			//7. calculate diff
			map<string, metric_val> diff_signal;
			fetch_diff(extract_measurements(pref_with_signal, args.measure_regex),
				extract_measurements(pref_without_signal, args.measure_regex), diff_signal);
			//8. store results in file pref_with_signal, pref_without_signal
			write_file(extract_measurements(pref_with_signal, args.measure_regex),
				"Group:" + group_name + ":time_window:" + to_string(time_win) + ":with_signals", samples_size, unique_ids, num_controls, num_cases, file_w);
			write_file(extract_measurements(pref_without_signal, args.measure_regex),
				"Group:" + group_name + ":time_window:" + to_string(time_win) + ":no_signals", samples_size, unique_ids, num_controls, num_cases, file_w);
			write_file(diff_signal,
				"Group:" + group_name + ":time_window:" + to_string(time_win) + ":difference", samples_size, unique_ids, num_controls, num_cases, file_w);
		}
		progress.update();
	}

	//End write report
	file_w.close();
	MLOG("Wrote %s report file\n", args.output.c_str());
	return 0;
}