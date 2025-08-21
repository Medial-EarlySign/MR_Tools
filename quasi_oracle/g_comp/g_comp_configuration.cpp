#include "g_comp_configuration.h"

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
	outf << "doTwoModels\t" << do_two_models << endl;
	outf << "includeOriginal\t" << include_original << endl;
	outf << "readInitial\t" << read_initial << endl;
	outf << "onlyInitial\t" << only_initial << endl;
	outf << "initialFile\t" << initialFile << endl;
	outf << "out\t " << out << endl;
	outf << "treatmentName\t" << treatmentName << endl;
	if (!treatmentTimeName.empty()) outf << "treatmentTimeName\t" << treatmentTimeName << endl;

	for (string key : {"initial","initial0","initial1","final"}) {
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
	vector<string> fields, subFields;
	map<string,int> types;

	while (getline(inf, line)) {
		boost::split(fields, line, boost::is_any_of("\t"));
		if (fields.size() != 2)
			MTHROW_AND_ERR("Cannot parse line \'%s\' in configuration file %s\n", line.c_str(), fileName.c_str());

		boost::split(subFields, fields[0], boost::is_any_of("_"));
		if (subFields.size() == 1) {
			if (fields[0] == "runDir") runDir = fields[1];
			else if (fields[0] == "repFile") repFile = fields[1];
			else if (fields[0] == "samplesFile") samplesFile = fields[1];
			else if (fields[0] == "featuresFile") featuresFile = fields[1];
			else if (fields[0] == "iteFile") iteFile = fields[1];
			else if (fields[0] == "nFolds") nFolds = stoi(fields[1]);
			else if (fields[0] == "readInitial") read_initial = stoi(fields[1]);
			else if (fields[0] == "onlyInitial") only_initial = stoi(fields[1]);
			else if (fields[0] == "initialFile") initialFile = fields[1];
			else if (fields[0] == "out") out = fields[1];
			else if (fields[0] == "treatmentName") treatmentName = fields[1];
			else if (fields[0] == "treatmentTimeName") treatmentTimeName = fields[1];
			else if (fields[0] == "doTwoModels") do_two_models = stoi(fields[1]);
			else if (fields[0] == "includeOriginal") include_original = stoi(fields[1]);
			else
				MTHROW_AND_ERR("Unknown fields \'%s\' in configuration file %s\n", fields[0].c_str(), fileName.c_str());
		}
		else if (subFields.size() == 2) {
			string key = subFields[0];
			if (key != "initial" && key != "initial0" && key != "initial1" && key != "final")
				MTHROW_AND_ERR("Cannot parse line \'%s\' in configuration file %s\n", line.c_str(), fileName.c_str());
			if (subFields[1] == "predictorName") predictorName[key] = fields[1];
			else if (subFields[1] == "predictorParams") predictorParams[key] = fields[1];
			else if (subFields[1] == "modelFile") modelFile[key] = fields[1];
			else if (subFields[1] == "calibrationParams") calibrationParams[key] = fields[1];
			else if (subFields[1] == "performanceFile") performanceFile[key] = fields[1];
			else if (subFields[1] == "modelAlts") modelAlts[key].push_back(fields[1]);
			else
				MTHROW_AND_ERR("Cannot parse line \'%s\' in configuration file %s\n", line.c_str(), fileName.c_str());
		}
		else
			MTHROW_AND_ERR("Cannot parse line \'%s\' in configuration file %s\n", line.c_str(), fileName.c_str());
	}

	// runDir - set to time-dependent name if not given
	if (runDir.empty()) {
		runDir = "g_comp." + pt::to_iso_string(pt::second_clock::local_time());
		// Create Directory
#ifndef  __unix__
		CreateDirectoryA(runDir.c_str(), NULL);
#else
		const int dir_err = mkdir(runDir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
		if (-1 == dir_err)
			MTHROW_AND_ERR("Cannot create directory %s\n", runDir.c_str());
#endif
	}

	// required
	if (out.empty())
		MTHROW_AND_ERR("Required parameter out not given\n");

	// Complete
	if (do_two_models)
		complete();

	// file names
	if (initialFile[0] != '/')
		initialFile= runDir + "/" + initialFile;

	if (!iteFile.empty() && iteFile[0] != '/')
		iteFile = runDir + "/" + iteFile;

	for (string key : {"initial", "initial0","initial1", "final"}) {
		if (!performanceFile[key].empty() && performanceFile[key][0] != '/')
			performanceFile[key] = runDir + "/" + performanceFile[key];

		if (calibrationParams[key].empty())
			calibrationParams[key] = defaultCalibrationParams;
	}
}

void::configuration::complete() {

	string base = "initial";
	for (string name : {"initial0", "initial1"}) {
		if (predictorName[name].empty())
			predictorName[name] = predictorName[base];

		if (predictorParams[name].empty())
			predictorParams[name] = predictorParams[base];

		if (modelFile[name].empty())
			modelFile[name] = modelFile[base];

		if (modelAlts[name].empty())
				modelFile[name] = modelFile[base];
	
		if (calibrationParams[name].empty()) 
			calibrationParams[name] = calibrationParams[base];

		if (performanceFile[name].empty())
			performanceFile[name] = name + "_" + performanceFile[base];
	}
}
