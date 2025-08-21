// Apply a model

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "Cmd_Args.h"
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <boost/algorithm/string.hpp>
#include <boost/regex.hpp>
#include <boost/filesystem.hpp>
#include <boost/algorithm/string_regex.hpp>
#include "CommonLib/CommonLib/commonHeader.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

namespace po = boost::program_options;

#include <MedUtils/MedUtils/MedGlobalRNG.h>

void read_input(const ProgramArgs &args, MedModel &model, MedPidRepository &rep) {
	// Read matrix/samples
	if (!args.inCsv.empty()) {
		MLOG("Reading matrix\n");
		if (model.features.read_from_csv_mat(args.inCsv) <= 0)
			MTHROW_AND_ERR("Cannot read matrix from %s\n", args.inCsv.c_str());
	}
	else if (!args.samples.empty()) {
		MLOG("Reading samples\n");
		MedSamples samples;
		if (samples.read_from_file(args.samples) != 0)
			MTHROW_AND_ERR("Cannot read samples from %s\n", args.samples.c_str());
		vector<int> ids;
		samples.get_ids(ids);

		if (!args.skip_model_apply) {
			model.load_repository(args.rep, ids, rep, true);
			model.apply(rep, samples);
		}
		else
			samples.export_to_sample_vec(model.features.samples);

		if (args.skip_model_apply && args.init_rep) {
			model.load_repository(args.rep, ids, rep, true);
			model.p_rep = &rep;
		}
	}
	vector<int> all_ids;
	if (args.skip_model_apply && args.init_rep && args.samples.empty()) {
		model.load_repository(args.rep, all_ids, rep, true);
		model.p_rep = &rep;
	}
}

int main(int argc, char *argv[])
{
	ProgramArgs args;

	// Initialize
	if (args.parse_parameters(argc, argv) < 0)
		return -1;

	globalRNG::srand(args.seed);

	// Read Model 
	MLOG("Reading model\n");
	MedModel model;
	model.read_from_file_with_changes(args.inModel, args.model_changes);

	// Replace predictor
	if (!args.predictor.empty()) {
		MLOG("Replacing predictor");
		MedPredictor *pred;
		read_predictor_from_file(pred, args.predictor);
		model.predictor = pred;
	}

	// Add pre-processors
	if (!args.preProcessors.empty()) {
		MLOG("Adding pre-processors\n");
		run_current_path = boost::filesystem::path(args.preProcessors).parent_path().string();
		int fp_set = (int)model.rep_processors.size(); //will add from this pos
		MLOG("%s\n", medial::io::get_list(args.alt_json).c_str());
		
		int added_proc = model.add_pre_processors_json_string_to_model("", args.preProcessors, args.alt_json, args.add_rep_first);
		if (args.learn_rep_proc) {
			MedPidRepository rep;
			read_input(args, model, rep);
			MedSamples learn_samples;
			learn_samples.import_from_sample_vec(model.features.samples);
			if (args.add_rep_first) {
				for (size_t i = 0; i < added_proc; ++i) {
					model.rep_processors[i]->dprint("Training " + to_string(i), 5);
					model.rep_processors[i]->learn(rep, learn_samples);
				}
			}
			else {
				for (size_t i = fp_set; i < model.rep_processors.size(); ++i) {
					model.rep_processors[i]->dprint("Training " + to_string(i), 5);
					model.rep_processors[i]->learn(rep, learn_samples);
				}
			}
		}
	}

	// Add post-processors
	if (!args.postProcessors.empty()) {
		MLOG("Adding post-processors\n");
		// Prepare
		MedPidRepository rep;
		read_input(args, model, rep);
		// clears all post_processors - and overwrite them
		int start_from = 0;
		if (!args.keep_existing_processors) {
			for (size_t i = 0; i < model.post_processors.size(); ++i)
				delete model.post_processors[i];
			model.post_processors.clear();
		}
		else
			start_from = (int)model.post_processors.size();
		run_current_path = boost::filesystem::path(args.postProcessors).parent_path().string();
		if (model.add_post_processors_json_string_to_model("", args.postProcessors, args.alt_json) < 0)
			MTHROW_AND_ERR("adding post processor failed\n");

		//model.init_from_json_file_with_alterations

		for (int i = start_from; i < model.post_processors.size(); ++i) {
			model.post_processors[i]->init_post_processor(model);
			model.post_processors[i]->Learn(model.features);
		}
	}
	if (args.generate_masks_for_features)
		model.generate_masks_for_features = 1;
	// Write model
	MLOG("Writing model\n");
	model.write_to_file(args.out);
}