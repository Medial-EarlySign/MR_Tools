#define _CRT_SECURE_NO_WARNINGS
#include "AnalyzeScores.h"
#include <random>
#include <ctime>
#include <iomanip>
#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/algorithm/string.hpp>

namespace po = boost::program_options;
boost::random::mt19937 rand_generator ;

std::minstd_rand randGen;

int time_unit_delays[] = {1,2,4} ;
int ntime_unit_delays = 3 ;

#define MAX_TIME_WINDOW 0

// Check validity of nbin_types value
int check_nbin_types_value(const int val) {
	if (val != 0 && val != 1 && val != 2) {
		fprintf(stderr,"Illeagal nbin-types %d\n", val) ;
	}

	return 0;
}
int extract_field_pos_from_header(FILE *fp, map <string, int> & pos, string pred_col) {
	char buffer[MAX_STRING_LEN];
	if (fgets(buffer, sizeof(buffer), fp) == NULL) {
		fprintf(stderr, "Could not read header line of file\n");
		return -1;
	}
	fprintf(stderr, "header line [%s]\n", buffer);
	vector<string> field_names;
	boost::split(field_names, buffer, boost::is_any_of(",\t\n\r")); 
	pos["id"] = -1;
	pos["date"] = -1;
	pos["outcome"] = -1;
	pos["outcome_date"] = -1;
	pos["pred"] = -1;

	for (int i = 0; i < field_names.size(); i++) {
		if (field_names[i] == "id" || field_names[i] == "pid")
			pos["id"] = i;
		else if (field_names[i] == "date" || field_names[i] == "time")
			pos["date"] = i;
		else if ((field_names[i] == "outcome") || (field_names[i] == "label"))
			pos["outcome"] = i;
		else if (field_names[i] == "outcomeTime" || field_names[i] == "outcome_date")
			pos["outcome_date"] = i;
		else if (pred_col == "" && (field_names[i] == "prediction" || field_names[i] == "pred"))
			pos["pred"] = i;
			
		if (pred_col != "" && field_names[i] == pred_col)
			pos["pred"] = i;
	}

	for (auto& e : pos) {
		if (e.second == -1) {
			fprintf(stderr, "header line does not contain [%s]\n", e.first.c_str());
			return -1;
		}
		else 
			fprintf(stderr, "header line contains [%s] at column [%d]\n", e.first.c_str(), e.second);
	}
		
	return 0;
}

// Read Scores File according to Inclusion/Exclusion lists
int read_scores(const char *file_name, map<string,vector<score_entry> >& scores, string& run_id, int nbin_types, map<string,periods>& include_list, map<string,periods>& remove_list,
	bool read_reg_from_scores, map<string, vector<pair<int, int> > >& registry, map<string, status>& censor, string pred_col) {

	fprintf(stderr, "Before Opening file [%s] for reading\n", file_name); fflush(stderr);
	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n", file_name) ;
		return -1 ;
	}

	fprintf(stderr, "Opened file [%s] for reading\n", file_name); fflush(stderr);

	// Read run-id
	char buffer[MAX_STRING_LEN] ;
	map <string, int> pos;
	if (read_reg_from_scores) {
		namespace pt = boost::posix_time;		
		run_id = file_name + pt::to_iso_string(pt::second_clock::local_time());
		if (extract_field_pos_from_header(fp, pos, pred_col) == -1)
			return -1;
		fprintf(stderr, "Extracted field_pos from header\n"); fflush(stderr);
	}
	else {
		if (fgets(buffer, sizeof(buffer), fp) == NULL) {
			fprintf(stderr, "Could not read header line of file \'%s\'\n", file_name);
			return -1;
		}

		if (feof(fp)) {
			fprintf(stderr, "Could not read run-id line from \'%s\'\n", file_name);
			return -1;
		}

		char *buffer_end = buffer;
		while ((*buffer_end != '\r') && (*buffer_end != '\n') && ((buffer_end - buffer) < (MAX_STRING_LEN - 1)))
			buffer_end++;
		*buffer_end = '\0';

		run_id = buffer;
	}
	fprintf(stderr,"RunId is \'%s\'\n",run_id.c_str()) ;

	char temp_id[MAX_STRING_LEN] ;
	int temp_date ;
	double temp_score ;
	int temp_bin = 0;
	int temp_eqsize_bin = 0 ;

	// Read scores
	int n = 0; int skipped_lines = 0;
	while (fgets(buffer, sizeof(buffer), fp)) {
		if (read_reg_from_scores) {
			int temp_outcome, temp_outcome_date;

			vector<string> fields;
			boost::split(fields, buffer, boost::is_any_of(",\t"));
			if (fields.size() < 5) {
				fprintf(stderr, "skipping line from [%s]. fields = %d, line = [%s]\n", file_name, int(fields.size()), buffer);
				if (skipped_lines++ > 10)
					return -1;
			}

			sprintf(temp_id, "%s", fields[pos["id"]].c_str());
			temp_date = stoi(fields[pos["date"]]);
			temp_score = stof(fields[pos["pred"]]);
			temp_outcome = stoi(fields[pos["outcome"]]);
			temp_outcome_date = stoi(fields[pos["outcome_date"]]);
			if (temp_outcome > 0) {
				if (temp_outcome_date >= 99999999) {
					fprintf(stderr, "temp_id [%s] temp_outcome [%d] temp_outcome_date [%d] >= 99999999\n",
						temp_id, temp_outcome, temp_outcome_date);
					return -1;
				}
					
				pair<int, int> entry(get_day(temp_outcome_date), 1);
				bool should_add = true;
				for (auto existing_entry : registry[temp_id])
					if (existing_entry == entry)
						should_add = false;
				if (should_add) {
					registry[temp_id].push_back(entry);
					if (registry.size() < 5)
						fprintf(stderr, "reg_size=%d id=[%s] outcome_date=[%d]\n", (int)registry.size(), temp_id, temp_outcome_date);
				}
			}
			if (temp_outcome == 0 && temp_outcome_date < 99999999) {
				if (censor.find(temp_id) != censor.end()) {
					if (censor[temp_id].days != get_day(temp_outcome_date)) {
						fprintf(stderr, "patient [%s] has 2 different outcome_dates [%d] and [%d]\n", temp_id, censor[temp_id].days, get_day(temp_outcome_date));
						return -1;
					}
				}
				else {
					status new_status;
					new_status.days = get_day(temp_outcome_date);
					new_status.reason = -1;
					new_status.stat = 2;
					censor[temp_id] = new_status;
					if (censor.size() < 5)
						fprintf(stderr, "censor_size=%d id=[%s] outcome_date=[%d]\n", (int)censor.size(), temp_id, temp_outcome_date);
				}
			}
				
		}
		else if (nbin_types == 0) {
			int rc = sscanf(buffer,"%s %d %lf\n",temp_id,&temp_date,&temp_score) ;
			if (rc == EOF)
				break ;

			if (rc < 3) {
				fprintf(stderr,"Could not read score line from \'%s\'. rc = %d\n",file_name,rc) ;
				return -1 ;
			}
		} else if (nbin_types == 1) {
			int rc = sscanf(buffer,"%s %d %lf %d\n",temp_id,&temp_date,&temp_score,&temp_bin) ;
			if (rc == EOF)
				break ;
	
			if (rc < 4) {
				fprintf(stderr,"Could not read score line from \'%s\'. rc = %d\n",file_name,rc) ;
				return -1 ;
			}
		} else if (nbin_types == 2) {
			int rc = sscanf(buffer,"%s %d %lf %d %d\n",temp_id,&temp_date,&temp_score,&temp_bin,&temp_eqsize_bin) ;
			if (rc == EOF)
				break ;
			if (rc < 5) {
				fprintf(stderr,"Could not read score line from \'%s\'. rc = %d\n",file_name,rc) ;
				return -1 ;
			}
		}

		// Filtering
		string id(temp_id) ;
		if (in_list(remove_list,id,temp_date) || (include_list.size() && ! in_list(include_list,id,temp_date)))
			continue ;

		score_entry new_entry ;
		new_entry.id = temp_id;
		new_entry.date = temp_date ;
		new_entry.days = get_day(temp_date) ;
		new_entry.year = temp_date/10000 ;
		new_entry.score = temp_score ;
		new_entry.bin = temp_bin ; 
		new_entry.eqsize_bin = temp_eqsize_bin ;
		scores[temp_id].push_back(new_entry) ;
		if (n++ < 5)
			fprintf(stderr, "n=%d id=[%s] date=[%d] score=%f\n", n, temp_id, temp_date, temp_score);
	}

	fprintf(stderr,"Read [%d] scores\n",n) ;
	if (read_reg_from_scores) {
		fprintf(stderr, "Added [%d] case patients to registry (according to their outcome_date)\n", (int)registry.size());
		fprintf(stderr, "Found [%d] control patients with outcome_date < 99999999 and added them to censor\n", (int)censor.size());
	}

	fclose(fp) ;
	return n ;
}

int in_list(map<string,periods>& list, string id, int date) {

	if (list.find(id) != list.end()) {
		for (unsigned int i=0; i<list[id].size(); i++) {
			if (date >= list[id][i].first && date <= list[id][i].second) {
				return 1 ;
			}
		}
	}

	return 0 ;
}

// Read bounds 
int read_bnds(const char *file_name, thresholds& bnds ,thresholds_autosim& bnds_autosim) {

	FILE *fp = fopen(file_name,"r");
	if (fp == NULL) {
		fprintf(stderr,"Could not open file\n") ;
		return -1 ;
	}

	int rc ;
	int min_age,max_age,min_days,max_days ;
	double score,sens,spec,earlysens1,earlysens2,earlysens3;

	char dummy[MAX_STRING_LEN] ;
	rc = fscanf(fp,"MinDays MaxDays MinAge  MaxAge  Score   TargetSens      %s",dummy) ;
	if (rc != 1 || strcmp(dummy,"TargetSpec") != 0) {
		fprintf(stderr,"Could not read header from \'%s\' (%d,%s)\n",file_name,rc,dummy) ;
		return -1 ;
	}

	while ((rc = fscanf(fp,"%d %d %d %d %lf %lf %lf\n",&min_days,&max_days,&min_age,&max_age,&score,&sens,&spec)) != EOF) {
		if (rc != 7) {
			fprintf(stderr,"Could not read line from \'%s\'\n",file_name) ;
			return -1 ;
		}

		pair<int,int> age_range(min_age,max_age) ;
		pair<int,int> time_window(min_days,max_days) ;
		target_bound bnd ;
		bnd.score = score ;
		bnd.sens = sens ;
		bnd.spec = spec ;
		cross_section entry(age_range,time_window) ;
		bnds[entry].push_back(bnd) ;
	}

	string fname_autosim = string(file_name)+".AutoSim";
	fp = fopen(fname_autosim.c_str(),"r");
	if (fp == NULL) {
		fprintf(stderr,"Could not open file  %s\n" , fname_autosim.c_str()) ;
		return -1 ;
	}

	rc = fscanf(fp,"MinAge	MaxAge	Score	TargetSens	TargetSpec	TargetEarlySens1	TargetEarlySens2	%s",dummy) ;
	if (rc != 1 || strcmp(dummy,"TargetEarlySens3") != 0) {
		fprintf(stderr,"Could not read header from \'%s\' (%d,%s)\n",fname_autosim.c_str(),rc,dummy) ;
		return -1 ;
	}

	while ((rc = fscanf(fp,"%d %d %lf %lf %lf %lf %lf %lf\n",&min_age,&max_age,&score,&sens,&spec,&earlysens1,&earlysens2,&earlysens3 )) != EOF) {
		if (rc != 8) {
			fprintf(stderr,"Could not read line from \'%s\'\n",fname_autosim.c_str()) ;
			return -1 ;
		}

		pair<int,int> age_range(min_age,max_age) ;
		target_bound_autosim bnd_autosim ;
		bnd_autosim.score = score ;
		bnd_autosim.sens = sens ;
		bnd_autosim.spec = spec ;
		bnd_autosim.earlysens1 = earlysens1 ;
		bnd_autosim.earlysens2 = earlysens2 ;
		bnd_autosim.earlysens3 = earlysens3 ;
		bnds_autosim[age_range].push_back(bnd_autosim) ;
	}




	return 0 ;
}

// Read Cancer Directions File : 
// Each cancer type has an indication: 
//		1. The cancer to predict
//		2. Cancer to exculde (irrespective of date)
//      3. Cancers to consider as healthy
int read_cancer_directions(const char *file_name, map<string,int>& cancer_directions) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open cancer directions from file \'%s\'\n", file_name) ;
		return -1 ;
	}

	char buffer[MAX_STRING_LEN] ;
	char *field_end ;

	while(!(feof(fp))) {      
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;

		// Identify Cancer
		field_end = buffer ;
		while ((*field_end != '\n') && (*field_end != '\r') && (*field_end != '\t'))
			field_end ++ ;

		if (*field_end != '\t') {
			fprintf(stderr,"Cannot parse line \'%s\'\n",buffer) ;
			return -1 ;
		}

		*field_end = '\0' ;
		string cancer = buffer ;

		// Read direction
		field_end ++ ;
		int direction = atoi(field_end) ;
		if (direction < 1 || direction > 3) {
			fprintf(stderr,"Unknown direction %s\n",field_end) ;
			return -1 ;
		}

		cancer_directions[cancer] = direction ;
		if (direction == 1)
			fprintf(stderr,"Predicting: %s\n",cancer.c_str()) ;

	}

	int n = (int) cancer_directions.size() ;
	fprintf(stderr,"Read directions for %d types of cancer\n",n) ;
	
	fclose(fp) ;
	return n ;
}

void read_simple_registry(const char *file_name, map<string, vector<pair<int, int> > >& registry) {
	fprintf(stderr, "reading %s and expecting pid,event_date format\n", file_name);
	ifstream inf(file_name);
	if (!inf.is_open()) {
		fprintf(stderr, "Cannot open %s for reading\n", file_name);
		throw new exception();
	}
	char s[1000];
	inf.getline(s, 1000); // skip the header
	fprintf(stderr, "found header: %s\n", s);
	int pid,cancer_date;
	char delim;
	while (!inf.eof()) {
		inf >> pid >> delim >> cancer_date;
		inf.ignore(10000, '\n');
		pair<int, int> entry(get_day(cancer_date), 1);
		registry[std::to_string(pid)].push_back(entry);
	}

	int n = (int)registry.size();
	fprintf(stderr, "Read cancer registry for %d ids\n", n);

	inf.close();
}

// Read Cancer Registry
int read_cancer_registry(const char *file_name, map<string,int>& cancer_directions , map<string,vector<pair<int,int> > >& registry ) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file\n") ;
		return -1 ;
	}

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
		for( ;  ;  ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == '\t')) {
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

		if (strcmp(line[0],"NR") != 0) {
			char cancer_type[MAX_STRING_LEN] ;
			sprintf(cancer_type,"%s",line[2]) ;

			if (cancer_directions.find(cancer_type) == cancer_directions.end()) {
				fprintf(stderr,"Adding default cancer direction %d to \'%s\'\n",DEF_CANCER_DIR,cancer_type) ;
				cancer_directions[cancer_type] = DEF_CANCER_DIR ;
			}

			int date ;
			if (sscanf(line[1],"%d",&date) != 1) {
				fprintf(stderr,"Could not parse date %s\n",line[1]) ;
				return -1 ;
			}

			pair<int,int> entry(get_day(date) , cancer_directions[cancer_type]) ;
			registry[line[0]].push_back(entry) ;
		}
	}

	int n = (int) registry.size() ;
	fprintf(stderr,"Read cancer registry for %d ids\n",n) ;
	
	fclose(fp) ;
	return n ;
}

int read_mhs_cancer_registry(const char *file_name, map<string,int>& cancer_directions , map<string,vector<pair<int,int> > >& registry ) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file\n") ;
		return -1 ;
	}

	char buffer[BUFFER_SIZE] ;
	char field[MAX_STRING_LEN] ;
	char line[MHS_REGISTRY_NFIELDS][MAX_STRING_LEN] ;
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
				if (ifield > MHS_REGISTRY_NFIELDS) {
					fprintf(stderr,"Could not read file, ifield=%d\n", ifield) ;
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

		if (strcmp(line[0],"NUMERATOR") != 0) {
			char cancer_type[MAX_STRING_LEN] ;
			sprintf(cancer_type,"%s,%s,%s",line[MHS_REGISTRY_CANCER_FIELD],line[MHS_REGISTRY_CANCER_FIELD+1],line[MHS_REGISTRY_CANCER_FIELD+2]) ;

			if (cancer_directions.find(cancer_type) == cancer_directions.end()) {
				fprintf(stderr,"Adding default cancer direction %d to \'%s\'\n",DEF_CANCER_DIR,cancer_type) ;
				cancer_directions[cancer_type] = DEF_CANCER_DIR ;
			}

			int day,month,year ;
			if (sscanf(line[MHS_REGISTRY_DATE_FIELD],"%d/%d/%d",&month,&day,&year) != 3) {
				fprintf(stderr,"Could not parse date %s\n",line[MHS_REGISTRY_DATE_FIELD]) ;
				return -1 ;
			}

			pair<int,int> entry(get_day(day + 100*month + 10000*year) , cancer_directions[cancer_type]) ;
			registry[line[MHS_REGISTRY_ID_FIELD]].push_back(entry) ;
		}
	}

	int n = (int) registry.size() ;
	fprintf(stderr,"Read MHS cancer registry for %d ids\n",n) ;
	
	fclose(fp) ;
	return n ;
}

