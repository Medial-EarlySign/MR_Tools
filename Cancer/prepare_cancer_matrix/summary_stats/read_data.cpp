#include "read_data.h"
#include "tools.h"
#include "data_types.h"
#include <string>
#include <algorithm>
#include <assert.h>
#include <iostream>
#include <fstream>
#include <ctime>
#include <set>
#include <string.h>

using namespace std;

/*
char crc_types[][MAX_STRING_LEN] = {
	"Respiratory system,Lung and Bronchus,Unspecified"
};

char colon_types[][MAX_STRING_LEN] = {
	"Respiratory system,Lung and Bronchus,Unspecified"
};

char rectum_types[][MAX_STRING_LEN] = {
	"Respiratory system,Lung and Bronchus,Unspecified"
	};
*/

/*
	621 Morph=Adenocarcinoma
    352 Morph=Non-small cell carcinoma
    268 Morph=Squamous cell carcinoma
*/

char crc_types[][MAX_STRING_LEN] = {
	"Digestive Organs,Digestive Organs,Colon",
	"Digestive Organs,Digestive Organs,Rectum",
	"cancer,crc,colon",
	"cancer,crc,rectum",
	"cancer,crc,rectum;colon"};

char colon_types[][MAX_STRING_LEN] = {
	"Digestive Organs,Digestive Organs,Colon",
	"cancer,crc,colon",
	"cancer,crc,rectum;colon"};

char rectum_types[][MAX_STRING_LEN] = {
	"Digestive Organs,Digestive Organs,Rectum",
	"cancer,crc,rectum" };




