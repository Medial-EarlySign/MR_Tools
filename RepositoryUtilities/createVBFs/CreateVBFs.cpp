// Create virtual bin files for learn/predict.
#define _CRT_SECURE_NO_WARNINGS

#include "CreateVBFs.h"
char genders[2][1024] = { "men","women" };
char allGenders[3][1023] = { "men","women","combined" };

int main(int argc, char *argv[])
{
	int rc = 0;

	// Running parameters
	po::variables_map vm;
	if (readRunParams(argc, argv, vm) < 0) {
		fprintf(stderr, "readRunParams failed\n");
		return -1;
	}

	string configFile = vm["config"].as<string>();
	string group = vm["group"].as<string>();
	string outDir = vm["out"].as<string>();
	string fileName = vm["name"].as<string>();
	int nfolds = vm["nfold"].as<int>();

	bool useIdLists = vm["use_id_lists"].as<bool>();
	bool skipInternal = vm["skip_internal"].as<bool>();
	bool skipExternal = vm["skip_external"].as<bool>();

	// Read repository
	MLOG("Before reading config file %s\n", vm["config"].as<string>().c_str());

	// Create Id-List Files
	if (!useIdLists) {
		if (createIdLists(configFile, outDir, nfolds, skipInternal, skipExternal) < 0) {
			fprintf(stderr, "createIdsList failed\n");
			return -1;
		}
	}

	// Create VBFs
	if (createVBFs(configFile, group, outDir, fileName, nfolds, skipInternal, skipExternal) < 0) {
		fprintf(stderr, " createVBFs failed\n");
		return -1;
	}

	return 0;
}

