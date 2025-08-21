#include "panel_stats.h"
#include "tools.h"
#include <vector>
#include <algorithm>
#include <assert.h>
#include <set>
#include <string>
#include <string.h> 
#include <cfloat>
#include <limits.h>
#include "xls.h"

using namespace std;

void cbc_for_demogrpahy( data_set_t& ds )
{
	int total_id_cnt[GENDERS_NUM];
	int cbc_cnt[GENDERS_NUM] ;
	int no_cbc_cnt[GENDERS_NUM] ;
	memset(total_id_cnt, 0, GENDERS_NUM * sizeof(int));
	memset(cbc_cnt, 0, GENDERS_NUM * sizeof(int));
	memset(no_cbc_cnt, 0, GENDERS_NUM * sizeof(int));

	for( demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++ ){
		int g = gender2number( it->second.gender );

		total_id_cnt[g]++;
		if( ds.cbc.find(it->first) == ds.cbc.end() ) {
			no_cbc_cnt[g]++;
		}
		else {
			cbc_cnt[g]++;
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nCBC counts for population\n" );
	WRITE_OUTPUT( "Total population: Males = %d Females = %d\n", total_id_cnt[MALE], total_id_cnt[FEMALE] );
	WRITE_OUTPUT( "Ids without CBC: Males = %d %.2f%% Females = %d %.2f%%\n",
		no_cbc_cnt[MALE], 100.0*no_cbc_cnt[MALE]/total_id_cnt[MALE],
		no_cbc_cnt[FEMALE], 100.0*no_cbc_cnt[FEMALE]/total_id_cnt[FEMALE] );
	WRITE_OUTPUT( "Ids with CBC: Males = %d %.2f%% Females = %d %.2f%%\n",
		cbc_cnt[MALE], 100.0*cbc_cnt[MALE]/total_id_cnt[MALE],
		cbc_cnt[FEMALE], 100.0*cbc_cnt[FEMALE]/total_id_cnt[FEMALE] );
	CLOSE_OUTPUT();
}

void cbc_amount_by_age( data_set_t& ds )
{
	int cbc_cnt[GENDERS_NUM] ;
	memset(cbc_cnt, 0, GENDERS_NUM * sizeof(int));
	map<int, int> cbc_cnt_by_age[GENDERS_NUM];

	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender); 
		int birth_year = ds.demography[id].byear;

		vector<date_t>& dates = it->second;
		for( vector<date_t>::iterator dit = dates.begin(); dit != dates.end(); dit++ ) {
			int cbc_year = days_since1900_2_year( *dit);
			int age = cbc_year - birth_year;
			cbc_cnt_by_age[gender][age] ++;
			cbc_cnt[gender]++;
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nCBC amount by age\n");
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		WRITE_OUTPUT("%s total count CBCs %d\n", gender_names[g], cbc_cnt[g] );
		for( int age = 0; age < 120; age ++ ) {
			WRITE_OUTPUT("%s aged %d: %d (%.2f%%) CBCs\n", 
				gender_names[g], age, cbc_cnt_by_age[g][age], 100 * (double) cbc_cnt_by_age[g][age] / cbc_cnt[g] );
		}
	}
	CLOSE_OUTPUT();
}

void cbc_amount_by_year( data_set_t& ds )
{
	int cbc_cnt[GENDERS_NUM];
	memset(cbc_cnt, 0, GENDERS_NUM * sizeof(int));
	map<int, int> cbc_cnt_by_year[GENDERS_NUM];
	map<int, set<int>> cbc_id_by_year[GENDERS_NUM];

	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender); 
		int birth_year = ds.demography[id].byear;
		
		vector<date_t>& dates = it->second;
		for( vector<date_t>::iterator it = dates.begin(); it != dates.end(); it++ ) {
			int cbc_year = days_since1900_2_year( *it );
			//int age = cbc_year - birth_year;
			//if( age >= 50 && age <= 75 ) {
				cbc_cnt_by_year[gender][cbc_year] ++;
				cbc_cnt[gender]++;
				cbc_id_by_year[gender][cbc_year].insert(id);
			//}
		}
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT( "\nCBC amount by year\n" );
#if 0
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		for( int y = 1990; y < 2013; y ++ ) {
			WRITE_OUTPUT("CBC number in year %d for %ss: %d (%.2f%%) CBCs for unique ids %d\n", 
				y, gender_names[g], cbc_cnt_by_year[g][y], 100.0*cbc_cnt_by_year[g][y]/cbc_cnt[g],
				cbc_id_by_year[g][y].size() );
		}
	}
#else
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		WRITE_OUTPUT("%s total count CBCs %d\n", gender_names[g], cbc_cnt[g] );
		for( map<int, int>::iterator it = cbc_cnt_by_year[g].begin() ; it != cbc_cnt_by_year[g].end(); it++ ) {
			WRITE_OUTPUT("CBC number in year %d for %ss: %d (%.2f%%)\n", 
				it->first, gender_names[g], it->second, 100.0*it->second/cbc_cnt[g] );
		}
	}
#endif
	CLOSE_OUTPUT()
}

