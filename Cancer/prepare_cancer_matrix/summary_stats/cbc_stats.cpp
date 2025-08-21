#include "read_data.h"
#include "cbc_stats.h"
#include "limits"
#include "tools.h"
#include "data_types.h"
#include <assert.h>
#include <algorithm>
#include <string>
#include <boost/math/distributions/fisher_f.hpp>
#include <set>
#include "xls.h"

using namespace std;
using namespace boost::math;

cbc_values_by_age_bin_t control_cbc_values_by_age_bin( data_set_t& ds ) 
	//
	// Exclude criteria: crc 
	//
{
	cbc_values_by_age_bin_t cbc_values_by_age_bin(ds.cbc_codes, ds.source, "control");

	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender);
		cbc_values_by_age_bin.cvbab.total_cnt[gender]++;

		// exclude criteria
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) {
			cbc_values_by_age_bin.cvbab.excluded_cnt[gender]++;
			continue ;
		}
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) {
			cbc_values_by_age_bin.cvbab.excluded_cnt[gender]++;
			continue ;
		}
		
		
		int bday = get_days(10000*ds.demography[id].byear + 101) + 183 ;

		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
			int date = ds.cbc_dates_ex.dates[id][i] ;
			int age_bin = (date - bday)/365/5 ;
			assert(age_bin < MAX_AGE_BIN) ;

			for (map<int,double>::iterator it = ds.cbc[id][date].begin();
				it != ds.cbc[id][date].end(); it++) {
				assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[it->first].serial_num ;
				double value = it->second ;
				cbc_values_by_age_bin.cvbab.n[gender][age_bin][idx] ++ ;
				cbc_values_by_age_bin.cvbab.s[gender][age_bin][idx] += value ;
				cbc_values_by_age_bin.cvbab.s2[gender][age_bin][idx] += value*value;
				if( value < cbc_values_by_age_bin.cvbab.min[gender][age_bin][idx] ) {
					cbc_values_by_age_bin.cvbab.min[gender][age_bin][idx] = value;
				}
				if( value > cbc_values_by_age_bin.cvbab.max[gender][age_bin][idx] ) {
					cbc_values_by_age_bin.cvbab.max[gender][age_bin][idx] = value;
				}

			}
		}
	}

	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
		int i = it->second.serial_num;
		for (int gender=0; gender<GENDERS_NUM; gender++) {
			for (int age_bin=0; age_bin<MAX_AGE_BIN; age_bin++) {
				cbc_values_by_age_bin.cvbab.mean[gender][age_bin][i] = cbc_values_by_age_bin.cvbab.s[gender][age_bin][i]/cbc_values_by_age_bin.cvbab.n[gender][age_bin][i] ;
				cbc_values_by_age_bin.cvbab.sdv[gender][age_bin][i] = (cbc_values_by_age_bin.cvbab.n[gender][age_bin][i]==1) ? 0 :
					sqrt((cbc_values_by_age_bin.cvbab.s2[gender][age_bin][i] - cbc_values_by_age_bin.cvbab.mean[gender][age_bin][i]*cbc_values_by_age_bin.cvbab.s[gender][age_bin][i])/(cbc_values_by_age_bin.cvbab.n[gender][age_bin][i] - 1)) ;		
			}
		} 
	}
	return cbc_values_by_age_bin;
}

void control_cbc_values_by_age_bin_to_stdout( data_set_t& ds ) 
{
	cbc_values_by_age_bin_t cbc_values_by_age_bin = control_cbc_values_by_age_bin( ds );

	OPEN_OUTPUT();
	WRITE_OUTPUT("\nCBC values for controls by age\n");
	for( int g=0; g<GENDERS_NUM; g++ ) {
		WRITE_OUTPUT("%s total %d excluded %d\n", gender_names[g], cbc_values_by_age_bin.cvbab.total_cnt[g], cbc_values_by_age_bin.cvbab.excluded_cnt[g] );
	}

	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
		int i = it->second.serial_num;
		for (int gender=0; gender<GENDERS_NUM; gender++) {
			for (int age_bin=0; age_bin<MAX_AGE_BIN; age_bin++) {
				if (cbc_values_by_age_bin.cvbab.n[gender][age_bin][i] > 0) {
					WRITE_OUTPUT("Uncensored control: Test [%s] at ages %d-%d for %s : Mean = %.2f Standard-Deviation = %.2f Min = %.2f Max = %.2f N = %d\n",
						it->second.name.c_str(), 5*age_bin, 5*(age_bin+1),
						gender_names[gender],cbc_values_by_age_bin.cvbab.mean[gender][age_bin][i],cbc_values_by_age_bin.cvbab.sdv[gender][age_bin][i],cbc_values_by_age_bin.cvbab.min[gender][age_bin][i],cbc_values_by_age_bin.cvbab.max[gender][age_bin][i],cbc_values_by_age_bin.cvbab.n[gender][age_bin][i]) ;
				}
			}
		}
	}
	CLOSE_OUTPUT();

}

