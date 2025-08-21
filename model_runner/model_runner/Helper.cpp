#include "Helper.h"
#include <map>
#include <fstream>
#include <boost/algorithm/string.hpp>
#include <boost/spirit/home/support/detail/hold_any.hpp>
#include <boost/filesystem.hpp>
#include "MedAlgo/MedAlgo/BinSplitOptimizer.h"
#include "MedProcessTools/MedProcessTools/Calibration.h"
#include <omp.h>
#include <random>
#include <regex>

unordered_map<string, int> conversion_map = {
	{ "propensity", propensity } ,
	{ "propensity_controls", propensity_controls } ,
	{ "outcome_event", outcome_event }
};
int weights_params::init(map<string, string>& map) {
	for (auto it = map.begin(); it != map.end(); ++it)
	{
		if (it->first == "base_folder_path")
			base_folder_path = it->second;
		else if (it->first == "medmodel_path")
			medmodel_path = it->second;
		else if (it->first == "predictor_path")
			predictor_path = it->second;
		else if (it->first == "predictor_type")
			predictor_type = it->second;
		else if (it->first == "feature_selection_path")
			feature_selection_path = it->second;
		else if (it->first == "registry_path")
			registry_path = it->second;
		else if (it->first == "censor_registry_path")
			censor_registry_path = it->second;
		else if (it->first == "censor_registry_signal")
			censor_registry_signal = it->second;
		else if (it->first == "sampler_type")
			sampler_type = it->second;
		else if (it->first == "sampler_params")
			sampler_params = it->second;
		else if (it->first == "calibration_init")
			calibration_init = it->second;
		else if (it->first == "change_action_prior")
			change_action_prior = stof(it->second);
		else if (it->first == "nfolds")
			nfolds = med_stoi(it->second);
		else if (it->first == "down_sample_to")
			down_sample_to = med_stoi(it->second);
		else if (it->first == "norm_weight_condition")
			norm_weight_condition = it->second;
		else if (it->first == "medmodel_has_predictor")
			medmodel_has_predictor = med_stof(it->second) > 0;
		else if (it->first == "medmodel_has_calibrator")
			medmodel_has_calibrator = med_stof(it->second) > 0;
		else if (it->first == "secondery_medmodel_path")
			secondery_medmodel_path = it->second;
		else if (it->first == "train_samples")
			train_samples = it->second;
		else if (it->first == "labeling_params")
			labeling_params.init_from_string(it->second);
		else if (it->first == "norm_all")
			norm_all = med_stoi(it->second) > 0;
		else if (it->first == "method") {
			if (conversion_map.find(it->second) != conversion_map.end())
				method = weighting_method(conversion_map.at(it->second));
			else
				MTHROW_AND_ERR("Unknown method \"%s\". options are: %s\n",
					it->second.c_str(), medial::io::get_list(conversion_map).c_str());
		}
		else
			MTHROW_AND_ERR("Unknown param \"%s\"\n", it->first.c_str());
	}

	//update default
	if (medmodel_path.empty())
		if (!base_folder_path.empty())
			medmodel_path = base_folder_path + path_sep() +
			"config_params" + path_sep() + "full_model.medmdl";
	if (predictor_path.empty())
		if (!base_folder_path.empty())
			predictor_path = base_folder_path + path_sep() +
			"config_params" + path_sep() + "best_model.mdl";
	if (feature_selection_path.empty())
		if (!base_folder_path.empty()) {
			if (file_exists(base_folder_path + path_sep() +
				"config_params" + path_sep() + "final_selection.list"))
				feature_selection_path = base_folder_path + path_sep() +
				"config_params" + path_sep() + "final_selection.list";
			else
				feature_selection_path = base_folder_path + path_sep() +
				"config_params" + path_sep() + "selected_signals.list";
		}
	if (predictor_type.empty())
		if (!base_folder_path.empty()) {
			string predictor_params;
			read_selected_model(base_folder_path + path_sep() +
				"config_params" + path_sep() + "selected_model.params",
				predictor_type, predictor_params);
		}

	if (medmodel_path.empty() || (!medmodel_has_predictor && (predictor_path.empty() || feature_selection_path.empty()
		|| predictor_type.empty())))
		MTHROW_AND_ERR("Missing init argument for assign_weights. please fill:\n"
			"medmodel_path,predictor_path,feature_selection_path,predictor_type"
			" or base_folder_path");
	active = true;

	return 0;
}

int compare_model_params::init(map<string, string>& map) {
	for (auto it = map.begin(); it != map.end(); ++it)
	{
		if (it->first == "model_path")
			model_path = it->second;
		else if (it->first == "selected_features_file")
			selected_features_file = it->second;
		else if (it->first == "final_score_calc")
			final_score_calc = it->second;
		else if (it->first == "predictor_type")
			predictor_type = it->second;
		else if (it->first == "predictor_path")
			predictor_path = it->second;
		else if (it->first == "need_learn")
			need_learn = stoi(it->second) > 0;
		else
			MTHROW_AND_ERR("Error in compare_model_params::init unknown parameter \"%s\"\n",
				it->first.c_str());
	}

	if (model_path.empty())
		MTHROW_AND_ERR("Error in compare_model_params::init model_path must be provided\n");

	return 0;
}

static unordered_map<string, int> _conv_map_stats = {
	{ "chi-square", (int)stat_test::chi_square },
	{ "fisher", (int)stat_test::fisher },
	{ "mcnemar", (int)stat_test::mcnemar },
	{ "cmh", (int)stat_test::cmh }
};
signal_dep_filters::signal_dep_filters() {
	//defaults
	minimal_count = 1000;
	fdr = (float)0.05;
	lift_below = (float)0.8;
	lift_above = (float)1.25;
	stat_metric = stat_test::mcnemar;
	chi_square_at_least = 0;
	minimal_chi_cnt = 5;
	filter_child_pval_diff = (float)1e-10;
	filter_child_count_ratio = (float)0.05;
	filter_child_lift_ratio = (float)0.05;
	filter_child_removed_ratio = 1;
}

int signal_dep_filters::init(map<string, string>& map) {
	for (auto it = map.begin(); it != map.end(); ++it)
	{
		if (it->first == "minimal_count")
			minimal_count = med_stoi(it->second);
		else if (it->first == "fdr")
			fdr = med_stof(it->second);
		else if (it->first == "lift_below")
			lift_below = med_stof(it->second);
		else if (it->first == "lift_above")
			lift_above = med_stof(it->second);
		else if (it->first == "filter_child_count_ratio")
			filter_child_count_ratio = med_stof(it->second);
		else if (it->first == "filter_child_lift_ratio")
			filter_child_lift_ratio = med_stof(it->second);
		else if (it->first == "filter_child_pval_diff")
			filter_child_pval_diff = med_stof(it->second);
		else if (it->first == "filter_child_removed_ratio")
			filter_child_removed_ratio = med_stof(it->second);
		else if (it->first == "chi_square_at_least")
			chi_square_at_least = med_stof(it->second);
		else if (it->first == "minimal_chi_cnt")
			minimal_chi_cnt = med_stoi(it->second);
		else if (it->first == "regex_filters")
			boost::split(regex_filters, it->second, boost::is_any_of(","));
		else if (it->first == "stat_metric") {
			if (_conv_map_stats.find(it->second) != _conv_map_stats.end())
				stat_metric = stat_test(_conv_map_stats.at(it->second));
			else
				MTHROW_AND_ERR("Unknown stat_test \"%s\". options are: %s\n",
					it->second.c_str(), medial::io::get_list(_conv_map_stats).c_str());
		}
		else
			HMTHROW_AND_ERR("Unsupported param %s for signal_dep_filters\n", it->first.c_str());
	}
	return 0;
}

unordered_map<string, int> convert_loss_metric{
	{ "AUC",        loss_metric::auc },
	{ "Kendall-Tau", loss_metric::kendall_tau },
	{ "ACCURACY",  loss_metric::accurarcy },
	{ "RMSE",       loss_metric::RMSE }
};
loss_metric get_loss_metric(const string &s) {
	unordered_map<string, int> lowercase_map;
	for (auto it = convert_loss_metric.begin(); it != convert_loss_metric.end(); ++it)
		lowercase_map[boost::to_lower_copy(it->first)] = it->second;
	string ls = boost::to_lower_copy(s);

	if (lowercase_map.find(ls) == lowercase_map.end())
		MTHROW_AND_ERR("ERROR metric not found. supported metrices: %s\n",
			medial::io::get_list(convert_loss_metric).c_str());
	return loss_metric(lowercase_map[ls]);
}
string get_loss_metric_name(loss_metric metric) {
	for (auto it = convert_loss_metric.begin(); it != convert_loss_metric.end(); ++it)
		if (it->second == metric)
			return it->first;
	MTHROW_AND_ERR("Not supported metric %d\n", metric);
}

void read_from_rep(const string &complete_reg_sig, const string &rep_path, MedRegistry &active_reg) {
	MLOG("Complete Active periods using Signal %s\n", complete_reg_sig.c_str());
	MedRepository rep2;
	vector<int> all_pids;
	vector<string> sigs_read = { complete_reg_sig };
	if (rep2.read_all(rep_path, all_pids, sigs_read) < 0)
		MTHROW_AND_ERR("Error reading repository %s\n", rep_path.c_str());
	int sid = rep2.sigs.sid(complete_reg_sig);
	if (rep2.sigs.Sid2Info[sid].n_time_channels != 2)
		MTHROW_AND_ERR("Error signal %s should have 2 time channels, has %d\n",
			complete_reg_sig.c_str(), rep2.sigs.Sid2Info[sid].n_time_channels);
	for (size_t i = 0; i < rep2.pids.size(); ++i)
	{
		MedRegistryRecord rec;
		rec.pid = rep2.pids[i];
		rec.registry_value = 1;

		UniversalSigVec usv;
		rep2.uget(rec.pid, sid, usv);
		for (int k = 0; k < usv.len; ++k)
		{
			rec.start_date = usv.Time(k, 0);
			rec.end_date = usv.Time(k, 1);
			active_reg.registry_records.push_back(rec);
		}
	}
}

void write_string_file(const unordered_set<string> &ls, const string &f_out) {
	ofstream fw(f_out);
	if (!fw.good())
		MTHROW_AND_ERR("IOError: can't open file for writing:\n%s\n", f_out.c_str());
	for (auto it = ls.begin(); it != ls.end(); ++it)
		fw << *it << endl;
	fw.close();
}
void read_string_file(const string &f_in, unordered_set<string> &ls) {
	vector<string> ls_t;
	medial::io::read_codes_file(f_in, ls_t);
	ls.insert(ls_t.begin(), ls_t.end());
}

void update_selected_sigs(unordered_set<string> &selected_sigs,
	const vector<pair<float, string>> &all_scores, float ref, int take_top,
	const string &out_path, const string &log_path, loss_metric metric, bool use_counts) {
	string log_path_fld = log_path;
	if (log_path == "")
		log_path_fld = out_path;

	vector<pair<int, string>> sigCnt;
	map<string, int> sigToInd;
	int currI = 0;
	selected_sigs.insert("Age");
	selected_sigs.insert("Gender");
	ofstream fw(log_path_fld + path_sep() + "FeatureSelectionLog.txt");
	if (!fw.good())
		MERR("IOError: can't open file for writing:\n%s\n", (log_path_fld + path_sep() + "FeatureSelectionLog.txt").c_str());
	fw << "Ref_Score\t" << ref << endl;
	bool is_higher_better = loss_function_order(metric);
	int move_step = is_higher_better ? -1 : 1;
	int start_pos = is_higher_better ? (int)all_scores.size() - 1 : 0;

	for (int i = start_pos; i >= 0 && i < all_scores.size() && currI < take_top; i += move_step)
	{
		vector<string> all_sig_tokens;
		boost::split(all_sig_tokens, all_scores[i].second, boost::is_any_of("|"));
		for (string &sig : all_sig_tokens) {
			boost::trim(sig);
			if (sig.empty())
				continue;
			if (sigToInd.find(sig) == sigToInd.end()) {
				sigToInd[sig] = currI;
				++currI;
				sigCnt.push_back(pair<int, string>(0, sig));
			}
			++sigCnt[sigToInd[sig]].first;
		}
		fw << all_scores[i].second << "\t" << all_scores[i].first << endl;
	}
	fw.close();
	if (use_counts)
		sort(sigCnt.begin(), sigCnt.end(), [](const pair<int, string> &a, const pair<int, string> &b) {
		return a.first < b.first;  });
	else  //sort reverse by the order of insertion:
		std::reverse(sigCnt.begin(), sigCnt.end());

	unordered_set<string> selected_clean(selected_sigs.begin(), selected_sigs.end());
	for (int i = (int)sigCnt.size() - 1; i >= 0; --i) {
		string clean_name = sigCnt[i].second;
		if (boost::starts_with(clean_name, "FTR_"))
			clean_name = clean_name.substr(clean_name.find(".") + 1);
		if (selected_clean.find(clean_name) == selected_clean.end()) {
			selected_clean.insert(clean_name);
			selected_sigs.insert(sigCnt[i].second);
		}
		else if (clean_name != "Age" && clean_name != "Gender")
			MWARN("Warning in update_selected_sigs - got feature \"%s\" which already exists(maybe forced features?) - skipping\n",
				sigCnt[i].second.c_str());
	}

	write_string_file(selected_sigs, out_path + path_sep() + "selected_signals.list");
}

void load_additional_featuress(MedModel &mod, const string &signalName,
	const string &selection_list, int win_from, int win_to) {
	//choosing last tab in each row:
	ifstream fr(selection_list);
	if (!fr.good())
		MTHROW_AND_ERR("IOError: can't read additional features\n");
	string line;
	vector<string> full_sets;
	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		full_sets.push_back(tokens.back());
	}
	fr.close();
	for (size_t i = 0; i < full_sets.size(); ++i)
	{
		FeatureGenerator *feat = FeatureGenerator::make_generator(
			FeatureGeneratorTypes::FTR_GEN_BASIC, "type=category_set;time_unit=Days");
		((BasicFeatGenerator *)feat)->sets = { full_sets[i] };
		((BasicFeatGenerator *)feat)->signalName = signalName;
		((BasicFeatGenerator *)feat)->win_from = win_from;
		((BasicFeatGenerator *)feat)->win_to = win_to;
		((BasicFeatGenerator *)feat)->set_names();
		feat->req_signals.assign(1, signalName);
		mod.add_feature_generator(feat);
	}
}

double prepare_model_from_json(MedSamples &samples,
	const string &RepositoryPath,
	MedModel &mod, MedPidRepository &dataManager, double change_prior) {
	medial::repository::prepare_repository(samples, RepositoryPath, mod, dataManager);
	double change_actual = -1;
	int sz = 0, feat_cnt = mod.get_nfeatures();
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
		sz += (int)samples.idSamples[i].samples.size();

	MLOG("Generating features for %d samples with %d features...\n", sz, feat_cnt);
	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
		"Generating features for %d samples with %d features...\n", sz, feat_cnt);
	//dont pass 2 Billion records:
	int max_smp = int((INT_MAX / feat_cnt) * 0.99) - 1;
	if (max_smp < sz && change_prior > 0) {
		vector<int> sel_idx;
		change_actual = medial::process::match_to_prior(samples, change_prior, sel_idx);
		if (!sel_idx.empty()) //did something
			sz = (int)sel_idx.size();
		else
			change_actual = -1;
	}
	if (max_smp < sz) {
		double down_factor = max_smp / double(sz);
		MWARN("WARN:: Too Many samples (%d) - down sampling by %2.3f...\n", sz, down_factor);
		//down_sample_by_pid(samples, down_factor);
		medial::process::down_sample(samples, down_factor);
		MLOG("Done Down sampling\n");
	}
	mod.serialize_learning_set = 0;
	if (mod.predictor == NULL) {
		MLOG("set default predictor for serialization\n");
		mod.set_predictor("gdlm");
	}
	return change_actual;
}

double load_matrix_from_json(MedSamples &samples,
	const string &RepositoryPath, const string &jsonPath, MedFeatures &dataMat, double change_prior) {
	MLOG("Reading repo file [%s]\n", RepositoryPath.c_str());
	MedModel mod;
	MedPidRepository dataManager;
	mod.init_from_json_file(jsonPath);
	mod.verbosity = 0;
	double change_actual = prepare_model_from_json(samples, RepositoryPath, mod, dataManager, change_prior);

	mod.learn(dataManager, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	dataMat = mod.features;
	return change_actual;
}

void read_ms_config(const string &file_path, const string &base_model,
	vector<MedPredictor *> &all_configs) {
	ifstream fr(file_path);
	if (!fr.good())
		MTHROW_AND_ERR("IOError: can't read model selection file\n");
	string line;
	vector<string> all_init = { "" };
	all_configs.clear();
	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("="));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("Bad Format in line \"%s\"\n", line.c_str());
		string param_name = boost::trim_copy(tokens[0]);
		string params_options = boost::trim_copy(tokens[1]);
		vector<string> opts;
		boost::split(opts, params_options, boost::is_any_of(","));
		int base_sz = (int)all_init.size();
		all_init.resize(base_sz * opts.size()); //cartezian multiply of options. copy the current options:
		for (size_t i = 1; i < opts.size(); ++i) //the first is already OK:
			for (size_t j = 0; j < base_sz; ++j)
				all_init[i*base_sz + j] = all_init[j];
		for (size_t i = 0; i < opts.size(); ++i) //the first is already OK:
			for (size_t j = 0; j < base_sz; ++j)
				all_init[i*base_sz + j] += param_name + "=" + opts[i] + ";";
	}
	fr.close();
	//I have string line to init all models:
	MLOG("I have %d models in model selection.\n", (int)all_init.size());

	int curr_lev = global_logger.levels[LOG_MEDALGO];
	global_logger.levels[LOG_MEDALGO] = MAX_LOG_LEVEL;
	all_configs.resize(all_init.size());
	for (size_t i = 0; i < all_init.size(); ++i)
		all_configs[i] = MedPredictor::make_predictor(base_model, all_init[i]);
	global_logger.levels[LOG_MEDALGO] = curr_lev;
}