void last_panel_before_date_control( data_set_t& ds )
	// exclude criteria: any cacner type
{
	
	const double EXTERNAL_FACTOR = (double)ds.params["EXTERNAL_FACTOR"] / 100;
	
	const int MAX_MONTH_BEFORE_COMPARISON_DATE = 37;
	const int TRIALS = 3;
	const int DATE_TO_COMPARE[TRIALS] = {
		ds.cbc_dates_ex.cbc_mode_year * 10000 + 1 * 100 + 12,
		ds.cbc_dates_ex.cbc_mode_year * 10000 + 6 * 100 + 4,
		ds.cbc_dates_ex.cbc_mode_year * 10000 + 12 * 100 + 25 };
	
	int DAYS_TO_COMPARE[TRIALS]; memset(DAYS_TO_COMPARE, 0, TRIALS * sizeof(int));
	double total[GENDERS_NUM]; memset(total, 0, GENDERS_NUM * sizeof(int));
	double total_valid[GENDERS_NUM]; memset(total_valid, 0, GENDERS_NUM * sizeof(int));
	int total_with_cbc[GENDERS_NUM]; memset(total_with_cbc, 0, GENDERS_NUM * sizeof(int));
	int total_with_cbc_before[GENDERS_NUM]; memset(total_with_cbc_before, 0, GENDERS_NUM * sizeof(int));
	int cbc_after_cnt[GENDERS_NUM]; memset(cbc_after_cnt, 0, GENDERS_NUM * sizeof(int));
	double no_cbc_cnt[GENDERS_NUM]; memset(no_cbc_cnt, 0, GENDERS_NUM * sizeof(int));
	int time_before[GENDERS_NUM][MAX_MONTH_BEFORE_COMPARISON_DATE]; memset(time_before, 0, GENDERS_NUM * MAX_MONTH_BEFORE_COMPARISON_DATE * sizeof(int));
	int time_before_cumulative[GENDERS_NUM][MAX_MONTH_BEFORE_COMPARISON_DATE]; memset(time_before_cumulative, 0, GENDERS_NUM * MAX_MONTH_BEFORE_COMPARISON_DATE * sizeof(int));

	// find min & max cbc dates

	
	//int n_dates = ds.cbc_dates_ex.dates.begin()->second.size();
	//printf("=========  n_dates %i\n",n_dates);
	//getchar();

	int min_date = ds.cbc_dates_ex.dates.begin()->second.front();
	int max_date = ds.cbc_dates_ex.dates.begin()->second.front();
	for( cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++ ) {
		// id_type id = it->first;
		std::vector<date_t> dates = it->second;
		if( min_date > dates.front() ) {
			min_date = dates.front();
		}
		if( max_date < dates.back() ) {
			max_date = dates.back();
		}
	}
	
	// make sure check dates are within valid dates (this is less relevant when using mode date)
	for( int i = 0; i < TRIALS; i++ ) {
		DAYS_TO_COMPARE[i] = get_days( DATE_TO_COMPARE[i] );
		if( DAYS_TO_COMPARE[i] < min_date || DAYS_TO_COMPARE[i] > max_date ) {
			fprintf( stderr, "*** Error: date %d in not within CBC min & max dates(%d, %d) *** \n",
				DAYS_TO_COMPARE[i], min_date, max_date);
			return;
		}
	}
	
	//map<int, int> ids;
	for( int tr = 0; tr < TRIALS; tr++ ) {
		for (demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++) {
			int id = it->first ;
			int gender = gender2number(ds.demography[id].gender);

			// exclude criteria
			if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ||
				ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() || 
				ds.registry[CANCER_TYPE_CRC_RECCURENCE].find(id) != ds.registry[CANCER_TYPE_CRC_RECCURENCE].end() ||
				ds.registry[CANCER_TYPE_NON_CRC_RECCURENCE].find(id) != ds.registry[CANCER_TYPE_NON_CRC_RECCURENCE].end() ) {
					continue;
			}

			total[gender] ++;

			if( ! is_in_censor_for_date_range( min_date, max_date, id, ds ) ) {
				continue;
			}

			total_valid[gender]++ ;

			if (ds.cbc_dates_ex.dates.find(id) == ds.cbc_dates_ex.dates.end() ) {
				no_cbc_cnt[gender]++;
				continue;
			}

			total_with_cbc[gender]++;
			
			if ( ds.cbc_dates_ex.dates[id][0] <= DAYS_TO_COMPARE[tr] ) {
				total_with_cbc_before[gender]++;
				int time = 0;
				for (unsigned int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
					if (ds.cbc_dates_ex.dates[id][i] > DAYS_TO_COMPARE[tr]) break ;
					time = DAYS_TO_COMPARE[tr] - ds.cbc_dates_ex.dates[id][i] ;
				}

				int nmonths = (int) time/30;
				if (nmonths >= MAX_MONTH_BEFORE_COMPARISON_DATE) {
					nmonths = MAX_MONTH_BEFORE_COMPARISON_DATE - 1;
				}

				//if( nmonths == 0 && gender == 0 ) ids[id] = 1;

				time_before[gender][nmonths]++ ;
				
			} else {
				cbc_after_cnt[gender]++;
			}
				
			
			
		}
		printf(" total_with_cbc_before for date %d : M = %d F = %d\n", DATE_TO_COMPARE[tr], total_with_cbc_before[MALE], total_with_cbc_before[FEMALE] );
	}

	// find mean of all trials
	for( int g = MALE; g<GENDERS_NUM; g++ ) {
		for( int t = 0; t < MAX_MONTH_BEFORE_COMPARISON_DATE; t++ ) {
			time_before[g][t] /= TRIALS ;
		}
		cbc_after_cnt[g] /= TRIALS;
		no_cbc_cnt[g]  /= TRIALS;
		no_cbc_cnt[g]  *= EXTERNAL_FACTOR;
		total[g] /= TRIALS;
		total[g] *= EXTERNAL_FACTOR;
		total_valid[g] /= TRIALS;
		total_valid[g] *= EXTERNAL_FACTOR ;
		total_with_cbc[g] /= TRIALS;
		total_with_cbc_before[g] /= TRIALS;


	}

	// cumulative values
	for (int g=MALE; g<GENDERS_NUM; g++) {
		time_before_cumulative[g][0] = time_before[g][0];
		for (int time=1; time < MAX_MONTH_BEFORE_COMPARISON_DATE; time++) {
			time_before_cumulative[g][time] = time_before_cumulative[g][time-1] + time_before[g][time];
		}
	}

	OPEN_OUTPUT();
	for (int g=MALE; g<GENDERS_NUM; g++) {
		WRITE_OUTPUT("\nHistogram of time from last panel to random date %s\n", gender_names[g]);
		for( int t = 0; t < TRIALS; t++ ) {
			WRITE_OUTPUT("DATE_TO_COMPARE[%d]=%d\n", t, DATE_TO_COMPARE[t] );
		}
		WRITE_OUTPUT("total ids= %.0f, total valid ids = %.0f, total ids with cbc = %d, total ids with cbc before date = %d\n",
			total[g], total_valid[g], total_with_cbc[g], total_with_cbc_before[g] );
		int time = 0;
		for (time=0; time < MAX_MONTH_BEFORE_COMPARISON_DATE - 1; time++) {
			WRITE_OUTPUT("%d months\t%d\t%.2f%%\t%.2f%%\t%.2f%%\t%.2f%%\t%.2f%%\t%.2f%%\n", 
				time,
				time_before[g][time],
				(100.0*time_before[g][time])/total[g],
				(100.0*time_before_cumulative[g][time])/total[g],
				(100.0*time_before[g][time])/total_with_cbc[g],
				(100.0*time_before_cumulative[g][time])/total_with_cbc[g],
				(100.0*time_before[g][time])/total_with_cbc_before[g],
				(100.0*time_before_cumulative[g][time])/total_with_cbc_before[g]);
				
		}
		assert( time == MAX_MONTH_BEFORE_COMPARISON_DATE - 1 );
		WRITE_OUTPUT("%d+ months\t%d\t%.2f%%\t%.2f%%\t%.2f%%\t%.2f%%\t%.2f%%\t%.2f%%\n",
			time,
			time_before[g][time],
			(100.0*time_before[g][time])/total[g],
			(100.0*time_before_cumulative[g][time])/total[g],
			(100.0*time_before[g][time])/total_with_cbc[g],
			(100.0*time_before_cumulative[g][time])/total_with_cbc[g],
			(100.0*time_before[g][time])/total_with_cbc_before[g],
			(100.0*time_before_cumulative[g][time])/total_with_cbc_before[g]);
		WRITE_OUTPUT("CBC after date\t%d\t%.2f%%\t%.2f%%\t%.2f%%\t%.2f%%\n",
			cbc_after_cnt[g],
			100.0*cbc_after_cnt[g]/total[g],
			100.0*(cbc_after_cnt[g]+time_before_cumulative[g][time])/total[g],
			100.0*cbc_after_cnt[g]/total_with_cbc[g],
			100.0*(cbc_after_cnt[g]+time_before_cumulative[g][time])/total_with_cbc[g]);
		WRITE_OUTPUT("NO CBC found\t%.0f\t%.2f%%\t%.2f%%\n",
			no_cbc_cnt[g],
			100.0*no_cbc_cnt[g]/total[g],
			100.0*(no_cbc_cnt[g]+cbc_after_cnt[g]+time_before_cumulative[g][time])/total[g]);
	}
	CLOSE_OUTPUT();
	
	// write output to xls
	try {
		xls_sheet_t s( "Last Panel Before Date for ctrl" );
		s.w( "Date 1" ); s.w( DATE_TO_COMPARE[0] ); s.nl();
		s.w( "Date 2" ); s.w( DATE_TO_COMPARE[1] ); s.nl();
		s.w( "Date 3" ); s.w( DATE_TO_COMPARE[2] ); s.nl();

		s.w( "" ); s.w( "Males" ); s.w( "Females" ); s.nl();
		s.w( "Total Ids" ); s.w( total[MALE] ); s.w( total[FEMALE] ); s.nl();
		s.w( "Total Valid Ids" ); s.w( total_valid[MALE] ); s.w( total_valid[FEMALE] ); s.nl();
		s.w( "Total Ids with cbc" ); s.w( total_with_cbc[MALE] ); s.w( total_with_cbc[FEMALE] ); s.nl();
		s.w( "Total Ids with cbc before date" ); s.w( total_with_cbc_before[MALE] ); s.w( total_with_cbc_before[FEMALE] ); s.nl();

		s.w( "Time(month)" ); s.nl();
		int max_time = MAX_MONTH_BEFORE_COMPARISON_DATE - 1;
		for (int time=0; time < max_time; time++) {
			s.w( time ); s.w( time_before[MALE][time] ); s.w( time_before[FEMALE][time] ); s.nl();
		}
		char label[MAX_STRING_LEN];
		snprintf( label, sizeof(label), "more than %d", max_time );
		s.w( label ); s.w( time_before[MALE][max_time] ); s.w( time_before[FEMALE][max_time] ); s.nl();

		s.w( "CBC after date" ); s.w( cbc_after_cnt[MALE] ); s.w( cbc_after_cnt[FEMALE] ); s.nl();
		s.w( "No CBC" ); s.w( no_cbc_cnt[MALE] ); s.w( no_cbc_cnt[FEMALE] ); s.nl();
	}
	catch (...) {

	}
}

