#pragma once 
#ifndef __DEMOGRAPHY_STATS__
#define __DEMOGRAPHY_STATS__

#include "read_data.h"
#include "data_types.h"

// functions

void general_demography_inforamtion( data_set_t& ds );
void population_by_year( data_set_t& ds, int min_age, int max_age );
void control_age_histogram_by_year( data_set_t& ds );

void control_age_distribution_bin_to_stdout( data_set_t& ds );
void control_age_distribution_bin_to_xls( data_set_t& ds );
void control_age_distribution_bin_compare( data_set_t& ds, reference_data_set_t& rds );

age_bin_t control_age_distribution_bin( data_set_t& ds );

#endif

