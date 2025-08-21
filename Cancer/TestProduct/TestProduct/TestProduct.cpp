// A Tester utilitiy for MeScorer

#include "TestProduct.h"

int main(int argc, char *argv[]) {

	if (argc != 5 && (argc !=6 || (strcmp(argv[5],"Short") && strcmp(argv[5], "UnitTesting")))) {
		fprintf(stderr, "Usage: Tester[.exe] EngineDirectory DataDirectory DataPrefix FullScorerFlag [Short|UnitTesting]\n");
		return -1;
	}

	int version[4] ;
	fprintf(stderr,"rc = %d\n",getMeScorerVersion(version)) ;
	fprintf(stderr,"Version: %d.%d.%d.%d\n",version[0],version[1],version[2],version[3]) ;

	// Parse Parameters
	string engineDir; fix_path_P(argv[1], engineDir);
	string dataDirectory; fix_path_P(argv[2], dataDirectory);
	
	string dataPrefix(argv[3]);
	string fullScorerFlag_s(argv[4]);
	bool fullScorerFlag;

	if (fullScorerFlag_s == "1" || fullScorerFlag_s == "yes" || fullScorerFlag_s == "Yes" || fullScorerFlag_s == "YES" || fullScorerFlag_s == "y" || fullScorerFlag_s == "Y")
		fullScorerFlag = true;
	else if (fullScorerFlag_s == "0" || fullScorerFlag_s == "no" || fullScorerFlag_s == "No" || fullScorerFlag_s == "NO" || fullScorerFlag_s == "n" || fullScorerFlag_s == "N")
		fullScorerFlag = false;
	else {
		fprintf(stderr, "Unknown FullScorerFlag option \'%s\' (Choose from 1,yes,Yes,YES,y,Y and 0,no,No,NO,n,N)\n", fullScorerFlag_s.c_str());
		return -1;
	}

	bool shortVersion = (argc == 6 && ! strcmp(argv[5], "Short"));
	bool unitTestingFlag = (argc == 6 && ! strcmp(argv[5], "UnitTesting"));

	// Initialize Engine
	clock_t tick1 = clock() ; 
	time_t time1 = time(NULL) ;

	int rc;
	ScorerSetUp setUpInfo;
	setUpInfo.encrypted = false;

	if ((rc = setUpInfo.setEngineDir(engineDir.c_str())) < 0) {
		fprintf(stderr, "Failed seting setup directory. rc = %d\n", rc);
		return -1;
	}

	MS_CRC_Scorer scorer;
	if ((rc = scorer.load(setUpInfo)) != 0) {
		fprintf(stderr, "Scorer SetUp failed. rc = %d\n", rc);
		return 100 + rc;
	}

	fprintf(stderr, "Engine Version: %s\n", scorer.getEngineVersion());

	clock_t tick2 = clock() ;
	time_t time2 = time(NULL) ;
	fprintf(stderr,"Loading time: %f ; CPU: %f\n",double(time2-time1),double(tick2-tick1)/CLOCKS_PER_SEC) ;
	tick1 = clock() ; 
	time1 = time(NULL) ;

	// Read data : Assumption - ids are numerically ordered (e.g. if ids are N_1,N_2 etc all N_# come together, not assuming internal order)
	string demFile = dataDirectory + "/" + dataPrefix + ".Demographics.txt";
	string dataFile = dataDirectory + "/" + dataPrefix + ".Data.txt";
	string outFile = dataDirectory + "/" + dataPrefix + ".Scores.txt";

	FILE *demFP = fopen(demFile.c_str(), "r");
	if (demFP == NULL) {
		fprintf(stderr, "Cannot open %s for reading\n", demFile.c_str());
		return -1;
	}

	// Open 2 file handlers (The first for extraction of list of unique id's in file, the second for reading all blood data)
	FILE *dataFP = fopen(dataFile.c_str(), "r");
	FILE *dataFP2 = fopen(dataFile.c_str(), "r");
	if (dataFP2 == NULL) {
		fprintf(stderr, "Cannot open %s for reading\n", dataFile.c_str());
		return -1;
	}

	FILE *outFP = fopen(outFile.c_str(), "w");
	if (outFP == NULL) {
		fprintf(stderr, "Cannot open %s for writing\n", outFile.c_str());
		return -1;
	}

	// Create vector of unique id's included in data file
	// Will be used to ignore id's in demographics file with no blood data
	vector<string> dataIds;
	string lastId = "";
	while (!feof(dataFP2)) {
		int temp1 = -1, temp2 = -1;
		double temp3 = -1.0;
		char dataId[MAX_NAME_LEN];
		int rc = fscanf(dataFP2, "%s %d %d %lf\n", dataId, &temp1, &temp2, &temp3);

		if (rc == EOF)
			break;

		if (rc != 4) {
			fprintf(stderr, "Cannot parse blood test line in %s\n", dataFile.c_str());
			return -1;
		}

		string dataId_s(dataId);
		if (lastId != dataId_s) {
			dataIds.push_back(dataId_s);
			lastId = dataId_s;
		}	
	}
	fclose(dataFP2);

	char id[MAX_NAME_LEN],dataId[MAX_NAME_LEN];
	int bYear;
	char gender;
	int currentId = -1, prevId = -1;
	ScorerBloodTest bloodTest;
	vector<ScorerResult> scores; 

	map<string, inData> allData;
	while (!feof(demFP)) {

		// Read Demographics
		int rc = fscanf(demFP, "%s %d %c\n", id, &bYear, &gender);
		if (rc == EOF)
			break;

		if (rc != 3) {
			fprintf(stderr, "Cannot parse demographics line in %s\n", demFile.c_str());
			return -1;
		}

		string id_s(id);
		currentId = atoi(id); // Ignores non numeric suffix

		// Skip id if he has no blood data
		if (!unitTestingFlag && std::find(dataIds.begin(), dataIds.end(), id_s) == dataIds.end())
			continue;

		if (allData.find(id_s) != allData.end()) {
			fprintf(stderr, "Multiple demographics lines for %s in \'%s\' n", id,demFile.c_str());
			return -1;
		}

		allData[id_s].BirthYear = bYear;
		allData[id_s].Gender = gender;

		// Is it a new numeric id ?
		if (prevId != -1 && currentId != prevId) {

			// Read Data
			// Assumes there are no id's in data that aren't in demographics file
			while (!feof(dataFP)) {
				int rc = fscanf(dataFP, "%s %d %d %lf\n", dataId, &bloodTest.Code, &bloodTest.Date, &bloodTest.Value);

				if (rc == EOF)
					break;

				if (rc != 4) {
					fprintf(stderr, "Cannot parse blood test line in %s\n", dataFile.c_str());
					return -1;
				}

				string id_s(dataId);
				allData[id_s].BloodTests.push_back(bloodTest);

				// Break if reached next id (meaning one record of the new id will already be loaded in allData)
				if (atoi(dataId) != prevId)
					break;
			}
			
			// Score and print prevId only
			vector<string> relevantIds;
			for (auto &data : allData) {
				const string printId = data.first;
				if (stoi(printId) == prevId)
					relevantIds.push_back(printId);
			}

			for (const string& printId : relevantIds) {
				if ((rc = getScores(scorer, printId, allData[printId], fullScorerFlag, scores)) < 0) {
					fprintf(stderr, "scoring failed for id %s. rc = %d\n", printId.c_str(), rc);
					return 200 + rc;
				}
				printScores(printId, scores, outFP, shortVersion);
				allData.erase(printId);
			}
		}

		prevId = currentId;
	}

	// Read Data - last id in demographics file
	while (!feof(dataFP)) {
		int rc = fscanf(dataFP, "%s %d %d %lf\n", dataId, &bloodTest.Code, &bloodTest.Date, &bloodTest.Value);

		if (rc == EOF)
			break;

		if (rc != 4) {
			fprintf(stderr, "Cannot parse blood test line in %s\n", dataFile.c_str());
			return -1;
		}

		string id_s(dataId);
		allData[id_s].BloodTests.push_back(bloodTest);

		if (atoi(dataId) != prevId)
			break;
	}

	// Score and print - last id in demographics file
	vector<string> relevantIds;
	for (auto &data : allData) {
		const string printId = data.first;
		if (stoi(printId) == prevId)
			relevantIds.push_back(printId);
	}

	for (const string& printId : relevantIds) {
		if ((rc = getScores(scorer, printId, allData[printId], fullScorerFlag, scores)) < 0) {
			fprintf(stderr, "scoring failed for id %s. rc = %d\n", printId.c_str(), rc);
			return 200 + rc;
		}

		printScores(printId, scores, outFP, shortVersion);
		allData.erase(printId);
	}

	return 0;
}