void last_panel_before_crc_onset( data_set_t& ds )
{
	const int max_month_before_registry = 13;

	int total[GENDERS_NUM]; memset(total, 0, GENDERS_NUM * sizeof(int));
	int total_with_cbc_before [GENDERS_NUM]; memset(total_with_cbc_before, 0, GENDERS_NUM * sizeof(int));
	int total_with_cbc_after_only [GENDERS_NUM]; memset(total_with_cbc_after_only, 0, GENDERS_NUM * sizeof(int));
	int time_before_registry [GENDERS_NUM][max_month_before_registry]; memset(time_before_registry, 0, GENDERS_NUM * max_month_before_registry * sizeof(int));

	map<vector<int>,int> panel_counts[GENDERS_NUM] ;

	for (int g=MALE; g<GENDERS_NUM; g++) 
		for (int d=0; d<=1; d++)
			for (int c=0; c<=1; c++)
				for (int b=0; b<=1; b++)
					for (int a=0; a<=1; a++)
					{
						vector<int> temp_panel(4,0) ;
						temp_panel[0]=a;
						temp_panel[1]=b;
						temp_panel[2]=c;
						temp_panel[3]=d;
						panel_counts[g][temp_panel]=0;
					}

	for (cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin(); it != ds.registry[CANCER_TYPE_CRC].end(); it++) 
	{
		int id = it->first ;
		int gender = gender2number(ds.demography[id].gender);
		vector<int> panel(4,0) ;


		total[gender]++ ;

		if (ds.cbc_dates_ex.dates.find(id) != ds.cbc_dates_ex.dates.end()) 
		{
			if (ds.cbc_dates_ex.dates[id][0] < it->second.days_since_1900) 
			{
					int time = 0;
					for (unsigned int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
						if (ds.cbc_dates_ex.dates[id][i] >= it->second.days_since_1900) break ;
						time = it->second.days_since_1900 - ds.cbc_dates_ex.dates[id][i] ;

						int temp_month = (int) (1 + time/90) ;

						if (temp_month>=0 && temp_month<=1) panel[0]=1;
						else if (temp_month>1 && temp_month<=2) panel[1]=1;
						else if (temp_month>2 && temp_month<=4) panel[2]=1;
						else if (temp_month>=5 && temp_month<=12) panel[3]=1;
					}
		
					int nmonths = (int) (1 + time/90) ;

					if (nmonths >= max_month_before_registry) {
						nmonths = max_month_before_registry - 1;
					}

					
	
					time_before_registry[gender][nmonths-1]++ ;
					total_with_cbc_before[gender]++ ;
			}
			else
			{
					total_with_cbc_after_only[gender]++ ;
			}
		}

		panel_counts[gender][panel] ++ ;

	}

	OPEN_OUTPUT();
	for (int g=MALE; g<GENDERS_NUM; g++) {
		WRITE_OUTPUT("Histogram of time from last panel to registry for %s\n", gender_names[g]);
		WRITE_OUTPUT("total %i\n", total[g]);
		WRITE_OUTPUT("total_with_cbc_before %i\n", total_with_cbc_before[g]);
		WRITE_OUTPUT("total_with_cbc_after_only %i\n", total_with_cbc_after_only[g]);

		for (int time=1; time < max_month_before_registry - 1; time++) {
			printf("%d months\t%d\t%.2f\n", 
				time, time_before_registry[g][time-1],
				(100.0*time_before_registry[g][time-1])/total[g]) ;
		}


		WRITE_OUTPUT("%d months and more\t%d\t%.2f\n\n",
			max_month_before_registry-1,
			time_before_registry[g][max_month_before_registry-1],
			(100.0*time_before_registry[g][max_month_before_registry-1])/total[g]) ;


		for (map<vector<int>,int>::iterator it = panel_counts[g].begin(); it != panel_counts[g].end(); it++) 
		{
			//printf("%i%i%i%i\t%i\n", it->first[0] , it->first[1], it->first[2] , it->first[3] , it->second);
			WRITE_OUTPUT("%i%i%i%i\t%i\n", it->first[0] , it->first[1], it->first[2] , it->first[3] , it->second);
		}

	}
	CLOSE_OUTPUT();

	try {
		xls_sheet_t s("Last Panel Before CRC");
		s.w( "" ); s.w( "Male" ); s.w( "Female" ); s.nl(); 
		s.w( "Total" ); s.w( total[MALE] ); s.w( total[FEMALE] ); s.nl();
		s.w( "Total with cbc before date" ); s.w( total_with_cbc_before[MALE] ); s.w( total_with_cbc_before[FEMALE] ); s.nl();
		s.w( "Total with cbc after date" ); s.w( total_with_cbc_after_only[MALE] ); s.w( total_with_cbc_after_only[FEMALE] ); s.nl();
		s.w( "Time(month)" ); s.nl();
		for (int time=0; time < max_month_before_registry - 1; time++) {
			s.w( time ); s.w( time_before_registry[MALE][time] ); s.w( time_before_registry[FEMALE][time] ); s.nl();
		}
		char label[MAX_STRING_LEN];
		sprintf( label, "%d months and more", max_month_before_registry-1 );
		s.w( label ); s.w( time_before_registry[MALE][max_month_before_registry-1] ); s.w( time_before_registry[FEMALE][max_month_before_registry-1] ); s.nl();
	}
	catch ( ... ) {
	}

}

