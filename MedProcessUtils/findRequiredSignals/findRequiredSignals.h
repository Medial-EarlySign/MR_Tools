#pragma once
#include "CommonLib/CommonLib/commonHeader.h"
#include "ProgramArgs.h"
#include "MedStat/MedStat/MedBootstrap.h"
#include "MedProcessTools/MedProcessTools/FeatureProcess.h"
#include "MedStat/MedStat/bootstrap.h"

void read_run_params(int argc, char **argv, po::variables_map& vm);
int nchoosek(int n, int k);
void combinations_recursive(vector<string> &elems, unsigned long req_len, vector<unsigned long> &pos, unsigned long depth, unsigned long margin, vector<unordered_set<string>> &out);
void combinations(vector<string>&elems, unsigned long req_len, vector<unordered_set<string>> &out);
void getSortedSignals(vector<pair<float, unordered_set<string>>> &performanceSignals, vector<string> &prevSignalsSorted, vector<string> &signalsSorted);
int find_num_signals(int num_required_iterations, int curr_num_signals);
bool sortbyfirstinv(const pair<float, unordered_set<string>> &a, const pair<float, unordered_set<string>> &b);
void writeResultsToFile(ofstream &out_file, vector<string> &sig_names, vector<pair<float, unordered_set<string>>> &performanceSignals, int evaluationsToPrint, float requiredAbsPerf, unordered_map<string, vector<float>> &ci_dict, unordered_map<string, int> &cnt_dict, int n_pids);
string set2string(unordered_set<string> stringSet);
void getSigsFromCombination(unordered_set<string> &comb, unordered_set<string> &required, vector<string> &sig_names, unordered_set<string> &sigsToDelete, unordered_set<string> &sigsToTake);
bool calcStoppingCriteria(float requiredAbsPerf, size_t maximalNumSignals, int numIterationsToContinue, float currBestPerform, int numSignals);
void filterFeatureMatrix(MedFeatures &matrix, string &cohort_params, MedBootstrap &bootstrapper, vector<float> &labels, vector<int> &pids, map<string, vector<float>> &additional_info);
bool combinationsIsSupersetOfAcceptableSet(vector<unordered_set<string>> acceptableCombinations, unordered_set<string> &comb, unordered_set<string> &acceptableCombOut);
int countEligible(vector <int> &pids, unordered_set<string> &sigsToTake, MedPidRepository &rep);