// Score
int getScores(MS_CRC_Scorer& scorer, map<string, inData>& allData, bool fullScorerFlag, map<string, vector<ScorerResult> >& scores) {

	for (auto it = allData.begin(); it != allData.end(); it++) {

		inData& idData = it->second;
		scores[it->first].clear();

		if (!fullScorerFlag) { // Score once using all data
			ScorerBloodData data;
			if (createBloodData(idData, it->first, -1, data) < 0)
				return -1;

			scores[it->first].resize(1);
			int rc = scorer.calculate(data, scores[it->first][0]);
			if (rc != 0) {
				fprintf(stderr, "Scorer failed on full-data on %s. rc = %d\n", it->first.c_str(), rc);
				return -1;
			}
			
		} else { // Score per date 
			// Get all dates
			map<int, int> dates;
			for (unsigned int i = 0; i < idData.BloodTests.size(); i++)
				dates[idData.BloodTests[i].Date] = 1;

			scores[it->first].resize(dates.size());

			int idx = 0;
			for (auto d_it = dates.begin(); d_it != dates.end(); d_it++) {
			
				ScorerBloodData data;
				if (createBloodData(idData, it->first, d_it->first, data) < 0)
					return -1;

				int rc = scorer.calculate(data, scores[it->first][idx++]);

				if (rc != 0) {
					fprintf(stderr, "Scorer failed on date %d on %s. rc = %d\n", d_it->first,it->first.c_str(), rc);
					return -1;
				}
			}
		}
	}

	return 0;
}


