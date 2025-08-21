#include "menu.h"
#include "demography_stats.h"
#include "registry_stats.h"
#include "panel_stats.h"
#include "cbc_stats.h"
#include "data_types.h"

int print_main_menu( void ) {
	fprintf( stderr, "\nMain Menu\n" );
	fprintf( stderr, "=========\n" );
	fprintf( stderr, "1. Demography stats\n" );
	fprintf( stderr, "2. Registry stats\n" );
	fprintf( stderr, "3. Panel stats\n" );
	fprintf( stderr, "4. CBC stats\n" );
	fprintf( stderr, "5. All stats\n" );
	fprintf( stderr, "6. Red Flags + Comparison\n" );
	fprintf( stderr, "7. Write XLS\n" );
	fprintf( stderr, "8. Exit\n" );
	fprintf( stderr, "Enter selection: " );
	int key = 0;
	scanf("%d", &key);
	return key;
}

bool run_main_menu( int selection, data_set_t& ds, reference_data_set_t& rds )
{
	int key = 0;
	bool retval = true;

	switch (selection) {
	case 1:
		key = print_demography_menu();
		run_demography_menu( key, ds );
		break;
	case 2:
		key = print_registry_menu();
		run_registry_menu( key, ds );
		break;
	case 3:
		key = print_panel_menu();
		run_panel_menu( key, ds );
		break;
	case 4:
		key = print_cbc_menu();
		run_cbc_menu( key, ds );
		break;
	case 5:
		run_all( ds, rds );
		break;
	case 6:
		compare( ds, rds );
		break;
	case 7:
		write_xls( ds, rds );
		break;
	case 8:
		retval = false;
		break;
	default:
		print_main_menu();
		break;
	}

	return retval;
}

int print_demography_menu( void ) {
	fprintf( stderr, "\nDemograhy Menu\n" );
	fprintf( stderr, "=============\n" );
	fprintf( stderr, "1. General population information\n" );
	fprintf( stderr, "2. Age distribtion\n" );
	fprintf( stderr, "3. Population by year\n" );
	fprintf( stderr, "4. Population by year (50-75)\n" );
	fprintf( stderr, "5. Age distribution for 2010 by bins\n" );
	fprintf( stderr, "Enter selection: " );
	int key = 0;
	scanf("%d", &key);
	return key;
}

void run_demography_menu( int selection, data_set_t& ds )
{
	switch (selection) {
	case 1:
		general_demography_inforamtion( ds );
		break;
	case 2:
		control_age_histogram_by_year( ds );
		break;
	case 3:
		population_by_year( ds, 0, 120 );		
		break;
	case 4:
		population_by_year( ds, 50, 75 );
		break;
	case 5:
		control_age_distribution_bin_to_stdout( ds );
		control_age_distribution_bin_to_xls( ds );
		break;
	case 6:
		break;
	case 7:
		break;
	case 8:
		break;
	case 9:
		break;
	default:
		fprintf( stderr, "Invalid selection!\n" );
		print_main_menu();
		break;
	}
}

int print_registry_menu( void ) {
	fprintf( stderr, "\nRegistry Menu\n" );
	fprintf( stderr, "=============\n" );
	fprintf( stderr, "1. CRC totals count\n" );
	fprintf( stderr, "2. CRC count by year\n" );
	fprintf( stderr, "3. CRC count by age\n" );
	fprintf( stderr, "4. CRC age distribution bin\n" );
	fprintf( stderr, "5. CRC calculate risk by age & year\n" );
	fprintf( stderr, "6. CRC calculate risk by age bin\n" );
	fprintf( stderr, "7. CRC relative risk by age\n" );
	fprintf( stderr, "8. CRC risk by year\n" );
	fprintf( stderr, "9. CRC risk by year(50-75)\n" );
	fprintf( stderr, "10. Other cancer types\n" );
	fprintf( stderr, "11. Health provider change around onset\n" );
	fprintf( stderr, "12. Stage distribution\n" );
	fprintf( stderr, "13. CRC moments and quantiles\n" );
	fprintf( stderr, "Enter selection: " );
	int key = 0;
	scanf( "%d", &key );
	return key;
}

