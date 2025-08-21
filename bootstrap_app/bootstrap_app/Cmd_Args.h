#ifndef __PROGRAM__ARGS__H__
#define __PROGRAM__ARGS__H__

#include <boost/program_options.hpp>
#include <boost/spirit/home/support/detail/hold_any.hpp>
#include <boost/algorithm/string.hpp>
#include <string>
#include <vector>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <Logger/Logger/Logger.h>
#include <MedUtils/MedUtils/MedUtils.h>
#include <MedUtils/MedUtils/LabelParams.h>
#include <MedStat/MedStat/MedBootstrap.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

namespace po = boost::program_options;
using namespace std;

enum Input_types {
	Samples = 1,
	Features = 2,
	Samples_Bin = 3,
	Features_Csv = 4,
	MedMat_Csv = 5
};

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	unordered_map<string, int> conv_map = {
		{ "samples", Samples }
		,{ "samples_bin", Samples_Bin }
		,{ "features", Features }
		,{ "features_csv", Features_Csv }
		,{ "medmat_csv", MedMat_Csv }
	};
	string input_type; //may be "samples, features, samples_bin"
	string working_points_sens, working_points_fpr, working_points_pr, working_points_score, working_points_topn;
	string part_auc_params;
	string blacklist_ids_file, whitelist_ids_file;
	string labeling_params_s;

	void convert_type() {
		if (conv_map.find(input_type) == conv_map.end())
			MTHROW_AND_ERR("couldn't find \"%s\" type. legal types are: %s\n", input_type.c_str(),
				medial::io::get_list(conv_map).c_str());
		inp_type = Input_types(conv_map[input_type]);
	}

	void parse_pred_ind() {
		vector<string> pred_inds;
		boost::trim(pred_ind);
		if (!pred_ind.empty())
			boost::split(pred_inds, pred_ind, boost::is_any_of(","));

		for (string s : pred_inds)
			pred_ind_set.insert(stoi(s));
	}

	void parse_working_points() {
		vector<string> sens;
		boost::trim(working_points_sens);
		boost::trim(working_points_fpr);
		boost::trim(working_points_pr);
		boost::trim(working_points_score);
		boost::trim(working_points_topn);
		boost::trim(part_auc_params);

		if (!working_points_sens.empty())
			boost::split(sens, working_points_sens, boost::is_any_of(","));
		points_sens.reserve((int)sens.size());
		for (string s : sens)
			points_sens.push_back(stof(s));
		sort(points_sens.begin(), points_sens.end());

		vector<string> fpr;
		if (!working_points_fpr.empty())
			boost::split(fpr, working_points_fpr, boost::is_any_of(","));
		points_fpr.reserve((int)fpr.size());
		for (string s : fpr)
			points_fpr.push_back(stof(s));
		sort(points_fpr.begin(), points_fpr.end());

		vector<string> pr;
		if (!working_points_pr.empty())
			boost::split(pr, working_points_pr, boost::is_any_of(","));
		points_pr.reserve((int)pr.size());
		for (string s : pr)
			points_pr.push_back(stof(s));
		sort(points_pr.begin(), points_pr.end());

		vector<string> scores;
		if (!working_points_score.empty())
			boost::split(scores, working_points_score, boost::is_any_of(","));
		points_score.reserve((int)scores.size());
		for (string s : scores)
			points_score.push_back(stof(s));
		sort(points_score.begin(), points_score.end());

		vector<string> topn;
		if (!working_points_topn.empty())
			boost::split(topn, working_points_topn, boost::is_any_of(","));
		points_topn.reserve((int)topn.size());
		for (string s : topn)
			points_topn.push_back(stoi(s));
		sort(points_topn.begin(), points_topn.end());
		
		vector<string> part_auc;
		if (!part_auc_params.empty())
			boost::split(part_auc, part_auc_params, boost::is_any_of(","));
		points_part_auc.reserve((int)part_auc.size());
		for (string s : part_auc)
			points_part_auc.push_back(stof(s));
		sort(points_part_auc.begin(), points_part_auc.end());
		if (!points_part_auc.empty()) {
			if (points_part_auc[0] <= 0 || points_part_auc.back() > 1)
				MTHROW_AND_ERR("Illegal partial AUC params : %s\n", part_auc_params.c_str());
		}
	}
	void parse_lists() {

		string line;
		if (!blacklist_ids_file.empty()) {
			ifstream fr(blacklist_ids_file);
			if (!fr.good())
				MTHROW_AND_ERR("IO Error: can't read \"%s\"\n", blacklist_ids_file.c_str());
			while (getline(fr, line)) {
				if (line.empty() || boost::starts_with(line, "#"))
					continue;
				blacklist_ids.push_back(stoi(line));
			}
			fr.close();
		}
		if (!whitelist_ids_file.empty()) {
			ifstream fr(whitelist_ids_file);
			if (!fr.good())
				MTHROW_AND_ERR("IO Error: can't read \"%s\"\n", whitelist_ids_file.c_str());
			while (getline(fr, line)) {
				if (line.empty() || boost::starts_with(line, "#"))
					continue;
				whitelist_ids.push_back(stoi(line));
			}
			fr.close();
		}
	}

	void post_process() {
		convert_type();
		parse_lists();

		if (do_autosim && (min_time == -1 || max_time == -1))
			MTHROW_AND_ERR("please min_time,max_time for autosim mode\n");
		if (working_points_sens.empty() && working_points_fpr.empty() && working_points_pr.empty() && working_points_score.empty()
			&& working_points_topn.empty())
			working_points_fpr = "0.1,1,5,10,20,30,40,50,55,60,65,70,75,80,85,90,95";
		parse_working_points();
		parse_pred_ind();
		if (!labeling_params_s.empty())
			labeling_params.init_from_string(labeling_params_s);

		if (output == "/dev/null")
			output_raw = false;
	}

