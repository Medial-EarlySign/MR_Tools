// Print Repository data

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void print_without_processing(MedPidRepository& rep, vector<int>& ids, vector<string>& signals);
void get_model(po::variables_map& vm, MedModel& model, int& learn);
void print_with_processing(MedPidRepository& rep, MedModel& model, vector<int>& ids, vector<string>& signals);
void get_rep(po::variables_map& vm, vector<int>& ids, vector<string>& signals, MedModel *model, MedPidRepository& rep);