void write_model_selection(const unordered_map<string, float> &model_loss,
	const unordered_map<string, float> &model_loss_train, const string &save_path) {
	ofstream fw(save_path);
	if (!fw.good())
		MTHROW_AND_ERR("IOError: can't write model_selection file\n");
	char buffer[5000];
	fw << "model_name" << "\t" << "loss_value" << "\t" << "loss_value_on_train" << endl;
	//print in sorted way by desc model_loss values and than by model_loss_train asc values:
	vector<pair<string, vector<double>>> sorted(model_loss.size());
	int i = 0;
	for (auto it = model_loss.begin(); it != model_loss.end(); ++it) {
		sorted[i].first = it->first;
		sorted[i].second = { it->second, -model_loss_train.at(it->first) };
		++i;
	}
	sort(sorted.begin(), sorted.end(), [](pair<string, vector<double>> a, pair<string, vector<double>> b) {
		int pos = 0;
		while (pos < a.second.size() &&
			a.second[pos] == b.second[pos])
			++pos;
		if (pos >= a.second.size())
			return false;
		return b.second[pos] > a.second[pos];
	});
	for (size_t ii = 0; ii < sorted.size(); ++ii)
	{
		snprintf(buffer, sizeof(buffer), "%s\t%2.4f\t%2.4f\n",
			sorted[ii].first.c_str(), sorted[ii].second[0], -sorted[ii].second[1]);
		string line = string(buffer);
		fw << line;
	}
	fw.close();
}

void commit_selection(MedFeatures &data, const unordered_set<string> &final_list) {
	unordered_set<string> clean_set_names;
	vector<string> origianl_names;
	data.get_feature_names(origianl_names);
	for (auto it = final_list.begin(); it != final_list.end(); ++it)
	{
		string clean_name = *it;
		if (boost::starts_with(clean_name, "FTR_"))
			clean_name = clean_name.substr(clean_name.find(".") + 1);
		clean_set_names.insert(clean_name);
	}
	for (auto it = data.data.begin(); it != data.data.end();) {
		string clean_name = it->first;
		if (boost::starts_with(clean_name, "FTR_"))
			clean_name = clean_name.substr(clean_name.find(".") + 1);
		if (clean_set_names.find(clean_name) == clean_set_names.end())  //not found - remove
			it = data.data.erase(it);
		else
			++it;
	}
	//check final_list size is same same of data:
	if (data.data.size() != final_list.size()) {
		unordered_set<string> data_names;
		unordered_map<string, vector<string>> date_un_to_all;
		for (auto it = data.data.begin(); it != data.data.end(); ++it) {
			string clean_name = it->first;
			if (boost::starts_with(clean_name, "FTR_"))
				clean_name = clean_name.substr(clean_name.find(".") + 1);
			data_names.insert(clean_name);
			date_un_to_all[clean_name].push_back(it->first);
		}
		//print diff between lists:
		for (const string &ftr : clean_set_names)
			if (data_names.find(ftr) == data_names.end()) {

				MWARN("Warning: Matrix is missing feature %s\n", ftr.c_str());
				int idx = find_in_feature_names(origianl_names, ftr, false);
				if (idx > 0)
					MWARN("Maybe you meant feature %s\n", origianl_names[idx].c_str());
			}
		for (const string &ftr : data_names)
			if (clean_set_names.find(ftr) == clean_set_names.end())
				MWARN("Warning: Matrix has additional feature %s\n", ftr.c_str());

		for (const auto &it : date_un_to_all)
			if (it.second.size() > 1) {
				string full_list_opt = medial::io::get_list(it.second, "|");
				MWARN("Warning: Matrix has basic feature %s(%zu): %s\n",
					it.first.c_str(), it.second.size(), full_list_opt.c_str());
			}

		for (auto it = data.data.begin(); it != data.data.end(); ++it) {
			string clean_name = it->first;
			if (boost::starts_with(clean_name, "FTR_"))
				clean_name = clean_name.substr(clean_name.find(".") + 1);
			MWARN("Info: Matrix feature (%s) => %s\n", clean_name.c_str(), it->first.c_str());
		}
		MTHROW_AND_ERR("Error in commit_selection - after commit selection request size was %zu(%zu unique), result size = %zu(%zu unique)\n",
			final_list.size(), clean_set_names.size(), data.data.size(), data_names.size());
	}
}

void filter_conflicts(MedFeatures &data) {
	unordered_map<int, int> pid_to_status;
	for (size_t i = 0; i < data.samples.size(); ++i)
	{
		int pid = data.samples[i].id;
		int outcome = int(data.samples[i].outcome > 0) + 1;
		pid_to_status[pid] |= outcome; //turn on mask
	}
	//choose only [1,1]. pids with 3 value:
	unordered_set<int> sel_pids;
	for (auto it = pid_to_status.begin(); it != pid_to_status.end(); ++it)
		if (it->second == 3)
			sel_pids.insert(it->first);
	vector<int> selected;
	//filter:
	for (size_t i = 0; i < data.samples.size(); ++i)
		if (sel_pids.find(data.samples[i].id) != sel_pids.end())
			selected.push_back((int)i);
	medial::process::filter_row_indexes(data, selected);
}
void filter_matrix_ages_years(MedFeatures &data, int min_age, int max_age, int min_year, int max_year) {
	vector<int> selected;
	//filter:
	int fetch_year_fact = 10000;
	if (global_default_time_unit == MedTime::Minutes)
		fetch_year_fact = 100000000;
	const vector<float> &age_vec = data.data["Age"];
	for (size_t i = 0; i < data.samples.size(); ++i)
		if ((age_vec[i] >= min_age && age_vec[i] <= max_age) &&
			(int(data.samples[i].time / fetch_year_fact) >= min_year && int(data.samples[i].time / fetch_year_fact) <= max_year))
			selected.push_back((int)i);
	medial::process::filter_row_indexes(data, selected);
}

