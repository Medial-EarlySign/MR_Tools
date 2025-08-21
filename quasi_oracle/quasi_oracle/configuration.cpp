#include "configuration.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#ifndef  __unix__
#include <windows.h>
#else
#include <sys/stat.h>
#endif

// Functions
void configuration::write_to_file(const string& fileName) {


	ofstream outf(fileName);
	if (!outf.is_open())
		MTHROW_AND_ERR("Cannot open %s for writing\n", fileName.c_str());

	if (!runDir.empty()) outf << "runDir\t" << runDir << endl;
	if (!repFile.empty()) outf << "repFile\t" << repFile << endl;
	if (!samplesFile.empty()) outf << "samplesFile\t" << samplesFile << endl;
	if (!featuresFile.empty()) outf << "featuresFile\t" << featuresFile << endl;
	if (!iteFile.empty()) outf << "iteFile\t" << iteFile << endl;
	outf << "nFolds\t" << nFolds << endl;
	outf << "readE\t" << read_e << endl;
	outf << "onlyE\t" << only_e << endl;
	outf << "eFile\t" << eFile << endl;
	outf << "readM\t" << read_m << endl;
	outf << "onlyM\t" << only_m << endl;
	outf << "mFile\t" << mFile << endl;
	outf << "out\t " << out << endl;
	outf << "treatmentName\t" << treatmentName << endl;
	if (!treatmentTimeName.empty()) outf << "treatmentTimeName\t" << treatmentTimeName << endl;

	for (string key : {"e", "m", "ite"}) {
		if (!predictorName[key].empty()) outf << key << "_predictorName\t" << predictorName[key] << endl;
		if (!predictorParams[key].empty()) outf << key << "_predictorParams\t" << predictorParams[key] << endl;
		if (!modelFile[key].empty()) outf << key << "_modelFile\t" << modelFile[key] << endl;
		if (!calibrationParams[key].empty()) outf << key << "_calibrationParams\t" << calibrationParams[key] << endl;
		if (!performanceFile[key].empty()) outf << key << "_performanceFile\t" << performanceFile[key] << endl;
		if (!modelAlts[key].empty()) outf << key << "_modelAlts\t" << boost::join(modelAlts[key], ",") << endl;
	}
}
void configuration::write_to_file() {
	write_to_file(runDir + "/out_config.txt");
}
void configuration::read_from_file(const string& fileName) {

	ifstream inf(fileName);
	if (!inf.is_open())
		MTHROW_AND_ERR("Cannot open %s for reading\n", fileName.c_str());

	string line;
	vector<string> fields,subFields; 
	while (getline(inf, line)) {
		boost::split(fields, line, boost::is_any_of("\t"));
		if (fields.size() != 2)
			MTHROW_AND_ERR("Cannot parse line \'%s\' in configuration file %s\n", line.c_str(), fileName.c_str());

		boost::split(subFields, fields[0], boost::is_any_of("_"));
		if (subFields.size()==1) {
			if (fields[0] == "runDir") runDir = fields[1];
			else if (fields[0] == "repFile") repFile = fields[1];
			else if (fields[0] == "samplesFile") samplesFile = fields[1];
			else if (fields[0] == "featuresFile") featuresFile = fields[1];
			else if (fields[0] == "iteFile") iteFile = fields[1];
			else if (fields[0] == "nFolds") nFolds = stoi(fields[1]);
			else if (fields[0] == "readE") read_e = stoi(fields[1]);
			else if (fields[0] == "onlyE") only_e = stoi(fields[1]);
			else if (fields[0] == "eFile") eFile = fields[1];
			else if (fields[0] == "readM") read_m = stoi(fields[1]);
			else if (fields[0] == "onlyM") only_m = stoi(fields[1]);
			else if (fields[0] == "mFile") mFile = fields[1];
			else if (fields[0] == "out") out = fields[1];
			else if (fields[0] == "treatmentName") treatmentName = fields[1];
			else if (fields[0] == "treatmentTimeName") treatmentTimeName = fields[1];
			else
				MTHROW_AND_ERR("Unknown fields \'%s\' in configuration file %s\n", fields[0].c_str(), fileName.c_str());
		}
		else if (subFields.size() == 2) {
			string key = subFields[0];
			if (key != "e" && key != "m" && key != "ite")
				MTHROW_AND_ERR("Cannot parse line \'%s\' in configuration file %s\n", line.c_str(), fileName.c_str());
			if (subFields[1] == "predictorName") predictorName[key] = fields[1];
			else if (subFields[1] == "predictorParams") predictorParams[key] = fields[1];
			else if (subFields[1] == "modelFile") modelFile[key] = fields[1];
			else if (subFields[1] == "calibrationParams") calibrationParams[key] = fields[1];
			else if (subFields[1] == "performanceFile") performanceFile[key] = fields[1];
			else if (subFields[1] == "tmodelAlts") modelAlts[key].push_back(fields[1]);
			else
				MTHROW_AND_ERR("Cannot parse line \'%s\' in configuration file %s\n", line.c_str(), fileName.c_str());
		} else
			MTHROW_AND_ERR("Cannot parse line \'%s\' in configuration file %s\n", line.c_str(), fileName.c_str());
	}

	// runDir - set to time-dependent name if not given
	if (runDir.empty()) {
		runDir = "quasi_oracle." + pt::to_iso_string(pt::second_clock::local_time());
		// Create Directory
#ifndef  __unix__
		CreateDirectoryA(runDir.c_str(), NULL);
#else
		const int dir_err = mkdir(runDir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
		if (-1 == dir_err)
			MTHROW_AND_ERR("Cannot create directory %s\n", runDir.c_str());
#endif
	}

	// required params
	if (eFile.empty())
		MTHROW_AND_ERR("Required parameter eFile not given\n");
	if (mFile.empty())
		MTHROW_AND_ERR("Required parameter mFile not given\n");
	if (out.empty())
		MTHROW_AND_ERR("Required parameter out not given\n");

	// file names
	if (eFile[0] != '/')
		eFile = runDir + "/" + eFile;
	if (mFile[0] != '/')
		mFile = runDir + "/" + mFile;

	for (string key : {"e", "m", "ite"}) {
		if (!performanceFile[key].empty() && performanceFile[key][0] != '/')
			performanceFile[key] = runDir + "/" + performanceFile[key];

		if (calibrationParams[key].empty())
			calibrationParams[key] = defaultCalibrationParams;
	}
}