void control_cbc_values_by_age_bin_to_xls( data_set_t& ds ) 
{
	cbc_values_by_age_bin_t cbc_values_by_age_bin = control_cbc_values_by_age_bin( ds );

	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
		int i = it->second.serial_num;
		
		char sheet_name[MAX_STRING_LEN];
		snprintf( sheet_name, sizeof(sheet_name), "%s control", it->second.name.c_str() );
		
		try {
			xls_sheet_t s( sheet_name );
			s.w( "Dataset" ); s.w( ds.source.c_str() ); s.nl();
			s.w( "Subset" ); s.w( "Control" ); s.nl();
			s.w( "Gender" ); s.w( "Male" ); s.w( "Male" ); s.w( "Male" ); s.w( "Male" ); s.w( "Male" ); \
				s.w( "Female" ); s.w( "Female" ); s.w( "Female" ); s.w( "Female" ); s.w( "Female" ); s.nl();
			s.w( "Age Group" ); s.w( "N" ); s.w( "Mean" ); s.w( "SDV" ); s.w( "Min" ); s.w( "Max" ); \
				s.w( "N" ); s.w( "Mean" ); s.w( "SDV" ); s.w( "Min" ); s.w( "Max" );  s.nl();

			for (int age_bin=0; age_bin<MAX_AGE_BIN; age_bin++) {
				if ( cbc_values_by_age_bin.cvbab.n[MALE][age_bin][i] > 0 &&
					cbc_values_by_age_bin.cvbab.n[FEMALE][age_bin][i] > 0 ) {
						char label[MAX_STRING_LEN];
						snprintf( label, sizeof(label), "%d-%d", 5*age_bin, 5*(age_bin+1) );
						s.w( label);
						for( int g = MALE; g < GENDERS_NUM; g++ ) {
							s.w( cbc_values_by_age_bin.cvbab.n[g][age_bin][i] );
							s.w( cbc_values_by_age_bin.cvbab.mean[g][age_bin][i] );
							s.w( cbc_values_by_age_bin.cvbab.sdv[g][age_bin][i] );
							s.w( cbc_values_by_age_bin.cvbab.min[g][age_bin][i] );
							s.w( cbc_values_by_age_bin.cvbab.max[g][age_bin][i] );
						}
						s.nl();
				}
			}
		}
		catch ( ... ) {
		}
		
	}
}

void control_cbc_values_by_age_bin_compare( data_set_t& ds, reference_data_set_t rds )
{
	cbc_values_by_age_bin_t source_cbc_values_by_age_bin = control_cbc_values_by_age_bin( ds );
	cbc_values_by_age_bin_compare( rds.cbc_values_by_age_bin, source_cbc_values_by_age_bin );
}

void cbc_values_for_controls_in_age_window_by_year( data_set_t& ds ) 
	//
	// Exclude criteria: crc 
	//
{
	const int MIN_AGE = 50;
	const int MAX_AGE = 55;

	int total_cnt[GENDERS_NUM];
	int excluded_cnt[GENDERS_NUM];
	memset(total_cnt, 0, GENDERS_NUM * sizeof(int));
	memset(excluded_cnt, 0, GENDERS_NUM * sizeof(int));

	map<int,int> n[GENDERS_NUM][MAX_CBC_CODE_NUM];
	map<int, double> s[GENDERS_NUM][MAX_CBC_CODE_NUM];
	map<int, double> s2[GENDERS_NUM][MAX_CBC_CODE_NUM];
	map<int, double> max[GENDERS_NUM][MAX_CBC_CODE_NUM];
	map<int, double> min[GENDERS_NUM][MAX_CBC_CODE_NUM];
	
	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender);
		total_cnt[gender]++;

		// exclude criteria
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) {
			excluded_cnt[gender]++;
			continue ;
		}
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) {
			excluded_cnt[gender]++;
			continue ;
		}
		
		
		int bday = get_days(10000*ds.demography[id].byear + 101) + 183 ;

		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
			int date = ds.cbc_dates_ex.dates[id][i] ;
			int year = days_since1900_2_year( date );
			int age = (date - bday)/365;
			if( age < MIN_AGE || age > MAX_AGE) {
				continue;
			}

			for (map<int,double>::iterator it = ds.cbc[id][date].begin();
				it != ds.cbc[id][date].end(); it++) {
				assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[it->first].serial_num ;
				double value = it->second ;
				n[gender][idx][year] ++ ;
				s[gender][idx][year] += value ;
				s2[gender][idx][year] += value*value;
				if( min[gender][idx].find(year) == min[gender][idx].end() ) {
					min[gender][idx][year] = value;
				} 
				else {
					if( value < min[gender][idx][year] ) {
						min[gender][idx][year] = value;
					}
				}
				if( max[gender][idx].find(year) == max[gender][idx].end() ) {
					max[gender][idx][year] = value;
				}
				else {
					if( value > max[gender][idx][year] ) {
						max[gender][idx][year] = value;
					}
				}

			}
		}

	}

	OPEN_OUTPUT()
	WRITE_OUTPUT("\nCBC values for controls by age\n");
	for( int g=0; g<GENDERS_NUM; g++ ) {
		WRITE_OUTPUT("%s total %d excluded %d\n", gender_names[g], total_cnt[g], excluded_cnt[g] );
	}

	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
		int i = it->second.serial_num;
		for (int gender=0; gender<GENDERS_NUM; gender++) {
			for (int year=2000; year<2020; year++) {
				if (n[gender][i][year] > 0) {
					double mean = s[gender][i][year]/n[gender][i][year];
					double sdv = (n[gender][i][year]==1) ? 0 : sqrt((s2[gender][i][year] - mean*s[gender][i][year])/(n[gender][i][year] - 1)) ;
					WRITE_OUTPUT("Uncensored control: Test [%s] at ages %d-%d year %d for %s : Mean = %.2f Standard-Devaition = %.2f Min = %.2f Max = %.2f N = %d\n",
						it->second.name.c_str(), MIN_AGE, MAX_AGE, year,
						gender_names[gender],mean,sdv,min[gender][i][year],max[gender][i][year],n[gender][i][year]) ;
				}
			}
		}
	}
	CLOSE_OUTPUT()
}