void panel_size_distribution( data_set_t& ds )
{
	int test_hist[GENDERS_NUM][MAX_CBC_CODE_NUM];
	memset(test_hist, 0, GENDERS_NUM*MAX_CBC_CODE_NUM * sizeof(int));
	
	for (int g=0; g<2; g++) memset(test_hist[g],0,MAX_CBC_CODE_NUM*sizeof(int)) ;

	int total[GENDERS_NUM];
	memset(total, 0, GENDERS_NUM * sizeof(int));

	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender); 
		vector<int>& dates = it->second ;
		total[gender] += (int) dates.size() ;
		for (int i=0; i<dates.size(); i++) {
			int ntests = (int) ds.cbc[id][dates[i]].size() ; 
//			assert( ntests <= CBC_MAX_CODES_NUM );
			test_hist[gender][ntests-1] ++ ;
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT("\nPanel Size distribution\n");
	for (int g=MALE; g<GENDERS_NUM; g++) {
		WRITE_OUTPUT("Distribution of panel size for %s\n",gender_names[g]) ;
		WRITE_OUTPUT("Total number of panels: %d\n", total[g]);
		for (int ntests=1; ntests<=ds.cbc_codes.codes.size(); ntests++) {
			WRITE_OUTPUT("%d Tests at Panel: %d %.2f%%\n",
				ntests,test_hist[g][ntests-1],(100.0*test_hist[g][ntests-1])/total[g]) ;
		}
		WRITE_OUTPUT("\n") ;
	}
	CLOSE_OUTPUT();

	try {
		xls_sheet_t s("Panel Size Distribution");

		s.w(""); s.w( "Males" ); s.w( "Females" ); s.nl(); 
		s.w( "# of tests" ); s.nl();
		for (int ntests=1; ntests<=ds.cbc_codes.codes.size(); ntests++) {
			s.w( ntests ); s.w( test_hist[MALE][ntests-1] ); s.w( test_hist[FEMALE][ntests-1] ); s.nl();
		}
		s.w( "Total" ); s.w( total[MALE] ); s.w( total[FEMALE] ); s.nl();
		
	}
	catch ( ... ) {
	}

}

