#pragma once
#include "CommonLib/CommonLib.h"
#include <time.h>


#define _CRT_SECURE_NO_WARNINGS

// Score
int getScores(MS_CRC_Scorer& scorer, map<string, inData>& allData, bool fullScorerFlag, map<string, vector<ScorerResult> >& scores);
int getScores(MS_CRC_Scorer& scorer, const string& id, inData &idData, bool fullScorerFlag, vector<ScorerResult>& scores);

// Print
int printScores(map<string, vector<ScorerResult> >& scores, string& directory, string& prefix, bool ShortVersion) ;
void printScores(const string& id, vector<ScorerResult>& idScores, FILE *fp, bool shortVersion);