void run_registry_menu( int selection, data_set_t& ds )
{
	switch (selection) {
	case 1:
		crc_total_count( ds );
		break;
	case 2:
		crc_count_by_year( ds );
		break;
	case 3:
		crc_count_by_age( ds );
		break;
	case 4:
		crc_age_distribution_bin_to_stdout( ds );
		crc_age_distribution_bin_to_xls( ds );
	case 5:
		crc_risk_by_age( ds );
		break;
	case 6:
		crc_risk_by_age_bin( ds );
		break;
	case 7:
		crc_risk_and_relative_risk_by_age( ds );
		break;
	case 8:
		crc_risk_by_year( ds, 0, 120 );
		break;
	case 9:
		crc_risk_by_year( ds, 50, 75 );
		break;
	case 10:
		other_cancer_information( ds );
		break;
	case 11:
		crc_onset_and_health_provider_change( ds );
		break;
	case 12:
		stage_distribution( ds );
		break;
	case 13:
		crc_moments_and_quantiles( ds );
		break;
	default:
		fprintf( stderr, "Invalid selection!\n" );
		print_main_menu();
		break;
	}
}

int print_panel_menu( void ) {
	fprintf( stderr, "\nCBC Menu\n" );
	fprintf( stderr, "========\n" );
	fprintf( stderr, "1. CBC amount for population\n" );
	fprintf( stderr, "2. CBC amount by age\n" );
	fprintf( stderr, "3. CBC amount by year\n" );
	fprintf( stderr, "4. Last panel before date for control\n" );
	fprintf( stderr, "5. Last panel before date for crc\n" );
	fprintf( stderr, "6. Panel Size distribution\n" );
	fprintf( stderr, "7. Panel Type distribution\n" );
	fprintf( stderr, "8. CBC code appearance\n" );
	fprintf( stderr, "9. Time difference between adjacent panels\n" ); 
	fprintf( stderr, "10. Panel # distribution for healthy\n" ); 
	fprintf( stderr, "11. CBC frequency\n" ); 
	fprintf( stderr, "12. Minimal Panel count\n" ); 
	fprintf( stderr, "13. CBC per person year\n" ); 
	fprintf( stderr, "Enter selection: " );
	int key = 0;
	scanf("%d", &key);
	return key;
}

void run_panel_menu( int selection, data_set_t& ds )
{
	switch (selection) {
	case 1:
		cbc_for_demogrpahy( ds );
		break;
	case 2:
		cbc_amount_by_age( ds );
		break;
	case 3:
		cbc_amount_by_year( ds );
		break;
	case 4:
		last_panel_before_date_control( ds );
		break;
	case 5:
		last_panel_before_crc_onset( ds );
		break;
	case 6:
		panel_size_distribution( ds );
		break;
	case 7:
		panel_type_distribution( ds );
		break;
	case 8:
		cbc_code_in_panel_distribution( ds );
		break;
	case 9:
		time_diff_for_adjacent_panels( ds );
		break;
	case 10:
		panel_number_distribution_for_healthy( ds );
		break;
	case 11:
		cbc_frequency( ds );
		break;
	case 12:
		check_panel_subsets( ds );
		break;
	case 13:
		cbc_for_control_per_person_per_age( ds );
		break;
	default:
		fprintf( stderr, "Invalid selection!\n" );
		print_main_menu();
		break;
	}
}

int print_cbc_menu( void ) {
	fprintf( stderr, "\nCBC Menu\n" );
	fprintf( stderr, "========\n" );
	fprintf( stderr, "1. CBC values for control by age\n" );
	fprintf( stderr, "2. CBC values for controls in age window by year\n" ); 
	fprintf( stderr, "3. CBC values for CRC by age\n" );
	fprintf( stderr, "4. CBC values distribution for controls\n" );
	fprintf( stderr, "5. CBC values distribution for CRC\n" );
	fprintf( stderr, "6. CBC values distribution for CRC within window\n" );
	fprintf( stderr, "7. CBC values quantiles for controls (outliers = 7*sdv)\n" );
	fprintf( stderr, "8. CBC values quantiles for controls (outliers = input file)\n" );
	fprintf( stderr, "9. CBC values quantiles for CRC (outliers = 7*sdv)\n" );
	fprintf( stderr, "10. CBC values quantiles for CRC (outliers = input file)\n" );
	fprintf( stderr, "11. CBC values by age bin and year - Anova\n" );
	fprintf( stderr, "Enter selection: " );
	int key = 0;
	scanf("%d", &key);
	return key;
}

