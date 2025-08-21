#include <algorithm>
#include <string>
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "Logger/Logger/Logger.h"
#include "MedAlgo/MedAlgo/MedAlgo.h"
#include "MedAlgo/MedAlgo/MedXGB.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include "MedProcessTools/MedProcessTools/Calibration.h"
#include "Helper.h"
#include "Cmd_Args.h"
#include <boost/filesystem.hpp>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

using namespace std;

void init_model(MedModel &mdl, MedPidRepository &rep, const ProgramArgs &args, const vector<int> &pids_to_take)
{
	string json_model = args.json_model;
	string rep_path = args.rep;
	vector<string> sigs = {"BDATE", "GENDER"};
	unordered_set<string> req_names;
	if (json_model.empty() && args.bin_learned_model.empty())
		MTHROW_AND_ERR("Error - Please provide either json_model or bin_learned_model for creating features for matching\n");
	if (!json_model.empty() && args.bin_learned_model.empty())
	{
		MLOG("Adding new features using %s\n", json_model.c_str());
		mdl.init_from_json_file(json_model);
		mdl.filter_rep_processors();
	}
	if (!args.bin_learned_model.empty())
	{
		MLOG("Adding new features using binary learned MedModel %s\n", args.bin_learned_model.c_str());
		mdl.read_from_file(args.bin_learned_model);
	}
	if (rep.init(rep_path) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	mdl.fit_for_repository(rep);
	mdl.get_required_signal_names(req_names);
	for (string s : req_names)
		sigs.push_back(s);
	sort(sigs.begin(), sigs.end());
	auto it = unique(sigs.begin(), sigs.end());
	sigs.resize(std::distance(sigs.begin(), it));
	int curr_level = global_logger.levels.front();
	global_logger.init_all_levels(LOG_DEF_LEVEL);
	if (rep.read_all(rep_path, pids_to_take, sigs) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	global_logger.init_all_levels(curr_level);
}

int main(int argc, char *argv[])
{
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;
	if (args.debug)
	{
		global_logger.init_all_levels(MIN_LOG_LEVEL);
		global_logger.levels[LOG_DICT] = LOG_DEF_LEVEL;
		global_logger.levels[LOG_INDEX] = LOG_DEF_LEVEL;
		global_logger.levels[LOG_REP] = LOG_DEF_LEVEL;
		global_logger.levels[LOG_SIG] = LOG_DEF_LEVEL;
	}
	if (!args.rep.empty())
		medial::repository::set_global_time_unit(args.rep);

	float matching_price_ratio = args.method_price_ratio; // 0 no matching, else do matching (use 7)
	bool reweigth_method = args.method_price_ratio < 0;
	bool use_model_score = args.probabilty_bin_init.empty() ||
						   args.features_bin_init.empty(); // matching to model or binning method to squeeze information
	int nFolds = args.nFolds_train;
	BinSettings probSettings, feature_sets;
	if (!args.probabilty_bin_init.empty())
		probSettings.init_from_string(args.probabilty_bin_init);
	if (!args.features_bin_init.empty())
		feature_sets.init_from_string(args.features_bin_init);
	if (use_model_score && args.models_selection_file.empty())
		MTHROW_AND_ERR("if not using bin method to block confounders, please specify models_selection_file\n");
	bool do_pairwise_mathcing = args.pairwise_matching_caliper > 0;
	string full_o = args.output;
	if (full_o == "/dev/null")
		full_o = "";
	else
		full_o += ".compare_pop";

	MedFeatures input_mat;
	MedSamples input_smp;
	MedMat<float> mat;
	bool was_sorted;
	switch (args.inp_type)
	{
	case Samples:
		input_smp.read_from_file(args.input, false);
		// check sorting:
		was_sorted = is_sorted(input_smp.idSamples.begin(), input_smp.idSamples.end(),
							   comp_patient_id_time);
		for (int i = 0; i < input_smp.idSamples.size() && was_sorted; ++i)
			was_sorted = was_sorted && is_sorted(input_smp.idSamples[i].samples.begin(),
												 input_smp.idSamples[i].samples.end(), comp_sample_id_time);
		if (!was_sorted)
		{
			MWARN("Warning : input MedSamples was not sorted.\nit causes troubles in the files:"
				  " patient_groups_file,patient_action that should be matched in same order");
			input_smp.sort_by_id_date();
		}
		input_smp.export_to_sample_vec(input_mat.samples);
		break;
	case Samples_Bin:
		input_smp.read_from_bin_file(args.input);
		input_smp.export_to_sample_vec(input_mat.samples);
		break;
	case Features:
		input_mat.read_from_file(args.input);
		break;
	case Features_Csv:
		input_mat.read_from_csv_mat(args.input);
		break;
	case MedMat_Csv:
		mat.read_from_csv_file(args.input, 1);
		input_mat.set_as_matrix(mat);
		break;
	default:
		MTHROW_AND_ERR("Unsupported type %d\n", args.inp_type);
	}

	MedFeatures *final_mat = &input_mat;
	MedModel mdl;
	MedPidRepository rep;
	vector<int> pids_to_take;

	// read action and group
	vector<string> compare_groups, action_feature;
	if (boost::starts_with(args.patient_groups_file, "attr:"))
		read_attr_from_samples(args.patient_groups_file.substr(5), final_mat->samples, compare_groups, "<EMPTY>");
	else
		read_strings(args.patient_groups_file, compare_groups);
	if (compare_groups.size() != final_mat->samples.size())
		MTHROW_AND_ERR("patient_groups_file has %d records. but input has %d records\n",
					   (int)compare_groups.size(), (int)final_mat->samples.size());
	unordered_set<string> grp_count;
	for (size_t i = 0; i < compare_groups.size(); ++i)
		grp_count.insert(compare_groups[i]);
	MLOG("Has %d groups\n", (int)grp_count.size());

	if (boost::starts_with(args.patient_action, "attr:"))
		read_attr_from_samples(args.patient_action.substr(5), final_mat->samples, action_feature, "<EMPTY>");
	else
		read_strings(args.patient_action, action_feature);
	if (action_feature.size() != final_mat->samples.size())
		MTHROW_AND_ERR("patient_action has %d records. but input has %d records\n",
					   (int)action_feature.size(), (int)final_mat->samples.size());
	unordered_map<string, int> action_to_val, action_to_cnt;
	for (size_t i = 0; i < action_feature.size(); ++i)
		if (action_to_cnt.find(action_feature[i]) == action_to_cnt.end())
		{
			++action_to_cnt[action_feature[i]];
		}
	if (action_to_cnt.size() == 1)
		MTHROW_AND_ERR("All the actions are the same. please look at file\n%s\n",
					   args.patient_action.c_str());
	if (action_to_cnt.size() > 2)
		MWARN("Warning: read more than binary action. has %d label values\n",
			  (int)action_to_cnt.size());

	vector<pair<int, string>> actions_sorted;
	actions_sorted.reserve(action_to_cnt.size());
	for (auto it = action_to_cnt.begin(); it != action_to_cnt.end(); ++it)
		actions_sorted.push_back(pair<int, string>(-it->second, it->first));
	sort(actions_sorted.begin(), actions_sorted.end()); // sort by count
	for (int i = 0; i < actions_sorted.size(); ++i)
	{
		action_to_val[actions_sorted[i].second] = i;
		if (args.debug)
			MLOG("Converting \"%s\" to %d\n", actions_sorted[i].second.c_str(), i);
	}

	if (args.select_year > 0)
	{
		MLOG("Filtering and selecting specific year\n");
		vector<int> sel_idx;
		for (int i = 0; i < final_mat->samples.size(); ++i)
			if ((final_mat->samples[i].time / 10000) == args.select_year)
				sel_idx.push_back(i);

		medial::process::filter_row_indexes(*final_mat, sel_idx);
		commit_selection(action_feature, sel_idx);
		commit_selection(compare_groups, sel_idx);
		MLOG("printing stats for outcome after filtering:\n");
		medial::print::print_samples_stats(final_mat->samples);
		// Filter: compare_groups, action_feature
	}

	if (args.debug && args.change_action_prior > 0 && args.change_action_prior < 1)
		print_stats(*final_mat, action_feature, action_to_val);
	if (args.change_action_prior > 0 && args.change_action_prior < 1)
	{
		MLOG("Subsampling of action prior to %2.1f%%\n", 100 * args.change_action_prior);
		vector<float> action_labels(final_mat->samples.size());
		for (size_t i = 0; i < final_mat->samples.size(); ++i)
			action_labels[i] = (float)action_to_val[action_feature[i]];
		vector<float> groups(final_mat->samples.size()); // all in the same group
		vector<int> selection_idx;
		medial::process::match_to_prior(action_labels, groups, args.change_action_prior, selection_idx);

		MLOG("has %zu samples, left with %zu samples\n", final_mat->samples.size(), selection_idx.size());
		MedFeatures cp_for_cmp = *final_mat;
		medial::process::filter_row_indexes(*final_mat, selection_idx);
		commit_selection(action_feature, selection_idx);
		commit_selection(compare_groups, selection_idx);
		string full_o2 = full_o;
		if (!full_o2.empty())
			full_o2 += ".change_mean";
		medial::process::compare_populations(cp_for_cmp, *final_mat, "original", "after_change_prior",
											 full_o2, args.model_validation_type, args.model_validation_init);
	}
	print_stats(*final_mat, action_feature, action_to_val);
	if (args.age_bin > 0)
	{
		print_age_stats(*final_mat, action_feature, action_to_val, args.age_bin);
		// return 0;
	}

	double rt = (double)args.down_sample_max_cnt / final_mat->samples.size();
	if (args.down_sample_max_cnt > 0 && rt < 1)
	{
		MLOG("Down sampling input by %1.2f facor\n", 1 / rt);
		vector<int> sel_idx;
		medial::process::down_sample(*final_mat, rt, false, &sel_idx);
		// filter  action_feature, compare_groups
		commit_selection(action_feature, sel_idx);
		commit_selection(compare_groups, sel_idx);
	}
	if (args.debug && args.down_sample_max_cnt > 0 && rt < 1)
		print_stats(*final_mat, action_feature, action_to_val);

	// MedSamples samples;
	input_smp.clear();
	final_mat->get_samples(input_smp); // output samples from final_mat

	switch (args.inp_type)
	{
	case Samples:
	case Samples_Bin:
		// Convert to MedFeatures:
		medial::print::print_samples_stats(input_smp);
		medial::print::print_by_year(input_smp, 1, false, true);

		input_smp.get_ids(pids_to_take);
		init_model(mdl, rep, args, pids_to_take);

		if (!args.json_model.empty() && args.bin_learned_model.empty())
		{
			if (mdl.learn(rep, &input_smp, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
				MTHROW_AND_ERR("Error creating age,gender for samples\n");
		}
		else
		{
			if (mdl.apply(rep, input_smp, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
				MTHROW_AND_ERR("Error creating features for medmodel\n");
		}
		final_mat = &mdl.features;

		break;
	case Features:
	case Features_Csv:
		if (!args.json_model.empty())
		{
			unordered_set<int> ids;
			for (size_t i = 0; i < input_mat.samples.size(); ++i)
			{
				if (ids.find(input_mat.samples[i].id) == ids.end())
				{ // start new pid
					MedIdSamples new_smp(input_mat.samples[i].id);
					input_smp.idSamples.push_back(new_smp);
				}
				input_smp.idSamples.back().samples.push_back(input_mat.samples[i]);

				ids.insert(input_mat.samples[i].id);
			}
			vector<int> pids_to_take(ids.begin(), ids.end());
			init_model(mdl, rep, args, pids_to_take);

			if (mdl.apply(rep, input_smp, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
				MTHROW_AND_ERR("Error creating age,gender for samples\n");
			final_mat = &mdl.features;
			// add old loaded features in mat:
			for (auto it = input_mat.data.begin(); it != input_mat.data.end(); ++it)
				final_mat->data[it->first].swap(it->second); // it may "steal" the memory of loaded feature
		}
		break;
	default:
		break;
	}
	MLOG("printing stats for outcome:\n");
	medial::print::print_samples_stats(final_mat->samples);

	// load from disk:
	vector<int> pids;
	input_smp.get_ids(pids);

	if (!args.confounders_file.empty())
	{
		unordered_set<string> confounders_input, confounders_final;
		read_confounders(args.confounders_file, confounders_input);
		// check that we have all confounders in matrix:
		for (auto i = confounders_input.begin(); i != confounders_input.end(); ++i)
			confounders_final.insert(get_name(final_mat->data, *i));
		// keep only confounder vars:
		for (auto it = final_mat->data.begin(); it != final_mat->data.end();)
			if (confounders_final.find(it->first) != confounders_final.end())
				++it;
			else
				it = final_mat->data.erase(it);
	}

	vector<MedPredictor *> all_models_configs;
	if (use_model_score)
		read_ms_config(args.models_selection_file, args.model_type, all_models_configs);
	// run on ldl.bin mat
	MedFeatures copy_all;
	vector<string> copy_compare_groups, copy_action_feature;
	// prepare and convert matrix to prctile values
	if (do_pairwise_mathcing)
		for (auto it = final_mat->data.begin(); it != final_mat->data.end(); ++it)
			medial::process::convert_prctile(final_mat->data[it->first]);

	// always create copy
	// if (args.nbootstrap > 1) {
	copy_all = *final_mat;
	copy_compare_groups = compare_groups;
	copy_action_feature = action_feature;
	//}

	vector<unordered_map<string, float>> all_general_measures; // loop, measure
	vector<vector<unordered_map<string, float>>> all_measures; // loop, group, measure
	all_general_measures.resize(args.nbootstrap);
	all_measures.resize(args.nbootstrap);
	unordered_set<string> groups_y_u(compare_groups.begin(), compare_groups.end());
	vector<string> groups_y_sorted(groups_y_u.begin(), groups_y_u.end());
	sort(groups_y_sorted.begin(), groups_y_sorted.end());
	for (size_t i = 0; i < all_measures.size(); ++i)
		all_measures[i].resize(groups_y_u.size());
	random_device rd;
	mt19937 gen(rd());
	int medAlg_level = global_logger.levels[LOG_MEDALGO];
	global_logger.levels[LOG_MEDALGO] = MAX_LOG_LEVEL;
	MedProgress progress("Bootstrap_action_effect", args.nbootstrap, 30, 1);

	string base_log_folder = boost::filesystem::path(args.output.c_str()).parent_path().string() +
							 path_sep() + "bootstrap_loop";
	if (args.nbootstrap > 1 && args.debug && args.output != "/dev/null")
		boost::filesystem::create_directories(base_log_folder);

	for (int loop = 0; loop < args.nbootstrap; ++loop)
	{
		MLOG("Starting bootstrap loop %d\n", loop + 1);
#pragma region prepare bootstrap matrix
		vector<float> sample_weights;
		vector<int> seleced_filt;
		vector<float> old_outcome_n;

		MedFeatures loop_feats;
		if (args.nbootstrap > 1)
		{							 // need sampling
			loop_feats = copy_all;	 // create full copy
			final_mat = &loop_feats; // start from original full copy
			compare_groups = copy_compare_groups;
			action_feature = copy_action_feature;
			vector<int> down_indexes;
			if (args.bootstrap_subsample == 1)
				medial::process::down_sample(*final_mat, 0.99999, true, &down_indexes); // becuase if ==1 wont do anything
			else
				medial::process::down_sample(*final_mat, args.bootstrap_subsample, true, &down_indexes);
			action_feature.resize(down_indexes.size());
			compare_groups.resize(down_indexes.size());
			for (size_t i = 0; i < down_indexes.size(); ++i)
			{
				action_feature[i] = copy_action_feature[down_indexes[i]];
				compare_groups[i] = copy_compare_groups[down_indexes[i]];
			}
		}
		MedFeatures treatFeats;
		treatFeats.samples = final_mat->samples;
		for (size_t i = 0; i < treatFeats.samples.size(); ++i)
			treatFeats.samples[i].outcome = (float)action_to_val[action_feature[i]];
		if (loop <= 0)
		{
			MLOG("printing stats for learning action:\n");
			medial::print::print_samples_stats(treatFeats.samples);
		}

		treatFeats.attributes = final_mat->attributes;
		treatFeats.data = final_mat->data;
		vector<float> treat_labels(treatFeats.samples.size());
		vector<int> cnts(2);
		for (size_t i = 0; i < treat_labels.size(); ++i)
		{
			treat_labels[i] = treatFeats.samples[i].outcome;
			++cnts[treat_labels[i] > 0];
		}
		float ratio = float(cnts[1]) / treat_labels.size();
		if (ratio / 2 < args.min_probablity_cutoff || (ratio > 0.5 && ((1 - ratio) / 2) < args.min_probablity_cutoff))
			MWARN("Warning: 0.5*the prior of action is less than cutoff probabilty!\nprior=%f, cutoff=%f\n",
				  ratio, args.min_probablity_cutoff);
#pragma endregion

		if (!do_pairwise_mathcing)
		{
#pragma region Learn_Treatment
			// Learn Treatment Model:
			vector<float> probs, preds;

			if (!use_model_score)
			{
				map<string, BinSettings> feature_settings;
				for (auto it = treatFeats.data.begin(); it != treatFeats.data.end(); ++it)
					feature_settings[it->first] = feature_sets;
				createProbabiltyBins(treatFeats, probSettings, feature_settings, probs);
				if (nFolds > 1)
				{
					float test_ratio = 1.0 / nFolds;
					uniform_int_distribution<> dist_r(0, (int)treatFeats.samples.size() - 1); // each id is once in this sample:
					MedFeatures testData = treatFeats;										  // copy
					vector<int> test_selection;
					vector<float> treatLabels_test;
					vector<bool> seen_test(treatFeats.samples.size());
					test_selection.reserve((int)(test_ratio * treatFeats.samples.size()));
					treatLabels_test.resize((int)(test_ratio * treatFeats.samples.size()));
					for (size_t i = 0; i < test_ratio * treatFeats.samples.size(); ++i)
					{
						int r = dist_r(gen);
						while (seen_test[r])
							r = dist_r(gen);
						seen_test[r] = true;
						test_selection.push_back(r);
					}
					medial::process::filter_row_indexes(testData, test_selection);
					medial::process::filter_row_indexes(treatFeats, test_selection, true); // train is opposite
					MLOG("Train size = %d, test_size=%d\n",
						 (int)treatFeats.samples.size(), (int)testData.samples.size());
					treat_labels.resize(treatFeats.samples.size());
					for (size_t i = 0; i < treat_labels.size(); ++i)
						treat_labels[i] = treatFeats.samples[i].outcome;
					for (size_t i = 0; i < testData.samples.size(); ++i)
						treatLabels_test[i] = testData.samples[i].outcome;

					vector<float> probs_test;
					createProbabiltyBins(testData, probSettings, feature_settings, probs_test);
					float auc_train = medial::performance::auc_q(probs, treat_labels);
					float auc_test = medial::performance::auc_q(probs_test, treatLabels_test);
					all_general_measures[loop]["TRAIN_AUC"] = auc_train;
					all_general_measures[loop]["TEST_AUC"] = auc_test;
					MLOG("Auc_train = %2.3f, Auc_test=%2.3f\n", auc_train, auc_test);
					unordered_set<float> uniq_probs(probs_test.begin(), probs_test.end());
					all_general_measures[loop]["PROB_BIN_CNT"] = (float)uniq_probs.size();
				}
				else
				{
					float auc_train = medial::performance::auc_q(probs, treat_labels);
					all_general_measures[loop]["TRAIN_AUC"] = auc_train;
					MLOG("Auc_train = %2.3f\n", auc_train);
					unordered_set<float> uniq_probs(probs.begin(), probs.end());
					all_general_measures[loop]["PROB_BIN_CNT"] = (float)uniq_probs.size();
				}
			}
			else
			{
				// prepare confounders
				MedPredictor *treatment_predictor = MedPredictor::make_predictor(args.model_type);

				loss_confounders_params loss_params;
				loss_params.all_matrix = &treatFeats;
				loss_params.validator_type = args.model_validation_type;
				loss_params.validator_init = args.model_validation_init;
				loss_params.validation_nFolds = args.nFolds_validation;
				loss_params.random_generator = &gen;
				vector<int> empty_int_arr;
				// loss_params.preds_bining_settings = pred_setts;
				vector<pair<string, unordered_map<string, float>>> results_measures;
				string optimal_setts = runOptimizerModel(treatFeats,
														 all_models_configs, nFolds, gen, args.model_prob_clibrator, args.min_probablity_cutoff, loss_target_confounders_AUC, &loss_params, results_measures);
				if (args.output != "/dev/null")
					write_model_selection(results_measures, args.output + ".model_selection");
				treatment_predictor->init_from_string(optimal_setts);
				all_models_configs.resize(1);
				all_models_configs[0] = treatment_predictor;

				medial::models::get_pids_cv(treatment_predictor, treatFeats, nFolds, gen, preds);
				for (size_t kk = 0; kk < preds.size(); ++kk)
					treatFeats.samples[kk].prediction = {preds[kk]};

				Calibrator cl;
				cl.init_from_string(args.model_prob_clibrator);
				cl.Learn(treatFeats.samples);
				cl.Apply(treatFeats.samples);
				probs.resize(preds.size());
				for (size_t kk = 0; kk < probs.size(); ++kk)
					probs[kk] = treatFeats.samples[kk].prediction[0];

				medial::print::print_hist_vec(preds, "scores hist", "%2.3f");
				medial::print::print_hist_vec(probs, "Prob hist", "%2.3f");

				float auc_train = medial::performance::auc_q(preds, treat_labels);
				float auc_train_bin = medial::performance::auc_q(probs, treat_labels);
				all_general_measures[loop]["TRAIN_CV_AUC"] = auc_train;
				all_general_measures[loop]["TRAIN_AUC_BINNED"] = auc_train_bin;
				if (nFolds > 1)
					MLOG("TRAIN_CV_AUC = %2.3f, TRAIN_AUC_BINNED=%2.3f\n", auc_train, auc_train_bin);

				else
					MLOG("TRAIN_AUC = %2.3f, TRAIN_AUC_BINNED=%2.3f\n", auc_train, auc_train_bin);
				unordered_set<float> uniq_probs(probs.begin(), probs.end());
				all_general_measures[loop]["PROB_BIN_CNT"] = (float)uniq_probs.size();
				// delete treatment_predictor;
			}

			final_mat->data["Treatment_Score"].resize(final_mat->samples.size());
			for (size_t i = 0; i < final_mat->samples.size(); ++i)
				final_mat->data["Treatment_Score"][i] = probs[i];

#pragma endregion

#pragma region Matching

			// Matching: match by matching_groups
			vector<string> filtered_groups(final_mat->samples.size());
			for (size_t i = 0; i < filtered_groups.size(); ++i)
				filtered_groups[i] = to_string(final_mat->data["Treatment_Score"][i]);

			sample_weights.resize(final_mat->samples.size(), 1);
			if (reweigth_method || matching_price_ratio > 0)
			{
				// override outcome and rewrite again:
				old_outcome_n.resize(final_mat->samples.size());
				for (size_t i = 0; i < old_outcome_n.size(); ++i)
				{
					old_outcome_n[i] = final_mat->samples[i].outcome;
					final_mat->samples[i].outcome = treat_labels[i];
				}

				if (reweigth_method)
				{
					sample_weights.resize(final_mat->samples.size());
					float min_prob = args.min_probablity_cutoff;
					int cutoff_cnt = 0;
					vector<int> cutoff_cnts_cl(2);
					vector<double> cutoff_outcome_ratio(2);
					double tot_w = 0;
					for (size_t k = 0; k < final_mat->samples.size(); ++k)
					{
						sample_weights[k] = get_weight(final_mat->data["Treatment_Score"][k], final_mat->samples[k].outcome, min_prob);
						if (final_mat->data["Treatment_Score"][k] < min_prob ||
							final_mat->data["Treatment_Score"][k] > 1 - min_prob)
						{
							++cutoff_cnt;
							sample_weights[k] = 0; // remove example
							++cutoff_cnts_cl[final_mat->data["Treatment_Score"][k] > 1 - min_prob];
							cutoff_outcome_ratio[final_mat->data["Treatment_Score"][k] > 1 - min_prob] +=
								old_outcome_n[k];
						}
						tot_w += sample_weights[k];
					}
					for (size_t k = 0; k < sample_weights.size(); ++k)
						sample_weights[k] *= ((sample_weights.size() - cutoff_cnt) / tot_w);

					for (size_t k = 0; k < 2; ++k)
						cutoff_outcome_ratio[k] = (cutoff_cnts_cl[k] > 0 ? cutoff_outcome_ratio[k] / cutoff_cnts_cl[k] : MED_MAT_MISSING_VALUE);

					// double min_factor = medial::process::reweight_by_general(*final_mat, filtered_groups, sample_weights, args.debug);
					MLOG("After Reweighting. factor by %1.4f, has %d[%d, %d] non ignorable\n",
						 float((sample_weights.size() - cutoff_cnt) / tot_w),
						 cutoff_cnt, cutoff_cnts_cl[0], cutoff_cnts_cl[1]);
					MLOG("Dropping %d(%2.3f%% of dropped, and %2.3f%% of original population) \"healthy\""
						 "(low probabilty for action) population\n",
						 cutoff_cnts_cl[0],
						 cutoff_cnt > 0 ? (100.0 * cutoff_cnts_cl[0]) / cutoff_cnt : 0.0,
						 (100.0 * cutoff_cnts_cl[0]) / final_mat->samples.size());
					MLOG("Dropping %d(%2.3f%% of dropped, and %2.3f%% of original population) \"sick\""
						 "(high probabilty for action) population\n",
						 cutoff_cnts_cl[1],
						 cutoff_cnt > 0 ? (100.0 * cutoff_cnts_cl[1]) / cutoff_cnt : 0.0,
						 (100.0 * cutoff_cnts_cl[1]) / final_mat->samples.size());
					all_general_measures[loop]["DROPPED_LOW_RISK_CNT"] = cutoff_cnts_cl[0];
					all_general_measures[loop]["DROPPED_HIGH_RISK_CNT"] = cutoff_cnts_cl[1];
					all_general_measures[loop]["DROPPED_LOW_RISK_OUTCOME_PROB"] = cutoff_outcome_ratio[0];
					all_general_measures[loop]["DROPPED_HIGH_RISK_OUTCOME_PROB"] = cutoff_outcome_ratio[1];
				}
				else
				{
					medial::process::match_by_general(*final_mat, filtered_groups, seleced_filt, matching_price_ratio, 5, args.debug);
					sample_weights.resize(final_mat->samples.size(), 1);
				}
			}

#pragma endregion
		}

		else
		{
#pragma region PairWise Matching
			vector<const vector<float> *> similarity_matrix(treatFeats.samples.size()); // feature matrix for similarity:
			vector<vector<float>> transposed(treatFeats.samples.size());
			for (size_t k = 0; k < transposed.size(); ++k)
			{
				transposed[k].resize(treatFeats.data.size());
				int dim_i = 0;
				for (auto it = treatFeats.data.begin(); it != treatFeats.data.end(); ++it)
				{
					transposed[k][dim_i] = it->second[k];
					++dim_i;
				}
			}

			for (size_t k = 0; k < similarity_matrix.size(); ++k)
				similarity_matrix[k] = &transposed[k];

			old_outcome_n.resize(final_mat->samples.size());
			for (size_t i = 0; i < old_outcome_n.size(); ++i)
			{
				old_outcome_n[i] = final_mat->samples[i].outcome;
				final_mat->samples[i].outcome = treat_labels[i];
			}

			match_samples_pairwise(treatFeats.samples, treat_labels, similarity_matrix, args.pairwise_matching_caliper, seleced_filt, !args.debug);
			medial::process::filter_row_indexes(*final_mat, seleced_filt);
			sample_weights.resize(final_mat->samples.size(), 1);
			final_mat->data["Treatment_Score"].resize(final_mat->samples.size());
			for (size_t i = 0; i < final_mat->samples.size(); ++i)
				final_mat->data["Treatment_Score"][i] = treatFeats.samples[seleced_filt[i]].outcome;
#pragma endregion
		}

#pragma region Commit Mathcing
		double tot_cases = 0, tot_cont = 0;
		for (size_t i = 0; i < final_mat->samples.size(); ++i)
			if (final_mat->samples[i].outcome > 0)
				tot_cases += sample_weights[i];
			else
				tot_cont += sample_weights[i];
		// for treatment
		all_general_measures[loop]["MATCHING_FINAL_NPOS"] = float(tot_cases);
		all_general_measures[loop]["MATCHING_FINAL_NNEG"] = float(tot_cont);
		all_general_measures[loop]["MATCHING_FINAL_RATIO"] = float(tot_cases / (tot_cases + tot_cont));
		MLOG("After Matching has %2.1f controls and %2.1f cases with %2.3f%% percentage\n",
			 tot_cont, tot_cases, 100.0 * tot_cases / (tot_cases + tot_cont));

		vector<string> filter_grp;
		vector<float> saved_debug_labels;
		if (args.debug && args.output != "/dev/null" && loop == 0)
		{
			saved_debug_labels.resize(final_mat->samples.size());
			for (size_t i = 0; i < final_mat->samples.size(); ++i)
				saved_debug_labels[i] = final_mat->samples[i].outcome;
		}
		// vector<vector<float>> confounder_data_filtered(all_confounders.size());
		for (size_t i = 0; i < final_mat->samples.size(); ++i)
			if (!seleced_filt.empty())
				final_mat->samples[i].outcome = old_outcome_n[seleced_filt[i]];
			else
				final_mat->samples[i].outcome = old_outcome_n[i];

		if (!seleced_filt.empty())
		{
			// filter :compare_groups and confounder vectors for testing:
			filter_grp.resize(seleced_filt.size());
			for (size_t k = 0; k < filter_grp.size(); ++k)
				filter_grp[k] = compare_groups[seleced_filt[k]];
			compare_groups.swap(filter_grp);
		}

		if (args.debug && args.output != "/dev/null" && loop == 0)
		{
			if (reweigth_method)
			{
				MLOG("writing reweighted samples to disk as csv in %s\n",
					 (args.output + ".matched.MedFeature.csv").c_str());
				final_mat->weights = sample_weights;
				final_mat->data["###Action###"] = saved_debug_labels;
				// Save Action for printing
				final_mat->write_as_csv_mat(args.output + ".matched.MedFeature.csv");
				final_mat->data.erase("###Action###");
			}
			else
			{
				MLOG("writing matched samples to disk in %s\n",
					 (args.output + ".matched.samples").c_str());
				MedSamples matched;
				final_mat->get_samples(matched);
				matched.write_to_file(args.output + ".matched.samples");
			}
		}

#pragma endregion

#pragma region Grouping

		vector<string> &group_y = compare_groups; // Ldl value for example
		vector<float> labels((int)final_mat->samples.size());
		for (size_t i = 0; i < final_mat->samples.size(); ++i)
			labels[i] = final_mat->samples[i].outcome;

		// sum stats:
		vector<double> counts_controls, counts_cases; // for each group_y the counts for 0,1
		counts_controls.resize(groups_y_sorted.size());
		counts_cases.resize(groups_y_sorted.size());

		for (size_t i = 0; i < group_y.size(); ++i)
		{
			int pos_group_y = medial::process::binary_search_index(groups_y_sorted.data(),
																   groups_y_sorted.data() + groups_y_sorted.size() - 1, group_y[i]);
			if (pos_group_y < 0 || pos_group_y >= counts_cases.size())
				MTHROW_AND_ERR("OutOfRange pos_group_y=%d, "
							   "groups_y_sorted.size()=%d, group_y[i]=%s,  counts_cases[pos_group_x].size()=%d\n",
							   pos_group_y, (int)groups_y_sorted.size(), group_y[i].c_str(),
							   (int)counts_cases.size());
			if (labels[i] > 0)
				counts_cases[pos_group_y] += sample_weights[i];
			else
				counts_controls[pos_group_y] += sample_weights[i];
		}

#pragma endregion

#pragma region Confounders Test
		// Test Independnce:
		/*vector<vector<float>> loss_confounders;
		loss_confounders.resize(all_confounders.size());
		int i_loss = 0;
		for (auto it = all_confounders.begin(); it != all_confounders.end(); ++it)
		{
			loss_confounders[i_loss] = it->second;
			++i_loss;
		}*/
		// vector<string> &groups_xx = groups_x;
		vector<string> groups_xx(group_y.size());
		unordered_set<string> uniqs;
		for (size_t i = 0; i < groups_xx.size(); ++i)
		{
			groups_xx[i] = to_string(final_mat->data["Treatment_Score"][i]);
			uniqs.insert(groups_xx[i]);
		}
		vector<string> groups_xx_sorted(uniqs.begin(), uniqs.end());
		sort(groups_xx_sorted.begin(), groups_xx_sorted.end());

		vector<float> treat_labels_final(final_mat->samples.size());
		for (size_t i = 0; i < treat_labels_final.size(); ++i)
			treat_labels_final[i] = (float)action_to_val[action_feature[i]];
		vector<float> *p_target = &treat_labels_final;
		if (args.do_validation_outcome)
		{
			p_target = &labels;
			if (loop == 0)
				MLOG("Validating on outcome as target!\n");
		}

		if (!args.do_validation_outcome)
		{
			for (size_t i = 0; i < final_mat->samples.size(); ++i)
				final_mat->samples[i].outcome = treat_labels_final[i];
		}

		// get weighted AUC:
		loss_confounders_params loss_params;
		loss_params.random_generator = &gen;
		loss_params.validation_nFolds = args.nFolds_validation;
		loss_params.validator_type = args.model_validation_type;
		loss_params.validator_init = args.model_validation_init;
		loss_params.all_matrix = final_mat;
		vector<float> treatment_score;
		treatment_score.swap(final_mat->data["Treatment_Score"]);
		final_mat->data.erase("Treatment_Score"); // remove Treatment_Score for learning again
		// final_mat->weights.resize(final_mat->samples.size(), 1);//TODO: fill
		if (reweigth_method)
			final_mat->weights = sample_weights;
		else
			final_mat->weights.clear();
		vector<float> validation_scores;

		double val_auc = loss_target_AUC(treatment_score, *p_target, validation_scores, &loss_params);
		double auc2;
		final_mat->data["Treatment_Score"].swap(treatment_score); // add back
		if (args.do_validation_outcome)
		{
			auc2 = medial::performance::auc_q(validation_scores, treat_labels, &final_mat->weights);
			all_general_measures[loop]["SECOND_WEIGHTED_AUC"] = float(auc2);
			MLOG("SECOND_WEIGHTED_AUC = %2.3f\n", auc2);
			all_general_measures[loop]["OUTCOME_WEIGHTED_AUC"] = float(val_auc);
			MLOG("OUTCOME_WEIGHTED_AUC = %2.3f\n", val_auc);
		}
		else
		{
			all_general_measures[loop]["SECOND_WEIGHTED_AUC"] = float(val_auc);
			MLOG("SECOND_WEIGHTED_AUC = %2.3f\n", val_auc);
		}
		if (!args.do_validation_outcome)
		{
			for (size_t i = 0; i < final_mat->samples.size(); ++i)
				final_mat->samples[i].outcome = labels[i];
		}

#pragma endregion

#pragma region Write Files
		// Write stats file:
		string full_output_name = args.output;
		if (args.nbootstrap > 1)
			full_output_name = base_log_folder + path_sep() + "loop." + to_string(loop);
		ofstream res_file;
		if (args.output != "/dev/null" && (args.debug || args.nbootstrap == 1))
		{
			res_file.open(full_output_name);
			if (!res_file.good())
				MTHROW_AND_ERR("Can't create output %s\n", full_output_name.c_str());
		}
		double tot_countorls = 0, tot_cases_d = 0;
		for (size_t j = 0; j < groups_y_sorted.size(); ++j)
		{
			tot_countorls += counts_controls[j];
			tot_cases_d += counts_cases[j];
		}
		double tot_ratio = 0;
		if (tot_cases_d + tot_countorls > 0)
			tot_ratio = tot_cases_d / (tot_cases_d + tot_countorls);
		all_general_measures[loop]["NPOS"] = float(tot_cases_d);
		all_general_measures[loop]["NNEG"] = float(tot_countorls);
		all_general_measures[loop]["PPV"] = float(tot_ratio);

		if (args.output != "/dev/null" && (args.debug || args.nbootstrap == 1))
		{
			res_file
				<< "mean_incidence_precantage=" << medial::print::print_obj(100 * tot_ratio, "%2.2f") << "%"
				<< "\n";
			res_file << "risk_factor" << "\t" << "controls_count" << "\t" << "cases_count" << "\t"
					 << "case percentage" << "\t" << "lift"
					 << "\n";
		}
		for (size_t j = 0; j < groups_y_sorted.size(); ++j)
		{
			double ratio = 0;
			double tot_cnt = counts_cases[j] + counts_controls[j];
			if (counts_cases[j] + counts_controls[j] > 0)
				ratio = counts_cases[j] / tot_cnt;
			all_measures[loop][j]["CONTROLS_CNT"] = (float)counts_controls[j];
			all_measures[loop][j]["CASES_CNT"] = (float)counts_cases[j];
			all_measures[loop][j]["CASES_PROB"] = (float)100 * ratio;
			all_measures[loop][j]["LIFT"] = float(ratio / tot_ratio);

			if (args.output != "/dev/null" && (args.debug || args.nbootstrap == 1))
				res_file << groups_y_sorted[j]
						 << "\t" << medial::print::print_obj(counts_controls[j], "%2.1f")
						 << "\t" << medial::print::print_obj(counts_cases[j], "%2.1f")
						 << "\t" << medial::print::print_obj(100 * ratio, "%2.2f") << "%"
						 << "\t" << medial::print::print_obj(ratio / tot_ratio, "%2.2f") // Lift
						 << "\n";
		}
		if (args.output != "/dev/null" && (args.debug || args.nbootstrap == 1))
		{
			res_file << endl; // flush buffer and create extra new line
			res_file.close();
		}

#pragma endregion

		if (loop == 0 && args.debug)
		{
			// print compare populations:
			medial::process::compare_populations(copy_all, *final_mat, "original", "matched", full_o,
												 args.model_validation_type, args.model_validation_init);
		}

		progress.update();
	}
	global_logger.levels[LOG_MEDALGO] = medAlg_level;
	// write  summerized stats:
	if (args.nbootstrap > 1)
	{
		map<string, float> final_general;
		vector<map<string, float>> final_specific(groups_y_u.size());
		gether_stats(all_general_measures, final_general);
		for (size_t i = 0; i < final_specific.size(); ++i)
		{
			vector<unordered_map<string, float>> raw(all_measures.size());
			for (size_t k = 0; k < raw.size(); ++k)
				for (auto it = all_measures[0][i].begin(); it != all_measures[0][i].end(); ++it)
					raw[k][it->first] = all_measures[k][i].at(it->first);
			gether_stats(raw, final_specific[i]);
		}

		// write summerized file:
		if (args.output != "/dev/null")
		{
			ofstream res_file(args.output);
			if (!res_file.good())
				MTHROW_AND_ERR("Can't create output %s\n", args.output.c_str());

			for (auto it = final_general.begin(); it != final_general.end(); ++it)
				res_file << "GENERAL" << "\t" << it->first << "\t" << it->second << "\n";
			for (size_t i = 0; i < final_specific.size(); ++i)
				for (auto it = final_specific[i].begin(); it != final_specific[i].end(); ++it)
					res_file << groups_y_sorted[i] << "\t" << it->first << "\t" << it->second << "\n";

			res_file.close();
		}
	}

	// print final stats if has no more than 2 groups. otherwise open results file yourself:
	if (grp_count.size() <= 10)
	{
		vector<map<string, float>> final_specific(groups_y_u.size());
		for (size_t i = 0; i < final_specific.size(); ++i)
		{
			vector<unordered_map<string, float>> raw(all_measures.size());
			for (size_t k = 0; k < raw.size(); ++k)
				for (auto it = all_measures[0][i].begin(); it != all_measures[0][i].end(); ++it)
					raw[k][it->first] = all_measures[k][i].at(it->first);
			gether_stats(raw, final_specific[i]);
		}
		for (size_t i = 0; i < final_specific.size(); ++i)
			MLOG("%s: Lift=%2.3f[%2.3f - %2.3f]\n", groups_y_sorted[i].c_str(),
				 final_specific[i].at("LIFT_Mean"),
				 final_specific[i].at("LIFT_CI.Lower.95"), final_specific[i].at("LIFT_CI.Upper.95"));
	}

	MLOG("Done\n");
	return 0;
}