void cbc_values_for_crc_by_age( data_set_t& ds )
	//
	// Include criteria: 
	// CRC
	// CBC within windows (CRC_DISCOVERY_WINDOWS_MINIMAL_DAYS - CRC_DISCOVERY_WINDOWS_MAXIMAL_DAYS)
	//
{
	int n[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	double s[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	double s2[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	
	memset(n, 0, MAX_AGE_BIN*MAX_CBC_CODE_NUM * sizeof(int));
	memset(s, 0, MAX_AGE_BIN*MAX_CBC_CODE_NUM * sizeof(double));
	memset(s2, 0, MAX_AGE_BIN*MAX_CBC_CODE_NUM * sizeof(double));

	for ( cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin();
		it != ds.registry[CANCER_TYPE_CRC].end(); it++) {
		int id = it->first ;

		if ( ds.cbc_dates_ex.dates.find(id) == ds.cbc_dates_ex.dates.end() ) { // no cbc for pt
			continue;
		}

		if( ds.cbc_dates_ex.dates[id][0] > it->second.days_since_1900 ) { // first cbc day is older than cbc onset
			continue;
		}
		
		// find last cbc within a window prior to crc
		int idx = -1 ;
//		assert( ds.cbc_dates[id].size() < INT_MAX ); 
		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
			if (ds.cbc_dates_ex.dates[id][i] >= it->second.days_since_1900 - ds.params["CRC_DISCOVERY_WINDOWS_MINIMAL_DAYS"])
				break ;
			if (ds.cbc_dates_ex.dates[id][i] >= it->second.days_since_1900 - ds.params["CRC_DISCOVERY_WINDOWS_MAXIMAL_DAYS"])
				idx = i ;
		}

		if (idx == -1) {
			continue; // no cbc within relevant range
		}
		
		int gender = gender2number(ds.demography[id].gender);
		int bday = get_days(10000*ds.demography[id].byear + 101) + 183 ;
		int date = ds.cbc_dates_ex.dates[id][idx] ;
		int age_bin = (date - bday)/365/5 ;
		assert(age_bin < MAX_AGE_BIN) ;

		for (map<int,double>::iterator it = ds.cbc[id][date].begin(); it != ds.cbc[id][date].end(); it++) {
			assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
			int idx = ds.cbc_codes.codes[it->first].serial_num;
			double value = it->second ;
			n[gender][age_bin][idx] ++ ;
			s[gender][age_bin][idx] += value ;
			s2[gender][age_bin][idx] += value*value;
		}

	}

	OPEN_OUTPUT()
	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin();
		it != ds.cbc_codes.codes.end(); it++ ) {
		int i = it->second.serial_num;
		for (int gender=0; gender<2; gender++) {
			for (int age_bin=0; age_bin<MAX_AGE_BIN; age_bin++) {
				if (n[gender][age_bin][i] > 0) {
					double mean = s[gender][age_bin][i]/n[gender][age_bin][i] ;
					double sdv = (n[gender][age_bin][i]==1) ? 0 : sqrt((s2[gender][age_bin][i] - mean*s[gender][age_bin][i])/(n[gender][age_bin][i] - 1)) ;
					WRITE_OUTPUT("CRC %d-%d days to registry: Test %s at ages %d-%d for %s : Mean = %.2f Standard-Deviation = %.2f N = %d\n",
						ds.params["CRC_DISCOVERY_WINDOWS_MINIMAL_DAYS"], ds.params["CRC_DISCOVERY_WINDOWS_MAXIMAL_DAYS"],
						it->second.name.c_str(), 5*age_bin,5*(age_bin+1), gender_names[gender],mean,sdv,n[gender][age_bin][i]) ;
				}
			}
			printf("\n") ;
		}
	}
	CLOSE_OUTPUT()
}

void crc_cbc_values_within_a_window_distribution_bin( data_set_t& ds )
	//
	// Include criteria: 
	// CRC
	// CBC within windows (CRC_DISCOVERY_WINDOWS_MINIMAL_DAYS - CRC_DISCOVERY_WINDOWS_MAXIMAL_DAYS)
	//
{
	map<double,int> values[MAX_CBC_CODE_NUM][GENDERS_NUM] ;

	for ( cancer_specific_type_registry_t::iterator rit = ds.registry[CANCER_TYPE_CRC].begin();
		rit != ds.registry[CANCER_TYPE_CRC].end(); rit++) {
		int id = rit->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender);

		if ( ds.cbc_dates_ex.dates.find(id) == ds.cbc_dates_ex.dates.end() ) { // no cbc for pt
			continue;
		}

		if( ds.cbc_dates_ex.dates[id][0] > rit->second.days_since_1900 ) { // first cbc day is older than cbc onset
			continue;
		}
		
		//for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
		for( vector<date_t>::reverse_iterator dit = ds.cbc_dates_ex.dates[id].rbegin(); dit != ds.cbc_dates_ex.dates[id].rend(); dit++ ) {
			int date = *dit;
			int window_start = rit->second.days_since_1900 - ds.params["CRC_DISCOVERY_WINDOWS_MAXIMAL_DAYS"];
			int window_end = rit->second.days_since_1900 - ds.params["CRC_DISCOVERY_WINDOWS_MINIMAL_DAYS"];
			if( date >= window_start && date <= window_end ) {
				for (map<int,double>::iterator cit = ds.cbc[id][date].begin(); cit != ds.cbc[id][date].end(); cit++) {
					assert(ds.cbc_codes.codes.find(cit->first) != ds.cbc_codes.codes.end()) ;
					int idx = ds.cbc_codes.codes[cit->first].serial_num ;
					double value = ((int) (ds.cbc_codes.codes[cit->first].resolution * cit->second))/ds.cbc_codes.codes[cit->first].resolution;
					values[idx][gender][value] ++ ;
				}
				continue; // we use only 1 date per person
			}
		}


	}

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nCBC Value Distribution for CRC within window (%d-%d days prior to crc)\n", 
		ds.params["CRC_DISCOVERY_WINDOWS_MINIMAL_DAYS"], ds.params["CRC_DISCOVERY_WINDOWS_MAXIMAL_DAYS"] ); 
	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin();
		it != ds.cbc_codes.codes.end(); it++ ) {
		int itest = it->second.serial_num;
		for (int gender = MALE ; gender < GENDERS_NUM ; gender ++) {

			vector<double> keys ;
			int ntotal = 0 ;
			for (map<double,int>::iterator itt = values[itest][gender].begin();
				itt != values[itest][gender].end(); itt++) {
				keys.push_back(itt->first) ;
				ntotal += itt->second ;
			}
			sort(keys.begin(),keys.end()) ;

			for (unsigned int i=0; i<keys.size(); i++) {
				WRITE_OUTPUT("Values Histogram of %s for %s : %f %.3f\n",
					it->second.name.c_str(), gender_names[gender], keys[i], (ntotal==0 ? 0 : (100.0*values[itest][gender][keys[i]])/ntotal)) ;
			}

		}
	}
	CLOSE_OUTPUT()
}

