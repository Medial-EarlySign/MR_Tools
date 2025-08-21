#pragma once 
#ifndef __PANEL_STATS__
#define __PANEL_STATS__

#include "read_data.h"

// constants


// functions

void cbc_for_demogrpahy( data_set_t& ds );
void cbc_amount_by_age( data_set_t& ds );
void cbc_amount_by_year( data_set_t& ds );
void cbc_frequency( data_set_t& ds );
void last_panel_before_date_control( data_set_t& ds );
void last_panel_before_crc_onset( data_set_t& ds );

void panel_size_distribution( data_set_t& ds );
void panel_type_distribution( data_set_t& ds );
void panel_number_distribution_for_healthy( data_set_t& ds );
void cbc_code_in_panel_distribution( data_set_t& ds );
void cbc_code_in_panel_redflag( data_set_t& ds );
void check_panel_subsets( data_set_t& ds );

void time_diff_for_adjacent_panels( data_set_t& ds );
void cbc_for_control_per_person_per_age( data_set_t& ds );


#endif // __PANEL_STATS__