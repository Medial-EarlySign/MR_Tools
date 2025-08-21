#ifndef __CMD_ARGS__H__
#define __CMD_ARGS__H__

#include "Logger/Logger/Logger.h"
#include <vector>
#include <string>
#include <unordered_map>
#include <MedUtils/MedUtils/MedUtils.h>
#include <boost/program_options.hpp>
#include <InfraMed/InfraMed/InfraMed.h>
#include <MedUtils/MedUtils/LabelParams.h>
#include <MedUtils/MedUtils/FilterParams.h>
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

using namespace std;
namespace po = boost::program_options;

class ProgramArgs : public medial::io::ProgramArgs_base
{
private:
	string conflicts_method_s;
	string labeling_params_s;
	string filtering_params_s;
	unordered_map<string, int> convert_map = {
		{ "none", medial::repository::fix_method::none },
		{ "drop", medial::repository::fix_method::drop },
		{ "first", medial::repository::fix_method::take_first },
		{ "last", medial::repository::fix_method::take_last },
		{ "mean", medial::repository::fix_method::take_mean },
		{ "min", medial::repository::fix_method::take_min },
		{ "max", medial::repository::fix_method::take_max }

	};

	void post_process() {
		if (convert_map.find(conflicts_method_s) == convert_map.end())
			MTHROW_AND_ERR("Wrong conflict method - please choose one of: %s\n",
				medial::io::get_list(convert_map).c_str());
		conflicts_method = medial::repository::fix_method(convert_map.at(conflicts_method_s));
		if (!labeling_params_s.empty())
			labeling_params.init_from_string(labeling_params_s);
		if (!filtering_params_s.empty())
			filtering_params.init_from_string(filtering_params_s);

		if (registry_load.empty() && registry_init.empty())
			HMTHROW_AND_ERR("ERROR in ProgramArgs - Must provide registry_load path or registry_init to create registry\n");
	}
public:
	string rep;
	string registry_type;
	string registry_init;
	string registry_save;
	string registry_load;
	string censor_load;
	string registry_censor_type;
	string registry_censor_init;
	string registry_active_periods_complete_controls; ///< if given active periods registry of patient to complete reg as controls
	string registry_active_periods_complete_controls_sig; ///< if given active periods registry of patient to complete reg as controls from signal
	bool use_active_for_reg_outcome; ///< If true will use active period for outcome reg
	LabelParams labeling_params; ///< how to label from registry, please reffer to LabelParams type
	FilterParams filtering_params; ///< filter params for sampling
	medial::repository::fix_method conflicts_method;
	string model_rep_proc_json;

	string sampler_type;
	string sampler_args;
	string samples_save;

	string reg_print_incidence;
	string reg_params_incidence;

	ProgramArgs() {
		po::options_description pr_global("Global Options");
		pr_global.add_options()
			("rep", po::value<string>(&rep)->required(), "repository path");

		po::options_description pr_opts("Registry Options");
		char buffer[500];
		snprintf(buffer, sizeof(buffer), "conlict options are: %s", medial::io::get_list(convert_map).c_str());
		string opt_desc = string(buffer);
		pr_opts.add_options()
			("registry_type", po::value<string>(&registry_type)->default_value("categories"), "registry type for creation")
			("registry_init", po::value<string>(&registry_init)->default_value(""), "registry init string for creation")
			("registry_censor_type", po::value<string>(&registry_censor_type)->default_value("keep_alive"), "registry censor type for creation")
			("registry_censor_init", po::value<string>(&registry_censor_init)->default_value(""), "registry censor init string for creation")
			("registry_active_periods_complete_controls", po::value<string>(&registry_active_periods_complete_controls)->default_value(""), "if given active periods registry of patient to complete reg as controls")
			("registry_active_periods_complete_controls_sig", po::value<string>(&registry_active_periods_complete_controls_sig)->default_value(""), "if given active periods registry of patient to complete reg as controls from rep signal")
			("model_rep_proc_json", po::value<string>(&model_rep_proc_json)->default_value(""), "json of MedModel for using rep_processors in registry")
			("conflicts_method", po::value<string>(&conflicts_method_s)->default_value("none"), opt_desc.c_str())
			("registry_save", po::value<string>(&registry_save)->default_value(""), "If supply will save registry in this path")
			("registry_load", po::value<string>(&registry_load)->default_value(""), "If supply will load registry from this path and will not use registry args")
			("censor_load", po::value<string>(&censor_load)->default_value(""), "If given will load censor registry from file")
			("use_active_for_reg_outcome", po::value<bool>(&use_active_for_reg_outcome)->default_value(0), "If true will also use active_period to complete controls period in outcome registry")
			("reg_print_incidence", po::value<string>(&reg_print_incidence)->default_value(""), "print by year stats when creating registry - inc file path")
			("reg_params_incidence", po::value<string>(&reg_params_incidence)->default_value(""), "the sampling params for yearly when print incidence file")
			;

		po::options_description smp_opts("Sampling Options");
		smp_opts.add_options()
			("labeling_params", po::value<string>(&labeling_params_s)->default_value("conflict_method=all;label_interaction_mode=0:all,before_end|1:before_start,after_start;censor_interaction_mode=all:within,within"), "how to label from registry, please reffer to LabelParams type")
			("filtering_params", po::value<string>(&filtering_params_s)->default_value(""), "filtering of sampling prior to sampling, please reffer to FilterParams type")
			("sampler_type", po::value<string>(&sampler_type)->default_value(""), "sampling method")
			("sampler_args", po::value<string>(&sampler_args)->default_value(""), "sampling init args")
			("samples_save", po::value<string>(&samples_save)->default_value(""), "samples save path If specified with sampler_type,sampler_args will output MedSamples also")
			;

		pr_global.add(pr_opts);
		pr_global.add(smp_opts);

		init(pr_global);
	}

};

#endif
