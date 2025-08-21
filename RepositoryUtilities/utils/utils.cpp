#define _CRT_SECURE_NO_WARNINGS

#include "utils.h"

int main(int argc, char *argv[])
{
	int rc = 0;

	// Running parameters
	po::variables_map vm;
	assert(read_run_params(argc, argv, vm) != -1);

	string configFile = vm["config"].as<string>();
	string util = vm["util"].as<string>();

	if (util == "get_members")
		get_members(vm, configFile);
	else if (util == "get_read_code_cases")
		get_read_code_cases(vm, configFile);
	else if (util == "get_drug_cases")
		get_drug_cases(vm, configFile);
	else
		cerr << "Unknown utility (not one of get_members/get_read_code_cases/get_drug_cases) :  " << util << endl;

}

int read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("config", po::value<string>()->required(), "configuration file")
			("util", po::value<string>()->required(), "utility to apply")

			// For Get Members
			("set", po::value<string>(), "set name")
			("section", po::value<string>(), "dictionary section")

			// For get read-code cases
			("read_codes",po::value<string>(),"read codes file")

			// For get drug cases
			("drugs", po::value<string>(), "drugs file")


			("ids", po::value<string>(), "ids file")
			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(0);

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

// Get Members of a set
void get_members(po::variables_map& vm, string& configFile) {

	assert(vm.count("set"));
	vector<string> sets;
	sets.push_back(vm["set"].as<string>());

	MedPidRepository rep;
	rep.init(configFile);

	string section = vm.count("section") ? vm["section"].as<string>() : "DEFAULT";
	cerr << "Dictionary section: " << section << endl;
	int sectionId = rep.dict.section_id(section);

	vector<char> lut;
	rep.dict.prep_sets_lookup_table(sectionId, sets, lut);

	for (unsigned int i = 0; i < lut.size(); i++) {
		if (lut[i] > 0) {
			string name = rep.dict.dicts[sectionId].name(i);
			cout << i << "\t" << name << endl;
		}
	}

}

// Get Appearances of a set of read codes
void get_read_code_cases(po::variables_map& vm, string& configFile) {

	// Get Read Codes
	assert(vm.count("read_codes"));
	string file = vm["read_codes"].as<string>();

	vector<string> readCodes;
	int rc = read_list(file, readCodes);
	assert(rc == 0);

	// Get ids
	vector<int> ids;
	if (vm.count("ids")) {
		string idsFile = vm["ids"].as<string>();
		read_ids_list(idsFile, ids);
	}

	// Read Repository
	MedPidRepository rep;
	vector<string> signals = { "RC" };
	rep.read_all(configFile, ids, signals);

	// Prepare Look-Up Table
	int sectionId = rep.dict.section_id("RC");
	int signalId = rep.dict.id("RC");
	vector<char> lut;
	rep.dict.prep_sets_lookup_table(sectionId,readCodes, lut);

	// Collect
	int len;
	for (int pid : rep.all_pids_list) {
		SDateVal *rc = (SDateVal *)rep.get(pid, signalId, len);
		for (int i = 0; i < len; i++) {
			if (lut[(int)rc[i].val]) {
				int value = (int)rc[i].val;
				string desc = rep.dict.dict(sectionId)->name(value);
				cout << pid << "\t" << rc[i].date << "\t" << value << "\t" << desc << "\n";
			}
		}
	}
}

// Get Appearances of a set of drugs
void get_drug_cases(po::variables_map& vm, string& configFile) {

	// Get Drugs
	assert(vm.count("drugs"));
	string file = vm["drugs"].as<string>();

	vector<string> drugCodes;
	int rc = read_list(file, drugCodes);
	assert(rc == 0);

	// Get ids
	vector<int> ids;
	if (vm.count("ids")) {
		string idsFile = vm["ids"].as<string>();
		read_ids_list(idsFile, ids);
	}

	// Read Repository
	MedPidRepository rep;
	vector<string> signals = { "Drug" };
	rep.read_all(configFile, ids, signals);

	// Prepare Look-Up Table
	int sectionId = rep.dict.section_id("Drug");
	int signalId = rep.dict.id("Drug");
	vector<char> lut;
	rep.dict.prep_sets_lookup_table(sectionId, drugCodes, lut);

	// Collect
	int len;
	for (int pid : rep.all_pids_list) {
		SDateShort2 *drug = (SDateShort2 *)rep.get(pid, signalId, len);
		for (int i = 0; i < len; i++) {
			if (lut[(int)drug[i].val1]) {
				int value = (int)drug[i].val1;
				string desc = rep.dict.dict(sectionId)->name(value);
				cout << pid << "\t" << drug[i].date << "\t" << value << "\t" << (int)drug[i].val2 << "\t" << desc << "\n";
			}
		}
	}
}


int read_list(const string& fname, vector<string>& list) {

	ifstream inf(fname);
	if (!inf.is_open()) {
		fprintf(stderr, "Cannot open %s for reading\n", fname.c_str());
		return -1;
	}

	string name;
	while (!inf.eof()) {
		inf >> name;
		if (!inf.eof())
			list.push_back(name);
	}

	inf.close();
	return 0;
}

int read_ids_list(const string& fname, vector<int>& ids) {

	ifstream inf(fname);
	if (!inf.is_open()) {
		fprintf(stderr, "Cannot open %s for reading\n", fname.c_str());
		return -1;
	}

	int id;
	while (!inf.eof()) {
		inf >> id;
		if (!inf.eof())
			ids.push_back(id);
	}

	inf.close();
	return 0;
}