// Read Extra Parameters
int read_extra_params(const char *file_name, vector<pair<int,int> >& time_windows, vector<pair<int,int> >& age_ranges, int *first_date, int *last_date, int *age_seg_num,
					  int *max_status_year) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file for reading\n") ;
		return -1 ;
	}

	char buffer[BUFFER_SIZE] ;
	char line[EXTRA_PARAMS_MAX_FIELDS][MAX_STRING_LEN] ;
	char field[MAX_STRING_LEN] ;
	char *startbuf,*endbuf ;
	*last_date = -1 ;
	*first_date = -1 ;
	*age_seg_num = -1 ;
	*max_status_year = -1 ;

	while(!(feof(fp))) {      
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;
			                
		startbuf = endbuf = buffer; 
		int ifield = 0 ;
		for( ;  ;  ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == '\t') || (*endbuf == ' ')) {
				strncpy(field, startbuf, endbuf-startbuf);                     
				field[endbuf-startbuf]='\0';

				ifield++ ;
				if (ifield > EXTRA_PARAMS_MAX_FIELDS) {
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

		if (strcmp(line[0],"TimeWindow") == 0) {
			if (ifield != 3) {
				fprintf(stderr,"Could not read TimeWindows line with %d entries\n",ifield) ;
				return -1 ;
			}

			pair<int,int> window(atoi(line[1]),atoi(line[2])) ;
			time_windows.push_back(window) ;
		} else if (strcmp(line[0],"LastDate") == 0) {
			if (ifield != 2) {
				fprintf(stderr,"Could not read LastDate line with %d entries\n",ifield) ;
				return -1 ;
			}

			if (*last_date != -1) {
				fprintf(stderr,"Could not read LastDate information from file\n") ;
				return -1 ;
			}

			*last_date = atoi(line[1]) ;
		} else if (strcmp(line[0],"FirstDate") == 0) {
			if (ifield != 2) {
				fprintf(stderr,"Could not read FirstDate line with %d entries\n",ifield) ;
				return -1 ;
			}

			if (*first_date != -1) {
				fprintf(stderr,"Could not read FirstDate information from file\n") ;
				return -1 ;
			}

			*first_date = atoi(line[1]) ;
		} else if (strcmp(line[0],"AgeRange") == 0) {
			if (ifield != 3) {
				fprintf(stderr,"Could not read AgeRange line with %d entries\n",ifield) ;
				return -1 ;
			}
			pair<int,int> range(atoi(line[1]),atoi(line[2])) ;
			age_ranges.push_back(range) ;
		} else if (strcmp(line[0],"AgeSegNum") == 0) {
			if (ifield != 2) {
				fprintf(stderr,"Could not read AgeSegNum line with %d entries\n",ifield) ;
				return -1 ;
			}

			if (*age_seg_num != -1) {
				fprintf(stderr,"Could not read AgeSegNum information from file\n") ;
				return -1 ;
			}

			*age_seg_num = atoi(line[1]) ;
			if (*age_seg_num < 1) {
				fprintf(stderr,"Could not read AgeSegNum information from file\n") ;
				return -1 ;
			}
		} else if (strcmp(line[0],"MaxStatusYear") == 0) {
			fprintf(stderr, "WARN: MaxStatusYear is deprecated and not used in our code anymore\n");
			if (ifield != 2) {
				fprintf(stderr,"Could not read MaxStatusYear line with %d entries\n",ifield) ;
				return -1 ;
			}

			if (*max_status_year != -1) {
				fprintf(stderr,"Could not read MaxStatusYear information from file\n") ;
				return -1 ;
			}

			*max_status_year = atoi(line[1]) ;
			if (*max_status_year < 1) {
				fprintf(stderr,"Could not read MaxStatusYear information from file\n") ;
				return -1 ;
			}
		} else {
			fprintf(stderr,"Could not recognize parameter-name \'%s\'\n",line[0]) ;
			return -1 ;
		}
	}

	if (*last_date == -1) {
		fprintf(stderr,"Could not find LastDate in parameters-file\n") ;
		return -1 ;
	}

	if (*first_date == -1){
		fprintf(stderr, "Could not find FirstDate in parameters-file\n");
		return -1;
	}

	if (*age_seg_num == -1)
		*age_seg_num = N_AGE_SEGS ;

	if (*max_status_year == -1)
		*max_status_year = MAX_STATUS_YEAR ;

	int n = (int) time_windows.size() ;
	fprintf(stderr,"Read %d time-windows\n",n) ;

	int m = (int) age_ranges.size() ;
	fprintf(stderr,"Read %d age-ranges\n",m) ;
	
	fclose(fp) ;
	return m*n ;
}

// Read Extra Parameters
int read_extra_params_for_oxford(const char *file_name, vector<pair<int, int> >& time_windows, vector<pair<int, int> >& age_ranges, int *age_seg_num) {

	FILE *fp = fopen(file_name, "r");
	if (fp == NULL) {
		fprintf(stderr, "Could not open file for reading\n");
		return -1;
	}

	char buffer[BUFFER_SIZE];
	char line[EXTRA_PARAMS_MAX_FIELDS][MAX_STRING_LEN];
	char field[MAX_STRING_LEN];
	char *startbuf, *endbuf;
	*age_seg_num = -1;

	while (!(feof(fp))) {
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break;

		startbuf = endbuf = buffer;
		int ifield = 0;
		for (; ; ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == '\t') || (*endbuf == ' ')) {
				strncpy(field, startbuf, endbuf - startbuf);
				field[endbuf - startbuf] = '\0';

				ifield++;
				if (ifield > EXTRA_PARAMS_MAX_FIELDS) {
					fprintf(stderr, "Could not read file\n");
					return -1;
				}

				strncpy(line[ifield - 1], field, MAX_STRING_LEN);
				line[ifield - 1][MAX_STRING_LEN - 1] = '\0';
				startbuf = endbuf + 1;
			}

			if ((*endbuf == '\n') || (*endbuf == '\r'))
				break;
			endbuf++;
		}

		if (strcmp(line[0], "TimeWindow") == 0) {
			if (ifield != 3) {
				fprintf(stderr, "Could not read TimeWindows line with %d entries\n", ifield);
				return -1;
			}

			pair<int, int> window(atoi(line[1]), atoi(line[2]));
			time_windows.push_back(window);
		}

		else if (strcmp(line[0], "AgeRange") == 0) {
			if (ifield != 3) {
				fprintf(stderr, "Could not read AgeRange line with %d entries\n", ifield);
				return -1;
			}
			pair<int, int> range(atoi(line[1]), atoi(line[2]));
			age_ranges.push_back(range);
		}
		else if (strcmp(line[0], "AgeSegNum") == 0) {
			if (ifield != 2) {
				fprintf(stderr, "Could not read AgeSegNum line with %d entries\n", ifield);
				return -1;
			}

			if (*age_seg_num != -1) {
				fprintf(stderr, "Could not read AgeSegNum information from file\n");
				return -1;
			}

			*age_seg_num = atoi(line[1]);
			if (*age_seg_num < 1) {
				fprintf(stderr, "Could not read AgeSegNum information from file\n");
				return -1;
			}
		}
		else {
			fprintf(stderr, "Could not recognize parameter-name \'%s\'\n", line[0]);
			return -1;
		}
	}

	if (*age_seg_num == -1)
		*age_seg_num = N_AGE_SEGS;

	int n = (int)time_windows.size();
	fprintf(stderr, "Read %d time-windows\n", n);

	int m = (int)age_ranges.size();
	fprintf(stderr, "Read %d age-ranges\n", m);

	fclose(fp);
	return m*n;
}


int read_extra_params(const char *file_name, vector<pair<int,int> >& initialization_dates, vector<pair<int,int> >& age_ranges, int *last_date, int *max_status_year) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file for reading\n") ;
		return -1 ;
	}

	char buffer[BUFFER_SIZE] ;
	char line[EXTRA_PARAMS_MAX_FIELDS][MAX_STRING_LEN] ;
	char field[MAX_STRING_LEN] ;
	char *startbuf,*endbuf ;
	*last_date = -1 ;
	*max_status_year = -1 ;

	while(!(feof(fp))) {      
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;
			                
		startbuf = endbuf = buffer; 
		int ifield = 0 ;
		for( ;  ;  ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == '\t') || (*endbuf == ' ')) {
				strncpy(field, startbuf, endbuf-startbuf);                     
				field[endbuf-startbuf]='\0';

				ifield++ ;
				if (ifield > EXTRA_PARAMS_MAX_FIELDS) {
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

		if (strcmp(line[0],"InitDates") == 0) {
			if (ifield != 3) {
				fprintf(stderr,"Could not read InitDates line with %d entries\n",ifield) ;
				return -1 ;
			}

			pair<int,int> window(atoi(line[1]),atoi(line[2])) ;
			initialization_dates.push_back(window) ;
		} else if (strcmp(line[0],"LastDate") == 0) {
			if (ifield != 2) {
				fprintf(stderr,"Could not read LastDate line with %d entries\n",ifield) ;
				return -1 ;
			}

			if (*last_date != -1) {
				fprintf(stderr,"Could not read LastDate information from file\n") ;
				return -1 ;
			}

			*last_date = atoi(line[1]) ;
		} else if (strcmp(line[0],"AgeRange") == 0) {
			if (ifield != 3) {
				fprintf(stderr,"Could not read AgeRange line with %d entries\n",ifield) ;
				return -1 ;
			}
			pair<int,int> range(atoi(line[1]),atoi(line[2])) ;
			age_ranges.push_back(range) ;
		} else if (strcmp(line[0],"MaxStatusYear") == 0) {
			if (ifield != 2) {
				fprintf(stderr,"Could not read MaxStatusYear line with %d entries\n",ifield) ;
				return -1 ;
			}

			if (*max_status_year != -1) {
				fprintf(stderr,"Could not read MaxStatusYear information from file\n") ;
				return -1 ;
			}

			*max_status_year = atoi(line[1]) ;
			if (*max_status_year < 1) {
				fprintf(stderr,"Could not read MaxStatusYear information from file\n") ;
				return -1 ;
			}
		} else {
			fprintf(stderr,"Could not recognize parameter-name \'%s\'\n",line[0]) ;
			return -1 ;
		}
	}

	if (*last_date == -1) {
		fprintf(stderr,"Could not find LastDate in parameters-file\n") ;
		return -1 ;
	}


	if (*max_status_year == -1)
		*max_status_year = MAX_STATUS_YEAR ;

	int n = (int) initialization_dates.size() ;
	fprintf(stderr,"Read %d init-dates\n",n) ;

	int m = (int) age_ranges.size() ;
	fprintf(stderr,"Read %d age-ranges\n",m) ;
	
	fclose(fp) ;
	return m*n ;
}

// Read censoring File
int read_censor(const char *file_name, map<string,status>& censor) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	// Read status
	char id[MAX_STRING_LEN] ;
	int date,stat,reason ;
	int already_censored = 0, status_other_than_2 = 0;
	fprintf(stderr, "Reading censor data from [%s] will handle only entries with status == 2 (DEATH/LEFT)\n", file_name);
	while (! feof(fp)) {
		int rc = fscanf(fp,"%s %d %d %d\n",id,&stat,&reason,&date) ;
		if (rc == EOF)
			break ;

		if (rc != 4) {
			fprintf(stderr,"Could not read status line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}
		if (censor.find(id) != censor.end() && censor[id].days < get_day(date)) {
			already_censored++;
			continue; // already censored before 
		}
		status new_status;
		if (stat == 2) {
			new_status.days = get_day(date);
			new_status.reason = reason;
			new_status.stat = stat;
			censor[id] = new_status;
		}
		else status_other_than_2++;
	}

	int n = (int) censor.size() ;
	fprintf(stderr,"Read [%d] censoring entries with status == 2 (DEATH/LEFT)\n",n) ;
	fprintf(stderr, "Ignored [%d] already censored entries\n", already_censored);
	fprintf(stderr, "Ignored [%d] entries with status != 2\n", status_other_than_2);

	fclose(fp) ;
	return n ;
}

// Read Incidence File
int read_probs(const char *file_name, map<int,double>& indicence_rate) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	// skip first three lines, just verifying correct format
	int rc;
	int d, n;
	float f;

	rc = fscanf(fp, "KeySize %d\n", &d) ;
	if (rc != 1 || d != 1) {
		fprintf(stderr,"Could not read first incidence line from \'%s\'. rc = %d\n",file_name,rc) ;
		return -1 ;
	}

	rc = fscanf(fp, "Nkeys %d\n", &n) ;
	if (rc != 1) {
		fprintf(stderr,"Could not read second incidence line from \'%s\'. rc = %d\n",file_name,rc) ;
		return -1 ;
	}

	rc = fscanf(fp, "%f\n", &f) ;
	if (rc != 1 || f != 1.0) {
		fprintf(stderr,"Could not read third incidence line from \'%s\'. rc = %d\n",file_name,rc) ;
		return -1 ;
	}

	// Read indicdence rate per age
	int age, num_case, num_ctrl ;
	double prob ;
	while (! feof(fp)) {
		int rc = fscanf(fp,"%d %d %d\n", &age, &num_case, &num_ctrl) ;
		if (rc == EOF)
			break ;

		if (rc != 3) {
			fprintf(stderr,"Could not read incidence line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		prob = (num_case + 0.0) / (num_case + num_ctrl) ;
		if (indicence_rate.find(age) != indicence_rate.end()) {
			fprintf(stderr,"Incidence rate for age %d given more than once in \'%s\'\n",age,file_name) ;
			return -1 ;
		}

		indicence_rate[age] = prob ;
	}

	fclose(fp) ;
	return 0 ;
}

// Read Removal File
int read_remove(const char *file_name, map<string,int>& remove_list) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	// Read list
	char id[MAX_STRING_LEN] ;

	while (! feof(fp)) {
		int rc = fscanf(fp,"%s\n",id) ;
		if (rc == EOF)
			break ;

		if (rc != 1) {
			fprintf(stderr,"Could not read removal line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		remove_list[id] = 1 ;
	}

	int n = (int) remove_list.size() ;
	fprintf(stderr,"Read %d ids in remove file\n",n) ;

	fclose(fp) ;
	return n ;
}

// Read periods of inclusion/exclusions
int read_list(const char *file_name, map<string,periods>& list) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}
	// Read list
	char buffer[MAX_STRING_LEN] ;
	char field[MAX_STRING_LEN] ;

	char *startbuf,*endbuf ;

	while(!(feof(fp))) {      
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;
			       
		startbuf = buffer;             
		endbuf = buffer;

		// Name
		while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != '\t'))
			*endbuf ++ ;

		if (endbuf - startbuf > MAX_STRING_LEN - 1)
			return -1 ;

		strncpy(field,startbuf, endbuf-startbuf);                     
		field[endbuf-startbuf]='\0';
		string id = field ;

		if (*endbuf != '\t') { // Only ID
			pair<int, int> period(0,99991231) ;
			list[id].push_back(period) ;
			continue ;
		}

		startbuf= ++endbuf ;

		// First Value
		while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != '\t'))
			*endbuf ++ ;

		if (endbuf - startbuf > MAX_STRING_LEN - 1)
			return -1 ;
		
		strncpy(field,startbuf, endbuf-startbuf);                     
		field[endbuf-startbuf]='\0';
		int from = atoi(field) ;

		if (*endbuf != '\t') { // Only ID + Date
			pair<int, int> period(from,from) ;
			list[id].push_back(period) ;
			continue ;
		}

		startbuf= ++endbuf ;

		// Second Value
		while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != '\t'))
			*endbuf ++ ;

		if (((*endbuf != '\r') && (*endbuf != '\n')) || endbuf - startbuf > MAX_STRING_LEN - 1)
			return -1 ;

		strncpy(field,startbuf, endbuf-startbuf);                     
		field[endbuf-startbuf]='\0';
		int to = atoi(field) ;

		// ID + From + To
		pair<int, int> period(from,to) ;
		list[id].push_back(period) ;
	}

	int n = (int)  list.size() ;
	fprintf(stderr,"Read include/exclude periods for %d ids from file \'%s\'\n",n, file_name) ;

	fclose(fp) ;
	return n ;
}

// Read list for inclusion from scores file
int read_list_from_scores(const char *file_name, int nbin_types, map<string,periods>& list, bool read_reg_from_scores, 
	map<string, vector<pair<int, int> > >& registry, map<string, status>& censor, string pred_col) {

	map<string,vector<score_entry> > all_inc_preds ;
	string dummy_run_id ;
	map<string, periods> dummy_remove_list ;
	map<string, periods> dummy_include_list ;

	int nscores_inc_preds = read_scores(file_name, all_inc_preds, dummy_run_id,nbin_types,dummy_include_list, dummy_remove_list, read_reg_from_scores,
		registry, censor, pred_col) ;
	if (nscores_inc_preds == -1) {
		fprintf(stderr, "Could not read scores from file \'%s\'\n", file_name) ;
		return -1 ;
	}

	for (auto it = all_inc_preds.begin(); it != all_inc_preds.end(); ++it) {
		vector<score_entry>& v = it->second;
		for (auto iv = v.begin(); iv != v.end(); ++iv) {
			pair<int, int> period(iv->date, iv->date);
			list[it->first].push_back(period);
		}
	}

	return 0 ;
}

