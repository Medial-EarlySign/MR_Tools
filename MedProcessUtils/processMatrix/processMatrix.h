// process a MedFeatures matrix

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void addExisting(MedFeatures& features);
void sample(MedFeatures& features, string& params);
void num_sample(MedFeatures& features, string& params);
void split(MedFeatures& features, string& params, MedFeatures& trainFeatures, MedFeatures& testFeatures);
void normalize(MedFeatures& features, string& inParamsFile, string& outParamsFile);
void denormalize(MedFeatures& features, string& paramsFile);
void combine(MedFeatures& features, MedFeatures& features2, float priceRatio);

// Classes
class normParams : public SerializableObject {
public:
	map<string, float> avg, std;

	// Serialization
	ADD_CLASS_NAME(normParams)
	ADD_SERIALIZATION_FUNCS(avg, std)
};

