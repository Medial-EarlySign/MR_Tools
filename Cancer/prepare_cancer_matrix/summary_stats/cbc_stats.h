#pragma once 
#ifndef __CBC_STATS__
#define __CBC_STATS__

#include "read_data.h"
#include "data_types.h"

// constants

// functions

cbc_values_by_age_bin_t control_cbc_values_by_age_bin( data_set_t& ds );

void control_cbc_values_by_age_bin_to_stdout( data_set_t& ds ); 
void control_cbc_values_by_age_bin_to_xls( data_set_t& ds ); 
void control_cbc_values_by_age_bin_compare( data_set_t& ds, reference_data_set_t rds);

void cbc_values_for_controls_in_age_window_by_year( data_set_t& ds ); 
void cbc_values_for_crc_by_age( data_set_t& ds );
void crc_cbc_values_within_a_window_distribution_bin( data_set_t& ds );
void control_cbc_values_distribtion_bin( data_set_t& ds );
void crc_cbc_values_distribtion_bin( data_set_t& ds );

void control_cbc_values_quantile_to_stdout( data_set_t& ds, bool calculated_outliers ); 
void control_cbc_values_quantile_compare( data_set_t& ds );

void crc_cbc_values_quantile( data_set_t& ds, bool calculated_outliers );  

void control_cbc_values_by_age_bin_anova( data_set_t& ds );

#endif // __CBC_STATS__