// Read Birth Years File
int read_byears(const char *file_name, map<string,int>& byear) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	// Read byears
	char temp_id[MAX_STRING_LEN] ;
	int temp_year ;

	while (! feof(fp)) {
		int rc = fscanf(fp,"%s %d\n",temp_id,&temp_year) ;
		if (rc == EOF)
			break ;

		if (rc != 2) {
			fprintf(stderr,"Could not read byear line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		byear[temp_id] = temp_year ;
	}

	int n = (int) byear.size() ;
	fprintf(stderr,"Read %d birth-years\n",n) ;

	fclose(fp) ;
	return n ;
}

// Read all input in Oxford format 
int read_oxford_input(const char *file_name, string& req_gender, input_data& indata) {

	FILE *fp = fopen(file_name, "r");
	if (fp == NULL) {
		fprintf(stderr, "Could not open file \'%s\' for reading\n", file_name);
		return -1;
	}

	// Read run-id
	char buffer[MAX_STRING_LEN];
	if (fgets(buffer, sizeof(buffer), fp) == NULL) {
		fprintf(stderr, "Could not read header line of file \'%s\'\n", file_name);
		return -1;
	}

	if (feof(fp)) {
		fprintf(stderr, "Could not read run-id line from \'%s\'\n", file_name);
		return -1;
	}

	char *buffer_end = buffer;
	while ((*buffer_end != '\r') && (*buffer_end != '\n') && ((buffer_end - buffer) < (MAX_STRING_LEN - 1)))
		buffer_end++;
	*buffer_end = '\0';

	indata.run_id = buffer;
	fprintf(stderr, "Header is \'%s\'\n", indata.run_id.c_str());

	// Read
	char field[MAX_STRING_LEN];
	char line[OXFORD_NFIELDS][MAX_STRING_LEN];
	char *startbuf, *endbuf;
	int n = 0;

	while (!(feof(fp))) {
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break;

		startbuf = endbuf = buffer;
		int ifield = 0;
		for (; ; ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == ',')) {
				strncpy(field, startbuf, endbuf - startbuf);
				field[endbuf - startbuf] = '\0';

				ifield++;
				if (ifield > OXFORD_NFIELDS) {
					fprintf(stderr, "Could not parse line %s from file %s\n", buffer, file_name);
					return -1;
				}

				strncpy(line[ifield - 1], field, MAX_STRING_LEN);
				line[ifield - 1][MAX_STRING_LEN - 1] = '\0';
				startbuf = endbuf + 1;
			}

			if ((*endbuf == '\n') || (*endbuf == '\r'))
				break;
			endbuf++;
		}

		if (ifield != OXFORD_NFIELDS) {
			fprintf(stderr, "Could not parse line %s from file %s\n", buffer, file_name);
			return -1;
		}

		//gender
		if (req_gender != "C" && string(line[4]) != req_gender)
			continue;

		// id
		score_entry new_entry;
		string id = line[0];
		new_entry.id = line[0];

		// score
		if (sscanf(line[1], "%lf", &(new_entry.score)) != 1) {
			fprintf(stderr, "Could not parse line %s from file %s\n", buffer, file_name);
			return -1;
		}
		new_entry.bin = 0;
		new_entry.eqsize_bin = 0;

		// scoring date
		if ((new_entry.date = getOxfordDate(line[2])) == -1) {
			fprintf(stderr, "Could not parse line %s from file %s\n", buffer, file_name);
			return -1;
		}
		new_entry.days = get_day(new_entry.date);
		new_entry.year = new_entry.date / 10000;

		indata.all_scores[id].push_back(new_entry);

		// birth year
		if (sscanf(line[3], "%d", &(indata.byears[id])) != 1) {
			fprintf(stderr, "Could not parse line %s from file %s\n", buffer, file_name);
			return -1;
		}

		// CRC flag
		int crcFlag = 0;
		if (strcmp(line[7], "1") == 0) {
			pair<int, int> entry(get_day(getOxfordDate(line[6])), 1);
			indata.registry[id].push_back(entry);
			crcFlag = 1;
		}

		// Censoring
		status new_status;
		if (crcFlag) {
			// Use start date
			new_status.days = get_day(getOxfordDate(line[5]));
			new_status.reason = 1;
			new_status.stat = 1;
		}
		else {
			// Use end date
			new_status.days = get_day(getOxfordDate(line[6]));
			new_status.reason = 2;
			new_status.stat = 8;
		}
		indata.censor[id] = new_status;

		n++;
	}

	fprintf(stderr, "Read %d lines\n", n);
	fclose(fp);

	return n;
}

int getOxfordDate(char *sdate) {

	int dd, mm, yyyy;
	if (sscanf(sdate, "%2d/%2d/%4d", &dd, &mm, &yyyy) != 3)
		return -1;

	return dd + 100 * mm + 10000 * yyyy;
}

int collect_all_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date,  int first_date,
					   pair<int,int> &time_window, pair<int, int>& age_range, 
					   map<string,int>& byears, map<string, status>& censor,
					   vector<string>& idstrs, int *dates, int *days, int *years, double *scores, int *ages,
					   int *id_starts, int *id_nums, int *types, int *nids, int *checksum) {

	*checksum = 0 ;
	int iscore = 0 ;
	idstrs.clear() ;
	*nids = 0 ;

	int last_days = get_day(last_date) ;
	int first_days = get_day(first_date) ;

	for (auto it = all_scores.begin(); it != all_scores.end(); it++) {

		string id = it->first ;

		// Identify type and last-date
		int type = 0 ;

		// only for healthy - take a safety buffer from the registry last day, so we'll never consider a patient healthy by mistake
		int last_allowed = last_days - time_window.second; 
		// add some more patients - we can add patients from before the first day of the registry if time window does not begin in 0
		int first_allowed = first_days - time_window.first;

		// only for healthy - take a safety buffer from death/leaving primary care
		if (censor.find(id) != censor.end() && censor[id].days < last_allowed && censor[id].stat == 2)
			last_allowed = censor[id].days - time_window.second;

		int first_cancer_day = get_day(99991231);
		if (registry.find(id) != registry.end()) {

			// registry[id][i].first holds the date of record in registry
			// registry[id][i].second holds cancer type listed in registry
			for (unsigned int i=0; i<registry[id].size(); i++) {
				if (registry[id][i].second == 2 && registry[id][i].first < first_cancer_day) {
					type = 2 ;
					first_cancer_day = registry[id][i].first ;
				} else if (registry[id][i].second == 1 && registry[id][i].first < first_cancer_day) {
					type = 1 ;
					first_cancer_day = registry[id][i].first ;
				// cases when directions file has cancers to be treated as controls (using flag '3')
				} else if (registry[id][i].second == 3 && registry[id][i].first < first_cancer_day) {
					type = 0;
					first_cancer_day = registry[id][i].first + MAX_TIME_WINDOW;
				}
			}
			// If sick - override last allowed day 
			if (first_cancer_day < get_day(99991231))
				last_allowed = first_cancer_day;
		}

		// Collect all relevant scores
		int found_score = 0 ;
		types[*nids] = type ;
		id_starts[*nids] = iscore ;
		id_nums[*nids] = 0 ;

		for (unsigned int i=0; i<all_scores[id].size(); i++) {
			int current_days = all_scores[id][i].days ;
			//fprintf(stderr, "DEBUG: id= %s date= %d cur_days= %d,first_allowed= %d, last_allowed= %d\n",
			//	id.c_str(), dates[iscore], current_days, first_allowed, last_allowed);
			if (current_days >= first_allowed && current_days <= last_allowed - MAX_TIME_WINDOW &&
				((type == 1 && current_days >= first_cancer_day - time_window.second && current_days <= first_cancer_day - time_window.first) || (type == 0))) {
				if (byears.find(id) == byears.end()) {
					fprintf(stderr,"Cannot find birth year for ID [%s]\n",id.c_str()) ;
					return -1 ;
				}

				int age = all_scores[id][i].year - byears[id] ;
				if (age >= age_range.first && age <= age_range.second) {
					(*checksum) = ((*checksum) + current_days) & 0xFFFF ;
					for (unsigned int j=0; j< id.length(); j++)
						(*checksum) = ((*checksum) + id[j]) & 0xFFFF ;

					found_score = 1 ;
					id_nums[*nids] ++ ;
					idstrs.push_back(all_scores[id][i].id) ;
					dates[iscore] = all_scores[id][i].date ;
					days[iscore] = current_days ;
					scores[iscore] = all_scores[id][i].score ;
					years[iscore] = all_scores[id][i].year ;
					ages[iscore] = age ;

					//fprintf(stderr, "DEBUG: id= %s age= %d score= %f date= %d type= %d win=%d-%d cur_days= %d,curr_days_dbg= %d, last_allowed=%d\n",
					// 	id.c_str(), age, scores[iscore], dates[iscore], type, time_window.first, time_window.second, current_days, all_scores[id][i].days, last_allowed);

					iscore ++ ;					
				}
			}

		}

		if (found_score)
			(*nids) ++ ;
	}

	return 0 ;
}

int collect_all_autosim_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date, int first_date,
					   pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor, vector<string>& idstrs, int *dates, int *days, int *years, double *scores, 
					   int *gaps, int *id_starts, int *id_nums, int *types, int *nids, int *checksum) {

	*checksum = 0 ;
	int iscore = 0 ;
	idstrs.clear() ; 
	*nids = 0 ;

	int first_days = get_day(first_date) ;
	int last_days = get_day(last_date) ;

	for (auto it = all_scores.begin(); it != all_scores.end(); it++) {
		string id = it->first ;

		// Identify type and and last-date
		int type = 0 ;

		// Note: last_days is fed from params.txt as LastDate. We ignore scores beyond this date. 
		// it is considered a good practice to use LastDate = max(cancer_registration_date) - 2 years. 
		// this way we can be sure healthy people are really healthy. 
		int last_allowed = last_days ;
		int first_cancer_day = get_day(99991231);

		if (registry.find(id) != registry.end()) {
			for (unsigned int i=0; i<registry[id].size(); i++) {
				if (registry[id][i].second == 2 && registry[id][i].first < first_cancer_day) {
					type = 2 ;
					first_cancer_day = registry[id][i].first ;
				} else if (registry[id][i].second == 1 && registry[id][i].first < first_cancer_day) {
					type = 1 ;
					first_cancer_day = registry[id][i].first ;
				} else if (registry[id][i].second == 3 && registry[id][i].first < first_cancer_day) {
					type = 0 ;
					first_cancer_day = registry[id][i].first ;
				}
			}
			if (first_cancer_day < last_allowed)
				last_allowed = first_cancer_day;
		}

		// Control
		// For control cases (no cancer registered) we take the max score per patient, if it passes the threshold, that would be counted as a false positive
		if (type == 0) {
			int last_allowed = last_days ; 
			if (censor.find(id) != censor.end() && censor[id].days < last_allowed && censor[id].stat == 2)
				last_allowed = censor[id].days ;

			double max_score ; 
			int max_score_index = -1 ;
			if (all_scores.find(id) != all_scores.end()) {
				for (unsigned int i=0; i<all_scores[id].size(); i++) {

					if (all_scores[id][i].days >= first_days && all_scores[id][i].days <= last_allowed) {
						if (byears.find(id) == byears.end()) {
							fprintf(stderr,"Cannot find birth year for ID [%s]\n",id.c_str()) ;
							return -1 ;
						}

						int age = all_scores[id][i].year - byears[id] ;
						if (age >= age_range.first && age <= age_range.second) {
							
							(*checksum) = ((*checksum) + all_scores[id][i].days) & 0xFFFF ;
							for (unsigned int j=0; j< id.length(); j++)
								(*checksum) = ((*checksum) + id[j]) & 0xFFFF ;
							
							if (max_score_index==-1 || all_scores[id][i].score > max_score) {
								max_score = all_scores[id][i].score ;
								max_score_index = i ;
							}
						}
					}
				}
			}

			if (max_score_index != -1) {
				id_nums[*nids] = 1 ;
				types[*nids] = 0 ;
				id_starts[*nids] = iscore ;
				idstrs.push_back(all_scores[id][max_score_index].id) ;
				dates[iscore] = all_scores[id][max_score_index].date;
				days[iscore] = all_scores[id][max_score_index].days ;
				scores[iscore] = all_scores[id][max_score_index].score ;
				years[iscore] = all_scores[id][max_score_index].year ;
				gaps[iscore] = -1 ;

				iscore ++ ;
				(*nids) ++ ;
			}
		} else if (type == 1) { // Case
			vector<pair<int,double> > id_scores ;
			for (unsigned int i=0; i<all_scores[id].size(); i++) {
				if (all_scores[id][i].days >= first_days && all_scores[id][i].days <= last_allowed) {
					if (byears.find(id) == byears.end()) {
						fprintf(stderr,"Cannot find birth year for ID [%s]\n",id.c_str()) ;
						return -1 ;
					}
					int age = all_scores[id][i].year - byears[id] ;

					if (age >= age_range.first && age <= age_range.second) {
						pair<int,double> current_score(i,all_scores[id][i].score) ;
						id_scores.push_back(current_score) ;

						(*checksum) = ((*checksum) + all_scores[id][i].days) & 0xFFFF ;
						for (unsigned int j=0; j< id.length(); j++)
							(*checksum) = ((*checksum) + id[j]) & 0xFFFF ;
					}
				}
			}
				
			if (id_scores.size()) {
				id_nums[*nids] = 0 ;
				types[*nids] = 1 ;
				id_starts[*nids] = iscore ;

				// for 2 scores of the same patient such that a > b we make sure that a is later than b! (for the same cancerous patient we make sure score is monotonic rising)
				sort(id_scores.begin(),id_scores.end(),rev_compare_pairs()) ;
				for (unsigned int i=0; i<id_scores.size(); i++) {
					if (i==0 || all_scores[id][id_scores[i].first].days < days[iscore-1]) {
						idstrs.push_back(all_scores[id][id_scores[i].first].id) ;
						dates[iscore] = all_scores[id][id_scores[i].first].date ;
						days[iscore] = all_scores[id][id_scores[i].first].days ;
						scores[iscore] = all_scores[id][id_scores[i].first].score ;
						years[iscore] = all_scores[id][id_scores[i].first].year ;
						gaps[iscore] = first_cancer_day - days[iscore] ;
						id_nums[*nids] ++ ;

						iscore ++ ;
					}
				}
				(*nids)++ ;
			}

		}
	}
	// nids = number of patients 
	// iscore = number of scores. for healthy patient we take only one score (the highest), and for cancer cases we take all scores
	fprintf(stderr, "collect_all_autosim_scores: iscore=%d, nids=%d\n", iscore, *nids);

	return 0 ;
}

int collect_periodic_autosim_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date, int first_date,
					   pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor,
					   vector<string>& idstrs, int *dates, int *days, int *years, double *scores, 
					   int *gaps, int *id_starts, int *id_nums, int *types, int *nids, int period, int *nperiods, int *checksum) {

	*checksum = 0 ;
	int iscore = 0 ;
	idstrs.clear() ; 
	*nids = 0 ;

	int first_days = get_day(first_date) ;
	int last_days = get_day(last_date) ;
	int max_period = 0 ;

	for (auto it = all_scores.begin(); it != all_scores.end(); it++) {
		string id = it->first ;

		// Identify type and and last-date
		int type = 0 ;

		int last_allowed = last_days ;
		int first_cancer_day = get_day(99991231);

		if (registry.find(id) != registry.end()) {
			for (unsigned int i=0; i<registry[id].size(); i++) {
				if (registry[id][i].second == 2 && registry[id][i].first < first_cancer_day) {
					type = 2 ;
					first_cancer_day = registry[id][i].first ;
				} else if (registry[id][i].second == 1 && registry[id][i].first < first_cancer_day) {
					type = 1 ;
					first_cancer_day = registry[id][i].first ;
				} else if (registry[id][i].second == 3 && registry[id][i].first < first_cancer_day) {
					type = 0 ;
					first_cancer_day = registry[id][i].first ;
				}
			}

			if (first_cancer_day < last_allowed)
				last_allowed = first_cancer_day;
		}

		// Control - max per period
		if (type == 0) {
			int last_allowed = last_days ;
			if (censor.find(id) != censor.end() && censor[id].days < last_allowed && censor[id].stat == 2)
				last_allowed = censor[id].days ;

			map<int,int> max_score_index ;
			for (unsigned int i=0; i<all_scores[id].size(); i++) {

				if (all_scores[id][i].days >= first_days && all_scores[id][i].days <= last_allowed) {
					if (byears.find(id) == byears.end()) {
						fprintf(stderr,"Cannot find birth year for ID [%s]\n",id.c_str()) ;
						return -1 ;
					}
					int age = all_scores[id][i].year - byears[id] ;

					if (age >= age_range.first && age <= age_range.second) {
							
						(*checksum) = ((*checksum) + all_scores[id][i].days) & 0xFFFF ;
						for (unsigned int j=0; j< id.length(); j++)
							(*checksum) = ((*checksum) + id[j]) & 0xFFFF ;
							
						int iperiod = (all_scores[id][i].days - first_days)/period ;
						if (iperiod > max_period)
							max_period = iperiod ;
						if (max_score_index.find(iperiod) == max_score_index.end() || all_scores[id][i].score > all_scores[id][max_score_index[iperiod]].score)
							max_score_index[iperiod] = i ;
					}
				}
			}

			if (max_score_index.size()) {
				id_nums[*nids] = 0 ;
				id_starts[*nids] = iscore ;
				types[*nids] = 0 ;
				id_nums[*nids] = (int) max_score_index.size() ;
				
				for (auto it=max_score_index.begin(); it!=max_score_index.end(); it++) {
					idstrs.push_back(all_scores[id][it->second].id) ;
					dates[iscore] = all_scores[id][it->second].date;
					days[iscore] = all_scores[id][it->second].days ;
					scores[iscore] = all_scores[id][it->second].score ;
					years[iscore] = all_scores[id][it->second].year ;
					gaps[iscore] = -1 ;

					iscore ++ ;
				}
				(*nids) ++ ;
			}
		// Case
		} else if (type == 1) { // Sequence of scores per period
			map<int,vector<pair<int,double> > > id_scores ;
			for (unsigned int i=0; i<all_scores[id].size(); i++) {
				if (all_scores[id][i].days >= first_days && all_scores[id][i].days <= last_allowed) {
					if (byears.find(id) == byears.end()) {
						fprintf(stderr,"Cannot find birth year for ID [%s]\n",id.c_str()) ;
						return -1 ;
					}
					int age = all_scores[id][i].year - byears[id] ;

					if (age >= age_range.first && age <= age_range.second) {

						int iperiod = (all_scores[id][i].days - first_days)/period ;
						if (iperiod > max_period)
							max_period = iperiod ;

						pair<int,double> current_score(i,all_scores[id][i].score) ;
						id_scores[iperiod].push_back(current_score) ;

						(*checksum) = ((*checksum) + all_scores[id][i].days) & 0xFFFF ;
						for (unsigned int j=0; j< id.length(); j++)
							(*checksum) = ((*checksum) + id[j]) & 0xFFFF ;
					}
				}
			}

			if (id_scores.size()) {
				id_nums[*nids] = 0 ;
				types[*nids] = 1 ;
				id_starts[*nids] = iscore ;

				for (auto it=id_scores.begin(); it != id_scores.end(); it++) {
					vector<pair<int,double> >& period_scores = it->second ;

					sort(period_scores.begin(),period_scores.end(),rev_compare_pairs()) ;
					for (unsigned int i=0; i<period_scores.size(); i++) {
						if (i==0 || all_scores[id][period_scores[i].first].days < days[iscore-1]) {
							idstrs.push_back(all_scores[id][period_scores[i].first].id) ;
							dates[iscore] = all_scores[id][period_scores[i].first].date ;
							days[iscore] = all_scores[id][period_scores[i].first].days ;
							scores[iscore] = all_scores[id][period_scores[i].first].score ;
							years[iscore] = all_scores[id][period_scores[i].first].year ;
							gaps[iscore] = first_cancer_day - days[iscore] ;
							id_nums[*nids] ++ ;

							iscore ++ ;
						}
					}
				}
				(*nids)++ ;
			}
		}
	}

	*nperiods = max_period + 1 ;
	return 0 ;
}