void run_cbc_menu( int selection, data_set_t& ds )
{
	switch (selection) {
	case 1:
		control_cbc_values_by_age_bin_to_stdout( ds );
		control_cbc_values_by_age_bin_to_xls( ds );
		break;
	case 2:
		cbc_values_for_controls_in_age_window_by_year( ds ); 
		break;
	case 3:
		cbc_values_for_crc_by_age( ds );
		break;
	case 4:
		control_cbc_values_distribtion_bin( ds );
		break;
	case 5:
		crc_cbc_values_distribtion_bin( ds );
		break;
	case 6:
		crc_cbc_values_within_a_window_distribution_bin( ds );
		break;
	case 7:
		control_cbc_values_quantile_to_stdout( ds, true );
		break;
	case 8:
		control_cbc_values_quantile_to_stdout( ds, false );
		break;
	case 9:
		crc_cbc_values_quantile( ds, true );
		break;
	case 10:
		crc_cbc_values_quantile( ds, false );
		break;
	case 11:
		control_cbc_values_by_age_bin_anova( ds );
		break;
	default:
		fprintf( stderr, "Invalid selection!\n" );
		print_main_menu();
		break;
	}
}

void compare( data_set_t& ds, reference_data_set_t& rds )
{
	control_age_distribution_bin_compare( ds, rds );
	//control_cbc_values_quantile_compare( ds );
	cbc_code_in_panel_redflag( ds );
	check_panel_subsets( ds );
	control_cbc_values_by_age_bin_compare( ds, rds ); 
	control_cbc_values_by_age_bin_anova( ds ); 
}

void write_xls( data_set_t& ds, reference_data_set_t& rds )
{
	general_demography_inforamtion( ds );
	
	crc_total_count( ds );

	control_age_distribution_bin_to_xls( ds );

	/////////////////////crc_total_count( ds_b);

	crc_age_distribution_bin_to_xls( ds );
	/////////	crc_age_distribution_bin_compare( ds , 0 );
	crc_risk_by_age_bin( ds );

	stage_distribution( ds );

	last_panel_before_date_control( ds );

	last_panel_before_crc_onset( ds ); 

	panel_size_distribution( ds );
	cbc_code_in_panel_distribution( ds );
	
	control_cbc_values_distribtion_bin( ds );
	crc_cbc_values_distribtion_bin( ds );

	control_cbc_values_by_age_bin_to_xls( ds ); // adding pages

	compare( ds, rds );
}

void run_all( data_set_t& ds, reference_data_set_t& rds )
{
	general_demography_inforamtion( ds );
	population_by_year( ds, 0, 120);
	control_age_histogram_by_year( ds );
	control_age_distribution_bin_to_stdout( ds );
	
	crc_total_count( ds );
	crc_count_by_year( ds );
	crc_count_by_age( ds );
	crc_age_distribution_bin_to_stdout( ds );
	crc_age_distribution_bin_to_xls( ds );
	crc_risk_by_age( ds );
	crc_risk_by_age_bin( ds );
	crc_risk_by_year( ds, 0, 120 );
	crc_risk_by_year( ds, 50, 75 );
	other_cancer_information( ds );
	crc_onset_and_health_provider_change( ds );
	stage_distribution( ds );
	crc_moments_and_quantiles( ds );

	cbc_amount_by_age( ds );
	cbc_amount_by_year( ds );
	last_panel_before_date_control( ds );
	last_panel_before_crc_onset( ds );
	panel_size_distribution( ds );
	panel_type_distribution( ds );
	cbc_code_in_panel_distribution( ds );
	time_diff_for_adjacent_panels( ds );
	panel_number_distribution_for_healthy( ds );
	cbc_frequency( ds );
	check_panel_subsets( ds );
	control_cbc_values_by_age_bin_anova( ds );
	cbc_for_control_per_person_per_age( ds );
	
	control_cbc_values_by_age_bin_to_stdout( ds );
	cbc_values_for_controls_in_age_window_by_year( ds ); 
	cbc_values_for_crc_by_age( ds );
	control_cbc_values_distribtion_bin( ds );
	crc_cbc_values_distribtion_bin( ds );
	crc_cbc_values_within_a_window_distribution_bin( ds );
	control_cbc_values_quantile_to_stdout( ds, true );
	control_cbc_values_quantile_to_stdout( ds, false );
	crc_cbc_values_quantile( ds, true );
	crc_cbc_values_quantile( ds, false );

}