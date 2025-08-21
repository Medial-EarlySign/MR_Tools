#pragma once 
#ifndef __TOOLS__
#define __TOOLS__

#include <stdarg.h>
#include <stdio.h>
#include <assert.h>
#include <ctime>

///
/// global variables
///

extern FILE* fflags;
//extern libxl::Book* book;
extern char output_last_full_filename[MAX_STRING_LEN];
extern char output_log_full_filename[MAX_STRING_LEN];

///
/// constants
///

static const int MIN_AGE = 0;
static const int MAX_AGE = 125;
static const int AGE_BIN_SIZE = 5;

///
/// DATES
///

inline int days_since1900_2_year( int days ) {
	return ( days / 365 ) + 1900;
}

// Days from 01/01/1900
inline int get_days(date_t date) {
	
	int ddays2month[] = {0,31,59,90,120,151,181,212,243,273,304,334} ;

	int year = date/100/100 ;
	int month = (date/100)%100 ;
	int day = date%100 ;

	// Full years
	int days = 365 * (year-1900) ;
	days += (year-1897)/4 ;
	days -= (year-1801)/100 ;
	days += (year-1601)/400 ;

	// Full Months
	days += ddays2month[month-1] ;
	if (month>2 && (year%4)==0 && ((year%100)!=0 || (year%400)==0))
		days ++ ;
	days += (day-1) ;

	return days;
}

bool is_in_censor_for_year( int year, id_type id, data_set_t &ds );
bool is_in_censor_for_date_range( int min_date, int max_date, id_type id, data_set_t &ds );

//
// OUTPUT
//

#define OPEN_OUTPUT()                                   \
	FILE* fout = fopen(output_last_full_filename, "wt" );\
	assert( fout != NULL );

#define CLOSE_OUTPUT()			                        \
	fclose( fout );										

#define WRITE_OUTPUT( format, ... )						\
	printf( format, ##__VA_ARGS__ );						\
	fprintf( fout, format, ##__VA_ARGS__ );

//
// COMPARISON OUTPUT
//

#define FLAGS_OUTPUT( format, ... )						\
	printf( format, ##__VA_ARGS__ );						\
	fprintf( fflags, format, ##__VA_ARGS__ );


//
// LOG
//

#define OPEN_LOG()											\
	FILE* flog = fopen(output_log_full_filename, "w+" );	\
	if( flog == NULL )	{										\
		fprintf( stderr, "*** Error opening output file [%s] ***\n", output_log_full_filename );		\
		throw "Error opening file";										\
	}

#define CLOSE_LOG()				                        \
	fclose( flog );										

#define WRITE_LOG( format, ... )						\
	fprintf( flog, format, __VA_ARGS__ );

// Red Flag in Printing
#define RED_FLAG_MARKER "[RED FLAG]"

#endif 