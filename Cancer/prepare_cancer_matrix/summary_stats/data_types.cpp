#include "data_types.h"
#include <string>
#include "tools.h"
#include "cbc_stats.h"
#include "demography_stats.h"
#include <boost/math/distributions/students_t.hpp>
#include <boost/filesystem.hpp>
#include "xls.h"

using namespace std;
using namespace boost::math;

void age_bins_print_stdout( age_bin_t& bin_a, age_bin_t& bin_b )
{

	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		printf( "Gender: %s\n", gender_names[g] );
		for( int b = 0; b < MAX_AGE_BIN; b++ ) {
				if( bin_a.age_bin.data[g][b] == 0 && bin_b.age_bin.data[g][b] == 0 ) continue;
				printf( "%d-%d: %d %.2f %d %.2f\n",
					b * bin_a.age_bin.size, (b + 1 )* bin_a.age_bin.size,
					bin_a.age_bin.data[g][b], 1.0*bin_a.age_bin.data[g][b] / bin_a.age_bin.cnt[g],
					bin_b.age_bin.data[g][b], 1.0*bin_b.age_bin.data[g][b] / bin_b.age_bin.cnt[g] );
		}
	}

}

void age_bins_print_xls( age_bin_t& bin_a, age_bin_t& bin_b, const string& type )
{
	char label[MAX_STRING_LEN];

	char sheet_name[MAX_STRING_LEN] ;
	snprintf(sheet_name,sizeof(sheet_name),"%s AgeBinComparison",type.c_str()) ;
	try {
		xls_sheet_t s( sheet_name );

		s.w( "Age Bin" );
		snprintf( label, sizeof(label), "%s Males N", bin_a.source.c_str() );
		s.w( label );
		snprintf( label, sizeof(label), "%s Males %%", bin_a.source.c_str() );
		s.w( label );
		snprintf( label, sizeof(label), "%s Females N", bin_a.source.c_str() );
		s.w( label );
		snprintf( label, sizeof(label), "%s Females %%", bin_a.source.c_str() );
		s.w( label );
		snprintf( label, sizeof(label), "%s Males N", bin_b.source.c_str() );
		s.w( label );
		snprintf( label, sizeof(label), "%s Males %%", bin_b.source.c_str() );
		s.w( label );
		snprintf( label, sizeof(label), "%s Females N", bin_b.source.c_str() );
		s.w( label );
		snprintf( label, sizeof(label), "%s Females %%", bin_b.source.c_str() );
		s.w( label );
		s.nl();
		for( int b = 0; b < MAX_AGE_BIN; b++ ) {
			if( bin_a.age_bin.data[MALE][b] == 0 && bin_b.age_bin.data[MALE][b] == 0 &&
				bin_a.age_bin.data[FEMALE][b] == 0 && bin_b.age_bin.data[FEMALE][b] == 0 ) continue;
			snprintf( label, sizeof(label), "%d-%d",
				b * bin_a.age_bin.size, (b + 1 )* bin_a.age_bin.size );
			s.w( label ); 

			s.w( bin_a.age_bin.data[MALE][b] ); s.w( 1.0*bin_a.age_bin.data[MALE][b] / bin_a.age_bin.cnt[MALE] );
			s.w( bin_a.age_bin.data[FEMALE][b] ); s.w( 1.0*bin_a.age_bin.data[FEMALE][b] / bin_a.age_bin.cnt[FEMALE] );
			s.w( bin_b.age_bin.data[MALE][b] ); s.w( 1.0*bin_b.age_bin.data[MALE][b] / bin_b.age_bin.cnt[MALE] );
			s.w( bin_b.age_bin.data[FEMALE][b] ); s.w( 1.0*bin_b.age_bin.data[FEMALE][b] / bin_b.age_bin.cnt[FEMALE] );
			s.nl();
		}
	} 
	catch ( ... ) {

	}

}

void age_bins_print( age_bin_t& bin_a, age_bin_t& bin_b, const string& type )
{
	age_bins_print_stdout( bin_a, bin_b );
	age_bins_print_xls( bin_a, bin_b, type );
}

