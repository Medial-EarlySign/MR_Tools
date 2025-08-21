#ifndef __CMD_ARGS__
#define __CMD_ARGS__
#include <MedUtils/MedUtils/MedUtils.h>
#include <fstream>
#include <MedProcessTools/MedProcessTools/MedSamples.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	string time_windows_s;
	string skip_list_s;

	void post_process() {
		vector<string> tokens;
		boost::split(tokens, time_windows_s, boost::is_any_of(","));
		if (tokens.empty())
			MTHROW_AND_ERR("Error - time_windows should include at least 1 element\n");
		time_windows.resize(tokens.size());
		for (size_t i = 0; i < tokens.size(); ++i)
			time_windows[i] = med_stoi(tokens[i]);

		boost::split(skip_list, skip_list_s, boost::is_any_of(","));
	}
public:
	string rep; ///< repository
	string model_path; ///< MedModel binary path
	string samples; ///< input samples
	string output; ///< output path for report
	string bt_filter_json; ///< bt filter json.
	string bt_filter_cohort; ///< bt filter cohort.
	string bt_args; ///< general args for bt
	string measure_regex; ///< regex to filter measurements from bootstrap
	vector<int> time_windows; ///< time window to deduce the signal "exists", can be multiple
	string features_groups; ///< grouping
	string group2signal; ///< file with 2 columns tab delimieted. group name, signal name
	vector<string> skip_list; ///< list of groups to skip, mandatory
	int min_group_analyze_size; ///< limit for minimal group analysis size
	bool no_filtering_of_existence; ///< If true will not filter by existence of signal
	int down_sample_max_count; ///< If given not 0, will down sample to this size if samples are bigger

	ProgramArgs() {
		po::options_description options("Program Options");
		options.add_options()
			("rep", po::value<string>(&rep)->required(), "repository path")
			("samples", po::value<string>(&samples)->required(), "input MedSamples with predictions")
			("model_path", po::value<string>(&model_path)->required(), "json to create features for cohorts")
			("output", po::value<string>(&output)->required(), "output file path")
			("bt_filter_json", po::value<string>(&bt_filter_json)->default_value(""), "bootstrap filter json")
			("bt_filter_cohort", po::value<string>(&bt_filter_cohort)->default_value(""), "bootstrap filter cohort")
			("bt_args", po::value<string>(&bt_args)->default_value(""), "Optional arguments for MedBootstrap init")
			("measure_regex", po::value<string>(&measure_regex)->default_value("AUC"), "regex to filter measurements from bootstrap")
			("group2signal", po::value<string>(&group2signal)->default_value(""), "file with 2 columns tab delimieted. group name [TAB] signal name. signal name can be multiple signal with comma separated")
			("skip_list", po::value<string> (&skip_list_s)->default_value(""), "comma separated list of groups to ignore in analysis")
			("min_group_analyze_size", po::value<int>(&min_group_analyze_size)->default_value(10), "minimal group size after filtering to analyze")
			("down_sample_max_count", po::value<int>(&down_sample_max_count)->default_value(0), "If given not 0, will down sample to this size if samples are bigger")
			("no_filtering_of_existence", po::value<bool>(&no_filtering_of_existence)->default_value(false), "If true will not filter by existence of signal")

			("time_windows", po::value<string>(&time_windows_s)->default_value("365,1095"), "Time window to deduce signal exists")
			("features_groups", po::value<string>(&features_groups)->default_value("BY_SIGNAL"), "grouping of features like butwhy format. Empty means no grouping")
			;

		init(options);
	}
};


#endif
