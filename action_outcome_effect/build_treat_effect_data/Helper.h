#ifndef __HELPER_H__
#define __HELPER_H__
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include <string>

using namespace std;

void load_matrix_from_json(MedSamples &samples,
	const string &RepositoryPath, const string &jsonPath, MedFeatures &dataMat);

void match_by_year(MedFeatures &data_records, float price_ratio, int year_bin_size, bool print_verbose,
	vector<int> *filter_inds_res = NULL);

MedRegistry *create_registry_full_with_rep(const string &registry_type, const string &init_str,
	const string &repository_path, MedModel &model_with_rep_processor, medial::repository::fix_method method,
	MedPidRepository &rep);

#endif