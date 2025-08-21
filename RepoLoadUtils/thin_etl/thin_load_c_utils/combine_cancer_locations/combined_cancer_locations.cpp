// Combined Cancer_Location files

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "combine_cancer_locations.h"

int main(int argc, char *argv[])
{

	fprintf(stderr, "Combining Cancer_Location files\n");

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	// Get all input files
	vector<string> files;
	get_files(vm["in_dir"].as<string>(), vm["in_prefix"].as<string>(), files);

	// Read Translation table
	vector<vector<string>> translations;
	read_translation_table(vm["table"].as<string>(), translations);

	// output file
	string outFile = vm["out_file"].as<string>();
	ofstream outf(outFile);
	if (!outf) {
		string err = "Cannot open " + outFile + " for writing\n";
		throw err;
	}

	// Do your stuff
	
	for (string& inFile : files) {
		cerr << "Working on " << inFile << "\n";
		handle_file(inFile, outf, translations);
	}
	return 0;
}

// Read input parametesr
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("in_dir", po::value<string>()->required(), "input files directory")
			("in_prefix", po::value<string>()->required(), "input files prefix")
			("out_file", po::value<string>()->required(), "output file")
			("table", po::value<string>()->required(), "input cancer types table")
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

// Get list of files
void get_files(string dir, string prefix, vector<string>& files) {

	if (!fs::exists(dir) || !fs::is_directory(dir)) {
		string err = "error: cannot read directory " + dir;
		throw(err);
	}

	for (auto const& entry : fs::recursive_directory_iterator(dir)) {
		if (fs::is_regular_file(entry)) {
			string name = entry.path().filename().string();
			if (name.substr(0, prefix.length()) == prefix) 
				files.push_back(dir + "/" + name);
		}
	}
	cerr << "Collected " << files.size() << " files\n";
}

// Read Table
void read_translation_table(string file, vector<vector<string>>& table) {

	ifstream inf(file);
	if (!inf) {
		string err = "Cannot open " + file + " for reading\n";
		throw err;
	}

	string line;
	vector<string> fields;
	table.clear();

	bool header = true;
	while (getline(inf, line)) {
		if (header)
			header = false;
		else {
			boost::split(fields, line, boost::is_any_of("\t"));
			table.push_back(fields);
		}
	}

	cerr << "Read " << table.size() << " lines from " << file << "\n";
	inf.close();
	return;
}

// Do the work
void handle_file(string& inFile, ofstream& outf, vector<vector<string>>& table) {

	ifstream inf(inFile);
	if (!inf) {
		string err = "Cannot open " + inFile + " for reading\n";
		throw err;
	}

	string line;
	vector<string> fields;

	bool header = true;
	int pid = -1;
	vector<vector<string>> idLines;

	while (getline(inf, line)) {
		if (header)
			header = false;
		else {
			boost::split(fields, line, boost::is_any_of(","));
			int id = stoi(fields[1]);
			if (pid != -1 && id != pid) {
				handle_id(idLines, outf, table);
				idLines.clear();
			}
			idLines.push_back(fields);
		}
	}

	handle_id(idLines, outf, table);
}

#define STATUS_FIELD 11
#define DATE_FIELD 2
#define SAME_CASE_GAP 62

// Handle single id information) {
void handle_id(vector<vector<string>>& idLines, ofstream& outf, vector<vector<string>>& table) {

	int n = (int)idLines.size();

	// Fix dates: if cancer after less than SAME_CASE_GAP days from anc/morph
	bool anc_morph = (idLines[0][STATUS_FIELD] == "anc" || idLines[0][STATUS_FIELD] == "morph");
	int prev_time = med_time_converter.convert_date(stoi(idLines[0][DATE_FIELD]), MedTime::Days);

	for (int i=1; i<n; i++) {
		if (idLines[i][STATUS_FIELD] == "cancer" && anc_morph) {
			int time_diff =med_time_converter..add_subtract_time()

	}



}
		
