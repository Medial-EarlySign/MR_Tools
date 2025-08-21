#include "CommonLib.h"
#include <iostream>
#include <sstream>

// Functions
// Read Data
int readData(string& directory, string& prefix, map<string, inData>& data) {

	// Read
	if (readDemographics(directory + "/" + prefix + ".Demographics.txt", data) < 0)
		return -1;

	if (readBloodData(directory + "/" + prefix + ".Data.txt", data) < 0)
		return -1;


	return 0;
}

int readDemographics(const string& fileName, map<string, inData>& data) {

	FILE *fp = fopen(fileName.c_str(), "r");
	if (fp == NULL) {
		fprintf(stderr, "Cannot open %s for reading\n", fileName.c_str());
		return -1;
	}

	char id[MAX_NAME_LEN];
	int bYear;
	char gender;

	while (!feof(fp)) {
		int rc = fscanf(fp, "%s %d %c\n", id, &bYear, &gender);
		if (rc == EOF)
			break;

		if (rc != 3) {
			fprintf(stderr, "Cannot parse demographics line in %s\n", fileName.c_str());
			return -1;
		}

		string id_s(id);
		if (data.find(id_s) != data.end()) {
			fprintf(stderr, "Multiple demographics lines for %s in %s\n", id, fileName.c_str());
			return -1;
		}

		data[id_s].BirthYear = bYear;
		data[id_s].Gender = gender;

	}

	return 0;
}

int readBloodData(const string& fileName, map<string, inData>& data) {

	FILE *fp = fopen(fileName.c_str(), "r");
	if (fp == NULL) {
		fprintf(stderr, "Cannot open %s for reading\n", fileName.c_str());
		return -1;
	}

	char id[MAX_NAME_LEN];

	while (!feof(fp)) {

		ScorerBloodTest bloodTest;
		int rc = fscanf(fp, "%s %d %d %lf\n", id, &bloodTest.Code, &bloodTest.Date, &bloodTest.Value);
		if (rc == EOF)
			break;

		if (rc != 4) {
			fprintf(stderr, "Cannot parse blood test line in %s\n", fileName.c_str());
			return -1;
		}

		string id_s(id);
		data[id_s].BloodTests.push_back(bloodTest);
	}

	return 0;
}


// create a blooData object
int createBloodData(inData& idData, const string& id, const int date, ScorerBloodData& outData) {

	try {
		// Count
		size_t size = 0 ;
		if (date == -1)
			size = idData.BloodTests.size() ;
		else {
			for (unsigned int i = 0; i < idData.BloodTests.size(); i++) {
				if (idData.BloodTests[i].Date <= date)
					size++;
			}
		}

		outData.BloodTests.resize(size) ;

		// Allocate
		if ((outData.Id = (char *) malloc(id.length() + 1)) == NULL) {
			fprintf(stderr, "Allocation failed int createBloodData\n");
			return -1; 
		}

		// Fill
		outData.BirthYear = idData.BirthYear;
		outData.Gender = idData.Gender;
		strcpy(outData.Id, id.c_str());

		int cnt = 0;
		for (unsigned int i = 0; i < idData.BloodTests.size(); i++) {
			if (date == -1 || idData.BloodTests[i].Date <= date)
				outData.BloodTests[cnt++] = idData.BloodTests[i];
		}

		return 0;
	} catch(...) {
		fprintf(stderr,"Problem handled inside\n") ;
		return -1 ;
	}

}


int fix_path_P(const string& in, string& out) {
	// fprintf(stderr, "Converting path \'%s\'\n", in.c_str());
	// fflush(stderr);
	map<string, string> folders;
	folders["W"] = "Work";
	folders["U"] = "UsersData";
	folders["X"] = "Temp";
	folders["P"] = "Products";
	folders["T"] = "Data";
	// fprintf(stderr, "Initialized network drive table\n");

#ifndef _WIN32
	// on Linux, handle first the Windows native format: \\\\nas1\\Work\..  
	if (in.length() >= 2 && in.substr(0, 2) == "\\\\") {
		// just switching '\' to '/'; works, but adjacent slashes should be unified
		out = in;
		char revSlash = '\\';
		char fwdSlash = '/';
		std::replace(out.begin(), out.end(), revSlash, fwdSlash);
		fprintf(stderr, "Converted path \'%s\' to \'%s\'\n", in.c_str(), out.c_str());
		fflush(stderr);

		return 0;
	}
#endif

	// Work only on "X:/...." or  "/cygdrive/X/...." input strings
	if ((in.length() < 3 || in.substr(1, 2) != ":/") &&
		(in.length() < 12 || in.substr(0, 10) != "/cygdrive/" || in.substr(11, 1) != "/")) {
		out = in;
		return 0;
	}

	char driveLetter = (in.substr(1, 2) == ":/") ? in.substr(0, 1)[0] : (char)toupper(in.substr(10, 1)[0]);
	string drive = string(1, driveLetter);

	if (drive == "C" || drive == "D" || drive == "H") {
		out = in;
		return 0;
	}

	int pathPos = (in.substr(1, 2) == ":/") ? 3 : 12;

	if (folders.find(drive) == folders.end()) {
		fprintf(stderr, "Unknown Folder Map %s\n", drive.c_str());
		return -1;
	}

#ifdef _WIN32
	out = "\\\\nas1\\" + folders[drive];
#else
	out = "/nas1/" + folders[drive];
#endif

	istringstream in_stream(in.substr(pathPos, in.length() - pathPos));
	string token;

	while (getline(in_stream, token, '/'))
#ifdef _WIN32
		out += "\\" + token;
#else
		out += "/" + token;
#endif
	fprintf(stderr, "Converted path \'%s\' to \'%s\'\n", in.c_str(), out.c_str());
	fflush(stderr);

	return 0;

}