int  age_bins_compare( age_bin_t& bin_ref, age_bin_t& bin_test )
{
	// we assume that the reference age bin includes all ages, while test bin may be only subset of ages
	if ( bin_ref.age_bin.min_age > bin_test.age_bin.min_age ) {
		printf( "Error! Can NOT compare age bins:\n" );
		printf( "Minimal age for ref bin %d, Minimal age for test bin %d\n", 
			bin_ref.age_bin.min_age, bin_test.age_bin.min_age );
		return -1;
	}
	if ( bin_ref.age_bin.max_age < bin_test.age_bin.max_age ) {
		printf( "Error! Can NOT compare age bins:\n" );
		printf( "Maximal age for ref bin %d, Maximal age for test bin %d\n", 
			bin_ref.age_bin.max_age, bin_test.age_bin.max_age );
		return -2;
	}

	const int min_bin = bin_test.age_bin.min_age / bin_test.age_bin.size;
	const int max_bin = bin_test.age_bin.max_age / bin_test.age_bin.size;
	
	// create proportion for reference
	int ref_cnt[GENDERS_NUM];
	memset(ref_cnt, 0, GENDERS_NUM * 2);
	for( int g = 0; g < GENDERS_NUM; g++ ) {
		for( int b = min_bin; b < max_bin; b++ ) {
			ref_cnt[g] += bin_ref.age_bin.data[g][b];
		}
	}
	double p_ref[GENDERS_NUM][MAX_AGE_BIN];
	double p_test[GENDERS_NUM][MAX_AGE_BIN];
	memset(p_ref, 0, GENDERS_NUM*MAX_AGE_BIN * sizeof(double));
	memset(p_test, 0, GENDERS_NUM*MAX_AGE_BIN * sizeof(double));

	for( int g = 0; g < GENDERS_NUM; g++ ) {
		for( int b = min_bin; b < max_bin; b++ ) {
			p_ref[g][b] = 1.0 * bin_ref.age_bin.data[g][b] / ref_cnt[g];
			p_test[g][b] = 1.0 * bin_test.age_bin.data[g][b] / bin_test.age_bin.cnt[g];
		}
	}

	for( int g = 0; g < GENDERS_NUM; g++ ) {
		for( int b = min_bin; b < max_bin; b++ ) {
			p_ref[g][b] = 1.0 * bin_ref.age_bin.data[g][b] / ref_cnt[g];
			p_test[g][b] = 1.0 * bin_test.age_bin.data[g][b] / bin_test.age_bin.cnt[g];
			if( abs( p_ref[g][b] - p_test[g][b] ) > 0.05 ) {
				printf( "Age bins differ for %s aged %d-%d: reference %d %.2f%% test %d %.2f%%\n",
					gender_names[g], b * bin_ref.age_bin.size, (b + 1 ) * bin_ref.age_bin.size,
					bin_ref.age_bin.data[g][b], p_ref[g][b], 
					bin_test.age_bin.data[g][b], p_test[g][b] );
				return -3;
			}
		}
	}

	return 0;
}

void cbc_estimates_print( cbc_estimates_t& est_a, cbc_estimates_t& est_b )
{
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		printf( "Gender: %s\n", gender_names[g] );
		for( int c = 0; c < MAX_CBC_CODE_NUM; c++ ) {
			double mean_a = est_a.s[g][c] / est_a.n[g][c];
			double sdv_a = est_a.n[g][c] == 1 ? 0 : sqrt( (est_a.s2[g][c] - mean_a * est_a.s2[g][c] ) / ( est_a.n[g][c] - 1 ) );
			double mean_b = est_b.s[g][c] / est_b.n[g][c];
			double sdv_b = est_b.n[g][c] == 1 ? 0 : sqrt( (est_b.s2[g][c] - mean_a * est_b.s2[g][c] ) / ( est_b.n[g][c] - 1 ) );
			printf( "code %d n %d %d mean %.2f %.2f sdv %.2f %.2f\n",
				c,
				est_a.n[g][c], est_b.n[g][c],
				mean_a, mean_b,
				sdv_a, sdv_b );
				
		}
	}
}

int  cbc_estimates_compare( cbc_estimates_t& est_a, cbc_estimates_t& est_b )
{
	for( int g = MALE; g < GENDERS_NUM; g++ ) {
		for( int c = 0; c < MAX_CBC_CODE_NUM; c++ ) {
			if( est_b.mean[g][c] < est_a.mean[g][c] - 2 * est_a.sdv[g][c] ) {
				return -1;
			}
			if( est_b.mean[g][c] > est_a.mean[g][c] + 2 * est_a.sdv[g][c] ) {
				return +1;
			}
		}
	}

	return 0;

}