int getScores(MS_CRC_Scorer& scorer, const string& id, inData &idData, bool fullScorerFlag, vector<ScorerResult>& scores) {


	scores.clear();

	if (!fullScorerFlag) { // Score once using all data
		ScorerBloodData data;
		if (createBloodData(idData, id, -1, data) < 0)
			return -1;

		scores.resize(1);
		int rc = scorer.calculate(data, scores[0]);
		if (rc != 0) {
			fprintf(stderr, "Scorer failed on full-data on %s. rc = %d\n", id.c_str(), rc);
			return -1;
		}
	}
	else { // Score per date 

		// Get all dates	
		map<int, int> dates;
		for (unsigned int i = 0; i < idData.BloodTests.size(); i++)
			dates[idData.BloodTests[i].Date] = 1;

		scores.resize(dates.size());

		int idx = 0;
		for (auto d_it = dates.begin(); d_it != dates.end(); d_it++) {

			ScorerBloodData data;
			if (createBloodData(idData, id, d_it->first, data) < 0)
				return -1;

			int rc = scorer.calculate(data, scores[idx++]);

			if (rc != 0) {
				fprintf(stderr, "Scorer failed on date %d on %s. rc = %d\n", d_it->first, id.c_str(), rc);
				return -1;
			}
		}
	}

	return 0;
}

// Print
int printScores(map<string, vector<ScorerResult> >& scores, string& directory, string& prefix, bool shortVersion) {

	string fileName = directory + "/" + prefix + ".Scores.txt";
	FILE *fp = fopen(fileName.c_str(), "w");
	if (fp == NULL) {
		fprintf(stderr, "Cannot open %s for wrinting\n", fileName.c_str());
		return -1 ;
	}

	for (auto it = scores.begin(); it != scores.end(); it++) {
		vector<ScorerResult>& idScores = it->second;
		for (unsigned int i = 0; i < idScores.size(); i++) {
			fprintf(fp, "%s\t", it->first.c_str());
			if (idScores[i].IsValid)
				fprintf(fp, "%d\t%.2f\t", idScores[i].Date,idScores[i].Score);
			else
				fprintf(fp, "\t\t");

			for (unsigned int j = 0; j < idScores[i].Messages.size(); j++) {
				if (j > 0)
					fprintf(fp, " ");
				fprintf(fp, "%d", idScores[i].Messages[j].Code);

				if (! shortVersion) {
					for (unsigned int k = 0; k < idScores[i].Messages[j].Parameters.size(); k++)
						fprintf(fp, ",%lf", idScores[i].Messages[j].Parameters[k]);
				}
			}
			fprintf(fp, "\n");
		}
	}

	return 0;
}

void printScores(const string& id, vector<ScorerResult>& idScores, FILE *fp, bool shortVersion) {

	for (unsigned int i = 0; i < idScores.size(); i++) {
		fprintf(fp, "%s\t", id.c_str());
		if (idScores[i].IsValid)
			fprintf(fp, "%d\t%.2f\t", idScores[i].Date, idScores[i].Score);
		else
			fprintf(fp, "\t\t");

		for (unsigned int j = 0; j < idScores[i].Messages.size(); j++) {
			if (j > 0)
				fprintf(fp, " ");
			fprintf(fp, "%d", idScores[i].Messages[j].Code);

			if (!shortVersion) {
				for (unsigned int k = 0; k < idScores[i].Messages[j].Parameters.size(); k++)
					fprintf(fp, ",%lf", idScores[i].Messages[j].Parameters[k]);
			}
		}
		fprintf(fp, "\n");
	}

	return;
}

