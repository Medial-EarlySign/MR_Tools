#include "registry_stats.h"
#include "tools.h"
#include <assert.h>
#include <algorithm>
#include <string>
#include "xls.h"
#include <string.h>

using namespace std;

void crc_total_count( data_set_t& ds )
{
	const int REGISTRY_FIRST_YEAR = ds.params["REGISTRY_FIRST_YEAR"];
	const int REGISTRY_LAST_YEAR = ds.params["REGISTRY_LAST_YEAR"];

	cancer_type_t cancer_type [] = {CANCER_TYPE_CRC,CANCER_TYPE_COLON,CANCER_TYPE_RECTUM};
	string cancer_type_desc [] = {"CANCER_TYPE_CRC","CANCER_TYPE_COLON","CANCER_TYPE_RECTUM"};

	try {
		OPEN_OUTPUT();
		xls_sheet_t s("CRC Total counts");
		s.w( "Cancer type" ); s.w( "Gender" ); s.w( "Total" ); s.w( "Valid" ); s.w( "Censor" ); s.w( "With blood count" ); s.nl();

		for (int ct=0; ct<3; ct++) {
			int cnts_total[GENDERS_NUM]; memset(cnts_total, 0, GENDERS_NUM * sizeof(int));
			int cnts_valid[GENDERS_NUM]; memset(cnts_valid, 0, GENDERS_NUM * sizeof(int));
			int cnts_censor[GENDERS_NUM]; memset(cnts_censor, 0, GENDERS_NUM * sizeof(int));
			int cnts_blood[GENDERS_NUM]; memset(cnts_blood, 0, GENDERS_NUM * sizeof(int));

			for (cancer_specific_type_registry_t::iterator it = ds.registry[cancer_type[ct]].begin();it != ds.registry[cancer_type[ct]].end(); it++) {
				int id = it->first ;
				assert(ds.demography.find(id) != ds.demography.end());
				int gender = (ds.demography[id].gender == 'M') ? 0 : 1 ;
				int onset_year = days_since1900_2_year(it->second.days_since_1900);

				int onset_day = it->second.days_since_1900;
				cnts_total[gender] ++ ;

				if (onset_year>=REGISTRY_FIRST_YEAR &&  onset_year<=REGISTRY_LAST_YEAR) {
					cnts_valid[gender] ++ ;

					if( is_in_censor_for_year( onset_year, id, ds ) ) {
						cnts_censor[gender] ++ ;
					}

					int size=0;
					if (ds.cbc_dates_ex.dates.find(id) != ds.cbc_dates_ex.dates.end() )
						size = (int) ds.cbc_dates_ex.dates[id].size();


					if( size > 0 ) {
						int date = ds.cbc_dates_ex.dates[id].front();
						if (date<onset_day) {
							cnts_blood[gender] ++ ;
						}
					}
				}			
			}

			WRITE_OUTPUT( "\nCRC total count\n" );
			WRITE_OUTPUT("\tgender\tcancer_type\t\ttotal\tvalid\tcensor\twith_blood\n");
			for (int g=MALE; g<GENDERS_NUM; g++) {
				WRITE_OUTPUT("\t%s\t%s\t%d\t%d\t%d\t%d\n",
					gender_names[g], cancer_type_desc[ct].c_str() , cnts_total[g], cnts_valid[g] , cnts_censor[g], cnts_blood[g] );
			}
			
			for (int g=MALE; g<GENDERS_NUM; g++) {
				s.w( cancer_type_desc[ct].c_str() );
				s.w( gender_names[g] );
				s.w( cnts_total[g] ); 
				s.w( cnts_valid[g] ); 
				s.w( cnts_censor[g] ); 
				s.w( cnts_blood[g] ); 
				s.nl();
			}
			
		}

		CLOSE_OUTPUT();
	}
	catch ( ... ) {
	}

}

void crc_count_by_year( data_set_t& ds )
{
	
	OPEN_OUTPUT()

	cancer_type_t cancer_type [] = {CANCER_TYPE_CRC,CANCER_TYPE_COLON,CANCER_TYPE_RECTUM};
	string cancer_type_desc [] = {"CANCER_TYPE_CRC","CANCER_TYPE_COLON","CANCER_TYPE_RECTUM"};

	for (int i=0; i<3; i++)
	{
		
		map<int, int> cnts[GENDERS_NUM];

		for (cancer_specific_type_registry_t::iterator it = ds.registry[cancer_type[i]].begin(); it != ds.registry[cancer_type[i]].end(); it++) {
			int id = it->first ;
			assert(ds.demography.find(id) != ds.demography.end());
			int gender = gender2number(ds.demography[id].gender);
			int year = days_since1900_2_year(it->second.days_since_1900);
			cnts[gender][year] ++ ;
		}

		
		WRITE_OUTPUT( "\nCRC count by year\n" );
		for (int g=MALE; g<GENDERS_NUM; g++) {
			for( map<int,int>::iterator it = cnts[g].begin(); it != cnts[g].end(); it++ ) {
				WRITE_OUTPUT("%ss in %d: %d %s cases\n",
					gender_names[g], it->first, it->second , cancer_type_desc[i].c_str() ) ;
			}
		}
		
	}

	CLOSE_OUTPUT()


}