void cbc_values_by_age_bin_compare(cbc_values_by_age_bin_t& v_a, cbc_values_by_age_bin_t& v_b)
{
	xls_sheet_t s( "CBCValuesByAgeBinComp" );

	s.w( "Source" ); s.w( "Population" ); s.w("RefCode"); s.w( "Code" ); s.w( "Gender" );  s.w( "Age Group" ); 
	s.w( "RefN" ); s.w( "RefMean" ); s.w( "RefSDV" ); s.w( "RefMin" ); s.w( "RefMax" ); 
	s.w( "N" ); s.w( "Mean" ); s.w( "SDV" ); s.w( "Min" ); s.w( "Max" ); 
	s.w( "T-Test" ); s.w( "q" ); s.w("Z"); s.w("RED FLAG"); s.nl();

	OPEN_OUTPUT()
	WRITE_OUTPUT("\nCBC values comparison by age bins:\n");	

	fprintf(stderr, "DEBUG: Begin-of-CBC-Compare: Size of loop on CBC labs: %zd\n", v_a.cbc_codes.codes.size()); fflush(stderr);
	for( map<cbc_code_id_type , cbc_code_t>::iterator it = v_a.cbc_codes.codes.begin(); it !=  v_a.cbc_codes.codes.end(); it++ ) {

		int ka = it->first;
		int sa = it->second.serial_num;

		string cbc_name = it->second.name;
		fprintf(stderr, "DEBUG: A-side, itr = %d, serial num = %d, CBC test name = %s, back translated to %d\n", ka, sa, cbc_name.c_str(), v_a.cbc_codes.code_name_to_code_id[cbc_name]);
		cbc_code_id_type cbc_code_id = v_b.cbc_codes.code_name_to_code_id[cbc_name];
		cbc_code_t cbc_code = v_b.cbc_codes.codes[cbc_code_id];
		int sb = cbc_code.serial_num;
		fprintf(stderr, "DEBUG: B-side, itr = N/A, serial num = %d, CBC test name = %s, back translated to %d\n", sb, cbc_code.name.c_str(), cbc_code_id);
	}
	// exit(-1) ;

	fprintf(stderr, "DEBUG: Before-CBC-Compare: Size of loop on CBC labs: %zd\n", v_a.cbc_codes.codes.size()); fflush(stderr);

	for( map<cbc_code_id_type , cbc_code_t>::iterator it = v_a.cbc_codes.codes.begin(); it !=  v_a.cbc_codes.codes.end(); it++ ) {
		fprintf(stderr, "DEBUG: starting iteration with index %d\n", it->first);
		int sa = it->second.serial_num;

		string cbc_name = it->second.name;
		fprintf(stderr, "DEBUG: Working on CBC test %s\n", cbc_name.c_str()); fflush(stderr);
		cbc_code_id_type cbc_code_id = v_b.cbc_codes.code_name_to_code_id[cbc_name];
		cbc_code_t cbc_code = v_b.cbc_codes.codes[cbc_code_id];
		int sb = cbc_code.serial_num;

		if( it->second.name != cbc_code.name ) {
			fprintf(stderr,  "*** Error: cannot compare name [%s] [%s] serial %d %d *** \n", 
				it->second.name.c_str(), cbc_code.name.c_str(),
				sa, sb );
			exit(-1);
			continue;
		}

		for (int g=MALE; g<GENDERS_NUM; g++) {

			for (int ab=0; ab<MAX_AGE_BIN; ab++) {
				if( v_a.cvbab.n[g][ab][sa] == 0 || v_b.cvbab.n[g][ab][sb] == 0 ) continue;
					
				double s2_1 = v_a.cvbab.sdv[g][ab][sa];
				double s2_2 = v_b.cvbab.sdv[g][ab][sb];
				double n_1 = v_a.cvbab.n[g][ab][sa];
				double n_2 = v_b.cvbab.n[g][ab][sb];
				double m_1 = v_a.cvbab.mean[g][ab][sa];
				double m_2 = v_b.cvbab.mean[g][ab][sb];
				double q_1 = 0.0;

				if (n_1 > 0) q_1 = s2_1 / n_1;
				double q_2 = 0.0;
				if (n_2 > 0) q_2 = s2_2 / n_2;
				double combind_s = sqrt( q_1 + q_2 );
				double ttest = 0.0;
				if (combind_s > 0.0) ttest = ( m_1 - m_2 ) / combind_s;
				double df = 1.0;
				if (n_1 > 1 && n_2 > 1) {
					df = pow( ( q_1 + q_2 ), 2) /
						( ( pow(q_1, 2) / ( n_1 - 1) ) + ( pow(q_2, 2) / ( n_2 - 1) ) );
				}

				students_t dist( df );
				double q = cdf( complement( dist, fabs(ttest) ) );

				double min_s = s2_1 < s2_2 ? s2_1 : s2_2;
				double baraks_score = 0.0;
				if (min_s > 0.0) baraks_score = abs(m_1 - m_2) / sqrt(min_s);

				s.w( v_b.source.c_str() );
				s.w( v_b.population.c_str() ); 
				s.w( it->second.name.c_str() );
				s.w( cbc_code.name.c_str() );
				s.w( gender_names[g] );
				char label[MAX_STRING_LEN];
				snprintf( label, sizeof(label), "%d-%d", 5*ab, 5*(ab+1) );
				s.w( label );
				s.w( v_a.cvbab.n[g][ab][sa] );
				s.w( v_a.cvbab.mean[g][ab][sa] );
				s.w( v_a.cvbab.sdv[g][ab][sa] );
				s.w( v_a.cvbab.min[g][ab][sa] );
				s.w( v_a.cvbab.max[g][ab][sa] );
				s.w( v_b.cvbab.n[g][ab][sb] );
				s.w( v_b.cvbab.mean[g][ab][sb] );
				s.w( v_b.cvbab.sdv[g][ab][sb] );
				s.w( v_b.cvbab.min[g][ab][sb] );
				s.w( v_b.cvbab.max[g][ab][sb] );
				s.w( ttest ); s.w( q );
				s.w( baraks_score );

				if( (s2_1 > 0.0 && s2_2 > 0.0 && n_1 > 1 && n_2 > 1) &&
					(v_b.cvbab.mean[g][ab][sb] < v_a.cvbab.mean[g][ab][sa] - 1 * v_a.cvbab.sdv[g][ab][sa] || 
					v_b.cvbab.mean[g][ab][sb] > v_a.cvbab.mean[g][ab][sa] + 1 * v_a.cvbab.sdv[g][ab][sa]) ) {
						WRITE_OUTPUT("%s Test [%s] at ages %d-%d for %s : Mean = %.2f %.2f SDV = %.2f %.2f N = %d %d, t = %g, q = %g, barak = %g\n",
							RED_FLAG_MARKER,
							it->second.name.c_str(), 
							5*ab, 5*(ab+1),
							gender_names[g],
							v_a.cvbab.mean[g][ab][sa], v_b.cvbab.mean[g][ab][sb],
							v_a.cvbab.sdv[g][ab][sa], v_b.cvbab.sdv[g][ab][sb],
							v_a.cvbab.n[g][ab][sa], v_b.cvbab.n[g][ab][sb],
							ttest, q, baraks_score) ;
						s.w("1") ;
				} else
					s.w("0") ;

				s.nl();

			}
		}
		fprintf(stderr, "Closing\n");
		fprintf(stderr, "DEBUG: finished iteration with index %d\n", it->first);
	}

	CLOSE_OUTPUT()
	fprintf(stderr, "DEBUG: End-of-CBC-Compare: Size of loop on CBC labs: %zd\n", v_a.cbc_codes.codes.size()); fflush(stderr);
}

int reference_data_set_t::read( char* path )
{
	int ret = 0;
	
	ret = cbc_values_by_age_bin.read( path );
	if( ret != 0 ) return ret;

	age_bin.read( path );

	return 0;
}

int reference_data_set_t::save( char *_path, data_set_t& ds )
{

	boost::filesystem::path p{ _path };
	if ( !boost::filesystem::is_directory(_path)) {
		try {
			create_directory(p);
		}
		catch (...) {
			fprintf(stderr, "Cannot create directory %s\n", _path);
			throw "creating directory";
		}
	}
	else {
		//printf( "output directory [%s] was foud\n", _path);
	}

	write_params( ds, _path);

	cbc_values_by_age_bin_t source_cbc_values_by_age_bin = control_cbc_values_by_age_bin( ds );
	int ret = source_cbc_values_by_age_bin.cvbab.save(_path);

	age_bin_t sorce_age_bin = control_age_distribution_bin( ds );
	sorce_age_bin.age_bin.write(_path);

	// Write test_codes
	return ds.cbc_codes.write(_path) ;

}