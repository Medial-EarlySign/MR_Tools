#ifndef __CMD_ARGS__H__
#define __CMD_ARGS__H__

#include <string>
#include <MedUtils/MedUtils/MedUtils.h>
#include <boost/algorithm/string.hpp>

using namespace std;
namespace po = boost::program_options;

#define LOCAL_SECTION LOG_APP
class ProgramArgs : public medial::io::ProgramArgs_base
{
private:
	void post_process() {
		if (learn_rep_proc && skip_model_apply)
			MTHROW_AND_ERR("Error in parameters, can't run adjust_model with learn_rep_proc true and skip_model_apply true\n");
	}
public:
	string rep;
	string inModel;
	string model_changes;
	string out;
	string preProcessors, postProcessors, predictor;
	string samples;
	string inCsv;
	vector<string> alt_json;
	int seed;
	bool skip_model_apply; 
	bool init_rep;
	bool keep_existing_processors;
	bool generate_masks_for_features;
	bool learn_rep_proc;
	bool add_rep_first;

	ProgramArgs() {
		po::options_description pr_opts("Adjust_model Options. Json format is -  { \"pre_processors\" : [ {\"rp_type\": \"history_limit\", ...} , ... ] }");
		pr_opts.add_options()
			("rep", po::value<string>(&rep)->default_value(""), "repository config for model-apply for post-processores learning")
			("inModel", po::value<string>(&inModel)->required(), "input model")
			("model_changes", po::value<string>(&model_changes)->default_value(""), "model changes")
			("out", po::value<string>(&out)->required(), "output model")
			("json_alt", po::value<vector<string>>(&alt_json)->composing(), "(multiple) alterations to model json file")
			("preProcessors", po::value<string>(&preProcessors)->default_value(""), "optional (learning-less) pre-processors json file")
			("postProcessors", po::value<string>(&postProcessors)->default_value(""), "optional (learning-less) post-processors json file")
			("predictor", po::value<string>(&predictor)->default_value(""), "optional (learned) predictor to replace one in model")
			//("predictor_alterations", po::value<vector<string>>()->composing(), "(multiple) adjustments to predictor, each of the format: predictor-type(for sanity);init-string")
			("samples", po::value<string>(&samples), "samples for model-apply for post-processores learning")
			("inCsv", po::value<string>(&inCsv)->default_value(""), "MedFeatures matrix for post-processores learning")
			("skip_model_apply", po::value<bool>(&skip_model_apply)->default_value(false), "If true will skip apply of model.usefull for example if already have CV of samples for calibration")
			("init_rep", po::value<bool>(&init_rep)->default_value(false), "If true will init rep even when skip apply")
			("seed", po::value<int>(&seed)->default_value(123456), "seed for globalRNG")
			("keep_existing_processors", po::value<bool>(&keep_existing_processors)->default_value(true), "If true will keep existing post_processors if exists")
			("generate_masks_for_features", po::value<bool>(&generate_masks_for_features)->default_value(true), "If true will turn on generate_masks_for_features in the model")
			("learn_rep_proc", po::value<bool>(&learn_rep_proc)->default_value(false), "If true will learn after adding rep processor")
			("add_rep_first", po::value<bool>(&add_rep_first)->default_value(false), "If true will add rep processor first")
			;

		init(pr_opts);
	}

};

#endif