void control_cbc_values_distribtion_bin( data_set_t& ds )
{
	map<double,int> values[MAX_CBC_CODE_NUM][GENDERS_NUM] ;
	int ninds[MAX_CBC_CODE_NUM][GENDERS_NUM];
	memset(ninds, 0, MAX_CBC_CODE_NUM*GENDERS_NUM * sizeof(int));

	for ( cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++ ) {
		int id = it->first ;

		//exculde criteria
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) {
			continue;
		}
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) {
			continue;
		}
		assert( ds.demography.find(id) != ds.demography.end() );
		if( ! ds.censor[id].in_censor ) {
			continue;
		}

		int gender = gender2number(ds.demography[id].gender);
		int bday = get_days(10000*ds.demography[id].byear + 101) + 183 ;

		int taken[MAX_CBC_CODE_NUM];
		memset(ninds, 0, MAX_CBC_CODE_NUM * sizeof(int));

		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
			int date = ds.cbc_dates_ex.dates[id][i] ;
			int age = (date - bday)/365 ;
			if (age < ds.params["MIN_AGE_FOR_DISTRIBTION"] || age > ds.params["MAX_AGE_FOR_DISTRIBUTION"])
				continue ;

			for (map<int,double>::iterator it = ds.cbc[id][date].begin(); it != ds.cbc[id][date].end(); it++) {
				assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[it->first].serial_num ;
				double value = ((int) (ds.cbc_codes.codes[it->first].resolution * it->second))/ds.cbc_codes.codes[it->first].resolution;
				values[idx][gender][value] ++ ;
				taken[idx] = 1 ;
			}
		}

		for (int i=0; i<MAX_CBC_CODE_NUM; i++)
			ninds[i][gender] += taken[i] ;
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT( "\nCBC Value Distribution for controls\n" ); 
	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin();
		it != ds.cbc_codes.codes.end(); it++ ) {
		int itest = it->second.serial_num;
		for (int gender = MALE ; gender < GENDERS_NUM ; gender ++) {

			vector<double> keys ;
			int ntotal = 0 ;
			for (map<double,int>::iterator itt = values[itest][gender].begin();
				itt != values[itest][gender].end(); itt++) {
				keys.push_back(itt->first) ;
				ntotal += itt->second ;
			}
			sort(keys.begin(),keys.end()) ;

			for (unsigned int i=0; i<keys.size(); i++) {
				WRITE_OUTPUT("Values Histogram of %s for %s : %f %.3f\n",
					it->second.name.c_str(), gender_names[gender], keys[i], (ntotal==0 ? 0 : (100.0*values[itest][gender][keys[i]])/ntotal)) ;
			}
			WRITE_OUTPUT("Total # of %s for %s = %d (for %d individuals)\n",
				it->second.name.c_str(), gender_names[gender],ntotal,ninds[itest][gender]) ;
		}
	}
	CLOSE_OUTPUT();

	try {
		for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
			int itest = it->second.serial_num;

			char sheet_name[MAX_STRING_LEN];
			snprintf( sheet_name, sizeof(sheet_name), "%s control values dist", it->second.name.c_str() );
			xls_sheet_t s( sheet_name );

			set<double> keys; // notice that set is a sorted container
			int ntotal[GENDERS_NUM];
			memset(ntotal, 0, GENDERS_NUM * sizeof(int));
			for( int g = MALE; g < GENDERS_NUM; g++ ) {
				for (map<double,int>::iterator itt = values[itest][g].begin(); 	itt != values[itest][g].end(); itt++) {
					keys.insert(itt->first) ;
					ntotal[g] += itt->second ;
				}
			}

			s.w( "Subset" ); s.w( "control" ); s.nl();
			s.w( "Value" ); s.w( "Males" ); s.w( "Females" ); s.nl();
			for( set<double>::iterator itt = keys.begin(); itt != keys.end(); itt++ ) {
				s.w( *itt );
				s.w( ntotal[MALE]==0 ? 0 : (100.0*values[itest][MALE][*itt])/ntotal[MALE] );
				s.w( ntotal[FEMALE] == 0 ? 0 : (100.0*values[itest][FEMALE][*itt])/ntotal[FEMALE] );
				s.nl();
			}
			s.w( "Total values" ); s.w( ntotal[MALE] ); s.w( ntotal[FEMALE] ); s.nl();
			s.w( "Total individuals" ); s.w( ninds[itest][MALE] ); s.w( ninds[itest][FEMALE] ); s.nl();
		}
	}
	catch ( ... ) {
	}

}

