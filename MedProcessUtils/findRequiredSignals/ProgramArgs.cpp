#include "ProgramArgs.h"

ProgramArgs::ProgramArgs() {

	po::options_description desc("Program options");

	desc.add_options()
		("model_file", po::value<string>(&model_file)->required(), "model file")
		("samples_file", po::value<string>(&samples_file)->required(), "samples file")
		("rep_file", po::value<string>(&rep_file)->required(), "repository file")
		("out_file", po::value<string>(&outFile)->required(), "output file")
		("req", po::value<string>(&req_signals_s)->default_value("BDATE,GENDER"), "comma-separated list of required signals")
		("max_num_tests_per_iter", po::value<int>(&numTestsPerIter), "maximal allowed tests to be done in a iteration")
		("required_ratio", po::value<float>(&requiredRatioPerf)->default_value(-1), "required perforamnce compared to the full model.")
		("required_abs", po::value<float>(&requiredAbsPerf)->default_value(-1), "Absolute required perforamnce. ")
		("num_iterations_to_continue", po::value<int>(&numIterationsToContinue)->default_value(0), "Number of iterations to performe after we get to the required performance.")
		("maximal_num_of_signals", po::value<size_t>(&maximalNumSignals)->default_value(666), "Maximal number of signals allowed")
		("evaluations_to_print", po::value<int>(&evaluationsToPrint)->default_value(0), "Number of evaluations to print in each stage (0 - Only combinations that pass the required preformance. 1 - The best result, 2 - The two best results. etc. -1 means print all")
		("bootstrap_params", po::value<string>(&bootstrap_params)->default_value("sample_per_pid:1"), " Parameters for bootstrap. e.g. sample_per_id=1 ('/' separated) file")
		("cohort_params", po::value<string>(&cohort_params)->default_value("Age:45,120/Time-Window:0,365"), "Parameters for defining the booststrap cohort. e.g. Age:50,75/Time-Window:0,365")
		("msr_params", po::value<string>(&msr_params)->default_value("AUC"), "Define the performance measurement. e.g. AUC or SENS,FPR,0.2 for Sensitivity at FPR=20%")
		("bootstrap_json", po::value<string>(&bootstrap_json)->default_value(""), "Bootstrap json")
		("skip_supersets", po::value<bool>(&skip_supersets)->default_value(true), "Skip supersets of acceptable combinations")
		("delete_signals", po::value<string>(&delete_signals_s)->default_value(""), "comma-separated list of signals to delete")
		;

	init(desc);
}

void ProgramArgs::post_process() {
	boost::split(req_signals, req_signals_s, boost::is_any_of(","));
	boost::split(delete_signals, delete_signals_s, boost::is_any_of(","));
	if (requiredAbsPerf > 0 && requiredRatioPerf > 0) {
		MTHROW_AND_ERR("Please provide a single stopping criterion (both required_ratio and required_abs were given)");
	}
	else if (requiredRatioPerf <= 0 && requiredAbsPerf <= 0)
		MTHROW_AND_ERR("Please provide a stopping criterion (required_ratio or required_abs)");
}

