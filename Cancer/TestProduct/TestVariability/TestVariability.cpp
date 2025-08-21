// A Tester utilitiy for MeScorer

#include "TestVariability.h"

int main(int argc, char *argv[]) {

	if (argc != 5 && argc != 6) {
		fprintf(stderr, "Usage: Tester[.exe] EngineDirectory DataDirectory DataPrefix variationsFile [factor = 1]\n");
		return -1;
	}

	// Parse Parameters
	string engineDir(argv[1]);
	string dataDirectory(argv[2]);
	string dataPrefix(argv[3]);
	string varFile(argv[4]);

	float factor = (float) ((argc==6) ? atof(argv[5]) : 1.0) ;

	// Initialize Engine
	int rc;
	ScorerSetUp setUpInfo;

	if ((rc = setUpInfo.setEngineDir(engineDir.c_str())) < 0) {
		fprintf(stderr, "Failed seting setup directory. rc = %d\n", rc);
		return -1;
	}

	MS_CRC_Scorer scorer;
	if ((rc = scorer.load(setUpInfo)) != 0) {
		fprintf(stderr, "Scorer SetUp failed. rc = %d\n", rc);
		return 100 + rc;
	}

	// Read Data
	map<string, inData> allData;
	if ((rc = readData(dataDirectory, dataPrefix, allData)) < 0) {
		fprintf(stderr, "reading Data from %s failed. rc = %d\n", dataDirectory.c_str(), rc);
		return -1;
	}

	map<int, float> variations;
	if ((rc = readVariations(varFile, variations,factor)) < 0) {
		fprintf(stderr, "reading Data from %s failed. rc = %d\n", varFile.c_str(), rc);
		return -1;
	}

	// Score
	if ((rc = getVariability(scorer, allData,variations)) < 0) {
		fprintf(stderr, "getVariability failed. rc = %d\n", rc);
		return 200 + rc;
	}

	return 0;
}