void sort_indexes(vector<int> &signal_indexes, const vector<double> &p_values,
	const vector<double> &lift, const vector<double> &scores) {
	vector<int> indexes_order(signal_indexes.size());
	vector<pair<int, vector<double>>> sort_pars(signal_indexes.size());
	for (size_t i = 0; i < signal_indexes.size(); ++i)
	{
		sort_pars[i].first = (int)signal_indexes[i];
		sort_pars[i].second.resize(3);
		sort_pars[i].second[0] = p_values[signal_indexes[i]];
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
	signal_indexes.swap(indexes_order);
}

int get_dof(float val, const map<float, map<float, vector<int>>> &male_stats,
	const map<float, map<float, vector<int>>> &female_stats) {
	int dof = -1;
	if (male_stats.find(val) != male_stats.end())
		dof += int(male_stats.at(val).size());
	if (female_stats.find(val) != female_stats.end())
		dof += int(female_stats.at(val).size());
	return dof;
}

string get_signal_name(MedDictionarySections &dict, int sectionId, int paramVal,
	const string &signalHirerchyType) {
	string sigName = dict.name(sectionId, paramVal);
	vector<string> all_sigNames = dict.dicts[sectionId].Id2Names[(int)paramVal];
	string additional = "";
	if (!signalHirerchyType.empty() && signalHirerchyType != "None")
		additional = medial::signal_hierarchy::filter_code_hierarchy(all_sigNames, signalHirerchyType);
	if (additional.empty())
		additional = sigName;
	sigName += "\t" + additional;
	return sigName;
}

void get_signal_stats(string &base_stats_path,
	const string &signal_expend_stats
	, MedLabels &train_labeler, const string &type_sampler, const string &init_sampler, const LabelParams &lbl_pr,
	MedRepository &rep, const string &RepositoryPath, const string &out_path, int top_take, const signal_dep_filters &filters, int signal_idx) {
	string fixed;
	unordered_set<int> empty_arr;
	fix_path(base_stats_path, fixed);
	base_stats_path.swap(fixed);
	map<float, map<float, vector<int>>> male_stats, female_stats;
	string regex_filter = "";
	if (signal_idx < filters.regex_filters.size())
		regex_filter = filters.regex_filters[signal_idx];
	if (!file_exists(base_stats_path)) {
		MedSamplingStrategy *sampler_age = MedSamplingStrategy::make_sampler(type_sampler, init_sampler);
		int age_bing = 5;
		if (type_sampler == "age")
			age_bing = ((MedSamplingAge *)sampler_age)->age_bin;
		train_labeler.calc_signal_stats(RepositoryPath, signal_expend_stats, regex_filter, age_bing,
			*sampler_age, lbl_pr, male_stats, female_stats, "", empty_arr);
		medial::contingency_tables::write_stats(base_stats_path, male_stats, female_stats);
		delete sampler_age;
	}
	else {
		MLOG("Loading stats from disk\n");
		medial::contingency_tables::read_stats(base_stats_path, male_stats, female_stats);
	}

	vector<int> all_signal_values;
	vector<int> signal_indexes;
	vector<double> total_cnts, pos_cnts, lift, chi_scores, p_values, pos_ratio;
	int smooth_balls = 10;
	float min_allowed = filters.chi_square_at_least;
	int min_count = filters.minimal_chi_cnt;

	float fdr_val = filters.fdr;
	switch (filters.stat_metric)
	{
	case stat_test::chi_square:
		medial::contingency_tables::calc_chi_scores(male_stats, female_stats, all_signal_values
			, signal_indexes, total_cnts, pos_cnts, lift, chi_scores,
			p_values, pos_ratio, smooth_balls, min_allowed, min_count);
		break;
	case stat_test::mcnemar:
		medial::contingency_tables::calc_mcnemar_scores(male_stats, female_stats, all_signal_values
			, signal_indexes, total_cnts, pos_cnts, lift, chi_scores,
			p_values, pos_ratio);
		break;
	case stat_test::cmh:
		medial::contingency_tables::calc_cmh_scores(male_stats, female_stats, all_signal_values
			, signal_indexes, total_cnts, pos_cnts, lift, chi_scores,
			p_values, pos_ratio);
		break;
	default:
		MTHROW_AND_ERR("Unsupported stat metric %d\n", (int)filters.stat_metric);
	}
	unordered_map<int, double> code_cnts;
	for (size_t i = 0; i < all_signal_values.size(); ++i)
		code_cnts[all_signal_values[i]] = total_cnts[i];

	MLOG("Loaded %d signal values\n", (int)signal_indexes.size());
	medial::contingency_tables::FilterRange(signal_indexes, total_cnts, filters.minimal_count, INT_MAX); //at least 1000 counts for signal
	MLOG("After total filter has %d signal values\n", (int)signal_indexes.size());
	//medial::contingency_tables::FilterRange(signal_indexes, pos_cnts, 0, INT_MAX); //at least 50 counts for signal with registry
	//MLOG("After positive filter has %d signal values\n", (int)signal_indexes.size());
	//medial::contingency_tables::FilterRange(signal_indexes, pos_ratio, 0, 1); //filter mean ratio
	//MLOG("After positive ratio filter has %d signal values\n", (int)signal_indexes.size());
	//Filter Hirarchy:
	//	rep.init(RepositoryPath);
	int section_id = rep.dict.section_id(signal_expend_stats);
	if (section_id < 0)
		MTHROW_AND_ERR("Error can't find section id for %s\n", signal_expend_stats.c_str());
	medial::contingency_tables::filterHirarchy(rep.dict.dict(section_id)->Member2Sets, rep.dict.dict(section_id)->Set2Members,
		signal_indexes, all_signal_values, p_values, total_cnts, lift, code_cnts,
		filters.filter_child_pval_diff, filters.filter_child_lift_ratio, filters.filter_child_count_ratio,
		filters.filter_child_removed_ratio);
	MLOG("After Hirarchy filter has %d signal values\n", (int)signal_indexes.size());
	//Change negative lift for filteing:
	vector<double> fixed_lift(lift);
	for (int index : signal_indexes)
		if (fixed_lift[index] < 1 && fixed_lift[index] > 0)
			fixed_lift[index] = 1 / fixed_lift[index];
	//Now Filer by Lift
	vector<int> lift_filter;
	lift_filter.reserve(signal_indexes.size());
	for (int index : signal_indexes)
		if (lift[index] >= filters.lift_above || lift[index] <= filters.lift_below)
			lift_filter.push_back(index);
	signal_indexes.swap(lift_filter);
	MLOG("After Lift filter has %d signal values\n", (int)signal_indexes.size());
	//Filter FDR:
	medial::contingency_tables::FilterFDR(signal_indexes, chi_scores, p_values, fixed_lift, fdr_val);
	MLOG("AfterFDR has %d signal values\n", (int)signal_indexes.size());
	//Take Top - from up and from down.

	//printing whats taking:
	sort_indexes(signal_indexes, p_values, fixed_lift, chi_scores);
	if (signal_indexes.size() > top_take)
		signal_indexes.resize(top_take); //take top 100 total and print them:
	ofstream signal_dep_out(out_path);
	if (!signal_dep_out.good())
		MTHROW_AND_ERR("IOError: cant open file for writing!");
	MLOG("p_value\tDOF\tscore\ttotal_count\tpos_count\tlift\tsignal_name\n");
	signal_dep_out << "#p_value\tDOF\tscore\ttotal_count\tpos_count\tlift\tsignal_name\n";
	char buffer[1000];
	for (int index : signal_indexes)
	{
		string sigName = get_signal_name(rep.dict, rep.dict.section_id(signal_expend_stats),
			int(all_signal_values[index]), signal_expend_stats);
		string full_row;
		snprintf(buffer, sizeof(buffer), "%f\t%d\t%2.2f\t%d\t%d\t%2.3f\t%s\n",
			p_values[index], get_dof(all_signal_values[index], male_stats, female_stats),
			chi_scores[index], int(total_cnts[index]), int(pos_cnts[index]), lift[index],
			sigName.c_str());
		full_row = string(buffer);
		MLOG("%s", full_row.c_str());
		signal_dep_out << full_row;
	}
	signal_dep_out.close();
}

bool need_fp(FeatureProcessor *fp, const unordered_set<string> &selected_sigs, string &needed_exm) {
	vector<string> all_names;
	fp->get_feature_names(all_names);
	bool needed_pr = false;
	needed_exm = "";
	for (size_t i = 0; i < all_names.size() && !needed_pr; ++i)
	{
		string strip_name = all_names[i];
		if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
			strip_name = strip_name.substr(strip_name.find(".") + 1);
		if (selected_sigs.find(strip_name) != selected_sigs.end()) {
			needed_pr = true;
			needed_exm = all_names[i];
		}
	}
	return needed_pr;
}

void shrink_med_model(MedModel &mod, const unordered_set<string> &feature_selection_set) {
	if (feature_selection_set.empty())
		return;
	unordered_set<string> selected_sigs; //apply feature selection on model
	for (auto it = feature_selection_set.begin(); it != feature_selection_set.end(); ++it)
	{
		string strip_name = *it;
		if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
			strip_name = strip_name.substr(strip_name.find(".") + 1);
		selected_sigs.insert(strip_name);
	}
	bool add_age = selected_sigs.find("Age") == selected_sigs.end();
	if (add_age)
		selected_sigs.insert("Age");
	bool add_gender = selected_sigs.find("Gender") == selected_sigs.end();
	if (add_gender)
		selected_sigs.insert("Gender");

	//remove processors
	for (auto it = mod.feature_processors.begin(); it != mod.feature_processors.end();)
	{
		string needed_exm;
		bool needed_pr = need_fp(*it, selected_sigs, needed_exm);

		if (!needed_pr) {
			delete *it; //release memory
			it = mod.feature_processors.erase(it);
			continue;
		}
		else {
			//check if multi - if multi - check inside:
			if ((*it)->processor_type != FeatureProcessorTypes::FTR_PROCESS_MULTI) {
				unordered_set<string> out_req, in_req;
				out_req.insert(needed_exm);
				(*it)->update_req_features_vec(out_req, in_req);
				for (const string &s_name : in_req)
				{
					string strip_name = s_name;
					if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
						strip_name = strip_name.substr(strip_name.find(".") + 1);
					selected_sigs.insert(strip_name);
				}
			}
			else {
				MultiFeatureProcessor *multi_p = ((MultiFeatureProcessor *)(*it));
				vector<int> selected_idxs;
				for (size_t i = 0; i < multi_p->processors.size(); ++i)
				{
					string needed_exm_i;
					bool needed_pr_i = need_fp(multi_p->processors[i], selected_sigs, needed_exm_i);
					if (needed_pr_i)
						selected_idxs.push_back((int)i);
					else {
						delete multi_p->processors[i];
						multi_p->processors[i] = NULL;
					}
				}
				//remove all - shouldn't happen
				if (selected_idxs.empty()) {
					delete *it; //release memory
					it = mod.feature_processors.erase(it);
					continue;
				}
				else {
					vector<FeatureProcessor *> _int_list(selected_idxs.size());
					for (size_t i = 0; i < selected_idxs.size(); ++i)
						_int_list[i] = multi_p->processors[selected_idxs[i]];
					multi_p->processors = move(_int_list);

					//run again:
					need_fp(*it, selected_sigs, needed_exm);
					unordered_set<string> out_req, in_req;
					out_req.insert(needed_exm);
					(*it)->update_req_features_vec(out_req, in_req);
					for (const string &s_name : in_req)
					{
						string strip_name = s_name;
						if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
							strip_name = strip_name.substr(strip_name.find(".") + 1);
						selected_sigs.insert(strip_name);
					}
				}
			}
		}
		++it;
	}

	unordered_set<string> needed_sigs;
	//original names:
	vector<FeatureGenerator *> filterd_gen;
	for (size_t i = 0; i < mod.generators.size(); ++i) {
		bool keep_generator = false;
		for (const string &nm : mod.generators[i]->names)
		{
			string strip_name = nm;
			if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
				strip_name = strip_name.substr(strip_name.find(".") + 1);
			if (selected_sigs.find(strip_name) != selected_sigs.end())
				keep_generator = true;
		}
		if (keep_generator) {
			filterd_gen.push_back(mod.generators[i]);
			mod.generators[i]->get_required_signal_names(needed_sigs);
		}
	}
	vector<string> needed_sigs_vec(needed_sigs.begin(), needed_sigs.end());
	filter_rep_processors(needed_sigs_vec, &mod.rep_processors);
	//remove generators:
	mod.generators.swap(filterd_gen);


	MLOG("generators %d fp %d\n", (int)mod.generators.size(), (int)mod.feature_processors.size());
}

double load_test_matrix(MedSamples &samples, MedFeatures &dataMat, MedModel &mod, unordered_map<string, vector<float>> &additional_bootstrap,
	const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior) {
	double prev_prior = -1;
	vector<int> pids_to_take;
	samples.get_ids(pids_to_take);

	unordered_set<string> req_names;
	MedPidRepository dataManager;
	if (dataManager.init(RepositoryPath) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", RepositoryPath.c_str());
	mod.fit_for_repository(dataManager);
	mod.get_required_signal_names(req_names);
	vector<string> sigs = { "BDATE", "GENDER", "TRAIN" };
	for (string s : req_names)
		sigs.push_back(s);
	sort(sigs.begin(), sigs.end());
	auto it = unique(sigs.begin(), sigs.end());
	sigs.resize(std::distance(sigs.begin(), it));


	if (dataManager.read_all(RepositoryPath, pids_to_take, sigs) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", RepositoryPath.c_str());

	shrink_med_model(mod, feature_selection_set);

	int sz = 0, feat_cnt = mod.get_nfeatures();
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
		sz += (int)samples.idSamples[i].samples.size();
	MLOG("Generating features for %d samples with %d features...\n", sz, feat_cnt);
	//dont pass 2 Billion records:
	int max_smp = int((INT_MAX / feat_cnt) * 0.9) - 1;
	if (max_smp < sz && change_prior > 0) {
		vector<int> sel_idx;
		prev_prior = medial::process::match_to_prior(samples, change_prior, sel_idx);
		if (!sel_idx.empty()) //did something
			sz = (int)sel_idx.size();
		else
			prev_prior = -1; //didn't change
	}
	if (max_smp < sz) {
		double down_factor = max_smp / double(sz);
		MWARN("WARN:: Too Many samples (%d) - down sampling by %2.3f...\n", sz, down_factor);
		medial::process::down_sample_by_pid(samples, down_factor);
		MLOG("Done Down sampling\n");
	}

	mod.apply(dataManager, samples, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);

	dataMat = mod.features;
	if (!feature_selection_set.empty()) {
		unordered_set<string> selected_sigs, loaded_sigs; //apply feature selection on model
		for (auto it = feature_selection_set.begin(); it != feature_selection_set.end(); ++it)
		{
			string strip_name = *it;
			if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
				strip_name = strip_name.substr(strip_name.find(".") + 1);
			selected_sigs.insert(strip_name);
		}
		bool add_age = selected_sigs.find("Age") == selected_sigs.end();
		if (add_age) {
			additional_bootstrap["Age"].swap(dataMat.data["Age"]);
			dataMat.data.erase("Age");
		}
		bool add_gender = selected_sigs.find("Gender") == selected_sigs.end();
		if (add_gender) {
			additional_bootstrap["Gender"].swap(dataMat.data["Gender"]);
			dataMat.data.erase("Gender");
		}

		commit_selection(dataMat, selected_sigs);
		for (auto it = dataMat.data.begin(); it != dataMat.data.end(); ++it) {
			string clean_name_stripped = it->first;
			if (boost::starts_with(clean_name_stripped, "FTR_") && clean_name_stripped.find(".") != string::npos)
				clean_name_stripped = clean_name_stripped.substr(clean_name_stripped.find(".") + 1);
			loaded_sigs.insert(clean_name_stripped);
		}
		if (loaded_sigs.size() != selected_sigs.size())
		{
			MWARN("Warning: Has missing feature in creation:\n");
			for (auto it = selected_sigs.begin(); it != selected_sigs.end(); ++it)
				if (loaded_sigs.find(*it) == loaded_sigs.end())
					MWARN("MISSING %s\n", it->c_str());
			for (auto it = loaded_sigs.begin(); it != loaded_sigs.end(); ++it)
				if (selected_sigs.find(*it) == selected_sigs.end())
					MWARN("Additional %s\n", it->c_str());
		}
	}
	return prev_prior;
}

//the path is of binary object
double load_test_matrix(MedSamples &samples, MedFeatures &dataMat, unordered_map<string, vector<float>> &additional_bootstrap
	, const string &modelFile, const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior) {
	//use MedModel - if want to use my code feature creator than need serialization support
	//TODO: support other feature creation

	ifstream mdl_file(modelFile);
	if (mdl_file.good()) {
		mdl_file.close();
		MedModel mod;
		mod.read_from_file(modelFile);
		mod.verbosity = 0;
		double pr = load_test_matrix(samples, dataMat, mod, additional_bootstrap, feature_selection_set, RepositoryPath, change_prior);
		if (mod.LearningSet != NULL) {//when reading model from disk need to clean LearningSet before exit - valgrind
			delete static_cast<MedSamples *>(mod.LearningSet);
			mod.LearningSet = 0;
			mod.serialize_learning_set = false;
		}
		return pr;
	}

	MTHROW_AND_ERR("Unsupported initialization without MedModel %s\n",
		modelFile.c_str());
}

template<class T> T avgVec(const vector<T> &vec) {
	T res = 0;
	int sz = 0;
	for (size_t i = 0; i < vec.size(); ++i)
	{
		if (vec[i] == MED_MAT_MISSING_VALUE) {
			continue;
		}
		res += vec[i];
		++sz;
	}
	if (sz == 0) {
		return MED_MAT_MISSING_VALUE;
	}
	return res / sz;
}
vector<int> FilterMissings(vector<float> &x, vector<float> &y) {
	vector<float> xfilt;
	vector<float> yfilt;
	vector<int> sel_inds;
	for (size_t i = 0; i < x.size(); ++i)
	{
		if (x[i] == MED_MAT_MISSING_VALUE || y[i] == MED_MAT_MISSING_VALUE) {
			continue;
		}
		sel_inds.push_back((int)i);
		xfilt.push_back(x[i]);
		yfilt.push_back(y[i]);
	}
	x.swap(xfilt);
	y.swap(yfilt);
	return sel_inds;
}

bool valid_subset(const vector<float> &y) {
	if (y.empty())
		return false;
	float last_val = y.front();

	//checks that y has at least diffrent label - not all the same
	bool found_diff = false;
	for (size_t i = 1; i < y.size() && !found_diff; ++i)
		found_diff = (y[i] != last_val);

	return found_diff;
}

void PrintFeatureMeasures(const vector<float> &res, string measureTitle,
	const vector<string> &SignalNames, bool upDown, const vector<float> &refData,
	const vector<float> &comp, const string &file_path) {
	vector<float> copyD(res);
	sort(copyD.begin(), copyD.end());

	//updown:
	int direction = +1;
	int startInd = 0;
	int endInd = (int)copyD.size();
	string additionalComment = "smaller is better";
	if (upDown) {
		direction = -1;
		startInd = endInd;
		endInd = 0;
		additionalComment = "bigger is beter";
	}
	ofstream fw;
	if (!file_path.empty())
		fw.open(file_path);
	if (!fw.good())
		MTHROW_AND_ERR("IOError in write to %s\n", file_path.c_str());

	MLOG("%s(%s):\n", measureTitle.c_str(), additionalComment.c_str());
	fw << measureTitle << "(" << additionalComment.c_str() << "):" << endl;
	int ii = 0;
	float prev_print = copyD[0] - 1;
	for (int i = startInd; ((endInd > 0 && i < endInd) || (endInd == 0 && i >= endInd)); i += direction)
	{
		float currentInfo = copyD[i];
		if (prev_print == currentInfo)
			continue;
		prev_print = currentInfo;
		vector<int> paramInd;
		for (size_t k = 0; k < res.size(); ++k)
			if (res[k] == currentInfo)
				paramInd.push_back((int)k);

		for (size_t k = 0; k < paramInd.size(); ++k)
		{
			int parameterIndex = paramInd[k];
			string signalName = SignalNames[parameterIndex];
			if (k >= comp.size()) {
				MLOG("Index=%d Parameter %s has value=%2.4f\n", ii, signalName.c_str(), refData[parameterIndex]);
				fw << "Index=" << ii << " Parameter " << signalName << " has value=" << refData[parameterIndex] << endl;
				if (k <= 10)
					global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
						"Index=%d Parameter %s has value=%2.4f\n", ii, signalName.c_str(), refData[parameterIndex]);
			}
			else {
				MLOG("Index=%d Parameter %s has value=%2.4f compare=%2.4f diff=%2.4f\n",
					ii, signalName.c_str(), refData[parameterIndex], comp[parameterIndex], comp[parameterIndex] - refData[parameterIndex]);
				fw << "Index=" << ii << " Parameter " << signalName << " has value=" << refData[parameterIndex] <<
					" compare=" << comp[parameterIndex] << " diff=" << comp[parameterIndex] - refData[parameterIndex] << endl;
				if (k <= 10)
					global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
						"Index=%d Parameter %s has value=%2.4f compare=%2.4f diff=%2.4f\n",
						ii, signalName.c_str(), refData[parameterIndex], comp[parameterIndex], comp[parameterIndex] - refData[parameterIndex]);
			}
		}
		++ii;
	}
	fw.close();
}
void FindBayesOptimal(const vector<vector<float>> &xData, const vector<float> &yData,
	double(*loss_function)(const vector<float> &, const vector<float> &, const vector<float> *),
	const vector<string> &signalNames, const BinSettings &bin_sett, vector<float> &baseErrs
	, vector<float> &lossArr) {
	lossArr.resize((int)xData.size());
	baseErrs.resize((int)xData.size());

	MedProgress progress("PrintFeatureMeasures", (int)xData.size(), 60, 1);
	progress.print_section = LOG_MED_MODEL;
#pragma omp parallel for schedule(dynamic,1)
	for (int i = 0; i < xData.size(); ++i)
	{
		vector<float> yCopy(yData);
		vector<float> x(xData[i]);
		FilterMissings(x, yCopy);
		if (!valid_subset(yCopy)) {
			MWARN("Warning: skiping features %d(%s) - all values are missing or only cases/controls. has %zu rows\n",
				i, signalNames[i].c_str(), yCopy.size());
			baseErrs[i] = MED_MAT_MISSING_VALUE;
			lossArr[i] = MED_MAT_MISSING_VALUE;
			progress.update();
			continue;
		}
		float avgYPred = avgVec(yCopy);
		medial::process::split_feature_to_bins(bin_sett, x, {}, yCopy);

		vector<vector<float>> xx = { x };
		map<float, float> xy = BuildAggeration(xx, yCopy, avgVec);
		//test this model for each x in xy will get y

		vector<float> preds((int)x.size());
		vector<float> predsConstant((int)x.size());
		for (size_t k = 0; k < x.size(); ++k)
		{
			float resY = xy[x[k]];
			preds[k] = resY;
			predsConstant[k] = avgYPred;

		}
		double avgLoss = loss_function(preds, yCopy, NULL);
		double baseLineErr = loss_function(predsConstant, yCopy, NULL);

		baseErrs[i] = (float)baseLineErr;
		lossArr[i] = (float)avgLoss;
		progress.update();
	}
}

void simple_uni_feature_sel(const MedFeatures &data,
	const vector<string> &signalNames, const string &output_path,
	const BinSettings &bin_sett, loss_metric metric) {
	vector<float> y(data.samples.size());
	vector<vector<float>> xData(data.data.size());
	for (size_t i = 0; i < xData.size(); ++i)
		xData[i].resize(y.size());
	for (size_t i = 0; i < data.samples.size(); ++i)
		y[i] = data.samples[i].outcome;
	int k = 0;
	for (auto it = data.data.begin(); it != data.data.end(); ++it)
	{
		memcpy(&xData[k][0], &it->second[0], sizeof(float) * y.size());
		++k;
	}

	vector<float> loss_vals_to_constant;
	time_t start_t = time(NULL);
	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
		"Starting Univariate Feature ranking\n");

	vector<float> loss_vals;
	loss_fun_sig loss_fun = get_loss_function(metric);

	FindBayesOptimal(xData, y, loss_fun, signalNames, bin_sett, loss_vals_to_constant, loss_vals);
	int duration = (int)difftime(time(NULL), start_t);
	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
		"took %d seconds to univariate feature selection\n", duration);
	if (metric == loss_metric::auc)
		for (size_t i = 0; i < loss_vals_to_constant.size(); ++i)
		{
			//loss_vals_to_constant[i] = 0.5;
			if (loss_vals[i] != MED_MAT_MISSING_VALUE && loss_vals[i] < 0.5)
				loss_vals[i] = 1 - loss_vals[i];
		}
	string measure_name = get_loss_metric_name(metric);
	PrintFeatureMeasures(loss_vals, measure_name + " on each parameter - binned", signalNames,
		loss_function_order(metric), loss_vals, loss_vals_to_constant, output_path);
}


vector<int> getRandomGroup(int grp_size, int max_ind) {
	vector<int> res(grp_size);
	vector<bool> in_groop(max_ind, false);

	random_device rd;
	mt19937 gen(rd());
	uniform_int_distribution<> int_dis(0, max_ind - 1);

	int i = 0;
	while (i < grp_size) {
		int num = int_dis(gen);
		if (in_groop[num])
			continue;
		in_groop[num] = true;
		res[i] = num;
		++i;
	}

	return res;
}
int getSignalIndex(const vector<string> &signalNames, const string &signal) {
	for (size_t i = 0; i < signalNames.size(); ++i)
		if (signalNames[i].find(signal) != string::npos)
			return (int)i;
	return -1;
}


void get_pids_shuffle(MedFeatures &dataMat, vector<int> &pids) {
	pids.resize((int)dataMat.pid_pos_len.size());
	int iter_i = 0;
	for (auto it = dataMat.pid_pos_len.begin(); it != dataMat.pid_pos_len.end(); ++it) {
		pids[iter_i] = it->first;
		++iter_i;
	}
	random_shuffle(pids.begin(), pids.end());

	MLOG("Has %d pids with %d feautres on %d samples\n",
		(int)pids.size(), (int)dataMat.data.size(), (int)dataMat.samples.size());
}
void match_by_year(MedFeatures &data_records, float price_ratio, int year_bin_size, bool print_verbose) {
	vector<string> groups((int)data_records.samples.size());
	for (size_t i = 0; i < data_records.samples.size(); ++i) {
		int prediction_year = int(year_bin_size*round(data_records.samples[i].time / 10000 / year_bin_size));
		groups[i] = to_string(prediction_year);
	}
	vector<int> filter_inds;
	medial::process::match_by_general(data_records, groups, filter_inds, price_ratio, 5, print_verbose);
}
void prepate_train_test(MedFeatures &dataMat, vector<int> &selectedInd, vector<int> &pids, bool(*filterTestCondition)(const MedFeatures &, int)
	, bool(*filterTrainCondition)(const MedFeatures &, int), bool filterTrainPid, float price_ratio,
	vector<vector<float>> &xTrain, vector<vector<float>> &xTest, vector<float> &yTrain, vector<float> &yTest, vector<float> &weights,
	vector<int> &test_pid_ord, vector<int> &y_time, vector<int> &prediction_time, vector<int> &train_pids, map<string, vector<float>> &additional_info,
	int kFold, size_t loop_fold, float test_ratio = 0, bool print_debug = true) {
	bool do_match = price_ratio > 0;
	time_t start_t = time(NULL);
	if (kFold > 1)
		test_ratio = (float)1.0 / kFold;
	// Split Pids to train and test:
	if (selectedInd.empty()) {
#pragma omp critical 
		{
			selectedInd.resize(dataMat.data.size());
			for (size_t i = 0; i < selectedInd.size(); ++i)
				selectedInd[i] = (int)i;
		}
	}

	if (pids.empty())
#pragma omp critical 
		get_pids_shuffle(dataMat, pids);
	int min_p = -1, max_p = -1;
	for (size_t i = 0; i < pids.size(); ++i)
	{
		if (pids[i] > max_p)
			max_p = pids[i];
		if (pids[i] < min_p || min_p == -1)
			min_p = pids[i];
	}
	int pids_len = max_p - min_p + 1;

	int signalCnt = (int)selectedInd.size();
	vector<string> signalNames;
	dataMat.get_feature_names(signalNames);

	int testSize = (int)(pids.size() * test_ratio);
	vector<float> all_preds;
	vector<float> all_y;
	vector<int> all_test_pid_ord;
	vector<int> all_y_time;
	vector<int> all_prediction_time;

	vector<bool> test_pids(pids_len);
	for (size_t i = loop_fold * testSize; i < (loop_fold + 1)*testSize; ++i)
		test_pids[pids[i] - min_p] = true;

	xTest.resize(signalCnt);
	vector<bool> took_test_pid(pids_len);

	vector<bool> took_train_pid(pids_len);
	MedFeatures train_records;
	vector<int> train_counts(2);
	vector<unordered_set<int>> train_pids_counts(2);
	vector<int> lbl_cnt(2);
	train_records.attributes = dataMat.attributes;
	train_records.time_unit = dataMat.time_unit;

	//allocate memory:
	train_records.samples.reserve(int(dataMat.samples.size() * (1 - test_ratio)));
	for (size_t k = 0; k < selectedInd.size(); ++k)
		train_records.data[signalNames[selectedInd[k]]].reserve(int(dataMat.samples.size() * (1 - test_ratio)));
	for (size_t k = 0; k < selectedInd.size(); ++k)
		xTest[k].reserve(int(dataMat.samples.size() * test_ratio));
	yTest.reserve(int(dataMat.samples.size() * test_ratio));
	test_pid_ord.reserve(int(dataMat.samples.size() * test_ratio));
	y_time.reserve(int(dataMat.samples.size() * test_ratio));
	train_pids.clear();
	prediction_time.reserve(int(dataMat.samples.size() * test_ratio));

	int duration = (int)difftime(time(NULL), start_t);
	//MLOG_D("Took %d seconds to prepare for sampling train|test\n", duration);

	start_t = time(NULL);
	//#pragma omp parallel for
	for (int i = 0; i < dataMat.samples.size(); ++i)
	{
		if (!test_pids[dataMat.samples[i].id - min_p]) { // in train (choose all for now):
			if (filterTrainCondition != NULL && !filterTrainCondition(dataMat, (int)i))
				continue;
			if (filterTrainPid && took_train_pid[dataMat.samples[i].id - min_p]) {
				continue;
			}

#pragma omp critical 
			{
				train_records.samples.push_back(dataMat.samples[i]);
				for (size_t k = 0; k < selectedInd.size(); ++k)
					train_records.data[signalNames[selectedInd[k]]].push_back(dataMat.data[signalNames[selectedInd[k]]][i]);

				++lbl_cnt[dataMat.samples[i].outcome > 0];
				took_train_pid[dataMat.samples[i].id - min_p] = true;
				++train_counts[dataMat.samples[i].outcome > 0];
				train_pids_counts[dataMat.samples[i].outcome > 0].insert(dataMat.samples[i].id);
				if (!dataMat.weights.empty())
					train_records.weights.push_back(dataMat.weights[i]);
			}
		}
		else { //in test - choose 1 prediction for each pid - based on exp.
			if (took_test_pid[dataMat.samples[i].id - min_p]) {
				//continue; //Take All - bootstrap will take care of rest:
			}
			if (filterTestCondition == NULL || filterTestCondition(dataMat, (int)i)) {

				//float time_diff = medial::repository::DateDiff(dataMat.samples[i].time, dataMat.samples[i].outcomeTime);
#pragma omp critical 
				{
					for (size_t k = 0; k < selectedInd.size(); ++k)
						xTest[k].push_back(dataMat.data[signalNames[selectedInd[k]]][i]);

					yTest.push_back(dataMat.samples[i].outcome);
					test_pid_ord.push_back(dataMat.samples[i].id);
					y_time.push_back(dataMat.samples[i].outcomeTime);
					prediction_time.push_back(dataMat.samples[i].time);
					took_test_pid[dataMat.samples[i].id - min_p] = true;
				}
			}
		}
	}
	train_records.init_pid_pos_len();
	duration = (int)difftime(time(NULL), start_t);
	if (print_debug)
		MLOG_D("Took %d seconds to samples train|test\n", duration);

	//Matching
	//print_by_year_target(train_records, pid_start);
	//match_by_year(train_records, price_ratio, 1, false);
	start_t = time(NULL);
	if (do_match) {
		//match_by_year_target(train_records, pid_start, price_ratio, 1, true);
		match_by_year(train_records, price_ratio, 1, false);
		//cout << "Done Matching" << endl;
	}
	else {
		if (print_debug) {
			if (dataMat.time_unit == MedTime::Date)
				medial::print::print_by_year(train_records.samples, 1);
			else
				medial::print::print_samples_stats(train_records.samples);
		}
	}
	duration = (int)difftime(time(NULL), start_t);
	if (print_debug)
		MLOG_D("Took %d seconds to matching\n", duration);
	start_t = time(NULL);
	//xTrain.clear();
	yTrain.resize(train_records.samples.size());
	xTrain.resize(signalCnt);
	train_pids.resize(train_records.samples.size());
	for (size_t i = 0; i < signalCnt; ++i)
		xTrain[i].resize(train_records.samples.size());
	if (!train_records.weights.empty())
		weights.resize(train_records.samples.size());
	lbl_cnt = vector<int>(2);
	for (size_t ii = 0; ii < train_records.samples.size(); ++ii)
	{
		for (size_t i = 0; i < signalCnt; ++i)
			xTrain[i][ii] = train_records.data[signalNames[selectedInd[i]]][ii];
		yTrain[ii] = train_records.samples[ii].outcome;
		if (!train_records.weights.empty())
			weights[ii] = train_records.weights[ii];
		++lbl_cnt[train_records.samples[ii].outcome > 0];
		train_pids[ii] = train_records.samples[ii].id;
	}
	duration = (int)difftime(time(NULL), start_t);
	if (print_debug) {
		MLOG("Train Labels: [%d, %d] %2.4f {took %d seconds}\n",
			lbl_cnt[0], lbl_cnt[1], float(lbl_cnt[1]) / (lbl_cnt[0] + lbl_cnt[1]), duration);
		global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Train Labels: [%d, %d] %2.4f {took %d seconds}\n",
			lbl_cnt[0], lbl_cnt[1], float(lbl_cnt[1]) / (lbl_cnt[0] + lbl_cnt[1]), duration);
	}
}

