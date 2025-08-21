#pragma once 
#ifndef __MENU__
#define __MENU__

#include "read_data.h"
#include "data_types.h"

int print_main_menu( void ); 
int print_demography_menu( void );
int print_registry_menu( void );
int print_panel_menu( void );
int print_cbc_menu( void );

bool run_main_menu( int selection, data_set_t& ds, reference_data_set_t& rds );
void run_registry_menu( int selection, data_set_t& ds );
void run_demography_menu( int selection, data_set_t& ds );
void run_panel_menu( int selection, data_set_t& ds );
void run_cbc_menu( int selection, data_set_t& ds );

void run_all( data_set_t& ds, reference_data_set_t& rds );
void write_xls( data_set_t& ds, reference_data_set_t& rds );
void compare( data_set_t& ds, reference_data_set_t& rds );

#endif 


