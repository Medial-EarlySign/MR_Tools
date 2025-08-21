#include <string>
#include <vector>
#include <map>
#include <unordered_map>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <boost/algorithm/string.hpp>
#include "Logger/Logger/Logger.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedProcessTools/MedProcessTools/MedFeatures.h"
#include "MedStat/MedStat/MedBootstrap.h"
#include "Cmd_Args.h"
#include "Helper.h"
#include <fenv.h>
#ifndef  __unix__
#pragma float_control( except, on )
#endif

using namespace std;

void load_selected_model(MedPredictor *&model, const programArgs &args, MedFeatures &data,
	const string &results_folder_name, const string &config_folder_name, loss_metric metric) {
	if (file_exists(args.output_folder + path_sep() + config_folder_name + path_sep() + "selected_model.params")) {
		string predictor_name, predictor_params;
		read_selected_model(args.output_folder + path_sep() + config_folder_name +
			path_sep() + "selected_model.params", predictor_name, predictor_params);
		model = MedPredictor::make_predictor(predictor_name, predictor_params);
	}
	else {
		vector<MedPredictor *> all_configs;
		read_ms_config(args.ms_configs_file, args.ms_predictor_name, all_configs);

		bool use_copy = false;
		MedFeatures copy;
		if (data.samples.size() > args.ms_max_count) {
			use_copy = true;
			double down_fact = double(args.ms_max_count) / double(data.samples.size());
			MLOG("Down sampling by %2.2f\n", down_fact);
			copy = data;
			medial::process::down_sample(data, down_fact);
		}
		vector<int> selectedI;
		unordered_map<string, float> model_loss, model_loss_train;
		string bestConfig = runOptimizerModel(data, args.sample_per_pid,
			args.price_ratio, selectedI, all_configs, model_loss, model_loss_train
			, args.ms_nfolds, metric);
		write_model_selection(model_loss, model_loss_train,
			args.output_folder + path_sep() + results_folder_name + path_sep() + "model_selection.log");
		//for (size_t i = 0; i < all_configs.size(); ++i)
		//	delete (MedXGB *)all_configs[i];
		if (use_copy) {
			data.samples.swap(copy.samples);
			data.data.swap(copy.data);
			data.weights.swap(copy.weights);
			data.pid_pos_len.swap(copy.pid_pos_len);
			data.attributes.swap(copy.attributes);
			data.tags.swap(copy.tags);
			data.time_unit = copy.time_unit;
		}

		float best_loss_test = model_loss.at(bestConfig);
		float best_loss_train = model_loss_train.at(bestConfig);
		if (bestConfig.find(":") != string::npos)
			bestConfig = bestConfig.substr(bestConfig.find(":") + 1);
		//write selection to file
		ofstream fw(args.output_folder + path_sep() + config_folder_name + path_sep()
			+ "selected_model.params");
		if (!fw.good())
			MTHROW_AND_ERR("IOError: can't write selected model\n");
		fw << "predictor_name" << "\t" << args.ms_predictor_name << endl;
		fw << "predictor_params" << "\t" << bestConfig << endl;
		fw.close();
		MLOG("Found best model for \"%s\" with loss_val=%2.4f, loss_val_train=%2.4f with those params:\n%s\n",
			args.ms_predictor_name.c_str(), best_loss_test, best_loss_train, bestConfig.c_str());

		model = MedPredictor::make_predictor(args.ms_predictor_name, bestConfig);
	}
}