int collect_periodic_cuts_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date, int first_date,
					   pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor,
					   vector<string>& idstrs, int *dates, int *days, int *years, double *scores, 
					   int *time_to_cancers, int *id_starts, int *id_nums, int *types, int *nids, int period, int gap, int *nperiods, int *checksum) {

	*checksum = 0 ;
	int iscore = 0 ;
	idstrs.clear() ; 
	*nids = 0 ;

	int first_days = get_day(first_date) ;
	int last_days = get_day(last_date) ;
	int max_period = 0 ;

	for (auto it = all_scores.begin(); it != all_scores.end(); it++) {
		string id = it->first ;

		// Identify type and and last-date
		int type = 0 ;

		int last_allowed = last_days ;
		if (registry.find(id) != registry.end()) {

			for (unsigned int i=0; i<registry[id].size(); i++) {
				if (registry[id][i].second == 2 && registry[id][i].first < last_allowed) {
					type = 2 ;
					last_allowed = registry[id][i].first ;
				} else if (registry[id][i].second == 1 && registry[id][i].first < last_allowed) {
					type = 1 ;
					last_allowed = registry[id][i].first ;
				} else if (registry[id][i].second == 3 && registry[id][i].first < last_allowed) {
					type = 0 ;
					last_allowed = registry[id][i].first ;
				}
			}
		}

		// Take last score per periods
		if (type == 0 || type == 1) {
			if (type == 0 && (censor.find(id) != censor.end() && censor[id].days < last_allowed  && censor[id].stat == 2))
				last_allowed = censor[id].days ;

			map<int,int> last_score_index ;
			for (unsigned int i=0; i<all_scores[id].size(); i++) {
				if (all_scores[id][i].days >= first_days && all_scores[id][i].days <= last_allowed) {
					if (byears.find(id) == byears.end()) {
						fprintf(stderr,"Cannot find birth year for ID [%s]\n",id.c_str()) ;
						return -1 ;
					}

					int age = all_scores[id][i].year - byears[id] ;
					if (age >= age_range.first && age <= age_range.second) {
							
						(*checksum) = ((*checksum) + all_scores[id][i].days) & 0xFFFF ;
						for (unsigned int j=0; j< id.length(); j++)
							(*checksum) = ((*checksum) + id[j]) & 0xFFFF ;
							
						int iperiod = (all_scores[id][i].days - first_days)/period ;
						if (iperiod > max_period)
							max_period = iperiod ;
						if (last_score_index.find(iperiod) == last_score_index.end() || all_scores[id][i].date > all_scores[id][last_score_index[iperiod]].score)
							last_score_index[iperiod] = i ;
					}
				}
			}

			if (last_score_index.size()) {
				id_nums[*nids] = 0 ;
				id_starts[*nids] = iscore ;
				types[*nids] = type ;
				id_nums[*nids] = 0 ;
				
				for (auto it=last_score_index.begin(); it!=last_score_index.end(); it++) {
					int iperiod = it->first ;
					int period_last_days = first_days + period*(iperiod + 1) ;

					idstrs.push_back(all_scores[id][it->second].id) ;
					dates[iscore] = all_scores[id][it->second].date;
					days[iscore] = all_scores[id][it->second].days ;
					scores[iscore] = all_scores[id][it->second].score ;
					years[iscore] = all_scores[id][it->second].year ;
					
					if (type == 0) {
						time_to_cancers[iscore++] = -1 ;
						id_nums[*nids] ++ ;
					} else if (last_allowed > period_last_days && last_allowed <= period_last_days + gap) {
						time_to_cancers[iscore++] = last_allowed - period_last_days ;
						id_nums[*nids] ++ ;
					}
				}

				if (id_nums[*nids])
					(*nids) ++ ;
			}
		}
	}

	*nperiods = max_period + 1 ;
	return 0 ;
}

int collect_all_binary_autosim_scores(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date,
					   pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor, vector<string>& idstrs, int *types, int *gaps, int *nids, int *checksum) {


	*checksum = 0 ;
	int iscore = 0 ;
	*nids = 0 ;
	idstrs.clear() ;

	int last_days = get_day(last_date) ;

	for (auto it = all_scores.begin(); it != all_scores.end(); it++) {
		string id = it->first ;

		// Identify type and last-date
		int type = 0 ;

		int last_allowed = last_days ;
		int first_cancer_day = get_day(99991231);

		if (registry.find(id) != registry.end()) {

			for (unsigned int i=0; i<registry[id].size(); i++) {
				if (registry[id][i].second == 2 && registry[id][i].first < first_cancer_day) {
					type = 2 ;
					first_cancer_day = registry[id][i].first ;
				} else if (registry[id][i].second == 1 && registry[id][i].first < first_cancer_day) {
					type = 1 ;
					first_cancer_day = registry[id][i].first ;
				} else if (registry[id][i].second == 3 && registry[id][i].first < first_cancer_day) {
					type = 0 ;
					first_cancer_day = registry[id][i].first ;
				}
			}
		}

		// Control
		if (type == 0) {
			int last_allowed = last_days ;
			if (censor.find(id) != censor.end() && censor[id].days < last_allowed  && censor[id].stat == 2)
				last_allowed = censor[id].days ;

			double max_score ;
			int max_score_index = -1 ;
			if (all_scores.find(id) != all_scores.end()) {
				for (unsigned int i=0; i<all_scores[id].size(); i++) {

					if (all_scores[id][i].days <= last_allowed) {
						if (byears.find(id) == byears.end()) {
							fprintf(stderr,"Cannot find birth year for ID [%s]\n",id.c_str()) ;
							return -1 ;
						}
						int age = all_scores[id][i].year - byears[id] ;

						if (age >= age_range.first && age <= age_range.second) {
							
							(*checksum) = ((*checksum) + all_scores[id][i].days) & 0xFFFF ;
							for (unsigned int j=0; j< id.length(); j++)
								(*checksum) = ((*checksum) + id[j]) & 0xFFFF ;

							if (max_score_index == -1 || all_scores[id][i].score > max_score)  {
								max_score = all_scores[id][i].score ;
								max_score_index = i ;
							}
						}
					}
				}
			}

			if (max_score_index != -1) {

				idstrs.push_back(all_scores[id][max_score_index].id) ;
				types[*nids] = 0 ;
				gaps[*nids] = (max_score > 0) ? 1 : -1 ;
				(*nids) ++ ;
			}
		// Case - Earliest pos
		} else if (type == 1) {
		
			double max_score ;
			int max_score_index = -1 ;
			for (unsigned int i=0; i<all_scores[id].size(); i++) {
				if (all_scores[id][i].days <= last_allowed) {
					if (byears.find(id) == byears.end()) {
						fprintf(stderr,"Cannot find birth year for ID [%s]\n",id.c_str()) ;
						return -1 ;
					}
					int age = all_scores[id][i].year - byears[id] ;

					if (age >= age_range.first && age <= age_range.second) {

						(*checksum) = ((*checksum) + all_scores[id][i].days) & 0xFFFF ;
						for (unsigned int j=0; j< id.length(); j++)
							(*checksum) = ((*checksum) + id[j]) & 0xFFFF ;

						if (max_score_index == -1 || (all_scores[id][i].score > 0 && (max_score <= 0 || all_scores[id][i].days < all_scores[id][max_score_index].days)))  {
							max_score = all_scores[id][i].score ;
							max_score_index = i ;
						}
					}
				}
			}

			if (max_score_index != -1) {
				idstrs.push_back(all_scores[id][max_score_index].id) ;
				types[*nids] = 1 ;
				if (max_score > 0) {
					gaps[*nids] = first_cancer_day - all_scores[id][max_score_index].days ;
					}
				else
					gaps[*nids] = -1 ;

				(*nids) ++ ;
			}
		}
	}

	return 0 ;
}


// Calculate statistics
void get_minimal_stats(vector<double>& pos, vector<double>& neg, all_stats& stats) {

	int tp = 0, fp = 0 ;
	int pos_ptr = 0, neg_ptr = 0 ;

	// Get vectors
	stats.n = (int) neg.size() ;
	stats.p = (int) pos.size() ;
	stats.tp.push_back(0) ;
	stats.fp.push_back(0) ;

	double min_score = ((neg[0] < pos[0]) ? neg[0] : pos[0]) - 0.1 ;
	stats.scores.push_back(min_score) ;

	if (stats.p == 0 || stats.n == 0)
		return ;

	double bnd = neg[neg_ptr] ;
	while (neg_ptr < stats.n) {
		while (pos_ptr < stats.p && pos[pos_ptr] >= bnd) {
			tp ++ ;
			pos_ptr ++ ;
		}

		while (neg_ptr < stats.n && neg[neg_ptr] == bnd) {
			fp ++ ;
			neg_ptr ++ ;
		}

		stats.fp.push_back(fp) ;
		stats.tp.push_back(tp) ;
		stats.scores.push_back(bnd) ;

		if (neg_ptr < stats.n)
			bnd = neg[neg_ptr] ;
	}

	return ;
}

void get_minimal_stats(vector<pair<int, double> >& scores, all_stats& stats) {

	int tp = 0, fp = 0 ;

	// Get vectors

	stats.tp.push_back(0) ;
	stats.fp.push_back(0) ;
	stats.scores.push_back(0) ;

	for (unsigned int i=0; i<scores.size(); i++) {
		if (scores[i].first == 1)
			tp ++ ;
		else
			fp ++ ;

		stats.fp.push_back(fp) ;
		stats.tp.push_back(tp) ;
		stats.scores.push_back(scores[i].second) ;
	}

	stats.n = stats.fp.back() ;
	stats.p = stats.tp.back() ;

	return ;
}

void get_stats(vector<double>& pos, vector<double>& neg, all_stats& stats) {

	int tp = 0, fp = 0 ;
	int pos_ptr = 0, neg_ptr = 0 ;

	// Get vectors
	stats.n = (int) neg.size() ;
	stats.p = (int) pos.size() ;
	stats.tp.push_back(0) ;
	stats.fp.push_back(0) ;

	if (stats.p == 0 || stats.n == 0)
		return ;

	double bnd = neg[neg_ptr] ;
	while (neg_ptr < stats.n) {
		while (pos_ptr < stats.p && pos[pos_ptr] >= bnd) {
			tp ++ ;
			pos_ptr ++ ;
		}

		while (neg_ptr < stats.n && neg[neg_ptr] == bnd) {
			fp ++ ;
			neg_ptr ++ ;
		}

		stats.fp.push_back(fp) ;
		stats.tp.push_back(tp) ;
		stats.scores.push_back(bnd) ;

		if (neg_ptr < stats.n)
			bnd = neg[neg_ptr] ;
	}

	// Pearson Correlation
	int n = stats.p + stats.n;
	double meany = stats.p/n ;

	double sum = 0 ;
	for (int i=0; i<stats.p; i++)
		sum += pos[i] ;

	for (int i=0; i<stats.n; i++)
		sum += neg[i] ;

	double meanx = sum/n ;

	double sxx = 0 ;
	double sxy = 0 ;

	double syy = stats.p*(1-meany)*(1-meany) + stats.n*meany*meany ;

	for (int i=0; i<stats.p; i++) {
		sxx += (pos[i]-meanx)*(pos[i]-meanx) ;
		sxy += (pos[i]-meanx)*(1-meany) ;
	}

	for (int i=0; i<stats.n; i++) {
		sxx += (neg[i]-meanx)*(neg[i]-meanx) ;
		sxy += (neg[i]-meanx)*meany ;
	}

	if (sxx==0) sxx=1 ;
	if (syy==0) syy=1 ;

	stats.corr = sxy/sqrt(sxx*syy) ;

	// Estimate AUC parameters.

	// Mean 
	int nrand = 30000 ;
	stats.theta = stats.q1 = stats.q2 = 0 ;
	for (int i=0; i<nrand; i++) {
		int ipos = (int) (1.0 * stats.p * globalRNG::rand() / (globalRNG::max())) ;
		int ineg = (int) (1.0 * stats.n * globalRNG::rand() / (globalRNG::max())) ;
		if (pos[ipos] > neg[ineg])
			stats.theta ++ ;
	}
	stats.theta /= nrand ;

	// Standard deviation
	for (int i=0; i<nrand; i++) {
		int ipos1 = (int) (1.0 * stats.p * globalRNG::rand() / (globalRNG::max())) ;
		int ipos2 = (int) (1.0 * stats.p * globalRNG::rand() / (globalRNG::max())) ;
		int ineg = (int) (1.0 * stats.n * globalRNG::rand() / (globalRNG::max())) ;
		if (pos[ipos1] > neg[ineg] && pos[ipos2]>neg[ineg])
			stats.q1 ++ ;
	}
	stats.q1 /= nrand ;

	for (int i=0; i<nrand; i++) {
		int ipos = (int) (1.0 * stats.p * globalRNG::rand() / (globalRNG::max())) ;
		int ineg1 = (int) (1.0 * stats.n * globalRNG::rand() / (globalRNG::max())) ;
		int ineg2 = (int) (1.0 * stats.n * globalRNG::rand() / (globalRNG::max())) ;
		if (pos[ipos] > neg[ineg1] && pos[ipos]>neg[ineg2])
			stats.q2 ++ ;
	}
	stats.q2 /= nrand ;

	return ;
}

double get_incidence(map<int,double>& incidence_rate, int age) {

	int lower = -1, upper = -1 ;

	for (map<int,double>::iterator it=incidence_rate.begin(); it != incidence_rate.end(); it++) {
		if (it->first <= age && (lower == -1 || it->first > lower))
			lower = it->first ;
		if (it->first >= age && (upper == -1 || it->first < upper))
			upper = it->first ;
	}

	assert(upper!=-1 || lower !=-1) ;

	if (upper == age)
		return incidence_rate[upper] ;
	else if (upper == -1)
		return incidence_rate[lower] ;
	else if (lower == -1)
		return incidence_rate[upper] ;
	else 
		return (incidence_rate[lower]*(upper-age) + incidence_rate[upper]*(age-lower))/(upper-lower) ;
}

int get_bootstrap_stats(double *scores, int *ages, int *types, int *id_starts, int *id_nums, int nids, all_stats& stats, map<int,double>& incidence_rate, double *incidence, bool use_last, quick_random& qrand, int take_all) {
	// Sample ids with replacement
	int *ids = (int *) malloc (nids*sizeof(int)) ;

	if (take_all) {
		for(int i=0; i<nids; i++)
			ids[i] = i ;
	} else {
		for (int i=0; i<nids; i++)
			ids[i] = int(nids * qrand.random()) ;
	}

	// Sample scores
	vector<pair<int, double> > selected_scores ;
	int npos=0,nneg=0 ;

	*incidence = (incidence_rate.size() > 0) ? 0 : -1 ;
	for (int i=0; i<nids; i++) {
		if (types[ids[i]] == 1) {
			int idx ;
			if (use_last)
				idx = id_nums[ids[i]]-1 ;
			else 
				idx = (int) (id_nums[ids[i]] * qrand.random()) ;
			pair<int, double> current (1,scores[id_starts[ids[i]]+idx]) ;
			selected_scores.push_back(current) ;
			npos ++ ;
		} else {
			int idx = (int) (id_nums[ids[i]] * qrand.random()) ;
			pair<int, double> current (0,scores[id_starts[ids[i]]+idx]) ;
			selected_scores.push_back(current) ;
			nneg ++ ;
			if (incidence_rate.size())
				(*incidence) += get_incidence(incidence_rate,ages[id_starts[ids[i]]+idx]) ;
		}
	}

	free(ids) ;

	if (npos && nneg) {
		shuffle_vector(selected_scores, qrand) ;
		sort(selected_scores.begin(), selected_scores.end(), rev_compare_pairs()) ;
		get_minimal_stats(selected_scores, stats) ;

		if (incidence_rate.size())
			(*incidence) /= nneg ;

		return 0 ;
	} else
		return -1 ;
}

int get_binary_bootstrap_stats(double *scores, int *ages, int *types, int *id_starts, int *id_nums, int nids, int stats[2][2], map<int,double>& incidence_rate, double *incidence, bool use_last, quick_random& qrand, int take_all) {

	stats[0][0] = stats[0][1] = stats[1][0] = stats[1][1] = 0 ;

	// Sample ids with replacement
	int *ids = (int *) malloc (nids*sizeof(int)) ;

	if (take_all) {
		for (int i=0; i<nids; i++)
			ids[i] = i ;
	} else {
		for (int i=0; i<nids; i++)
			ids[i] = int(nids * qrand.random()) ;
	}

	// Sample scores
	*incidence = (incidence_rate.size() > 0) ? 0 : -1 ;
	for (int i=0; i<nids; i++) {
		int idx ;
		if (types[ids[i]] == 1) {
			if (use_last) 
				idx = id_nums[ids[i]]-1;
			else 
				idx = (int) (id_nums[ids[i]] * qrand.random()) ;

			int binary_score = (scores[id_starts[ids[i]]+idx] > 0) ? 1 : 0 ;
			stats[1][binary_score] ++ ;
		} else {
			int idx = (int) (id_nums[ids[i]] * qrand.random()) ;
			int binary_score = (scores[id_starts[ids[i]]+idx] > 0) ? 1 : 0 ;
			stats[0][binary_score] ++ ;
			if (incidence_rate.size())
				(*incidence) += get_incidence(incidence_rate,ages[id_starts[ids[i]]+idx]) ;
		}
	}

	free(ids) ;

	int nneg = stats[0][0] + stats[0][1] ;
	int npos = stats[1][0] + stats[1][1] ;

	if (nneg && npos) {
		if (incidence_rate.size())
			(*incidence) /= nneg ;

		return 0 ;
	} else
		return -1 ;
}

