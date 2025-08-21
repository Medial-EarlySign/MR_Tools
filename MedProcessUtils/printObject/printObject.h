// Read an object from a binary file and print

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void print_predictor(MedPredictor *predictor, FILE *fp, int level);
void print_feature_importance(MedPredictor *predictor, FILE *fp);