void prepare_registry(MedPidRepository &rep, const programArgs &args, int start_year, int end_year,
	MedRegistry *&registry, const string &conflict_method, const string &results_folder_name,
	MedRegistry *&censor_registry) {

	registry = MedRegistry::make_registry(args.registry_type);
	censor_registry = NULL;

	vector<string> sigs;
	vector<int> pids = {};

	//create/read censor if needed
	string censor_path_file = args.registry_active_periods;
	read_active_periods(censor_path_file, args.registry_active_periods_sig,
		args.censor_registry_type, args.censor_registry_init, args.rep, rep, args.registry_fix_method,
		args.registry_path + ".censoring", censor_registry);

	registry->registry_records.clear();
	if (!file_exists(args.registry_path))
	{
		if (rep.signal_fnames.empty())
			if (rep.init(args.rep) < 0)
				MTHROW_AND_ERR("ERROR in prepare_registry - can't read repository %s\n",
					args.rep.c_str());
		MedModel model_rep_processors;
		if (!args.registry_rep_processors.empty()) {
			model_rep_processors.init_from_json_file(args.registry_rep_processors);
			model_rep_processors.collect_and_add_virtual_signals(rep);
			registry->set_rep_for_init(rep);
		}

		registry->init_from_string(args.registry_init_cfg);

		vector<string> sig_all_codes;
		registry->get_registry_creation_codes(sig_all_codes);
		vector<string> read_signals;

		medial::repository::prepare_repository(rep, sig_all_codes, read_signals, &model_rep_processors.rep_processors);
		if (rep.read_all(args.rep, pids, read_signals) < 0)
			MTHROW_AND_ERR("can't read repo %s\n", args.rep.c_str());

		registry->create_registry(rep, args.registry_fix_method, &model_rep_processors.rep_processors);
		registry->clear_create_variables();

		//complete controls in registry if needed:
		if (args.use_active_for_reg_outcome)
			complete_control_active_periods(*registry, censor_path_file, args.registry_active_periods_sig, args.rep);

		ofstream fo(args.output_folder + path_sep() + "registry_creation.log", ios::trunc);
		fo.close(); //override file
		medial::print::print_reg_stats(registry->registry_records, args.output_folder + path_sep() + "registry_creation.log");
		registry->write_text_file(args.registry_path);
	}
	else
		registry->read_text_file(args.registry_path);

	MLOG("Done Processing Registry with %d records\n", (int)registry->registry_records.size());
	//use censoring to censor train - not validation:

	if (args.metric == "auc") { //force registry to be binary [0, 1]:
		bool warn_shown = false;
		for (size_t i = 0; i < registry->registry_records.size(); ++i)
		{
			if (registry->registry_records[i].registry_value != 0 && registry->registry_records[i].registry_value != 1) {
				if (!warn_shown) {
					char buffer[1000];
					snprintf(buffer, sizeof(buffer), "Warning metric=%s and registry is not binary, has record with value=%2.3f. fixing registry...\n",
						args.metric.c_str(), registry->registry_records[i].registry_value);
					string msg_text = string(buffer);
					MWARN("%s", msg_text.c_str());
					global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "%s", msg_text.c_str());
				}
				warn_shown = true;
				registry->registry_records[i].registry_value = float(int(registry->registry_records[i].registry_value > 0));
			}
		}
		medial::print::print_reg_stats(registry->registry_records);
	}
}