int read_registry(char *file_name, registry_t& registry) {

	int crc_cnt = 0;

	// Prepare
	map<string,int> crcs;
	for (int i=0; i<sizeof(crc_types)/MAX_STRING_LEN; i++)
		crcs[crc_types[i]] = 1 ;
	map<string,int> colons;
	for (int i=0; i<sizeof(colon_types)/MAX_STRING_LEN; i++)
		colons[colon_types[i]] = 1 ;
	map<string,int> rectums;
	for (int i=0; i<sizeof(rectum_types)/MAX_STRING_LEN; i++)
		rectums[rectum_types[i]] = 1 ;

	// Read 
	FILE *fp  = fopen(file_name, "r");
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for readingn", file_name) ;
		return -1 ;
	}
	fprintf(stderr, "Reading registry %s\n", file_name);

	OPEN_LOG();
	
	char buffer[BUFFER_SIZE] ;
	char field[MAX_STRING_LEN] ;
	char line[REGISTRY_NFIELDS][MAX_STRING_LEN] ;
	char *startbuf,*endbuf ;

	while(!(feof(fp))) {
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;
			                
		startbuf = endbuf = buffer; 
		int ifield = 0 ;

		// Parse each line into fields, and save all lines in "line" array
		for( ;  ;  ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == ',')) {
				strncpy(field, startbuf, endbuf-startbuf);                     
				field[endbuf-startbuf]='\0';

				ifield++ ;
				if (ifield > REGISTRY_NFIELDS) {
					fprintf(stderr,"Could not read file\n") ;
					return -1 ;
				}
					
				strncpy(line[ifield-1],field,MAX_STRING_LEN) ;
				line[ifield-1][MAX_STRING_LEN-1] = '\0' ;
				startbuf=endbuf+1 ;
			}

			if ((*endbuf == '\n') || (*endbuf == '\r'))
				break ;                      
			endbuf++;
		}

		if (strcmp(line[0],"NUMERATOR") != 0) { //skips header only

			int id = atoi(line[REGISTRY_ID_FIELD]) ;
			int stage = -1; 
			if( strcmp( line[REGISTRY_STAGE_FIELD], " " ) != 0 ) {
				stage = atoi(line[REGISTRY_STAGE_FIELD]);
			}

			int day,month,year ;
			if (sscanf(line[REGISTRY_DATE_FIELD],"%d/%d/%d",&month,&day,&year) != 3) { // check whether date matches pattern MM/DD/YYYY
				if (sscanf(line[REGISTRY_DATE_FIELD],"%4d%2d%2d",&year,&month,&day) != 3) { // if no match, check that date matches pattern YYYYMMDD. If no match as well - quit.
					fprintf(stderr,"Could not parse date %s. Expected format is: MM/DD/YYY or YYYYMMDD\n",line[REGISTRY_DATE_FIELD]) ;
					return -1 ;
				}
			}
			if( day < 1 || day > 31 ) { 
				WRITE_LOG("Warning: Error parsing crc onset date [%s] for id %d: day %d is out of noraml range\n",
					line[REGISTRY_DATE_FIELD], id, day);
				day = 1;
			}
			if( month < 1 || month > 12 ) {
				WRITE_LOG("Warning: Error parsing crc onset date [%s] for id %d: month %d is out of noraml range\n",
					line[REGISTRY_DATE_FIELD], id, month);
				month = 1;
			}
			if( year < 1900 || year > 2999 ) {
				fprintf(stderr, "Error parsing crc onset date [%s] for id %d: year %d is out of noraml range\n",
					line[REGISTRY_DATE_FIELD], id, year);
				return -1;
			}
			int days = get_days(day + 100*month + 10000*year) ;
			assert(days>0);

			char cancer_type[MAX_STRING_LEN] ;
			sprintf(cancer_type,"%s,%s,%s",line[REGISTRY_CANCER_FIELD],line[REGISTRY_CANCER_FIELD+1],line[REGISTRY_CANCER_FIELD+2]) ;

			if( id == 0 || id == 1 ) {
				printf("Line=[%s], id = %d, day = %d, month = %d, year = %d, days = %d, stage = %d\n",
					buffer, id, day, month, year, days, stage);
			}

			registry_entry_t new_entry;
			new_entry.days_since_1900 = days;
			new_entry.stage = stage;

			if (crcs.find(cancer_type) != crcs.end()) { // CRC
				crc_cnt++;
				if ( registry[CANCER_TYPE_CRC].find(id) == registry[CANCER_TYPE_CRC].end() || 
					 days < registry[CANCER_TYPE_CRC][id].days_since_1900 ) {
						 registry[CANCER_TYPE_CRC][id] = new_entry;
						 if( colons.find(cancer_type) != colons.end() ) {
							 registry[CANCER_TYPE_COLON][id] = new_entry;
							 if( registry[CANCER_TYPE_RECTUM].find(id) != registry[CANCER_TYPE_RECTUM].end() ) {
								 registry[CANCER_TYPE_RECTUM].erase(id);
							 }
						 }
						 if( rectums.find(cancer_type) != rectums.end() ) {
							 registry[CANCER_TYPE_RECTUM][id] = new_entry;
							 if( registry[CANCER_TYPE_COLON].find(id) != registry[CANCER_TYPE_COLON].end() ) {
								 registry[CANCER_TYPE_COLON].erase(id);
							 }
						 }
				} 
				else {
					registry[CANCER_TYPE_CRC_RECCURENCE][id] = new_entry;
					if( colons.find(cancer_type) != colons.end() ) {
							 registry[CANCER_TYPE_COLON_RECCURENCE][id] = new_entry;
						 }
						 if( rectums.find(cancer_type) != rectums.end() ) {
							 registry[CANCER_TYPE_RECTUM_RECCURENCE][id] = new_entry;
						 }
				}
			}
			else {// NON CRC
				if ( registry[CANCER_TYPE_NON_CRC].find(id) == registry[CANCER_TYPE_NON_CRC].end() || 
					 days < registry[CANCER_TYPE_NON_CRC][id].days_since_1900 ) {
						 registry[CANCER_TYPE_NON_CRC][id] = new_entry;
				} 
				else {
					registry[CANCER_TYPE_NON_CRC_RECCURENCE][id] = new_entry;
				}
			}

		}
	}

	fprintf(stderr, "Registry information:\n" );
	fprintf(stderr, "CRC: %zd reccurence %zd total %zd\n",
		registry[CANCER_TYPE_CRC].size(), registry[CANCER_TYPE_CRC_RECCURENCE].size(),
		registry[CANCER_TYPE_CRC].size() + registry[CANCER_TYPE_CRC_RECCURENCE].size());
	fprintf(stderr, "COLON: %zd reccurence %zd total %zd\n",
		registry[CANCER_TYPE_COLON].size(), registry[CANCER_TYPE_COLON_RECCURENCE].size(),
		registry[CANCER_TYPE_COLON].size() + registry[CANCER_TYPE_COLON_RECCURENCE].size() );
	fprintf(stderr, "RECTUM: %zd reccurence %zd total %zd\n",
		registry[CANCER_TYPE_RECTUM].size(), registry[CANCER_TYPE_RECTUM_RECCURENCE].size(),
		registry[CANCER_TYPE_RECTUM].size() + registry[CANCER_TYPE_RECTUM_RECCURENCE].size() );
	fprintf(stderr, "NON CRC: %zd reccurence %zd total %zd\n",
		registry[CANCER_TYPE_NON_CRC].size(), registry[CANCER_TYPE_NON_CRC_RECCURENCE].size(),
		registry[CANCER_TYPE_NON_CRC].size() + registry[CANCER_TYPE_NON_CRC_RECCURENCE].size() ) ;
	
	fclose(fp) ;
	CLOSE_LOG();
	return 0 ;
}