void prepare_splits(const MedFeatures &dataMat, const vector<int> &selectedInd, float price_ratio, int kFold,
	vector<vector<MedFeatures>> &matrixes_folds) {
	static random_device rd;
	static mt19937 gen(rd());

	unordered_map<int, int> pid_to_split;
	uniform_int_distribution<> dist_int(0, kFold - 1);
	for (size_t i = 0; i < dataMat.samples.size(); ++i)
		if (pid_to_split.find(dataMat.samples[i].id) == pid_to_split.end())
			pid_to_split[dataMat.samples[i].id] = dist_int(gen);

	vector<string> features;
	dataMat.get_feature_names(features);
	if (!selectedInd.empty())
	{
		vector<string> selected(selectedInd.size());
		for (size_t i = 0; i < selected.size(); ++i)
			selected[i] = features[selectedInd[i]];
		features.swap(selected);
	}

	//prepare all splits:
	matrixes_folds.resize(kFold); //2nd index: 0 is train, 1 is test
	for (size_t fold = 0; fold < kFold; ++fold)
	{
		matrixes_folds[fold].resize(2);
		medial::process::split_matrix(dataMat, pid_to_split, (int)fold, matrixes_folds[fold][0], matrixes_folds[fold][1], &features);
		//matching on train by years if needed:
		if (price_ratio > 0)
			match_by_year(matrixes_folds[fold][0], price_ratio, 1, false);
	}


}

vector<pair<float, string>> runFeatureSelectionModel(MedPredictor *model, const MedFeatures &data_records, const vector<string> &signalNames, float &refScore,
	const vector<string> &baseSigs, int find_addition, int loopIter, loss_metric metric) {
	vector<vector<float>> xData((int)data_records.data.size());
	MedPredictor *qrf_ref = (MedPredictor *)model;

	for (size_t i = 0; i < xData.size(); ++i)
		xData[i].resize(data_records.data.begin()->second.size());
	string aggStr = "";
	vector<float> yData((int)data_records.samples.size());
	int baseCnt = (int)baseSigs.size();
	unordered_set<string> baseSignalSet(baseSigs.begin(), baseSigs.end());
	for (size_t ii = 0; ii < data_records.samples.size(); ++ii)
		yData[ii] = data_records.samples[ii].outcome;
	int i = 0;
	for (auto it = data_records.data.begin(); it != data_records.data.end(); ++it)
	{
		xData[i] = data_records.data.at(it->first);
		++i;
	}

	vector<int> sigInds(baseCnt);
	for (size_t i = 0; i < sigInds.size(); ++i) {
		sigInds[i] = getSignalIndex(signalNames, baseSigs[i]);
		if (sigInds[i] == -1)
			MTHROW_AND_ERR("ERROR: signalNames is missing signal %s", baseSigs[i].c_str());
	}
	for (int i = 0; i < baseCnt - 1; ++i)
		aggStr += baseSigs[i] + "_";
	if (baseCnt > 0)
		aggStr += baseSigs[baseCnt - 1];

	int split_th = int(yData.size() * 0.7);
	int res_size = (int)yData.size() - split_th;

	vector<vector<float>> vec_all(baseCnt);
	for (size_t i = 0; i < sigInds.size(); ++i)
		vec_all[i] = xData[sigInds[i]];
	cout << "Feature Selection: " << endl;
	if (find_addition == 1)
		loopIter = (int)xData.size(); //no random - iterate all options
	if (find_addition > (int)xData.size() - baseCnt)
		throw invalid_argument("too much paramters to feature selection");

	if (baseCnt > 0) {
		float ref_score = 0;

		vector<float> x_train_ref(baseCnt * split_th), x_test_ref(baseCnt * res_size);
		vector<float> train_y_ref(split_th), test_y_ref(res_size), weights_ref;
		if (!data_records.weights.empty())
			weights_ref.resize(split_th);
		vector<int> choosed_ind = getRandomGroup(split_th, (int)yData.size());
		for (size_t ii = 0; ii < choosed_ind.size(); ++ii) {
			for (size_t m = 0; m < baseCnt; ++m)
				x_train_ref[ii * baseCnt + m] = vec_all[m][choosed_ind[ii]];
			train_y_ref[ii] = yData[choosed_ind[ii]];
			if (!data_records.weights.empty())
				weights_ref[ii] = data_records.weights[ii];
		}
		unordered_set<int> sel_ind_mask(choosed_ind.begin(), choosed_ind.end());
		int curr_ind = 0;
		for (size_t m = 0; m < yData.size(); ++m)
			if (sel_ind_mask.find((int)m) == sel_ind_mask.end()) {
				for (size_t i = 0; i < baseCnt; ++i)
					x_test_ref[curr_ind * baseCnt + i] = vec_all[i][m];
				test_y_ref[curr_ind] = yData[m];
				++curr_ind;
			}
		vector<float> preds_ref;
		qrf_ref->learn(x_train_ref, train_y_ref, weights_ref, (int)train_y_ref.size(), baseCnt);
		qrf_ref->predict(x_test_ref, preds_ref, (int)test_y_ref.size(), baseCnt);
		ref_score = loss_function_metric(metric, preds_ref, test_y_ref);
		//delete qrf_ref;

		refScore = ref_score;
		cout << "Ref_Score=" << ref_score << endl;
	}
	else {
		cout << "No reference score" << endl;
		refScore = 0;
	}

	vector<pair<float, string>> all_scores(loopIter);
	vector<vector<int>> random_selection_inds(loopIter);
	if (find_addition == 1)
		for (size_t i = 0; i < all_scores.size(); ++i) {
			all_scores[i].second = signalNames[i];
			random_selection_inds[i] = { (int)i };
		}
	else {
		random_device rd;
		mt19937 rd_gen(rd());
		uniform_int_distribution<> num_gen(0, (int)xData.size() - 1);
		for (size_t i = 0; i < all_scores.size(); ++i) {
			unordered_set<int> seen_params(sigInds.begin(), sigInds.end()); //not from baseline
			random_selection_inds[i].resize(find_addition);
			for (size_t k = 0; k < find_addition; ++k)
			{
				int selected_p = num_gen(rd_gen);
				while (seen_params.find(selected_p) != seen_params.end())
					selected_p = num_gen(rd_gen);
				random_selection_inds[i][k] = selected_p;
				all_scores[i].second += signalNames[selected_p] + "|";
			}
		}
	}

	//map<string, int> sigCounts;
	map<string, bool> op;
	MedProgress progress("FeatureSelectionModel", loopIter, 30, 1);
	progress.print_section = LOG_MED_MODEL;

	vector<float> train_x((baseCnt + find_addition) * split_th), test_x((baseCnt + find_addition) * res_size);
	vector<float> train_y(split_th), test_y(res_size), weights;
	if (!data_records.weights.empty())
		weights.resize(split_th);
	vector<MedPredictor *> all_models(loopIter);
	for (size_t i = 0; i < all_models.size(); ++i)
		all_models[i] = (MedPredictor *)medial::models::copyInfraModel(model, false);

#pragma omp parallel for firstprivate(train_x, test_x, train_y, test_y, weights, all_models) schedule(dynamic,1)
	for (int i = 0; i < loopIter; ++i)
	{
		//vector<float> cp_y(yData);
		//vector<float> cp_x(xData[i]);
		//vector<int> sel = FilterMissings(cp_x, cp_y);
		//vector<vector<float>> vec(vec_all); //copy baseline
		//for (size_t k = 0; k < vec.size(); ++k) {
		//commitSeletion(vec[k], sel);
		//}

		bool seen_0 = false, seen_1 = false;
		for (size_t k = 0; k < yData.size(); ++k)
		{
			seen_0 = seen_0 || yData[k] <= 0;
			seen_1 = seen_1 || yData[k] > 0;
			if (seen_0 && seen_1)
				break;
		}
		float auc = 0.5;
		if (seen_0 && seen_1) {
			MedPredictor *qrf = all_models[i];
			//vector<float> train_x((baseCnt + find_addition) * split_th), test_x((baseCnt + find_addition) * res_size);
			//vector<float> train_y(split_th), test_y(res_size);

			vector<int> choosed_ind = getRandomGroup(split_th, (int)yData.size());
			for (size_t m = 0; m < choosed_ind.size(); ++m)
			{
				int ind = choosed_ind[m];
				for (size_t mm = 0; mm < find_addition; ++mm) //add random selection
					train_x[m * (baseCnt + find_addition) + mm] = xData[random_selection_inds[i][mm]][ind];
				for (size_t k = find_addition; k < baseCnt + find_addition; ++k) //add base
					train_x[m * (baseCnt + find_addition) + k] = vec_all[k - find_addition][ind];
				train_y[m] = yData[ind];
				if (!data_records.weights.empty())
					weights[m] = data_records.weights[m];
			}
			unordered_set<int> sel_ind_mask(choosed_ind.begin(), choosed_ind.end());
			int curr_ind = 0;
			for (size_t m = 0; m < yData.size(); ++m)
			{
				if (sel_ind_mask.find((int)m) == sel_ind_mask.end()) { //if not exists in train - so in test
					for (size_t mm = 0; mm < find_addition; ++mm) //add random selection
						test_x[curr_ind * (baseCnt + find_addition) + mm] = xData[random_selection_inds[i][mm]][m];
					for (size_t k = find_addition; k < baseCnt + find_addition; ++k)
						test_x[curr_ind * (baseCnt + find_addition) + k] = vec_all[k - find_addition][m];
					test_y[curr_ind] = yData[m];
					++curr_ind;
				}
			}

			qrf->learn(train_x, train_y, weights, split_th, (baseCnt + find_addition));
			vector<float> score_preds;
			qrf->predict(test_x, score_preds, res_size, (baseCnt + find_addition));

			delete qrf;

			auc = loss_function_metric(metric, score_preds, test_y);
		}
		//#pragma omp critical
		//sigCounts[all_scores[i].second] = (int)yData.size();
#pragma omp critical
		all_scores[i].first = auc;

		progress.update();
	}
	sort(all_scores.begin(), all_scores.end());
	bool higer_is_better = loss_function_order(metric);
	string metric_name = get_loss_metric_name(metric);

	if (higer_is_better)
		for (int i = (int)all_scores.size() - 1; i >= 0 && i >= all_scores.size() - 100; --i)
		{
			string add = "";
			if (op.find(all_scores[i].second) != op.end())
				add = " (OPP)";
			cout << "Signal " << all_scores[i].second << " QRF_With_" << aggStr << "_" << metric_name << "=" << all_scores[i].first <<
				add << endl;
		}
	else
		for (int i = 0; i <= 1000 && i < all_scores.size(); ++i)
		{
			string add = "";
			if (op.find(all_scores[i].second) != op.end())
				add = " (OPP)";
			cout << "Signal " << all_scores[i].second << " QRF_With_" << aggStr << "_" << metric_name << "=" << all_scores[i].first <<
				add << endl;
		}

	return all_scores;
}

string runOptimizerModel(MedFeatures &dataMat, bool filterTrainPid, float price_ratio
	, vector<int> &selectedInd, const vector<MedPredictor *> &all_models_config,
	unordered_map<string, float> &model_loss, unordered_map<string, float> &model_loss_train,
	int nFold, loss_metric metric) {

	vector<vector<MedFeatures>> matrix_splits;
	prepare_splits(dataMat, {}, price_ratio, nFold, matrix_splits); //done once for all features
	vector<vector<float>> test_labels_splits(nFold), train_labels_split(nFold);
	for (size_t i = 0; i < test_labels_splits.size(); ++i) {
		test_labels_splits[i].resize(matrix_splits[i][1].samples.size());
		for (size_t j = 0; j < test_labels_splits[i].size(); ++j)
			test_labels_splits[i][j] = matrix_splits[i][1].samples[j].outcome;
	}
	for (size_t i = 0; i < train_labels_split.size(); ++i) {
		train_labels_split[i].resize(matrix_splits[i][0].samples.size());
		for (size_t j = 0; j < train_labels_split[i].size(); ++j)
			train_labels_split[i][j] = matrix_splits[i][0].samples[j].outcome;
	}

	time_t start = time(NULL);
	time_t last_time_print = start;
	int duration;
	float minVal = 10000;
	string bestParams = "";
	int tot_done = 0;
	vector<MedMat<float>> test_mats(nFold), train_mats(nFold);
	for (size_t kFold = 0; kFold < nFold; ++kFold)
		matrix_splits[kFold][1].get_as_matrix(test_mats[kFold]);
	for (size_t kFold = 0; kFold < nFold; ++kFold)
		matrix_splits[kFold][0].get_as_matrix(train_mats[kFold]);
#pragma	omp parallel for
	for (int i = 0; i < all_models_config.size(); ++i) {
		vector<float> allRuns_train(nFold), allRuns(nFold);
		string modelName = medial::models::getParamsInfraModel(all_models_config[i]);
		for (size_t kFold = 0; kFold < nFold; ++kFold)
		{
			all_models_config[i]->learn(matrix_splits[kFold][0]);
			vector<float> scores, scores_train;
			all_models_config[i]->predict(test_mats[kFold], scores);
			all_models_config[i]->predict(train_mats[kFold], scores_train);
			float lossVals = loss_function_metric(metric, scores, test_labels_splits[kFold], &matrix_splits[kFold][1].weights, true);
			float lossVals_train = loss_function_metric(metric, scores_train, train_labels_split[kFold], &matrix_splits[kFold][0].weights, true);

			allRuns_train[kFold] = lossVals_train;
			allRuns[kFold] = lossVals;
		}
		float avg_loss_test = avgVec(allRuns);
		float avg_loss_train = avgVec(allRuns_train);
		delete all_models_config[i]; //clear memory

		MLOG("%s has loss_val=%2.4f on train %2.4f\n", modelName.c_str(), avg_loss_test, avg_loss_train);

#pragma omp critical
		{
			model_loss[modelName] = avg_loss_test;
			model_loss_train[modelName] = avg_loss_train;
			if (avg_loss_test < minVal || bestParams.empty()) {
				minVal = avg_loss_test;
				bestParams = modelName;
			}
		}
#pragma omp atomic 
		++tot_done;
		duration = (int)difftime(time(NULL), last_time_print);
		if (duration >= 60) {
			int time_from_start = (int)difftime(time(NULL), start);
			double estimate = ((double)(all_models_config.size() - tot_done) / tot_done) * time_from_start / 60.0;
			printf("Done %d out of %d(%2.2f%%). minutes_elapsed=%2.1f, estimate_minutes=%2.1f\n",
				tot_done, (int)all_models_config.size(),
				100.0* double(tot_done) / all_models_config.size(),
				time_from_start / 60.0, estimate);
			last_time_print = time(NULL);
		}
	}
	MLOG("Done! best score = %2.4f with %s\n", minVal, bestParams.c_str());
	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
		"Done! best score = %2.4f with %s\n", minVal, bestParams.c_str());
	return bestParams;
}

