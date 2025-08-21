#ifndef __CMD_ARGS_H__
#define __CMD_ARGS_H__

#include <MedUtils/MedUtils/MedUtils.h>

/**
* Setting to control how to print representative selection
* for each contributer will print it's value, contributing value (percent from contributions)
*/
class Representative_Group_Settings : public SerializableObject {
public:
	int min_count = 1; ///< minimal limit on number of features to take as representative
	float sum_ratio = 0; ///< minimal sum of contrib to reach group contrib
	bool only_same_direction = false; ///< take only same direction contributions

	int init(map<string, string>& m) {
		for (const auto &it : m)
		{
			if (it.first == "min_count")
				min_count = med_stoi(it.second);
			else if (it.first == "sum_ratio")
				sum_ratio = med_stof(it.second);
			else if (it.first == "only_same_direction")
				only_same_direction = med_stoi(it.second) > 0;
			else
				HMTHROW_AND_ERR("Error  - unknown param %s\n", it.first.c_str());
		}
		return 0;
	}

	ADD_CLASS_NAME(Representative_Group_Settings)
		ADD_SERIALIZATION_FUNCS(min_count, sum_ratio, only_same_direction)
};

class Program_Args : public medial::io::ProgramArgs_base {
private:
	string rep_settings_s;
	void post_process() {
		if (!rep_settings_s.empty())
			rep_settings.init_from_string(rep_settings_s);
	}
public:
	string samples_path;
	string model_path;
	string change_model_file;
	string change_model_init;
	string output_path;
	string rep;
	int take_max;
	string viewer_url_base;
	bool transform_contribution;
	bool expend_dict_names;
	bool expend_feature_names;
	Representative_Group_Settings rep_settings;

	Program_Args() {
		po::options_description prg_options("Global Options");
		vector<string> flds;
		rep_settings.serialized_fields_name(flds);
		string help_s = medial::io::get_list(flds, ", ");

		prg_options.add_options()
			("rep", po::value<string>(&rep)->required(), "repository to apply model without feature processors.remain unorm")
			("samples_path", po::value<string>(&samples_path)->required(), "samples path to apply")
			("model_path", po::value<string>(&model_path)->required(), "the medmodel path with explainer")
			("change_model_init", po::value<string>(&change_model_init)->default_value(""), "init argument to change the model in runtime")
			("change_model_file", po::value<string>(&change_model_file)->default_value(""), "json file to read multiple changes to the model in runtime - should have \"changes\" element with array of change requests")
			("output_path", po::value<string>(&output_path)->required(), "the output path")
			("take_max", po::value<int>(&take_max)->default_value(10), "how much to take for each explain")
			("transform_contribution", po::value<bool>(&transform_contribution)->default_value(false), "If true will transform contributition into probs")
			("rep_settings", po::value<string>(&rep_settings_s)->default_value(""), ("the representative config, with fields: [" + help_s + "]").c_str())

			("expend_dict_names", po::value<bool>(&expend_dict_names)->default_value(false), "If true will add column that will expend dict val aliases")
			("expend_feature_names", po::value<bool>(&expend_feature_names)->default_value(false), "If true will add column that will expend each feature val aliases")
			("viewer_url_base", po::value<string>(&viewer_url_base)->default_value("http://node-04:8194/pid,%d,%d,prediction_time"), "the viewer url template")

			;

		init(prg_options);
	}
};


#endif // !__CMD_ARGS_H__