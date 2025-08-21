#include "demography_stats.h"
#include "tools.h"
#include <string>
#include <algorithm>
#include "xls.h"
#include <string.h>

using namespace std;

void general_demography_inforamtion( data_set_t& ds ) 
{

	int cnt_total = 0;
	int cnt_by_sex[GENDERS_NUM];
	int cnt_in_censor[GENDERS_NUM];
	int cnt_out_censor[GENDERS_NUM][2];

	memset(cnt_by_sex, 0, GENDERS_NUM * sizeof(int));
	memset(cnt_in_censor, 0, GENDERS_NUM * sizeof(int));
	memset(cnt_out_censor, 0, 2*GENDERS_NUM * sizeof(int));

	for( demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++ ) {
		id_type id = it->first;
		int gender = gender2number( it->second.gender );
		bool in_censor = ds.censor[id].in_censor;
		int in_censor_reason = ds.censor[id].in_censor_reason;
		cnt_total++;
		cnt_by_sex[gender]++;
		if( in_censor ) {
			cnt_in_censor[gender]++;
		} else {
			cnt_out_censor[gender][in_censor_reason-1]++;
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nGeneral population information\n" );
	WRITE_OUTPUT( "Total demography size: \t%d\n", cnt_total );
	for( int g=MALE;g<GENDERS_NUM;g++ ) {
		WRITE_OUTPUT( "%ss in demography: \t%d\t%.2f%%\n", gender_names[g], cnt_by_sex[g], 100.0*cnt_by_sex[g]/cnt_total );
		WRITE_OUTPUT( "%ss in censor: \t%d\t%.2f%%\n", gender_names[g], cnt_in_censor[g], 100.0*cnt_in_censor[g]/cnt_by_sex[g] );
		WRITE_OUTPUT( "%ss out of censor (reason - entrance after %d): \t%d\t%.2f%%\n",
			gender_names[g], ds.params["CENSOR_INSCULSION_END_DATE"], cnt_out_censor[g][0], 100.0*cnt_out_censor[g][0]/cnt_by_sex[g] );
		WRITE_OUTPUT( "%ss out of censor (reason - exit before %d): \t%d\t%.2f%%\n", 
			gender_names[g], ds.params["CENSOR_INSCULSION_START_DATE"], cnt_out_censor[g][1], 100.0*cnt_out_censor[g][1]/cnt_by_sex[g] );
	}
	CLOSE_OUTPUT();

	try {
		xls_sheet_t s( "general" );
		s.w( "Total demography" ); s.w( cnt_total ); s.nl();
		s.w( "" ); s.w( "Males" ); s.w( "Females" ); s.nl();
		s.w( "demography" ); s.w( cnt_by_sex[MALE] ); s.w( cnt_by_sex[FEMALE] ); s.nl();
		s.w( "censor in" ); s.w( cnt_in_censor[MALE] ); s.w( cnt_in_censor[FEMALE] ); s.nl();
		s.w( "censor out(reason start)" ); s.w( cnt_out_censor[MALE][0] ); s.w( cnt_out_censor[FEMALE][0] ); s.nl();
		s.w( "censor out(reason end)" ); s.w( cnt_out_censor[MALE][1] ); s.w( cnt_out_censor[FEMALE][1] ); s.nl();
	}
	catch ( ... ) {
	}
}

void control_age_histogram_by_year( data_set_t& ds )
{

	map<int,map<int, int>> cnt[GENDERS_NUM];
	map<int, int> total[GENDERS_NUM];
	for( demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++ ) {
		int id = it->first;
		int birth_year = it->second.byear;
		int gender = gender2number(it->second.gender);

		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) {
			continue;
		}
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) {
			continue;
		}
		
		for( int year = ds.params["REGISTRY_FIRST_YEAR"]; year < ds.params["REGISTRY_LAST_YEAR"]; year++ ) {
			if( is_in_censor_for_year( year, id, ds ) ) {

				int age = year - birth_year;

				cnt[gender][year][age] ++;
				//if( ( age >= 50 ) && ( age < 75 ) ) {
					total[gender][year] ++;
				//}
			}
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nAge Histogram by year (%d-%d)\n", ds.params["REGISTRY_FIRST_YEAR"], ds.params["REGISTRY_LAST_YEAR"] );
	for( int g = MALE; g< GENDERS_NUM; g++ ) {
		for( int a = 0; a < 100; a++ ) {
			WRITE_OUTPUT( "%ss aged %d: ", gender_names[g], a );
			for( int y = ds.params["REGISTRY_FIRST_YEAR"]; y < ds.params["REGISTRY_LAST_YEAR"]; y++ ) {
				WRITE_OUTPUT("%d %.2f%% ", cnt[g][y][a], 100.0*cnt[g][y][a]/total[g][y]);
			}
			WRITE_OUTPUT( "\n" );
		}
	}
	CLOSE_OUTPUT();
}

void population_by_year( data_set_t& ds, int min_age, int max_age )
{

	map<int, int> cnt[GENDERS_NUM];
	for( demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++ ) {
		int id = it->first;
		int gender = gender2number(it->second.gender);
		int birth_year = it->second.byear;

		for( int y=ds.params["REGISTRY_FIRST_YEAR"]; y<ds.params["REGISTRY_LAST_YEAR"]; y++ ) {
			int age = y - birth_year;

			if( age < min_age || age > max_age ) {
				continue;
			}

			if( is_in_censor_for_year( y, id, ds ) ) {
				cnt[gender][y] ++ ;
			}
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nPopulation in censor by year (for ages %d-%d)\n", min_age, max_age );
	WRITE_OUTPUT( "Year\tMales\tFemales\n" );
	for( int y=ds.params["REGISTRY_FIRST_YEAR"]; y<ds.params["REGISTRY_LAST_YEAR"]; y++ ) {
		WRITE_OUTPUT( "%d\t%d\t%d\n", y, cnt[MALE][y], cnt[FEMALE][y] );
	}
	CLOSE_OUTPUT();
}

age_bin_t control_age_distribution_bin( data_set_t& ds )
{

	const int current_year = ds.params["REF_YEAR_FOR_AGE_CALCULATION"];
	const int min_age_for_distribution = ds.params["MIN_AGE_FOR_DISTRIBUTION"];
	const int max_age_for_distribution = ds.params["MAX_AGE_FOR_DISTRIBUTION"];

	age_bin_t bin(AGE_BIN_SIZE, min_age_for_distribution, ds.source);
		
	for( demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++ ) {
		int id = it->first;
		
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) {
			continue;
		}
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) {
			continue;
		}

		int birth_year = it->second.byear;
		int age = current_year - birth_year;
		if( age < min_age_for_distribution || age >= max_age_for_distribution ) {
			continue;
		}
		int gender = gender2number(it->second.gender);
		if( is_in_censor_for_year(current_year, id, ds) ) {
			bin.age_bin.add( age, gender );
		}
	}

	return bin;
}

void control_age_distribution_bin_to_stdout( data_set_t& ds ) 
{
	age_bin_t bin = control_age_distribution_bin( ds );
	const int year = ds.params["REF_YEAR_FOR_AGE_CALCULATION"];

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nAge distribution for year %d by bins\n", year );
	WRITE_OUTPUT( "Include criteria: %s\n", "Demography in censor" );
	WRITE_OUTPUT( "Exclude criteria: %s\n", "CANCER_TYPE_CRC" );
	WRITE_OUTPUT( "Exclude criteria: %s\n", "CANCER_TYPE_NON_CRC" );
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		for( int b = 0; b < MAX_AGE_BIN; b++ ) {
			printf( "%ss aged [%d-%d): %d %.2f\n",
				gender_names[g],
				b * bin.age_bin.size, (b + 1)*bin.age_bin.size,
				bin.age_bin.data[g][b], 100.0*bin.age_bin.data[g][b]/bin.age_bin.cnt[g] );
		}
		printf( "%ss total %d\n", gender_names[g], bin.age_bin.cnt[g] );
	}
	CLOSE_OUTPUT();
}

void control_age_distribution_bin_to_xls( data_set_t& ds ) 
{
	age_bin_t bin = control_age_distribution_bin( ds );

	try {
		xls_sheet_t s( "control age dist by bins" );
		s.w( "Subset" ); s.w( "Control" ); s.nl();
		s.w( "Reference year" ); s.w( ds.params["REF_YEAR_FOR_AGE_CALCULATION"] ); s.nl();
		s.w( "Age Bin" ); s.w( "N Male" ); s.w( "N Female" ); s.nl();
		for( int b = 0; b < MAX_AGE_BIN; b++ ) {
			char label[MAX_STRING_LEN];
			snprintf( label, sizeof(label), "%d-%d", b *bin.age_bin.size, ( b + 1 )*bin.age_bin.size );
			s.w(label); s.w(bin.age_bin.data[MALE][b]); s.w(bin.age_bin.data[FEMALE][b]); s.nl();
		}
		s.w( "Total" ); s.w( bin.age_bin.cnt[MALE] ); s.w( bin.age_bin.cnt[FEMALE] ); s.nl();
	}
	catch ( ... ) {
	}

}

void control_age_distribution_bin_compare( data_set_t& ds, reference_data_set_t& rds )
{
	age_bin_t source_bin = control_age_distribution_bin( ds );
	int ret = age_bins_compare( rds.age_bin, source_bin );

	OPEN_OUTPUT()
	WRITE_OUTPUT("\n")
	if (ret == 0) {
		WRITE_OUTPUT("Control age histogram comparison - OK\n")
	} else { 
		WRITE_OUTPUT("%s Control age histogram Differs\n",RED_FLAG_MARKER)
	}

	CLOSE_OUTPUT()
	age_bins_print( rds.age_bin, source_bin, "control");	// this prints bins without notice to min & max
}