public:
	string rep; ///<the repository if needed for age\gender cohorts
	string input; ///< the location to read input
	Input_types inp_type; ///< the input typeplease reffer to Input_types enum for options
	string output; ///< the location to write output
	string incidence_file; ///< incidence file path
	string json_model; ///< json model for creating features for the filtering of cohorts in bootstrap
	vector<string> train_test_json_alt; ///< alteration for the json model for creating features for the filtering of cohorts in bootstrap format: TBD!
	string registry_path; ///< the registry from_to path to calc accurate incidence by samplings (slower)
	string censoring_registry_path; ///< the registry from_to path to when giving registry_path to censor records in sampling
	string censoring_signal; ///< the registry from_to signal to when giving registry_path to censor records in sampling
	LabelParams labeling_params; ///< how to label from registry, please reffer to LabelParams type
	string incidence_sampling_args; ///< the init argument string for the MedSamplingAge for the sampling. has default
	bool do_kaplan_meir; ///< calcing incidence in kaplan meir manar
	string weights_file;
	float control_weight; ///< used when controls were down sampled to weight them in the bootstrap
	string fetch_score_from_feature; ///< Only if given and the input is matrix (or matrix after json_model) - it will override pred_0 with this feature

	int nbootstrap;
	int sample_per_pid;
	bool sample_pid_label;
	int sample_seed;
	string cohorts_file;
	vector<string> cohort;
	float score_resolution;
	int score_bins;
	bool fix_label_to_binary;
	bool exclude_controls_without_followup;
	float max_diff_working_point;
	int min_score_quants_to_force_score_wp;
	bool force_score_working_points;
	vector<float> points_sens, points_fpr, points_pr, points_score;
	vector<float> points_part_auc;
	vector<int> points_topn;
	unordered_set<int> pred_ind_set;
	vector<int> whitelist_ids, blacklist_ids;
	bool do_autosim;
	float censor_time_factor;
	int min_time, max_time;
	bool use_censor;
	bool output_raw;
	bool use_splits;
	bool sim_time_window;
	int sample_min_year, sample_max_year;
	string print_graphs_path;
	string run_id;
	string pred_ind;
	bool output_all_formats; ///< if true will also print old format and binary format
	string measurement_type; ///< what measure to perform
	string multiclass_top_n;
	string multi_class_dist_name;
	string multi_class_dist_file;
	bool multi_class_auc;
	string general_measurements_args;


	string bootstrap_logo = "\
####                  #             #                         \n\
 #  #                 #             #                         \n\
 #  #   ###    ###   ####    ###   ####   # ##    ###   # ##  \n\
 ###   #   #  #   #   #     #       #     ##  #      #  ##  # \n\
 #  #  #   #  #   #   #      ###    #     #       ####  ##  # \n\
 #  #  #   #  #   #   #  #      #   #  #  #      #   #  # ##  \n\
####    ###    ###     ##   ####     ##   #       ####  #   \n\
                                                        #     \n\
                                                        #";

	ProgramArgs() {
		unsigned int row_size = (unsigned int)po::options_description::m_default_line_length;
		po::options_description desc("Program Modes", row_size * 2, row_size);
		string option_ls = "the input type (" + medial::io::get_list(conv_map) + ")";

		po::options_description input_output("IO options", row_size * 2, row_size);
		input_output.add_options()
			("rep", po::value<string>(&rep), "the repository if needed for age\\gender cohorts")
			("input_type", po::value<string>(&input_type)->default_value("samples"), option_ls.c_str())
			("input", po::value<string>(&input)->required(), "the location to read input")
			("pred_ind", po::value<string>(&pred_ind)->default_value(""), "prediction column index - for multiclass prediction. (Should be > 0)")
			("weights_file", po::value<string>(&weights_file)->default_value(""), "a file with weights for the input - in the same order of input. or use \"attr:\" prefix to search attribute in samples")
			("control_weight", po::value<float>(&control_weight)->default_value(-1), "If given >0 will use this to weight controls")
			("cohorts_file", po::value<string>(&cohorts_file), "cohorts definition file")
			("cohort", po::value<vector<string>>(&cohort)->composing(), "run the analysis on this single cohort (e.g Time-Window:0,365;Age:40,80). will override --cohorts_file")
			("json_model", po::value<string>(&json_model), "json model for creating features for the filtering of cohorts in bootstrap")
			("fetch_score_from_feature", po::value<string>(&fetch_score_from_feature)->default_value(""), "Only if given and the input is matrix (or matrix after json_model) - it will override pred_0 with this feature")
			("train_test_json_alt", po::value<vector<string>>(&train_test_json_alt)->composing(), "(multiple) alterations to model json file")
			("print_graphs_path", po::value<string>(&print_graphs_path)->default_value(""), "the graphs path. if empty, won't print graphd")
			("output_raw", po::bool_switch(&output_raw), "flag to output bootstrap filtering of label,score to output")
			("output_all_formats", po::value<bool>(&output_all_formats)->default_value(false), "If true will output and save also old format(no pivot) and binary serialized format")
			("output", po::value<string>(&output)->required(), "the location to write output")
			;

		po::options_description inc_args("Incidence options", row_size * 2, row_size);
		inc_args.add_options()
			("incidence_file", po::value<string>(&incidence_file), "the location to load incidence file")
			("registry_path", po::value<string>(&registry_path)->default_value(""), "the registry from_to path to calc accurate incidence by samplings (slower)")
			("censoring_registry_path", po::value<string>(&censoring_registry_path)->default_value(""), "path to censoring registry if given registry_path to censor samples in incidence file")
			("censoring_signal", po::value<string>(&censoring_signal)->default_value(""), "the signal to censoring registry if given registry_path to censor samples in incidence file")
			("labeling_params", po::value<string>(&labeling_params_s)->default_value("conflict_method=max;label_interaction_mode=0:within,all|1:before_start,after_start;censor_interaction_mode=all:within,all"), "how to label from registry, please reffer to LabelParams type")
			("incidence_sampling_args", po::value<string>(&incidence_sampling_args)->default_value("start_time=20070101;end_time=20140101;time_jump=1;time_jump_unit=Year;time_range_unit=Date"), "the init argument string for the MedSamplingYearly for the sampling. has default")
			("do_kaplan_meir", po::value<bool>(&do_kaplan_meir)->default_value(true), "if to use kaplan meir calculation for incidence by registry (recommand to used always but specially when time window is large)")
			;

		string metrics_options = medial::io::get_list(MedBootstrap::measurement_function_name_map, ",");

		po::options_description bootstrap_opts("Bootstrap options", row_size * 2, row_size);
		bootstrap_opts.add_options()
			("nbootstrap", po::value<int>(&nbootstrap)->default_value(500), "bootstrap loop count")
			("fix_label_to_binary", po::value<bool>(&fix_label_to_binary)->default_value(true), "If given will treat labels as label=outcome>0")
			;

		po::options_description measurement_options("Bootstrap Metrics/Measurements options", row_size * 2, row_size);
		measurement_options.add_options()
			("measurement_type", po::value<string>(&measurement_type)->default_value(""), ("what measure to perform. options: " + metrics_options).c_str())
			("general_measurements_args", po::value<string>(&general_measurements_args)->default_value(""), "Argument to pass to measurement init function")
			("max_diff_working_point", po::value<float>(&max_diff_working_point)->default_value((float)0.05), "the maximal diff in calculated working point to requested working point to put missing value")
			("force_score_working_points", po::bool_switch(&force_score_working_points), "force using scores as working points")
			("min_score_quants_to_force_score_wp", po::value<int>(&min_score_quants_to_force_score_wp)->default_value(10), "Minimal number of score bins that if prediciton file has less than this number, the reported performance will be reported ONLY by score cutoffs")
			("score_resolution", po::value<float>(&score_resolution)->default_value((float)0.0001), "score bin resolution rounding for speed up. put 0 to no rounding")
			("score_bins", po::value<int>(&score_bins)->default_value(0), "score bin count for speed up. put 0 to no use")
			("working_points_sens", po::value<string>(&working_points_sens), "sens working point - list with \",\" between each one. in percentage 0-100")
			("working_points_fpr", po::value<string>(&working_points_fpr), "fpr working point - list with \",\" between each one. in percentage 0-100")
			("working_points_pr", po::value<string>(&working_points_pr), "pr working point - list with \",\" between each one. in percentage 0-100")
			("working_points_score", po::value<string>(&working_points_score), "score working point - list with \",\" between each one")
			("working_points_topn", po::value<string>(&working_points_topn), "topn working point - list with \",\" of integers")
			("part_auc_params", po::value<string>(&part_auc_params), "partial auc points - list with \",\" between each, in 0-1")
			("multiclass_top_n", po::value<string>(&multiclass_top_n)->default_value("1,5"), "In multiclass mode  top_n predictions to consider (comma separated")
			("multiclass_dist_name", po::value<string>(&multi_class_dist_name), "In multiclass-  name of distance function. If Jaccarad/Uniform, distance can be calculated and not given")
			("multiclass_dist_file", po::value<string>(&multi_class_dist_file), "In multiclass- file with distance metric")
			("multiclass_auc", po::value<bool>(&multi_class_auc)->default_value(false), "perform class-wise auc in multi-class analysis")
			;

		po::options_description bootstrap_sample("Bootstrap Sampling options", row_size * 2, row_size);
		bootstrap_sample.add_options()
			("sample_per_pid", po::value<int>(&sample_per_pid)->default_value(1), "num of samples to take for each patient. 0 - means take all samples for patient")
			("sample_pid_label", po::bool_switch(&sample_pid_label), "sample on each pid and label")
			("exclude_controls_without_followup", po::value<bool>(&exclude_controls_without_followup)->default_value(true), "If true, controls are excluded if the they don't have enough follow up according to the time window. If false, controls are never excluded.")
			("do_autosim", po::bool_switch(&do_autosim), "to do auto simulation - requires min_time,max_time")
			("min_time", po::value<int>(&min_time), "min_time for autosim")
			("max_time", po::value<int>(&max_time), "max_time for autosim")
			("sim_time_window", po::bool_switch(&sim_time_window), "flag to treat cases as controls which are not in time window and not censor them")
			("censor_time_factor", po::value<float>(&censor_time_factor)->default_value(2), "Used when sim_time_window is on - what's the facor to censor cases, the rest are turned into controls. 1 means all cases beyond window will turn into controls without censoring")
			;

		po::options_description bootstrap_filters("Bootstrap Filtering options", row_size * 2, row_size);
		bootstrap_filters.add_options()
			("use_censor", po::value<bool>(&use_censor)->default_value(false), "if true will use repository censor")
			("whitelist_ids_file", po::value<string>(&whitelist_ids_file), "file with whitelist of ids to take")
			("blacklist_ids_file", po::value<string>(&blacklist_ids_file), "file with blacklist of ids to remove")
			("sample_min_year", po::value<int>(&sample_min_year)->default_value(-1), "used for filtering samples before that year. when sample_min_year < 0 will not filter anything")
			("sample_max_year", po::value<int>(&sample_max_year)->default_value(-1), "used for filtering samples after that year. when sample_max_year < 0 will not filter anything")
			;

		desc.add_options()
			("sample_seed", po::value<int>(&sample_seed)->default_value(0), "seed for bootstrap sampling")
			("use_splits", po::bool_switch(&use_splits), "flag to perform split-wise analysis in addition to full_data")
			("run_id", po::value<string>(&run_id)->default_value("run_id_not_set"), "run_id identifies this execution of the bootstrap app")
			;

		desc.add(input_output);
		desc.add(measurement_options);
		desc.add(bootstrap_sample);
		desc.add(bootstrap_filters);
		desc.add(bootstrap_opts);
		desc.add(inc_args);


		min_time = -1; max_time = -1;
		init(desc, bootstrap_logo);
	}

	bool is_rep_needed() {
		if (inp_type != Features && inp_type != Features_Csv) {
			if (!cohorts_file.empty()) {
				ifstream fr(cohorts_file);
				if (!fr.good())
					MTHROW_AND_ERR("IO Error: can't read \"%s\"\n", cohorts_file.c_str());
				string line;
				while (getline(fr, line)) {
					if (line.find("Age:") != string::npos || line.find("Gender:") != string::npos)
						return true;
				}
				fr.close();
			}
			for (auto &single_cohort : cohort)
				if (!cohort.empty()) {
					if (single_cohort.find("Age:") != string::npos || single_cohort.find("Gender:") != string::npos)
						return true;
				}
		}

		return !incidence_file.empty() || !json_model.empty() || !registry_path.empty();
	}
};
#endif