int is_in_censor(int stat, date_t date, params_t& params)
{
	int result = 0;

	int min_day = get_days(params["CENSOR_INSCULSION_START_DATE"]) ;
	int max_day = get_days(params["CENSOR_INSCULSION_END_DATE"]) ;

	if (stat == 1 && date > max_day) result = 1;
	if (stat == 2 && date < min_day) result = 2;

	return result;
}

int read_demography(char *file_name, params_t& params, demography_t& demography) {

	assert( params.size() > 0 );

	FILE *fp = fopen(file_name, "r");
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}
	fprintf(stderr, "Reading demography %s\n", file_name);
	

	// Read demography
	int id ;
	int byear ;
	char gender ;

	while (! feof(fp)) {
		int rc = fscanf(fp,"%d %d %c\n",&id,&byear,&gender) ;
		if (rc == EOF)
			break ;

		if (rc != 3) {
			fprintf(stderr,"Could not read status line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		demography_entry_t new_dem ;
		new_dem.byear = byear ;
		new_dem.gender = gender;
		demography[id] = new_dem ;
	}


	fclose(fp) ;

	fprintf(stderr,"Read %zd entries in %s\n", demography.size(), file_name) ;

	return 0 ;
}

int read_censor(char *file_name ,params_t&params, censor_t& censor) {

	assert( params.size() > 0 );

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}
	fprintf(stderr, "Reading censor %s\n", file_name);


	// Read status
	int id ;
	int date,stat,reason ;

	while (! feof(fp)) {
		int rc = fscanf(fp,"%d %d %d %d\n",&id,&stat,&reason,&date) ;
		if (rc == EOF)
			break ;

		if (rc != 4) {
			fprintf(stderr,"Could not read status line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		date_t date_days = get_days(date);

		censor_entry_t new_censor_entry ;
		new_censor_entry.date = date_days ;
		new_censor_entry.reason = reason ;
		new_censor_entry.stat = stat ;
		int in_censor = is_in_censor(stat, date_days, params); 
		new_censor_entry.in_censor = in_censor == 0 ? true : false;
		new_censor_entry.in_censor_reason = in_censor;
		censor[id] = new_censor_entry ;
	}

	fclose(fp) ;
	fprintf(stderr,"Read %zd entries in %s\n", censor.size(), file_name) ;
	return 0 ;
}

int read_cbc_codes(char *file_name, cbc_codes_t& cbc_codes) {

	FILE *fp = fopen(file_name, "r");
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n", file_name) ;
		return -1 ;
	}
	
	enum {
		TEST_CODE_NUMBER_FIELD = 0,
		TEST_CODE_NAME_FIELD,
		TEST_CODE_RESOLUTION_FIELD,
		TEST_CODE_MALE_MIN_OUTLIER_FIELD,
		TEST_CODE_MALE_MAX_OUTLIER_FIELD,
		TEST_CODE_FEMALE_MIN_OUTLIER_FIELD,
		TEST_CODE_FEMALE_MAX_OUTLIER_FIELD,
		TEST_CODE_RED_FLAG,
		TEST_CODE_NFIELDS
	};

	char buffer[BUFFER_SIZE] ;
	char field[MAX_STRING_LEN] ;
	char line[TEST_CODE_NFIELDS][MAX_STRING_LEN] ;
	char *startbuf,*endbuf ;
	
	int code_cnt = 0;
	cbc_codes.text = "";
	while(!(feof(fp))) {      
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;
		
		// appending the line to the text field
		for (int posBuf = 0; posBuf < BUFFER_SIZE && buffer[posBuf] != '\0'; ++posBuf) {
			cbc_codes.text += buffer[posBuf];
		}

		startbuf = endbuf = buffer; 
		int ifield = 0 ;
		for( ;  ;  ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == ',')) {
				strncpy(field, startbuf, endbuf-startbuf);                     
				field[endbuf-startbuf]='\0';

				ifield++ ;
				if (ifield > TEST_CODE_NFIELDS) {
					fprintf(stderr,"Could not read file %s\n", file_name) ;
					return -1 ;
				}
					
				strncpy(line[ifield-1],field,MAX_STRING_LEN) ;
				line[ifield-1][MAX_STRING_LEN-1] = '\0' ;
				startbuf=endbuf+1 ;
			}

			if ((*endbuf == '\n') || (*endbuf == '\r')) {
				break ;
			}
			endbuf++;
		}

		cbc_code_id_type cbc_code ;
		if (sscanf(line[TEST_CODE_NUMBER_FIELD],"%d",&cbc_code) != 1) {
			fprintf(stderr,"Could not parse test code %s\n",line[TEST_CODE_NUMBER_FIELD]) ;
			return -1 ;
		}

		char cbc_code_name[MAX_STRING_LEN] ;
		sprintf(cbc_code_name,"%s",line[TEST_CODE_NAME_FIELD]) ;

		double cbc_code_resolution = 0 ;
		if (sscanf(line[TEST_CODE_RESOLUTION_FIELD],"%lf",&cbc_code_resolution) != 1) {
			fprintf(stderr,"Could not parse test code %s min outlier\n",line[TEST_CODE_NUMBER_FIELD]) ;
			return -1 ;
		}

		double cbc_code_male_min_outlier = 0 ;
		if (sscanf(line[TEST_CODE_MALE_MIN_OUTLIER_FIELD],"%lf",&cbc_code_male_min_outlier) != 1) {
			fprintf(stderr,"Could not parse test code %s min outlier\n",line[TEST_CODE_NUMBER_FIELD]) ;
			return -1 ;
		}

		double cbc_code_male_max_outlier = 0 ;
		if (sscanf(line[TEST_CODE_MALE_MAX_OUTLIER_FIELD],"%lf",&cbc_code_male_max_outlier) != 1) {
			fprintf(stderr,"Could not parse test code %s max outlier\n",line[TEST_CODE_NUMBER_FIELD]) ;
			return -1 ;
		}

		double cbc_code_female_min_outlier = 0 ;
		if (sscanf(line[TEST_CODE_FEMALE_MIN_OUTLIER_FIELD],"%lf",&cbc_code_female_min_outlier) != 1) {
			fprintf(stderr,"Could not parse test code %s min outlier\n",line[TEST_CODE_NUMBER_FIELD]) ;
			return -1 ;
		}

		double cbc_code_female_max_outlier = 0 ;
		if (sscanf(line[TEST_CODE_FEMALE_MAX_OUTLIER_FIELD],"%lf",&cbc_code_female_max_outlier) != 1) {
			fprintf(stderr,"Could not parse test code %s max outlier\n",line[TEST_CODE_NUMBER_FIELD]) ;
			return -1 ;
		}

		int cbc_code_red_flag = 0;
		if (sscanf(line[TEST_CODE_RED_FLAG],"%d",&cbc_code_red_flag) != 1) {
			fprintf(stderr,"Could not parse test code %s red flag\n", line[TEST_CODE_RED_FLAG]) ;
			return -1 ;
		}

		cbc_code_t new_cbc_code;
		new_cbc_code.serial_num = code_cnt++;
		new_cbc_code.name = cbc_code_name;
		new_cbc_code.resolution = cbc_code_resolution;
		new_cbc_code.min_outlier[MALE] = cbc_code_male_min_outlier;
		new_cbc_code.max_outlier[MALE] = cbc_code_male_max_outlier;
		new_cbc_code.min_outlier[FEMALE] = cbc_code_female_min_outlier;
		new_cbc_code.max_outlier[FEMALE] = cbc_code_female_max_outlier;
		new_cbc_code.red_flag = cbc_code_red_flag;
		cbc_codes.codes[cbc_code] = new_cbc_code;
		cbc_codes.code_name_to_code_id[cbc_code_name] = cbc_code;
	}

