#define _CRT_SECURE_NO_WARNINGS
#define D_SCL_SECURE_NO_WARNINGS

#include "bootstrap_analysis_for_oxford.h"

/*			Main			*/
int main(int argc, char *argv[]) {

	// Read Running Parameters
	po::variables_map vm;
	running_flags flags;

	assert(read_run_params_for_oxford(argc, argv, vm, flags) != -1);

	// Init Output Parameter Names
	int nestimates, autosim_nestimates;
	double extra_fpr = vm["fpr"].as<double>();
	double extra_sens = vm["sens"].as<double>();
	double extra_sim_fpr = vm["sim_fpr"].as<double>();
	char *param_names, *autosim_param_names;

	assert(init_param_names(extra_fpr, extra_sim_fpr, extra_sens,flags.all_fpr, &nestimates, &param_names, &autosim_nestimates, &autosim_param_names) != -1);

	// Initialize random numbers
	int nthreads = vm["nthreads"].as<int>();
	globalRNG::srand(vm["seed"].as<int>());

	quick_random qrand;
	vector<quick_random> threaded_qrand;
	for (int i = 0; i<nthreads; i++)
		threaded_qrand.push_back(quick_random(NRANDOM));

	int period = vm["period"].as<int>();
	int gap = vm["gap"].as<int>();

	// Read data
	input_data indata;
	assert(read_all_input_data_for_oxford(vm, indata) != -1);
	fflush(stderr);

	// Open output files 
	const char *out_file = vm["out"].as<string>().c_str();

	out_fps fouts;
	fouts.info_fout = NULL;
	assert(open_all_output_files(out_file, flags, period, param_names, nestimates, autosim_param_names, autosim_nestimates, fouts) != -1);
	fflush(stderr);

	// Allocate.
	work_space work;
	assert(allocate_data(indata, work) != -1);

	// Auto-simulation

	assert(do_autosim(indata, work, fouts, flags, autosim_nestimates, extra_sim_fpr, threaded_qrand, nthreads, 500) != -1);
	fflush(stderr);

	// Periodic Analyses
	if (!flags.raw_only && period > 0) {
		assert(do_periodic_autosim(indata, work, fouts, flags, autosim_nestimates, autosim_param_names, extra_sim_fpr, period, threaded_qrand, nthreads, 500) != -1);
		assert(do_periodic_cuts(indata, work, fouts, flags, autosim_nestimates, autosim_param_names, extra_fpr,period, gap, threaded_qrand, nthreads, 500) != -1);
	}

	// Time Windows: Loop on time-windows x age-ranges
	assert(do_time_windows(indata, work, fouts, flags, nestimates, extra_fpr, extra_sens, qrand, threaded_qrand, nthreads, 500) != -1);

	return 0;
}

// Functions
/////////////

int read_run_params_for_oxford(int argc, char **argv, po::variables_map& vm, running_flags& flags) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("in", po::value<string>()->required(), "input file")
			("params", po::value<string>()->required(), "file specifying time windows, age groups, and last date")
			("out", po::value<string>()->required(), "prefix of output file names")
			("prbs", po::value<string>(), "incidence per age file")
			("gender", po::value<string>()->required(), "Gender: M/F/C")
			("seed", po::value<int>()->default_value(1234), "seed for randomizations")
			("fpr", po::value<double>()->default_value(-1.0), "additional FPR point")
			("sens", po::value<double>()->default_value(-1.0), "additional Sensitivity point")
			("sim_fpr", po::value<double>()->default_value(-1.0), "additional SIM FPR point")
			("all_fpr", po::bool_switch(&(flags.all_fpr)), "use an extensive list of FPR points in time windows")
			("raw_only", po::bool_switch(&(flags.raw_only)), "print .Raw and .Info files and exit")
			("auto_sim_raw", po::bool_switch(&(flags.auto_sim_raw)), "print AutoSimRaw file")
			("last", po::bool_switch(&(flags.use_last)), "use last score in window for cases")
			("period", po::value<int>()->default_value(DEF_PERIOD), "Period for periodic analyses (non-positive to avoid)")
			("gap", po::value<int>()->default_value(365 * 100), "Gap (in days) for predicting cancer in periodic cuts")
			("nthreads", po::value<int>()->default_value(1), " Number of threads")
			("first_date", po::value<int>()->required(), "first date for which cancer data is reliable")
			("last_date",po::value<int>()->required(), "last date for which cancer/censor data is available")
			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);
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







