// Split file by id

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "split_by_id.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#define MAX_LINE 16384

int main(int argc, char *argv[])
{

	int rc = 0;

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	string inFile = vm["in"].as<string>();
	string outPref = vm["pref"].as<string>();
	int idCol = vm["col"].as<int>();
	int nDigits = vm["ndigit"].as<int>();
	int nFields = vm["nFields"].as<int>();
	int minId = vm["minId"].as<int>();

	ifstream ifp(inFile);
	if (!ifp.is_open())
		MTHROW_AND_ERR("Cannot open %s for reading\n", inFile.c_str());
	map<string, ofstream> ofps;

	string line;
	vector<string> fields, outFields;

	while (getline(ifp, line)) {
		boost::split(fields, line, boost::is_any_of("\t"));

		if (outFields.size()>=nFields && line[0]>='0' && line[0]<='9' && stoi(line)>=minId) {
			string key = outFields[idCol].substr(0, nDigits);
			string outFile = outPref + "." + key;
			if (ofps.find(outFile) == ofps.end()) {
				ofps[outFile].open(outFile, ofstream::out);
				if (!ofps[outFile].is_open())
					MTHROW_AND_ERR("Cannot open %s for writing\n", outFile.c_str());
			}

			string outLine = boost::join(outFields, "\t");
			ofps[outFile] << outLine << "\n";
			outFields.clear();
		}

		if (outFields.size()) {
			outFields.back() += " ***newline*** " + fields[0];
			outFields.insert(outFields.end(), fields.begin() + 1, fields.end());
		}
		else
			outFields = fields;
	}

	// Last line
	string key = outFields[idCol].substr(0, nDigits);
	string outFile = outPref + "." + key;
	if (ofps.find(outFile) == ofps.end()) {
		ofps[outFile].open(outFile, ofstream::out);
		if (!ofps[outFile].is_open())
			MTHROW_AND_ERR("Cannot open %s for writing\n", outFile.c_str());
	}

	string outLine = boost::join(outFields, "\t");
	boost::replace_all(outLine, "\n", "**newline**");
	ofps[outFile] << outLine << "\n";
}


// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("in", po::value<string>()->required(), "input file")
			("pref", po::value<string>()->required(), "output prefix")
			("col", po::value<int>()->default_value(0), "columns of id")
			("ndigit", po::value<int>()->default_value(2),"# of leading digits to consider in id")
			("nFields", po::value<int>()->default_value(0),"required # of fields per line")
			("minId", po::value<int>()->default_value(0), "minimal int to consider as id")
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