map<string, map<string, float>> print_booststrap(const vector<float> &preds, const vector<float> &y,
	const vector<int> &pids, const vector<float> *weights, const vector<int> &y_times, const vector<int> &prediction_time,
	const map<string, vector<float>> &additional_info, const map<string, FilterCohortFunc> &cohort_defs,
	string f_name, const vector<MeasurementFunctions> &meas_funs, ROC_Params *roc_params, int samples_per_pid
	, bool output_file, int loopCnt, loss_metric metric) {
	//Write File to un bootstrap
	if (preds.size() != y.size() || preds.size() != pids.size())
		MTHROW_AND_ERR("bootstrap sizes aren't equal preds=%zu y=%zu\n", preds.size(), y.size());
	string metric_name = get_loss_metric_name(metric);

	ROC_Params pr("score_resolution=0.0001;score_bins=0");
	if (roc_params == NULL) {
		roc_params = &pr;
	}
	float sample_ratio = (float)0.7;
	vector<Measurement_Params *> func_params = { roc_params };
	vector<int> preds_ord(preds.size());
	map<string, map<string, float>> bootstrap_res = booststrap_analyze(preds, preds_ord, y, weights, pids, additional_info,
		cohort_defs, meas_funs, NULL, &func_params, NULL, preprocess_bin_scores, roc_params, sample_ratio, samples_per_pid, loopCnt);
	if (output_file)
		write_pivot_bootstrap_results(f_name, bootstrap_res);

	float auc = bootstrap_res["All"][metric_name + "_Mean"];

	float auc_all = bootstrap_res["All"][metric_name + "AUC_Obs"];
	if (output_file)
		MLOG("Wrote [%s]\n", f_name.c_str());
	MLOG("%s_Mean=%f %s_Obs=%f\n", metric_name.c_str(), auc, metric_name.c_str(), auc_all);

	return bootstrap_res;
}

float evaluate_model(const vector<vector<MedFeatures>> &matrixes_folds, const vector<int> &selectedInd,
	MedPredictor *model, loss_metric metric) {
	double mean_auc = 0;
	vector<string> features;
	if (!(selectedInd.empty() || selectedInd.size() == matrixes_folds[0][0].data.size())) {
		matrixes_folds[0][0].get_feature_names(features);
		vector<string> selected(selectedInd.size());
		for (size_t i = 0; i < selected.size(); ++i)
			selected[i] = features[selectedInd[i]];
		features.swap(selected);
	}

	for (size_t loop_fold = 0; loop_fold < matrixes_folds.size(); ++loop_fold) {
		//fetch and prepare data
		vector<float> scores, test_labels(matrixes_folds[loop_fold][1].samples.size());
		MedMat<float> testMat;

		matrixes_folds[loop_fold][1].get_as_matrix(testMat, features);
		for (size_t i = 0; i < test_labels.size(); ++i)
			test_labels[i] = matrixes_folds[loop_fold][1].samples[i].outcome;

		//learn on train
		if (selectedInd.empty() || selectedInd.size() == matrixes_folds[loop_fold][0].data.size())
			model->learn(matrixes_folds[loop_fold][0]);
		else {
			//need to select features for train:
			MedFeatures selected_feats;
			selected_feats.samples = matrixes_folds[loop_fold][0].samples;
			selected_feats.weights = matrixes_folds[loop_fold][0].weights;

			for (const string &feat_name : features)
			{
				selected_feats.data[feat_name] = matrixes_folds[loop_fold][0].data.at(feat_name);
				selected_feats.attributes[feat_name] = matrixes_folds[loop_fold][0].attributes.at(feat_name);
			}

			selected_feats.init_pid_pos_len();
			model->learn(selected_feats);
		}
		//predcit on test
		model->predict(testMat, scores);
		//evaluate on test
		float auc = -loss_function_metric(metric, scores, test_labels, &matrixes_folds[loop_fold][1].weights, true);
		mean_auc += auc;
	}
	mean_auc /= matrixes_folds.size();

	return mean_auc;
}

map<string, map<string, float>> runExperiment(MedFeatures &dataMat, string f_name
	, bool(*filterTestCondition)(const MedFeatures &, int)
	, bool(*filterTrainCondition)(const MedFeatures &, int), bool filterTrainPid
	, MedPredictor *&model, vector<int> &selectedInd, float price_ratio, int kFold,
	const map<string, FilterCohortFunc> &cohort_defs, const vector<MeasurementFunctions> &measurement_functions, bool onTrain, bool returnOnlyAuc, loss_metric metric) {
	loss_fun_sig loss_function = get_loss_function(metric);
	string metric_name = get_loss_metric_name(metric);

	vector<int> pids;
	get_pids_shuffle(dataMat, pids);

	vector<float> all_preds;
	vector<float> all_y;
	vector<int> all_test_pid_ord;
	vector<int> all_y_time;
	vector<int> all_prediction_time;
	map<string, vector<float>> additional_info;
	for (size_t loop_fold = 0; loop_fold < kFold; ++loop_fold)
	{
		//cout << "Start CV = " << loop_fold << endl;
		//test on loop_fold fold: train on all the rest:

		//Create Train-Test
		vector<vector<float>> xTrain, xTest;
		vector<float> yTrain, yTest, weights;
		vector<int> test_pid_ord;
		vector<int> y_time;
		vector<int> prediction_time;
		vector<int> train_pids;
		prepate_train_test(dataMat, selectedInd, pids, filterTestCondition, filterTrainCondition, filterTrainPid,
			price_ratio, xTrain, xTest, yTrain, yTest, weights, test_pid_ord, y_time, prediction_time, train_pids, additional_info,
			kFold, loop_fold);

		//init and zero learning from other splits:
		time_t start_t = time(NULL);
		medial::models::initInfraModel((void *&)model);
		int duration = (int)difftime(time(NULL), start_t);
		MLOG_D("Took %d seconds to init model\n", duration);

		// Train Model on Train Data (Pids not in test_pids), and Test on test_pids
		start_t = time(NULL);
		medial::models::learnInfraModel(model, xTrain, yTrain, weights);
		duration = (int)difftime(time(NULL), start_t);
		MLOG_D("Took %d seconds to train\n", duration);

		//Get Preds for model:
		start_t = time(NULL);
		vector<float> preds;
		if (onTrain)
			preds = medial::models::predictInfraModel(model, xTrain);
		else
			preds = medial::models::predictInfraModel(model, xTest);
		duration = (int)difftime(time(NULL), start_t);
		MLOG_D("Took %d seconds to predict\n", duration);

		all_preds.insert(all_preds.end(), preds.begin(), preds.end());
		//concat all results:
		if (onTrain) {
			float auc_split = loss_function(preds, yTrain, &weights);
			cout << metric_name << " on Train Split=" << auc_split << endl;
			all_y.insert(all_y.end(), yTrain.begin(), yTrain.end());
		}
		else {
			all_y.insert(all_y.end(), yTest.begin(), yTest.end());
			all_test_pid_ord.insert(all_test_pid_ord.end(), test_pid_ord.begin(), test_pid_ord.end());
			all_y_time.insert(all_y_time.end(), y_time.begin(), y_time.end());
			all_prediction_time.insert(all_prediction_time.end(), prediction_time.begin(), prediction_time.end());
		}
	}
	map<string, map<string, float>> bootstrap_results;
	if (kFold > 0) {
		if (onTrain) {
			float auc = loss_function(all_preds, all_y, NULL);
			MLOG("%s on Train All=%f\n", metric_name.c_str(), auc);
		}
		else
			bootstrap_results = print_booststrap(all_preds, all_y, all_test_pid_ord, NULL, all_y_time, all_prediction_time, additional_info, cohort_defs, f_name,
				measurement_functions, NULL, 1, !returnOnlyAuc, returnOnlyAuc ? 100 : 500, metric);
	}

	if (returnOnlyAuc)
		return bootstrap_results;
	//run on all
	MLOG("Create model on all samples...\n");
	medial::models::initInfraModel((void*&)model);

	//match by year:
	MedFeatures train_records_dt;
	MedFeatures *train_records = &dataMat;
	if (price_ratio > 0) {
		train_records = &train_records_dt;
		train_records->attributes = dataMat.attributes;
		train_records->time_unit = dataMat.time_unit;
		train_records->samples = vector<MedSample>(dataMat.samples);
		train_records->data = map<string, vector<float>>(dataMat.data);
		train_records->weights = dataMat.weights;

		match_by_year(*train_records, price_ratio, 1, false);

		vector<int> lbl_cnt(2);
		for (size_t ii = 0; ii < train_records->samples.size(); ++ii)
			++lbl_cnt[train_records->samples[ii].outcome > 0];

		MLOG("Train Labels: [%d, %d] %2.4f\n", lbl_cnt[0], lbl_cnt[1], float(lbl_cnt[1]) / (lbl_cnt[0] + lbl_cnt[1]));
	}

	vector<vector<float>> xData((int)train_records->data.size());
	vector<float> y((int)train_records->samples.size());
	int ii = 0;
	for (auto it = train_records->data.begin(); it != train_records->data.end(); ++it)
	{
		xData[ii] = it->second;
		++ii;
	}
	for (size_t i = 0; i < y.size(); ++i)
		y[i] = train_records->samples[i].outcome;
	model->learn(*train_records);

	return bootstrap_results;
}

vector<int> find_simpler_model(MedFeatures &dataMat, float price_ratio, int kfold, float max_auc_change
	, float min_diff_th, void *model_input, const string &log_file, loss_metric metric) {
	//float max_auc_change = (float)0.01;
	//float min_diff_th = (float)0.001;
	//int kfold = 5;

	int log_lev = global_logger.levels[LOG_MEDSTAT];
	global_logger.levels[LOG_MEDSTAT] = MAX_LOG_LEVEL;
	MedPredictor *model = (MedPredictor *)model_input;
	//((MedQRF *)model)->params.ntry = 0;
	ofstream write_log;
	if (!log_file.empty()) {
		write_log.open(log_file);
		if (!write_log.good())
			MWARN("Unable to open file %s for writing\n", log_file.c_str());
	}

	vector<int> selectedI; //play with selected features for the exp:
	int max_features = (int)dataMat.data.size();
	selectedI.resize(max_features);
	for (size_t i = 0; i < max_features; ++i)
		selectedI[i] = (int)i;
	vector<vector<MedFeatures>> matrix_splits;
	prepare_splits(dataMat, selectedI, price_ratio, kfold, matrix_splits); //done once for all features

	float best_simpler = evaluate_model(matrix_splits, selectedI, model, metric);
	string measure_name = get_loss_metric_name(metric);

	medial::print::log_with_file(write_log, "Original: %s_Mean=%2.4f\n", measure_name.c_str(), best_simpler);
	vector<int> max_auc_sel, simpler_select, best_simpler_sel;
	vector<string> signalNames;
	dataMat.get_feature_names(signalNames);
	float simpler_auc = 0, max_auc = 0, last_auc = 0;
	simpler_select = selectedI;

	//find which to remove:
	int duration;
	while (true) {
		if (selectedI.size() == 1)
			break; //finished nothing to remove
		vector<int> remove_inds;
		//((MedQRF *)model)->params.ntry =0;
		int tot_done = 0;
		time_t start = time(NULL);
		time_t last_time_print = start;
		int best_removal = -1;
		float round_max_auc = -1;
		for (size_t i = 0; i < selectedI.size(); ++i)
		{
			vector<int> sel(selectedI.size() - 1);//shrink array by 1:

			for (size_t j = 0; j < sel.size(); ++j)
				sel[j] = selectedI[j + int(j >= i)];

			float auc = evaluate_model(matrix_splits, sel, model, metric);
			medial::print::log_with_file(write_log, "Without %s: %s_Mean=%2.4f\n",
				signalNames[selectedI[i]].c_str(), measure_name.c_str(), auc);
			if (auc > max_auc) {
				max_auc_sel.swap(sel);
				max_auc = auc;
			}
			if (best_removal == -1 || auc > round_max_auc) {
				round_max_auc = auc;
				best_removal = (int)i;
			}
			if (auc > best_simpler + min_diff_th)
				remove_inds.push_back((int)i);

#pragma omp atomic 
			++tot_done;
			duration = (int)difftime(time(NULL), last_time_print);
			if (duration >= 60) {
				int time_from_start = (int)difftime(time(NULL), start);
				double estimate = ((double)(selectedI.size() - tot_done) / tot_done) * time_from_start / 60.0;
				printf("Done %d out of %d(%2.2f%%). minutes_elapsed=%2.1f, estimate_minutes=%2.1f\n",
					tot_done, (int)selectedI.size(),
					100.0* double(tot_done) / selectedI.size(),
					time_from_start / 60.0, estimate);
				last_time_print = time(NULL);
			}

		}

		if (best_simpler - round_max_auc < max_auc_change) {
			//commit change - remove best feature to remove:
			if (remove_inds.size() > 0) {
				for (int i = (int)remove_inds.size() - 1; i >= 0; --i) {
					medial::print::log_with_file(write_log, "REMOVE %s\n", signalNames[selectedI[remove_inds[i]]].c_str());
					selectedI.erase(selectedI.begin() + remove_inds[i]);
				}
				float new_base_auc = evaluate_model(matrix_splits, selectedI, model, metric);
				simpler_select = selectedI; //current last simpler that should improve
				simpler_auc = new_base_auc;
				last_auc = new_base_auc;
				if (new_base_auc > best_simpler) {
					best_simpler = new_base_auc; //never goes down
					best_simpler_sel = selectedI; //save best simpler selection
				}
				if (new_base_auc > max_auc) {
					max_auc_sel = selectedI;
					max_auc = new_base_auc;
				}

				//best_simpler never goes down
				medial::print::log_with_file(write_log, "Max_AUC=%2.4f(has %zu features), new_model_after_selection_auc=%2.4f(has %zu features), best_simpler=%2.4f(has %zu features)\n",
					max_auc, max_auc_sel.size(), new_base_auc, selectedI.size(), best_simpler, best_simpler_sel.size());
			}
			else {
				medial::print::log_with_file(write_log, "REMOVE_w %s, left with %s=%2.4f\n",
					signalNames[selectedI[best_removal]].c_str(), measure_name.c_str(), round_max_auc);
				selectedI.erase(selectedI.begin() + best_removal);

				if (round_max_auc > simpler_auc) {
					simpler_select = selectedI; //current last simpler that improves
					simpler_auc = round_max_auc;
				}
				if (round_max_auc > best_simpler) {
					best_simpler = round_max_auc; //never goes down
					best_simpler_sel = selectedI; //save best simpler selection
				}
				if (round_max_auc > max_auc) {
					max_auc_sel = selectedI;
					max_auc = round_max_auc;
				}
				last_auc = round_max_auc;
			}

		}
		else //the diff is to big - stop!
			break; //no change to commit
	}

	MLOG("Finished: max_%s=%2.4f(%zu features), best_simpler_%s=%2.4f(%zu features), simplest_%s=%2.4f(%zu features)\n",
		measure_name.c_str(), max_auc, max_auc_sel.size(),
		measure_name.c_str(), best_simpler, best_simpler_sel.size(),
		measure_name.c_str(), simpler_auc, simpler_select.size());
	if (!max_auc_sel.empty() && max_auc_sel.size() != best_simpler_sel.size()) {
		medial::print::log_with_file(write_log, "Max %s with less params(feat_size=%zu)."
			" max_%s=%2.4f\nFeature List:\n", measure_name.c_str(), max_auc_sel.size(), measure_name.c_str(), max_auc);
		for (size_t i = 0; i < max_auc_sel.size(); ++i)
			medial::print::log_with_file(write_log, "%s\n", signalNames[max_auc_sel[i]].c_str());
	}
	if (max_auc_sel.empty())
		max_auc_sel = best_simpler_sel;

	if (!best_simpler_sel.empty() && simpler_select.size() != best_simpler_sel.size()) {
		medial::print::log_with_file(write_log, "Best simpler Model %s with less params(feat_size=%zu)."
			" best_simpler_%s=%2.4f\nFeature List:\n", measure_name.c_str(), best_simpler_sel.size(),
			measure_name.c_str(), best_simpler);
		for (size_t i = 0; i < best_simpler_sel.size(); ++i)
			medial::print::log_with_file(write_log, "%s\n", signalNames[best_simpler_sel[i]].c_str());
	}

	if (!simpler_select.empty() && simpler_select.size() != selectedI.size()) {
		medial::print::log_with_file(write_log, "Simpler Model %s with less params(feat_size=%zu)."
			" %s_base=%2.4f\nFeature List:\n", measure_name.c_str(), simpler_select.size(), measure_name.c_str(), simpler_auc);
		for (size_t i = 0; i < simpler_select.size(); ++i)
			medial::print::log_with_file(write_log, "%s\n", signalNames[simpler_select[i]].c_str());
	}
	if (max_auc_sel.empty())
		max_auc_sel = simpler_select;

	if (!selectedI.empty()) {
		medial::print::log_with_file(write_log, "Simplest Model %s with less params(feat_size=%zu)."
			" %s_base=%2.4f\nFeature List:\n", measure_name.c_str(), selectedI.size(), measure_name.c_str(), last_auc);
		for (size_t i = 0; i < selectedI.size(); ++i)
			medial::print::log_with_file(write_log, "%s\n", signalNames[selectedI[i]].c_str());
	}
	if (max_auc_sel.empty())
		max_auc_sel = selectedI;

	global_logger.levels[LOG_MEDSTAT] = log_lev;

	return max_auc_sel;
}

