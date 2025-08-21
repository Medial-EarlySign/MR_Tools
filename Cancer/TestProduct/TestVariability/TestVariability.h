#pragma once
#include "CommonLib/CommonLib.h"

#define _CRT_SECURE_NO_WARNINGS

// Read Variation Sizes
int readVariations(const string& fileName, map<int, float>& variations, float factor);

// check Variability
int getVariability(MS_CRC_Scorer& scorer, map<string, inData>& allData, map<int, float>& variations);

// Score + check
int getScore(ScorerBloodData& data, MS_CRC_Scorer& scorer, int last_date, float& outScore);