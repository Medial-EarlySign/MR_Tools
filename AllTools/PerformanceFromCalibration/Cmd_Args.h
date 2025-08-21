#ifndef __CMD_ARGS__
#define __CMD_ARGS__
#include <MedUtils/MedUtils/MedUtils.h>
#include <fstream>
#include <MedProcessTools/MedProcessTools/MedSamples.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	string tests_file;

	void post_process() {
	}
public:
	string rep;
	string preds;
	string output;
	

	string json_model; ///< json to create features for cohorts
	string cohorts_file; ///< cohorts - like in bootstrap

	ProgramArgs() {
		po::options_description options("Program Options");
		options.add_options()
			("preds", po::value<string>(&preds)->required(), "input MedSamples with predictions")
			("output", po::value<string>(&output)->required(), "output file path")

			("rep", po::value<string>(&rep)->default_value(""), "repository path")
			("json_model", po::value<string>(&json_model)->default_value(""), "json to create features for cohorts")
			("cohorts_file", po::value<string>(&cohorts_file)->default_value(""), "cohorts - like in bootstrap. If empty will just analyze all samples")
			;

		init(options);
	}
};


#endif
