#include "unite_admissions.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
	CmdArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;
	
	// Read File
	vector<admin> admissions; 
	read_admissions(args.file, admissions);

	// Unite Overlapping admissions
	process_admissions(admissions);
	
	// Write File
	write_admissions(args.file, admissions);

	return 0;
}

// Command arguments
CmdArgs::CmdArgs() {

	po::options_description desc("Program options");

	desc.add_options()
		("file", po::value<string>(&file)->required(),"input/output file")
		;

	init(desc);
}

// Read admissions
void read_admissions(string& file, vector<admin>& admissions) {
	
	admissions.clear();
	
	ifstream fp;
	fp.open(file);
	if (!fp.is_open())
		MTHROW_AND_ERR("Unable to open file: %s\n", file.c_str());
	
	string line;
	vector<string> fields;
	while (getline(fp, line)) {
		boost::trim(line);
		boost::algorithm::split(fields, line, boost::is_any_of("\t"));

		if (fields.size() != 5)
			MTHROW_AND_ERR("Cannot read input line :%s\n", line.c_str());

		admin newAdmin(fields);
		admissions.push_back(newAdmin);
	}
	MLOG("Read %d lines from %s\n", (int)admissions.size(), file.c_str());
}

// Process 
void process_admissions(vector<admin>& admissions) {

	unsigned int outIdx = 0;
	for (unsigned int idx = 1; idx < admissions.size(); idx++) {
		if (admissions[idx].pid != admissions[outIdx].pid || admissions[idx].start > admissions[outIdx].end)
			admissions[++outIdx] = admissions[idx];
		else {
			admissions[outIdx].type = "combined";
			if (admissions[idx].end > admissions[outIdx].end)
				admissions[outIdx].end = admissions[idx].end;
		}
	}

	admissions.resize(outIdx);
	MLOG("United to %d admissions\n", (int)admissions.size());

}

// Write
void write_admissions(string& file, vector<admin>& admissions) {

	ofstream fp;
	fp.open(file);
	if (!fp.is_open())
		MTHROW_AND_ERR("Unable top open file %s for writing\n", file.c_str());

	for (auto& admission : admissions)
		fp << admission.pid << "\tADMISSION\t" << admission.start << "\t" << admission.end << "\t" << admission.type << "\n";
}