//	assert( cbc_codes.codes.size() < CBC_MAX_CODES_NUM );
//	assert( cbc_codes.codes.size() < CBC_MAX_CODES_NUM );
	fprintf(stderr,"Read %zd entries in %s\n", cbc_codes.codes.size(), file_name) ;
	
	fclose(fp) ;
	return 0 ;
}

int read_cbcs_txt(char *file_name, cbc_codes_t& cbc_codes, cbc_t& cbc) {
	// this code is no in use

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}
	fprintf(stderr, "Reading cbc file %s\n", file_name);

	int id, code, date ;
	double value ;

	int itest = 0 ;
	while (! feof(fp)) {
		int rc = fscanf(fp,"%d %d %d %lf\n",&id,&code,&date,&value) ;
		if (rc == EOF)
			break ;
		
		if (rc != 4) {
			fprintf(stderr,"Could not read status line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		if (date%10000 == 0) {
			fprintf(stderr,"(Ignoring %d %d %d %lf)",id,code,date,value) ;
			continue;
		}

		assert( cbc_codes.codes.find(code) != cbc_codes.codes.end() );
		cbc[id][get_days(date)][code] = value ; 

		if ((++itest)%1000000 == 0) {
			fprintf(stderr,"Read %d tests... ",itest) ;
		}
	}

	fprintf(stderr,"Read %d cbc test for %zd ids in %s\n", itest, cbc.size(), file_name) ;

	fprintf(stderr,"\n") ;
	fclose(fp) ;
	return 0 ;
}

