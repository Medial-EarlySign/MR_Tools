// Perform hyper-parameters tuning

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "qo_runner.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#ifndef  __unix__
#define NOMINMAX
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

	// Read and select parameters options
	vector<map<string, string> > runOptions;
	string inConfigFile = vm["config"].as<string>();
	int nRuns = vm.count("nRuns") ? vm["nRuns"].as<int>() : -1;
	get_options(inConfigFile, nRuns, runOptions);

	// Variables
	string dirName = vm["dir"].as<string>();
	string prefix = vm["prefix"].as<string>();

	// Read header of condor runner
	vector<string> condor_runner;
	vector<string> commands;
	string inCondor = vm["inCondor"].as<string>();
	string command = vm["command"].as<string>();

	read_condor_runner(inCondor, condor_runner);

	string logger;
	if (vm.count("log"))
		logger = vm["log"].as<string>();
	else
		logger = dirName + "/condor.log";

	condor_runner.push_back("log = " + logger);
	condor_runner.push_back("executable = " + command);
	condor_runner.push_back("");

	// Generate commands and files
	for (int i = 0; i < runOptions.size(); i++) {
		string subDirName = dirName + "/" + prefix + "." + to_string(i);
		create_directory(subDirName);

		string configName = subDirName + "/config.txt";
		create_config_file(configName, subDirName, runOptions[i]);

		condor_runner.push_back("arguments = " + configName);
		condor_runner.push_back("output = " + subDirName + "/stdout");
		condor_runner.push_back("error = " + subDirName + "/stderr");
		condor_runner.push_back("queue\n\n");

		commands.push_back(command + " " + configName + " > " + subDirName + "/stdout 2> " + subDirName + "/stderr");
	}

	// Generate condor runner
	string outCondor = vm["outCondor"].as<string>();
	write_file(outCondor, condor_runner);

	// Generate commands
	if (vm.count("outCommands")) {
		string outCommands = vm["outCommands"].as<string>();
		write_file(outCommands, commands);
	}

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
			("prefix", po::value<string>()->default_value("quasi_oracle"), "sub-directories prefix")
			("inCondor", po::value<string>()->default_value(string(pPath) + "/Tools/quasi_oracle/qo_runner/condor_header.txt"), "condor-runner skeleton file")
			("outCondor", po::value<string>()->default_value("condor_runner"), "condor-runner file")
			("config", po::value<string>()->required(), "config file with options")
			("nRuns", po::value<int>(), "optional number of parameters combinations to check")
			("command", po::value<string>()->default_value(string(pPath)+"/Tools/quasi_oracle/Linux/Release/quasi_oracle"), "command to run")
			("log", po::value<string>(), "condor log file, if not given, use $dir/condor.log")
			("outCommands", po::value<string>(), "output commands file")
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

// Get options list
// Options are:
//	[field@]key	value
//	[field@]key	val1,val2,...
//	[field@]key	from,to,step
// field@key will be translated to: key	field=X;....
void get_options(string& paramsFile, int nRuns, vector<map<string, string> >& options) {

	map<string, vector<string> > optimizationOptions;
	int nOptions = read_optimization_ranges(paramsFile, optimizationOptions);
	if (nRuns < 0)
		nRuns = nOptions;
	float prob = (nRuns + 0.0) / nOptions;

	if (prob < 0.5) {
		// Select randomly
		unordered_set<string> selected;
		while (selected.size() < nRuns) {
			string option_s;
			map<string, string> option;

			for (auto& rec : optimizationOptions) {
				int index = rec.second.size() * (globalRNG::rand() / (globalRNG::max() + 0.0));
				option[rec.first] = rec.second[index];
				option_s += "," + rec.second[index];
			}

			if (selected.find(option_s) == selected.end()) {
				selected.insert(option_s);
				options.push_back(option);
			}
		}
	}
	else {
		// Select systematically
		vector<string> paramNames;
		for (auto& rec : optimizationOptions)
			paramNames.push_back(rec.first);
		int nParams = (int) paramNames.size();
		vector<int> pointers(nParams, 0);
		int index = 0;
		while (1) {
			map<string, string> option;
			for (int i = 0; i < nParams; i++)
				option[paramNames[i]] = optimizationOptions[paramNames[i]][pointers[i]];
			options.push_back(option);

			// Next
			int idx = (int) pointers.size() - 1;
			while (idx >= 0 && pointers[idx] == optimizationOptions[paramNames[idx]].size() - 1)
				idx--;

			if (idx < 0)
				break;

			pointers[idx] ++;
			for (int j = idx + 1; j < nParams; j++)
				pointers[j] = 0;
		}

		random_shuffle(options.begin(), options.end());
		options.resize(nRuns);
		options.shrink_to_fit();
	}
}
int read_optimization_ranges(string& optFile, map<string, vector<string> >& optimizationOptions) {

	ifstream inf(optFile);
	if (!inf)
		MTHROW_AND_ERR("Cannot open %s for reading\n", optFile.c_str());

	string line;
	int nOptions = 0;
	vector<string> fields;

	while (getline(inf, line)) {
		boost::split(fields, line, boost::is_any_of("\t"));
		if (fields.size() == 4) {
			float val = stof(fields[1]);
			float to = stof(fields[2]);
			float step = stof(fields[3]);
			while (val <= to) {
				// Keep int as int ...
				if (int(val) == val)
					optimizationOptions[fields[0]].push_back(to_string(int(val)));
				else
					optimizationOptions[fields[0]].push_back(to_string(val));
				val += step;
			}

			if (nOptions == 0)
				nOptions = 1;
			nOptions *= (int) optimizationOptions[fields[0]].size();
		}
		else if (fields.size() == 2) {
			vector<string> options;
			boost::split(options, fields[1], boost::is_any_of(","));
			for (string& val : options)
				optimizationOptions[fields[0]].push_back(val);

			if (nOptions == 0)
				nOptions = 1;
			nOptions *= (int) optimizationOptions[fields[0]].size();

		}
		else
			MTHROW_AND_ERR("Cannot parse input line \'%s\'\n", line.c_str());
	}

	if (nOptions == 0) {
		MTHROW_AND_ERR("Cannot optimzize without options\n");
	}
	else
		MLOG("Options file contains %d combinations\n", nOptions);

	return nOptions;
}

// Create directory
void create_directory(string& name) {
	// Create Directory
#ifndef  __unix__
	CreateDirectoryA(name.c_str(), NULL);
#else
	const int dir_err = mkdir(name.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
	if (-1 == dir_err)
		MTHROW_AND_ERR("Cannot create directory %s\n", name.c_str());
#endif
}

// Create config file from options
void create_config_file(string& configName, string& subDirName, map<string, string>& runOption) {

	ofstream outf(configName);
	if (!outf.is_open())
		MTHROW_AND_ERR("Cannot open %s for writing\n", configName.c_str());

	map<string, vector<string> > outOptions;
	vector<string> fields;

	for (auto& rec : runOption) {
		boost::split(fields, rec.first, boost::is_any_of("@"));
		if (fields.size() == 2)
			outOptions[fields[1]].push_back(fields[0] + "=" + rec.second);
		else
			outOptions[fields[0]].push_back(rec.second);
	}

	if (outOptions.find("runDir") == outOptions.end())
		outOptions["runDir"] = { subDirName };

	for (auto& rec : outOptions)
		outf << rec.first << "\t" << boost::join(rec.second, ";") << "\n";

	outf.close();
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