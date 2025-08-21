#include "read_data.h"
#include <assert.h>
#include "tools.h"

char output_last_full_filename[MAX_STRING_LEN];
char output_log_full_filename[MAX_STRING_LEN];
char output_full_comparison_filename[MAX_STRING_LEN];

bool is_in_censor_for_year( int year, id_type id, data_set_t &ds )
{
	int censor_status = ds.censor[id].stat;
	int censor_reason = ds.censor[id].reason;
	int censor_year = days_since1900_2_year( ds.censor[id].date );
	if( ( censor_status == 1 ) && ( year >= censor_year ) ) {
		return true;  // join
	}
	if( ( censor_status == 2 && 8!=censor_reason )) {
		return true; // leave
	}
	if( ( censor_status == 2 && 8==censor_reason ) && ( year <= censor_year ) ) { 
		return true; // leave
	}

	return false;
}

bool is_in_censor_for_date_range( int min_date, int max_date, id_type id, data_set_t &ds )
{
	int censor_status = ds.censor[id].stat;
	int censor_reason = ds.censor[id].reason;
	int censor_date = ds.censor[id].date;

	if( ( censor_status == 1 ) && ( censor_date <= max_date  ) ) {
		return true;  // join before max date
	}

	if( ( censor_status == 2 && 8!=censor_reason )) {
		return true; // ???
	}

	if( ( censor_status == 2 && 8==censor_reason ) && ( censor_date <= max_date ) ) { 
		return true; // leave before max date
	}

	return false;

}