int read_cbcs_bin_with_no_header(char *file_name, cbc_codes_t& cbc_codes, cbc_t& cbc) {
	
	// assumes first integer is the number of lines in file

	fprintf(stderr, "Reading cbc file %s\n", file_name);

	typedef struct {
		int id;
		int code;
		int date;
		double value;
	} cbc_entry_t;

	FILE *fp = fopen(file_name,"rb") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	int lines = 0;
	size_t rc = fread( &lines, sizeof(lines), 1, fp);
	if( rc != 1 ) {
		fprintf(stderr,"Error reading number of lines. return code = %zd",rc) ;
	}
	printf("Input file contains %d lines\n", lines );
	

	cbc_entry_t cbc_entry;

	int itest = 0 ;
	while (! feof(fp)) {
		//int rc = fscanf(fp,"%d %d %d %lf\n",&id,&code,&date,&value) ;
		size_t rc = fread( &cbc_entry, sizeof(cbc_entry_t), 1, fp);
		if (rc == 0)
			break ;


		for( int i = 0; i < rc; i++ ) {
			assert( cbc_codes.codes.find(cbc_entry.code) != cbc_codes.codes.end() );
			cbc[cbc_entry.id][get_days(cbc_entry.date)][cbc_entry.code] = cbc_entry.value ; 
		}

		if ((++itest)%1000000 == 0) {
			fprintf(stderr,"Read %d tests... ",itest) ;
		}
	}

	fprintf(stderr,"Read %d cbc test for %zd ids in %s\n", itest, cbc.size(), file_name) ;

	fprintf(stderr,"\n") ;
	fclose(fp) ;
	return 0 ;
}

int read_cbcs_bin(char *file_name, cbc_codes_t& cbc_codes, cbc_t& cbc) {
	
	fprintf(stderr, "Reading cbc file %s\n", file_name);

	typedef struct {
		int id;
		int code;
		int date;
		double value;
	} cbc_entry_t;

	FILE *fp = fopen(file_name,"rb") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	int lines = 0;
	size_t rc = fread( &lines, sizeof(lines), 1, fp);
	if( rc != 1 ) {
		fprintf(stderr,"Error reading number of lines. return code = %zd",rc) ;
		return -1;
	}
	
	cbc_entry_t *cbc_entry = (cbc_entry_t *)malloc(lines*sizeof(cbc_entry_t));
	if( cbc_entry == NULL ) {
		fprintf(stderr,"Error allocating memory for %d elements of size %zd (%.2fGB)\n",
			lines, sizeof(cbc_entry_t), (1.0*lines*sizeof(cbc_entry_t))/1024/1024/1024 ) ;
		return -1;
	}

	fprintf(stderr,"Reading %d lines from %s ... ", lines, file_name) ;
	rc = fread(cbc_entry, sizeof(cbc_entry_t), lines, fp);
	if (rc != lines ) {
		fprintf(stderr,"Error reading data from %s. read %zd cbc_entrys",file_name, rc) ;
		return -1;
	} else {
		fprintf(stderr,"Done!\n") ;
	}

	fprintf(stderr,"Reading tests ... ") ;
	for( size_t i = 0; i < rc; i++ ) {
		assert( cbc_codes.codes.find(cbc_entry[i].code) != cbc_codes.codes.end() );
		if ( i > 0 && i % 10000000 == 0) {
			fprintf(stderr,"%zd...",i) ;
		}
		// if you want to filter data set by dates
		// if( get_days(cbc_entry[i].date)] < ds.params["CBC_MIN_DAY"] ) than continue .... 
		cbc[cbc_entry[i].id][get_days(cbc_entry[i].date)][cbc_entry[i].code] = cbc_entry[i].value ; 
	}
	fprintf(stderr,"Done!\n ") ;

	fprintf(stderr,"Read %zd cbc test for %zd ids in %s\n", rc, cbc.size(), file_name) ;

	free( cbc_entry );
	fclose(fp) ;
	return 0 ;
}

int convert_cbc_to_cbc_dates( cbc_t &cbc, cbc_dates_ex_t& cbc_dates_ex, cbc_codes_t& cbc_codes )
{
	// create a vector of all cbc days per id
	// this vector contains only unique days (asserted by a special set)

	std::map<int, int> year_cnt;
	std::map<int, int> day_cnt;

	for (cbc_t::iterator it = cbc.begin(); it != cbc.end(); it ++) {
		int id = it->first;
		std::map<date_t, std::map<cbc_code_id_type, double> >& dates = it->second ;

		std::vector<date_t> vdates; 
		std::set<date_t>    sdates;
		for (std::map<date_t, std::map<cbc_code_id_type, double> >::iterator it = dates.begin();
			it != dates.end(); it++) {
				day_cnt[it->first] ++;
				int year = days_since1900_2_year( it->first );
				year_cnt[year] ++; 
				if( sdates.find( it->first ) == sdates.end() ) {
					vdates.push_back(it->first) ;
					sdates.insert( it->first );
				}
		}

		if (vdates.size() > 0) {
			cbc_dates_ex.dates[id] = vdates ;
			sort(cbc_dates_ex.dates[id].begin(),cbc_dates_ex.dates[id].end(),int_compare()) ;
		}
		
	}

	fprintf(stderr,"Converted cbc dates for %zd ids\n", cbc_dates_ex.dates.size()) ;

	int cbc_mode_year = year_cnt.begin()->first;
	for( std::map<int,int>::iterator it = year_cnt.begin(); it != year_cnt.end(); it++ ) {
		if( it->second > year_cnt[cbc_mode_year] ) {
			cbc_mode_year = it->first;
		}
	}

	int cbc_min_date = day_cnt.begin()->first;
	int cbc_max_date = day_cnt.begin()->first;
	for( std::map<int, int>::iterator it = day_cnt.begin(); it != day_cnt.end(); it++ ) {
		if( it->first < cbc_min_date ) cbc_min_date = it->first;
		if( it->first > cbc_max_date ) cbc_max_date = it->first;
	}

	cbc_dates_ex.cbc_mode_year = cbc_mode_year;
	cbc_dates_ex.cbc_min_day = cbc_min_date;
	cbc_dates_ex.cbc_max_day = cbc_max_date;

	return 0;
}