void panel_type_distribution( data_set_t& ds )
{
	map<vector<int>,int> panel_counts ;
	int total_counts = 0 ;
	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		vector<int>& dates = it->second;
		for (int i=0; i<dates.size(); i++) {
			vector<int> panel(ds.cbc_codes.codes.size(),0) ;
			for (map<int,double>::iterator cit = ds.cbc[id][dates[i]].begin();
				cit != ds.cbc[id][dates[i]].end(); cit++) {
				assert(ds.cbc_codes.codes.find(cit->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[cit->first].serial_num ;
				panel[idx] = 1 ;
			}
			panel_counts[panel] ++ ;
			total_counts ++ ;
		}
	}

	vector< pair<vector<int>,int> > p_counts ;
	for (map<vector<int>,int>::iterator it=panel_counts.begin(); it!=panel_counts.end(); it++) {
		vector<int> temp = it->first ;
		int num = it->second ;
		pair<vector<int>,int> count(temp,num) ;
		p_counts.push_back(count) ;
	}

	sort(p_counts.begin(),p_counts.end(),panel_compare()) ;

	OPEN_OUTPUT()
	WRITE_OUTPUT("Histogram of panel types\n") ;
	for (vector<pair<vector<int>,int> >::iterator it=p_counts.begin(); it!=p_counts.end(); it++) {
		double perc = 100 * (it->second+0.0)/total_counts ;
		if (perc > 0.1) {
			WRITE_OUTPUT("Panel ");
			for (int i=0; i<ds.cbc_codes.codes.size(); i++) {
				WRITE_OUTPUT("%d",(it->first)[i]) ;
			}
			WRITE_OUTPUT(" Appears %d times - %.1f%%\n",it->second,perc) ;
		}
	}
	WRITE_OUTPUT("\n") ;
	CLOSE_OUTPUT();
}

void cbc_code_in_panel_distribution( data_set_t& ds )
{
	int panel_cnt = 0;
	vector<int> cbc_code_in_panel_cnt(ds.cbc_codes.codes.size(),0) ;
	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		vector<int>& dates = it->second;
		for (int i=0; i<dates.size(); i++) {
			panel_cnt++;
			for (map<int,double>::iterator cit = ds.cbc[id][dates[i]].begin();
				cit != ds.cbc[id][dates[i]].end(); cit++) {
				assert(ds.cbc_codes.codes.find(cit->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[cit->first].serial_num ;
				cbc_code_in_panel_cnt[idx] ++ ;
			}
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT("\nCBC codes distribution\n");
	WRITE_OUTPUT("Total number of panels: %d\n", panel_cnt);
	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin();
		it != ds.cbc_codes.codes.end(); it++ ) {
			int idx = it->second.serial_num;
			WRITE_OUTPUT("CBC code %d %s: appears %d times %.2f%%\n",
				it->first, it->second.name.c_str(), cbc_code_in_panel_cnt[idx],
				100.0*cbc_code_in_panel_cnt[idx] / panel_cnt);
	}
	CLOSE_OUTPUT();

	// Writing to XLS
	try {
		xls_sheet_t s("CBC Code Distribution");
		s.w("Total # of Panels"); s.w(panel_cnt); s.nl();
		s.w("Code #");s.w("Code Name");s.w("Appearance #"); s.w("Appearance %"); s.nl();
		for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin();
			it != ds.cbc_codes.codes.end(); it++ ) {
				int idx = it->second.serial_num;
				s.w(it->first);
				s.w(it->second.name.c_str() ); 
				s.w(cbc_code_in_panel_cnt[idx]); 
				s.w(100.0*cbc_code_in_panel_cnt[idx] / panel_cnt);
				s.nl();
		}
	}
	catch ( ... ) {
	}

}

void cbc_code_in_panel_redflag( data_set_t& ds )
{
	int panel_cnt = 0;
	vector<int> cbc_code_in_panel_cnt(ds.cbc_codes.codes.size(),0) ;
	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		vector<int>& dates = it->second;
		for (int i=0; i<dates.size(); i++) {
			panel_cnt++;
			for (map<int,double>::iterator cit = ds.cbc[id][dates[i]].begin();
				cit != ds.cbc[id][dates[i]].end(); cit++) {
				assert(ds.cbc_codes.codes.find(cit->first) != ds.cbc_codes.codes.end()) ;
				int idx = ds.cbc_codes.codes[cit->first].serial_num ;
				cbc_code_in_panel_cnt[idx] ++ ;
			}
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT("\nCBC codes distribution\n");
	WRITE_OUTPUT("Total number of panels: %d\n", panel_cnt);
	for( map<cbc_code_id_type , cbc_code_t>::iterator it = ds.cbc_codes.codes.begin();
		it != ds.cbc_codes.codes.end(); it++ ) {
			int idx = it->second.serial_num;
			int red_flag = 100 * cbc_code_in_panel_cnt[idx] / panel_cnt;
			if( red_flag <= it->second.red_flag ) {
				WRITE_OUTPUT("%s CBC code %d %s: appears %d times %.2f%%\n",RED_FLAG_MARKER,
					it->first, it->second.name.c_str(), cbc_code_in_panel_cnt[idx],
					100.0*cbc_code_in_panel_cnt[idx] / panel_cnt);
			}
	}
	CLOSE_OUTPUT();
}

void check_panel_subsets( data_set_t& ds )
{
	int total_panel_cnt = 0;
	int panel_a_cnt = 0;
	int panel_a_plt_cnt = 0;
	int panel_b_cnt = 0;
	int panel_b_plt_cnt = 0;
	int panel_a_and_b_cnt = 0;
	int panel_a_and_b_plt_cnt = 0;

	const cbc_code_id_type RBC_CODE = ds.cbc_codes.code_name_to_code_id["RBC"];
	const cbc_code_id_type HGB_CODE = ds.cbc_codes.code_name_to_code_id["HGB"];
	const cbc_code_id_type HCT_CODE = ds.cbc_codes.code_name_to_code_id["HCT"];
	const cbc_code_id_type MCH_CODE = ds.cbc_codes.code_name_to_code_id["MCH"];
	const cbc_code_id_type MCHC_CODE = ds.cbc_codes.code_name_to_code_id["MCHC_M"];
	const cbc_code_id_type PLT_CODE = ds.cbc_codes.code_name_to_code_id["PLT"];

	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		vector<int>& dates = it->second;
		
		for (int i=0; i<dates.size(); i++) {
			total_panel_cnt++;

			if( ds.cbc[id][dates[i]].find( RBC_CODE ) != ds.cbc[id][dates[i]].end() &&
				ds.cbc[id][dates[i]].find( HCT_CODE ) != ds.cbc[id][dates[i]].end() &&
				ds.cbc[id][dates[i]].find( MCH_CODE ) != ds.cbc[id][dates[i]].end() ) {
					panel_a_cnt++;
					if( ds.cbc[id][dates[i]].find( PLT_CODE ) != ds.cbc[id][dates[i]].end() ) {
						panel_a_plt_cnt++;
					}
			}

			if( ds.cbc[id][dates[i]].find( HGB_CODE ) != ds.cbc[id][dates[i]].end() &&
				ds.cbc[id][dates[i]].find( HCT_CODE ) != ds.cbc[id][dates[i]].end() &&
				ds.cbc[id][dates[i]].find( MCHC_CODE ) != ds.cbc[id][dates[i]].end() ) {
					panel_b_cnt++;
					if( ds.cbc[id][dates[i]].find( PLT_CODE ) != ds.cbc[id][dates[i]].end() ) {
						panel_b_plt_cnt++;
					}
			}

			if( ds.cbc[id][dates[i]].find( RBC_CODE ) != ds.cbc[id][dates[i]].end() &&
				ds.cbc[id][dates[i]].find( HGB_CODE ) != ds.cbc[id][dates[i]].end() &&
				ds.cbc[id][dates[i]].find( HCT_CODE ) != ds.cbc[id][dates[i]].end() &&
				ds.cbc[id][dates[i]].find( MCH_CODE ) != ds.cbc[id][dates[i]].end() &&
				ds.cbc[id][dates[i]].find( MCHC_CODE ) != ds.cbc[id][dates[i]].end() ) {
					panel_a_and_b_cnt++;
					if( ds.cbc[id][dates[i]].find( PLT_CODE ) != ds.cbc[id][dates[i]].end() ) {
						panel_a_and_b_plt_cnt++;
					}
			}
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT("\nPanel Subsets:\n");
	WRITE_OUTPUT("Total: %d\n", total_panel_cnt );
	WRITE_OUTPUT("%s RBC, HCT, MCH\t\t\t: %d %.2f%%\n", RED_FLAG_MARKER, panel_a_cnt, 100.0*panel_a_cnt/total_panel_cnt );
	WRITE_OUTPUT("%s HGB, HCT, MCHC_M\t\t: %d %.2f%%\n", RED_FLAG_MARKER, panel_b_cnt, 100.0*panel_b_cnt/total_panel_cnt );
	WRITE_OUTPUT("%s RBC, HGB, HCT, MCH, MCHC_M\t: %d %.2f%%\n", RED_FLAG_MARKER, panel_a_and_b_cnt, 100.0*panel_a_and_b_cnt/total_panel_cnt );
	WRITE_OUTPUT("%s RBC, HCT, MCH, PLT\t\t: %d %.2f%%\n", RED_FLAG_MARKER, panel_a_plt_cnt, 100.0*panel_a_plt_cnt/total_panel_cnt );
	WRITE_OUTPUT("%s HGB, HCT, MCHC_M, PLT\t\t: %d %.2f%%\n", RED_FLAG_MARKER, panel_b_plt_cnt, 100.0*panel_b_plt_cnt/total_panel_cnt );
	WRITE_OUTPUT("%s RBC, HGB, HCT, MCH, MCHC_M, PLT\t: %d %.2f%%\n", RED_FLAG_MARKER, panel_a_and_b_plt_cnt, 100.0*panel_a_and_b_plt_cnt/total_panel_cnt );
	CLOSE_OUTPUT();

}

void panel_number_distribution_for_healthy( data_set_t& ds )
{
	// Mark Good Subjects (available in realted period)
	int min_day = get_days( ds.params["CBC_FIRST_DATE"] );
	int max_day = get_days( ds.params["CBC_LAST_DATE"] );

	map<id_type,int> good_subject ;
	int ngood = 0, ntotal = 0 ;
	for (censor_t::iterator it = ds.censor.begin(); it != ds.censor.end(); it++) {
		id_type id = it->first ;
		int stat = it->second.stat ;
		int date = it->second.date ;
		
		ntotal ++ ;
		if (stat == 1 && date < min_day) {
			good_subject[id] = 1 ;
			ngood ++ ;
		}
		if (stat == 2 && date > max_day) {
			good_subject[id] = 2 ;
			ngood ++ ;
		}
	}

	// Distribution of panels per healthy person 
	int nsubjects[GENDERS_NUM] = {0,0} ;
	int total[GENDERS_NUM] = {0,0} ;
	memset(total,0,sizeof(total)) ;

	// find all healthy subjects in kupa
	for (demography_t::iterator it=ds.demography.begin(); it != ds.demography.end(); it++) {
		int id = it->first ;
		if ( good_subject.find(id) == good_subject.end() ) {
			continue;
		}
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end()) {
			continue ;
		}

		int gender = gender2number(it->second.gender);
		nsubjects[gender]++ ;
	}

#if 0
	for (int g=MALE; g<GENDERS_NUM; g++) {
		nsubjects[g] = (int) (internal_factor[DATA_TYPE] * nsubjects[g]) ;
	}
#endif

	vector<map<int,int>> npanels(GENDERS_NUM);
	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		int gender = gender2number(ds.demography[id].gender);

		if ( good_subject.find(id) == good_subject.end() ) {
			continue ;
		}
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) {
			continue;
		}

		int ndates =  0 ;
		for (unsigned int i=0; i<it->second.size(); i++) {
			if (it->second[i] > min_day && it->second[i] < max_day) {
				ndates++ ;
			}
		}
		npanels[gender][ndates]++ ;
		total[gender]++ ;
	}
	for (int g=MALE; g<GENDERS_NUM; g++) {
		npanels[g][0] = nsubjects[g] - total[g] ;
	}

	OPEN_OUTPUT()
	for (int g=0; g<2; g++) {
		WRITE_OUTPUT("Distribution of # of panels in %d-%d for uncensored control %s\n",
			ds.params["CBC_FIRST_DATE"], ds.params["CBC_LAST_DATE"], gender_names[g]) ;

		int maxn = 0 ;
		for (map<int,int>::iterator it=npanels[g].begin(); it != npanels[g].end(); it++) {
			if (it->first > maxn)
				maxn = it->first ;
		}

		for (int n=0; n<=maxn; n++) {
			if (npanels[g].find(n) != npanels[g].end())
				WRITE_OUTPUT("%d Panels : %d %.2f\n",
				n, npanels[g][n], (100.0*npanels[g][n])/nsubjects[g]) ;
		}
		WRITE_OUTPUT("\n") ;
	}
	CLOSE_OUTPUT()
}

void time_diff_for_adjacent_panels( data_set_t& ds ) 
{
	const int MAX_TIME_DELTA = 37; // time in month

	int total[GENDERS_NUM];
	int time_delta[GENDERS_NUM][MAX_TIME_DELTA];
	memset(total, 0, GENDERS_NUM * sizeof(int));
	memset(time_delta, 0, GENDERS_NUM*MAX_TIME_DELTA * sizeof(int));
	
	for (cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++) {
		int id = it->first ;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender);
#if 0
		if ( good_subject.find(id) == good_subject.end() ) {
			continue ;
		}
		if( registry.find(id) != registry.end() ) {
			continue;
		}
#endif
		
//		assert( ds.cbc_dates[id].size() < INT_MAX );
		for (int i=1; i<ds.cbc_dates_ex.dates[id].size() ; i++) {
			int delta = ds.cbc_dates_ex.dates[id][i] - ds.cbc_dates_ex.dates[id][i-1] ;		
			int nmonths = (int) (1 + delta/30) ;
			if (nmonths > MAX_TIME_DELTA - 1) {
				nmonths = MAX_TIME_DELTA - 1;
			}
			time_delta[gender][nmonths-1]++ ;
			total[gender]++ ;
		}
	}

	OPEN_OUTPUT()
	for (int g=0; g<GENDERS_NUM; g++) {
		WRITE_OUTPUT("\nHistogram of time difference between adjacent panels for uncensored control %s\n",
			gender_names[g]) ;
		for (int time=1; time < MAX_TIME_DELTA - 1; time++) {
			printf("%d months\t%d\t%.2f\n",
				time, time_delta[g][time-1], (100.0*time_delta[g][time-1])/total[g]) ;
		}
		WRITE_OUTPUT("36 months and more\t%d\t%.2f\n\n",
			time_delta[g][36-1],(100.0*time_delta[g][36-1])/total[g]) ;
	}
	CLOSE_OUTPUT()
}

