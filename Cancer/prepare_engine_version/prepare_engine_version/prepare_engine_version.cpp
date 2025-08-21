// Prepare engine for MS_CRC_Scorer based on setup file //

#define _CRT_SECURE_NO_WARNINGS
#include "prepare_engine_version.h"

int main(int argc, char *argv[]) {

	// Open input file
	if (argc != 4) {
		fprintf(stderr,"Usage : %s method SetUpFile EngineDirectory\n",argv[0]) ;
		return -1 ;
	}

	int method ;
	if (strcmp(argv[1],"rfgbm")==0) {
		method = 0 ;
	} else {
		fprintf(stderr,"Method %s not implemented (yet ?). Quitting\n",argv[1]) ;
		return -1 ;
	}

	FILE *setup_fp = fopen(argv[2],"r") ;
	assert(setup_fp != NULL) ;

	char dir[MAX_STRING_LEN] ;
	strcpy(dir,argv[3]) ;

	// Initialize
	char test_names[NTESTS][MAX_STRING_LEN] = {"RBC","WBC","MPV","Hemoglobin","Hematocrit","MCV","MCH","MCHC-M","RDW","Platelets","Eosinophils #","Neutrophils %",
		"Monocytes %","Eosinophils %","Basophils %","Neutrophils #","Monocytes #","Basophils #","Lymphocytes %","Lymphocytes #"} ;

	map<string,int> test_cols ;
	for (int i=0; i<NTESTS; i++)
		test_cols[test_names[i]] = i + 1;

	char all_file_names[1][NFILES][MAX_STRING_LEN] = {{"Features","Extra","menParams","menLM","menRF","menGBM","menComb","womenParams","womenLM","womenRF","womenGBM","womenComb"}} ;

	map<string,int> file_cnt ;
	for (int i=0; i<NFILES; i++)
		file_cnt[all_file_names[method][i]] = 0 ;

	//Read instructions
	map<string,string> file_names ;

	char name[MAX_STRING_LEN],type[MAX_STRING_LEN] ;

	while (!feof(setup_fp)) {
		int rc = fscanf(setup_fp,"%s %s\n",type,name) ;
		if (rc == EOF)
			break ;
		assert(rc == 2) ;
	
		if (file_cnt.find(type) == file_cnt.end() || file_cnt[type] != 0) {
			fprintf(stderr,"Problems with %s\n",type) ;
			return -1 ;
		}

		file_cnt[type] ++ ;
		file_names[type] = name ;
	}
	fclose(setup_fp) ;

	for (int i=0; i<NFILES; i++)
		assert(file_cnt[all_file_names[method][i]] == 1) ;

	//Read Features
	FILE *features_fp = fopen(file_names["Features"].c_str(),"r") ;
	assert(features_fp != NULL) ;

	vector<string> features ;
	char var[MAX_STRING_LEN],full_name[MAX_STRING_LEN] ;

	while (!feof(features_fp)) {
		int rc = fscanf(features_fp,"%s %s\n",var,full_name) ;
		if (rc == EOF)
			break ;
		assert(rc == 2) ;

		if (strcmp(full_name + strlen(full_name) - 8,"_Current") == 0) {
			strncpy(name,full_name,strlen(full_name) - 8) ;
			name[strlen(full_name) - 8] = '\0' ;
		} else 
			strcpy(name,full_name) ;

		char *name_ptr = name ;
		while (*name_ptr != '\0') {
			if (*name_ptr == '_')
				*name_ptr = ' ' ;
			name_ptr ++ ;
		}
		features.push_back(name) ;
	}
	fclose(features_fp) ;

	// Method Specific
	if (method == 0) {
		// Copy ...
		copy(file_names["Extra"],dir,"extra_params.txt") ;
		copy(file_names["menLM"],dir,"men_lm_params.bin") ;
		copy(file_names["menGBM"],dir,"men_gbm_model") ;
		copy(file_names["menComb"],dir,"men_comb_params") ;
		copy(file_names["womenLM"],dir,"women_lm_params.bin") ;
		copy(file_names["womenGBM"],dir,"women_gbm_model") ;
		copy(file_names["womenComb"],dir,"women_comb_params") ;

		copy(file_names["menRF"],dir,"men_rf_model") ;
		copy(file_names["womenRF"],dir,"women_rf_model") ;

		// Read Param
		map<int,params> men_data ;
		map<int,params> women_data ;

		read_params(file_names["menParams"],men_data) ;
		read_params(file_names["womenParams"],women_data) ;

		char codes_file[MAX_STRING_LEN] ;
		sprintf(codes_file,"%s/codes.txt",dir) ;

		FILE *out_fp = fopen(codes_file,"w") ;
		assert(out_fp != NULL) ;

		int id ;
		for (unsigned int i=0; i<features.size(); i++) {
			if (test_cols.find(features[i]) == test_cols.end())
				id = -1 ;
			else
				id = test_cols[features[i]] ;

			assert(men_data.find(i) != men_data.end()) ;
			assert(women_data.find(i) != women_data.end()) ;
			fprintf(out_fp,"%d\t%s\t%f\t%f\t%f\t%f\n",id,features[i].c_str(),men_data[i].min,men_data[i].max,women_data[i].min,women_data[i].max) ;
		}

		fclose(out_fp) ;
	}
	return 0 ;
}

// Functions:


void copy(string& from, char *dir, char *to) {

	char cmd[MAX_STRING_LEN] ;
	sprintf(cmd,"cp %s %s/%s",from.c_str(),dir,to) ;

	assert(system(cmd)==0) ;

	return ;
}

void read_params(string& fname, map<int,params>& parameters) {

	FILE *fp = fopen(fname.c_str(),"r") ;
	assert(fp != NULL) ;

	char buffer[MAX_BUF_SIZE] ;
	int id ;
	double value1,value2 ;

	while (!feof(fp)) {
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;

		if (sscanf(buffer,"Completion %d %lf %lf",&id,&value1,&value2) == 3) {
			// Ignore completion parameters (all CBC are completed through the LM models
		} else if (sscanf(buffer,"Bounds %d %lf %lf",&id,&value1,&value2) == 3) {
			parameters[id].min = value1 ;
			parameters[id].max = value2 ;
		}
	}

	fclose(fp) ;
	return ; 
}