int read_params(char* file_name, params_t& params)
{
	FILE *fp = fopen(file_name, "r");
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n", file_name) ;
		return -1 ;
	}
	
	enum {
		PARAM_NAME_FIELD = 0,
		PARAM_VALUE_FIELD,
		PARAM_NFIELDS
	};

	char buffer[BUFFER_SIZE] ;
	char field[MAX_STRING_LEN] ;
	char line[PARAM_NFIELDS][MAX_STRING_LEN] ;
	char *startbuf,*endbuf ;

	while(!(feof(fp))) {      
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;

		startbuf = endbuf = buffer; 
		int ifield = 0 ;
		for( ;  ;  ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == ',')) {
				strncpy(field, startbuf, endbuf-startbuf);                     
				field[endbuf-startbuf]='\0';

				ifield++ ;
				if (ifield > PARAM_NFIELDS) {
					fprintf(stderr,"Could not read file %s\n", file_name) ;
					return -1 ;
				}

				strncpy(line[ifield-1],field,MAX_STRING_LEN) ;
				line[ifield-1][MAX_STRING_LEN-1] = '\0' ;
				startbuf=endbuf+1 ;
			}

			if ((*endbuf == '\n') || (*endbuf == '\r'))
				break ;                      
			endbuf++;
		}

		char param_name[MAX_STRING_LEN] ;
		sprintf(param_name,"%s",line[PARAM_NAME_FIELD]) ;

		int param_value ;
		if (sscanf(line[PARAM_VALUE_FIELD],"%d",&param_value) != 1) {
			fprintf(stderr,"Could not parse test code %s\n",line[PARAM_VALUE_FIELD]) ;
			return -1 ;
		}

		params[param_name] = param_value;
	}

	fprintf(stderr,"Read %zd entries in %s:\n", params.size(), file_name) ;
	for( params_t::iterator it = params.begin(); it != params.end(); it++ ) {
		printf("%s = %d\n", it->first.c_str(), it->second );
	}
	
	fclose(fp) ;
	return 0 ;
}

int calculate_params(data_set_t& ds)
{
	// registry years
	int first_registry_year = days_since1900_2_year( ds.registry[CANCER_TYPE_CRC].begin()->second.days_since_1900 );
	int last_registry_year = days_since1900_2_year( ds.registry[CANCER_TYPE_CRC].begin()->second.days_since_1900 );
	for (cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin();
		it != ds.registry[CANCER_TYPE_CRC].end(); it++) {
			int year = days_since1900_2_year( it->second.days_since_1900 );
			if( year < first_registry_year ) {
				first_registry_year = year;
			}
			if( year > last_registry_year ) {
				last_registry_year = year;
			}
	}
	ds.params["REGISTRY_FIRST_YEAR"] = first_registry_year;
	ds.params["REGISTRY_LAST_YEAR"] = last_registry_year;
	printf("Registry: first crc year %d, last crc year %d\n", first_registry_year, last_registry_year );

	int first_cbc_year = days_since1900_2_year( ds.cbc_dates_ex.dates.begin()->second.front() );
	int last_cbc_year = days_since1900_2_year( ds.cbc_dates_ex.dates.begin()->second.back() );
	for( cbc_dates_t::iterator it = ds.cbc_dates_ex.dates.begin() ; it != ds.cbc_dates_ex.dates.end(); it++ ) {
		int first_year = days_since1900_2_year( it->second.front() );
		if( first_year < first_cbc_year ) {
			first_cbc_year = first_year;
		}
		int last_year = days_since1900_2_year( it->second.back() );
		if( last_year > last_cbc_year ) {
			last_cbc_year = last_year;
		}
	}
	ds.params["CBC_FIRST_YEAR"] = first_cbc_year;
	ds.params["CBC_LAST_YEAR"] = last_cbc_year;
	printf("CBC: first cbc date %d, last cbc date %d\n", first_cbc_year, last_cbc_year );

	return 0;
}