void cbc_frequency( data_set_t& ds )
{
	int invalid_cnt = 0, total_cnt = 0;

	// find first & last cbc date
//	assert( ds.cbc_dates.size() > 0);
	date_t cbc_global_first_date = ds.cbc_dates_ex.dates.begin()->second.front(); 
	date_t cbc_global_last_date = ds.cbc_dates_ex.dates.begin()->second.front();
	for(cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++ ) {
		std::vector<date_t> dates = it->second;
		if( cbc_global_first_date > dates.front() ) {
			cbc_global_first_date = dates.front();
		}
		if( cbc_global_last_date < dates.back() ) {
			cbc_global_last_date = dates.back();
		}
	}

	map<int, int> time_table[GENDERS_NUM];
	map<int, int> test_table[GENDERS_NUM];
	for(cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin(); it != ds.cbc_dates_ex.dates.end(); it++ ) {
		id_type id = it->first;
		std::vector<date_t> dates = it->second;

		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender); 
		assert( ds.censor.find(id) != ds.censor.end() );
		
		assert( dates.size() < INT_MAX );
		int number_of_tests = (int)dates.size();

		assert( number_of_tests > 0 );

		date_t cbc_first_date = dates.front();
		date_t cbc_last_date = dates.back();
		assert( cbc_first_date < cbc_last_date );

		date_t first_date = ds.censor[id].stat == 1 ? ds.censor[id].date : cbc_first_date;
		first_date = first_date < cbc_global_first_date ? cbc_global_first_date : first_date;
		
		date_t last_date = ds.censor[id].stat == 2 ? ds.censor[id].date : cbc_last_date;
		last_date = last_date > cbc_global_last_date ? cbc_global_last_date : last_date;

		int days = last_date - first_date;
		if( days < 0 ) {
			//printf( "id = %d, first = %d, last = %d, tests %d censor stat %d date %d cbc first %d last %d\n",
			//	id, first_date, last_date, number_of_tests, ds.censor[id].stat, ds.censor[id].date, cbc_first_date, cbc_last_date );
			invalid_cnt++;
		} 
		else {
			int time = days / 36;
			time_table[gender][time] ++ ;
			test_table[gender][number_of_tests] ++ ;
			total_cnt++;
		}

	}

	OPEN_OUTPUT()
	WRITE_OUTPUT( "\nCBC Frequency\n" );
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		for( map<int,int>::iterator it = time_table[g].begin(); it != time_table[g].end(); it++ ) {
			WRITE_OUTPUT("%ss month %d: %d %.2f%%\n", gender_names[g], it->first, it->second, 100.0*it->second/total_cnt);
		}
		for( map<int,int>::iterator it = time_table[g].begin(); it != time_table[g].end(); it++ ) {
			WRITE_OUTPUT("%ss month %d: %d %.2f%%\n", gender_names[g], it->first, it->second, 100.0*it->second/total_cnt);
		}

	}
	CLOSE_OUTPUT()

}