// Read Parameters
int readRunParams(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("config", po::value<string>()->required(), "conversion confifuration file")
			("group", po::value<string>()->required(), "cancer group")
			("out", po::value<string>()->required(), "output directory")
			("name", po::value<string>()->required(), "name of files")
			("nfold", po::value<int>()->default_value(8), "cross validation folds")
			("use_id_lists", po::bool_switch()->default_value(false), "use existing id-lists files")
			("skip_internal", po::bool_switch()->default_value(false), "skip generation of internal validation files")
			("skip_external", po::bool_switch()->default_value(false), "skip generation of external validation files");

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

// Write id lists to files
int createIdLists(const string& configFile, const string& outDir, int nfolds, bool skipInternal, bool skipExternal) {

	MedRepository rep;
	if (rep.read_all(configFile) < 0) {
		MERR("Cannot read all repository %s\n", configFile.c_str());
		return -1;
	}

	map<string, map<string,vector<int> > > ids;
	int len;

	for (unsigned int j = 0; j < rep.index.pids.size(); j++) {
		int id = rep.index.pids[j];

		SVal *gender = (SVal *)rep.get(id, "GENDER", len);
		if (len != 1) {
			fprintf(stderr, "Cannot find GENDER for %d\n", id);
			return -1;
		}

		SVal *train = (SVal *)rep.get(id, "TRAIN", len);
		if (len != 1) {
			fprintf(stderr, "Cannot find TRAIN for %d\n", id);
			return -1;
		}

		string gender_s = (gender[0].val == 1) ? "men" : "women";
		if (train[0].val == 1)
			ids["Train"][gender_s].push_back(id);
		else if (train[0].val == 2)
			ids["Internal"][gender_s].push_back(id);
		else
			ids["External"][gender_s].push_back(id);
	}

	// Train - full
	for (int iGender = 0; iGender < 2; iGender++) {
		string fileName = outDir + "/Train/" + genders[iGender] + "_id_list";
		if (writeIdsToFile(fileName, ids["Train"][genders[iGender]]) < 0) {
			fprintf(stderr, "Cannot write ids to %s\n", fileName.c_str());
			return -1;
		}
	}

	vector<int> allIds(ids["Train"]["men"]);
	allIds.insert(allIds.end(), ids["Train"]["women"].begin(), ids["Train"]["women"].end());
	string fileName = outDir + "/Train/combined_id_list";
	if (writeIdsToFile(fileName, allIds) < 0) {
		fprintf(stderr, "Cannot write ids to %s\n", fileName.c_str());
		return -1;
	}


	// Train - folds
	map<string, int> foldSize;
	
	boost::mt19937 state;
	randomGen rand(state);

	for (int iGender = 0; iGender < 2; iGender++) {	
		random_shuffle(ids["Train"][genders[iGender]].begin(), ids["Train"][genders[iGender]].end(), rand);
		foldSize[genders[iGender]] = (int) ids["Train"][genders[iGender]].size() / nfolds;
	}

	char fileName_cs[1024];
	for (int iFold = 0; iFold < nfolds; iFold++) {
		
		map<string, vector<int> > trainIds, testIds;

		for (int iGender = 0; iGender < 2; iGender++) {
			vector<int>& currentIds = ids["Train"][genders[iGender]];

			for (int i = 0; i < currentIds.size(); i++) {
				if (i < iFold*foldSize[genders[iGender]] || (iFold != nfolds - 1 && i >= (iFold + 1)*foldSize[genders[iGender]])) // Train
					trainIds[genders[iGender]].push_back(currentIds[i]);
				else  // Test
					testIds[genders[iGender]].push_back(currentIds[i]);
			}

			// Train
			sprintf(fileName_cs, "%s/Train/SplitData/%s.train%d.id_list", outDir.c_str(), genders[iGender], iFold+1);

			if (writeIdsToFile(fileName_cs, trainIds[genders[iGender]]) < 0) {
				fprintf(stderr, "Cannot write ids to %s\n", fileName.c_str());
				return -1;
			}

			// Test
			sprintf(fileName_cs, "%s/Train/SplitData/%s.test%d.id_list", outDir.c_str(), genders[iGender], iFold+1);

			if (writeIdsToFile(fileName_cs, testIds[genders[iGender]]) < 0) {
				fprintf(stderr, "Cannot write ids to %s\n", fileName.c_str());
				return -1;
			}
		}

		// Combined train
		vector<int> allIds(trainIds["men"]);
		allIds.insert(allIds.end(), trainIds["women"].begin(), trainIds["women"].end());

		sprintf(fileName_cs, "%s/Train/SplitData/combined.train%d.id_list", outDir.c_str(), iFold+1);
		if (writeIdsToFile(fileName_cs, allIds) < 0) {
			fprintf(stderr, "Cannot write ids to %s\n", fileName_cs);
			return -1;
		}

		// Combined test
		allIds.clear();
		allIds.insert(allIds.end(), testIds["men"].begin(), testIds["men"].end());
		allIds.insert(allIds.end(), testIds["women"].begin(), testIds["women"].end());

		sprintf(fileName_cs, "%s/Train/SplitData/combined.test%d.id_list", outDir.c_str(), iFold+1);
		if (writeIdsToFile(fileName_cs, allIds) < 0) {
			fprintf(stderr, "Cannot write ids to %s\n", fileName_cs);
			return -1;
		}	
	}


	// Internal
	if (!skipInternal) {
		for (int iGender = 0; iGender < 2; iGender++) {
			string fileName = outDir + "/IntrnlV/" + genders[iGender] + "_id_list";
			if (writeIdsToFile(fileName, ids["Internal"][genders[iGender]]) < 0) {
				fprintf(stderr, "Cannot write ids to %s\n", fileName.c_str());
				return -1;
			}
		}

		vector<int> allIds(ids["Internal"]["men"]);
		allIds.insert(allIds.end(), ids["Internal"]["women"].begin(), ids["Internal"]["women"].end());
		string fileName = outDir + "/IntrnlV/combined_id_list";
		if (writeIdsToFile(fileName, allIds) < 0) {
			fprintf(stderr, "Cannot write ids to %s\n", fileName.c_str());
			return -1;
		}
	}

	// External
	if (!skipExternal) {
		for (int iGender = 0; iGender < 2; iGender++) {
			string fileName = outDir + "/ExtrnlV/" + genders[iGender] + "_id_list";
			if (writeIdsToFile(fileName, ids["External"][genders[iGender]]) < 0) {
				fprintf(stderr, "Cannot write ids to %s\n", fileName.c_str());
				return -1;
			}
		}

		vector<int> allIds(ids["External"]["men"]);
		allIds.insert(allIds.end(), ids["External"]["women"].begin(), ids["External"]["women"].end());
		string fileName = outDir + "/ExtrnlV/combined_id_list";
		if (writeIdsToFile(fileName, allIds) < 0) {
			fprintf(stderr, "Cannot write ids to %s\n", fileName.c_str());
			return -1;
		}
	}


	return 0;
}

// Create Virtual Bin Files
int createVBFs(string& config, string& group, string& outDir, string& name, int nfolds, bool skipInternal, bool skipExternal) {

	// Train - full
	for (int iGender = 0; iGender < 3; iGender++) {
		string fileName = outDir + "/Train/" + allGenders[iGender] + "_" + name + ".bin";
		string idsFileName = outDir + "/Train/" + allGenders[iGender] + "_id_list";
		if (createVBF(fileName, config, group, idsFileName) < 0) {
			fprintf(stderr, "Cannot create Virtual Bin File %s\n", fileName.c_str());
			return -1;
		}
	}

	// Train - folds
	char fileName_cs[1024], idsFileName_cs[1024];
	for (int iFold = 0; iFold < nfolds; iFold++) {
		for (int iGender = 0; iGender < 3; iGender++) {
			sprintf(fileName_cs, "%s/Train/SplitData/%s_%s.train%d.bin", outDir.c_str(), allGenders[iGender], name.c_str(), iFold+1);
			sprintf(idsFileName_cs, "%s/Train/SplitData/%s.train%d.id_list", outDir.c_str(), allGenders[iGender], iFold+1);
			if (createVBF(fileName_cs, config, group, idsFileName_cs) < 0) {
				fprintf(stderr, "Cannot create Virtual Bin File %s\n", fileName_cs);
				return -1;
			}

			sprintf(fileName_cs, "%s/Train/SplitData/%s_%s.test%d.bin", outDir.c_str(), allGenders[iGender], name.c_str(), iFold+1);
			sprintf(idsFileName_cs, "%s/Train/SplitData/%s.test%d.id_list", outDir.c_str(), allGenders[iGender], iFold+1);
			if (createVBF(fileName_cs, config, group, idsFileName_cs) < 0) {
				fprintf(stderr, "Cannot create Virtual Bin File %s\n", fileName_cs);
				return -1;
			}
		}
	}

	// Internal
	if (!skipInternal) {
		for (int iGender = 0; iGender < 3; iGender++) {
			string fileName = outDir + "/IntrnlV/" + allGenders[iGender] + "_validation.bin";
			string idsFileName = outDir + "/IntrnlV/" + allGenders[iGender] + "_id_list";
			if (createVBF(fileName, config, "", idsFileName) < 0) {
				fprintf(stderr, "Cannot create Virtual Bin File %s\n", fileName_cs);
				return -1;
			}
		}
	}

	// External
	if (!skipExternal) {
		for (int iGender = 0; iGender < 3; iGender++) {
			string fileName = outDir + "/ExtrnlV/" + allGenders[iGender] + "_validation.bin";
			string idsFileName = outDir + "/ExtrnlV/" + allGenders[iGender] + "_id_list";
			if (createVBF(fileName, config, "", idsFileName) < 0) {
				fprintf(stderr, "Cannot create Virtual Bin File %s\n", fileName_cs);
				return -1;
			}
		}
	}

	return 0;
}

int createVBF(const string& fileName, const string& configFileName, const string& group, const string& idsFileName) {
	
	ofstream outf(fileName);

	if (!outf.is_open()) {
		fprintf(stderr, "Cannot open %s for writing\n", fileName.c_str());
		return -1;
	}

	outf << "#VBF" << endl;
	outf << "#rep\t" << configFileName << endl;
	outf << "#id_list\t" << idsFileName << endl;
	if (group != "")
		outf << "#groups\t" << group << endl;

	outf.close();
	return 0;
}

int writeIdsToFile(const string& fileName, vector<int>& ids) {

	ofstream outf(fileName);

	if (!outf.is_open()) {
		fprintf(stderr, "Cannot open %s for writing\n", fileName.c_str());
		return -1;
	}

	for (auto id : ids)
		outf << id << endl;

	outf.close();
	return 0;
}