void backward_selection(const string &output_folder, const string &log_file,
	MedFeatures &data, float price_ratio, int kfold, float max_auc_change, float min_diff_th,
	int max_count, const vector<string> &signal_names, unordered_set<string> &final_list, void *model,
	loss_metric metric, double change_prior) {
	if (!file_exists(output_folder + path_sep() + "final_selection.list")) {
		MedFeatures copy;
		bool use_copy = false;
		if (data.samples.size() > max_count && change_prior > 0) {
			vector<int> sel_idx;
			medial::process::match_to_prior(data, change_prior, sel_idx);
		}
		if (data.samples.size() > max_count) {
			use_copy = true;
			double down_fact = double(max_count) / double(data.samples.size());
			MLOG("Down sampling by %2.2f\n", down_fact);
			copy = data;
			medial::process::down_sample(data, down_fact);
		}

		vector<int> selected = find_simpler_model(data, price_ratio, kfold, max_auc_change, min_diff_th,
			model, log_file, metric);
		for (int index : selected)
			final_list.insert(signal_names[index]);
		if (use_copy) {
			data.samples.swap(copy.samples);
			data.data.swap(copy.data);
			data.weights.swap(copy.weights);
			data.pid_pos_len.swap(copy.pid_pos_len);
			data.attributes.swap(copy.attributes);
			data.tags.swap(copy.tags);
			data.time_unit = copy.time_unit;
		}
		write_string_file(final_list, output_folder + path_sep() + "final_selection.list");
	}
	else {
		read_string_file(output_folder + path_sep() + "final_selection.list", final_list);
		MLOG("Read backward and final selection of %d features.\n", (int)final_list.size());
	}
}

void split_registry_train_test(const string &rep_path, MedRegistry &regRecords
	, vector<MedRegistryRecord> &only_train,
	vector<MedRegistryRecord> &only_test, MedRepository &rep) {
	vector<int> reg_pids;
	regRecords.get_pids(reg_pids);
	vector<string> signal_names = { "TRAIN", "BDATE" };
	if (rep.read_all(rep_path, reg_pids, signal_names) < 0)
		MTHROW_AND_ERR("Unable to read repository.\n");
	MedDictionarySections rep_dict = rep.dict;
	int trn_code = rep.sigs.sid("TRAIN");
	only_train.reserve(int(regRecords.registry_records.size() * 0.71));
	only_test.reserve(int(regRecords.registry_records.size() * 0.21));
	for (size_t i = 0; i < regRecords.registry_records.size(); ++i) {
		int trn_val = medial::repository::get_value(rep, regRecords.registry_records[i].pid, trn_code);
		if (trn_val == 1)
			only_train.push_back(regRecords.registry_records[i]);
		else if (trn_val == 2)
			only_test.push_back(regRecords.registry_records[i]);
		//skip external validation trn_code==3
	}
	MLOG("After split - train has %zu(%2.1f%%) records, test has %zu(%2.1f%%) records. total was %zu\n",
		only_train.size(), 100 * only_train.size() / float(regRecords.registry_records.size()),
		only_test.size(), 100 * only_test.size() / float(regRecords.registry_records.size()),
		regRecords.registry_records.size()
	);
	if (only_train.empty() || only_test.empty())
		MTHROW_AND_ERR("Error in split_registry_train_test - only_train or only_test is empty - please verify TRAIN sig\n");
}

void read_selected_model(const string &selected_mode_path,
	string &predictor_name, string &predictor_params) {
	if (file_exists(selected_mode_path)) {
		ifstream fr(selected_mode_path);
		if (!fr.good())
			MTHROW_AND_ERR("IOError: can't read selected model\n");
		string line;
		predictor_name = "";
		predictor_params = "";
		while (getline(fr, line)) {
			boost::trim(line);
			if (line.empty() || line[0] == '#')
				continue;
			vector<string> tokens;
			boost::split(tokens, line, boost::is_any_of("\t"));
			if (tokens.size() != 2)
				MTHROW_AND_ERR("wrong format in line \"%s\". searching for \"TAB\"", line.c_str());
			boost::trim(tokens[0]);
			boost::trim(tokens[1]);
			if (tokens[0] == "predictor_params")
				predictor_params += tokens[1];
			else if (tokens[0] == "predictor_name")
				predictor_name = tokens[1];
			else
				MTHROW_AND_ERR("wrong format in line \"%s\"\n"
					". command was \"%s\" and should be predictor_name|predictor_params",
					line.c_str(), tokens[0].c_str());
		}
		fr.close();
		if (predictor_name.empty() || predictor_params.empty())
			MTHROW_AND_ERR("missing predictor_params or predictor lines in file");
	}
	else
		MTHROW_AND_ERR("IOError: can't read selected model in %s\n",
			selected_mode_path.c_str());
}

void unorm_weights(MedFeatures &dataMat, const weights_params &params) {
	switch (params.method)
	{
	case propensity:
		for (size_t i = 0; i < dataMat.weights.size(); ++i)
			if (dataMat.weights[i] != 0) {
				if (dataMat.samples[i].outcome > 0)
					dataMat.weights[i] = 1 / dataMat.weights[i];
				else
					dataMat.weights[i] = -1 / dataMat.weights[i] + 1;
			}
		break;
		//with probabilty p we need to throw the case (event happend by itself) and in p prob we lost control
	case propensity_controls:
		for (size_t i = 0; i < dataMat.weights.size(); ++i)
			if (dataMat.weights[i] != 0)
				dataMat.weights[i] = 1 - (1 / dataMat.weights[i]);
		break;
	case outcome_event:
		for (size_t i = 0; i < dataMat.weights.size(); ++i)
			dataMat.weights[i] = dataMat.samples[i].outcome > 0 ? 1 - dataMat.weights[i] : 1;
		break;
	default:
		MTHROW_AND_ERR("unsupported method %d\n", params.method);
	}
}

void norm_weights(const vector<MedSample> &samples, vector<float> &weights, const weights_params &params, double propensity_cutoff = 0.005) {
	//lets divide by the prior: which means if example is similar to prior gets 1, otherwise using lift from prior
	switch (params.method)
	{
	case propensity:
		for (size_t i = 0; i < weights.size(); ++i)
			if (weights[i] >= propensity_cutoff &&
				weights[i] <= 1 - propensity_cutoff) {
				if (samples[i].outcome > 0)
					weights[i] = 1 / weights[i];
				else
					weights[i] = 1 / (1 - weights[i]);
			}
			else
				weights[i] = 0; //drop
		break;
		//with probabilty p we need to throw the case (event happend by itself) and in p prob we lost control
	case propensity_controls:
		for (size_t i = 0; i < weights.size(); ++i)
			if (weights[i] <= 1 - propensity_cutoff)
				weights[i] = 1 / (1 - weights[i]);
			else
				weights[i] = 0; //drop
		break;
	case outcome_event:
		for (size_t i = 0; i < weights.size(); ++i)
			weights[i] = samples[i].outcome > 0 ? 1 - weights[i] : 1;
		break;
	default:
		MTHROW_AND_ERR("unsupported method %d\n", params.method);
	}

	medial::print::print_hist_vec(weights, "weights hist", "%2.5f");
}

void fix_samples(MedSamples &samples, const MedFeatures &feats, bool print_warn) {
	int samples_before = samples.nSamples();
	if (samples_before != feats.samples.size()) {
		if (print_warn) {
			MLOG("MedSamples is %d, matrix has %zu, regenerating MedSamples\n",
				samples_before, feats.samples.size());
			global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "MedSamples is %d, matrix has %zu, regenerating MedSamples\n",
				samples_before, feats.samples.size());
		}
		samples.idSamples.clear();
		feats.get_samples(samples);
	}

}

float auc_samples(const vector<MedSample> &samples, const vector<float> *weights = NULL) {
	if (samples.empty())
		MTHROW_AND_ERR("Error in auc_samples - samples is empty\n");
	if (weights != NULL && !weights->empty() && weights->size() != samples.size())
		MTHROW_AND_ERR("Error in auc_samples - samples(%zu) and weights(%zu) not in same size\n",
			samples.size(), weights->size());
	if (samples.front().prediction.empty())
		MTHROW_AND_ERR("Error in auc_samples - no predictions\n");
	vector<float> y(samples.size()), preds(samples.size());
	bool has_0 = false, has_1 = false;
	for (size_t i = 0; i < samples.size(); ++i)
	{
		y[i] = samples[i].outcome;
		preds[i] = samples[i].prediction[0];
		has_0 |= y[i] <= 0;
		has_1 |= y[i] > 0;
	}
	if (!has_0 || !has_1) {
		if (has_0)
			MLOG("No AUC - got only controls\n");
		else
			MLOG("No AUC - got only cases\n");
		return -1;
	}
	else
		return medial::performance::auc_q(preds, y, weights);
}


void fix_scores_probs(MedSamples &samples, MedFeatures &risk_model_features,
	const string &rep_path, const weights_params &params, double change_prior,
	MedRegistry &registry) {
	MedFeatures train_matrix;
	unordered_set<string> selected_sigs;
	unordered_map<string, vector<float>> additional_bootstrap;

	MedModel secondry_model_calibrated;
	if (!params.secondery_medmodel_path.empty()) {
		ifstream mdl_file(params.secondery_medmodel_path);
		if (!mdl_file.good())
			MTHROW_AND_ERR("Unsupported initialization without MedModel %s\n",
				params.secondery_medmodel_path.c_str());
		mdl_file.close();
		secondry_model_calibrated.read_from_file(params.secondery_medmodel_path);
		secondry_model_calibrated.verbosity = 0;

		MLOG("Loaded secondry model %s\n", params.secondery_medmodel_path.c_str());
		global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Loaded secondry model %s\n", params.secondery_medmodel_path.c_str());
		medial::medmodel::apply(secondry_model_calibrated, samples, rep_path, MED_MDL_END);
	}

	if (params.medmodel_has_predictor && params.medmodel_has_calibrator) {
		//simple case - assume train & calibrated on diffrent set. otherwise, don't active both flags.
		MedModel model_calibrated;
		ifstream mdl_file(params.medmodel_path);
		if (!mdl_file.good())
			MTHROW_AND_ERR("Unsupported initialization without MedModel %s\n",
				params.medmodel_path.c_str());
		mdl_file.close();
		model_calibrated.read_from_file(params.medmodel_path);
		model_calibrated.verbosity = 0;

		medial::medmodel::apply(model_calibrated, samples, rep_path, MED_MDL_END);
		risk_model_features = move(model_calibrated.features);
		//multiply with secondry_model_calibrated:
		if (!params.secondery_medmodel_path.empty())
			for (size_t i = 0; i < risk_model_features.samples.size(); ++i)
				risk_model_features.samples[i].prediction[0] *= secondry_model_calibrated.features.samples[i].prediction[0];

		return;
	}

	if (!params.feature_selection_path.empty())
		read_string_file(params.feature_selection_path, selected_sigs);
	MLOG("Loading matrix on samples to apply calibration\n");
	load_test_matrix(samples, risk_model_features, additional_bootstrap, params.medmodel_path,
		selected_sigs, rep_path, change_prior);
	double factor = 1;
	//Get Risk scores for samples:
	MedModel mod;
	ifstream mdl_file(params.medmodel_path);
	if (!mdl_file.good())
		MTHROW_AND_ERR("Unsupported initialization without MedModel %s\n",
			params.medmodel_path.c_str());
	mdl_file.close();
	mod.read_from_file(params.medmodel_path);
	mod.verbosity = 0;
	MedPredictor *model;
	if (!params.medmodel_has_predictor) {
		model = MedPredictor::make_predictor(params.predictor_type);
		model->read_from_file(params.predictor_path);
	}
	else
		model = mod.predictor;

	//create matrix on original data - train only!:
	MedRegistry registry_censor;
	vector<MedRegistryRecord> only_train, only_test;
	MedRepository rep;
	MedSamples train_samples;
	if (!params.train_samples.empty())
		train_samples.read_from_file(params.train_samples);
	else {
		registry.read_text_file(params.registry_path);
		if (!params.censor_registry_path.empty())
			registry_censor.read_from_file(params.censor_registry_path);
		else if (!params.censor_registry_signal.empty())
			read_from_rep(params.censor_registry_signal, rep_path, registry_censor);
		split_registry_train_test(rep_path, registry, only_train, only_test, rep);
		MedSamplingStrategy *sampler = MedSamplingStrategy::make_sampler(params.sampler_type,
			params.sampler_params);
		sampler->init_sampler(rep);
		MedLabels train_labeler(params.labeling_params);
		train_labeler.prepare_from_registry(only_train, registry_censor.registry_records.empty() ? NULL : &registry_censor.registry_records);
		train_labeler.create_samples(sampler, train_samples);
		delete sampler;
	}
	MLOG("Loading matrix for train for calibration\n");
	int cntrl_cnt = 0, cases_cnt = 0;
	for (size_t i = 0; i < train_samples.idSamples.size(); ++i)
		for (size_t j = 0; j < train_samples.idSamples[i].samples.size(); ++j) {
			cases_cnt += train_samples.idSamples[i].samples[j].outcome > 0;
			cntrl_cnt += train_samples.idSamples[i].samples[j].outcome <= 0;
		}

	bool changed_prior = false;
	double prev_prior = load_test_matrix(train_samples, train_matrix, mod, additional_bootstrap,
		selected_sigs, rep_path, params.change_action_prior);
	if (prev_prior > 0)
		changed_prior = true;
	if (mod.LearningSet != NULL) {//when reading model from disk need to clean LearningSet before exit - valgrind
		delete static_cast<MedSamples *>(mod.LearningSet);
		mod.LearningSet = 0;
		mod.serialize_learning_set = false;
	}

	double case_cnt = 0;
	for (size_t i = 0; i < train_matrix.samples.size(); ++i)
		case_cnt += int(train_matrix.samples[i].outcome > 0);
	double init_prior = case_cnt / train_matrix.samples.size();
	if (prev_prior <= 0 && init_prior < params.change_action_prior) {
		vector<int> selection_idx;
		medial::process::match_to_prior(train_matrix, params.change_action_prior, selection_idx);
		case_cnt = 0;
		for (size_t i = 0; i < train_matrix.samples.size(); ++i)
			case_cnt += int(train_matrix.samples[i].outcome > 0);
		double final_prior = case_cnt / train_matrix.samples.size();
		MLOG("Change Prior from %2.3f%% to %2.3f%%\n", 100 * init_prior, 100 * final_prior);
		changed_prior = true;
	}
	if (changed_prior) {
		int controls2_cnt = 0;
		for (size_t i = 0; i < train_matrix.samples.size(); ++i)
			controls2_cnt += int(train_matrix.samples[i].outcome <= 0);
		factor = double(cntrl_cnt) / controls2_cnt;
	}

	model->predict(risk_model_features);
	vector<float> preds_samples(risk_model_features.samples.size()); //before norm for testing
	for (size_t i = 0; i < risk_model_features.samples.size(); ++i)
		preds_samples[i] = risk_model_features.samples[i].prediction[0];
	//collect predicition in CV manner:
	vector<float> train_preds;
	if (params.nfolds > 0) {
		random_device rd;
		mt19937 gen(rd());
		if (params.down_sample_to > 0 && train_matrix.samples.size() > params.down_sample_to) {
			int init_sz = (int)train_matrix.samples.size();
			medial::process::down_sample(train_matrix, (double)params.down_sample_to / train_matrix.samples.size());
			MLOG("Down samples of train mat from %d to %zu by %1.4f\n",
				init_sz, train_matrix.samples.size(), (double)params.down_sample_to / init_sz);
		}
		medial::print::print_samples_stats(train_matrix.samples);
		medial::models::get_pids_cv(model, train_matrix, params.nfolds, gen, train_preds);
		vector<float> lbls(train_matrix.samples.size());
		for (size_t i = 0; i < train_matrix.samples.size(); ++i) {
			train_matrix.samples[i].prediction = { train_preds[i] };
			lbls[i] = train_matrix.samples[i].outcome;
		}
		if (params.nfolds > 1)
			MLOG("Learn with CV, AUC=%2.4f\n", medial::performance::auc_q(train_preds, lbls));
		else
			MLOG("Learned on train, AUC=%2.4f\n", medial::performance::auc_q(train_preds, lbls));
	}
	else {
		model->predict(train_matrix); //predict on right sampled data set to caliberate
		train_preds.resize(train_matrix.samples.size());
		vector<float> lbls(train_matrix.samples.size());
		for (size_t i = 0; i < train_matrix.samples.size(); ++i) {
			train_preds[i] = train_matrix.samples[i].prediction[0];
			lbls[i] = train_matrix.samples[i].outcome;
		}
		MLOG("Learned AUC=%2.4f\n", medial::performance::auc_q(train_preds, lbls));
	}

	medial::print::print_hist_vec(train_preds, "scores hist", "%2.5f");
	medial::print::print_hist_vec(preds_samples, "scores hist for samples in validation", "%2.5f");

	Calibrator cl;
	cl.init_from_string(params.calibration_init);
	cl.control_weight_down_sample = factor;
	cl.Learn(train_matrix.samples);
	cl.Apply(risk_model_features.samples);

	if (factor != 1) {
		MLOG("Control Factor=%f\n", factor);
		global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Control Factor=%f\n", factor);
	}

	if (!params.medmodel_has_predictor)
		delete model;
	//multiply with secondry_model_calibrated:
	if (!params.secondery_medmodel_path.empty())
		for (size_t i = 0; i < risk_model_features.samples.size(); ++i)
			risk_model_features.samples[i].prediction[0] *= secondry_model_calibrated.features.samples[i].prediction[0];
}