void sample_ids(int *sampled_ids, int nids, quick_random& qrand) {

	// Sample ids with replacement
	for (int i=0; i<nids; i++) {
		sampled_ids[i] = int(nids * qrand.random()) ;
	}

	return ;
}

int get_bootstrap_scores(double *scores, int *types, int *id_starts, int *id_nums, int nids, vector<double>& pos_scores, vector<double>& neg_scores, quick_random& qrand, int take_all) {

	// Sample ids with replacement (or not)
	int *ids = (int *) malloc (nids*sizeof(int)) ;
	if (take_all) {
		for (int i=0; i<nids; i++)
			ids[i] = i ;
	} else
		sample_ids(ids, nids, qrand) ;

	// Sample scores
	for (int i=0; i<nids; i++) {
		if (types[ids[i]] == 1)
			pos_scores.push_back(scores[id_starts[ids[i]]+id_nums[ids[i]]-1]) ;
		else {
			int idx = (int) (id_nums[ids[i]] * qrand.random()) ;
			neg_scores.push_back(scores[id_starts[ids[i]]+idx]) ;
		}
	}

	free(ids) ;

	return 0 ;
}

double max_vector (vector<double>& vec) {
	double max_val=vec[0];
	if (vec.size()>1) {
		for (int ii=1; ii<vec.size(); ii++) {
			if (vec[ii]>max_val) {
				max_val = vec[ii];
			}
		}
	}

	return max_val;
}

int max_vector_int (vector<int>& vec) {
	int max_val=vec[0];
	if (vec.size()>1) {
		for (int ii=1; ii<vec.size(); ii++) {
			if (vec[ii]>max_val) {
				max_val = vec[ii];
			}
		}
	}

	return max_val;
}




int get_autosim_scores(int *gaps , double *scores, int *types, int *id_starts, int *id_nums, int nids, vector<double>& pos_scores, vector<double>& neg_scores, quick_random& qrand,
					   vector<double>& earlysens1pos_scores,vector<double>& earlysens2pos_scores,vector<double>& earlysens3pos_scores, int take_all) {

	// Sample ids with replacement
	int *ids = (int *) malloc (nids*sizeof(int)) ;
	if (take_all == 1) {
		for (int i=0; i<nids; i++)
			ids[i] = i ;
	} else
		sample_ids(ids, nids, qrand) ;

	// Sample scores
	for (int i=0; i<nids; i++) {
		if (types[ids[i]] == 1) {

			vector<double> early1; 
			vector<double> early2; 
			vector<double> early3; 

			double max_score= scores[id_starts[ids[i]]+0];
			for (int idx=1; idx<id_nums[ids[i]]; idx++) {
				if (scores[id_starts[ids[i]]+idx]>max_score) max_score = scores[id_starts[ids[i]]+idx];
			}
			pos_scores.push_back(max_score) ;

			for (int idx=0; idx<id_nums[ids[i]]; idx++) {
				int temp_gap = min(AUTOSIM_NGAPS-1,gaps[id_starts[ids[i]]+idx]/AUTOSIM_GAP) ;
				if (temp_gap>=1) early1.push_back(scores[id_starts[ids[i]]+idx]);
				if (temp_gap>=2) early2.push_back(scores[id_starts[ids[i]]+idx]);
				if (temp_gap>=4) early3.push_back(scores[id_starts[ids[i]]+idx]);
			}
			
			if (early1.size()>0) earlysens1pos_scores.push_back( max_vector(early1));
			if (early2.size()>0) earlysens2pos_scores.push_back( max_vector(early2));
			if (early3.size()>0) earlysens3pos_scores.push_back( max_vector(early3));
		}
		else {

			double max_score=scores[id_starts[ids[i]]+0];
			for (int idx=1; idx<id_nums[ids[i]]; idx++) {
				if (scores[id_starts[ids[i]]+idx]>max_score) max_score = scores[id_starts[ids[i]]+idx];
			}
			neg_scores.push_back(max_score) ;
		}
	}
	free(ids) ;

	return 0 ;
}



void print_raw_and_info(vector<string>& idstrs, int *dates, double *scores, int *types, int *id_starts, int *id_nums, int nids, quick_random& qrand, 
						FILE *fp_raw, FILE *fp_info, char *prefix, bool use_last) {
	for (int i=0; i<nids; i++) {
		if (types[i] == 1) {
			int idx;
			if (use_last)
				idx = id_nums[i] - 1;
			else
				idx = (int)(id_nums[i] * qrand.random());
			fprintf(fp_raw, "%s %f 1\n", prefix, scores[id_starts[i]+idx]) ;
			if (fp_info != NULL) {
				fprintf(fp_info, "%s %f 1 %s %d\n", prefix, scores[id_starts[i]+idx], 
													idstrs[id_starts[i]+idx].c_str(), dates[id_starts[i]+idx]) ;
			}
		}
		else {
			int idx = (int) (id_nums[i] * qrand.random()) ;
			fprintf(fp_raw, "%s %f 0\n", prefix, scores[id_starts[i]+idx]) ;
			if (fp_info != NULL) {
				fprintf(fp_info, "%s %f 0 %s %d\n", prefix, scores[id_starts[i]+idx],
											        idstrs[id_starts[i]+idx].c_str(), dates[id_starts[i]+idx]) ;
			}
		}
	}
	return ;
}