void crc_cbc_values_distribtion_bin( data_set_t& ds )
{
	map<double,int> values[MAX_CBC_CODE_NUM][GENDERS_NUM] ;
	int ninds[MAX_CBC_CODE_NUM][GENDERS_NUM];
	memset(ninds, 0, MAX_CBC_CODE_NUM*GENDERS_NUM * sizeof(int));

	for ( cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++ ) {
		int id = it->first ;

		//exculde criteria
		if( ds.registry[CANCER_TYPE_CRC].find(id) == ds.registry[CANCER_TYPE_CRC].end() ) {
			continue;
		}
		assert( ds.demography.find(id) != ds.demography.end() );
		if( ! ds.censor[id].in_censor ) {
			continue;
		}

		int gender = gender2number(ds.demography[id].gender);
		//int bday = get_days(10000*demography[id].byear + 101) + 183 ;

		int taken[MAX_CBC_CODE_NUM];
		memset(taken, 0, MAX_CBC_CODE_NUM * sizeof(int));

		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
			int date = ds.cbc_dates_ex.dates[id][i] ;

			for (map<int,double>::iterator it = ds.cbc[id][date].begin(); it != ds.cbc[id][date].end(); it++) {
				assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[it->first].serial_num ;
				double value = ((int) (ds.cbc_codes.codes[it->first].resolution * it->second))/ds.cbc_codes.codes[it->first].resolution;
				values[idx][gender][value] ++ ;
				taken[idx] = 1 ;
			}
		}

		for (int i=0; i<MAX_CBC_CODE_NUM; i++)
			ninds[i][gender] += taken[i] ;
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT( "\nCBC Value Distribution for CRC\n" ); 
	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
		int itest = it->second.serial_num;
		for (int gender = 0 ; gender < 2 ; gender ++) {

			vector<double> keys ;
			int ntotal = 0 ;
			for (map<double,int>::iterator itt = values[itest][gender].begin(); itt != values[itest][gender].end(); itt++) {
				keys.push_back(itt->first) ;
				ntotal += itt->second ;
			}
			sort(keys.begin(),keys.end()) ;

			for (unsigned int i=0; i<keys.size(); i++) {
				WRITE_OUTPUT("Values Histogram of %s for %s : %f %.3f\n",
				it->second.name.c_str(), gender_names[gender], keys[i], (ntotal==0 ? 0 : (100.0*values[itest][gender][keys[i]])/ntotal)) ;
			}

			WRITE_OUTPUT("Total # of %s for %s = %d (for %d individuals)\n",
				it->second.name.c_str(), gender_names[gender],ntotal,ninds[itest][gender]) ;
		}
	}
	CLOSE_OUTPUT();

	try {
		for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
			int itest = it->second.serial_num;

			char sheet_name[MAX_STRING_LEN];
			snprintf( sheet_name, sizeof(sheet_name), "%s crc values dist", it->second.name.c_str() );
			xls_sheet_t s( sheet_name );

			set<double> keys; // notice that set is a sorted container
			int ntotal[GENDERS_NUM];
			memset(ntotal, 0, GENDERS_NUM * sizeof(int));
			for( int g = MALE; g < GENDERS_NUM; g++ ) {
				for (map<double,int>::iterator itt = values[itest][g].begin(); 	itt != values[itest][g].end(); itt++) {
					keys.insert(itt->first) ;
					ntotal[g] += itt->second ;
				}
			}

			s.w( "Subset" ); s.w( "crc" ); s.nl();
			s.w( "Value" ); s.w( "Males" ); s.w( "Females" ); s.nl();
			for( set<double>::iterator itt = keys.begin(); itt != keys.end(); itt++ ) {
				s.w( *itt );
				s.w( ntotal[MALE]==0 ? 0 : (100.0*values[itest][MALE][*itt])/ntotal[MALE] );
				s.w( ntotal[FEMALE] == 0 ? 0 : (100.0*values[itest][FEMALE][*itt])/ntotal[FEMALE] );
				s.nl();
			}
			s.w( "Total values" ); s.w( ntotal[MALE] ); s.w( ntotal[FEMALE] ); s.nl();
			s.w( "Total individuals" ); s.w( ninds[itest][MALE] ); s.w( ninds[itest][FEMALE] ); s.nl();
		}
	}
	catch ( ... ) {
	}
}

cbc_estimates_t control_cbc_values_quantile( data_set_t& ds ) 
	//
	// Exclude criteria: crc 
	//
{
	cbc_estimates_t est;

	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;

		// exclude criteria
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) {
			continue ;
		}
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) {
			continue ;
		}

		int gender = gender2number(ds.demography[id].gender);

		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
			int date = ds.cbc_dates_ex.dates[id][i] ;
			for (map<int,double>::iterator it = ds.cbc[id][date].begin();
				it != ds.cbc[id][date].end(); it++) {
				assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[it->first].serial_num ;
				double value = it->second ;
				est.n[gender][idx] ++ ;
				est.s[gender][idx] += value ;
				est.s2[gender][idx] += value*value;
				est.values[gender][idx].push_back( value );
			}
		}
	}

	for( int g=MALE; g < GENDERS_NUM; g++ ) {
		for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
			int idx = it->second.serial_num;
			est.mean[g][idx] = est.s[g][idx]/est.n[g][idx] ;
			est.sdv[g][idx] = (est.n[g][idx]==1) ? 0 : sqrt((est.s2[g][idx] - est.mean[g][idx]*est.s[g][idx])/(est.n[g][idx] - 1)) ;
		}
	}

	return est;
}