void crc_count_by_age( data_set_t& ds )
{
	
	const int REGISTRY_FIRST_YEAR = ds.params["REGISTRY_FIRST_YEAR"];
	const int REGISTRY_LAST_YEAR = ds.params["REGISTRY_LAST_YEAR"];

	int crc_cnts_total[GENDERS_NUM]; memset(crc_cnts_total, 0, GENDERS_NUM * sizeof(int));
	int crc_cnts_by_age[GENDERS_NUM][MAX_AGE]; memset(crc_cnts_by_age, 0, GENDERS_NUM * MAX_AGE * sizeof(int));
	for (cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin();
		it != ds.registry[CANCER_TYPE_CRC].end(); it++) {
		int id = it->first ;
		assert(ds.demography.find(id) != ds.demography.end());
		int gender = gender2number(ds.demography[id].gender);
		int age = days_since1900_2_year(it->second.days_since_1900) - ds.demography[id].byear;
		int onset_year = days_since1900_2_year(it->second.days_since_1900);
		assert(age>=0);
		assert(age<MAX_AGE);
		assert(gender<GENDERS_NUM);
		
		if (onset_year>=REGISTRY_FIRST_YEAR &&  onset_year<=REGISTRY_LAST_YEAR) {
			if( is_in_censor_for_year( onset_year, id, ds ) ) {
				crc_cnts_total[gender] ++ ;
				crc_cnts_by_age[gender][age] ++ ;
			}
		}
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT( "\nCRC count by age\n" );
	for (int g=MALE; g<GENDERS_NUM; g++) {
		for( int age=MIN_AGE; age<MAX_AGE; age++ ) {
			WRITE_OUTPUT("%ss aged %d: %d CRC cases ( %.2f )\n",
				gender_names[g], age, crc_cnts_by_age[g][age], 100.0*crc_cnts_by_age[g][age]/crc_cnts_total[g]) ;
		}
	}
	CLOSE_OUTPUT()
}

age_bin_t crc_age_distribution_bin( data_set_t& ds , int V_CANCER_TYPE )
{
	
	cancer_type_t cancer_type [] = {CANCER_TYPE_CRC,CANCER_TYPE_COLON,CANCER_TYPE_RECTUM};
	
	const int min_age_for_distribution = ds.params["MIN_AGE_FOR_DISTRIBUTION"];
	const int max_age_for_distribution = ds.params["MAX_AGE_FOR_DISTRIBUTION"];
	const int REGISTRY_FIRST_YEAR = ds.params["REGISTRY_FIRST_YEAR"];
	const int REGISTRY_LAST_YEAR = ds.params["REGISTRY_LAST_YEAR"];

	age_bin_t bin(AGE_BIN_SIZE, min_age_for_distribution, ds.source);
	
	for (cancer_specific_type_registry_t::iterator it = ds.registry[cancer_type[V_CANCER_TYPE]].begin();
		it != ds.registry[cancer_type[V_CANCER_TYPE]].end(); it++) {
		int id = it->first ;
		
		assert(ds.demography.find(id) != ds.demography.end());
		int gender = gender2number(ds.demography[id].gender);
		int onset_year = days_since1900_2_year(it->second.days_since_1900);
		int age = onset_year - ds.demography[id].byear;
		if( age < min_age_for_distribution || age >= max_age_for_distribution ) {
			continue;
		}
		if (onset_year>=REGISTRY_FIRST_YEAR &&  onset_year<REGISTRY_LAST_YEAR) {

			if( is_in_censor_for_year( onset_year, id, ds ) ) {
				bin.age_bin.add( age, gender );
			}
		}
	}

	return bin;
}

void crc_age_distribution_bin_to_stdout( data_set_t& ds )
{
	

	string cancer_type_desc [] = {"CANCER_TYPE_CRC","CANCER_TYPE_COLON","CANCER_TYPE_RECTUM"};

	OPEN_OUTPUT();

	for( int c = 0; c < 3; c++ ) {
		age_bin_t bin = crc_age_distribution_bin( ds, c );
		
		WRITE_OUTPUT( "\nCRC Age distribution by bin\n" );
		WRITE_OUTPUT( "Include criteria: %s in censor\n" , cancer_type_desc[c].c_str() );
		for (int g=MALE; g<GENDERS_NUM; g++) {
			for( int b = 0; b < MAX_AGE_BIN; b++ ) {
				WRITE_OUTPUT("%ss aged %d-%d: %d %.2f CRC cases\n",
					gender_names[g], 
					b * bin.age_bin.size, (b + 1 )* bin.age_bin.size,
					bin.age_bin.data[g][b], 100.0*bin.age_bin.data[g][b]/bin.age_bin.cnt[g]) ;
			}
			WRITE_OUTPUT("%ss total %d\n", gender_names[g], bin.age_bin.cnt[g] );
		}
	}

	CLOSE_OUTPUT();
}

void crc_age_distribution_bin_to_xls( data_set_t& ds ) 
{
	string cancer_type_desc [] = {"CRC","COLON Cancer","RECTAL Cancer"};

	age_bin_t crc_bin = crc_age_distribution_bin( ds , 0 );
	age_bin_t colon_bin = crc_age_distribution_bin( ds , 1 );
	age_bin_t rectum_bin = crc_age_distribution_bin( ds , 2 );

	try {
		xls_sheet_t s("CRC Age Distribution");

		s.w(""); 
		s.w( cancer_type_desc[0] ); s.w( cancer_type_desc[0] ); 
		s.w( cancer_type_desc[1] ); s.w( cancer_type_desc[1] );
		s.w( cancer_type_desc[2] ); s.w( cancer_type_desc[2] );
		s.nl();

		s.w( "Age Group" ); 
		s.w( "N Male" ); s.w( "N Female" );
		s.w( "N Male" ); s.w( "N Female" );
		s.w( "N Male" ); s.w( "N Female" );
		s.nl();

		for( int b = 0; b < MAX_AGE_BIN; b++ ) {
			char label[MAX_STRING_LEN];
			snprintf( label, sizeof(label), "%d-%d", b * crc_bin.age_bin.size, (b + 1 )* crc_bin.age_bin.size );
			s.w(label);
			s.w( crc_bin.age_bin.data[MALE][b] ); s.w( crc_bin.age_bin.data[FEMALE][b] );
			s.w( colon_bin.age_bin.data[MALE][b] ); s.w( colon_bin.age_bin.data[FEMALE][b] );
			s.w( rectum_bin.age_bin.data[MALE][b] ); s.w( rectum_bin.age_bin.data[FEMALE][b] );
			s.nl();
		}
		s.w( "Total" );
		s.w( crc_bin.age_bin.cnt[MALE] ); s.w( crc_bin.age_bin.cnt[FEMALE] );
		s.w( colon_bin.age_bin.cnt[MALE] ); s.w( colon_bin.age_bin.cnt[FEMALE] );
		s.w( rectum_bin.age_bin.cnt[MALE] ); s.w( rectum_bin.age_bin.cnt[FEMALE] );
		s.nl();
	}
	catch( ... ) {
	}

}

void crc_age_distribution_bin_compare( data_set_t& ds, int V_CANCER_TYPE )
{
	age_bin_t bin_a = crc_age_distribution_bin( ds, V_CANCER_TYPE );
	age_bin_t bin_b = crc_age_distribution_bin( ds, V_CANCER_TYPE );
	int ret = age_bins_compare( bin_a, bin_b );
	FLAGS_OUTPUT( "\nCRC age distribution comparison = %d\n", ret );
	age_bins_print( bin_a, bin_b, std::string("CRC") );	
}

//////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////

void crc_risk_by_age( data_set_t& ds )
	// 
	// Calculation:
	//     cnt_born_sick_year[gender][birth_year][sick_year]  
	// ----------------------------------------------------------
	// cnt_born_in_censor_for_year[gender][birth_year][sick_year]
	//
{
	const int MIN_RISK_AGE = ds.params["MIN_AGE_FOR_DISTRIBUTION"];
	const int MAX_RISK_AGE = ds.params["MAX_AGE_FOR_DISTRIBUTION"];
	const double EXTERNAL_FACTOR = (double)ds.params["EXTERNAL_FACTOR"] / 100;

	map<int, map<int, double>> crc_risk_by_age_sickyear[GENDERS_NUM];
	map<int, map<int, int>> crc_sick_by_age_sickyear[GENDERS_NUM];
	map<int, map<int, double>> crc_control_by_age_sickyear[GENDERS_NUM];
	for( int gender=MALE; gender < GENDERS_NUM; gender++ ) {
		for( int age = MIN_RISK_AGE; age < MAX_RISK_AGE; age++ ) {
			for(int sick_year = ds.params["REGISTRY_FIRST_YEAR"]; sick_year <= ds.params["REGISTRY_LAST_YEAR"]; sick_year++ ) {
				int birth_year = sick_year - age;
				int nominator = ds.cnt_crc_born_sick_year[gender][birth_year][sick_year];
				double denominator = ds.cnt_born_in_censor_for_year[gender][birth_year][sick_year] * EXTERNAL_FACTOR;
				if( denominator > 0 ) {
					crc_risk_by_age_sickyear[gender][age][sick_year] = (double)nominator/ denominator ;
				}
				crc_sick_by_age_sickyear[gender][age][sick_year] = nominator;
				crc_control_by_age_sickyear[gender][age][sick_year] = denominator;
			}
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nCRC Risk by age & year (%d-%d)\n", ds.params["REGISTRY_FIRST_YEAR"], ds.params["REGISTRY_LAST_YEAR"] );
	for( int g=MALE; g<GENDERS_NUM; g++ ) {
		for( int age = MIN_RISK_AGE; age <= MAX_RISK_AGE; age++ ) {
			WRITE_OUTPUT( "%ss aged %d: ", gender_names[g], age );
			for( int year=ds.params["REGISTRY_FIRST_YEAR"]; year<ds.params["REGISTRY_LAST_YEAR"]; year++ ) {
				WRITE_OUTPUT( "%.2f%%\t%d\t%.0f\t",
					100.0*crc_risk_by_age_sickyear[g][age][year],
					crc_sick_by_age_sickyear[g][age][year],
					crc_control_by_age_sickyear[g][age][year] );
			}
			 WRITE_OUTPUT( "risk for CRC per year\n" );
		}
	}
	CLOSE_OUTPUT();

}

void crc_risk_by_age_bin( data_set_t& ds )
	// 
	// Calculation:
	//     cnt_born_sick_year[gender][birth_year][sick_year]  
	// ----------------------------------------------------------
	// cnt_born_in_censor_for_year[gender][birth_year][sick_year]
	//
{
//	assert( object_num == 0 || object_num == 1 );

	int AGE_GROUP = 1;

	const int MIN_RISK_AGE = ds.params["MIN_AGE_FOR_DISTRIBUTION"];
	const int MAX_RISK_AGE = ds.params["MAX_AGE_FOR_DISTRIBUTION"];

	const double EXTERNAL_FACTOR = (double)ds.params["EXTERNAL_FACTOR"] / 100;
	
	map<int, double> total_born_in_censor_for_age[GENDERS_NUM];
	map<int, int> total_crc_born_sick_age[GENDERS_NUM];
	map<int, int> total_colon_born_sick_age[GENDERS_NUM];
	map<int, int> total_rectum_born_sick_age[GENDERS_NUM];
	
	for( int gender=MALE; gender < GENDERS_NUM; gender++ ) {
		for( int age = MIN_RISK_AGE; age < MAX_RISK_AGE; age++ ) {
			for(int sick_year = ds.params["REGISTRY_FIRST_YEAR"]; sick_year < ds.params["REGISTRY_LAST_YEAR"]; sick_year++ ) {
				int birth_year = sick_year - age;
				total_born_in_censor_for_age[gender][age] +=
					(double)ds.cnt_born_in_censor_for_year[gender][birth_year][sick_year] * EXTERNAL_FACTOR;
				total_crc_born_sick_age[gender][age] += 
					ds.cnt_crc_born_sick_year[gender][birth_year][sick_year];
				total_colon_born_sick_age[gender][age] += 
					ds.cnt_colon_born_sick_year[gender][birth_year][sick_year];
				total_rectum_born_sick_age[gender][age] += 
					ds.cnt_rectum_born_sick_year[gender][birth_year][sick_year];
			}
		}
	}


	/*
	printf("i am here \n");//getchar();
	printf("sick_year_from %i\n" ,ds.params["REGISTRY_FIRST_YEAR"] );
	printf("sick_year_from %i\n" ,ds.params["REGISTRY_LAST_YEAR"] );

	FILE *fage =  fopen("\\\\server\\temp\\risk_matrix.txt", "w");
	for( int gender=MALE; gender < GENDERS_NUM; gender++ ) 
	{
		for( int age = MIN_RISK_AGE; age <= MAX_RISK_AGE; age++ ) 
		{
			fprintf(fage ,"%i\t%i\t%i\t%i\t%i\n", gender , age, total_crc_born_sick_age[gender][age], total_colon_born_sick_age[gender][age], total_rectum_born_sick_age[gender][age]);
		}
	}
	fclose(fage);
	*/
	//getchar();



	map<int, double> total_born_in_censor_for_age_bin[GENDERS_NUM];
	map<int, int> total_crc_born_sick_age_bin[GENDERS_NUM];
	map<int, int> total_colon_born_sick_age_bin[GENDERS_NUM];
	map<int, int> total_rectum_born_sick_age_bin[GENDERS_NUM];
	for( int gender=MALE; gender < GENDERS_NUM; gender++ ) {
		for( int age = MIN_RISK_AGE; age <= MAX_RISK_AGE; age++ ) {
			int age_bin = age / AGE_GROUP;
			total_born_in_censor_for_age_bin[gender][age_bin] += total_born_in_censor_for_age[gender][age];
			total_crc_born_sick_age_bin[gender][age_bin] += total_crc_born_sick_age[gender][age];
			total_colon_born_sick_age_bin[gender][age_bin] += total_colon_born_sick_age[gender][age];
			total_rectum_born_sick_age_bin[gender][age_bin] += total_rectum_born_sick_age[gender][age];
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT("\nCRC risk by age bin\n" );
	for( int g=MALE; g<GENDERS_NUM; g++ ) {
		for( int age_bin = MIN_RISK_AGE/AGE_GROUP; age_bin < MAX_RISK_AGE/AGE_GROUP; age_bin++ ) {
			WRITE_OUTPUT( "%s\t%d\t%d\t%d\t%.2f%%\t%d\t%.2f%%\t%d\t%.2f%%\t%.0f\n",
				gender_names[g],
				age_bin*AGE_GROUP, (age_bin+1)*AGE_GROUP,
				total_colon_born_sick_age_bin[g][age_bin], 
				100.0*total_colon_born_sick_age_bin[g][age_bin]/total_born_in_censor_for_age_bin[g][age_bin],
				total_rectum_born_sick_age_bin[g][age_bin], 
				100.0*total_rectum_born_sick_age_bin[g][age_bin]/total_born_in_censor_for_age_bin[g][age_bin],
				total_crc_born_sick_age_bin[g][age_bin], 
				100.0*total_crc_born_sick_age_bin[g][age_bin]/total_born_in_censor_for_age_bin[g][age_bin],
				total_born_in_censor_for_age_bin[g][age_bin] );
		}
	}
	CLOSE_OUTPUT();

	try {
		xls_sheet_t s("CRC Risk Age Bin");
		s.w("Age-Bin"); s.w("Gender"); 
		s.w("Colon sick #"); s.w("Colon sick Risk %");
		s.w("Rectum sick #"); s.w("Rectum sick Risk %");
		s.w("CRC sick #"); s.w("CRC sick Risk %");
		s.w("Population @ age bin");
		s.nl();
		for( int g=MALE; g<GENDERS_NUM; g++ ) {
			for( int age_bin = MIN_RISK_AGE/AGE_GROUP; age_bin < MAX_RISK_AGE/AGE_GROUP; age_bin++ ) {
				char label[MAX_STRING_LEN];
				sprintf( label, "%d-%d", age_bin*AGE_GROUP, (age_bin + 1)*AGE_GROUP );
				s.w( label );
				s.w( gender_names[g] );
				s.w( total_colon_born_sick_age_bin[g][age_bin] );
				s.w( 100.0*total_colon_born_sick_age_bin[g][age_bin]/total_born_in_censor_for_age_bin[g][age_bin] );
				s.w( total_rectum_born_sick_age_bin[g][age_bin] );
				s.w( 100.0*total_rectum_born_sick_age_bin[g][age_bin]/total_born_in_censor_for_age_bin[g][age_bin] );
				s.w( total_crc_born_sick_age_bin[g][age_bin] );
				s.w( 100.0*total_crc_born_sick_age_bin[g][age_bin]/total_born_in_censor_for_age_bin[g][age_bin] );
				s.w( total_born_in_censor_for_age_bin[g][age_bin] );
				s.nl();
			}
		}
	}
	catch ( ... ) {
	}


}

void crc_risk_and_relative_risk_by_age( data_set_t& ds )
	// 
	// Calculation:
	//     cnt_born_sick_year[gender][birth_year][sick_year]  
	// ----------------------------------------------------------
	// cnt_born_in_censor_for_year[gender][birth_year][sick_year]
	//
{
	const int MIN_RISK_AGE = ds.params["MIN_AGE_FOR_DISTRIBUTION"];
	const int MAX_RISK_AGE = ds.params["MAX_AGE_FOR_DISTRIBUTION"];
	const double EXTERNAL_FACTOR = (double)ds.params["EXTERNAL_FACTOR"] / 100;

	map<int, double> crc_risk_by_age[GENDERS_NUM];
	map<int, int> crc_risk_by_age_nominator[GENDERS_NUM];
	map<int, double> crc_risk_by_age_denominator[GENDERS_NUM];
	for( int g = MALE; g<GENDERS_NUM; g++ ) {
		for( int age = MIN_RISK_AGE; age < MAX_RISK_AGE; age++ ) {
			int nominator = 0;
			double denominator = 0;
			for(int sick_year = ds.params["REGISTRY_FIRST_YEAR"]; sick_year < ds.params["REGISTRY_LAST_YEAR"]; sick_year++ ) {
				int birth_year = sick_year - age;
				nominator += ds.cnt_crc_born_sick_year[g][birth_year][sick_year];
				denominator += (double)ds.cnt_born_in_censor_for_year[g][birth_year][sick_year] * EXTERNAL_FACTOR;
			}
			crc_risk_by_age_nominator[g][age] = nominator;
			crc_risk_by_age_denominator[g][age] = denominator;
			crc_risk_by_age[g][age] = (double)nominator / denominator;
		}
	}
	
	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nCRC Risk by age (years %d-%d)\n", 
		ds.params["REGISTRY_LAST_YEAR"], ds.params["REGISTRY_FIRST_YEAR"]  );
	for( int g=MALE; g<GENDERS_NUM; g++ ) {
		int nominator = 0;
		double denominator = 0;
		for( int age = MIN_RISK_AGE; age < MAX_RISK_AGE; age++ ) {
			nominator += crc_risk_by_age_nominator[g][age];
			denominator += crc_risk_by_age_denominator[g][age];
			WRITE_OUTPUT( "%ss aged %d: %.2f%% ( %d / %.0f ) risk for CRC\n",
				gender_names[g], age, 100*crc_risk_by_age[g][age], crc_risk_by_age_nominator[g][age], crc_risk_by_age_denominator[g][age] );
		}
		// double risk = (double)nominator / denominator;
		//printf( "*** risk for %s = %.2f%% (%d,%d)\n", gender_names[g], 100.0*risk, nominator, denominator );
	}
	
	const int MIN_AGE_FOR_RELATIVE_RISK_PIVOT = ds.params["MIN_AGE_FOR_RELATIVE_RISK_PIVOT"];
	const int MAX_AGE_FOR_RELATIVE_RISK_PIVOT = ds.params["MAX_AGE_FOR_RELATIVE_RISK_PIVOT"];
	double relative_risk_pivot[GENDERS_NUM]; memset(relative_risk_pivot, 0, GENDERS_NUM * sizeof(double));

	for( int g = MALE; g<GENDERS_NUM; g++ ) {
		int nominator = 0;
		double denominator = 0;
		for( int age = MIN_AGE_FOR_RELATIVE_RISK_PIVOT; age < MAX_AGE_FOR_RELATIVE_RISK_PIVOT; age++ ) {
			nominator += crc_risk_by_age_nominator[g][age];
			denominator += crc_risk_by_age_denominator[g][age];
		}
		relative_risk_pivot[g] = (double) nominator / denominator;
		//printf( "relative_risk_pivot[%s]= %f\n", gender_names[g], relative_risk_pivot[g] );
	}

	map<int, double> relative_risk_by_age[GENDERS_NUM];
	for( int g = MALE; g<GENDERS_NUM; g++ ) {
		for( int age = MIN_RISK_AGE; age < MAX_RISK_AGE; age++ ) {
			relative_risk_by_age[g][age] = crc_risk_by_age[g][age] / relative_risk_pivot[g];
		}
	}

	WRITE_OUTPUT( "\nRelative CRC Risk\n" );
	for( int g=MALE; g<GENDERS_NUM; g++ ) {
		for( int age = MIN_RISK_AGE; age < MAX_RISK_AGE; age++ ) {
			WRITE_OUTPUT( "%ss aged %d: %.2f Relative Risk for CRC\n",
				gender_names[g], age, relative_risk_by_age[g][age]);
		}
	}
	CLOSE_OUTPUT()

}

//////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////

void crc_risk_by_year( data_set_t& ds, int min_age, int max_age )
{

	const double EXTERNAL_FACTOR = (double)ds.params["EXTERNAL_FACTOR"] / 100;
	map<int, int> sick_in_year[GENDERS_NUM];
	map<int, double> alive_in_year[GENDERS_NUM];

	for( int gender=MALE; gender < GENDERS_NUM; gender++ ) {
		for(int sick_year = ds.params["REGISTRY_FIRST_YEAR"]; sick_year < ds.params["REGISTRY_LAST_YEAR"]; sick_year++ ) {
			for( int age = min_age; age < max_age; age++ ) {
				int birth_year = sick_year - age;
				sick_in_year[gender][sick_year] += ds.cnt_crc_born_sick_year[gender][birth_year][sick_year];
				alive_in_year[gender][sick_year] += ds.cnt_born_in_censor_for_year[gender][birth_year][sick_year] * EXTERNAL_FACTOR;
			}
		}
	}

	OPEN_OUTPUT();
	WRITE_OUTPUT( "\nCRC Risk by year for ages %d-%d\n", min_age, max_age );
	for( int g=MALE; g<GENDERS_NUM; g++ ) {
		for( int year=ds.params["REGISTRY_FIRST_YEAR"]; year<ds.params["REGISTRY_LAST_YEAR"]; year++) {
			WRITE_OUTPUT("%ss in %d: %.5f%% risk for CRC (%d sick of %.0f)\n",
				gender_names[g], year,
				100.0*sick_in_year[g][year]/alive_in_year[g][year], 
				sick_in_year[g][year], 
				alive_in_year[g][year] );
		}
	}
	CLOSE_OUTPUT();
}

void other_cancer_information( data_set_t& ds ) 
{
	const int MAX_BIN = 61;
	int total_crc_cnt[GENDERS_NUM]; memset(total_crc_cnt, 0, GENDERS_NUM * sizeof(int));
	int total_cancer_comorbidity_cnts[GENDERS_NUM]; memset(total_cancer_comorbidity_cnts, 0, GENDERS_NUM * sizeof(int));
	int before_cnts[GENDERS_NUM]; memset(before_cnts, 0, GENDERS_NUM * sizeof(int));
	int after_cnts[GENDERS_NUM]; memset(after_cnts, 0, GENDERS_NUM * sizeof(int));
	int before_bin_cnts[GENDERS_NUM][MAX_BIN]; memset(before_bin_cnts, 0, GENDERS_NUM * MAX_BIN * sizeof(int));

	for (cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin();
		it != ds.registry[CANCER_TYPE_CRC].end(); it++) {
		
			int id = it->first ;
			assert( ds.demography.find(id) != ds.demography.end() );
			int gender = gender2number(ds.demography[id].gender);

			total_crc_cnt[gender] ++;

			if( ds.registry[CANCER_TYPE_NON_CRC].find(id) != ds.registry[CANCER_TYPE_NON_CRC].end() ) {
				total_cancer_comorbidity_cnts[gender]++;
				int crc_date = it->second.days_since_1900;
				int ncrc_date = ds.registry[CANCER_TYPE_NON_CRC][id].days_since_1900;
				if( crc_date < ncrc_date ) {
					after_cnts[gender]++;
				}
				else {
					before_cnts[gender]++;
					int delta_days = crc_date - ncrc_date;
					assert( delta_days >= 0 );
					int delta_months = (int) delta_days / 30;
					if( delta_months >= MAX_BIN ) {
						delta_months = MAX_BIN - 1;
					}
					before_bin_cnts[gender][delta_months] ++;
				}
			}
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT( "\nOther cacncer information\n" );
	for (int g=MALE; g<GENDERS_NUM; g++) {
		WRITE_OUTPUT("%ss: %d (%d before, %d after) cases of cancer comorbidity (out of %d)\n",
			gender_names[g], total_cancer_comorbidity_cnts[g], before_cnts[g], after_cnts[g], total_crc_cnt[g]) ;
		for( int m = MAX_BIN - 1; m >= 0; m-- ) {
			WRITE_OUTPUT( "%ss other cancer comorbidity %d months prior to CRC: %d\n",
				gender_names[g], m, before_bin_cnts[g][m] );
		}
	}
	CLOSE_OUTPUT()
}

void crc_onset_and_health_provider_change( data_set_t& ds )
{
	const int MAX_MONTH = 61;
	int count_unknown[GENDERS_NUM]; memset(count_unknown, 0, GENDERS_NUM * sizeof(int));
	int count_after[GENDERS_NUM][MAX_MONTH]; memset(count_after, 0, GENDERS_NUM * MAX_MONTH * sizeof(int));
	int count_before[GENDERS_NUM][MAX_MONTH]; memset(count_before, 0, GENDERS_NUM * MAX_MONTH * sizeof(int));
	for (cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin();
		it != ds.registry[CANCER_TYPE_CRC].end(); it++) {
		int id = it->first;
		date_t registry_date = it->second.days_since_1900;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender);
		assert( ds.censor.find(id) != ds.censor.end() );
		date_t censor_date = ds.censor[id].date;
		int censor_stat = ds.censor[id].stat;
		if( censor_stat == 1 ) { // join 
			int delta_days = registry_date - censor_date;
			int delta_month = (int)delta_days / 30;
			if( delta_month >= 0 ) {
				if( delta_month >= MAX_MONTH ) {
					delta_month = MAX_MONTH - 1;
				}
				count_after[gender][delta_month] ++;
			}
			else {
				delta_month = -1 * delta_month;
				if( delta_month >= MAX_MONTH ) {
					delta_month = MAX_MONTH - 1;
				}
				count_before[gender][delta_month] ++;
			}
		}
		else { // we have no join date 
			count_unknown[gender] ++;
		}
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT("\nHealth provider change around onset\n");
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		for( int m = MAX_MONTH - 1; m > 0 ; m-- ) {
			WRITE_OUTPUT( "%ss who joined health service %d months before CRC: %d\n",
				gender_names[g], m, count_before[g][m] );
		}
		for( int m = 0; m < MAX_MONTH; m++ ) {
			WRITE_OUTPUT( "%ss who joined health service %d months after CRC: %d\n",
				gender_names[g], m, count_after[g][m] );
		}
		WRITE_OUTPUT( "%ss with unknown join date: %d\n\n", gender_names[g], count_unknown[g] );
	}
	CLOSE_OUTPUT()
}

void stage_distribution( data_set_t& ds )
{
	const int REGISTRY_FIRST_YEAR = ds.params["REGISTRY_FIRST_YEAR"];
	const int REGISTRY_LAST_YEAR = ds.params["REGISTRY_LAST_YEAR"];

	const int min_age = ds.params["MIN_AGE_FOR_DISTRIBUTION"];
	const int max_age = ds.params["MAX_AGE_FOR_DISTRIBUTION"];
	
	const int min_stage = 0;
	const int max_stage = 10;
	int cnt_uknonwn[GENDERS_NUM]; memset(cnt_uknonwn, 0, GENDERS_NUM * sizeof(int));
	int cnt_stages[GENDERS_NUM][max_stage]; memset(cnt_stages, 0, GENDERS_NUM * max_stage * sizeof(int));
	int cnt_total[GENDERS_NUM]; memset(cnt_total, 0, GENDERS_NUM * sizeof(int));
	for (cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin();
		it != ds.registry[CANCER_TYPE_CRC].end(); it++) {
		int id = it->first;
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number(ds.demography[id].gender);
		int birth_year = ds.demography[id].byear;
		int stage = it->second.stage;
		int onset_year = days_since1900_2_year( it->second.days_since_1900 );

		if (onset_year>=REGISTRY_FIRST_YEAR &&  onset_year<REGISTRY_LAST_YEAR) {
			int age = onset_year - birth_year;

			if (is_in_censor_for_year(onset_year , id ,ds)) {

				if( age >= min_age && age < max_age ) {
					if( stage == -1 ) {
						cnt_uknonwn[gender] ++;
					}
					else {
						cnt_stages[gender][stage] ++;
						cnt_total[gender] ++;
					}
				}
			}
		}		
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT("\nCRC Stage distribution for ages %d-%d for %s\n", min_age, max_age, ds.source.c_str() );
	for( int g=MALE; g<GENDERS_NUM; g++ ) {
		for( int s = min_stage; s < max_stage; s++ ) {
			WRITE_OUTPUT("%ss stage %d: %d (%.2f%%) cases\n", gender_names[g], s, cnt_stages[g][s],
					cnt_total[g] == 0 ? 0 : 100 * (double)cnt_stages[g][s] / cnt_total[g]); // print 0% if denominator is 0
		}
		WRITE_OUTPUT( "%ss uknown stage: %d cases\n", gender_names[g], cnt_uknonwn[g] );
	}
	CLOSE_OUTPUT()

	try {
		xls_sheet_t s("CRC Stage Distribution");
		s.w("Stage"); s.w("Male N"); s.w("Male %"); s.w("Female N"); s.w("Female %"); s.nl();
		for( int stage = min_stage; stage < max_stage; stage++ ) {
			s.w( stage );
			s.w( cnt_stages[MALE][stage] );
			s.w( cnt_total[MALE] == 0 ? 0 : 100.0 * cnt_stages[MALE][stage] / cnt_total[MALE] ); // print 0% if denominator is 0
			s.w( cnt_stages[FEMALE][stage] );
			s.w( cnt_total[FEMALE] == 0 ? 0 : 100.0 * cnt_stages[FEMALE][stage] / cnt_total[FEMALE] ); // print 0% if denominator is 0
			s.nl();
		}
		s.w( "Unknown" );
		s.w( cnt_uknonwn[MALE] ); s.w( cnt_total[MALE] == 0 ? 0 : cnt_uknonwn[MALE] / cnt_total[MALE] );
		s.w( cnt_uknonwn[MALE] ); s.w( cnt_total[FEMALE] == 0 ? 0 : cnt_uknonwn[FEMALE] / cnt_total[FEMALE] );
		s.nl();
	}
	catch ( ... ) {
	}

}

#if 0
void censor_information( data_set_t& ds )
{
	int cnt = 0;
	int join = 0;
	int sick_before_join = 0;
	int sick_after_join = 0;
	int leave = 0;
	int sick_before_leave = 0;
	int sick_after_leave = 0;
	map<int, map<int, int>> status_reason_cnt;
	for (cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin(); it != ds.registry[CANCER_TYPE_CRC].end(); it++) {
		int id = it->first ; 
		date_t sick_date = it->second.days_since_1900;
		int sick_year = days_since1900_2_year(it->second.days_since_1900);
		assert( ds.demography.find(id) != ds.demography.end() );
		int birth_year = ds.demography[id].byear;
		int gender = gender2number( ds.demography[id].gender );
		assert( ds.censor.find(id) != ds.censor.end() );
		int censor_status = ds.censor[id].stat;
		date_t censor_date = ds.censor[id].date;
		int censor_reason = ds.censor[id].reason;

		if( sick_year < 2003 ) {
			continue;
		}

		cnt++;
		switch (censor_status) {
		case 1: // join
			join++;
			if( censor_date < sick_date ) {
				sick_after_join++;
			}
			else {
				sick_before_join++;
			}
			break;
		case 2: // leave
			leave++;
			if( censor_date < sick_date ) {
				sick_after_leave++;
			}
			else {
				sick_before_leave++;
			}
			break;
		default:
			break;
		}
		status_reason_cnt[censor_status][censor_reason]++;
	}

	OPEN_OUTPUT()
	WRITE_OUTPUT( "Sick # %d\n", cnt );
	WRITE_OUTPUT( "Join # %d\n", join );
	WRITE_OUTPUT( "Sick before Join # %d\n", sick_before_join );
	WRITE_OUTPUT( "Sick after Join # %d\n", sick_after_join );
	WRITE_OUTPUT( "Leave # %d\n", leave );
	WRITE_OUTPUT( "Sick before leave # %d\n", sick_before_leave );
	WRITE_OUTPUT( "Sick after leave # %d\n", sick_after_leave );
	for( map<int, map<int,int>>::iterator it = status_reason_cnt.begin(); it != status_reason_cnt.end(); it++ ) {
		int status = it->first;
		for( map<int, int>::iterator itt = it->second.begin(); itt != it->second.end(); itt++ ) {
			int reason = itt->first;
			int value = itt->second;
			WRITE_OUTPUT( "staus %d reason %d count %d\n", status, reason, value );
		}
	}
	CLOSE_OUTPUT()
}

#endif 
void crc_moments_and_quantiles( data_set_t& ds )
{
	int n[GENDERS_NUM]; memset(n, 0, GENDERS_NUM * sizeof(int));
	double s[GENDERS_NUM]; memset(s, 0, GENDERS_NUM * sizeof(double));
	double s2[GENDERS_NUM]; memset(s2, 0, GENDERS_NUM * sizeof(double));
	vector<double> onset_ages[GENDERS_NUM];

	for (cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin();
		it != ds.registry[CANCER_TYPE_CRC].end(); it++) {

			int id = it->first ;
			assert(ds.demography.find(id) != ds.demography.end());
			int gender = gender2number(ds.demography[id].gender);
			assert(gender<GENDERS_NUM);
			//int onset_age = date2year(it->second.days_since_1900) - ds.demography[id].byear;
			double onset_age_in_days = it->second.days_since_1900 - get_days(ds.demography[id].byear * 10000 + 6 * 100 + 1);
			double onset_age_in_years = onset_age_in_days / 365;
			assert(onset_age_in_years>=0 && onset_age_in_years<MAX_AGE);

			n[gender]++;
			s[gender] += onset_age_in_years;
			s2[gender] += onset_age_in_years*onset_age_in_years;
			onset_ages[gender].push_back( onset_age_in_years );
	}
		
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		sort( onset_ages[g].begin(), onset_ages[g].end() );
	}
	
	
	OPEN_OUTPUT()
	WRITE_OUTPUT( "\nCRC Moments & Quantiles\n" );
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		if (n[g] > 0) {
			size_t size = onset_ages[g].size();
			size_t min = 0;
			size_t q1 = size / 4;
			size_t q2 = q1 * 2;
			size_t q3 = q1 * 3;
			size_t median = (size + 1) / 2;
			size_t max = size - 1;

			size_t age_50_idx = 0;
			while( onset_ages[g][age_50_idx] < 50 ) {
				age_50_idx++;
			}
			double age_50_percentile = (double)age_50_idx / size;

			size_t age_75_idx = 0;
			while( onset_ages[g][age_75_idx] < 75 ) {
				age_75_idx++;
			}
			double age_75_percentile = (double)age_75_idx / size;
			
			double mean = double(s[g])/n[g] ;
			double sdv = (n[g]==1) ? 0 : sqrt((s2[g] - mean*s[g])/(n[g] - 1)) ;
			WRITE_OUTPUT("CRC onset age for %ss: Mean = %.2f Standard-Devaition = %.2f c = %d\n",
				gender_names[g], mean, sdv, n[g] );
			WRITE_OUTPUT("CRC onset age for %ss: min = %.2f, q1 = %.2f, q2 = %.2f, median = %.2f, q3 = %.2f, max = %.2f\n",
				gender_names[g], onset_ages[g][min], onset_ages[g][q1], onset_ages[g][q2], onset_ages[g][median], onset_ages[g][q3], onset_ages[g][max] );
			WRITE_OUTPUT("CRC percentiles for %ss: age 50 = %.2f, age 75 = %.2f\n",
				gender_names[g], age_50_percentile, age_75_percentile );

		}
		else {
			WRITE_OUTPUT("CRC onset age for %s: No patients were found to calculate moments\n", gender_names[g] );
		}
	}
	CLOSE_OUTPUT()
		
}