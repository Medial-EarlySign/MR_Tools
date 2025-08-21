#include "Cmd_Args.h"
#include <fenv.h>
#include <boost/filesystem.hpp>
#include "Helper.h"
#include <random>
#include <algorithm>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
#if defined(__unix__)
	feenableexcept(FE_DIVBYZERO | FE_INVALID | FE_OVERFLOW);
#endif

	// Parse the command-line parameters
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return 1;

	boost::filesystem::create_directories(args.result_folder);
	boost::filesystem::create_directories(args.config_folder);
	string full_name = "exported_full_model.medmdl";
	string progress_path = args.result_folder + path_sep() + "optimize.progress.txt";

	unordered_map<string, MedSamples> train_samples, test_samples;
	vector<string> train_path_order, temp_test;
	vector<unordered_set<int>> train_ordered_cases_def, train_ordered_controls_def;
	vector<unordered_set<int>> test_ordered_cases_def, test_ordered_controls_def;

	// Load mapping pid->split 
	unordered_map<int, int> pid_to_split;
	read_splits_file(args.splits_file, pid_to_split);

	// Load train samples [optionally from multiple files]
	if (args.train_test_samples_single) {
		train_path_order.push_back(args.train_samples_files);
		train_ordered_cases_def.push_back(move(unordered_set<int>(args.train_cases_labels.begin(), args.train_cases_labels.end())));
		train_ordered_controls_def.push_back(move(unordered_set<int>(args.train_control_labels.begin(), args.train_control_labels.end())));
	}
	else
		get_train_paths(args.train_samples_files, args.train_cases_labels, args.train_control_labels, train_path_order, train_ordered_cases_def, train_ordered_controls_def);

	read_samples(train_path_order, train_samples, train_ordered_cases_def, train_ordered_controls_def, pid_to_split);

	// Load test samples [optionally from multiple files]
	if (args.train_samples_files == args.test_samples_files || args.test_samples_files.empty())
		//split train samples alone:
		test_samples = train_samples;
	else {
		if (args.train_test_samples_single) {
			temp_test.push_back(args.test_samples_files);
			test_ordered_cases_def.push_back(move(unordered_set<int>(args.test_cases_labels.begin(), args.test_cases_labels.end())));
			test_ordered_controls_def.push_back(move(unordered_set<int>(args.test_control_labels.begin(), args.test_control_labels.end())));
		}
		else
			get_train_paths(args.test_samples_files, args.test_cases_labels, args.test_control_labels, temp_test, test_ordered_cases_def, test_ordered_controls_def);
		read_samples(temp_test, test_samples, test_ordered_cases_def, test_ordered_controls_def, pid_to_split);
	}

	// Load split from file (iif provided) or create new split 
	assign_splits_if_needed(train_samples, test_samples, args.nfolds);

	validate_train_test(train_samples, test_samples);
	split_train_test_till_year(train_samples, test_samples, args.train_till_time);

	// Apply filters if specified
	if (args.has_filters()) {
		MedPidRepository only_byears;
		vector<string> sigs_yearrs = { "BDATE" };
		prepare_rep_for_signals(only_byears, args.rep, sigs_yearrs, train_samples, test_samples);

		for (auto &it : train_samples)
			filter_age_years(it.second, only_byears, args.min_age_filter, args.max_age_filter, args.min_year_filter, args.max_year_filter);
		for (auto &it : test_samples)
			filter_age_years(it.second, only_byears, args.min_age_filter, args.max_age_filter, args.min_year_filter, args.max_year_filter);
	}

	//	Subsample controls to reach specified prior [only when "change_to_prior" is set]
	if (args.change_to_prior > 0) {
		for (auto &it : train_samples) {
			vector<int> sel_idx;
			medial::process::match_to_prior(it.second, args.change_to_prior, sel_idx);
		}
	}

	// Filter TEST set according to bootstrap definition
	if (!args.bt_cohort.empty() && args.bt_cohort != "All") {
		//has filters:
		filter_test_bootstrap_cohort(args.rep, test_samples, args.bt_json, args.bt_cohort);
	}

	// Downsample TRAIN set if requested
	if (args.down_sample_train_count > 0) {
		for (auto &it : train_samples)
			if (it.second.nSamples() > args.down_sample_train_count)
				medial::process::down_sample(it.second, args.down_sample_train_count);
	}

	// Downsample TEST set if requested
	if (args.down_sample_test_count > 0) {
		for (auto &it : test_samples)
			if (it.second.nSamples() > args.down_sample_test_count)
				medial::process::down_sample(it.second, args.down_sample_test_count);
	}

	// Load repository taking into account requirements specified in model configuration
	MedModel feature_model_gen;
	MedPidRepository rep;
	feature_model_gen.init_from_json_file(args.json_model);
	feature_model_gen.verbosity = 0;
	prepare_rep_from_model(feature_model_gen, rep, args.rep, train_samples, test_samples);

	// Enrich repository with signals required for matching
	if (!args.matching_json.empty()) {
		MedModel matching_model;
		matching_model.init_from_json_file(args.matching_json);
		matching_model.verbosity = 0;
		enrich_rep_from_model(matching_model, rep, args.rep);
	}

	// =============================================================

	full_train_args best_train_params, curr_candidate;
	best_train_params.samples_id = "";

	// Calculate the number of "experiments" to be executed in order to select an optimal configuration
	vector<full_train_args> documented_opts;
	int excpeted_exp = 1;
	excpeted_exp *= (int)train_samples.size();
	excpeted_exp *= (int)args.train_weights_method.size();
	vector<MedPredictor *> all_configs_tmp;
	read_ms_config(args.ms_configs_file, args.ms_predictor_name, all_configs_tmp);
	int inner_exp_size = (int)all_configs_tmp.size();
	for (size_t i = 0; i < all_configs_tmp.size(); i++)
	{
		delete all_configs_tmp[i];
		all_configs_tmp[i] = NULL;
	}

	

	vector<full_train_args> merge_with;
	if (!args.combine_with_report.empty())
		read_old_results(args.combine_with_report, train_path_order, merge_with);
	//read only not duplicates
	if (!args.override_all_results && file_exists(progress_path))  //try and read results from current dir:
		read_old_results(progress_path, train_path_order, merge_with);

	// Load partial progress info, if continuing interrupted optimization
	documented_opts = merge_with; //load existing and rewrite progress:
	ofstream full_progress(progress_path);
	for (size_t i = 0; i < documented_opts.size(); ++i) {
		full_progress << documented_opts[i].to_string() << endl;
		if (best_train_params.samples_id.empty() || documented_opts[i].auc > best_train_params.auc)
			best_train_params = documented_opts[i];
	}
	bool need_to_check_already = !documented_opts.empty();

	MLOG("Has %d options without predictor tuning, start with %zu processed\n",
		excpeted_exp, documented_opts.size());

	// Assign split per pid [only when "use_same_splits" is disabled]
	unordered_set<int> selected_splits;
	if (args.use_same_splits && !test_samples.empty()) {
		const vector<MedIdSamples> &vec = test_samples.begin()->second.idSamples;
		unordered_set<int> splits_ids;
		for (MedIdSamples s : vec)
			splits_ids.insert(s.split);
		int nsplits = (int)splits_ids.size();
		select_splits_numbers(nsplits, args.split_sel, selected_splits);
	}

	//=================================================================================================================================
	// Search for optimal parameters  [start, or continue if earlier interrupted]

	MedProgress full_progress_update("Optimizer_Full", excpeted_exp, 30, 1);
	int file_id = 0;
	if (excpeted_exp * inner_exp_size > 1) {
		if (excpeted_exp != documented_opts.size()) {
			// Loop over files with training samples
			for (const auto &it : train_samples)
			{

				// Load train & test samples 
				const MedSamples &curr_train = it.second;
				const MedSamples &curr_test = test_samples.at(it.first);
				string option_name = "samples_" + it.first;
				curr_candidate.samples_id = it.first;
				curr_candidate.price_ratio = args.price_ratio;
				curr_candidate.matching_strata = args.matching_strata;
				curr_candidate.matching_json = args.matching_json;
				curr_candidate.cases_def = train_ordered_cases_def[file_id];
				curr_candidate.controls_def = train_ordered_controls_def[file_id];
				int id = med_stoi(curr_candidate.samples_id);
				curr_candidate.samples_path = train_path_order[id];

				// Prepare sample-to-split mapping for current train and test
				unordered_map<string, MedSamples> split_to_samples_train, split_to_samples_test;
				samples_to_splits_train_test(curr_train, curr_test, split_to_samples_train, split_to_samples_test);

				// When "--split_sel" command line parameter is provided use only a subset of splits 
				unordered_map<string, MedSamples> train_samples_sel, test_samples_sel;
				if (!args.use_same_splits)
					select_splits(split_to_samples_train, split_to_samples_test, args.split_sel, train_samples_sel, test_samples_sel);
				else
					commit_select_splits(split_to_samples_train, split_to_samples_test, args.split_sel, selected_splits, train_samples_sel, test_samples_sel);

				// For each split, take(train, test) samples
				// and convert to(train_mat_for_split, test_mat_for_split) feature matrices
				unordered_map<string, MedModel> models;
				unordered_map<string, MedFeatures> train_mat, test_mat;
				run_all_splits_mat(
					train_samples_sel,
					test_samples_sel,
					args.json_model,
					rep,
					args.price_ratio,
					args.matching_change_to_prior,
					args.matching_strata,
					args.matching_json,
					false,
					train_mat,
					test_mat,
					models,
					NULL,
					false
				);
				for (auto &it : models)
					it.second.clear(); //free memory
				models.clear();

				int method_num = 0;

				// Loop over different versions of weights [usually not used]
				for (weights_params &train_weight_m : args.train_weights_method)
				{
					string fname = option_name;
					fname += "_weight_function_" + to_string(method_num);
					fix_filename_chars(&fname, '-');
					curr_candidate.w_params = train_weight_m;
					//check if can skip!

					curr_candidate.predictor_type = args.ms_predictor_name;
					if (need_to_check_already && already_did(merge_with, train_path_order, curr_candidate)) {
						MLOG("Skip %s\n", curr_candidate.to_string().c_str());
						++method_num;
						full_progress_update.skip_update();
						continue;
					}

					unordered_map<int, unordered_map<int, float>> pid_time_weight;
					if (train_weight_m.active()) {
						MedFeatures data_train_mat;
						curr_train.export_to_sample_vec(data_train_mat.samples);
						data_train_mat.init_pid_pos_len(); //without the matrix
						assign_weights(args.rep, data_train_mat, train_weight_m);
						//copy to attributes:
						for (size_t i = 0; i < data_train_mat.samples.size(); ++i)
							data_train_mat.samples[i].attributes["weight"] = data_train_mat.weights[i];
						index_pid_time_prob(data_train_mat.samples, pid_time_weight);
					}

					//update weights in train mats:
					for (auto &train_mat_it : train_mat)
						update_mat_weights(train_mat_it.second, args.price_ratio, &pid_time_weight);

					if (args.debug_mat_weights && !train_mat.empty()) {
						//debug first split only!
						MedFeatures &mat = train_mat.begin()->second;
						MedSamples dbg_samples;
						dbg_samples.import_from_sample_vec(mat.samples);
						if (!mat.weights.empty()) {
							int indx = 0;
							for (MedIdSamples &pid_samples : dbg_samples.idSamples)
							{
								for (MedSample &p_samples : pid_samples.samples) {
									p_samples.attributes["weight"] = mat.weights[indx];
									++indx;
								}
							}
						}
						//write to file:
						dbg_samples.write_to_file(args.result_folder + path_sep() + "dbg_train_" + fname + ".samples");
					}

					//=================
					// Model selection:		
					// ================
					//
					//		Find "best configuration", export resulting predictor to "winner"
					//
					// NOTE:
					//		load_selected_model() calls runOptimizerModel(), 
					//		which trains a model per (configuration,split) 
					//		and then averages TEST AUC over splits 

					MedPredictor *winner = NULL;
					float best_auc = load_selected_model(
						winner,
						train_mat,
						test_mat,
						feature_model_gen,
						args.json_model,
						rep,
						args.ms_configs_file,
						args.ms_predictor_name,
						args.result_folder,
						"/dev/null",
						args.price_ratio,
						args.matching_strata,
						args.matching_json,
						fname,
						&pid_time_weight,
						args.override_all_results,
						curr_candidate,
						args.bootstrap_args,
						args.bootstrap_measure,
						args.generelization_error_factor,
						args.debug
					);

					string predictor_args = clean_model_prefix(medial::models::getParamsInfraModel(winner));
					curr_candidate.predictor_args = predictor_args;
					curr_candidate.auc = best_auc;

					//document results:
					full_progress << curr_candidate.to_string() << endl;
					documented_opts.push_back(curr_candidate);

					if (best_train_params.samples_id.empty() || best_auc > best_train_params.auc)
						best_train_params = curr_candidate;

					delete winner;
					full_progress_update.update();
					++method_num;
				}
				++file_id;
			}
		}
	}
	else {
		MLOG("Optimizer, there is only one option for optimizing, so no need to do optimization, skipping...\n");
		curr_candidate.samples_id = train_samples.begin()->first;
		curr_candidate.price_ratio = args.price_ratio;
		curr_candidate.matching_strata = args.matching_strata;
		curr_candidate.matching_json = args.matching_json;
		curr_candidate.cases_def = train_ordered_cases_def[0];
		curr_candidate.controls_def = train_ordered_controls_def[0];
		int id = med_stoi(curr_candidate.samples_id);
		curr_candidate.samples_path = train_path_order[id];
		curr_candidate.predictor_type = args.ms_predictor_name;
		curr_candidate.w_params = args.train_weights_method.front();

		vector<MedPredictor *> all_configs;
		read_ms_config(args.ms_configs_file, args.ms_predictor_name, all_configs);
		string predictor_args = clean_model_prefix(medial::models::getParamsInfraModel(all_configs[0]));
		curr_candidate.predictor_args = predictor_args;

		curr_candidate.auc = -1;
		curr_candidate.auc_train = -1;

		documented_opts.push_back(curr_candidate);
		best_train_params = documented_opts[0];
	}
	full_progress.close();

	// write full all options:
	sort(documented_opts.begin(), documented_opts.end(), [](const full_train_args&a, const full_train_args&b) {
		return a.auc > b.auc; });
	ofstream fw(args.config_folder + path_sep() + "optimize.full.txt");
	for (size_t i = 0; i < documented_opts.size(); ++i)
		fw << documented_opts[i].to_string() << "\n";
	fw.close();

	// Load file with training samples which resulted in the best performance  
	const MedSamples &best_train = train_samples.at(best_train_params.samples_id);
	const MedSamples &best_test = test_samples.at(best_train_params.samples_id);

	// load weights for winner method
	unordered_map<int, unordered_map<int, float>> pid_time_weight_winner;
	if (best_train_params.w_params.active()) {
		MedFeatures data_train_mat;
		best_train.export_to_sample_vec(data_train_mat.samples);
		data_train_mat.init_pid_pos_len(); //without the matrix
		assign_weights(args.rep, data_train_mat, best_train_params.w_params);
		//copy to attributes:
		for (size_t i = 0; i < data_train_mat.samples.size(); ++i)
			data_train_mat.samples[i].attributes["weight"] = data_train_mat.weights[i];
		index_pid_time_prob(data_train_mat.samples, pid_time_weight_winner);
	}

	// 
	if (args.override_all_results || !file_exists(args.config_folder + path_sep() + full_name)) {

		// Initialize predictor with the best parameters
		MedPredictor *winner = MedPredictor::make_predictor(
			best_train_params.predictor_type,
			best_train_params.predictor_args
		);

		// Train model on all the train samples from the training file which resulted in best performing model during parameter selection / Cross validation stage
		unordered_map<string, MedSamples> use_all;
		use_all["All"] = best_train;

		MedSamples flat_train;
		train_model(
			*winner,
			flat_train,
			use_all,
			feature_model_gen,
			args.json_model,
			rep,
			best_train_params.price_ratio,
			args.matching_change_to_prior,
			best_train_params.matching_strata,
			best_train_params.matching_json,
			&pid_time_weight_winner
		);

		// Add the "winner" predictor to MedModel
		if (feature_model_gen.predictor != NULL)
			delete feature_model_gen.predictor;
		feature_model_gen.predictor = winner;

		// Export the MedModel to file
		feature_model_gen.write_to_file(args.config_folder + path_sep() + full_name);

		// Export matched train samples to file
		flat_train.write_to_file(args.config_folder + path_sep() + "matched_full_train.samples");
	}

	if (args.exit_after_full_model)
		return 0;

	//==============================================================================================================================
	// Use optimal parameters to train a separate model on each CV split
	// This is done for subsequent calibration of the model 
	// [so that model returns probabilities]

	float temp1, temp2;
	vector<MedSample> all_collected_samples;
	unordered_map<string, MedModel> model_for_split;
	string save_pattern = args.result_folder + path_sep() + "CV_MODEL_%s.medmdl";

	// associate a set of train/test samples with each split
	unordered_map<string, MedSamples> split_to_samples_train, split_to_samples_test;
	samples_to_splits_train_test(
		best_train,
		best_test,
		split_to_samples_train,
		split_to_samples_test
	);

	// Given optimal parameters, train predictor separately for every participating split, apply and compute AUCs
	run_all_splits(
		split_to_samples_train,
		split_to_samples_test,
		args.json_model,
		rep,
		best_train_params.predictor_type,
		best_train_params.predictor_args,
		best_train_params.price_ratio,
		args.matching_change_to_prior,
		best_train_params.matching_strata,
		best_train_params.matching_json,
		true,
		temp1,
		temp2,
		all_collected_samples,
		model_for_split,
		args.bootstrap_args,
		args.bootstrap_measure,
		true,
		&pid_time_weight_winner,
		save_pattern
	);

	// Export union of all _test_ samples collected over all splits
	// [note that, since this is cross-validation, these samples are still a part of the TRAIN set
	// moreover, when ALL splits are used this union will be identical to the TRAIN set]
	MedSamples results_samples;
	results_samples.import_from_sample_vec(all_collected_samples, true);
	results_samples.write_to_file(args.config_folder + path_sep() + "train_cv_collected.preds");
	return 0;
}