void control_cbc_values_quantile_to_stdout( data_set_t& ds, bool calculated_outliers )
{
	cbc_estimates_t est = control_cbc_values_quantile( ds );

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nCBC values quantiles with outliers for crc\n" );
	for( int g=MALE; g < GENDERS_NUM; g++ ) {
		for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
			int idx = it->second.serial_num;
			size_t size = est.values[g][idx].size();
			if( size == 0 ) {
				WRITE_OUTPUT( "%ss %s: No values found\n", gender_names[g], it->second.name.c_str() );
				continue;
			}

			std::sort( est.values[g][idx].begin(), est.values[g][idx].end() );
			
			size_t min = 0;
			size_t q1 = size / 4;
			size_t q2 = q1 * 2;
			size_t q3 = q1 * 3;
			size_t median = (size + 1) / 2;
			size_t max = size - 1;
			double mean_val = est.s[g][idx]/est.n[g][idx] ;
			double sdv_val = (est.n[g][idx]==1) ? 0 : sqrt((est.s2[g][idx] - mean_val*est.s[g][idx])/(est.n[g][idx] - 1)) ;
			
			double min_outlier_value = mean_val - 7 *sdv_val < 0 ? 0: mean_val - 7 *sdv_val;
			double max_outlier_value = mean_val + 7 *sdv_val;
			if( ! calculated_outliers ) {
				min_outlier_value = it->second.min_outlier[g]; 
				max_outlier_value = it->second.max_outlier[g]; 
			} 

			int min_outlier_cnt = 0;
			int max_outlier_cnt = 0;
			
			for( vector<double>::iterator vit = est.values[g][idx].begin(); vit != est.values[g][idx].end(); vit++ ) {
				if( *vit < min_outlier_value ) {
					min_outlier_cnt++;
				}
				else {
					break;
				}
			}

			for( vector<double>::reverse_iterator vit = est.values[g][idx].rbegin();
				vit != est.values[g][idx].rend(); 
				vit++ ) {
				if( *vit > max_outlier_value ) {
					max_outlier_cnt++;
				}
				else {
					break;
				}
			}

			WRITE_OUTPUT( "%ss %s: min = %.2f, q1 = %.2f, q2 = %.2f, median = %.2f, q3 = %.2f, max = %.2f\n",
				gender_names[g], it->second.name.c_str(), 
				est.values[g][idx][min], est.values[g][idx][q1], est.values[g][idx][q2], est.values[g][idx][median], est.values[g][idx][q3], est.values[g][idx][max] );
			WRITE_OUTPUT( "%ss %s min outlier: value %.2f count %d (%.2f%%)\n",
				gender_names[g], it->second.name.c_str(), 
				min_outlier_value, min_outlier_cnt, 100.0*min_outlier_cnt/size );
			WRITE_OUTPUT( "%ss %s max outlier: value %.2f cout %d (%.2f%%)\n",
				gender_names[g], it->second.name.c_str(), 
				max_outlier_value, max_outlier_cnt, 100.0*max_outlier_cnt/size );
		}
	}
	CLOSE_OUTPUT();
}

void control_cbc_values_quantile_compare( data_set_t& ds ) 
{
	cbc_estimates_t est_a = control_cbc_values_quantile( ds );
	cbc_estimates_t est_b = control_cbc_values_quantile( ds );
	int ret = cbc_estimates_compare( est_a, est_b );
	printf( "\nControl cbc distribution comparison = %d\n", ret );
	cbc_estimates_print( est_a, est_b );
}

void crc_cbc_values_quantile( data_set_t& ds, bool calculated_outliers ) 
	//
	// Include criteria: crc 
	//
{
	int n[GENDERS_NUM][MAX_CBC_CODE_NUM];
	double s[GENDERS_NUM][MAX_CBC_CODE_NUM];
	double s2[GENDERS_NUM][MAX_CBC_CODE_NUM];
	memset(n, 0, GENDERS_NUM*MAX_CBC_CODE_NUM * sizeof(int));
	memset(s, 0, GENDERS_NUM*MAX_CBC_CODE_NUM * sizeof(double));
	memset(s2, 0, GENDERS_NUM*MAX_CBC_CODE_NUM * sizeof(double));

	vector<double> values[GENDERS_NUM][MAX_CBC_CODE_NUM];

	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;

		// include criteria
		if( ds.registry[CANCER_TYPE_CRC].find(id) == ds.registry[CANCER_TYPE_CRC].end() ) {
			continue ;
		}

		int gender = gender2number(ds.demography[id].gender);

		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
			int date = ds.cbc_dates_ex.dates[id][i] ;
			for (map<int,double>::iterator it = ds.cbc[id][date].begin();
				it != ds.cbc[id][date].end(); it++) {
				assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[it->first].serial_num ;
				double value = it->second ;
				n[gender][idx] ++ ;
				s[gender][idx] += value ;
				s2[gender][idx] += value*value;
				values[gender][idx].push_back( value );
			}
		}
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT( "\nCBC values quantiles with outliers for CRC\n" );
	for( int g=MALE; g < GENDERS_NUM; g++ ) {
		for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin();
		it != ds.cbc_codes.codes.end(); it++ ) {
			int idx = it->second.serial_num;
			size_t size = values[g][idx].size();
			if( size == 0 ) {
				WRITE_OUTPUT( "%ss %s: No values found\n", gender_names[g], it->second.name.c_str() );
				continue;
			}

			std::sort( values[g][idx].begin(), values[g][idx].end() );
			
			size_t min = 0;
			size_t q1 = size / 4;
			size_t q2 = q1 * 2;
			size_t q3 = q1 * 3;
			size_t median = (size + 1) / 2;
			size_t max = size - 1;
			double mean_val = s[g][idx]/n[g][idx] ;
			double sdv_val = (n[g][idx]==1) ? 0 : sqrt((s2[g][idx] - mean_val*s[g][idx])/(n[g][idx] - 1)) ;
			
			double min_outlier_value = mean_val - 7 *sdv_val < 0 ? 0: mean_val - 7 *sdv_val;
			double max_outlier_value = mean_val + 7 *sdv_val;
			if( ! calculated_outliers ) {
				min_outlier_value = it->second.min_outlier[g]; 
				max_outlier_value = it->second.max_outlier[g]; 
			} 

			int min_outlier_cnt = 0;
			int max_outlier_cnt = 0;
			
			for( vector<double>::iterator vit = values[g][idx].begin(); vit != values[g][idx].end(); vit++ ) {
				if( *vit < min_outlier_value ) {
					min_outlier_cnt++;
				}
				else {
					break;
				}
			}

			for( vector<double>::reverse_iterator vit = values[g][idx].rbegin();
				vit != values[g][idx].rend(); 
				vit++ ) {
				if( *vit > max_outlier_value ) {
					max_outlier_cnt++;
				}
				else {
					break;
				}
			}

			WRITE_OUTPUT( "%ss %s: min = %.2f, q1 = %.2f, q2 = %.2f, median = %.2f, q3 = %.2f, max = %.2f\n",
				gender_names[g], it->second.name.c_str(), 
				values[g][idx][min], values[g][idx][q1], values[g][idx][q2], values[g][idx][median], values[g][idx][q3], values[g][idx][max] );
			WRITE_OUTPUT( "%ss %s min outlier: value %.2f count %d (%.2f%%)\n",
				gender_names[g], it->second.name.c_str(), 
				min_outlier_value, min_outlier_cnt, 100.0*min_outlier_cnt/size );
			WRITE_OUTPUT( "%ss %s max outlier: value %.2f cout %d (%.2f%%)\n",
				gender_names[g], it->second.name.c_str(), 
				max_outlier_value, max_outlier_cnt, 100.0*max_outlier_cnt/size );
		}
	}
	CLOSE_OUTPUT()
}

