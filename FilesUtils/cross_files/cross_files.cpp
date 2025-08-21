// Cross files with headers

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "cross_files.h"
#include <iostream>

int main(int argc, char *argv[])
{

	int rc = 0;

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	// Handle Fields
	set<string> names1, names2;
	get_fields(vm, names1, names2);

	string file1 = vm["f1"].as<string>();
	string file2 = vm["f2"].as<string>();
	string common = vm["c"].as<string>();
	char separator = get_sep(vm["s"].as < string>());
	cross(file1, file2, separator, common, names1, names2);

}
// Cross files
void cross(string& file1, string&file2, char separator, string &common, set<string>& names1, set<string>& names2) {

	// Open files
	ifstream inf1, inf2;
	inf1.open(file1, ios::in);
	if (!inf1)
		throw("Cannot open " + file1);

	inf2.open(file2, ios::in);
	if (!inf2)
		throw("Cannot open " + file2);

	// Read headers
	vector<int> common1_cols, names1_cols;
	vector<int> common2_cols, names2_cols;

	string header = get_cols(inf1, file1, separator, common, names1, common1_cols, names1_cols,1);
	header += get_cols(inf2, file2, separator, common, names2, common2_cols, names2_cols,0);
	cout << header << "\n";

	// Collect from file2

	unordered_map<string, string> index;
	
	string inLine;
	vector<string> fields;

	int idx = 0;
	while (getline(inf2, inLine)) {
		mySplit(fields, inLine, separator);

		string key = get_string(fields, separator, common2_cols);
		index[key] = get_string(fields, separator, names2_cols);
	}

	// Check in file1 and print
	int c = 0;
	while (getline(inf1, inLine)) {
		mySplit(fields, inLine, separator);

		string key = get_string(fields, separator, common1_cols);
		if (index.find(key) != index.end())
			//			cout << key << separator << get_string(fields, separator, names1_cols) << separator << index[key] << endl;
			c++;
	}
	cerr << c << "\n";
}

void mySplit(vector<string>& fields, string line, char sep) {

	int start = 0, current = 0;
	fields.clear();
	while (current < line.size()) {
		if (line[current] == sep) {
			if (current > start)
				fields.push_back(line.substr(start, current - start));
			start = current + 1;
		}
		current++;
	}

	if (start != line.size())
		fields.push_back(line.substr(start, current - start));
}

string get_cols(ifstream& inf, string& file, char sep, string& common, set<string>& names, vector<int>& common_cols, vector<int>& names_cols, int first) {

	// Common fileds
	vector<string> common_v;
	mySplit(common_v, common, ',');
	set<string> common_s(common_v.begin(), common_v.end());

	string inLine;
	vector<string> fields, names1_v;

	if (!getline(inf, inLine))
		throw("Cannot read header from " + file);
	mySplit(fields, inLine, sep);

	for (int i = 0; i < fields.size(); i++) {
		if (common_s.find(fields[i]) != common_s.end()) {
			common_cols.push_back(i);
			common_s.erase(fields[i]);
		}

		if (names.find(fields[i]) != names.end()) {
			names_cols.push_back(i);
			names.erase(fields[i]);
		}
	}
	if (!common_s.empty())
		throw("Cannot find all common fields in " + file);
	if (!names.empty())
		throw("Cannot find all names in " + file);

	// Print to output 
	string header;
	if (first)
		header = get_string(fields, sep, common_cols); ;

	for (int col : names_cols)
		header += (sep + file + "_" + fields[col]); ;

	return header;
}

// Get string
inline string get_string(vector<string> fields, char sep, vector<int> cols) {

	string out;
	if (cols.size()) {
		out = fields[cols[0]];
		for (int i = 1; i < cols.size(); i++)
			out += (sep + fields[cols[i]]);
	}

	return out;
}

// Get Fields
void get_fields(po::variables_map& vm, set<string>& names1, set<string>&names2) {

	if (!(vm.count("n") || vm.count("n1") || vm.count("n2")))
		throw("no fields given. Quitting\n");

	vector<string> names;
	string names_s;

	if (vm.count("n1")) {
		string names_s = vm["n1"].as<string>();
		boost::split(names, names_s, boost::is_any_of(","));
		for (string name : names)
			names1.insert(name);
	}

	if (vm.count("n2")) {
		names_s = vm["n2"].as<string>();
		boost::split(names, names_s, boost::is_any_of(","));
		for (string name : names)
			names2.insert(name);
	}

	if (vm.count("n")) {
		names_s = vm["n"].as<string>();
		boost::split(names, names_s, boost::is_any_of(","));
		for (string name : names) {
			names1.insert(name);
			names2.insert(name);
		}
	}
}

// Separator
char get_sep(string code) {
	
	if (code == "tab") return '\t';
	else return code[0];
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("f1", po::value<string>()->required(), "first file")
			("f2", po::value<string>()->required(), "second file")
			("c", po::value<string>()->required(), "common fields (comma separated)")
			("n1", po::value<string>(), "first file fields (comma separated)")
			("n2", po::value<string>(), "second file fields (comma separated)")
			("n", po::value<string>(), "both file fields (comma separated)")
			("s", po::value<string>()->default_value("tab"),"tab/char")
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