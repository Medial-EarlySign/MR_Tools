#ifndef __DATA_TYPES__
#define __DATA_TYPES__

#include "read_data.h"
#include <vector>

#include <fstream>
#include <ostream>
#include <cfloat>

using namespace std;

// data type definitions

class age_bin_fx_t
{
public:
	int size;
	int min_age;
	int max_age;
	int cnt[GENDERS_NUM];
	int data[GENDERS_NUM][MAX_AGE_BIN];

	age_bin_fx_t(int _size = 1, int _min_age = 0, int _max_age = 120): size(_size), min_age(_min_age), max_age(_max_age)
	{
		for( int g = MALE; g < GENDERS_NUM; g++ ) {
			cnt[g] = 0;
			for( int b = 0; b < MAX_AGE_BIN; b++ ) {
				data[g][b] = 0;
			}
		}
	};

	void add( int age, int gender ) 
	{
		if( age < min_age ) return;
		if( age >= max_age ) return;
		int bin = age / size;
		if ( bin >= MAX_AGE_BIN ) return;
		cnt[gender] ++ ;
		data[gender][bin]++;
	}

	void print( void )
	{
		printf( " *** AGE BIN *** \n" );
		printf( "size = %d\n", size );
		printf( "min = %d\n", min_age );
		printf( "max = %d\n", max_age );
		printf( "cnt = %d\n", cnt[0] );
		for( int b = 0; b < MAX_AGE_BIN; b++ ) {
			printf( "[%d] = %d\n", b, data[0][b] );
		}

	}

	bool operator==( const age_bin_fx_t& right ) {
		int ret = 0;
		ret = size - right.size;
		if( ret != 0 ) {
			printf( "size %d %d\n", size, right.size );
			return false;
		}
		ret = min_age - right.min_age;
		if( ret != 0 ) {
			printf( "min %d %d\n", min_age, right.min_age );
			return false;
		}
		ret = max_age - right.max_age;
		if( ret != 0 ) {
			printf( "max %d %d\n", max_age, right.max_age );
			return false;
		}
		for( int g = 0; g < GENDERS_NUM; g++ ) {
			ret = cnt[g] - right.cnt[g];
			if( ret != 0 ) {
				printf( "cnt %d %d\n", cnt[g], right.cnt[g] );
				return false;
			}
			for( int b = 0; b < MAX_AGE_BIN; b++ ) {
				ret = data[g][b] - right.data[g][b];
				if( ret != 0 ) {
					printf( "data[g][b] %d %d\n", data[g][b], right.data[g][b] );
					return false;
				}
			}
		}
		printf( "ret = %d\n", ret );
		return true;
	}

	void write( char *path ) {
		char filename[MAX_STRING_LEN];
		sprintf( filename, "%s/%s", path, reference_age_filename);
		printf( "Writing file %s\n", filename );
		ofstream ofs( filename, ios::binary );
		ofs.write( (char *)this, sizeof(age_bin_fx_t) );
		if( ofs.fail() ) {
			printf( "Error writing file %s\n", filename );
			throw std::invalid_argument( "error writing file" );
		} 
	}

	void read( char* path ) {
		char filename[MAX_STRING_LEN];
		sprintf( filename, "%s/%s", path, reference_age_filename);
		printf( "Reading file %s\n", filename );
		ifstream ofs( filename, ios::binary );
		ofs.read( (char *)this, sizeof(age_bin_fx_t) );
		if( ofs.fail() ) {
			printf( "error reading file %s\n", filename );
			throw std::invalid_argument( "error reading file" );
		}
	}

};

class age_bin_t
{
public:
	age_bin_fx_t age_bin;
	std::string source;

	age_bin_t(int _size = 1, int _first = 0, std::string _source = "none") : age_bin(_size, _first), source(_source)
	{ }

	age_bin_t( char *path ) : source("maccabi")
	{
		age_bin.read( path );
	}

	void read( char *path ) {
		age_bin.read( path );
		source = "maccabi";
	}

};


