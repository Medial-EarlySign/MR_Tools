// Perform hyper-parameters tuning

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "analyzer.h"
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

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	// Collect directories
	vector<string> directories;
	string dir = vm["dir"].as<string>();
	string prefix = vm["prefix"].as<string>();
	get_directories(dir, prefix, directories);

	// Collect parameters
	vector<set<string>> params;
	string config = vm["configFile"].as<string>();
	string inField = vm["inField"].as<string>();
	get_params(directories, config, inField, params);

	// Collect performance
	vector<float> performance;
	string perf = vm["performance"].as<string>();
	get_performance(directories, perf, performance);

	// Get performance means
	map<string, pair<int,float>> performanceMean;
	get_mean_performance(params, performance, performanceMean);

	// Print
	for (auto& rec : performanceMean)
		cout << "Mean (" << perf << ") for " << inField << ":" << rec.first << " = " << rec.second.second << " (" << rec.second.first << ")\n";

	// Max Performances.
	string mode = vm["mode"].as<string>();
	if (mode != "Max" && mode != "Min")
		MTHROW_AND_ERR("Allowed modes: Min/Max");

	float optPerfInd = 0;
	for (int i = 0; i < performance.size(); i++) {
		if ((mode == "Max" && performance[i] > performance[optPerfInd]) || (mode == "Min" && performance[i] < performance[optPerfInd]))
			optPerfInd = i;
	}
	cout << mode << " " << "Mean (" << perf << ") = " << performance[optPerfInd] << " at " << directories[optPerfInd] << "\n";

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
			("prefix", po::value<string>()->default_value("quasi_oracle"), "sub-directories prefix (comma separated)")
			("configFile", po::value<string>()->required(), "config files name")
			("performance", po::value<string>()->required(), "performance parameters to analyze: field@file,field@file,...")
			("inField", po::value<string>()->required(), "field to analyze")
			("mode",po::value<string>()->default_value("Max"), "look for Min/Max performance")
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


// Read config files and extract parameters
void get_params(vector<string>& directories, const string& config, const string& inField, vector<set<string>>& params) {

	params.resize(directories.size());
	for (unsigned int i = 0; i < params.size(); i++) {
		string fileName = directories[i] + "/" + config;

		ifstream inf(fileName);
		if (!inf.is_open())
			MTHROW_AND_ERR("Cannot open %s for reading\n", fileName.c_str());

		string line;
		vector<string> fields, subFields;
		while (getline(inf, line)) {
			boost::split(fields, line, boost::is_any_of("\t"));
			if (fields[0] == inField) {
				boost::split(subFields, fields[1], boost::is_any_of(";"));
				for (string& param : subFields)
					params[i].insert(param);
			}
		}
	}
}

void get_performance(vector<string>& directories, const string& perf, vector<float>& performance) {

	// Parse performance string
	vector<string> entries;
	boost::split(entries, perf, boost::is_any_of(","));

	map<string, unordered_set<string> > perf_by_file;
	int n_perf = 0;
	for (string& entry : entries) {
		vector<string> fields;
		boost::split(fields, entry, boost::is_any_of("@"));
		if (fields.size() != 2)
			MTHROW_AND_ERR("Cannot parse performance entry \'%s\'\n", entry.c_str());
		perf_by_file[fields[1]].insert(fields[0]);
		n_perf++;
	}

	MLOG("Analyzing:\n");
	for (auto& rec : perf_by_file) {
		MLOG("%s : ", rec.first.c_str());
		for (string key : rec.second)
			MLOG("%s ", key.c_str());
		MLOG("\n");
	}
	MLOG("\n");

	performance.assign(directories.size(),0);
	for (unsigned int i = 0; i < performance.size(); i++) {
		for (auto& rec : perf_by_file) {
			string fileName = directories[i] + "/" + rec.first;

			ifstream inf(fileName);
			if (!inf.is_open())
				MTHROW_AND_ERR("Cannot open %s for reading\n", fileName.c_str());

			string line;
			vector<string> fields;
			while (getline(inf, line)) {
				boost::split(fields, line, boost::is_any_of(" \t"));
				if (rec.second.find(fields[0]) != rec.second.end())
					performance[i] += stof(fields.back());
			}
		}
	}

	for (unsigned int i = 0; i < performance.size(); i++)
		performance[i] /= n_perf;

}

void get_mean_performance(vector<set<string>>& params, vector<float>& performance, map<string, pair<int, float>>& performanceMean) {

	for (unsigned int i = 0; i < params.size(); i++) {
		for (string param : params[i]) {
			performanceMean[param].first ++;
			performanceMean[param].second += performance[i];
		}
	}

	for (auto& rec : performanceMean)
		rec.second.second /= rec.second.first;
}