int extra( data_set_t& ds )
{
	for( demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++ ) {
		int id = it->first;
		assert( ds.censor.find(id) != ds.censor.end() );
		int birth_year = it->second.byear;
		int gender = gender2number(it->second.gender);
		for( int y=ds.params["REGISTRY_FIRST_YEAR"]; y<ds.params["REGISTRY_LAST_YEAR"]; y++ ) {
			if( is_in_censor_for_year(y, id, ds) ) {
				ds.cnt_born_in_censor_for_year[gender][birth_year][y]++;
			}
		}
	}

	for( cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin(); it != ds.registry[CANCER_TYPE_CRC].end(); it++ ) {
		int id = it->first;
		int sick_year = days_since1900_2_year(it->second.days_since_1900);
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number( ds.demography[id].gender );
		int birth_year = ds.demography[id].byear;
		if( is_in_censor_for_year(sick_year, id, ds) ) {
			ds.cnt_crc_born_sick_year[gender][birth_year][sick_year]++;
		}
	}

	for( cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_COLON].begin(); it != ds.registry[CANCER_TYPE_COLON].end(); it++ ) {
		int id = it->first;
		int sick_year = days_since1900_2_year(it->second.days_since_1900);
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number( ds.demography[id].gender );
		int birth_year = ds.demography[id].byear;
		if( is_in_censor_for_year(sick_year, id, ds) ) {
			ds.cnt_colon_born_sick_year[gender][birth_year][sick_year]++;
		}
	}

	for( cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_RECTUM].begin(); it != ds.registry[CANCER_TYPE_RECTUM].end(); it++ ) {
		int id = it->first;
		int sick_year = days_since1900_2_year(it->second.days_since_1900);
		assert( ds.demography.find(id) != ds.demography.end() );
		int gender = gender2number( ds.demography[id].gender );
		int birth_year = ds.demography[id].byear;
		if( is_in_censor_for_year(sick_year, id, ds) ) {
			ds.cnt_rectum_born_sick_year[gender][birth_year][sick_year]++;
		}
	}

	return 0;
}

void validate_data_set( data_set_t& ds )
{
	fprintf(stderr, "\nValidating Dataset\n");

	// Params: check minimal number
	if( ds.params.size() < 14 ) {
		fprintf(stderr, "Error!!! Params should have 14 values. Check params (see maccabi params as reference)\n" );
		exit( -1 );
	}


	// compare censor IDs to Demography IDs
	if( ds.censor.size() != ds.demography.size() ) {
		fprintf(stderr, "Warning!!! censor size %zd <> demography size %zd\n", ds.censor.size(), ds.demography.size() );
	}
	for( censor_t::iterator it = ds.censor.begin(); it != ds.censor.end(); it++ ) {
		if( ds.demography.find(it->first) == ds.demography.end() ) {
			fprintf(stderr, "Warning!!! ID %d is found in censor, but not in demography\n", it->first);
		}
	}
	for( demography_t::iterator it = ds.demography.begin(); it != ds.demography.end(); it++ ){
		if( ds.censor.find(it->first) == ds.censor.end() ) {
			fprintf(stderr, "Warning!!! ID %d is found in demography, but not in censor\n", it->first);
		}
	}


	// Check Registry: every ID appears in demography
	for( cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin();
		it != ds.registry[CANCER_TYPE_CRC].end(); it++ ) {
		if( ds.demography.find(it->first) == ds.demography.end() ) {
			fprintf(stderr, "Warning!!! ID %d is found in registry, but not in demography\n", it->first);
		}
	}

	// Check CBC: every ID appears in demography
	for( cbc_t::iterator it = ds.cbc.begin(); it != ds.cbc.end(); it++ ) {
		if( ds.demography.find(it->first) == ds.demography.end() ) {
			fprintf(stderr, "Warning!!! ID %d is found in cbc, but not in demography\n", it->first);
		}
	}

	// Registry dates
#if 0 // check registry min & max years
	int params_registry_first_year = ds.params["REGISTRY_FIRST_YEAR"];
	int params_registry_last_year = ds.params["REGISTRY_LAST_YEAR"];
	int registry_first_date = ds.registry[CANCER_TYPE_CRC].begin()->second.days_since_1900;
	int registry_last_date = ds.registry[CANCER_TYPE_CRC].begin()->second.days_since_1900;
	for( cancer_specific_type_registry_t::iterator it = ds.registry[CANCER_TYPE_CRC].begin(); it != ds.registry[CANCER_TYPE_CRC].end(); it++ ) {
		if( it->second.days_since_1900 < registry_first_date ) {
			registry_first_date = it->second.days_since_1900;
		}
		if( it->second.days_since_1900 > registry_last_date ) {
			registry_last_date = it->second.days_since_1900;
		}
	}
	int registry_first_year = 1900 + registry_first_date / 365; 
	int registry_last_year = 1900 + registry_last_date / 365; 
	if( params_registry_first_year != registry_first_year ) {
		fprintf(stderr, "Warning!!! params - REGISTRY_FIRST_YEAR = %d, while first year found in registry = %d\n",
			params_registry_first_year, registry_first_year );
	} 
	if( params_registry_last_year != registry_last_year ) {
		fprintf(stderr, "Warning!!! params - REGISTRY_LAST_YEAR = %d, while last year found in registry = %d\n",
			params_registry_last_year, registry_last_year );
	} 
#endif

	// CBC dates
#if 0 // check cbc min & max years
	int params_cbc_first_year = ds.params["CBC_FIRST_YEAR"];
	int cbc_min_year = ds.cbc_dates_ex.cbc_min_day / 365 + 1900;
	if( cbc_min_year != params_cbc_first_year ) {
		fprintf(stderr, "Warning!!! params - CBC_FIRST_YEAR = %d, while first year found in cbc = %d\n",
			params_cbc_first_year, cbc_min_year );
	}
	int params_cbc_last_year = ds.params["CBC_LAST_YEAR"];
	int cbc_max_year = ds.cbc_dates_ex.cbc_max_day / 365 + 1900;
	if( cbc_max_year != params_cbc_last_year ) {
		fprintf(stderr, "Warning!!! params - CBC_LAST_YEAR = %d, while last year found in cbc = %d\n",
			params_cbc_last_year, cbc_max_year );
	}
#endif 

	fprintf(stderr, "Done Validating\n");

}