void get_probs_weights(MedSamples &samples, const string &rep_path, const weights_params &params,
	vector<float> &weights, vector<int> &sel_idx, double change_prior) {
	MedFeatures model_features;
	MedRegistry weight_reg;
	weight_reg.read_text_file(params.registry_path);

	fix_scores_probs(samples, model_features, rep_path, params, change_prior, weight_reg);

	if (params.medmodel_has_predictor && params.medmodel_has_calibrator) {
		//simple case - assume train & calibrated on diffrent set. otherwise, don't active both flags.
		model_features.weights.resize(model_features.samples.size());
		for (size_t i = 0; i < model_features.samples.size(); ++i)
			model_features.weights[i] = model_features.samples[i].prediction[0];
		medial::print::print_hist_vec(model_features.weights, "scores hist for samples in validation", "%2.5f");
		//Need to change outcome for propensity to be as new registry:
		unordered_map<int, vector<const MedRegistryRecord *>> pid_to_reg;
		for (size_t i = 0; i < weight_reg.registry_records.size(); ++i)
			pid_to_reg[weight_reg.registry_records[i].pid].push_back(&weight_reg.registry_records[i]);
		vector<const MedRegistryRecord *> empty_censor;

		int miss_pid = 0, multi_smp = 0;
		MedLabels all_labeler(params.labeling_params);
		all_labeler.prepare_from_registry(weight_reg.registry_records);
		for (size_t i = 0; i < model_features.samples.size(); ++i)
		{
			int smp_time = model_features.samples[i].time;
			int pid = model_features.samples[i].id;
			//get new label:
			vector<MedSample> samples_match;
			SamplingRes r = all_labeler.get_samples(pid, smp_time, samples_match);
			if (r.miss_pid_in_reg_cnt > 0) {
				++miss_pid;
				if (miss_pid < 5)
					MWARN("Warning - Can't find pid %d in registry - ignoring\n", pid);
				continue;
			}
			if (samples_match.size() != 1) {
				++multi_smp;
				if (multi_smp < 5)
					MWARN("Warning - empty/multiple(%zu) labels for sample %d for time %d in registry - ignoring\n",
						samples_match.size(), pid, smp_time);
				continue;
			}
			model_features.samples[i].outcome = samples_match[0].outcome;
			sel_idx.push_back((int)i);
		}
		if (miss_pid > 0 || multi_smp > 0) {
			MWARN("Has %d missing pids and %d empty/multiple labels for same sample so ignoring them...\n", miss_pid, multi_smp);
			global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
				"Has %d missing pids and %d empty/multiple labels for same sample so ignoring them...\n", miss_pid, multi_smp);
		}
		medial::process::filter_row_indexes(model_features, sel_idx);
		//Test AUC:
		float auc_prop = auc_samples(model_features.samples);
		MLOG("AUC of new model %s = %2.3f\n", params.medmodel_path.c_str(), auc_prop);
		global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "AUC of new model %s = %2.3f\n", params.medmodel_path.c_str(), auc_prop);

		norm_weights(model_features.samples, model_features.weights, params, 0.005);

		weights.resize(model_features.samples.size(), 1);
		for (size_t i = 0; i < model_features.samples.size(); ++i)
			weights[i] = model_features.weights[i];

		medial::print::print_hist_vec(weights, "bootstrap weights hist", "%2.5f");

		return;
	}

	model_features.weights.resize(model_features.samples.size());
	for (size_t i = 0; i < model_features.samples.size(); ++i)
		model_features.weights[i] = model_features.samples[i].prediction[0];
	//Need to change outcome for propensity to be as new registry:
	unordered_map<int, vector<const MedRegistryRecord *>> pid_to_reg;
	for (size_t i = 0; i < weight_reg.registry_records.size(); ++i)
		pid_to_reg[weight_reg.registry_records[i].pid].push_back(&weight_reg.registry_records[i]);

	int miss_pid = 0, multi_smp = 0;
	MedLabels all_labeler(params.labeling_params);
	all_labeler.prepare_from_registry(weight_reg.registry_records);
	for (size_t i = 0; i < model_features.samples.size(); ++i)
	{
		int smp_time = model_features.samples[i].time;
		int pid = model_features.samples[i].id;
		//get new label:
		vector<MedSample> samples_match;
		SamplingRes r = all_labeler.get_samples(pid, smp_time, samples_match);
		if (r.miss_pid_in_reg_cnt > 0) {
			++miss_pid;
			if (miss_pid < 5)
				MWARN("Warning - Can't find pid %d in registry - ignoring\n", pid);
			continue;
		}
		if (samples_match.size() != 1) {
			++multi_smp;
			if (multi_smp < 5)
				MWARN("Warning - empty/multiple(%zu) labels for sample %d for time %d in registry - ignoring\n",
					samples_match.size(), pid, smp_time);
			continue;
		}
		model_features.samples[i].outcome = samples_match[0].outcome;
		sel_idx.push_back((int)i);
	}
	if (miss_pid > 0 || multi_smp > 0) {
		MWARN("Has %d missing pids and %d empty/multiple labels for same sample so ignoring them...\n", miss_pid, multi_smp);
		global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
			"Has %d missing pids and %d empty/multiple labels for same sample so ignoring them...\n", miss_pid, multi_smp);
	}
	medial::process::filter_row_indexes(model_features, sel_idx);
	float auc_prop = auc_samples(model_features.samples);
	MLOG("AUC of new model %s = %2.3f\n", params.medmodel_path.c_str(), auc_prop);
	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "AUC of new model %s = %2.3f\n", params.medmodel_path.c_str(), auc_prop);

	norm_weights(model_features.samples, model_features.weights, params, 0.005);

	weights.resize(model_features.samples.size(), 1);
	for (size_t i = 0; i < model_features.samples.size(); ++i)
		weights[i] = model_features.weights[i];

	medial::print::print_hist_vec(weights, "bootstrap weights hist", "%2.5f");
}

void assign_weights(const string &rep_path, MedFeatures &dataMat, const weights_params &params,
	bool do_norm, double change_prior) {
	if (!params.active) //no use
		return;
	//create MedSamples from dataMat
	MedSamples train_samples;
	unordered_map<int, int> pid_to_index;
	for (size_t i = 0; i < dataMat.samples.size(); ++i)
	{
		MedSample sample = dataMat.samples[i];
		if (pid_to_index.find(dataMat.samples[i].id) == pid_to_index.end()) {
			MedIdSamples sample_id(dataMat.samples[i].id);
			pid_to_index[dataMat.samples[i].id] = (int)train_samples.idSamples.size();
			sample_id.samples.push_back(sample);
			train_samples.idSamples.push_back(sample_id);
		}
		else
			train_samples.idSamples[pid_to_index[dataMat.samples[i].id]].samples.push_back(sample);
	}

	MLOG("Assigning Weights..\n");
	//use other model for risk score:
	string feature_model_path = params.medmodel_path;
	string feat_sel_path = params.feature_selection_path;
	string model_path = params.predictor_path;
	string registry_path = params.registry_path;
	//to pass registry that we can sample validation incidence set by ourseleves
	//string binary_original_mat_path = base_path + separator() + "features.bin";

	MedFeatures risk_model_features;
	MedRegistry other_model_reg;
	fix_scores_probs(train_samples, risk_model_features,
		rep_path, params, change_prior, other_model_reg);
	if (do_norm) {
		if (params.method == weighting_method::propensity) {
			MedLabels all_labeler(params.labeling_params);
			all_labeler.prepare_from_registry(other_model_reg.registry_records);
			//Need to change outcome for propensity to be as new registry:
			unordered_map<int, vector<const MedRegistryRecord *>> pid_to_reg;
			for (size_t i = 0; i < other_model_reg.registry_records.size(); ++i)
				pid_to_reg[other_model_reg.registry_records[i].pid].push_back(&other_model_reg.registry_records[i]);
			vector<const MedRegistryRecord *> empty_censor;

			vector<int> sel_idx;
			int miss_pid = 0, multi_smp = 0;
			for (size_t i = 0; i < risk_model_features.samples.size(); ++i)
			{
				int smp_time = risk_model_features.samples[i].time;
				int pid = risk_model_features.samples[i].id;
				//get new label:
				vector<MedSample> samples_match;
				SamplingRes r = all_labeler.get_samples(pid, smp_time, samples_match);
				if (r.miss_pid_in_reg_cnt > 0) {
					++miss_pid;
					if (miss_pid < 5)
						MWARN("Warning - Can't find pid %d in registry - ignoring\n", pid);
					continue;
				}
				if (samples_match.size() != 1) {
					++multi_smp;
					if (multi_smp < 5)
						MWARN("Warning - empty/multiple(%zu) labels for sample %d for time %d in registry - ignoring\n",
							samples_match.size(), pid, smp_time);
					continue;
				}
				risk_model_features.samples[i].outcome = samples_match[0].outcome;
				sel_idx.push_back((int)i);
			}
			if (miss_pid > 0 || multi_smp > 0) {
				MWARN("Has %d missing pids and %d empty/multiple labels for same sample so ignoring them...\n", miss_pid, multi_smp);
				global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
					"Has %d missing pids and %d empty/multiple labels for same sample so ignoring them...\n", miss_pid, multi_smp);
			}
			medial::process::filter_row_indexes(risk_model_features, sel_idx);
			medial::process::filter_row_indexes(dataMat, sel_idx);
			float auc_prop = auc_samples(risk_model_features.samples);
			MLOG("AUC of new model %s = %2.3f\n", params.medmodel_path.c_str(), auc_prop);
			global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "AUC of new model %s = %2.3f\n", params.medmodel_path.c_str(), auc_prop);
		}
		risk_model_features.weights.resize(risk_model_features.samples.size());
		for (size_t i = 0; i < risk_model_features.weights.size(); ++i)
			risk_model_features.weights[i] = risk_model_features.samples[i].prediction[0];
		norm_weights(risk_model_features.samples, risk_model_features.weights, params);

		//assign weights to new model:
		dataMat.weights.resize((int)dataMat.samples.size());
		for (size_t i = 0; i < dataMat.samples.size(); ++i)
			dataMat.weights[i] = risk_model_features.weights[i];
	}
	else {
		//assign weights to new model:
		dataMat.weights.resize((int)dataMat.samples.size());
		for (size_t i = 0; i < dataMat.weights.size(); ++i)
			dataMat.weights[i] = risk_model_features.samples[i].prediction[0];
	}

	//Print prob hist:
	medial::print::print_hist_vec(dataMat.weights, "probability hist", "%2.5f");
	MLOG("Done Weights\n");
}

template<class T> string list_signals(const map<string, T> &f, const string &delimeter) {
	string res = "";
	auto it = f.begin();
	if (it != f.end())
		res += it->first;
	for (; it != f.end(); ++it)
		res += delimeter + it->first;

	return res;
}
template string list_signals<vector<float>>(const map<string, vector<float>> &f, const string &delimeter);

template<class T> string get_name(const map<string, T> &mapper, const string &col_name, bool throw_error) {
	string cl_name = col_name;
	clean_ftr_name(cl_name);
	for (auto i = mapper.begin(); i != mapper.end(); ++i)
		if (i->first.find(cl_name) != string::npos) //finds exact name
			return i->first;
	string all_options = list_signals(mapper, "\n");

	MERR("Not found \"%s\" in options:\n%s\n", all_options.c_str(), col_name.c_str());
	if (throw_error)
		MTHROW_AND_ERR("Not found \"%s\" in options:\n%s\n", all_options.c_str(), col_name.c_str());
	return "";
}
template string get_name<vector<float>>(const map<string, vector<float>> &mapper, const string &col_name, bool throw_error);

void run_bootstrap(const string &rep, MedFeatures &validation_data,
	const unordered_map<string, vector<float>> &additional_bootstrap,
	const string &bootstrap_params, const string &cohort_file, const weights_params &weights_args,
	const string &output_path, const string &model_name, vector<float> &compare_preds,
	vector<float> *ret_weights, loss_metric metric, with_registry_args *bootstrap_reg_args) {
	MedSamples validation_smp;
	validation_data.get_samples(validation_smp);
	validation_smp.write_to_file(output_path + path_sep()
		+ "validation_" + model_name + ".preds");
	if (!validation_data.weights.empty()) {
		stringstream file_cont;
		for (size_t i = 0; i < validation_data.weights.size(); ++i)
			file_cont << validation_data.weights[i] << "\n";
		string final_str = file_cont.str();
		string weights_pt = output_path + path_sep()
			+ "validation_" + model_name + ".weights";
		write_string(weights_pt, final_str);
		global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
			"writing weights to %s\n", weights_pt.c_str());
	}
	//validate results for real:
	MedBootstrapResult b;
	b.bootstrap_params.init_from_string(bootstrap_params);
	if (!cohort_file.empty()) {
		b.bootstrap_params.filter_cohort.clear();
		b.bootstrap_params.parse_cohort_file(cohort_file);
	}
	MeasurementFunctions boot_function = get_loss_function_bootstrap(metric);
	b.bootstrap_params.measurements_with_params = {
		pair<MeasurementFunctions, Measurement_Params *>(boot_function, metric == loss_metric::auc ? &b.bootstrap_params.roc_Params
		: NULL) };
	if (metric != auc)
		b.bootstrap_params.measurements_with_params.push_back(pair<MeasurementFunctions, Measurement_Params *>(calc_npos_nneg, NULL));

	MedFeatures *final_feats = &validation_data;
	MedFeatures cp_feats;
	if (!additional_bootstrap.empty()) {
		cp_feats = validation_data;
		for (auto it = additional_bootstrap.begin(); it != additional_bootstrap.end(); ++it)
			cp_feats.data[it->first] = it->second;
		final_feats = &cp_feats;
	}
	compare_preds.resize(final_feats->samples.size());
	for (size_t i = 0; i < final_feats->samples.size(); ++i)
		compare_preds[i] = final_feats->samples[i].prediction[0];

	//Debug  weights:
	if (!final_feats->weights.empty()) {
		if (final_feats->weights.size() != final_feats->samples.size())
			MTHROW_AND_ERR("bootstrap Error: samples and weights not same size\n");
		for (size_t i = 0; i < final_feats->samples.size(); ++i)
			if (final_feats->weights[i] <= 0)
				MTHROW_AND_ERR("bootstrap Error: got weights[%zu]=%f. should be positive\n", i,
					final_feats->weights[i]);

	}

	b.bootstrap(*final_feats, NULL, bootstrap_reg_args);

	b.write_results_to_text_file(output_path + path_sep()
		+ "validation_" + model_name + ".pivot.csv");
	string measure_name = get_loss_metric_name(metric) + "_Mean";
	for (auto it = b.bootstrap_results.begin(); it != b.bootstrap_results.end(); ++it)
		if (it->second.find(measure_name) != it->second.end()) {
			MLOG("%s$%s=%f\n", it->first.c_str(), measure_name.c_str(), it->second.at(measure_name));
			global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "%s$%s=%f\n",
				it->first.c_str(), measure_name.c_str(), it->second.at(measure_name));
		}
	if (weights_args.active && weights_args.method == weighting_method::outcome_event) {
		//do also with weights:
		b.bootstrap_params.roc_Params.fix_label_to_binary = false;
		b.bootstrap_params.is_binary_outcome = false;
		vector<float> bootstrap_w_backup;
		if (!final_feats->weights.empty())
			bootstrap_w_backup = final_feats->weights;

		if (ret_weights == NULL || ret_weights->empty()) {
			MLOG("calcing weights for bootstrap..\n");
			global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "calcing weights for bootstrap..\n");
			assign_weights(rep, *final_feats, weights_args, false, weights_args.change_action_prior);
			ret_weights->resize(final_feats->weights.size());
			for (size_t i = 0; i < final_feats->weights.size(); ++i)
				(*ret_weights)[i] = final_feats->weights[i];
		}
		else { //read from given ret_weights
			global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "using old weights for bootstrap\n");
			final_feats->weights.resize(ret_weights->size());
			for (size_t i = 0; i < final_feats->weights.size(); ++i)
				final_feats->weights[i] = (*ret_weights)[i];
		}
		//TODO: support for more weights methods - now only for outcome_event (influenza removal of other event)
		if (weights_args.method == weighting_method::outcome_event) {
			string full_search_name = "";
			if (!weights_args.norm_weight_condition.empty() && !weights_args.norm_all)
			{
				vector<string> all_names;
				final_feats->get_feature_names(all_names);
				int pos_f = find_in_feature_names(all_names, weights_args.norm_weight_condition);
				full_search_name = all_names[pos_f];
			}
			for (size_t i = 0; i < final_feats->weights.size(); ++i)
				if (weights_args.norm_weight_condition.empty() || weights_args.norm_all || final_feats->data.at(full_search_name)[i] > 0)
					final_feats->samples[i].outcome -= final_feats->weights[i];
		}
		if (!bootstrap_w_backup.empty())
			final_feats->weights = bootstrap_w_backup;
		else
			final_feats->weights.clear();


		medial::print::print_samples_stats(final_feats->samples);
		MedSamples weighted_samples;
		final_feats->get_samples(weighted_samples);
		weighted_samples.write_to_file(output_path + path_sep()
			+ "validation_weighted_" + model_name + ".preds");
		b.bootstrap_results.clear();
		b.bootstrap(*final_feats, NULL, bootstrap_reg_args);
		b.write_results_to_text_file(output_path + path_sep()
			+ "validation_weighted_" + model_name + ".pivot.csv");
		for (auto it = b.bootstrap_results.begin(); it != b.bootstrap_results.end(); ++it)
			if (it->second.find(measure_name) != it->second.end()) {
				MLOG("WEIGHTED %s$%s=%f\n", it->first.c_str(), measure_name.c_str(), it->second.at(measure_name));
				global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "WEIGHTED %s$%s=%f\n",
					it->first.c_str(), measure_name.c_str(), it->second.at(measure_name));
			}
	}
}

void read_compare_models(const string &file_path, vector<pair<string, compare_model_params>> &model_name_json) {
	ifstream fr(file_path);
	if (!fr.good())
		MTHROW_AND_ERR("IOError: Can't open %s for reading\n", file_path.c_str());
	string line;
	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("IOError: bad file format %s expected TAB delimieter with 2 fields"
				" got line:\n%s\n", file_path.c_str(), line.c_str());
		string &model_name = tokens.front();
		string &model_config = tokens.back();
		boost::trim(model_name);
		boost::trim(model_config);
		compare_model_params model_params;
		model_params.init_from_string(model_config);

		if (!file_exists(model_params.model_path))
			MTHROW_AND_ERR("File %s has wrong model path. json model not exist:\n%s\n"
				, file_path.c_str(), model_params.model_path.c_str());
		if (!model_params.selected_features_file.empty() &&
			!file_exists(model_params.selected_features_file))
			MTHROW_AND_ERR("File %s has wrong selected features path. path not exist:\n%s\n"
				, file_path.c_str(), model_params.selected_features_file.c_str());

		model_name_json.push_back(pair<string, compare_model_params>(model_name, model_params));
	}
	fr.close();
}