class cbc_values_by_age_bin_fx_t 
{
public:
	int total_cnt[GENDERS_NUM];
	int excluded_cnt[GENDERS_NUM];
	int n[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	double s[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	double s2[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	double max[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	double min[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	double mean[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];
	double sdv[GENDERS_NUM][MAX_AGE_BIN][MAX_CBC_CODE_NUM];

public:
	cbc_values_by_age_bin_fx_t( void ) 	
	{
		for( int g = 0; g< GENDERS_NUM; g++ ) {
			total_cnt[g] = 0;
			excluded_cnt[g] = 0;
			for(int ab = 0; ab < MAX_AGE_BIN; ab++ ) {
				for(int cc = 0; cc < MAX_CBC_CODE_NUM; cc++ ) {
					n[g][ab][cc] = 0;
					s[g][ab][cc] = 0;
					s2[g][ab][cc] = 0;
					max[g][ab][cc] = DBL_MIN;
					min[g][ab][cc] = DBL_MAX;
					mean[g][ab][cc] = 0;
					sdv[g][ab][cc] = 0;
				}
			}
		}
	}

	cbc_values_by_age_bin_fx_t( char *filename ) 
	{
		printf( "reading file %s\n", filename );
		ifstream ifs( filename, ios::binary );
		ifs.read( (char *)this, sizeof(cbc_values_by_age_bin_fx_t) );;
		
	}

	bool operator==( const cbc_values_by_age_bin_fx_t& right ) 
	{
		for( int g = 0; g< GENDERS_NUM; g++ ) {
			if( total_cnt[g] != right.total_cnt[g] ) return false;
			if( excluded_cnt[g] == right.excluded_cnt[g] ) return false;
			for(int ab = 0; ab < MAX_AGE_BIN; ab++ ) {
				for(int cc = 0; cc < MAX_CBC_CODE_NUM; cc++ ) {
					if( n[g][ab][cc] != right.n[g][ab][cc] ) return false;
					if( s[g][ab][cc] != right.s[g][ab][cc] ) return false;
					if( s2[g][ab][cc] != right.s2[g][ab][cc] ) return false;
					if( max[g][ab][cc] != right.max[g][ab][cc] ) return false;
					if( min[g][ab][cc] != right.min[g][ab][cc] ) return false;
					if( mean[g][ab][cc] != right.mean[g][ab][cc] ) return false;
					if ( sdv[g][ab][cc] != right.sdv[g][ab][cc] ) return false;
				}
			}
		}
		return true;
	}

	int save( char* path ) 
	{
		char filename[MAX_STRING_LEN];
		snprintf( filename, sizeof(filename), "%s/%s", path, reference_cbc_filename);
		printf("writing file %s\n", filename );
		ofstream ofs( filename, ios::binary );
		ofs.write( (char *)this, sizeof(cbc_values_by_age_bin_fx_t) );
		if( ofs.fail() ) {
			printf("Error writing file %s\n", filename );
			return -1;
		}
		return 0;
	}

	void print( void ) 
	{
		printf( "DBL_MIN = %.2f\n", DBL_MIN );
		printf( "DBL_MAX = %.2f\n", DBL_MAX );
		for( int g = 0; g < 1; g++ ) {
			printf( "total_cnt[%d] = %d\n", g, total_cnt[g] );
			printf( "excluded_cnt[%d] = %d\n", g, excluded_cnt[g] );
			for( int a = 10; a < 11; a++ ) {
				for( int c = 3; c < 4; c++ ) {
					printf( "n[%d][%d][%d] = %d\n", g, a, c, n[g][a][c] );
					printf( "s[%d][%d][%d] = %.2f\n", g, a, c, s[g][a][c] );
					printf( "s2[%d][%d][%d] = %.2f\n", g, a, c, s2[g][a][c] );
					printf( "max[%d][%d][%d] = %.2f\n", g, a, c, max[g][a][c] );
					printf( "min[%d][%d][%d] = %.2f\n", g, a, c, min[g][a][c] );
					printf( "mean[%d][%d][%d] = %.2f\n", g, a, c, mean[g][a][c] );
					printf( "sdv[%d][%d][%d] = %.2f\n", g, a, c, sdv[g][a][c] );
				}
			}
		}
	}

	int read( char *path )
	{
		char filename[MAX_STRING_LEN];
		snprintf(filename, sizeof(filename), "%s/%s", path, reference_cbc_filename );
		ifstream ifs( filename, ios::binary );
		ifs.read( (char *)this, sizeof(cbc_values_by_age_bin_fx_t) );
		if( ifs.fail() ) {
			printf ("Error reading %s\n", filename );
			return -1;
		}
		return 0;
	}

};



class cbc_values_by_age_bin_t 
{
public:
	cbc_codes_t cbc_codes;
	std::string source;
	std::string population;
	cbc_values_by_age_bin_fx_t cvbab;

	cbc_values_by_age_bin_t( void ) {}

	cbc_values_by_age_bin_t( cbc_codes_t& _cbc_codes, std::string _source, std::string _population ) :
		cbc_codes(_cbc_codes), source(_source), population( _population )
	{
	}

	int read( char *path ) 
	{
		char filename[MAX_STRING_LEN];
		int return_code = -1;

		snprintf(filename, MAX_STRING_LEN*sizeof(char), "%s/%s", path, cbc_codes_filename_pattern);
		return_code = read_cbc_codes(filename, cbc_codes);
		if ( return_code != 0 ) {
			printf ("Error reading cbc codes\n" );
			return return_code;
		}

		return_code = cvbab.read( path );
		if ( return_code != 0 ) {
			printf ("Error reading cbc values by age bin\n" );
			return return_code;
		}

		population = "control";
		source = "maccabi";

		return 0;
	}
	
};

class cbc_estimates_t
{
public:
	int n[GENDERS_NUM][MAX_CBC_CODE_NUM];
	double s[GENDERS_NUM][MAX_CBC_CODE_NUM];
	double s2[GENDERS_NUM][MAX_CBC_CODE_NUM];
	std::vector<double> values[GENDERS_NUM][MAX_CBC_CODE_NUM];

	double mean[GENDERS_NUM][MAX_CBC_CODE_NUM];
	double sdv[GENDERS_NUM][MAX_CBC_CODE_NUM];

	cbc_estimates_t( void ) 
	{
		for( int g = MALE; g < GENDERS_NUM; g++ ) {
			for( int c = 0; c < MAX_CBC_CODE_NUM; c++ ) {
				n[g][c] = 0;
				s[g][c] = 0;
				s2[g][c] = 0;

				mean[g][c] = 0;
				sdv[g][c] = 0;
			}
		}
	}
};

class reference_data_set_t 
{
public:
	cbc_values_by_age_bin_t cbc_values_by_age_bin;
	age_bin_t age_bin;
public:
	int read( char* path );
	static int save( char *path, data_set_t& ds );
};

// functions

void age_bins_print  ( age_bin_t& bin_a, age_bin_t& bin_b, const string& type );
int  age_bins_compare( age_bin_t& bin_a, age_bin_t& bin_b );

void cbc_estimates_print( cbc_estimates_t& cbc_a, cbc_estimates_t& cbc_b );
int cbc_estimates_compare( cbc_estimates_t& cbc_a, cbc_estimates_t& cbc_b );

void cbc_values_by_age_bin_compare(cbc_values_by_age_bin_t& v_a, cbc_values_by_age_bin_t& v_b);

#endif /* __DATA_TYPES__ */