// check Variability
int getVariability(MS_CRC_Scorer& scorer, map<string, inData>& allData, map<int, float>& variations) {

	// Variation Codes
	vector<int> varCodes;
	for (auto it = variations.begin(); it != variations.end(); it++)
		varCodes.push_back(it->first);

	// Check
	for (auto it = allData.begin(); it != allData.end(); it++) {

		inData& idData = it->second;
		double max_score = -1, min_score = -1;
		string max_desc, min_desc;

		// Get Last date
		int last_date = -1;
		for (unsigned int i = 0; i < idData.BloodTests.size(); i++) {
			if (idData.BloodTests[i].Date > last_date)
				last_date = idData.BloodTests[i].Date;
		}

		// Gather All History
		ScorerBloodData data;
		if (createBloodData(idData, it->first, last_date - 1, data) < 0)
			return -1;
		size_t origBloodTestCount = data.BloodTests.size();

		// Last One ...
		vector<ScorerBloodTest> LastBloodTest;
		map<int, int> LastTestCodes;
		for (unsigned int i = 0; i < idData.BloodTests.size(); i++) {
			if (idData.BloodTests[i].Date == last_date) {
				LastBloodTest.push_back(idData.BloodTests[i]);
				LastTestCodes[idData.BloodTests[i].Code] = 1;
			}
		}

		// Check all tests are given
		for (unsigned int i = 0; i < varCodes.size(); i++) {
			if (LastTestCodes.find(varCodes[i]) == LastTestCodes.end()) {
				fprintf(stderr, "Code %d not available for last date. Ignoring ID %s\n",varCodes[i],it->first.c_str());
				continue;
			}
		}

		// Allocation for last test
		data.BloodTests.resize(origBloodTestCount + LastBloodTest.size()) ;

		// True Score
		size_t bloodTestCount = origBloodTestCount;
		for (unsigned j = 0; j < LastBloodTest.size(); j++) {
			int code = LastBloodTest[j].Code;
			if (variations.find(code) != variations.end()) 
				data.BloodTests[bloodTestCount++] = LastBloodTest[j];
		}

		float trueScore;
		if (getScore(data, scorer, last_date, trueScore) < 0) {
			fprintf(stderr, "True Scoring Failed\n");
			return -1;
		}

		// Directions
		map <int, int > directions;
		for (unsigned int i = 0; i < varCodes.size(); i++) {

			directions[varCodes[i]] = 0;
			for (int dir = -1; dir <= 1; dir += 2) {
				// Change
				bloodTestCount = origBloodTestCount;
				for (unsigned j = 0; j < LastBloodTest.size(); j++) {
					int code = LastBloodTest[j].Code;
					if (variations.find(code) != variations.end()) {
						data.BloodTests[bloodTestCount] = LastBloodTest[j];
						if (code == varCodes[i])
							data.BloodTests[bloodTestCount].Value += dir * variations[varCodes[i]];
						bloodTestCount++;
					}
				}

				float iscore;
				if (getScore(data, scorer, last_date, iscore) < 0) {
					fprintf(stderr, "Shift Scoring Failed for %d\n",i);
					return -1;
				}

				int iDirection = 0;
				if (iscore > trueScore)
					iDirection = dir;
				else
					iDirection = -dir;

				if (iDirection != 0) {
					directions[varCodes[i]] = iDirection;
					break;
				}
			}
		}
				
		// Variations
		int nVariations = 2 << varCodes.size();

		for (int i = 1; i < nVariations; i++) {

			// Decide on changes
			int idx = 0;
			map<int, int> iVar;
			string description;

			for (unsigned int idx = 0; idx < varCodes.size(); idx++) {
				if (i & (1 << idx) && directions[varCodes[idx]] != 0) {
					description += '1';
					iVar[varCodes[idx]] = 1;
				}
				else {
					description += '0';
					iVar[varCodes[idx]] = 0;
				}
			}


			// Change - Increase
			bloodTestCount = origBloodTestCount;
			for (unsigned j = 0; j < LastBloodTest.size(); j++) {
				int code = LastBloodTest[j].Code;
				if (iVar.find(code) != iVar.end()) {
					data.BloodTests[bloodTestCount] = LastBloodTest[j];
					if (iVar[code] == 1)
						data.BloodTests[bloodTestCount].Value += directions[code] * variations[code];
					bloodTestCount++;
				}
			}

			// Score
			float iscore;
			if (getScore(data, scorer, last_date, iscore) < 0) {
				fprintf(stderr, "Up Scoring Failed for %d\n", i);
				return -1;
			}

			if (max_score == -1 || iscore > max_score) {
				max_desc = description;
				max_score = iscore;
			}


			// Change - Decrease
			bloodTestCount = origBloodTestCount;
			for (unsigned j = 0; j < LastBloodTest.size(); j++) {
				int code = LastBloodTest[j].Code;
				if (iVar.find(code) != iVar.end()) {
					data.BloodTests[bloodTestCount] = LastBloodTest[j];
					if (iVar[code] == 1)
						data.BloodTests[bloodTestCount].Value -= directions[code] * variations[code];
					bloodTestCount++;
				}
			}

			// Score
			if (getScore(data, scorer, last_date, iscore) < 0) {
				fprintf(stderr, "Down Scoring Failed for %d\n", i);
				return -1;
			}

			if (min_score == -1 || iscore < min_score) {
				min_desc = description;
				min_score = iscore;
			}
		}

		printf("%s\t%d\t%f\t%f [%s]\t%f [%s]\n", it->first.c_str(), last_date, trueScore,min_score,min_desc.c_str(),max_score,max_desc.c_str());
	}

	return 0;
}
		
// Read Variations
int readVariations(const string& fileName, map<int, float>& variations,float factor) {

	FILE *fp = fopen(fileName.c_str(), "r");
	if (fp == NULL) {
		fprintf(stderr, "Cannot open %s for reading\n", fileName.c_str());
		return -1;
	}

	int code;
	float varSize;

	while (!feof(fp)) {
		int rc = fscanf(fp, "%d %f\n", &code, &varSize);
		if (rc == EOF)
			break;

		if (rc != 2) {
			fprintf(stderr, "Cannot parse variations line in %s\n", fileName.c_str());
			return -1;
		}

		if (code < 1 || code > 20) {
			fprintf(stderr, "Illegal variations line in %s\n", fileName.c_str());
			return -1;
		}
		
		variations[code] = factor * varSize;

	}

	return 0;
}

int getScore(ScorerBloodData& data, MS_CRC_Scorer& scorer, int last_date, float& outScore) {

	ScorerResult score;
	int rc = scorer.calculate(data, score);

	if (rc != 0) {
		fprintf(stderr, "Scorer failed on date %d on %s. rc = %d\n", last_date, data.Id, rc);
		return -1;
	}

	if (!score.IsValid || score.Date != last_date) {
		fprintf(stderr, "Scoring failed for %s ! IsValid = %d ; Scoring Date = %d Last Date = %d\n", data.Id, score.IsValid, score.Date, last_date);

		for (unsigned int i = 0; i < score.Messages.size(); i++) {
			fprintf(stderr, "Message : %d", score.Messages[i].Code);
			for (unsigned int j = 0; j < score.Messages[i].Parameters.size(); j++)
				fprintf(stderr, "\t%f", score.Messages[i].Parameters[j]);
			fprintf(stderr, "\n");
		}

		return -1;
	}

	outScore = (float) score.Score;
	return 0;
}