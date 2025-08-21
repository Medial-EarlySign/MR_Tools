#pragma once
#include "MeScorer/MeScorer.h"

#define _CRT_SECURE_NO_WARNINGS

#include "stdlib.h"
#include "stdio.h"
#include "math.h"
#include <map>
#include <algorithm>
#include <iostream>
#include <vector>
#include <string>
#include <random>

using namespace std;

class inData {
public:
	int BirthYear; // year of birth YYYY
	char Gender; // Gender : M/F
	vector<ScorerBloodTest> BloodTests; // All Blood Tests
};

// Functions
// Read Data
int readData(string& directory, string& prefix, map<string, inData>& data);
int readDemographics(const string& fileName, map<string, inData>& data);
int readBloodData(const string& fileName, map<string, inData>& data);

// Score
int createBloodData(inData& idData, const string& id, const int date, ScorerBloodData& outData);

int fix_path_P(const string& in, string& out);