void control_cbc_values_by_age_bin_anova( data_set_t& ds ) 
{
	map<int,int> n[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	map<int, double> s[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	map<int, double> s2[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	int gn[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	double gs[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	double SSBetween[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	int SSBetweenDF[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	double SSWithin[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	int SSWithinDF[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	double gmean[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];

	const int min_year = ds.params["CBC_FIRST_YEAR"];
	const int max_year = ds.params["CBC_LAST_YEAR"];
	const int k = max_year - min_year;
	map<int, double> mean[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];
	map<int, double> sdv[GENDERS_NUM][MAX_CBC_CODE_NUM][MAX_AGE_BIN];

	for( int g = 0; g < GENDERS_NUM; g++ ) {
		for( int c = 0 ; c < MAX_CBC_CODE_NUM; c++ ) {
			for( int ab = 0; ab < MAX_AGE_BIN; ab++ ) {
				gn[g][c][ab] = 0;
				gs[g][c][ab] = 0;
				SSBetween[g][c][ab] = 0;
				SSBetweenDF[g][c][ab] = 0;
				SSWithin[g][c][ab] = 0;
				SSWithinDF[g][c][ab] = 0;
				gmean[g][c][ab] = 0;
			}
		}
	}

	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender);

		// exclude criteria
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) continue ;
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) continue ;
		
		int bday = get_days(10000*ds.demography[id].byear + 101) + 183 ;

		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {

			int date = ds.cbc_dates_ex.dates[id][i] ;
			int year = days_since1900_2_year( date );
			if( year < min_year || year >= max_year ) continue;

			int age = (date - bday) / 365;
			int age_bin = age / AGE_BIN_SIZE;
			if( age_bin >= MAX_AGE_BIN ) continue;

			for (map<int,double>::iterator it = ds.cbc[id][date].begin(); it != ds.cbc[id][date].end(); it++) {
				assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[it->first].serial_num ;
				double value = it->second ;
				n[gender][idx][age_bin][year] ++ ;
				s[gender][idx][age_bin][year] += value ;
				s2[gender][idx][age_bin][year] += value * value ;
				gn[gender][idx][age_bin] ++ ;
				gs[gender][idx][age_bin] += value ;
			}
		}
	}

	// Between Variance
	for (int g=0; g<GENDERS_NUM; g++) {
		for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
			int i = it->second.serial_num;
			for( int ab = 0; ab < MAX_AGE_BIN; ab ++ ) {
				if( gn[g][i][ab] > 0 ) {
					gmean[g][i][ab] = gs[g][i][ab] / gn[g][i][ab];
					for (int year=min_year; year<max_year; year++) {
						if( n[g][i][ab][year] > 0 ) {
							double m = s[g][i][ab][year] / n[g][i][ab][year];
							mean[g][i][ab][year] = m;
							sdv[g][i][ab][year] = sqrt( ( s2[g][i][ab][year] - m * s[g][i][ab][year] ) / ( n[g][i][ab][year] - 1 ) );
							SSBetween[g][i][ab] += n[g][i][ab][year] * ( ( m - gmean[g][i][ab] ) * ( m - gmean[g][i][ab] ) );
							SSBetweenDF[g][i][ab] ++;
						}
					}
				}
			}
		}
	}

	// Within Variance
	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender);
		
		// exclude criteria
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) continue ;
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) continue ;
		
		int bday = get_days(10000*ds.demography[id].byear + 101) + 183 ;

		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {

			int date = ds.cbc_dates_ex.dates[id][i] ;
			int year = days_since1900_2_year( date );
			if( year < min_year || year >= max_year ) continue;

			int age = (date - bday) / 365;
			int age_bin = age / AGE_BIN_SIZE;
			if( age_bin >= MAX_AGE_BIN ) continue;

			for (map<int,double>::iterator it = ds.cbc[id][date].begin(); it != ds.cbc[id][date].end(); it++) {
				assert(ds.cbc_codes.codes.find(it->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[it->first].serial_num ;
				double value = it->second ;
				double m = mean[gender][idx][age_bin][year];
				double d = value - m;
				SSWithin[gender][idx][age_bin] += ( d * d );
				SSWithinDF[gender][idx][age_bin] ++ ;
			}
		}
	}
	
	// Correct Degreas of freedom
	for( int g = 0; g< GENDERS_NUM;g++ ) {
		for( int idx = 0; idx < MAX_CBC_CODE_NUM; idx++ ) {
			for( int age_bin = 0; age_bin < MAX_AGE_BIN; age_bin++ ) {
				SSBetweenDF[g][idx][age_bin] -= 1; // K - 1
				SSWithinDF[g][idx][age_bin] -= k;  // N - k
			}
		}
	}
	
	OPEN_OUTPUT()
	WRITE_OUTPUT("\nCBC values Anova\n");
	for (int g=0; g<GENDERS_NUM; g++) {
		for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
			int i = it->second.serial_num;
			for( int ab = 0; ab < MAX_AGE_BIN; ab ++ ) {
				if( SSBetweenDF[g][i][ab] > 0 && SSWithinDF[g][i][ab] > 0 ) {

					double F = ( SSBetween[g][i][ab] / SSBetweenDF[g][i][ab] ) / ( SSWithin[g][i][ab] / SSWithinDF[g][i][ab] );
					double p = 1 - cdf( fisher_f(SSBetweenDF[g][i][ab], SSWithinDF[g][i][ab]), F );
					const int bonferonni = GENDERS_NUM * MAX_CBC_CODE_NUM * MAX_AGE_BIN;
					double corrected_p = p * bonferonni;

					double min_mean = DBL_MAX, max_mean = DBL_MIN;
					double min_sdv = DBL_MAX, max_sdv = DBL_MIN;
					for( int y = min_year; y < max_year; y++ ) {
						if( sdv[g][i][ab][y] < min_sdv ) min_sdv = sdv[g][i][ab][y];
						if( sdv[g][i][ab][y] > max_sdv ) max_sdv = sdv[g][i][ab][y];
						if( mean[g][i][ab][y] < min_mean ) min_mean = mean[g][i][ab][y];
						if( mean[g][i][ab][y] > max_mean ) max_mean = mean[g][i][ab][y];
					}
					double sdv_d = max_sdv - min_sdv;
					double mean_d = max_mean - min_mean;
					
					if( corrected_p < 0.05 ) {
						WRITE_OUTPUT("%s Test [%s] at ages %d-%d for %s : BW = %.2f, WI = %.2f, F(%d,%d) = %.2f, p = %g, corrected p = %g, delta-mean/min_sdv=%.2f;",
							RED_FLAG_MARKER,
							it->second.name.c_str(), 
							ab*AGE_BIN_SIZE, (ab+1)*AGE_BIN_SIZE, gender_names[g], 
							SSBetween[g][i][ab], SSWithin[g][i][ab], 
							SSBetweenDF[g][i][ab], SSWithinDF[g][i][ab], 
							F, p, corrected_p, mean_d / min_sdv ) ;
						WRITE_OUTPUT("\tMean for years %d-%d %.2f (SUM=%.2f N=%d): ", min_year, max_year, gmean[g][i][ab], gs[g][i][ab], gn[g][i][ab] );
						for( int y = min_year; y < max_year; y++ ) {
							WRITE_OUTPUT( "(%d N=%d, m=%.2f s=%.2f), ", y, n[g][i][ab][y], mean[g][i][ab][y], sdv[g][i][ab][y] );
						}
						WRITE_OUTPUT( "\n" );
					}
				}
			}
		}
	}
	WRITE_OUTPUT( "CBC values anova - Done!\n" );
	CLOSE_OUTPUT()

		try {
			xls_sheet_t sh( "CBC values anova" );

			sh.w("Code");sh.w("Age");sh.w("Gender");sh.w("BW");sh.w("WI");sh.w("df BW");sh.w("df WI");sh.w("F");sh.w("P");sh.w("Corrected P");
			sh.w("mean/sdv", "DIfference between maximal and minimal per-year means divided by the smallest per-year sdv"); 
			char label[MAX_STRING_LEN];
			sprintf( label, "gloabl N (%d-%d)", min_year, max_year ); sh.w(label);
			sprintf( label, "Global mean (%d-%d)", min_year, max_year ); sh.w(label);
			sprintf( label, "global SDV (%d-%d)", min_year, max_year ); sh.w(label);
			for( int y = min_year; y < max_year; y++ ) {
				sprintf( label, "%d N", y ); sh.w( label );
				sprintf( label, "%d mean", y ); sh.w( label );
				sprintf( label, "%d sdv", y ); sh.w( label );
			}
			sh.w("RED FLAG") ;
			sh.nl();

			for (int g=0; g<GENDERS_NUM; g++) {
				for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin(); it != ds.cbc_codes.codes.end(); it++ ) {
					int i = it->second.serial_num;
					for( int ab = 0; ab < MAX_AGE_BIN; ab ++ ) {
						if( SSBetweenDF[g][i][ab] > 0 && SSWithinDF[g][i][ab] > 1 ) {

							double F = ( SSBetween[g][i][ab] / SSBetweenDF[g][i][ab] ) / ( SSWithin[g][i][ab] / SSWithinDF[g][i][ab] );
							double p = 1 - cdf( fisher_f(SSBetweenDF[g][i][ab], SSWithinDF[g][i][ab]), F );
							const int bonferonni = GENDERS_NUM * MAX_CBC_CODE_NUM * MAX_AGE_BIN;
							double corrected_p = p * bonferonni;

							double min_mean = DBL_MAX, max_mean = DBL_MIN;
							double min_sdv = DBL_MAX, max_sdv = DBL_MIN;
							for( int y = min_year; y < max_year; y++ ) {
								if( sdv[g][i][ab][y] < min_sdv ) min_sdv = sdv[g][i][ab][y];
								if( sdv[g][i][ab][y] > max_sdv ) max_sdv = sdv[g][i][ab][y];
								if( mean[g][i][ab][y] < min_mean ) min_mean = mean[g][i][ab][y];
								if( mean[g][i][ab][y] > max_mean ) max_mean = mean[g][i][ab][y];
							}
							double sdv_d = max_sdv - min_sdv;
							double mean_d = max_mean - min_mean;

							sh.w(it->second.name.c_str());
							sprintf(label, "%d-%d", ab*AGE_BIN_SIZE, (ab+1)*AGE_BIN_SIZE); sh.w(label);
							sh.w(gender_names[g]);
							sh.w(SSBetween[g][i][ab]);
							sh.w(SSWithin[g][i][ab]);
							sh.w(SSBetweenDF[g][i][ab]);
							sh.w(SSWithinDF[g][i][ab]);
							sh.w(F);
							sh.w(p);
							sh.w(corrected_p);
							sh.w(mean_d / min_sdv) ;

							sh.w(gn[g][i][ab]);
							sh.w(gmean[g][i][ab]);
							sh.w(gs[g][i][ab]);

							for( int y = min_year; y < max_year; y++ ) {
								sh.w(n[g][i][ab][y]);
								sh.w(mean[g][i][ab][y]);
								sh.w(sdv[g][i][ab][y]);
							}

							if (corrected_p < 0.05)
								sh.w("1") ;
							else
								sh.w("0") ;

							sh.nl();

						}
					}
				}
			}
	}
	catch ( ... ) {
	}
	
}
