#pragma once 
#ifndef __STATS__
#define __STATS__

#include "read_data.h"
#include "data_types.h"

// constants

// functions

void crc_total_count( data_set_t& ds );
void crc_count_by_year( data_set_t& ds );
void crc_count_by_age( data_set_t& ds );

void crc_age_distribution_bin_to_stdout( data_set_t& ds );
void crc_age_distribution_bin_to_xls( data_set_t& ds );
void crc_age_distribution_bin_compare( data_set_t& ds, int v_type );

void crc_risk_by_age( data_set_t& ds );
void crc_risk_by_age_bin( data_set_t& ds );
void crc_risk_and_relative_risk_by_age( data_set_t& ds );

void crc_risk_by_year( data_set_t& ds, int min_age, int max_age );
//void crc_risk_by_year_aged_50_75( data_set_t& ds );

void other_cancer_information( data_set_t& ds );
void crc_onset_and_health_provider_change( data_set_t& ds );
void stage_distribution( data_set_t& ds );

void crc_moments_and_quantiles( data_set_t& ds );

//void censor_information( data_set_t& ds );

#endif