void get_bootstrap_estimate(all_stats& stats,vector<double>& estimate, double incidence, double extra_fpr, double extra_sens, bool all_fpr, vector<bool>& valid) {

	int size = (int) stats.tp.size() ;

	int iftr = 0 ;
	estimate[iftr++] = stats.p ;
	estimate[iftr++] = stats.n ;

	// Regular AUC
	// direct integration over the trapezoids. Each of them has 
	// * a base with width delta(fp) 
	// * left edge height is tp(i-1)
	// * right edge height is tp(i)
	// which comes down to area of delta(fp)*[tp(i-1) + tp(i)]/2
	double auc = 0 ;
	for (int i=1; i<size; i++)
		auc += ((stats.fp[i] + 0.0)/stats.n - (stats.fp[i-1] + 0.0)/stats.n) * ((stats.tp[i] + 0.0)/stats.p + (stats.tp[i-1] + 0.0)/stats.p) /2.0 ;
	estimate[iftr++] = auc ;

	// Weighted auc
	double wauc = 0 ;
	for (int i=1; i<size; i++) {
		double sens = ((stats.tp[i] + 0.0)/stats.p + (stats.tp[i-1] + 0.0)/stats.p) /2.0 ;
		double spec = 1 - (stats.fp[i] + 0.0)/stats.n ;

		wauc += sens * ((stats.fp[i] + 0.0)/stats.n - (stats.fp[i-1] + 0.0)/stats.n) * spec ;
	}
	estimate[iftr++] = wauc ;

	// Area under Precison-Recall curve
	double auc_pr = 0.0;
	for (int i=1; i<size; i++) {
		// fprintf(stderr, "i=%d, tp_a: %d, fp_a: %d, tp_b: %d, fp_b: %d\n", 
		//		i, stats.tp[i-1], stats.fp[i-1], stats.tp[i], stats.fp[i]); 
		double prec_b = (stats.tp[i] + 0.0)/(stats.tp[i] + stats.fp[i]);
		double prec_a = prec_b;
		if (i > 1) prec_a = (stats.tp[i-1] + 0.0)/(stats.tp[i-1] + stats.fp[i-1]);
		auc_pr +=  ((stats.tp[i] + 0.0)/stats.p - (stats.tp[i-1] + 0.0)/stats.p) *
					(prec_a + prec_b) /2.0 ;
		// fprintf(stderr, "prec_a: %f, prec_b: %f, auc_pr: %f\n", prec_a, prec_b, auc_pr);
	}
	estimate[iftr++] = auc_pr ;

	double sens,spec,score ;
	double pos_rate,neg_rate ;
	double ppv,npv,odds_ratio,lift,rr ;
	double new_diff;
	double diff = 2.0 ;

	// Sample at different false-positive-rate points 
	int npoints = get_fpr_points_num(all_fpr) ;
	double *fpr_points = get_fpr_points(all_fpr) ;
	int ptr = 0 ;

	double fpr ;

	for (int i=0; i<npoints; i++) {
		// Are we already at the end ?
		if (ptr > size) {
			for (int j=0; j<9; j++) 
				valid[iftr++] = false ;
		}

		// Otherwise
		while (ptr <= size) {
			if (ptr == size)
				new_diff = 2.0 ;
			else {
				fpr = (stats.fp[ptr] + 0.0)/stats.n;
				new_diff = abs(fpr - fpr_points[i]/100) ;
			}

			if (new_diff <= diff) {
				diff = new_diff ;
				ptr ++ ;
			} else {
				int fp = stats.fp[ptr-1] ;
				int tp = stats.tp[ptr-1] ;
				int fn = stats.p - stats.tp[ptr-1] ;
				int tn = stats.n - stats.fp[ptr-1] ;
				score = stats.scores[ptr-1] ;

				sens = (tp+fn == 0) ? -1 : (100.0 * tp)/(tp+fn) ;
				spec = 100.0 - (100.0 * fp)/stats.n ;
				odds_ratio = (fp == 0 ||  tn == 0 ||  fn ==  0) ? -1 : ((tp+0.0)/fp)/((fn+0.0)/tn) ;

				if (incidence != -1) {
					pos_rate = incidence*sens + (1.0-incidence)*(100-spec) ;
					neg_rate = incidence*(100-sens) + (1.0-incidence)*spec ;

					ppv = (pos_rate==0) ? -1 : 100 * incidence*sens/pos_rate ;
					npv = (neg_rate==0) ? -1 : 100 * (1.0-incidence)*spec/neg_rate ;
					lift = ppv/incidence/100 ;
					rr = ppv*neg_rate/(100*incidence*(100-sens)) ;

				} else {
					pos_rate = -1;
					ppv = -1 ;
					npv = -1 ;
					lift = -1 ;
					rr = -1 ;
				}
				
				fpr = (fp+0.0)/stats.n ;

				// Sensitivity
				if (sens == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = sens ;
				// Odds Ratio
				if (odds_ratio == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = odds_ratio ;
				// Negative Predictive Value
				if (npv == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = npv ;
				// Positive Predictive Value
				if (ppv == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = ppv ;
				// Positive Rate
				if (pos_rate == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = pos_rate;
				// Lift
				if (lift == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = lift ;
				// Positive Likelihood Ratio
				if (spec == 100) 
					valid[iftr++]= false ;
				else
					estimate[iftr++] = sens/(100.0-spec) ;
				// Negative Likelihhod Ratio
				if (spec == 0)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = (100.0-sens)/spec ; 
				// Score
				estimate[iftr++] = score ;
				// Relative risk
				if (rr == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = rr ;

				if (i != npoints)
					diff = abs(fpr - fpr_points[i+1]/100) ;
				ptr ++ ;
				break ;
			}
		}
	}

	// Sample at different sensitivity points.
	npoints = get_sens_points_num() ;
	double *sens_points = get_sens_points() ;
	
	ptr = 0 ;
	diff=2.0 ;
	for (int i=0; i<npoints; i++) {
		// Are we already at the end ?
		if (ptr > size) {
			for (int j=0; j<9; j++) 
				valid[iftr++] = false ;
		}

		// Otherwise
		while (ptr <= size) {
			if (ptr == size)
				new_diff = 2.0 ;
			else {
				sens = (stats.tp[ptr] + 0.0)/stats.p ;
				new_diff = abs(sens - sens_points[i]/100) ;
			}

			if (new_diff <= diff) {
				diff = new_diff ;
				ptr ++ ;
			} else {
				int fp = stats.fp[ptr-1] ;
				int tp = stats.tp[ptr-1] ;
				int fn = stats.p - stats.tp[ptr-1] ;
				int tn = stats.n - stats.fp[ptr-1] ;

				sens = (tp+fn == 0) ? -1 : (100.0 * tp)/(tp+fn) ;
				spec = 100.0 - (100.0 * fp)/stats.n ;
				score = stats.scores[ptr-1] ;
				odds_ratio = (fp == 0 ||  tn == 0 ||  fn ==  0) ? -1 : ((tp+0.0)/fp)/((fn+0.0)/tn) ;

				if (incidence != -1) {
					pos_rate = incidence*sens + (1.0-incidence)*(100-spec) ;
					neg_rate = incidence*(100-sens) + (1.0-incidence)*spec ;

					ppv = (pos_rate==0) ? -1 : 100 * incidence*sens/pos_rate ;
					npv = (neg_rate==0) ? -1 : 100 * (1.0-incidence)*spec/neg_rate ;
					lift = ppv/incidence/100 ;
					rr = ppv*neg_rate/(100*incidence*(100-sens)) ;

				} else {
					pos_rate = -1;
					ppv = -1 ;
					npv = -1 ;
					lift = -1 ;
					rr = -1 ;
				}
				//fprintf(stderr, "score: %f, sens: %f, spec: %f, tp: %d, fp: %d, fn: %d, tn: %d\n", score, sens, spec, tp, fp, fn, tn);
				// Specificity
				if (spec == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = spec ;
				// Odds Ratio
				if (odds_ratio == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = odds_ratio ;
				// Negative Predictive Value
				if (npv == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = npv ;
				// Positive Predictive Value
				if (ppv == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = ppv ;
				// Positive Rate
				if (pos_rate == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = pos_rate;
				// Lift
				if (lift == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = lift ;
				// Positive Likelihood Ratio
				if (spec == 100) 
					valid[iftr++]= false ;
				else
					estimate[iftr++] = sens/(100.0-spec) ;
				// Negative Likelihhod Ratio
				if (spec == 0)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = (100.0-sens)/spec ; 
				// Score
				estimate[iftr++] = score ;
				// Relative risk
				if (rr == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = rr ;
				
				if (i != npoints)
					diff = abs(sens - sens_points[i+1]/100) ;
				ptr ++ ;
				break ;
			}
		}
	}

	// Sample at different sensitivity points.
	npoints = get_score_points_num();
	double *score_points = get_score_points();

	ptr = 1;
	for (int i = 0; i<npoints; i++) {
		// Are we already at the end ?
		if (ptr == size) {
			for (int j = 0; j<9; j++)
				valid[iftr++] = false;
		}

		// Otherwise
		while (ptr < size) {
			score = stats.scores[ptr];
			//fprintf(stderr, "score: %f, ptr: %d, i: %d, scores[ptr]: %f\n", score, ptr, i, score_points[i]);

			if (score > score_points[i]) {
				ptr++;
			}
			else {
				int fp = stats.fp[ptr - 1];
				int tp = stats.tp[ptr - 1];
				int fn = stats.p - stats.tp[ptr - 1];
				int tn = stats.n - stats.fp[ptr - 1];

				sens = (tp + fn == 0) ? -1 : (100.0 * tp) / (tp + fn);
				spec = 100.0 - (100.0 * fp) / stats.n;
				double score = stats.scores[ptr - 1];
				odds_ratio = (fp == 0 || tn == 0 || fn == 0) ? -1 : ((tp + 0.0) / fp) / ((fn + 0.0) / tn);

				if (incidence != -1) {
					pos_rate = incidence*sens + (1.0 - incidence)*(100 - spec);
					neg_rate = incidence*(100 - sens) + (1.0 - incidence)*spec;

					ppv = (pos_rate == 0) ? -1 : 100 * incidence*sens / pos_rate;
					npv = (neg_rate == 0) ? -1 : 100 * (1.0 - incidence)*spec / neg_rate;
					lift = ppv / incidence / 100;
					rr = ppv*neg_rate / (100 * incidence*(100 - sens));

				}
				else {
					pos_rate = -1;
					ppv = -1;
					npv = -1;
					lift = -1;
					rr = -1;
				}
				//fprintf(stderr, "score: %f, sens: %f, spec: %f, tp: %d, fp: %d, fn: %d, tn: %d ptr: %d, scores[ptr]: %f\n", 
				//	score, sens, spec, tp, fp, fn, tn, ptr, stats.scores[ptr]);
				// Sensitivity
				if (sens == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = sens;
				// Odds Ratio
				if (odds_ratio == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = odds_ratio;
				// Negative Predictive Value
				if (npv == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = npv;
				// Positive Predictive Value
				if (ppv == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = ppv;
				// Positive Rate
				if (pos_rate == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = pos_rate;
				// Lift
				if (lift == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = lift;
				// Positive Likelihood Ratio
				if (spec == 100)
					valid[iftr++] = false;
				else
					estimate[iftr++] = sens / (100.0 - spec);
				// Negative Likelihhod Ratio
				if (spec == 0)
					valid[iftr++] = false;
				else
					estimate[iftr++] = (100.0 - sens) / spec;
				// Score
				if (spec == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = spec;
				// Relative risk
				if (rr == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = rr;

				//ptr++;
				break;
			}
		}
	}

	// Check extra fpr point
	ptr = 0 ;
	if (extra_fpr != -1) {
		while (ptr <= size) {
			if (ptr == size)
				new_diff = 2.0 ;
			else {
				fpr = (stats.fp[ptr] + 0.0)/stats.n;
				new_diff = abs(fpr - extra_fpr/100.0) ;
			}

			if (new_diff <= diff) {
				diff = new_diff ;
				ptr ++ ;
			} else {
				int fp = stats.fp[ptr-1] ;
				int tp = stats.tp[ptr-1] ;
				int fn = stats.p - stats.tp[ptr-1] ;
				int tn = stats.n - stats.fp[ptr-1] ;
				double score = stats.scores[ptr-1] ;

				sens = (tp+fn == 0) ? -1 : (100.0 * tp)/(tp+fn) ;
				spec = 100.0 - (100.0 * fp)/stats.n ;
				odds_ratio = (fp == 0 ||  tn == 0 ||  fn ==  0) ? -1 : ((tp+0.0)/fp)/((fn+0.0)/tn) ;

				if (incidence != -1) {
					pos_rate = incidence*sens + (1.0-incidence)*(100-spec) ;
					neg_rate = incidence*(100-sens) + (1.0-incidence)*spec ;

					ppv = (pos_rate==0) ? -1 : 100 * incidence*sens/pos_rate ;
					npv = (neg_rate==0) ? -1 : 100 * (1.0-incidence)*spec/neg_rate ;
					lift = ppv/incidence/100 ;
					rr = ppv*neg_rate/(100*incidence*(100-sens)) ;

				} else {
					pos_rate = -1;
					ppv = -1 ;
					npv = -1 ;
					lift = -1 ;
					rr = -1;
				}
				
				fpr = (fp+0.0)/stats.n ;

				// Sensitivity
				if (sens == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = sens ;
				// Odds Ratio
				if (odds_ratio == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = odds_ratio ;
				// Negative Predictive Value
				if (npv == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = npv ;
				// Positive Predictive Value
				if (ppv == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = ppv ;
				// Positive Rate
				if (pos_rate == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = pos_rate;
				// Lift
				if (lift == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = lift ;
				// Positive Likelihood Ratio
				if (spec == 100) 
					valid[iftr++]= false ;
				else
					estimate[iftr++] = sens/(100.0-spec) ;
				// Negative Likelihhod Ratio
				if (spec == 0)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = (100.0-sens)/spec ; 
				// Score
				estimate[iftr++] = score ;
				// Relative risk
				if (rr == -1)
					valid[iftr++] = false ;
				else
					estimate[iftr++] = rr ;
				
				ptr ++ ;
				break ;
			}
		}
	}

	// Check extra sensitivity point
	ptr = 0;
	diff = 2.0;
	if (extra_sens != -1) {
		while (ptr <= size) {
			if (ptr == size)
				new_diff = 2.0;
			else {
				sens = (stats.tp[ptr] + 0.0) / stats.p;
				new_diff = abs(sens - extra_sens / 100);
			}

			if (new_diff <= diff) {
				diff = new_diff;
				ptr++;
			}
			else {
				int fp = stats.fp[ptr - 1];
				int tp = stats.tp[ptr - 1];
				int fn = stats.p - stats.tp[ptr - 1];
				int tn = stats.n - stats.fp[ptr - 1];

				sens = (tp + fn == 0) ? -1 : (100.0 * tp) / (tp + fn);
				spec = 100.0 - (100.0 * fp) / stats.n;
				double score = stats.scores[ptr - 1];
				odds_ratio = (fp == 0 || tn == 0 || fn == 0) ? -1 : ((tp + 0.0) / fp) / ((fn + 0.0) / tn);

				if (incidence != -1) {
					pos_rate = incidence*sens + (1.0 - incidence)*(100 - spec);
					neg_rate = incidence*(100 - sens) + (1.0 - incidence)*spec;

					ppv = (pos_rate == 0) ? -1 : 100 * incidence*sens / pos_rate;
					npv = (neg_rate == 0) ? -1 : 100 * (1.0 - incidence)*spec / neg_rate;
					lift = ppv / incidence / 100;
					rr = ppv*neg_rate / (100 * incidence*(100 - sens));

				}
				else {
					pos_rate = -1;
					ppv = -1;
					npv = -1;
					lift = -1;
					rr = -1;
				}

				// Specificity
				if (spec == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = spec;
				// Odds Ratio
				if (odds_ratio == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = odds_ratio;
				// Negative Predictive Value
				if (npv == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = npv;
				// Positive Predictive Value
				if (ppv == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = ppv;
				// Positive Rate
				if (pos_rate == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = pos_rate;
				// Lift
				if (lift == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = lift;
				// Positive Likelihood Ratio
				if (spec == 100)
					valid[iftr++] = false;
				else
					estimate[iftr++] = sens / (100.0 - spec);
				// Negative Likelihhod Ratio
				if (spec == 0)
					valid[iftr++] = false;
				else
					estimate[iftr++] = (100.0 - sens) / spec;
				// Score
				estimate[iftr++] = score;
				// Relative risk
				if (rr == -1)
					valid[iftr++] = false;
				else
					estimate[iftr++] = rr;

				ptr++;
				break;
			}
		}
	}

	return ;
}

void get_binary_bootstrap_estimate(int stats[2][2],vector<double>& estimate, double incidence) {

	int tp = stats[1][1];
	int fp = stats[0][1];
	int tn = stats[0][0];
	int fn = stats[1][0];

	int npos = tp + fn ;
	int nneg = fp + tn ;
	int size = npos + nneg ;

	double sens, spec , pos_rate , neg_rate , ppv , npv , lift , rr , plr , nlr ,odds_ratio;

	sens = (tp+fn == 0) ? -1 : (100.0 * tp)/(tp+fn) ;
	spec = 100.0 - (100.0 * fp)/nneg ;
	odds_ratio = (fp == 0 ||  tn == 0 ||  fn ==  0) ? -1 : ((tp+0.0)/fp)/((fn+0.0)/tn) ;

	if (incidence != -1) {
		pos_rate = incidence*sens + (1.0-incidence)*(100-spec) ;
		neg_rate = incidence*(100-sens) + (1.0-incidence)*spec ;

		ppv = (pos_rate==0) ? -1 : 100 * incidence*sens/pos_rate ;
		npv = (neg_rate==0) ? -1 : 100 * (1.0-incidence)*spec/neg_rate ;
		lift = ppv/incidence/100 ;
		rr = ppv*neg_rate/(100*incidence*(100-sens)) ;
	} else {
		pos_rate = -1;
		ppv = -1 ;
		npv = -1 ;
		lift = -1 ;
		rr = -1 ;
	}	

	plr = (spec==100) ? -1 : sens/(100.0-spec) ;    // Positive Likelihood Ratio
	nlr = (spec==0) ? -1 : (100.0-sens)/spec ;     // Negative Likelihhod Ratio

	int iftr = 0 ;
	estimate[iftr++] = npos ;
	estimate[iftr++] = nneg ;
	estimate[iftr++] = spec;
	estimate[iftr++] = sens;
	estimate[iftr++] = odds_ratio;
	estimate[iftr++] = npv;
	estimate[iftr++] = ppv;
	estimate[iftr++] = pos_rate;
	estimate[iftr++] = lift;
	estimate[iftr++] = plr;
	estimate[iftr++] = nlr;
	estimate[iftr++] = rr;


	return ;
}

void get_bootstrap_performance(vector<double>& pos_scores, vector<double>& neg_scores, vector<target_bound>& bnds, vector<double>& estimates) {

	double npos  = (double) pos_scores.size() ;
	double nneg = (double) neg_scores.size() ;

	int iftr = 0 ;
	int ntp,nfp ;
	double bnd ;

	for (unsigned int i=0; i<bnds.size(); i++) {

		bnd = bnds[i].score ;
		ntp = 0 ;
		for (unsigned j=0; j<pos_scores.size(); j++) {
			if (pos_scores[j] > bnd)
				ntp ++ ;
		}
		estimates[iftr++] = ntp/npos ;

		nfp = 0 ;
		for (unsigned j=0; j<neg_scores.size(); j++) {
			if (neg_scores[j] > bnd)
				nfp ++ ;
		}
		estimates[iftr++] = 1 - nfp/nneg ;
	}

	return ;
}

void get_bootstrap_performance_autosim(vector<double>& pos_scores,vector<double>& earlysens1pos_scores ,vector<double>&  earlysens2pos_scores,vector<double>& earlysens3pos_scores, vector<double>& neg_scores, vector<target_bound_autosim>& bnds, vector<double>& estimates) {

	double npos  = (double) pos_scores.size() ;
	double nneg = (double) neg_scores.size() ;
	double nearly1 = (double) earlysens1pos_scores.size() ;
	double nearly2 = (double) earlysens2pos_scores.size() ;
	double nearly3 = (double) earlysens3pos_scores.size() ;

	int iftr = 0 ;
	int ntp,nfp,bnd_early1,bnd_early2,bnd_early3 ;
	double bnd ;

	for (unsigned int i=0; i<bnds.size(); i++) {

		bnd = bnds[i].score ;
		ntp = 0 ;
		for (unsigned j=0; j<pos_scores.size(); j++) {
			if (pos_scores[j] > bnd)
				ntp ++ ;
		}
		estimates[iftr++] = ntp/npos ;

		nfp = 0 ;
		for (unsigned j=0; j<neg_scores.size(); j++) {
			if (neg_scores[j] > bnd)
				nfp ++ ;
		}
		estimates[iftr++] = 1 - nfp/nneg ;

		bnd_early1=0;
		for (unsigned j=0; j<earlysens1pos_scores.size(); j++) {
			if (earlysens1pos_scores[j] > bnd)
				bnd_early1 ++ ;
		}
		estimates[iftr++] = bnd_early1/nearly1;

		bnd_early2=0;
		for (unsigned j=0; j<earlysens2pos_scores.size(); j++) {
			if (earlysens2pos_scores[j] > bnd)
				bnd_early2 ++ ;
		}
		estimates[iftr++] = bnd_early2/nearly2;

		bnd_early3=0;
		for (unsigned j=0; j<earlysens3pos_scores.size(); j++) {
			if (earlysens3pos_scores[j] > bnd)
				bnd_early3 ++ ;
		}
		estimates[iftr++] = bnd_early3/nearly3;
	}
	return ;
}

// calculate all stats (fp, tp, ppv, sensitivity, etc.) per interesting fpr point
void get_autosim_parameters(int *ids, int *types, int *id_starts, int *id_nums, int nids,  double *all_scores, int *all_gaps, vector<double>& estimate, vector<bool>& valid, quick_random& qrand , double extra_fpr) {
	
	assert(ntime_unit_delays==3) ;

	// Create scores vector
	int np_early1=0;
	int np_early2=0;
	int np_early3=0;

	vector<autosim_score > scores ;
	for (int i=0; i<nids; i++) {

		int id_type = types[ids[i]];
		int max_gap=-1;
		for (int j=0; j<id_nums[ids[i]]; j++) {
			autosim_score new_score ;
			new_score.id = i ;
			// fprintf(stderr, "get_autosim_parameters: i=%d, j=%d, ids=%d, num_id=%d, id_start=%d\n", i, j, ids[i], id_nums[ids[i]], id_starts[ids[i]]);
			new_score.score = all_scores[id_starts[ids[i]] + j] ;
			new_score.gap = min(AUTOSIM_NGAPS-1,all_gaps[id_starts[ids[i]]+j]/AUTOSIM_GAP) ;
			scores.push_back(new_score) ;
			if (id_type==1 && new_score.gap>max_gap)  
				max_gap = new_score.gap; 
		}
		
		if (id_type==1) {
			if (max_gap>=1) np_early1++ ; 
			if (max_gap>=2) np_early2++ ; 
			if (max_gap>=4) np_early3++ ; 
		}
	}

	shuffle_vector(scores, qrand) ; // break ties in score randomly
	sort(scores.begin(),scores.end(),rev_compare_autosim_scores()) ;

	// Create Full Histogram
	// per score from highest to lowest accumulate fp, tp
	// and gaps = matrix of 16 accumulative tp per time unit
	vector<int> fp ;
	vector<int> tp ;
	vector<double> curr_score ;
	vector<vector<int> > gaps ;
	map<int,int> idx_gap ;

	fp.push_back(0) ;
	tp.push_back(0) ;
	gaps.push_back(vector<int>(AUTOSIM_NGAPS,0));
	curr_score.push_back(-999.999) ;

	for (unsigned int i=0; i<scores.size(); i++) {

		int idx = scores[i].id ; // patient_id
		int type = types[ids[idx]] ;
		curr_score.push_back(scores[i].score);
		gaps.push_back(gaps[i]) ; // gaps[i+1] = gaps[i] 

		if (type == 0) {
			fp.push_back(fp.back()+1) ;
			tp.push_back(tp.back()) ;
		} else {
			int gap = scores[i].gap ;

			if (idx_gap.find(idx) == idx_gap.end()) {
				fp.push_back(fp.back()) ;
				tp.push_back(tp.back()+1) ;
				gaps[i+1][gap] ++ ;
			} else {
				// note that all counters are distinct per patient!
				// important: we already made sure in collect_all_autosim_scores that if we have 2 scores a > b than a is later than b... 
				// SO: if we encounter the same patient again we don't add to the tp/fp, and we update the per-time-unit gaps counters to the lowest score
				// E.g. if we gave a patient score 0.95 in 3 time-units before the cancer, we add 1 to the 3rd counter. 
				// Later, we encounter a score 0.74 for the same patient 8 time-units before cancer (must be >3), we deduct 1 from the 3rd counter and add 1 to the 8th counter. 
				fp.push_back(fp.back()) ; // fp[i+1] = fp
				tp.push_back(tp.back()) ; // tp[i+1] = tp
				gaps[i+1][idx_gap[idx]] -- ;
				gaps[i+1][gap] ++ ;
			}

			idx_gap[idx] = gap ; // latest gap per patient
		}
	}

	// Select Interesting points
	// Sample at different false-positive-rate points 

	int npoints = get_sim_fpr_points_num() ;
	double *sim_fpr_points = get_sim_fpr_points() ;
	int ptr = 1 ;

	double new_diff;
	double diff = 2.0 ;

	int np = tp.back() ;
	int nn = fp.back() ;
	int size = (int) fp.size() ;

	if (nn==0 || np==0)
		return ;

	double fpr ;
	int iftr = 0 ;

	for (int i=0; i<npoints; i++) {
		// Are we already at the end ?
		if (ptr > size) {
			for (int j=0; j<9; j++) 
				valid[iftr++] = false ;
		}

		// Otherwise
		while (ptr <= size) {
			if (ptr == size)
				new_diff = 2.0 ;
			else {
				fpr = (fp[ptr] + 0.0)/nn ;
				new_diff = abs(fpr - sim_fpr_points[i]/100) ;
			}

			if (new_diff <= diff) {
				diff = new_diff ;
				ptr ++ ;
			} else {
				valid[iftr] = true ; estimate[iftr++] = (double) tp[ptr-1] ; // TP
				valid[iftr] = true ; estimate[iftr++] = (double) fp[ptr-1] ; // FP
				valid[iftr] = true ; estimate[iftr++] = (tp[ptr-1]+0.0)/(tp[ptr-1] + fp[ptr-1]) ; // PPV
				valid[iftr] = true ; estimate[iftr++] = 100.0 - (100.0*fp[ptr-1])/nn ; // Specificity
				valid[iftr] = true ; estimate[iftr++] = (100.0*tp[ptr-1])/np ; // Sensitivity
				valid[iftr] = true ; estimate[iftr++]  = curr_score[ptr-1];

				// Sensitivity at 1-time-unit delay
				int count = tp[ptr-1] - gaps[ptr-1][0] ;
				valid[iftr] = true ; estimate[iftr++] = (100.0*count/np_early1) ;
				// Sensitivity at 2-time-unit delay
				count -= gaps[ptr-1][1] ;
				valid[iftr] = true ; estimate[iftr++] = (100.0*count/np_early2) ;
				// Sensitivity at 4-time-unit delay
				count -= (gaps[ptr-1][2] + gaps[ptr-1][3]) ;
				valid[iftr] = true ; estimate[iftr++] = (100.0*count/np_early3) ;
				
				if (i != npoints)
					diff = abs(fpr - sim_fpr_points[i+1]/100) ;
				ptr ++ ;
				break ;
			}
		}
	}


	// Check extra fpr point
	ptr = 1;
	diff = 2.0 ;
	if (extra_fpr != -1) {
		while (ptr <= size) {
			if (ptr == size)
				new_diff = 2.0 ;
			else {
				fpr = (fp[ptr] + 0.0)/nn ;
				new_diff = abs(fpr - extra_fpr/100.0) ;
			}

			if (new_diff <= diff) {
				diff = new_diff ;
				ptr ++ ;
			} else {
				valid[iftr] = true ; estimate[iftr++] = (double) tp[ptr-1] ; // TP
				valid[iftr] = true ; estimate[iftr++] = (double) fp[ptr-1] ; // FP
				valid[iftr] = true ; estimate[iftr++] = (tp[ptr-1]+0.0)/(tp[ptr-1] + fp[ptr-1]) ; // PPV
				valid[iftr] = true ; estimate[iftr++] = 100.0 - (100.0*fp[ptr-1])/nn ; // Specificity
				valid[iftr] = true ; estimate[iftr++] = (100.0*tp[ptr-1])/np ; // Sensitivity
				valid[iftr] = true ; estimate[iftr++]  = curr_score[ptr-1];

				// Sensitivity at 1-time-unit delay
				int count = tp[ptr-1] - gaps[ptr-1][0] ;
				valid[iftr] = true ; estimate[iftr++] = (100.0*count/np) ;
				// Sensitivity at 2-time-unit delay
				count -= gaps[ptr-1][1] ;
				valid[iftr] = true ; estimate[iftr++] = (100.0*count/np) ;
				// Sensitivity at 4-time-unit delay
				count -= (gaps[ptr-1][2] + gaps[ptr-1][3]) ;
				valid[iftr] = true ; estimate[iftr++] = (100.0*count/np) ;


				ptr ++ ;
				break ;
			}
		}
	}
}

// Work Seperately on scores in each period 
void get_periodic_autosim_parameters(int *ids, int *types, int *id_starts, int *id_nums, int nids, double *all_scores, int *all_gaps, int *all_days, 
									vector<double>& estimate, quick_random& qrand , double extra_fpr, int first_days, int period, int nperiods, int tot_autosim_nestimates, int autosim_nestimates, vector<bool>& valid) {


	assert(ntime_unit_delays==3) ;

	// Create scores vector
	vector<periodic_autosim_score> scores ;
	for (int i=0; i<nids; i++) {
		for (int j=0; j<id_nums[ids[i]]; j++) {
			periodic_autosim_score new_score ;
			new_score.id = i ;
			new_score.score = all_scores[id_starts[ids[i]] + j] ;
			new_score.gap = min(AUTOSIM_NGAPS-1,all_gaps[id_starts[ids[i]]+j]/AUTOSIM_GAP) ;
			new_score.iperiod = (all_days[id_starts[ids[i]]+j] - first_days)/period ;
			scores.push_back(new_score) ;
		}
	}
	
	shuffle_vector(scores, qrand) ;
	sort(scores.begin(),scores.end(),rev_compare_periodic_autosim_scores()) ;
	
	// Create Full Histogram
	map<int, vector<int> > fp ;
	map<int, vector<int> > tp ;
	map<int, vector<double> > curr_score ;
	map <int, vector<vector<int> > > gaps ;
	map <int, map<int,int> > idx_gap ;
	map <int, int> counters ;
	for (int i=0; i<nperiods; i++) {
		fp[i].push_back(0) ;
		tp[i].push_back(0) ;
		curr_score[i].push_back(-999.999) ;
		gaps[i].resize(1) ;
		gaps[i][0].resize(AUTOSIM_NGAPS,0) ;
		counters[i] = 0 ;
	}

	for (unsigned int i=0; i<scores.size(); i++) {
		int iperiod = scores[i].iperiod ;
		int idx = scores[i].id ;
		int type = types[ids[idx]] ;
		curr_score[iperiod].push_back(scores[i].score);

		gaps[iperiod].push_back(gaps[iperiod][counters[iperiod]]) ;
	
		if (type == 0) {
			fp[iperiod].push_back(fp[iperiod].back()+1) ;
			tp[iperiod].push_back(tp[iperiod].back()) ;
		} else {
			int gap = scores[i].gap ;

			if (idx_gap[iperiod].find(idx) == idx_gap[iperiod].end()) {
				fp[iperiod].push_back(fp[iperiod].back()) ;
				tp[iperiod].push_back(tp[iperiod].back()+1) ;
				gaps[iperiod][counters[iperiod]+1][gap] ++ ;
			} else {
				fp[iperiod].push_back(fp[iperiod].back()) ;
				tp[iperiod].push_back(tp[iperiod].back()) ;
				gaps[iperiod][counters[iperiod]+1][idx_gap[iperiod][idx]] -- ;
				gaps[iperiod][counters[iperiod]+1][gap] ++ ;
			}

			idx_gap[iperiod][idx] = gap ;
		}
		counters[iperiod]++ ;
	}

	// Select Interesting points
	// Sample at different false-positive-rate points 
	int npoints = get_sim_fpr_points_num() ;
	double *sim_fpr_points = get_sim_fpr_points() ;
	int iftr = 0 ;

	for (int iperiod=0; iperiod < nperiods; iperiod ++) {
		int ptr = 1 ;

		double new_diff;
		double diff = 2.0 ;

		int size = (int) fp[iperiod].size() ;
		if (size == 0) {
			iftr += autosim_nestimates ;
			valid.resize((iperiod+1)*autosim_nestimates,false) ;
			continue ;
		}

		int np = tp[iperiod].back() ;
		int nn = fp[iperiod].back() ;

		if (np == 0 || nn == 0) {
			iftr += autosim_nestimates ;
			valid.resize((iperiod+1)*autosim_nestimates,false) ;
			continue ;
		}
	
		valid.resize((iperiod+1)*autosim_nestimates,true) ;

		double fpr ;
		for (int i=0; i<npoints; i++) {
			// Are we already at the end ?
			if (ptr > size) {
				for (int j=0; j<9; j++) 
					valid[iftr++] = false ;
			}

			// Otherwise
			while (ptr <= size) {
				if (ptr == size)
					new_diff = 2.0 ;
				else {
					fpr = (fp[iperiod][ptr] + 0.0)/nn ;
					new_diff = abs(fpr - sim_fpr_points[i]/100) ;
				}

				if (new_diff <= diff) {
					diff = new_diff ;
					ptr ++ ;
				} else {
					estimate[iftr++] = (double) tp[iperiod][ptr-1] ; // TP
					estimate[iftr++] = (double) fp[iperiod][ptr-1] ; // FP
					estimate[iftr++] = (tp[iperiod][ptr-1]+0.0)/(tp[iperiod][ptr-1] + fp[iperiod][ptr-1]) ; // PPV
					estimate[iftr++] = 100.0 - (100.0*fp[iperiod][ptr-1])/nn ; // Specificity
					estimate[iftr++] = (100.0*tp[iperiod][ptr-1])/np ; // Sensitivity
					estimate[iftr++]  = curr_score[iperiod][ptr-1];

					// Sensitivity at 1-time-unit delay
					int count = tp[iperiod][ptr-1] - gaps[iperiod][ptr-1][0] ;
					estimate[iftr++] = (100.0*count/np) ;
					// Sensitivity at 2-time-unit delay
					count -= gaps[iperiod][ptr-1][1] ;
					estimate[iftr++] = (100.0*count/np) ;
					// Sensitivity at 4-time-unit delay
					count -= (gaps[iperiod][ptr-1][2] + gaps[iperiod][ptr-1][3]) ;
					estimate[iftr++] = (100.0*count/np) ;

					if (i != npoints)
						diff = abs(fpr - sim_fpr_points[i+1]/100) ;
					ptr ++ ;
					break ;
				}
			}
		}
		
		// Check extra fpr point
		ptr = 1;
		if (extra_fpr != -1) {
			while (ptr <= size) {
				if (ptr == size)
					new_diff = 2.0 ;
				else {
					fpr = (fp[iperiod][ptr] + 0.0)/nn ;
					new_diff = abs(fpr - extra_fpr/100.0) ;
				}

				if (new_diff <= diff) {
					diff = new_diff ;
					ptr ++ ;
				} else {
					estimate[iftr++] = (double) tp[iperiod][ptr-1] ; // TP
					estimate[iftr++] = (double) fp[iperiod][ptr-1] ; // FP
					estimate[iftr++] = (tp[iperiod][ptr-1]+0.0)/(tp[iperiod][ptr-1] + fp[iperiod][ptr-1]) ; // PPV
					estimate[iftr++] = 100.0 - (100.0*fp[iperiod][ptr-1])/nn ; // Specificity
					estimate[iftr++] = (100.0*tp[iperiod][ptr-1])/np ; // Sensitivity
					estimate[iftr++]  = curr_score[iperiod][ptr-1];

					// Sensitivity at 1-time-unit delay
					int count = tp[iperiod][ptr-1] - gaps[iperiod][ptr-1][0] ;
					estimate[iftr++] = (100.0*count/np) ;
					// Sensitivity at 2-time-unit delay
					count -= gaps[iperiod][ptr-1][1] ;
					estimate[iftr++] = (100.0*count/np) ;
					// Sensitivity at 4-time-unit delay
					count -= (gaps[iperiod][ptr-1][2] + gaps[iperiod][ptr-1][3]) ;
					estimate[iftr++] = (100.0*count/np) ;

					ptr ++ ;
					break ;
				}
			}
		}
	}

	return ;
}


void get_periodic_cuts_parameters(int *ids, int *types, int *id_starts, int *id_nums, int nids, double *all_scores, int *all_time_to_cancer, int *all_days, 
									vector<double>& estimate, quick_random& qrand , double extra_fpr, int first_days, int period, int nperiods, int tot_autosim_nestimates, int autosim_nestimates, vector<bool>& valid) {

	assert(ntime_unit_delays==3) ;

	// Create scores vector
	vector<periodic_autosim_score> scores ;
	for (int i=0; i<nids; i++) {
		for (int j=0; j<id_nums[ids[i]]; j++) {
			periodic_autosim_score new_score ;
			new_score.id = i ;
			new_score.score = all_scores[id_starts[ids[i]] + j] ;
			new_score.gap = min(CUT_NGAPS-1,all_time_to_cancer[id_starts[ids[i]]+j]/CUT_GAP) ;
			new_score.iperiod = (all_days[id_starts[ids[i]]+j] - first_days)/period ;
			scores.push_back(new_score) ;
		}
	}

	shuffle_vector(scores, qrand) ;
	sort(scores.begin(),scores.end(),rev_compare_periodic_autosim_scores()) ;

	// Create Full Histogram
	map<int, vector<int> > fp ;
	map <int, vector<vector<int> > > tps ;
	map<int, vector<double> > curr_score ;
	map <int, int> counters ; ;
	
	for (int i=0; i<nperiods; i++) {
		fp[i].push_back(0) ;
		tps[i].resize(1) ;
		tps[i][0].resize(CUT_NGAPS,0) ;
		curr_score[i].push_back(-999.999) ;
		counters[i] = 0 ;
	}
			
	for (unsigned int i=0; i<scores.size(); i++) {
		int iperiod = scores[i].iperiod ;
		int idx = scores[i].id ;
		int type = types[ids[idx]] ;
		int gap = scores[i].gap ;
		curr_score[iperiod].push_back(scores[i].score);

		tps[iperiod].push_back(tps[iperiod].back()) ;
		fp[iperiod].push_back(fp[iperiod].back()) ;

		if (type == 0)
			fp[iperiod].back() ++ ;
		else {
			for (int j=0; j<= gap; j++)
				tps[iperiod][counters[iperiod]+1][j]++ ;

		}
		counters[iperiod]++ ;
	}

	// Select Interesting points
	// Sample at different false-positive-rate points 
	int npoints = get_sim_fpr_points_num() ;
	double *sim_fpr_points = get_sim_fpr_points() ;
	int iftr = 0 ;

	for (int iperiod=0; iperiod < nperiods; iperiod ++) {
		int ptr = 1 ;

		double new_diff;
		double diff = 2.0 ;

		int size = (int) fp[iperiod].size() ; 
		if (size == 0) {
			iftr += autosim_nestimates ;
			valid.resize((iperiod+1)*autosim_nestimates,false) ;
			continue ;
		}

		vector<int> nps ;
		for (int i=0; i<CUT_NGAPS; i++) 
			nps.push_back((tps[iperiod].back())[i]) ;

		int nn = fp[iperiod].back() ;

		if (nps[0] == 0 || nn == 0) {
			iftr += autosim_nestimates ;
			valid.resize((iperiod+1)*autosim_nestimates,false) ;
			continue ;
		}

		valid.resize((iperiod+1)*autosim_nestimates,true) ;
		double fpr ;
		for (int i=0; i<npoints; i++) {
			// Are we already at the end ?
			if (ptr > size) {
				for (int j=0; j<9; j++) 
					valid[iftr++] = false ;
			}

			// Otherwise
			while (ptr <= size) {
				if (ptr == size)
					new_diff = 2.0 ;
				else {
					fpr = (fp[iperiod][ptr] + 0.0)/nn ;
					new_diff = abs(fpr - sim_fpr_points[i]/100) ;
				}

				if (new_diff <= diff) {
					diff = new_diff ;
					ptr ++ ;
				} else {
					estimate[iftr++] = (double) tps[iperiod][ptr-1][0] ; // TP
					estimate[iftr++] = (double) fp[iperiod][ptr-1] ; // FP
					estimate[iftr++] = (tps[iperiod][ptr-1][0]+0.0)/(tps[iperiod][ptr-1][0] + fp[iperiod][ptr-1]) ; // PPV
					estimate[iftr++] = 100.0 - (100.0*fp[iperiod][ptr-1])/nn ; // Specificity
					estimate[iftr++] = (100.0*tps[iperiod][ptr-1][0])/nps[0] ; // Sensitivity
					estimate[iftr++]  = curr_score[iperiod][ptr-1];

					// Sensitivity at 1,2,4-time-unit delay
					for (int it=0; it<3; it++) {
						if (nps[time_unit_delays[it]])
							estimate[iftr++] = (100.0*tps[iperiod][ptr-1][time_unit_delays[it]]/nps[time_unit_delays[it]]) ; 
						else
							valid[iftr++] = false ;
					}
				
					if (i != npoints)
						diff = abs(fpr - sim_fpr_points[i+1]/100) ;
					ptr ++ ;
					break ;
				}
			}
		}

		// Check extra fpr point
		ptr = 1;
		if (extra_fpr != -1) {
			while (ptr <= size) {
				if (ptr == size)
					new_diff = 2.0 ;
				else {
					fpr = (fp[iperiod][ptr] + 0.0)/nn ;
					new_diff = abs(fpr - extra_fpr/100.0) ;
				}

				if (new_diff <= diff) {
					diff = new_diff ;
					ptr ++ ;
				} else {
					estimate[iftr++] = (double) tps[iperiod][ptr-1][0] ; // TP
					estimate[iftr++] = (double) fp[iperiod][ptr-1] ; // FP
					estimate[iftr++] = (tps[iperiod][ptr-1][0]+0.0)/(tps[iperiod][ptr-1][0] + fp[iperiod][ptr-1]) ; // PPV
					estimate[iftr++] = 100.0 - (100.0*fp[iperiod][ptr-1])/nn ; // Specificity
					estimate[iftr++] = (100.0*tps[iperiod][ptr-1][0])/nps[0] ; // Sensitivity
					estimate[iftr++]  = curr_score[iperiod][ptr-1];

					// Sensitivity at 1,2,4-time-unit delay
					for (int it=0; it<3; it++) {
						if (nps[time_unit_delays[it]])
							estimate[iftr++] = (100.0*tps[iperiod][ptr-1][time_unit_delays[it]]/nps[time_unit_delays[it]]) ;
						else
							valid[iftr++] = false ;
					}

					ptr ++ ;
					break ;
				}
			}
		}

	}

	return ;
}


int get_binary_autosim_parameters(int *ids, int *types, int nids, int *gaps, vector<double>& estimate) {

	assert(ntime_unit_delays==3) ;

	int fp=0, tn=0 ;
	int tp[4], fn[4] ;
	for (int i=0; i<4; i++)
		tp[i] = fn[i] = 0 ;

	// Interesting points - Anything, 1, 2, and 4 time-units
	for (int i=0; i<nids; i++) {
		if (types[ids[i]]==0) {
			if (gaps[ids[i]] > 0)
				fp ++ ;
			else 
				tn ++ ;
		} else {

			int max_gap ;
			if (gaps[ids[i]] == -1)
				max_gap = -1 ;
			else if (gaps[ids[i]] <= time_unit_delays[0]*AUTOSIM_GAP)
				max_gap = 0 ;
			else if (gaps[ids[i]] <= time_unit_delays[1]*AUTOSIM_GAP)
				max_gap = 1 ;
			else if (gaps[ids[i]] <= time_unit_delays[2]*AUTOSIM_GAP)
				max_gap =2 ;
			else
				max_gap = 3;

			for (int igap=0; igap<max_gap; igap++)
				tp[igap] ++ ;
			for (int igap=max_gap; igap<4; igap++)
				fn[igap]++ ;
		}
	}



				
	int iftr = 0 ;
	int npos = tp[0] + fn[0] ;
	int nneg = tn + fp ;

	estimate[iftr++] = (double) tp[0] ; // TP
	estimate[iftr++] = (double) fp ; // FP
	estimate[iftr++] = (tp[0]+0.0)/(tp[0] + fp) ; // PPV
	estimate[iftr++] = 100.0 - (100.0*fp)/nneg ; // Specificity
	estimate[iftr++] = (100.0*tp[0])/npos ; // Sensitivity
	estimate[iftr++] = (100.0*tp[1])/npos ; // Sensitivity at first time-unit delay
	estimate[iftr++] = (100.0*tp[2])/npos ; // Sensitivity at second time-unit delay
	estimate[iftr++] = (100.0*tp[3])/npos ; // Sensitivity at third time-unit delay

	return 0 ;

}

// Create a matrix for Cox hazard ratio analysis.
int create_matrix_for_cox(map<string,vector<score_entry> >& all_scores, map<string,vector<pair<int,int> > >& registry, int last_date,
						  pair<int,int> &initialization_date, pair<int, int>& age_range, map<string,int>& byears, map<string, status>& censor, char *matrix_file) {

	int last_days = get_day(last_date) ;

	FILE *fp = fopen(matrix_file,"w") ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for wrinting\n",matrix_file) ;
		return -1 ;
	}

	fprintf(fp,"Score\tCRC\ttime\n") ;

	// Loop on ids.
	for (map<string,vector<score_entry> >::iterator it=all_scores.begin(); it!=all_scores.end(); it++) {
		string id = it->first ;

		// Age Range
		int age = initialization_date.first/10000 - byears[id] ;
		if (age < age_range.first || age > age_range.second)
			continue ;

		int init_day = get_day(initialization_date.second) ;
		int pre_init_day = get_day(initialization_date.first) ;

		// Censor
		if (censor.find(id) != censor.end() && censor[id].days < init_day)
			continue ;

		// Relevant score
		int score_day = -1 ;
		double score ;

		for (unsigned int iscore=0; iscore<all_scores[id].size(); iscore++) {
			if (all_scores[id][iscore].days >= pre_init_day && all_scores[id][iscore].days <= init_day && (score_day == -1 || 
				all_scores[id][iscore].days > score_day)) {
				score_day = all_scores[id][iscore].days ;
				score = all_scores[id][iscore].score ;
			}
		}

		if (score_day == -1)
			continue ;

		// Censoring/Cancer date ...
		int last_day = -1;
		int cancer = 0 ;
		if (registry.find(id) != registry.end()) {
			for (unsigned int ireg = 0 ; ireg < registry[id].size(); ireg ++) {
				if (registry[id][ireg].second != 3 && (last_day == -1 || registry[id][ireg].first < last_day)) {
					last_day = registry[id][ireg].first ;
					cancer = registry[id][ireg].second ;
				}
			}
		}

		if (last_day == -1) {
			last_day = last_days ;
			if (censor.find(id) != censor.end() && censor[id].days < last_day)
				last_day = censor[id].days ;
		}

		if (last_day > init_day && cancer != 2)
			fprintf(fp,"%f\t%d\t%d\n",score,cancer,last_day-init_day) ;
	}

	fclose(fp) ;
	return 0 ;
}

int perform_cox_analysis(char *matrix_file, const char *out_dir)  {

	// Create R script

	char script_file[MAX_STRING_LEN] ;
	sprintf(script_file,"%s\\%s",out_dir,COX_SCRIPT_FILE) ;
	FILE *rfp = fopen(script_file,"w") ;
	if (rfp==NULL) {
		fprintf(stderr,"Cannot open %s for wrinting\n",script_file) ;
		return -1 ;
	}

	fprintf(rfp,"library(survival) ;\n") ;
	fprintf(rfp,"data <- read.table(\"%s\",header=T) ;\n",matrix_file); 
	fprintf(rfp,"cox.model <- coxph(Surv(time,CRC) ~ Score, data=data) ;\n") ;
	fprintf(rfp,"sink(\"%s/Summary\") ;\n",out_dir) ;
	fprintf(rfp,"summary(cox.model) ;\n") ;
	fprintf(rfp,"sink() ;\n") ;

	fprintf(rfp,"jpeg(\"%s/Survival.jpeg\") ;\n",out_dir) ;
	fprintf(rfp,"scores <- sort(data$Score[data$CRC==1 & data$time<360]) ;\n") ;
	fprintf(rfp,"points <- c(min(scores),scores[floor(0.5*length(scores))],max(scores)) ;\n") ;
	fprintf(rfp,"newdata <- data.frame(Score=points) ;\n") ;
	fprintf(rfp,"plot(survfit(cox.model,newdata=newdata),conf.int=T,col=c(\"red\",\"blue\",\"green\"),xlim=c(0,720),ylim=c(0.99,1.0)) ;\n") ;
	fprintf(rfp,
		"legend(\"bottomleft\",c(sprintf(\"score = %%.2f\",points[1]),sprintf(\"score = %%.2f\",points[2]),sprintf(\"score = %%.2f\",points[3])),lty=1,col=c(\"red\",\"blue\",\"green\")) ;\n") ;

	fclose(rfp) ;

	// Run script
	char std_file[MAX_STRING_LEN] ;
	sprintf(std_file,"%s\\%s",out_dir,COX_STDOUT_FILE) ;

	char cmd[MAX_STRING_LEN] ;
	sprintf(cmd,"%s %s %s",R_EXEC,script_file,std_file) ; 
	if (system(cmd) != 0) {
		fprintf(stderr,"%s failed\n",cmd) ;
		return -1 ;
	}

	return 0 ;
}

// helper function for the quick_random class
void quick_random::shuffle() {		
	int shuffle_parity = ((globalRNG::rand() + 0.0)/globalRNG::max() > 0.5) ? 1 : 0 ;
	int shuffle_step = globalRNG::rand() % vec_size ;
	fprintf(stderr," (Randomizing %d) ",shuffle_step) ;

	for (int i=0; i<vec_size; i+=2) {
		double temp = vec[i + shuffle_parity] ;
		vec[i + shuffle_parity] = vec[(i + shuffle_parity + shuffle_step) % vec_size] ;
		vec[(i + shuffle_parity + shuffle_step) % vec_size] = temp ;
	}
}

// priary method of quick_random class:
// provide the current random number and reshuffle internal reservoir, if needed
double quick_random::random() {
	if (irand == vec_size) {
		irand = 0;
		shuffle();
	}
	double res = vec[irand];
	irand++;

	return res;
}

// random shuffling of a vector
template<typename T>
void shuffle_vector(vector<T>& input, quick_random& qrand) {
	int nrows = (int) input.size() ;

	for (int i = 0; i < nrows; i++) {
		double r = qrand.random() ;
		int id = (int) (r*(nrows-i)) ;
	
		T temp = input[i + id] ;
		input[i + id] = input[i] ;
		input[i] = temp ;
	}
}

// An envelop for reading all input data
int read_all_input_data(po::variables_map& vm, bool inc_from_pred, bool mhs_reg_format, bool simple_reg_format, bool read_reg_from_scores, input_data& indata) {

	// Read removal file
	if (vm.count("rem") == 1) {
		string rem_file ;
		fix_path(vm["rem"].as<string>(),rem_file) ;
		if (read_list(rem_file.c_str(), indata.remove_list) == -1) {
			fprintf(stderr,"Could not read removal list from file \'%s\'\n", rem_file.c_str()) ;
			return -1 ;
		}
	}

	// Read inclsion file
	if (vm.count("inc") == 1)  {
		string inc_file ;
		fix_path(vm["inc"].as<string>(),inc_file) ;
		if (inc_from_pred)	{
			if (read_list_from_scores(inc_file.c_str(),vm["nbin_types"].as<int>(),indata.include_list, read_reg_from_scores, indata.registry, indata.censor, vm["pred_col"].as<string>()) == -1) {
				fprintf(stderr,"Could not read inclusion list from scores file \'%s\'\n", inc_file.c_str()) ;
				return -1 ;
			}
		} else if (read_list(inc_file.c_str(), indata.include_list) == -1) {
				fprintf(stderr,"Could not read inclusion list from file \'%s\'\n", vm["inc"].as<string>().c_str()) ;
				return -1 ;
		}
	}

	fprintf(stderr, "Before reading scores\n"); fflush(stderr);
	// Read Scores File
	string scores_file;
	fix_path(vm["in"].as<string>(),scores_file) ;
	fprintf(stderr, "Before read_scores()\n"); fflush(stderr);
	int nscores = read_scores(scores_file.c_str(), indata.all_scores, indata.run_id, vm["nbin_types"].as<int>(),
		indata.include_list, indata.remove_list, read_reg_from_scores, indata.registry, indata.censor, vm["pred_col"].as<string>());
	if (nscores == -1) {
		fprintf(stderr, "Could not read scores from file \'%s\'\n", vm["in"].as<string>().c_str()) ;
		return -1 ;
	}
	fprintf(stderr, "After reading scores\n"); fflush(stderr);

	// Read Cancer Directions File
	if (simple_reg_format || read_reg_from_scores) {
		fprintf(stderr, "Using simple_reg_format/read_reg_from_scores, no need for directions file\n");
	} else {
		string directions_file;
		fix_path(vm["dir"].as<string>(), directions_file);
		if (read_cancer_directions(directions_file.c_str(), indata.cancer_directions) == -1) {
			fprintf(stderr, "Could not read cancer directions from file \'%s\'\n", directions_file.c_str());
			return -1;
		}
	}

	// Read Age-Dependent Incidence File
	if (vm.count("prbs") == 1) {
		string prbs_file ;
		fix_path(vm["prbs"].as<string>(),prbs_file) ;
		if (read_probs(prbs_file.c_str(),indata.incidence_rate) == -1) {
			fprintf(stderr,"Could not read age-dependent incidence from file \'%s\'\n",prbs_file.c_str()) ;
			return -1 ;
		}
	}

	// Read Extra Params
	string params_file ;
	fix_path(vm["params"].as<string>(),params_file) ;
	if (read_extra_params(params_file.c_str(), indata.time_windows, indata.age_ranges, &(indata.first_date), &(indata.last_date), &(indata.age_seg_num), &(indata.max_status_year))==-1) {
		fprintf(stderr,"Could not read extra parameters from file \'%s\'\n", params_file.c_str()) ;
		return -1 ;
	}

	fprintf(stderr, "FirstDate: %d LastDate: %d\n", indata.first_date, indata.last_date); 
	// Read Cancer Registry
	if (read_reg_from_scores)
		fprintf(stderr, "Already read registry from scores file\n");
	else {
		string reg_file;
		fix_path(vm["reg"].as<string>(), reg_file);
		if (mhs_reg_format) {
			if (read_mhs_cancer_registry(reg_file.c_str(), indata.cancer_directions, indata.registry) == -1) {
				fprintf(stderr, "Could not read cancer registry in MHS format from file \'%s\'\n", reg_file.c_str());
				return -1;
			}
		}
		else if (simple_reg_format)
			read_simple_registry(reg_file.c_str(), indata.registry);
		else {
			if (read_cancer_registry(reg_file.c_str(), indata.cancer_directions, indata.registry) == -1) {
				fprintf(stderr, "Could not read cancer registry from file \'%s\'\n", reg_file.c_str());
				return -1;
			}
		}
	}
	// Read birth-years
	string byears_file ;
	fix_path(vm["byear"].as<string>(),byears_file) ;
	if (read_byears(byears_file.c_str(), indata.byears) == -1) {
		fprintf(stderr, "Could not read birth years from file \'%s\'\n", byears_file.c_str()) ;
		return -1 ;
	}

	// Read censoring data
	string censor_file ;
	fix_path(vm["censor"].as<string>(),censor_file) ;
	if (read_censor(censor_file.c_str(), indata.censor) == -1) {
		fprintf(stderr,"Could not read censoring status from file \'%s\'\n", censor_file.c_str()) ;
		return -1 ;
	}

	return 0 ;
}

// An envelop for reading all input data
int read_all_input_data_for_oxford(po::variables_map& vm, input_data& indata) {

	// Read Input File
	string in_file = vm["in"].as<string>();
	string req_gender = vm["gender"].as<string>();
	if (read_oxford_input(in_file.c_str(), req_gender, indata) == -1) {
		fprintf(stderr, "Could not read input data from file \'%s\'\n", vm["in"].as<string>().c_str());
		return -1;
	}

	// Read Age-Dependent Incidence File
	if (vm.count("prbs") == 1) {
		string prbs_file;
		fix_path(vm["prbs"].as<string>(), prbs_file);
		if (read_probs(prbs_file.c_str(), indata.incidence_rate) == -1) {
			fprintf(stderr, "Could not read age-dependent incidence from file \'%s\'\n", prbs_file.c_str());
			return -1;
		}
	}

	// Read Extra Params
	string params_file;
	fix_path(vm["params"].as<string>(), params_file);
	if (read_extra_params_for_oxford(params_file.c_str(), indata.time_windows, indata.age_ranges, &(indata.age_seg_num)) == -1) {
		fprintf(stderr, "Could not read extra parameters from file \'%s\'\n", params_file.c_str());
		return -1;
	}

	indata.first_date = vm["first_date"].as<int>(); 
	indata.last_date = vm["last_date"].as<int>();
	indata.max_status_year = indata.last_date / 10000;

	return 0;
}

// Open output files and write headers
int open_output_files(const char *out_file, running_flags& flags, char *param_names, int nestimates, char *autosim_param_names, int autosim_nestimates, out_fps& fouts) {

	char raw_file_name[MAX_STRING_LEN] ;
	sprintf(raw_file_name,"%s.Raw", out_file) ;
	fouts.raw_fout = fopen(raw_file_name,"w") ;
	if (fouts.raw_fout == NULL) {
		fprintf(stderr,"Could not open raw output file \'%s\' for writing\n",raw_file_name) ;
		return -1 ;
	}
	fprintf(stderr, "open raw output file \'%s\' for writing\n", raw_file_name);

	if (flags.raw_only) { // .Info file is printed only in raw_only mode in order to prevent leakage of external validation registry
		char info_file_name[MAX_STRING_LEN] ;
		sprintf(info_file_name,"%s.Info", out_file) ;
		fouts.info_fout = fopen(info_file_name,"w") ;
		if (fouts.info_fout == NULL) {
			fprintf(stderr,"Could not open info output file \'%s\' for writing\n",info_file_name) ;
			return -1 ;
		}
		fprintf(stderr, "open info output file \'%s\' for writing\n", info_file_name);
	}

	if (flags.auto_sim_raw) {
		char sim_raw_file_name[MAX_STRING_LEN] ;
		sprintf(sim_raw_file_name,"%s.AutoSimRaw", out_file) ;
		fouts.sim_raw_fout = fopen(sim_raw_file_name,"w") ;
		if (fouts.sim_raw_fout == NULL) {
			fprintf(stderr,"Could not open sim raw output file \'%s\' for writing\n",sim_raw_file_name) ;
			return -1 ;
		}
		fprintf(stderr, "open sim raw output file \'%s\' for writing\n", sim_raw_file_name);
	}


	if (! flags.raw_only) {
		// Open files
		fouts.fout = fopen(out_file, "w") ;
		if (fouts.fout == NULL) {
			fprintf(stderr,"Could not open output file \'%s\' for writing\n", out_file) ;
			return -1 ;
		}
		fprintf(stderr, "open output file \'%s\' for writing\n", out_file);

		char autosim_file_name[MAX_STRING_LEN] ;
		sprintf(autosim_file_name,"%s.AutoSim", out_file) ;
		fouts.autosim_fout = fopen(autosim_file_name, "w") ;
		if (fouts.autosim_fout == NULL) {
			fprintf(stderr,"Could not open autosim output file \'%s\' for writing\n", autosim_file_name) ;
			return -1 ;
		}
		fprintf(stderr, "open autosim output file \'%s\' for writing\n", autosim_file_name);

		// Headers
		fprintf(fouts.fout,"Time-Window\tAge-Range\tCheckSum\tNBootStrap") ;

		for (int i=0; i<nestimates; i++)
			fprintf(fouts.fout,"\t%s-Obs\t%s-Mean\t%s-Sdv\t%s-CI-Lower\t%s-CI-Upper",param_names+i*MAX_STRING_LEN,param_names+i*MAX_STRING_LEN,param_names+i*MAX_STRING_LEN,param_names+i*MAX_STRING_LEN,param_names+i*MAX_STRING_LEN) ;
		fprintf(fouts.fout,"\n") ;

		fprintf(fouts.autosim_fout,"Age-Range\tCheckSum\tNBootStrap") ;
		for (int i=0; i<autosim_nestimates; i++)
			fprintf(fouts.autosim_fout,"\t%s-Obs\t%s-Mean\t%s-Sdv\t%s-CI-Lower\t%s-CI-Upper",autosim_param_names+i*MAX_STRING_LEN,autosim_param_names+i*MAX_STRING_LEN,autosim_param_names+i*MAX_STRING_LEN,
																					 autosim_param_names+i*MAX_STRING_LEN,autosim_param_names+i*MAX_STRING_LEN) ;
		fprintf(fouts.autosim_fout,"\n") ;
	}

	return 0 ;
}

// Allocation
int allocate_data(input_data& indata, work_space& work) {

	int nall_ids =(int)  indata.all_scores.size() ;
	int nall_scores = 0 ;
	for (auto it=indata.all_scores.begin(); it != indata.all_scores.end(); it++)
		nall_scores += (int) ((it->second).size()) ;

	work.idstrs.clear() ;
	work.days = (int *) malloc(nall_scores*sizeof(int)) ;
	work.dates = (int *) malloc(nall_scores*sizeof(int)) ;
	work.years = (int *) malloc(nall_scores*sizeof(int)) ;
	work.scores = (double *) malloc(nall_scores*sizeof(double)) ;
	work.id_starts = (int *) malloc(nall_ids*sizeof(int)) ;
	work.id_nums = (int *) malloc (nall_ids*sizeof(int)) ;
	work.types = (int *) malloc(nall_ids*sizeof(int)) ;
	work.gaps = (int *) malloc(nall_scores*sizeof(int)) ;
	work.ages = (int *) malloc(nall_scores*sizeof(int)) ;
	work.time_to_cancer = (int *) malloc(nall_scores*sizeof(int)) ;

	if (work.dates==NULL || work.scores==NULL || work.id_starts==NULL || work.id_nums==NULL || work.types==NULL || work.gaps==NULL || work.ages==NULL || work.time_to_cancer==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	} else
		return 0 ;
}

// Print bootstrap output
void print_bootstrap_output(vector<vector<double> >& estimates, vector<double>& obs, int nestimates, int nbootstrap, vector<vector<bool> >& valid, vector<bool>& valid_obs, FILE *fp) {

	for (int l=0; l<nestimates; l++) {

		// Observable
		if (valid_obs[l])
			fprintf(fp,"\t%.3f",obs[l]) ;
		else
			fprintf(fp,"\tNA") ;

		// Bootstrap Estimate
		vector<double> values ;
		int num = 0 ;
		double sum = 0, sum2 = 0  ;
		for (int k=0; k<nbootstrap; k++) {
			if (valid[k][l]) {
				double value = estimates[k][l] ;
				sum += value ;
				sum2 += value * value ;
				values.push_back(value) ;
				num++ ;
			}
		}

		if (num) {
			sort(values.begin(),values.end()) ;
			double mean = sum/num ;
			double sdv = sqrt((sum2 - sum*mean)/(num-1)) ;
			double ci_lower = values[(int)(0.025*num)] ;
			double ci_upper = values[(int)(0.975*num)] ;
			fprintf(fp,"\t%.3f\t%.3f\t%.3f\t%.3f",mean,sdv,ci_lower,ci_upper) ;
		} else
			fprintf(fp,"\tNA\tNA\tNA\tNA") ;
	}
}

/* Working points */

double fpr_points[] = {0.1,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,10} ;
double sens_points[] = {5,10,20,30,40,50,60,70,80,90} ;
double score_points[] = { 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0 };
double sim_fpr_points[] = {0.1,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,10,15,20,25,30} ;

/* Extensive list of FP points for time windows */
double all_fpr_points[] = { 0.1,0.3,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20 };

//double fpr_points[] = {1} ;
//double sens_points[] = {20,40,60,80,90,95,99} ;
//double sim_fpr_points[] = {1} ;


/* Access working points */
int get_fpr_points_num(bool all_fpr) {
	if (all_fpr)
		return sizeof(all_fpr_points) / sizeof(double);
	return sizeof(fpr_points)/sizeof(double) ;
}

double *get_fpr_points(bool all_fpr) {
	if (all_fpr)
		return all_fpr_points;
	return fpr_points ;
}

int get_sens_points_num() {
	return sizeof(sens_points)/sizeof(double) ;
}

double *get_sens_points() {
	return sens_points ;
}

int get_score_points_num() {
	return sizeof(score_points) / sizeof(double);
}

double *get_score_points() {
	return score_points;
}

int get_sim_fpr_points_num() {
	return sizeof(sim_fpr_points)/sizeof(double) ;
}

double *get_sim_fpr_points() {
	return sim_fpr_points ;
}