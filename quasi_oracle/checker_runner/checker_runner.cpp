// Perform hyper-parameters tuning

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "checker_runner.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#ifndef  __unix__
#include <windows.h>
#else
#include <sys/stat.h>
#endif

int main(int argc, char *argv[])
{

	int rc = 0;
	globalRNG::srand(12131415);

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	string script;
	if (vm.count("script"))
		script = vm["script"].as<string>();

	string commandsFile;
	if (vm.count("outCommands"))
		commandsFile = vm["outCommands"].as<string>();

	// Collect directories
	vector<string> directories;
	string dir = vm["dir"].as<string>();
	string inDir = vm["inDir"].as<string>();
	string prefix = vm["prefix"].as<string>();
	get_directories(dir, prefix, directories);

	// Read header of condor runner
	vector<string> condor_runner, commands;
	string inCondor = vm["inCondor"].as<string>();
	string command = vm["command"].as<string>();

	read_condor_runner(inCondor, condor_runner);

	string logger;
	if (vm.count("log"))
		logger = vm["log"].as<string>();
	else
		logger = dir + "/condor.log";

	condor_runner.push_back("log = " + logger);
	condor_runner.push_back("executable = " + command);
	condor_runner.push_back("");

	// Generate commands
	for (string& subDirName : directories) {
		
		string arguments;
		if (script.empty())
			arguments = "--testMatrix " + inDir + "/TestMatrix.bin --trainMatrix " + inDir + "/TrainMatrix.bin --validationMatrix " + inDir +
			"/TestMatrix.bin --params " + inDir + "/model_params.bin --do_external_predictor --predictor_file " + subDirName + "/outPredictor --out " + subDirName +
			"/analyzeTest --summary_file " + subDirName + "/summarizeTest";
		else
			arguments = "--testMatrix " + inDir + "/TestMatrix.bin --trainMatrix " + inDir + "/TrainMatrix.bin --validationMatrix " + inDir +
			"/TestMatrix.bin --params " + inDir + "/model_params.bin --do_external_script --script " + script + " --script_input " + subDirName +"/matrix --script_output " +
			subDirName + "/test_predictions --script_params \"--predictor " + subDirName + "/outPredictor\" --out " + subDirName +"/analyzeTest --summary_file " + 
			subDirName + "/summarizeTest";

		condor_runner.push_back("arguments = " + arguments);
		condor_runner.push_back("output = " + subDirName + "/checker_stdout");
		condor_runner.push_back("error = " + subDirName + "/checker_stderr");
		condor_runner.push_back("queue\n\n");

		commands.push_back(command + " " + arguments + " > " + subDirName + "/checker_stdout 2> " + subDirName + "/checker_stderr");
	}

	// Generate condor runner
	string outCondor = vm["outCondor"].as<string>();
	write_file(outCondor, condor_runner);

	if (!commandsFile.empty())
		write_file(commandsFile, commands);

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	char* pPath;
	pPath = getenv("MR_ROOT");
	if (pPath == NULL)
		MTHROW_AND_ERR("The current MR_ROOT is not available ");

	try {
		desc.add_options()
			("help", "produce help message")
			("dir", po::value<string>()->required(), "working directory")
			("inDir", po::value<string>()->required(), "input matrices directory")
			("prefix", po::value<string>()->default_value("quasi_oracle"), "sub-directories prefix (comma separated)")
			("inCondor", po::value<string>()->default_value(string(pPath) + "/Tools/quasi_oracle/qo_runner/condor_header.txt"), "condor-runner skeleton file")
			("outCondor", po::value<string>()->default_value("condor_runner"), "condor-runner file")
			("outCommands", po::value<string>(), "optional commands output file")
			("command", po::value<string>()->default_value(string(pPath) + "/Projects/Shared/CausalEffects/CausalEffectsUtils/Linux/Release/check_toy_model"), "command to run")
			("log", po::value<string>(), "condor log file, if not given, use $dir/condor.log")
			("script", po::value<string>(), "script to use with do_external_script mode")
			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);
	}
	catch (exception& e) {
		string err = "error: " + string(e.what()) + "; run with --help for usage information\n";
		throw runtime_error(err);
	}
	catch (...) {
		throw runtime_error("Exception of unknown type!\n");
	}
}

void get_directories(const string& dir, const string& prefix, vector<string>& directories) {

	if (!fs::exists(dir))
		MTHROW_AND_ERR("Cannot find direct");

	vector<string> prefices;
	boost::split(prefices, prefix, boost::is_any_of(","));

	fs::directory_iterator end_itr; // default construction yields past-the-end

	for (fs::directory_iterator itr(dir); itr != end_itr; ++itr)
	{
		const string name = itr->path().filename().string();
		for (string& pref : prefices) {
			if (name.find(pref) == 0)
				directories.push_back(dir + "/" + name);
		}
	}

	cerr << "Found " << directories.size() << " directories\n";
}

// Read/Write condor
void read_condor_runner(string& fileName, vector<string>& condor_runner) {

	ifstream inf(fileName);
	if (!inf.is_open())
		MTHROW_AND_ERR("Cannot open %s for reading\n", fileName.c_str());

	string line;
	while (getline(inf, line))
		condor_runner.push_back(line);
}

void write_file(string& fileName, vector<string>& condor_runner) {

	ofstream outf(fileName);
	if (!outf.is_open())
		MTHROW_AND_ERR("Cannot open %s for writing\n", fileName.c_str());

	for (string& line : condor_runner)
		outf << line << "\n";
}
