//
// Usage example: howe to create a feature on some samples recipe
//


#include <string>
#include <iostream>
#include <boost/program_options.hpp>
#include <boost/algorithm/string/split.hpp>
#include <InfraMed/InfraMed/InfraMed.h>
#include <InfraMed/InfraMed/MedPidRepository.h>
#include <MedProcessTools/MedProcessTools/MedModel.h>

#include <Logger/Logger/Logger.h>
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
using namespace std;
namespace po = boost::program_options;

//=========================================================================================================
int read_run_params(int argc, char *argv[], po::variables_map& vm) {
	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value("/home/Repositories/THIN/thin_jun2017/thin.repository"), "repository file name")
			("samples", po::value<string>()->default_value(""), "samples file to work with")
			("feature", po::value<string>()->default_value(""), "feature name to run")
			("feature_params", po::value<string>()->default_value(""), "feature params to use")
			("feature_signals", po::value<string>()->default_value(""), "signals to run features on (for features that need this)")
			("out_mat", po::value<string>()->default_value("out.mat"), "output matrix")
			;


		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);

		MLOG("=========================================================================================\n");
		MLOG("Command Line:");
		for (int i=0; i<argc; i++) MLOG(" %s", argv[i]);
		MLOG("\n");
		MLOG("..........................................................................................\n");
	}
	catch (exception& e) {
		cerr << "error: " << e.what() << "; run with --help for usage information\n";
		return -1;
	}
	catch (...) {
		cerr << "Exception of unknown type!\n";
		return -1;
	}

	return 0;
}


//========================================================================================
// MAIN
//========================================================================================

int main(int argc, char *argv[])
{
	int rc = 0;
	po::variables_map vm;

	// Reading run Parameters
	MLOG("Reading params\n");
	rc = read_run_params(argc, argv, vm);
	assert(rc >= 0);


	// Read samples
	MedSamples samples;
	if (samples.read_from_file(vm["samples"].as<string>()) < 0) {
		MERR("ERROR: failed reading samples file %s\n", vm["samples"].as<string>().c_str());
		return -1;
	}


	// Prepare a model with our feature generator
	MedModel model;

	string feat_name = vm["feature"].as<string>();
	string feat_params = vm["feature_params"].as<string>();
	vector<string> feat_sigs;
	boost::split(feat_sigs, vm["feature_signals"].as<string>(), boost::is_any_of(","));

	// MAIN POINT OF INTEREST(1) : defining the model
	// This is the actual line of adding the requested feature to the model
	model.add_feature_generators(feat_name, feat_sigs, feat_params);

	// get required signals from model to load
	unordered_set<string> load_sigs;
	vector<string> load_sigs_v;

	// This API is a useful one as well : getting the minimal set of signals a model needs in order to work.
	// In cases in which the repository is already preloaded one can skip this stage and the loading.
	model.get_required_signal_names(load_sigs);
	MLOG("Required signals : ");
	for (auto s : load_sigs) {
		MLOG("%s ", s.c_str());
		load_sigs_v.push_back(s);
	}
	MLOG("\n");

	// load rep
	vector<int> pids;
	samples.get_ids(pids);
	MedPidRepository rep;
	if (rep.read_all(vm["rep"].as<string>(), pids, load_sigs_v) < 0) {
		MERR("ERROR: failed reading repository %s\n", vm["rep"].as<string>().c_str());
		return -1;
	}

	// MAIN POINT OF INTEREST(2) : applying and creating the features
	MLOG("Before Apply\n");
	// ready for production : actually applying the model (just feature generators stages here) on the rep and samples we have
	model.apply(rep, samples, MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_APPLY_FTR_GENERATORS);
	MLOG("After Apply\n");

	MedMat<float> x;
	// nice API to get the results in a matrix - the matrix will also hold the pid,time,label etc... for each line
	model.features.get_as_matrix(x);

	// writing a matrix as a csv
	x.write_to_csv_file(vm["out_mat"].as<string>());

	MLOG("Write matrix of %d x %d to file %s\n", x.nrows, x.ncols, vm["out_mat"].as<string>().c_str());

	// Done !!

	return 0;
}