int main(int argc, char *argv[]) {
#if defined(__unix__)
	feenableexcept(FE_DIVBYZERO | FE_INVALID | FE_OVERFLOW);
#endif
	programArgs args;
	int exit_code = args.parse_parameters(argc, argv);
	global_logger.fds[LOG_MED_UTILS].resize(1); //remove debug output for MedLogger dctor won't close twice
	if (exit_code == -1) //help
		return 0;
	if (exit_code < 0)
		MTHROW_AND_ERR("unable to parse arguments\n");
	log_section_to_name[LOG_APP] = "MODEL_RUNNER";
	if (args.debug)
		global_logger.levels[LOG_MED_MODEL] = LOG_DEF_LEVEL;
	loss_metric metric = get_loss_metric(args.metric);
	string results_folder_name = "results";
	string config_folder_name = args.config_folder_name;
	string bootstrap_folder_name = args.bootstrap_folder_name;
	boost::filesystem::create_directories(args.output_folder + path_sep() + results_folder_name);
	boost::filesystem::create_directories(args.output_folder + path_sep() + config_folder_name);
	boost::filesystem::create_directories(args.output_folder + path_sep() + bootstrap_folder_name);

	if (args.skip_to_compare) {
		if (args.load_test_samples.empty() || args.load_train_samples.empty())
			MTHROW_AND_ERR("Error - in skip_to_compare must provide load_test_samples,load_train_samples\n");
	}

	unordered_set<string> selected_sigs, final_list;
	string forward_mat_path = args.output_folder + path_sep() + config_folder_name + path_sep()
		+ args.registry_name + "_forward_train_matrix.bin";
	string full_mat_path = args.output_folder + path_sep() + config_folder_name + path_sep()
		+ args.registry_name + "_full_train_matrix.bin";
	string med_model_path = args.output_folder + path_sep() + config_folder_name + path_sep()
		+ "full_model.medmdl";
	string export_full_model_path = args.output_folder + path_sep() + config_folder_name + path_sep()
		+ "exported_full_model.medmdl";

	//timeunit
	MedPidRepository rep;
	medial::repository::set_global_time_unit(args.rep);

	MedRegistry *regRecords, *censorReg;
	MedSamples samples, validation_samples;
	MedFeatures data, validation_data;

	vector<MedRegistryRecord> only_train, only_test;
	MedLabels train_labeling(args.labeling_params), test_labeling(args.labeling_params);
	if (args.load_test_samples.empty() || args.load_train_samples.empty() || !args.fg_signals.empty()) {
		prepare_registry(rep, args, 2003, 2011, regRecords, "all", results_folder_name, censorReg);
		vector<MedRegistryRecord> *censor_records = censorReg == NULL ? NULL : &censorReg->registry_records;

		split_registry_train_test(args.rep, *regRecords, only_train, only_test, rep);

		train_labeling.prepare_from_registry(only_train, censor_records);
		test_labeling.prepare_from_registry(only_test, censor_records);
	}

	MedPredictor *model;
	MedModel skip_to_model;
	bool model_in_full_m = false;
	if (!args.skip_to_compare) {
		bool predictor_learned = file_exists(args.output_folder + path_sep() + config_folder_name + path_sep()
			+ "best_model.mdl");
		double did_change = 0;
		if (!predictor_learned || !file_exists(med_model_path)) {
			if (!file_exists(forward_mat_path)
				|| !file_exists(med_model_path)) {
				if (!file_exists(full_mat_path)
					|| !file_exists(med_model_path)) {
					//Find RC, Drug relevant to use:
					string base_stats_path = args.dictonary_folder_name + path_sep();
					if (args.dictonary_folder_name[0] != path_sep() &&
						!(args.dictonary_folder_name.size() >= 2 && args.dictonary_folder_name[1] == ':')) {//relative
						base_stats_path = args.output_folder + path_sep() + args.dictonary_folder_name + path_sep();
						MLOG_D("Using relative path %s for searching dicts\n", base_stats_path.c_str());
					}
					boost::filesystem::create_directories(base_stats_path.data());
					char str_buff[500];
					snprintf(str_buff, sizeof(str_buff),
						"start_age=%d;end_age=%d;age_bin=%d"
						"", args.min_age, args.max_age, args.fg_sampler_age_bin);
					string init_sampler = string(str_buff);

					int save_from = train_labeling.labeling_params.time_from;
					int save_to = train_labeling.labeling_params.time_to;
					train_labeling.labeling_params.time_from = args.fg_win_from_test;
					train_labeling.labeling_params.time_to = args.fg_win_to_test;
					int signal_idx = 0;
					for (const string &signal_fg : args.fg_signals)
					{
						string full_pt = base_stats_path + args.registry_name + "_stats_" + signal_fg + ".dict";
						get_signal_stats(full_pt, signal_fg, train_labeling, "age", init_sampler, args.fg_sampler_age_labeling, rep, args.rep,
							args.output_folder + path_sep() + results_folder_name + path_sep()
							+ args.registry_name + "_" + signal_fg + ".options", args.fg_take_top, args.fg_filters, signal_idx);

						if (!file_exists(args.output_folder + path_sep() + config_folder_name + path_sep()
							+ args.registry_name + "_" + signal_fg + ".choosed"))
							copy_file(args.output_folder + path_sep() + results_folder_name + path_sep()
								+ args.registry_name + "_" + signal_fg + ".options",
								args.output_folder + path_sep() + config_folder_name + path_sep()
								+ args.registry_name + "_" + signal_fg + ".choosed");

						++signal_idx;
					}
					train_labeling.labeling_params.time_from = save_from;
					train_labeling.labeling_params.time_to = save_to;

					MedSamplingStrategy *sampler = MedSamplingStrategy::make_sampler(args.sampler_train_name,
						args.sampler_train_params);
					sampler->filtering_params = args.train_filtering_params;
					MLOG("Sampling for train samples...\n");
					vector<int> empty_pids;
					vector<string> bdate_sigs = { "BDATE" };
					int bdate_cd = rep.sigs.sid(bdate_sigs.front());
					if (bdate_cd < 0 || !rep.index.index_table[bdate_cd].is_loaded)
						if (rep.read_all(args.rep, empty_pids, bdate_sigs) < 0)
							MTHROW_AND_ERR("Error can't read rep %s\n", args.rep.c_str());
					sampler->init_sampler(rep);
					rep.clear();
					if (args.load_train_samples.empty())
						train_labeling.create_samples(sampler, samples);
					else
						samples.read_from_file(args.load_train_samples);
					medial::print::print_samples_stats(samples);

					if (!args.filter_feat_name.empty() && !args.json_mat_filter.empty()) {
						MedFeatures filter_mat;
						did_change = load_matrix_from_json(samples, args.rep, args.json_mat_filter, filter_mat, args.change_prior);
						vector<string> filter_feature_names;
						filter_mat.get_feature_names(filter_feature_names);
						int pos_name = find_in_feature_names(filter_feature_names, args.filter_feat_name);
						const string &full_filt_name = filter_feature_names[pos_name];
						vector<int> after_filt_idxs;
						int before_size = (int)filter_mat.samples.size();
						for (size_t i = 0; i < filter_mat.samples.size(); ++i)
							if (filter_mat.data[full_filt_name][i] >= args.filter_low &&
								filter_mat.data[full_filt_name][i] <= args.filter_high)
								after_filt_idxs.push_back((int)i);

						medial::process::filter_row_indexes(filter_mat, after_filt_idxs);
						MLOG("Filter condition on %s[%2.4f , %2.4f], before was %d after filtering %zu\n",
							full_filt_name.c_str(), args.filter_low, args.filter_high, before_size, filter_mat.samples.size());
						samples.idSamples.clear();
						filter_mat.get_samples(samples);
						medial::print::print_samples_stats(samples);
					}

					if (did_change <= 0 && args.change_prior > 0) {
						vector<int> sel_idx;
						medial::process::match_to_prior(samples, args.change_prior, sel_idx);
					}
					if (args.debug)
						samples.write_to_file(args.output_folder + path_sep() + results_folder_name + path_sep() +
							"train.samples");
					delete sampler;

					MedModel mod;
					MedPidRepository dataManager;
					mod.init_from_json_file(args.json_model);
					//adding optional signals RC and drugs to model.
					for (const string &addition_sig : args.fg_signals)
						load_additional_featuress(mod, addition_sig, args.output_folder + path_sep() +
							config_folder_name + path_sep() + args.registry_name + "_" + addition_sig + ".choosed", args.fg_win_from, args.fg_win_to);

					prepare_model_from_json(samples, args.rep, mod, dataManager, args.change_prior);

					mod.learn(dataManager, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
					data = move(mod.features);
					data.write_to_file(full_mat_path);
					mod.write_to_file(med_model_path);
					mod.LearningSet = NULL; //do not clear learning set!
				}
				else
					data.read_from_file(full_mat_path);

				data.init_pid_pos_len();
				assign_weights(args.rep, data, args.weights_args, true, args.change_prior); //will assign weights if needed
				if (file_exists(args.output_folder + path_sep() + config_folder_name + path_sep() + "selected_signals.list")) {
					MLOG("Loading forward features selection from disk\n");
					read_string_file(args.output_folder + path_sep() + config_folder_name + path_sep()
						+ "selected_signals.list", selected_sigs);
					MLOG("Loaded %d features. need to keep %d signals\n",
						(int)data.data.size(), (int)selected_sigs.size());
				}
				else {
					MLOG("Has %d features with %d samples\n",
						(int)data.data.size(), (int)data.samples.size());
					vector<string> signalNames;
					data.get_feature_names(signalNames);
					//print simple univariate first:
					if (!args.fs_uni_bin_init.empty()) {
						BinSettings bin_sets;
						bin_sets.init_from_string(args.fs_uni_bin_init);
						simple_uni_feature_sel(data, signalNames,
							args.output_folder + path_sep() + results_folder_name + path_sep()
							+ "feature_importance.log", bin_sets, metric);
					}
					vector<pair<float, string>> all_scores;
					if (args.fs_loop_count > 0) {
						MedPredictor *model_feat = MedPredictor::make_predictor(args.fs_predictor_name,
							args.fs_predictor_params);
						float refScore;

						unordered_set<string> base_signals;
						if (!args.fs_base_signal.empty())
							read_string_file(args.fs_base_signal, base_signals);
						vector<string> base_signals_list(base_signals.begin(), base_signals.end());
						MLOG("Has %d base signals\n", (int)base_signals_list.size());
						MedFeatures copy = data;
						filter_matrix_ages_years(data, args.min_age, args.max_age, args.min_year, args.max_year);
						MLOG("After Age filter left with %d samples\n", (int)data.samples.size());
						if (data.samples.size() > args.fs_f_max_count) {
							double down_fact = double(args.fs_f_max_count) / double(data.samples.size());
							MLOG("Down sampling by %2.2f\n", down_fact);
							medial::process::down_sample(data, down_fact);
						}

						all_scores = runFeatureSelectionModel(model_feat, data,
							signalNames, refScore, base_signals_list, args.fs_deep_size, args.fs_loop_count, metric);
						data.samples.swap(copy.samples);
						data.data.swap(copy.data);
						data.weights.swap(copy.weights);
						data.pid_pos_len.swap(copy.pid_pos_len);
						data.attributes.swap(copy.attributes);
						data.tags.swap(copy.tags);
						data.time_unit = copy.time_unit;
						for (const string &s : base_signals_list) //add base signals
							selected_sigs.insert(s);

						delete model_feat;
						update_selected_sigs(selected_sigs, all_scores, refScore, args.fs_take_top,
							args.output_folder + path_sep() + config_folder_name,
							args.output_folder + path_sep() + results_folder_name, metric, args.fs_sort_by_count);
					}
					else {
						//select all
						MLOG("Skip forward selection - keep all\n");
						for (const string &s : signalNames) //add base signals
							selected_sigs.insert(s);
						write_string_file(selected_sigs, args.output_folder + path_sep() + config_folder_name + path_sep() + "selected_signals.list");
					}
				}
				commit_selection(data, selected_sigs);
				data.write_to_file(forward_mat_path);
			}
			else {
				data.read_from_file(forward_mat_path);
				MLOG("loaded from forward_feature_matrix with %d samples and %d features\n",
					(int)data.samples.size(), (int)data.data.size());

				string search_file = args.output_folder + path_sep() + config_folder_name + path_sep()
					+ "continue_signals.list";
				if (file_exists(search_file)) {
					unordered_set<string> temp_list;
					read_string_file(search_file, temp_list);
					int sz_bef = (int)data.data.size();
					commit_selection(data, temp_list);
					MLOG("Before has %d features, now has %zu features\n", sz_bef, data.data.size());
				}
			}
			data.init_pid_pos_len();
			if (args.weights_args.active && data.weights.empty()) {
				MWARN("Warning: learned prepartion matrix without weights. now assigning weights\n");
				assign_weights(args.rep, data, args.weights_args, true, args.change_prior);
			}
			//MedFeatures copy = data; //no need to keep old copy
			filter_matrix_ages_years(data, args.min_age, args.max_age, args.min_year, args.max_year);
			MLOG("After Age filter left with %d samples\n", (int)data.samples.size());
			vector<string> data_sig_names;
			data.get_feature_names(data_sig_names);
			if (!args.fs_skip_backward) {
				void *model_back = MedPredictor::make_predictor(args.fs_predictor_name,
					args.fs_predictor_params);
				backward_selection(args.output_folder + path_sep() + config_folder_name,
					args.output_folder + path_sep() + results_folder_name + path_sep() + "backward_selection.log",
					data, args.price_ratio, args.fs_nfolds, args.fs_max_change, args.fs_min_remove, args.fs_max_count,
					data_sig_names, final_list, model_back, metric, did_change >= 0 ? args.change_prior : 0);
				delete (MedPredictor *)model_back;
			}
			else
				read_string_file(args.output_folder + path_sep() + config_folder_name + path_sep()
					+ "selected_signals.list", final_list);
			commit_selection(data, final_list);
			data_sig_names.clear();
			data.get_feature_names(data_sig_names);

			if (args.sample_conflict_pids)
				filter_conflicts(data);
		}
		else {
			//load select list if has:
			if (file_exists(args.output_folder + path_sep() + config_folder_name + path_sep()
				+ "final_selection.list")) {
				read_string_file(args.output_folder + path_sep() + config_folder_name + path_sep()
					+ "final_selection.list", final_list);
				MLOG("Read %zu selected singals from final_selection.list\n", final_list.size());
			}
			else if (file_exists(args.output_folder + path_sep() + config_folder_name + path_sep()
				+ "selected_signals.list")) {
				read_string_file(args.output_folder + path_sep() + config_folder_name + path_sep()
					+ "selected_signals.list", final_list);
				MLOG("Read %zu selected singals from selected_signals.list\n", final_list.size());
			}
		}
		//model selection
		load_selected_model(model, args, data, results_folder_name, config_folder_name, metric); //only the params for the best

		MedModel full_m;

		if (!file_exists(args.output_folder + path_sep() + config_folder_name + path_sep()
			+ "best_model.mdl")) {
			MLOG("Training Model...\n");
			if (!args.weights_args.active && !data.weights.empty()) {
				MLOG("Request to remove weights for training. removing them\n");
				global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Request to remove weights for training. removing them\n");
				data.weights.clear();
			}
			global_logger.init_all_levels(MIN_LOG_LEVEL);
			map<string, FilterCohortFunc> cohort_default_functions = { { "All", [](const map<string, vector<float>> &records, int i, void *p) { return true; } } };
			vector<MeasurementFunctions> measurement_default_functions = { get_loss_function_bootstrap(metric) };
			vector<int> default_empty_arr;

			map<string, map<string, float>> res = runExperiment(data,
				args.output_folder + path_sep() + bootstrap_folder_name + path_sep() + "cv.pivot.csv", NULL, NULL,
				args.sample_per_pid, model, default_empty_arr, args.price_ratio, args.kfold
				, cohort_default_functions, measurement_default_functions,
				false, false, metric);
			global_logger.init_all_levels(LOG_DEF_LEVEL);
			((MedPredictor *)model)->write_to_file(args.output_folder + path_sep() + config_folder_name
				+ path_sep() + "best_model.mdl");
			map<string, float> m = res["All"];
			string measure_name = get_loss_metric_name(metric);
			MLOG("%s_Mean=%f, %s_Obs=%f\n", measure_name.c_str(), m[measure_name + "_Mean"], measure_name.c_str(), m[measure_name + "_Obs"]);
			global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL,
				"%s_Mean=%f, %s_Obs=%f\n", measure_name.c_str(), m[measure_name + "_Mean"], measure_name.c_str(), m[measure_name + "_Obs"]);
			//Save in full export model:

			full_m.read_from_file(med_model_path);
			shrink_med_model(full_m, final_list);
			if (full_m.LearningSet != NULL) {//when reading model from disk need to clean LearningSet before exit - valgrind
				delete static_cast<MedSamples *>(full_m.LearningSet);
				full_m.LearningSet = NULL;
				full_m.serialize_learning_set = false;
			}
			//Add Filter for final features:
			//string all_features_ls = medial::io::get_list(final_list);
			FeatureProcessor *filter_p = FeatureProcessor::make_processor("tags_selector", "verbose=0");
			vector<string> resolved_names; resolved_names.reserve(final_list.size());
			vector<string> full_names; full_m.get_all_features_names(full_names, (int)full_m.feature_processors.size());
			for (auto it = final_list.begin(); it != final_list.end(); ++it) {
				string strip_name = *it;
				if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
					strip_name = strip_name.substr(strip_name.find(".") + 1);
				resolved_names.push_back(full_names[find_in_feature_names(full_names, *it)]);
			}
			((TagFeatureSelector *)filter_p)->selected_tags.insert(((TagFeatureSelector *)filter_p)->selected_tags.end(), resolved_names.begin(), resolved_names.end());
			((FeatureSelector *)filter_p)->selected.insert(((FeatureSelector *)filter_p)->selected.end(), resolved_names.begin(), resolved_names.end());
			full_m.add_feature_processor(filter_p);
			delete full_m.predictor;
			full_m.predictor = model;
			model_in_full_m = true;
			full_m.write_to_file(export_full_model_path);
		}
		else {
			((MedPredictor *)model)->read_from_file(args.output_folder + path_sep() + config_folder_name
				+ path_sep() + "best_model.mdl");
			MLOG("Loaded trained model of %s...\n",
				predictor_type_to_name[((MedPredictor *)model)->classifier_type].c_str());
		}
	}
	else {
		skip_to_model.read_from_file(export_full_model_path);
		model = skip_to_model.predictor;
		model_in_full_m = true;
		med_model_path = export_full_model_path;
	}

	if (args.load_test_samples.empty()) {
		MedSamplingStrategy *sampler_years = MedSamplingStrategy::make_sampler(args.sampler_validation_name,
			args.sampler_validation_params);
		sampler_years->filtering_params = args.test_filtering_params;
		vector<int> empty_pids;
		vector<string> bdate_sigs = { "BDATE" };
		int bdate_cd = rep.sigs.sid(bdate_sigs.front());
		if (bdate_cd < 0 || !rep.index.index_table[bdate_cd].is_loaded)
			if (rep.read_all(args.rep, empty_pids, bdate_sigs) < 0)
				MTHROW_AND_ERR("Error can't read rep %s\n", args.rep.c_str());
		sampler_years->init_sampler(rep);
		test_labeling.create_samples(sampler_years, validation_samples);
		delete sampler_years;
	}
	else
		validation_samples.read_from_file(args.load_test_samples);
	//sampler_years->do_sample(only_test, validation_samples); //no censoring on validation

	if (global_default_time_unit == MedTime::Date)
		medial::print::print_by_year(validation_samples, 1, false, true, args.output_folder + path_sep() + bootstrap_folder_name + path_sep()
			+ "validation_hist.txt");
	else
		medial::print::print_samples_stats(validation_samples);
	validation_samples.write_to_file(args.output_folder + path_sep() +
		bootstrap_folder_name + path_sep() + "validation.samples");

	MLOG("Loading Validation\n");
	unordered_map<string, vector<float>> additional_bootstrap;
	args.change_prior = 0;
	load_test_matrix(validation_samples, validation_data, additional_bootstrap,
		med_model_path, final_list, args.rep, args.change_prior);
	MLOG("Loaded %zu with %zu features\n", validation_data.samples.size(), validation_data.data.size());
	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Loaded %zu with %zu features\n",
		validation_data.samples.size(), validation_data.data.size());
	fix_samples(validation_samples, validation_data);

	//run model on validation:
	((MedPredictor *)model)->predict(validation_data);
	vector<float> assigned_probs, model_preds, original_labels;

	vector<float> bootstrap_weights;
	if (args.bootstrap_weights.active) {
		vector<int> sel_idx;
		//load probs to validation_data - update bootstrap_weights and weights in validation_data
		get_probs_weights(validation_samples, args.rep, args.bootstrap_weights, bootstrap_weights, sel_idx, args.change_prior);
		medial::process::filter_row_indexes(validation_data, sel_idx);
		//update also validation_data
		validation_data.weights = bootstrap_weights;
		if (validation_data.samples.size() != validation_data.weights.size())
			MTHROW_AND_ERR("Error in bootstrap_weights - validation_data.samples.size()=%zu, validation_data.weights.size()=%zu\n"
				, validation_data.samples.size(), validation_data.weights.size());
		//filter zero weights in validation_samples, validation_data:

		sel_idx.clear();
		for (int i = 0; i < bootstrap_weights.size(); ++i) //filter zero weights
			if (bootstrap_weights[i] > 0)
				sel_idx.push_back(i);
		medial::process::filter_row_indexes(validation_data, sel_idx);
		//validate weights:
		for (size_t i = 0; i < validation_data.samples.size(); ++i)
			if (validation_data.weights[i] <= 0)
				MTHROW_AND_ERR("Error in bootstrap weights: got weights = %f in %zu\n", validation_data.weights[i], i);

		validation_samples.clear();
		validation_data.get_samples(validation_samples);
		if (validation_data.samples.size() < bootstrap_weights.size()) {
			char buff_str[5000];
			snprintf(buff_str, sizeof(buff_str), "Warning: got weights in bootstrap that are zero - removing them. "
				"origianl_size was %zu, new_size is %zu(%2.1f%%)\n",
				bootstrap_weights.size(), validation_data.samples.size(),
				100.0*validation_data.samples.size() / bootstrap_weights.size());
			MWARN("%s", buff_str);
			global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "%s", buff_str);
			if (bootstrap_weights.size() > 1000 && validation_data.samples.size() < 100)
				MTHROW_AND_ERR("Error: final validaiton size is %zu which is too small - check bootstrap weights\n",
					validation_data.samples.size());
			bootstrap_weights = validation_data.weights;
		}
	}

	//add aditional signals to validation for filtering if needed:
	if (!args.bootstrap_json_model.empty()) {
		MedFeatures additional;
		load_matrix_from_json(validation_samples, args.rep, args.bootstrap_json_model, additional, args.change_prior);
		if (additional.samples.size() != validation_data.samples.size())
			MTHROW_AND_ERR("Error in bootstrap_json_model - can't generate additional features. orig_size=%zu, additional_size=%zu\n",
				validation_data.samples.size(), additional.samples.size());
		//join feature to additional_bootstrap:
		vector<string> validation_names;
		validation_data.get_feature_names(validation_names);
		for (auto it = additional.data.begin(); it != additional.data.end(); ++it)
		{
			string clean_name = it->first;
			clean_ftr_name(clean_name);
			if (clean_name == "Age" || clean_name == "Gender") {
				additional_bootstrap[clean_name].swap(it->second); //to protect normalizations - save value
				continue;
			}
			if (find_in_feature_names(validation_names, clean_name, false) >= 0) {
				MWARN("Warning : bootstrap additional feature %s also exists in original matrix\n",
					clean_name.c_str());
				//continue;
			}
			additional_bootstrap[clean_name].swap(it->second);
		}
	}

	with_registry_args reg_args;
	with_registry_args *p_reg_args = NULL;
	reg_args.do_kaplan_meir = true;
	reg_args.rep_path = args.rep;
	reg_args.registry = regRecords;
	reg_args.registry_censor = censorReg;
	reg_args.json_model = args.bootstrap_json_model;
	reg_args.labeling_params = args.labeling_params;
	MedSamplingYearly sampler_reg_bootstrap;
	if (!args.bootstrap_sampler_args.empty())
		sampler_reg_bootstrap.init_from_string(args.bootstrap_sampler_args);
	reg_args.sampler = &sampler_reg_bootstrap;
	if (!args.bootstrap_sampler_args.empty())
		p_reg_args = &reg_args;
	else {
		MWARN("Running Bootstrap Analysis without registry parameter for incidence. "
			"to use registry, please specify bootstrap_sampler_args\n");
		global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Running Bootstrap Analysis without registry parameter for incidence. "
			"to use registry, please specify bootstrap_sampler_args\n");
	}
	vector<float> labels;
	if (!args.compare_models_file.empty()) {
		original_labels.resize(validation_data.samples.size());
		for (size_t i = 0; i < validation_data.samples.size(); ++i)
			original_labels[i] = validation_data.samples[i].outcome;
	}
	run_bootstrap(args.rep, validation_data, additional_bootstrap, args.bootstrap_params,
		args.cohort_file, args.bootstrap_outcome_correction, args.output_folder + path_sep() + bootstrap_folder_name,
		"model", model_preds, &assigned_probs, metric, p_reg_args);
	if (!args.compare_models_file.empty() && args.bootstrap_outcome_correction.active && args.bootstrap_outcome_correction.method == weighting_method::outcome_event) {
		labels.resize(validation_data.samples.size());
		string full_search_name = "";
		if (!args.bootstrap_outcome_correction.norm_weight_condition.empty() && !args.bootstrap_outcome_correction.norm_all)
		{
			vector<string> all_names;
			validation_data.get_feature_names(all_names);
			int pos_f = find_in_feature_names(all_names, args.bootstrap_outcome_correction.norm_weight_condition, false);
			if (pos_f < 0) {
				all_names.clear();
				for (auto it = additional_bootstrap.begin(); it != additional_bootstrap.end(); ++it)
					all_names.push_back(it->first);
				pos_f = find_in_feature_names(all_names, args.bootstrap_outcome_correction.norm_weight_condition, false);
				if (pos_f < 0)
					MTHROW_AND_ERR("Can't find norm_weight_condition %s in matrix and additional bootstrap matrix\n",
						args.bootstrap_outcome_correction.norm_weight_condition.c_str());
			}
			full_search_name = all_names[pos_f];
		}
		if (!args.bootstrap_outcome_correction.norm_weight_condition.empty() || args.bootstrap_outcome_correction.norm_all) {
			if (args.bootstrap_outcome_correction.norm_all || validation_data.data.find(full_search_name) != validation_data.data.end()) {
				for (size_t i = 0; i < labels.size(); ++i)
					if (args.bootstrap_outcome_correction.norm_all || validation_data.data.at(full_search_name)[i] > 0)
						labels[i] = original_labels[i] - assigned_probs[i];
			}
			else
				for (size_t i = 0; i < labels.size(); ++i)
					if (args.bootstrap_outcome_correction.norm_all || additional_bootstrap.at(full_search_name)[i] > 0)
						labels[i] = original_labels[i] - assigned_probs[i];
		}

	}

	//run compare models:
	if (!args.compare_models_file.empty()) {
		unordered_map<string, vector<float>> empty_map_vals;
		MedSamples train_samples;
		if (!data.samples.empty())
			data.get_samples(train_samples);
		else
			train_samples.read_from_file(args.load_train_samples);

		vector<pair<string, compare_model_params>> other_models;
		vector<vector<float>> all_preds = { model_preds };
		vector<string> model_names = { "Medial_Model" };

		read_compare_models(args.compare_models_file, other_models);
		global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "has %d compare models\n", (int)other_models.size());
		for (size_t i = 0; i < other_models.size(); ++i) {
			vector<float> other_preds;
			run_compare_model(other_models[i], train_samples, validation_samples, &bootstrap_weights, additional_bootstrap
				, args.rep, args.bootstrap_params, args.cohort_file, args.bootstrap_outcome_correction,
				args.output_folder + path_sep() + bootstrap_folder_name, other_preds, &assigned_probs, metric,
				args.change_prior, p_reg_args);
			all_preds.push_back(other_preds);
			model_names.push_back(other_models[i].first);
		}
		if (metric == loss_metric::auc) {
			//add additional data into validation_data.data for plot, destroys additional_bootstrap:
			for (auto it = additional_bootstrap.begin(); it != additional_bootstrap.end(); ++it)
				if (validation_data.data.find(it->first) == validation_data.data.end())
					validation_data.data[it->first].swap(it->second);
			//plot AUC graphs for each cohort (need todo for weighted and unweighted):
			plotAUC_graphs(original_labels, validation_data.data, all_preds, &bootstrap_weights, model_names, args.cohort_file,
				args.output_folder + path_sep() + bootstrap_folder_name + path_sep() + "roc_graphs");
			if (args.bootstrap_outcome_correction.active && !labels.empty())
				plotAUC_graphs(labels, validation_data.data, all_preds, &bootstrap_weights, model_names, args.cohort_file,
					args.output_folder + path_sep() + bootstrap_folder_name + path_sep() + "roc_graphs_weighted");
		}
	}
	MLOG("Done and exits successfully!\n");

	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Exits Successfully\n");
	delete regRecords;
	if (!model_in_full_m)
		delete (MedPredictor *)model; //clear for each type
	return 0;
}
