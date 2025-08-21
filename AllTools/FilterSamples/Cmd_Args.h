#ifndef __CMD_ARGS__
#define __CMD_ARGS__
#include <MedUtils/MedUtils/MedUtils.h>

class ProgramArgs : public medial::io::ProgramArgs_base {
public:
	string rep;
	string samples;
	int filter_train;
	string output;

	string json_mat;
	string filter_feat;
	float low_val, high_val;
	string filter_by_bt_cohort;

	ProgramArgs() {
		po::options_description options("Program Options");
		options.add_options()
			("rep", po::value<string>(&rep)->default_value("/home/Repositories/THIN/thin_final/thin.repository"), "repository path")
			("samples", po::value<string>(&samples)->required(), "MedSamples input str")
			("filter_train", po::value<int>(&filter_train)->default_value(1), "filter Train == val")

			("json_mat", po::value<string>(&json_mat)->default_value(""), "the json matrix for filter")
			("filter_feat", po::value<string>(&filter_feat)->default_value(""), "filter feature name")
			("low_val", po::value<float>(&low_val), "filter feature low val")
			("high_val", po::value<float>(&high_val), "filter feature high val")
			("filter_by_bt_cohort", po::value<string>(&filter_by_bt_cohort)->default_value(""), "If given will filter like bootstrap syntax")

			("output", po::value<string>(&output)->default_value(""), "output file MedSamples")
			;

		init(options);
	}
};

#endif
