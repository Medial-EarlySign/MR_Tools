#include "Cmd_Args.h"
#include <unordered_map>
#include <map>
#include <vector>
#include <fstream>
#include <iostream>
#include "MedStat/MedStat/MedBootstrap.h"
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include "MedUtils/MedUtils/MedSamplingStrategy.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include <boost/filesystem/path.hpp>
#include <boost/filesystem.hpp>

using namespace std;

void init_model(MedModel &mdl, MedPidRepository& rep, const ProgramArgs& args, const vector<int> &pids_to_take) {
	string json_model = args.json_model;
	string rep_path = args.rep;
	if (!json_model.empty()) {
		MLOG("Adding new features using %s\n", json_model.c_str());
		vector<string> alter_vec = args.train_test_json_alt;
		mdl.init_from_json_file_with_alterations(json_model, alter_vec);
	}

	bool need_age = true, need_gender = true;
	for (FeatureGenerator *generator : mdl.generators) {
		if (generator->generator_type == FTR_GEN_AGE)
			need_age = false;
		if (generator->generator_type == FTR_GEN_GENDER)
			need_gender = false;
	}
	if (need_age)
		mdl.add_age();
	if (need_gender)
		mdl.add_gender();

	if (rep.init(rep_path) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	mdl.fit_for_repository(rep);
	unordered_set<string> req_names;
	mdl.get_required_signal_names(req_names);

	vector<string> sigs = { "BDATE", "GENDER" };
	if (args.use_censor)
		sigs.push_back("Censor");
	for (string s : req_names)
		sigs.push_back(s);
	sort(sigs.begin(), sigs.end());
	auto it = unique(sigs.begin(), sigs.end());
	sigs.resize(std::distance(sigs.begin(), it));
	mdl.filter_rep_processors();

	int curr_level = global_logger.levels.front();
	global_logger.init_all_levels(LOG_DEF_LEVEL);
	if (rep.read_all(rep_path, pids_to_take, sigs) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	global_logger.init_all_levels(curr_level);
}

void get_cohort_params_use(const MedBootstrap &m, vector<string> &param_use) {
	param_use.clear();
	unordered_set<string> con_set;
	for (auto ii = m.filter_cohort.begin(); ii != m.filter_cohort.end(); ++ii)
		for (size_t i = 0; i < ii->second.size(); ++i)
			con_set.insert(ii->second[i].param_name);
	param_use.insert(param_use.end(), con_set.begin(), con_set.end());
}

bool valid_cohort(const vector<float> &y) {
	//valid if not empty and has both case and control.
	//we will check that has case and control - search for first occourance of case or control
	//after seeing the other one
	for (size_t i = 1; i < y.size(); ++i)
		if (y[i] != y[i - 1])
			return true;
	return false;
}

void read_weights_file(const string &fp, vector<float> &weights) {
	ifstream fr(fp);
	if (!fr.good())
		MTHROW_AND_ERR("Error: unable to read file %s\n", fp.c_str());
	string line;
	while (getline(fr, line)) {
		float w = med_stof(line);
		weights.push_back(w);
	}
	fr.close();
}

void read_weights_samples(const string &attr, vector<float> &weights, const vector<MedSample> &samples) {
	bool has_miss = false, found = false;
	weights.resize(samples.size(), 1); //give 1 weights to all
	for (size_t i = 0; i < samples.size(); ++i) {
		if (samples[i].attributes.find(attr) == samples[i].attributes.end())
			has_miss = true;
		else {
			weights[i] = samples[i].attributes.at(attr);
			found = true;
		}
	}
	if (has_miss && found)
		MWARN("Warning get_weights: has weights for some of the samples\n");
	else if (found)
		MLOG("Read Weights from samples attr %s\n", attr.c_str());
}


int main(int argc, char *argv[])
{
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;
	if (args.debug)
		global_logger.levels[LOG_APP] = MIN_LOG_LEVEL;
	//global_logger.init_all_levels(MIN_LOG_LEVEL);
	if (!args.rep.empty())
		medial::repository::set_global_time_unit(args.rep);
	if (args.use_censor && args.rep.empty())
		MWARN("WARNING: You have request to censor, but haven't given repository."
			" No censoring for you!\n");
	bool need_rep = args.is_rep_needed();
	if (need_rep && args.rep.empty())
		MTHROW_AND_ERR("Given MedSamples file with cohort definition with no repository"
			" and the cohort uses Age or Gender or has registry_path for calcing incidence!\n");
	if (!args.incidence_file.empty() && !args.registry_path.empty()) {
		MWARN("WARNING: You have provided both registry_path and general incidence_file."
			"will use the registry_path to create incidence on each cohort and will igonre your "
			"incidence_file.\n");
		args.incidence_file = "";
	}
	MedBootstrapResult m;

	//bootstrap params:
	m.bootstrap_params.loopCnt = args.nbootstrap;
	if (!args.cohort.empty()) {
		m.bootstrap_params.filter_cohort.clear();
		for (string& cohort : args.cohort)
			m.bootstrap_params.get_cohort_from_arg(cohort);
	}
	else if (!args.cohorts_file.empty()) {
		m.bootstrap_params.filter_cohort.clear();
		m.bootstrap_params.parse_cohort_file(args.cohorts_file);
	}

	//Sampling params
	m.bootstrap_params.sample_ratio = 1.0;
	m.bootstrap_params.sample_per_pid = args.sample_per_pid;
	m.bootstrap_params.sample_patient_label = args.sample_pid_label;
	m.bootstrap_params.sample_seed = args.sample_seed;
	m.bootstrap_params.simTimeWindow = args.sim_time_window;
	m.bootstrap_params.censor_time_factor = args.censor_time_factor;
	//ROC params:
	m.bootstrap_params.roc_Params.max_diff_working_point = args.max_diff_working_point;
	m.bootstrap_params.roc_Params.score_bins = args.score_bins;
	m.bootstrap_params.roc_Params.score_resolution = args.score_resolution;
	m.bootstrap_params.roc_Params.use_score_working_points = args.force_score_working_points;
	m.bootstrap_params.roc_Params.working_point_FPR = args.points_fpr;
	m.bootstrap_params.roc_Params.working_point_SENS = args.points_sens;
	m.bootstrap_params.roc_Params.working_point_PR = args.points_pr;
	m.bootstrap_params.roc_Params.working_point_TOPN = args.points_topn;
	m.bootstrap_params.roc_Params.working_point_auc = args.points_part_auc;
	m.bootstrap_params.roc_Params.working_point_Score = args.points_score;
	m.bootstrap_params.roc_Params.fix_label_to_binary = args.fix_label_to_binary;
	m.bootstrap_params.roc_Params.min_score_quants_to_force_score_wp = args.min_score_quants_to_force_score_wp;

	// Multiclass params
	vector<string> fields;
	boost::split(fields, args.multiclass_top_n, boost::is_any_of(","));
	if (!fields.empty()) 
		m.bootstrap_params.multiclass_params.top_n.clear();
	for (string& _n : fields)
		m.bootstrap_params.multiclass_params.top_n.push_back(stoi(_n));
	sort(m.bootstrap_params.multiclass_params.top_n.begin(), m.bootstrap_params.multiclass_params.top_n.end());
	if (!args.multi_class_dist_file.empty())
		m.bootstrap_params.multiclass_params.read_dist_matrix_from_file(args.multi_class_dist_file);
	m.bootstrap_params.multiclass_params.dist_name = boost::to_upper_copy(args.multi_class_dist_name);
	m.bootstrap_params.multiclass_params.do_class_auc = args.multi_class_auc;

	m.bootstrap_params.is_binary_outcome = args.fix_label_to_binary;
	//m.bootstrap_params.use_time_control_as_case
	if (!args.incidence_file.empty())
		m.bootstrap_params.roc_Params.inc_stats.read_from_text_file(args.incidence_file);

	//Read Input:
	MedSamples samples;
	MedFeatures features;
	map<string, vector<float>> additinal_sigs;
	MedMat<float> mat;
	switch (args.inp_type)
	{
	case Samples:
		samples.read_from_file(args.input);
		break;
	case Samples_Bin:
		samples.read_from_bin_file(args.input);
		break;
	case Features:
		features.read_from_file(args.input);
		break;
	case Features_Csv:
		features.read_from_csv_mat(args.input);
		break;
	case MedMat_Csv:
		mat.read_from_csv_file(args.input, 1);
		features.set_as_matrix(mat);
		break;
	default:
		MTHROW_AND_ERR("Unsupported type %d\n", args.inp_type);
	}

	MedFeatures *features_final = &features;

	MedModel mdl;
	MedPidRepository rep;
	switch (args.inp_type)
	{
	case Samples:
	case Samples_Bin:
		//Convert to MedFeatures:
		if (need_rep) {
			vector<int> pids_to_take;
			samples.get_ids(pids_to_take);
			init_model(mdl, rep, args, pids_to_take);

			if (mdl.learn(rep, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
				MTHROW_AND_ERR("Error creating age,gender for samples\n");
			features_final = &mdl.features;
		}
		else {
			//populate features:
			features.init_all_samples(samples.idSamples);
			features.set_time_unit(samples.time_unit);
			//no additional signals!
		}

		break;
	case Features:
	case Features_Csv:
		if (!args.json_model.empty()) {
			unordered_set<int> ids;
			for (size_t i = 0; i < features.samples.size(); ++i) {
				if (ids.find(features.samples[i].id) == ids.end()) { //start new pid
					MedIdSamples new_smp(features.samples[i].id);
					samples.idSamples.push_back(new_smp);
				}
				samples.idSamples.back().samples.push_back(features.samples[i]);

				ids.insert(features.samples[i].id);
			}
			vector<int> pids_to_take(ids.begin(), ids.end());
			init_model(mdl, rep, args, pids_to_take);

			if (mdl.apply(rep, samples, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
				MTHROW_AND_ERR("Error creating age,gender for samples\n");
			features_final = &mdl.features;
			//add old loaded features in mat:
			for (auto it = features.data.begin(); it != features.data.end(); ++it)
				features_final->data[it->first].swap(it->second); //it may "steal" the memory of loaded feature
		}
		break;
	default:
		break;
	}
	m.bootstrap_params.clean_feature_name_prefix(features_final->data);
	//load weights if given:
	if (!args.weights_file.empty()) {
		MLOG("Loading bootstrap weights from %s\n", args.weights_file.c_str());
		vector<float> bootstrap_weights;
		if (!boost::starts_with(args.weights_file, "attr:"))
			read_weights_file(args.weights_file, bootstrap_weights);
		else
			read_weights_samples(args.weights_file.substr(5), bootstrap_weights, features_final->samples);
		features_final->weights.swap(bootstrap_weights);
		if (features_final->weights.size() != features_final->samples.size())
			MTHROW_AND_ERR("Error input has %zu records, and weights has %zu records\n",
				features_final->samples.size(), features_final->weights.size());
		medial::print::print_hist_vec(features_final->weights, "bootstrap_weights", "%2.4f");
	}
	else if (args.control_weight > 0) {
		MLOG("USING CONTROL_WEIGHTS=%f\n", args.control_weight);
		features_final->weights.resize(features_final->samples.size(), 1);
		for (size_t i = 0; i < features_final->samples.size(); ++i)
			if (features_final->samples[i].outcome <= 0)
				features_final->weights[i] = args.control_weight;
	}

	if (args.pred_ind != "")
	{
		// in multiclass, remove rows with different outcomes, and pick to correct pred.
		vector<int> selected, notSelected;
		for (size_t samp_ind = 0; samp_ind < features_final->samples.size(); samp_ind++)
		{
			float total_predict_prob = 0;
			for (auto ind : args.pred_ind_set)
			{
				if (features_final->samples[samp_ind].prediction.size() <= ind)
				{
					MTHROW_AND_ERR("Number of predictions is smaller than prediction ind \n");
				}

				total_predict_prob += features_final->samples[samp_ind].prediction[ind];
			}
			features_final->samples[samp_ind].prediction = { total_predict_prob };
			if ((features_final->samples[samp_ind].outcome == 0) || (args.pred_ind_set.find(features_final->samples[samp_ind].outcome) != args.pred_ind_set.end()))
			{
				// always pick 0 (control) and another prediction column
				selected.push_back((int)samp_ind);
			}
		}

		medial::process::filter_row_indexes(*features_final, selected);
	}

	if (!args.fetch_score_from_feature.empty()) {
		//check we can find the feature
		vector<string> all_data_names;
		features_final->get_feature_names(all_data_names);
		int feature_idx = find_in_feature_names(all_data_names, args.fetch_score_from_feature, false);
		if (feature_idx < 0) {
			MERR("Error - when given fetch_score_from_feature - the feature most exists in matrix\n");
			find_in_feature_names(all_data_names, args.fetch_score_from_feature, true);
		}
		const vector<float> &new_pred = features_final->data.at(all_data_names[feature_idx]);
		if (new_pred.size() != features_final->samples.size())
			MTHROW_AND_ERR("Error feature is not calclated correctly and not same size of samples\n");
		for (size_t i = 0; i < features_final->samples.size(); ++i)
			features_final->samples[i].prediction = { new_pred[i] };
		MLOG("Took %s instead of score\n", args.fetch_score_from_feature.c_str());
	}

	if (args.debug) {
		MLOG("Feature Names availible for cohort filtering:\n");
		for (auto it = features_final->data.begin(); it != features_final->data.end(); ++it)
			MLOG("%s\n", it->first.c_str());
		MLOG("Time-Window\n");
		MLOG("Label\n");
		MLOG("\n");
	}
	//check cohort file errors:
	vector<string> param_use;
	if (!args.cohorts_file.empty()) {
		get_cohort_params_use(m.bootstrap_params, param_use);
		unordered_set<string> valid_params;
		valid_params.insert("Time-Window");
		valid_params.insert("Label");
		for (auto it = features_final->data.begin(); it != features_final->data.end(); ++it)
			valid_params.insert(it->first);
		vector<string> all_names_ls(valid_params.begin(), valid_params.end());

		bool all_valid = true;
		for (string param_name : param_use)
			if (valid_params.find(param_name) == valid_params.end()) {
				//try and fix first:
				int fn_pos = find_in_feature_names(all_names_ls, param_name, false);
				if (fn_pos < 0) {
					all_valid = false;
					MERR("ERROR:: Wrong use in \"%s\" as filter params. the parameter is missing\n", param_name.c_str());
				}
				else {
					//fix name:
					string found_nm = all_names_ls[fn_pos];
					MLOG("Mapped %s => %s\n", param_name.c_str(), found_nm.c_str());
					for (auto &it_cohort : m.bootstrap_params.filter_cohort)
					{
						vector<Filter_Param> &vec = it_cohort.second;
						for (Filter_Param &pp : vec)
							if (pp.param_name == param_name)
								pp.param_name = found_nm;
					}
				}
			}

		if (!all_valid) {
			if (!args.debug) {
				MLOG("Feature Names availible for cohort filtering:\n");
				for (auto it = features_final->data.begin(); it != features_final->data.end(); ++it)
					MLOG("%s\n", it->first.c_str());
				MLOG("Time-Window\n");
				MLOG("\n");
			}
			MTHROW_AND_ERR("Cohort file has wrong paramter names. look above for all avaible params\n");
		}
	}

	//whitelist, blacklist:
	unordered_set<int> white(args.whitelist_ids.begin(), args.whitelist_ids.end());
	unordered_set<int> black(args.blacklist_ids.begin(), args.blacklist_ids.end());
	MedFeatures filtered_ids;
	if (!white.empty() || !black.empty() ||
		args.sample_min_year > 0 || args.sample_max_year > 0) {
		filtered_ids.time_unit = features_final->time_unit;
		filtered_ids.attributes = features_final->attributes;
		int original_size = (int)features_final->samples.size();
		for (size_t i = 0; i < features_final->samples.size(); ++i)
		{
			int pred_year = int(features_final->samples[i].time / 10000);
			if ((white.empty() || white.find(features_final->samples[i].id) != white.end())
				&& (black.empty() || black.find(features_final->samples[i].id) == black.end()) &&
				(args.sample_min_year <= 0 || pred_year >= args.sample_min_year) &&
				(args.sample_max_year <= 0 || pred_year <= args.sample_max_year)) {
				filtered_ids.samples.push_back(features_final->samples[i]);
				for (auto it = features_final->data.begin(); it != features_final->data.end(); ++it)
					filtered_ids.data[it->first].push_back(it->second[i]);
				if (!features_final->weights.empty())
					filtered_ids.weights.push_back(features_final->weights[i]);
			}

		}
		filtered_ids.init_pid_pos_len();
		features_final = &filtered_ids;
		MLOG("Done Filtering blacklist\\whitelist  of ids and sample_min_date-sample_max_date."
			" left with %d samples out of %d\n",
			(int)features_final->samples.size(), original_size);
	}

	//censor if needed:
	if (args.use_censor && !args.rep.empty()) {
		MLOG("Censoring..\n");
		if (rep.all_pids_list.empty()) {
			vector<string> sigs = { "Censor" };
			unordered_set<int> pids_u;
			for (size_t i = 0; i < features_final->samples.size(); ++i)
				pids_u.insert(features_final->samples[i].id);
			vector<int> pids_to_take(pids_u.begin(), pids_u.end());

			int curr_level = global_logger.levels.front();
			global_logger.init_all_levels(LOG_DEF_LEVEL);
			if (rep.read_all(args.rep, pids_to_take, sigs) < 0)
				MTHROW_AND_ERR("ERROR could not read repository %s\n", args.rep.c_str());
			global_logger.init_all_levels(curr_level);
		}
		unordered_map<int, int> censor_dates;
		for (int pid : rep.all_pids_list)
		{
			UniversalSigVec usv_censor;
			rep.uget(pid, "Censor", usv_censor);
			for (int i = usv_censor.len - 1; i >= 0; --i)
				if (int(int(usv_censor.Val(i)) / 1000) == 2 &&
					(censor_dates.find(pid) == censor_dates.end())) {
					censor_dates[pid] = usv_censor.Time(i);
					break;
				}
		}

		m.bootstrap_params.apply_censor(censor_dates, *features_final);
		MLOG("Done Censoring!\n");
	}
	MedFeatures features_fixed;

	//autosim if needed:
	if (args.do_autosim) {
		m.bootstrap_params.change_sample_autosim(*features_final, args.min_time, args.max_time, features_fixed);
		features_final = &features_fixed;
	}

	Regression_Params reg_params;
	if (args.measurement_type != "") {
		vector<string> measures_tokens;
		boost::split(measures_tokens, args.measurement_type, boost::is_any_of(",;"));

		m.bootstrap_params.measurements_with_params.resize(measures_tokens.size());
		for (size_t i = 0; i < measures_tokens.size(); ++i)
		{


			MeasurmentFunctionType measure_type = m.bootstrap_params.measurement_function_name_to_type(measures_tokens[i]);
			if (measure_type == MeasurmentFunctionType::calc_roc_measures_with_inc)
				m.bootstrap_params.measurements_with_params[i] = pair<MeasurementFunctions, Measurement_Params*>(calc_roc_measures_with_inc, NULL); // should add supprt for params instead of NULL
			else if (measure_type == MeasurmentFunctionType::calc_only_auc)
				m.bootstrap_params.measurements_with_params[i] = pair<MeasurementFunctions, Measurement_Params*>(calc_only_auc, NULL); // should add supprt for params instead of NULL
			else if (measure_type == MeasurmentFunctionType::calc_npos_nneg)
				m.bootstrap_params.measurements_with_params[i] = pair<MeasurementFunctions, Measurement_Params*>(calc_npos_nneg, NULL); // should add supprt for params instead of NULL
			else if (measure_type == MeasurmentFunctionType::calc_multi_class)
			{
				if (features_final->samples.empty() || features_final->samples[0].prediction.empty())
					MTHROW_AND_ERR("not good: samples are in size: %d, prediction is of size: %d \n", (int)features_final->samples.size(), (int)features_final->samples[0].prediction.size());

				size_t n_categ = features_final->samples[0].prediction.size();
				m.bootstrap_params.multiclass_params.init_from_string("n_categ=" + to_string(n_categ));
				m.bootstrap_params.measurements_with_params[i] = pair<MeasurementFunctions, Measurement_Params*>(calc_multi_class, &m.bootstrap_params.multiclass_params); // should add supprt for params instead of NULL
				m.bootstrap_params.sort_preds_in_multicategory = true;
				m.bootstrap_params.is_binary_outcome = false;
			}
			else if (measure_type == MeasurmentFunctionType::calc_kandel_tau)
				m.bootstrap_params.measurements_with_params[i] = pair<MeasurementFunctions, Measurement_Params*>(calc_kandel_tau, NULL); // should add supprt for params instead of NULL
			else if (measure_type == MeasurmentFunctionType::calc_harrell_c_statistic) {
				//manipulate outcome:
				for (MedSample &sample : features_final->samples)
				{
					if (sample.outcome > 0)
						sample.outcome = medial::repository::DateDiff(sample.time, sample.outcomeTime);
					else
						sample.outcome = -medial::repository::DateDiff(sample.time, sample.outcomeTime);
				}
				m.bootstrap_params.measurements_with_params[i] = pair<MeasurementFunctions, Measurement_Params*>(calc_harrell_c_statistic, NULL); // should add supprt for params instead of NULL
			}
			else if (measure_type == MeasurmentFunctionType::calc_regression) {
				reg_params.do_logloss = true;
				m.bootstrap_params.measurements_with_params[i] =
					pair<MeasurementFunctions, Measurement_Params*>(calc_regression, &reg_params); // should add supprt for params instead of NULL
			}
			else
				MTHROW_AND_ERR("Error - unknown Measurement type %d\n", (int)measure_type);

			if (i == 0 && !args.general_measurements_args.empty()) 
				m.bootstrap_params.measurements_with_params[i].second->init_from_string(args.general_measurements_args);
		}
	}


	if (args.sim_time_window && args.registry_path.empty())
		MWARN("WARNING :: using sim time window without registry_path - may sample"
			" samples that should be censored\n");

	map<int, map<string, map<string, float>>> results_per_split;
	map<int, map<string, map<string, float>>> *results_per_split_p = NULL;
	if (args.use_splits)
		results_per_split_p = &results_per_split;
	with_registry_args reg_args;
	with_registry_args *reg_args_p = NULL;
	MedRegistry registry, registry_censor;
	if (!args.registry_path.empty())
	{
		reg_args.do_kaplan_meir = args.do_kaplan_meir;
		reg_args.json_model = args.json_model;
		reg_args.rep_path = args.rep;
		reg_args.sampler = (MedSamplingYearly *)MedSamplingStrategy::make_sampler("yearly",
			args.incidence_sampling_args);
		reg_args.labeling_params = args.labeling_params;
		registry.read_text_file(args.registry_path);
		if (!args.censoring_registry_path.empty()) {
			registry_censor.read_text_file(args.censoring_registry_path);
			reg_args.registry_censor = &registry_censor;
		}
		else if (!args.censoring_signal.empty()) {
			MLOG("Reading censor registry from signal %s\n", args.censoring_signal.c_str());
			vector<int> all_pids;
			vector<string> sigs_read = { args.censoring_signal };
			if (rep.read_all(args.rep, all_pids, sigs_read) < 0)
				MTHROW_AND_ERR("Error reading repository %s\n", args.rep.c_str());
			int sid = rep.sigs.sid(args.censoring_signal);
			if (rep.sigs.Sid2Info[sid].n_time_channels != 2)
				MTHROW_AND_ERR("Error signal %s should have 2 time channels, has %d\n",
					args.censoring_signal.c_str(), rep.sigs.Sid2Info[sid].n_time_channels);
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
					registry_censor.registry_records.push_back(rec);
				}
			}
			reg_args.registry_censor = &registry_censor;
		}
		reg_args.registry = &registry;
		reg_args_p = &reg_args;
	}

	if (!args.exclude_controls_without_followup) {
		// If we don't want to exclude controls without enough followup time, we add 100 years to their outcome time
		for (auto & sample : features_final->samples)
		{
			if (sample.outcome <= 0.0)
				sample.outcomeTime = medial::repository::DateAdd(sample.outcomeTime, 36500);
		}
	}

	m.bootstrap(*features_final, results_per_split_p, reg_args_p);
	if (!args.registry_path.empty())
		delete reg_args.sampler;

	//output:
	if (args.output_all_formats && args.output != "/dev/null") {
		m.write_to_file(args.output + ".bin");
		MLOG("Wrote binary object [%s]\n", (args.output + ".bin").c_str());
	}
	if (!m.bootstrap_results.empty()) {
		if (args.output != "/dev/null") {
			if (args.output_all_formats) {
				m.write_results_to_text_file(args.output + ".txt", false, args.run_id);
				MLOG("Wrote [%s]\n", (args.output + ".txt").c_str());
			}
			m.write_results_to_text_file(args.output + ".pivot_txt", true, args.run_id);
			MLOG("Wrote [%s]\n", (args.output + ".pivot_txt").c_str());
		}
	}
	else
		MWARN("Warning: No cohort results - skipped all.\n");

	if (args.use_splits) {
		for (auto& splitRes : results_per_split) {
			if (splitRes.first != -1) {
				if (args.output != "/dev/null") {
					if (args.output_all_formats) {
						write_bootstrap_results(args.output + ".split" + to_string(splitRes.first) + ".txt", splitRes.second, args.run_id);
						MLOG("Wrote [%s]\n", (args.output + ".split" + to_string(splitRes.first) + ".txt").c_str());
					}
					write_pivot_bootstrap_results(args.output + ".split" + to_string(splitRes.first) + ".pivot_txt", splitRes.second, args.run_id);
					MLOG("Wrote [%s]\n", (args.output + ".split" + to_string(splitRes.first) + ".pivot_txt").c_str());
				}
			}
		}
	}

	// Currently - raw output not implemented per split
	if (!args.print_graphs_path.empty() || args.output_raw) {
		vector<float> preds, y;
		vector<int> pids;
		map<string, vector<float>> data;

		vector<vector<float>> all_preds;
		vector<vector<float>> all_y;
		vector<vector<float>> all_w;
		vector<vector<float>> all_pids;
		vector<string> model_names;
		unordered_set<string> param_use_set(param_use.begin(), param_use.end());
		vector<int> preds_order;
		m.bootstrap_params.prepare_bootstrap(*features_final, preds, y, pids, data, preds_order);

		ofstream raw_file;
		if (args.output_raw) {
			raw_file.open(args.output + ".Raw");
			if (!raw_file.good())
				MTHROW_AND_ERR("IO Error: can't write \"%s\"\n", (args.output + ".Raw").c_str());
			raw_file << "cohort_name" << "\t" << "prediction" << "\t" << "label" << "\t" << "pid"
				<< "\t" << "prediction_time" << "\t" << "outcome_time" << "\t" << "split";
			if (!features_final->weights.empty())
				raw_file << "\t" << "weight";

			if (args.debug)
				for (auto it = data.begin(); it != data.end(); it++)
					if (param_use_set.find(it->first) != param_use_set.end())
						raw_file << "\t" << it->first;
			raw_file << endl;
		}
		unordered_map<int, vector<MedRegistryRecord *>> pid_to_reg, pid_to_censor;
		MedRegistry registry, censor_reg;
		if (m.bootstrap_params.simTimeWindow && (!args.registry_path.empty())) {
			registry.read_text_file(args.registry_path);
			for (size_t i = 0; i < registry.registry_records.size(); ++i)
				pid_to_reg[registry.registry_records[i].pid].push_back(&registry.registry_records[i]);
			if (!args.censoring_registry_path.empty()) {
				censor_reg.read_text_file(args.censoring_registry_path);
				for (size_t i = 0; i < registry.registry_records.size(); ++i)
					pid_to_censor[censor_reg.registry_records[i].pid].push_back(&censor_reg.registry_records[i]);
			}
		}
		for (auto it = m.bootstrap_params.filter_cohort.begin(); it != m.bootstrap_params.filter_cohort.end(); ++it)
		{
			vector<float> *y_changed = &y;
			map<string, vector<float>> *data_changed = &data;
			vector<float> y_new;
			map<string, vector<float>> cp_info;
			vector<int> outcome_time_vec;
			vector<int> selected_rows;
			vector<MedRegistryRecord *> empty_arr;
			if (args.sim_time_window) {
				Filter_Param time_filter;
				time_filter.param_name = "";
				for (size_t i = 0; i < it->second.size(); ++i)
					if (it->second[i].param_name == "Time-Window")
					{
						time_filter = it->second[i];
						break;
					}

				map<string, FilterCohortFunc> cohorts_t;
				map<string, void *> cohort_params_t;

				outcome_time_vec.resize(y.size());
				selected_rows.reserve(y_changed->size());
				for (size_t i = 0; i < y_changed->size(); ++i)
				{
					outcome_time_vec[i] = features_final->samples[i].outcomeTime;
					if (y[i] <= 0 || time_filter.param_name.empty()) {
						selected_rows.push_back((int)i);
						continue;
					}
					int time_df = (int)data["Time-Window"][i]; //time to turn into case
					if (time_df > time_filter.max_range) {
						//search for intersection:
						const vector<MedRegistryRecord *> *reg_censor = &empty_arr;
						if (pid_to_censor.find(features_final->samples[i].id) != pid_to_censor.end())
							reg_censor = &pid_to_censor[features_final->samples[i].id];
						bool is_legal = reg_censor->empty();
						for (size_t k = 0; k < reg_censor->size(); ++k)
						{
							//only controls
							int diff_to_allowed = int(365 * (medial::repository::DateDiff(features_final->samples[i].time,
								(*reg_censor)[k]->end_date)));
							if (diff_to_allowed >= time_filter.max_range && features_final->samples[i].time >= (*reg_censor)[k]->start_date) {
								is_legal = true;
								outcome_time_vec[i] = (*reg_censor)[k]->end_date;
								break;
							}
						}
						if (is_legal)
							selected_rows.push_back((int)i); //add if legal
					}
					else
						selected_rows.push_back((int)i);
				}

				medial::process::make_sim_time_window(it->first, it->second, y, data,
					y_new, cp_info, cohorts_t, cohort_params_t, m.bootstrap_params.censor_time_factor);
				y_changed = &y_new;
				data_changed = &cp_info;
			}
			all_preds.push_back(vector<float>());
			all_y.push_back(vector<float>());
			all_w.push_back(vector<float>());
			all_pids.push_back(vector<float>());
			string cohort_name = it->first;
			model_names.push_back(cohort_name);
			vector<Filter_Param> *filt = &it->second;
			void *params = filt;
			if (selected_rows.empty()) {
				for (size_t i = 0; i < y_changed->size(); ++i)
					if (filter_range_params(*data_changed, (int)i, params)) {
						if (args.output_raw) {
							raw_file << cohort_name << "\t" << preds[i] << "\t" << (*y_changed)[i]
								<< "\t" << pids[i] << "\t" << features_final->samples[i].time
								<< "\t" << features_final->samples[i].outcomeTime
								<< "\t" << features_final->samples[i].split;
							if (!features_final->weights.empty())
								raw_file << "\t" << features_final->weights[i];

							if (args.debug)
								for (auto it = data_changed->begin(); it != data_changed->end(); it++)
									if (param_use_set.find(it->first) != param_use_set.end())
										raw_file << "\t" << it->second[i];
							raw_file << "\n";
						}
						all_preds.back().push_back(preds[i]);
						all_y.back().push_back((*y_changed)[i]);
						all_pids.back().push_back(pids[i]);
						if (!features_final->weights.empty())
							all_w.back().push_back(features_final->weights[i]);
					}
			}
			else {
				for (size_t ii = 0; ii < selected_rows.size(); ++ii) {
					int i = selected_rows[ii];
					if (filter_range_params(*data_changed, i, params)) {
						if (args.output_raw) {
							raw_file << cohort_name << "\t" << preds[i] << "\t" << (*y_changed)[i]
								<< "\t" << pids[i] << "\t" << features_final->samples[i].time
								<< "\t" << outcome_time_vec[i]
								<< "\t" << features_final->samples[i].split;
							if (!features_final->weights.empty())
								raw_file << "\t" << features_final->weights[i];
							if (args.debug)
								for (auto it = data_changed->begin(); it != data_changed->end(); it++)
									if (param_use_set.find(it->first) != param_use_set.end())
										raw_file << "\t" << it->second[i];
							raw_file << "\n";
						}
						all_preds.back().push_back(preds[i]);
						all_y.back().push_back((*y_changed)[i]);
						all_pids.back().push_back(pids[i]);
						if (!features_final->weights.empty())
							all_w.back().push_back(features_final->weights[i]);
					}
				}
			}

		}
		if (args.output_raw) {
			raw_file.flush();
			raw_file.close();
			MLOG("Wrote Raw file into %s\n", (args.output + ".Raw").c_str());
		}

		if (!args.print_graphs_path.empty()) {
			int max_plots = 10;
			random_device rd;
			mt19937 rnd_generator(rd());
			for (int i = (int)all_preds.size() - 1; i >= 0; --i)
			{
				//filter per pid if needed from all_pids:
				if (args.sample_per_pid > 0) { //need to do the filtering:
					vector<int> final_selected_idx;
					unordered_map<int, vector<int>> pid_to_index;
					for (int j = 0; j < all_pids[i].size(); ++j)
						pid_to_index[all_pids[i][j]].push_back(j);
					//do random selection for each patient:
					for (const auto &it : pid_to_index)
					{
						const vector<int> &opt_idx = it.second;
						uniform_int_distribution<> rnd_num(0, (int)opt_idx.size() - 1);
						for (size_t k = 0; k < args.sample_per_pid; ++k)
							final_selected_idx.push_back(opt_idx[rnd_num(rnd_generator)]);
					}

					//commit selection with repeats of final_selected_idx to : all_preds[i], all_y[i], all_w[i]:
					vector<float> preds_select(final_selected_idx.size()), y_selected(final_selected_idx.size()), w_selected;
					if (!all_w[i].empty())
						w_selected.resize(final_selected_idx.size());
					for (size_t j = 0; j < final_selected_idx.size(); ++j)
					{
						preds_select[j] = all_preds[i][final_selected_idx[j]];
						y_selected[j] = all_y[i][final_selected_idx[j]];
						if (!all_w[i].empty())
							w_selected[j] = all_w[i][final_selected_idx[j]];
					}

					all_y[i] = move(y_selected);
					all_preds[i] = move(preds_select);
					all_w[i] = move(w_selected);
				}

				if (!valid_cohort(all_y[i])) {
					MWARN("Skiping plot of empty cohort or missing cases/controls \"%s\"\n", model_names[i].c_str());
					all_preds.erase(all_preds.begin() + i);
					all_y.erase(all_y.begin() + i);
					all_w.erase(all_w.begin() + i);
					model_names.erase(model_names.begin() + i);
				}
			}
			if (model_names.size() > max_plots) {
				MWARN("WARN: more than %d cohorts available(%zu). prints only firsts\n", max_plots, model_names.size());
				all_preds.resize(max_plots);
				all_y.resize(max_plots);
				all_w.resize(max_plots);
				model_names.resize(max_plots);
			}
			plotAUC(all_preds, all_y, all_w, model_names, args.print_graphs_path);


		}


	}

	return 0;
}