void run_compare_model(const pair<string, compare_model_params> &param,
	MedSamples &train_samples, MedSamples &validation_samples, const vector<float> *bootstrap_weights,
	const unordered_map<string, vector<float>> &additional_feature_bootstrap,
	const string &rep_path, const string &bootstrap_params,
	const string &cohort_file, const weights_params &weights_args,
	const string &bootstrap_output_path, vector<float> &compare_preds, vector<float> *ret_weights, loss_metric metric,
	double change_prior, with_registry_args *bootstrap_reg_args) {
	const compare_model_params &mdl_params = param.second;
	MLOG("Running on \"%s\":\n", param.first.c_str());
	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Running on \"%s\":\n", param.first.c_str());
	MedPidRepository dataManager;
	MedModel med_other;
	MedPredictor *other = NULL;
	unordered_set<string> feat_sel;
	MedFeatures *validation_for_other;
	unordered_map<string, vector<float>> additional_bootstrap = additional_feature_bootstrap;
	unordered_map<string, vector<float>> more_feats;

	if (!mdl_params.selected_features_file.empty())
		read_string_file(mdl_params.selected_features_file, feat_sel);

	//learn on train
	if (mdl_params.need_learn) {
		med_other.init_from_json_file(mdl_params.model_path);
		prepare_model_from_json(train_samples, rep_path, med_other, dataManager, change_prior);
		med_other.learn(dataManager, &train_samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
		MedFeatures &train_for_other = med_other.features;
		other = med_other.predictor;

		if (!mdl_params.selected_features_file.empty())
			commit_selection(train_for_other, feat_sel);
		if (mdl_params.final_score_calc == "predictor")
			other->learn(train_for_other); //on train samples
										   //predict on validation
		medial::repository::prepare_repository(validation_samples, rep_path, med_other, dataManager);
		med_other.apply(dataManager, validation_samples, MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_APPLY_FTR_PROCESSORS);

		if (!mdl_params.selected_features_file.empty())
			commit_selection(med_other.features, feat_sel);
		validation_for_other = &med_other.features;
	}
	else {
		MLOG("Loading matrix for other model\n");
		med_other.read_from_file(mdl_params.model_path);
		med_other.verbosity = 0;
		load_test_matrix(validation_samples, med_other.features, med_other, more_feats,
			feat_sel, rep_path, change_prior);
		if (med_other.LearningSet != NULL) {//when reading model from disk need to clean LearningSet before exit - valgrind
			delete static_cast<MedSamples *>(med_other.LearningSet);
			med_other.LearningSet = 0;
			med_other.serialize_learning_set = false;
		}

		if (!mdl_params.predictor_type.empty() && !mdl_params.predictor_path.empty()) {
			other = MedPredictor::make_predictor(mdl_params.predictor_type);
			other->read_from_file(mdl_params.predictor_path);
		}
		else
			other = med_other.predictor;

		for (auto it = more_feats.begin(); it != more_feats.end(); ++it)
		{
			string clean_name = it->first;
			clean_ftr_name(clean_name);
			if (additional_bootstrap.find(clean_name) != additional_bootstrap.end())
				if (clean_name != "Age" && clean_name != "Gender")
					MWARN("Has %s also in model - override\n", clean_name.c_str());
			additional_bootstrap[clean_name].swap(it->second);
		}

		validation_for_other = &med_other.features;
	}

	if (mdl_params.final_score_calc == "predictor")
		other->predict(*validation_for_other);
	else {
		string exact_name = get_name(validation_for_other->data, mdl_params.final_score_calc, false);
		if (exact_name.empty()) {
			MERR("ERROR: compare model %s has final_score_calc=%s. "
				"not found in model features\n", param.first.c_str(),
				mdl_params.final_score_calc.c_str());
			return;
		}
		for (size_t i = 0; i < validation_for_other->samples.size(); ++i)
			validation_for_other->samples[i].prediction = { validation_for_other->data[exact_name][i] };
	}
	if (bootstrap_weights != NULL && !bootstrap_weights->empty())
		validation_for_other->weights = *bootstrap_weights;

	run_bootstrap(rep_path, *validation_for_other, additional_bootstrap, bootstrap_params,
		cohort_file, weights_args, bootstrap_output_path, param.first, compare_preds, ret_weights, metric,
		bootstrap_reg_args);

	if (!mdl_params.predictor_type.empty() && !mdl_params.predictor_path.empty())
		delete other;
}

void plotAUC_graphs(const vector<float> &yFixed, const map<string, vector<float>> &dataMat,
	const vector<vector<float>> &all_model_preds, const vector<float> *weights, const vector<string> &model_names,
	const string &cohort_file, const string &bootstrap_output_base) {
	medial::print::print_hist_vec(yFixed, "plotAUC::labels histogram", "%2.4f");
	vector<bool> selected_indexes((int)yFixed.size(), true);
	MedBootstrap b_params;
	if (!cohort_file.empty()) {
		b_params.filter_cohort.clear();
		b_params.parse_cohort_file(cohort_file);
	}

	map<string, FilterCohortFunc> bootstrap_cohorts;
	map<string, void *> filter_params;
	for (auto it = b_params.filter_cohort.begin(); it != b_params.filter_cohort.end(); ++it) {
		bootstrap_cohorts[it->first] = filter_range_params;
		filter_params[it->first] = &it->second;
	}
	for (auto it = b_params.additional_cohorts.begin(); it != b_params.additional_cohorts.end(); ++it)
		if (bootstrap_cohorts.find(it->first) == bootstrap_cohorts.end()) {
			bootstrap_cohorts[it->first] = it->second;
			filter_params[it->first] = NULL;
		}
		else
			MWARN("Cohort \"%s\" name already exists - skip additional\n", it->first.c_str());
	for (auto it = bootstrap_cohorts.begin(); it != bootstrap_cohorts.end(); ++it)
	{
		int rec_cout = 0;
		bool has_both_classes = false;
		int prev_id = -1;
		for (size_t i = 0; i < selected_indexes.size(); ++i) {
			selected_indexes[i] = it->second(dataMat, (int)i, filter_params[it->first]);
			rec_cout += (selected_indexes[i]);
			if (!has_both_classes && prev_id > 0 && selected_indexes[i])
				has_both_classes = yFixed[i] != yFixed[prev_id];
			if (selected_indexes[i])
				prev_id = (int)i;
		}
		if (rec_cout < 100) {
			MLOG("Empty Graph \"%s\" Skiping...\n", it->first.c_str());
			continue;
		}
		if (!has_both_classes) {
			MLOG("Has only one class \"%s\" Skiping...\n", it->first.c_str());
			continue;
		}
		string filter_name = it->first;
		fix_filename_chars(&filter_name, '_');
		plotAUC(all_model_preds, yFixed, model_names, bootstrap_output_base + path_sep() +
			filter_name, selected_indexes, weights);
	}
}

void clean_ftr_name(string &name) {
	if (boost::starts_with(name, "FTR_") && name.find(".") != string::npos)
		name = name.substr(name.find(".") + 1);
}

float loss_function_metric(loss_metric metric, const vector<float> &preds, const vector<float> &labels,
	const vector<float> *weights, bool make_smaller_better) {

	switch (metric)
	{
	case auc:
		if (!make_smaller_better)
			return medial::performance::auc_q(preds, labels, weights);
		else
			return -medial::performance::auc_q(preds, labels, weights);
	case kendall_tau:
		if (!make_smaller_better)
			return medial::performance::kendall_tau_without_cleaning(preds, labels, weights);
		else
			return -abs(medial::performance::kendall_tau_without_cleaning(preds, labels, weights));
	case accurarcy:
		return medial::performance::accuracy(preds, labels, weights);
	case RMSE:
		return medial::performance::rmse_without_cleaning(preds, labels, weights);
	default:
		MTHROW_AND_ERR("loss_function_metric - Not implemented metric %d\n", metric);
	}


}

loss_fun_sig get_loss_function(loss_metric metric, bool make_smaller_better) {
	loss_fun_sig fun;
	switch (metric)
	{
	case auc:
		if (!make_smaller_better)
			fun = [](const vector<float> &preds, const vector<float> &labels,
				const vector<float> *weights) {
			return (double)medial::performance::auc_q(preds, labels, weights);
		};
		else
			fun = [](const vector<float> &preds, const vector<float> &labels,
				const vector<float> *weights) {
			return -(double)medial::performance::auc_q(preds, labels, weights);
		};
		break;
	case kendall_tau:
		if (!make_smaller_better)
			fun = [](const vector<float> &preds, const vector<float> &labels,
				const vector<float> *weights) {
			return medial::performance::kendall_tau_without_cleaning(preds, labels, weights);
		};
		else
			fun = [](const vector<float> &preds, const vector<float> &labels,
				const vector<float> *weights) {
			return -abs(medial::performance::kendall_tau_without_cleaning(preds, labels, weights));
		};
		break;
	case accurarcy:
		fun = [](const vector<float> &preds, const vector<float> &labels,
			const vector<float> *weights) {
			return (double)medial::performance::accuracy(preds, labels, weights);
		};
		break;
	case RMSE:
		fun = [](const vector<float> &preds, const vector<float> &labels,
			const vector<float> *weights) {
			return (double)medial::performance::rmse_without_cleaning(preds, labels, weights);
		};
		break;
	default:
		MTHROW_AND_ERR("get_loss_function - Not implemented metric %d\n", metric);
	}

	return fun;
}

map<string, float> calc_rmse(Lazy_Iterator *iterator, int thread_num, Measurement_Params *params) {
	map<string, float> res;

	float pred_val, label, weight;
	double total_cnt = 0, sum_prd = 0;
	while (iterator->fetch_next_external(thread_num, label, pred_val, weight)) {
		total_cnt += weight != -1 ? weight : 1;
		sum_prd += (weight != -1 ? weight : 1) * (pred_val - label)*(pred_val - label);
	}
	total_cnt += weight != -1 ? weight : 1;
	sum_prd += (weight != -1 ? weight : 1) *(pred_val - label)*(pred_val - label);
	sum_prd /= total_cnt;
	sum_prd = sqrt(sum_prd);

	res["RMSE"] = sum_prd;

	return res;
}

map<string, float> calc_acc(Lazy_Iterator *iterator, int thread_num, Measurement_Params *params) {
	map<string, float> res;

	float pred_val, label, weight;
	double total_cnt = 0, sum_prd = 0;
	while (iterator->fetch_next_external(thread_num, label, pred_val, weight)) {
		total_cnt += weight != -1 ? weight : 1;
		sum_prd += (pred_val == label) * (weight != -1 ? weight : 1);
		//sum_lbls += label;
	}
	total_cnt += weight != -1 ? weight : 1;
	sum_prd += (pred_val == label) * (weight != -1 ? weight : 1);
	sum_prd /= total_cnt;

	res["ACCURACY"] = sum_prd;
	return res;
}

MeasurementFunctions get_loss_function_bootstrap(loss_metric metric) {
	MeasurementFunctions fun;
	switch (metric)
	{
	case auc:
		fun = calc_roc_measures_with_inc;
		break;
	case kendall_tau:
		fun = calc_kandel_tau;
		break;
	case accurarcy:
		fun = calc_acc;
		break;
	case RMSE:
		fun = calc_rmse;
		break;
	default:
		MTHROW_AND_ERR("get_loss_function_bootstrap - Not implemented metric %d\n", metric);
	}

	return fun;
}

void complete_control_active_periods(MedRegistry &reg, const string &complete_reg,
	const string &complete_reg_sig, const string &complete_reg_type, const string &complete_reg_args
	, MedPidRepository &rep, const string &rep_path) {
	if (complete_reg.empty() && complete_reg_sig.empty() && (complete_reg_type.empty() || complete_reg_args.empty()))
		return;
	MedRegistry active_reg;
	vector<int> all_pids;
	if (!complete_reg.empty()) {
		MLOG("Complete Active periods using %s\n", complete_reg.c_str());
		active_reg.read_text_file(complete_reg);
	}
	else if (!complete_reg_sig.empty()) {
		MLOG("Complete Active periods using Signal %s\n", complete_reg_sig.c_str());

		vector<string> sigs_read = { complete_reg_sig };
		if (rep.read_all(rep_path, all_pids, sigs_read) < 0)
			MTHROW_AND_ERR("Error reading repository %s\n", rep_path.c_str());
		int sid = rep.sigs.sid(complete_reg_sig);
		if (rep.sigs.Sid2Info[sid].n_time_channels != 2)
			MTHROW_AND_ERR("Error signal %s should have 2 time channels, has %d\n",
				complete_reg_sig.c_str(), rep.sigs.Sid2Info[sid].n_time_channels);
		for (size_t i = 0; i < rep.pids.size(); ++i)
		{
			MedRegistryRecord rec;
			rec.pid = rep.pids[i];
			rec.registry_value = 1;

			UniversalSigVec usv;
			rep.uget(rec.pid, sid, usv);
			for (size_t k = 0; k < usv.len; ++k)
			{
				rec.start_date = usv.Time((int)k, 0);
				rec.end_date = usv.Time((int)k, 1);
				active_reg.registry_records.push_back(rec);
			}
		}

	}
	else {
		MLOG("Complete Active periods using Registry Type %s\n", complete_reg_type.c_str());
		if (rep.signal_fnames.empty())
			if (rep.init(rep_path) < 0)
				MTHROW_AND_ERR("can't read repository %s\n", rep_path.c_str());
		MedRegistry *active_reg_pt = MedRegistry::make_registry(complete_reg_type, rep, complete_reg_args);

		vector<string> sig_all_codes;
		active_reg_pt->get_registry_creation_codes(sig_all_codes);
		vector<string> read_signals;

		medial::repository::prepare_repository(rep, sig_all_codes, read_signals);
		if (rep.read_all(rep_path, all_pids, read_signals) < 0)
			MTHROW_AND_ERR("can't read repo %s\n", rep_path.c_str());

		active_reg_pt->create_registry(rep);
		active_reg_pt->clear_create_variables();
		active_reg.registry_records = move(active_reg_pt->registry_records);
	}
	medial::registry::complete_active_period_as_controls(reg.registry_records, active_reg.registry_records);
}

//true if higher is better
bool loss_function_order(loss_metric metric) {
	switch (metric)
	{
	case auc:
		return true;
	case kendall_tau:
		return true;
	case accurarcy:
		return false;
	case RMSE:
		return false;
	default:
		MTHROW_AND_ERR("loss_function_order - Not implemented metric %d\n", metric);
	}
}

void complete_control_active_periods(MedRegistry &reg, const string &complete_reg,
	const string &complete_reg_sig, const string &rep_path) {
	if (complete_reg.empty() && complete_reg_sig.empty())
		return;
	MedRegistry active_reg;
	if (!complete_reg.empty()) {
		MLOG("Complete Active periods using %s\n", complete_reg.c_str());
		active_reg.read_text_file(complete_reg);
	}
	else {
		MLOG("Complete Active periods using Signal %s\n", complete_reg_sig.c_str());
		MedRepository rep;
		vector<int> all_pids;
		vector<string> sigs_read = { complete_reg_sig };
		if (rep.read_all(rep_path, all_pids, sigs_read) < 0)
			MTHROW_AND_ERR("Error reading repository %s\n", rep_path.c_str());
		int sid = rep.sigs.sid(complete_reg_sig);
		if (rep.sigs.Sid2Info[sid].n_time_channels != 2)
			MTHROW_AND_ERR("Error signal %s should have 2 time channels, has %d\n",
				complete_reg_sig.c_str(), rep.sigs.Sid2Info[sid].n_time_channels);
		for (size_t i = 0; i < rep.pids.size(); ++i)
		{
			MedRegistryRecord rec;
			rec.pid = rep.pids[i];
			rec.registry_value = 1;

			UniversalSigVec usv;
			rep.uget(rec.pid, sid, usv);
			for (int k = 0; k < usv.len; ++k)
			{
				rec.start_date = usv.Time(k, 0);
				rec.end_date = usv.Time(k, 1);
				active_reg.registry_records.push_back(rec);
			}
		}

	}
	medial::registry::complete_active_period_as_controls(reg.registry_records, active_reg.registry_records);
}

void read_active_periods(string &complete_reg, const string &complete_reg_sig, const string &complete_reg_type,
	const string &complete_reg_args, const string &rep_path, MedPidRepository &rep,
	medial::repository::fix_method registry_fix_method, const string &save_censor_path,
	MedRegistry *&active_reg) {
	//three options:
	//1. from file complete_reg
	//2. from signal complete_reg_sig
	//3. from init line: complete_reg_type, complete_reg_args => stores to save_censor_path

	if (!complete_reg.empty()) {
		MLOG("Complete Active periods using %s\n", complete_reg.c_str());
		active_reg = MedRegistry::make_registry("keep_alive");
		active_reg->read_text_file(complete_reg);
		active_reg->clear_create_variables();
	}
	else {
		if (!complete_reg_sig.empty()) {
			active_reg = MedRegistry::make_registry("keep_alive");
			read_from_rep(complete_reg_sig, rep_path, *active_reg);
			active_reg->clear_create_variables();
		}
		else {
			//try with init arg
			if (!complete_reg_args.empty() && !complete_reg_type.empty()) {
				vector<int> pids = {};
				MLOG("Loading censor registry\n");
				if (rep.signal_fnames.empty())
					if (rep.init(rep_path) < 0)
						MTHROW_AND_ERR("can't read repository %s\n", rep_path.c_str());
				MedModel empty_model;
				active_reg = MedRegistry::make_registry(complete_reg_type, rep, complete_reg_args);

				vector<string> sig_all_codes;
				active_reg->get_registry_creation_codes(sig_all_codes);
				vector<string> read_signals;


				medial::repository::prepare_repository(rep, sig_all_codes, read_signals);
				if (rep.read_all(rep_path, pids, read_signals) < 0)
					MTHROW_AND_ERR("can't read repo %s\n", rep_path.c_str());

				active_reg->create_registry(rep, registry_fix_method);
				active_reg->clear_create_variables();

				active_reg->write_text_file(save_censor_path);
				complete_reg = save_censor_path; //use create censor reg
			}
		}
	}
}