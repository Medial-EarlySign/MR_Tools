// Learn a model starting with a matrix

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void write_predictor_to_file(MedPredictor *pred, string& outFile);