int read_data_set( const char* path, const  char* source, data_set_t& ds, int index )
{
	char filename[MAX_STRING_LEN];
	int return_code = -1;

	fprintf( stdout, "Reading data set for %s\n", source );

	ds.index = index;

	string s(source);
	ds.source = s;
	
	snprintf(filename, MAX_STRING_LEN*sizeof(char), input_filename_patten, path, source, param_filename_pattern);
	return_code = read_params( filename, ds.params);
	if ( return_code != 0 ) return return_code;
		
	snprintf(filename, MAX_STRING_LEN*sizeof(char), input_filename_patten, path, source, dem_filename_pattern);
	return_code = read_demography(filename, ds.params, ds.demography);
	if ( return_code != 0 ) return return_code;

	snprintf(filename, MAX_STRING_LEN*sizeof(char), input_filename_patten, path, source, censor_filename_pattern);
	return_code = read_censor(filename, ds.params, ds.censor);
	if ( return_code != 0 ) return return_code;

	snprintf(filename, MAX_STRING_LEN*sizeof(char), input_filename_patten, path, source, reg_filename_pattern);
	return_code = read_registry(filename, ds.registry);
	if ( return_code != 0 ) return return_code;
		
	snprintf(filename, MAX_STRING_LEN*sizeof(char), input_filename_patten, path, source, cbc_codes_filename_pattern);
	return_code = read_cbc_codes(filename, ds.cbc_codes);
	if ( return_code != 0 ) return return_code;
	
	snprintf(filename, MAX_STRING_LEN*sizeof(char), input_filename_patten, path, source, cbc_filename_pattern_bin);
	return_code = read_cbcs_bin( filename, ds.cbc_codes, ds.cbc);
	if ( return_code != 0 ) return return_code;
	
	return_code = convert_cbc_to_cbc_dates( ds.cbc, ds.cbc_dates_ex, ds.cbc_codes );
	if ( return_code != 0 ) return return_code;

	return_code = extra( ds );
	if ( return_code != 0 ) return return_code;
	
	validate_data_set( ds );

	return 0;
}

int cbc_codes_t::write (char *path) {

	FILE *fp = NULL;
	char file_name[MAX_STRING_LEN] ;
	sprintf(file_name,"%s/%s",path,cbc_codes_filename_pattern) ;

	fp = fopen(file_name, "w");
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for writingn", file_name) ;
		return -1 ;
	}

	fprintf(fp, "%s", text.c_str());
	
	fclose(fp) ;
	return 0 ;
}

int write_params( data_set_t &ds, char *path )
{
	FILE *fp = NULL;
	char file_name[MAX_STRING_LEN] ;
	sprintf(file_name,"%s/%s",path, param_filename_pattern) ;

	fp = fopen(file_name, "w");
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for writing\n", file_name) ;
		return -1 ;
	}
	fprintf(fp, "WHO SOURCE,%s\n", ds.source.c_str() );
	for( auto it = ds.params.begin(); it != ds.params.end(); it++ ) {
		fprintf(fp, "%s,%d\n", it->first.c_str(), it->second );
	}

	return 0;
}