void cbc_for_control_per_person_per_age( data_set_t& ds )
{
	map< int, int> total_cbc_count_per_age[GENDERS_NUM];
	map< int, int> id_count[GENDERS_NUM];
	map< int, map<int, int>> cbc_count_per_age_histogram[GENDERS_NUM];

	const int cbc_first_year = ds.params["CBC_FIRST_YEAR"];
	const int cbc_last_year = ds.params["CBC_LAST_YEAR"];

	for( demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++ ) {
		int id = it->first;
		int birth_year = it->second.byear;
		int gender = gender2number(it->second.gender);

		// censor
		// exclude criteria: if the person in censor, he should enter the HMO before cbc_first_year
		if( ds.censor.find(id) != ds.censor.end() ) {
			if( ds.censor[id].stat != 1 || ds.censor[id].reason != 1 ) {
				continue;
			}
			int date = ds.censor[id].date;
			int year = date / 10000;
			if( year > cbc_first_year ) continue; 
		}
		
		if( ds.registry[CANCER_TYPE_CRC].find(id) != ds.registry[CANCER_TYPE_CRC].end() ) continue;
		if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) continue;

		
		map< int, int> id_cbc_historgram;
		for (int i=0; i<ds.cbc_dates_ex.dates[id].size(); i++) {
			int cbc_date = ds.cbc_dates_ex.dates[id][i];
			int cbc_year = days_since1900_2_year( cbc_date );
			if( cbc_year >= cbc_first_year && cbc_year <= cbc_last_year ) {
				int age = cbc_year - birth_year;
				total_cbc_count_per_age[gender][age] ++;
				id_cbc_historgram[age] ++;
			}
		}

		for( map<int, int>::iterator it = id_cbc_historgram.begin(); it != id_cbc_historgram.end(); it++ ) {
			cbc_count_per_age_histogram[gender][it->first][it->second]++;
		}

		for( int year = cbc_first_year; year <= cbc_last_year; year++ ) {
			int age = year - birth_year;
			id_count[gender][age] ++;
		}
	}

	const int min_age = ds.params["MIN_AGE_FOR_DISTRIBUTION"];
	const int max_age = ds.params["MAX_AGE_FOR_DISTRIBUTION"];

	OPEN_OUTPUT()
	WRITE_OUTPUT("\nCBC Per person years (CBC first year %d, CBC last year %d)\n", cbc_first_year, cbc_last_year);
	for( int g = 0; g < GENDERS_NUM; g++ ) {
		for( int age = min_age; age < max_age; age++ ) {
			double q = ( id_count[g][age] == 0 )  ? 0 : (double)total_cbc_count_per_age[g][age]/id_count[g][age] ;
			WRITE_OUTPUT( "%ss aged %d: cbc = %d, id = %d, cbc per person years = %.2f\n",
				gender_names[g] ,age, total_cbc_count_per_age[g][age], id_count[g][age], q );
		}
#if 0
		for( map< int, map<int, int>>::iterator it1 = cbc_count_per_age_histogram[g].begin();
			it1 != cbc_count_per_age_histogram[g].end(); it1++ ) {
				for( map<int, int>:: iterator it2 = cbc_count_per_age_histogram[g][it1->first].begin();
					it2 != cbc_count_per_age_histogram[g][it1->first].end(); it2++ ) {
						WRITE_OUTPUT("%ss aged %d cout %d = %d\n", gender_names[g], it1->first, it2->first, it2->second );
				}
		}
#endif
	}
	CLOSE_OUTPUT()
}