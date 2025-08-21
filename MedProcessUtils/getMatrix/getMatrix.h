// Generate a matrix given samples and a model (either as JSON or as bin)

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void strip_matrix(MedFeatures& features);