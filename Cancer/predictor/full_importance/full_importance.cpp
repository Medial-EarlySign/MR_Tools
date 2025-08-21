#define _CRT_SECURE_NO_WARNINGS

#include "full_importance.h"

char all_names[][MAX_STRING_LEN] = 
		{"RBC","WBC","MPV","Hem","Hct","MCV","MCH","MCHC","RDW","Plt","EosN","NeuP","MonP","EosP","BasP","NeuN","MonN","BasN","LymP","LymN"} ;

int main(int argc, char *argv[]) {

	// Running parameters
	po::variables_map vm ;
	if (read_run_params(argc,argv,vm) == -1) {
		fprintf(stderr,"Read Run Params Failed\n");
		return -1 ;
	}

	string temp_path,path ;
	string orig_path = vm["path"].as<string>() ;
	fix_path(orig_path,path) ;

	string prefix = vm["prefix"].as<string>() ;

	fprintf(stderr,"Input Files: %s at %s\n",prefix.c_str(),path.c_str()) ;

	int min_test_gap = 0 ;
	int min_test_num = 0 ;
	int take_only_last_f = 1 ;

	char method[MAX_STRING_LEN] ;
	strcpy(method,vm["method"].as<string>().c_str()) ;

	int nfold =  vm["nfold"].as<int>() ;

	char work_dir[MAX_STRING_LEN] ;
	fix_path(vm["workdir"].as<string>(),temp_path) ;
	strcpy(work_dir,temp_path.c_str()) ;

	char measures_file[MAX_STRING_LEN] ;
	strcpy(measures_file,vm["measures"].as<string>().c_str()) ;

	char output_file[MAX_STRING_LEN] ;
	strcpy(output_file,vm["out"].as<string>().c_str()) ;

	int seed = vm["seed"].as<int>() ;

	string features_template = vm["features"].as<string>().c_str() ;

	string learn_config = vm["learn_config"].as<string>() ;
	string predict_config = vm["predict_config"].as<string>() ;
	string analyze_config = vm["analyze_config"].as<string>() ;

	// Read Data
	char full_data[MAX_STRING_LEN] ;
	sprintf(full_data,"%s/%s.bin",path.c_str(),prefix.c_str()) ;
	gzFile fin = safe_gzopen(full_data, "rb");

	double *lines; 
	int nlines = readInputLines(fin, &lines) ;
	fprintf(stderr,"Read %d lines\n",nlines) ;

	// Get All Correlations
	double corrs[NFTRS][NFTRS] ;

	int cols[NFTRS+2] ;
	for (int i=0; i<NCBC; i++)
		cols[i] = TEST_COL + i ;

	get_corrs(lines,nlines,MAXCOLS,cols,corrs) ;

	// Get Combinations to run
	vector<int> combinations[NFTRS][NFTRS][2] ;
	char names[NFTRS][NFTRS][MAX_STRING_LEN] ;
	get_combinations(corrs,combinations,names) ;

	map<vector<int>,int> combinations_hash ;
	vector<vector<int> > combinations_list ;
	int icomb = 0 ;

	for (int i=0; i<NFTRS; i++) {
		for (int j=0; j<NFTRS; j++) {
			for (int k=0; k<2; k++) {
				if (combinations_hash.find(combinations[i][j][k]) == combinations_hash.end()) {
					combinations_hash[combinations[i][j][k]] = icomb++ ;
					combinations_list.push_back(combinations[i][j][k]) ;
				}
			}
		}
	}
	fprintf(stderr,"Number of combinatsion to check = %zd\n",combinations_list.size()) ;

	int stage_start = 0 ;

	// Get Relevant Predictors
	if (stage_start || (stage_start = start_here("Get-Predictors"))) {
		if (get_predictors(combinations_list,orig_path,prefix,method,nfold,work_dir,seed,features_template,learn_config) == -1) {
			fprintf(stderr,"Get-Predictions failed\n") ;
			return -1 ;
		}
	}

	// Get Relevant Predictions
	if (stage_start || (stage_start = start_here("Get-Predictions"))) {
		if (get_predictions(combinations_list,orig_path,prefix,method,nfold,work_dir,seed,features_template,predict_config) == -1) {
			fprintf(stderr,"Get-Predictions failed\n") ;
			return -1 ;
		}
	}

	// Get Relevant Performances
	if (stage_start || (stage_start = start_here("Get-Performance"))) {
		if (get_performances(combinations_list,work_dir,nfold,analyze_config) == -1) {
			fprintf(stderr,"Get-Performance failed\n") ;
			return -1 ;
		}
	}

	// get_measures
	vector<measure> measures ;
	read_measures(measures_file,measures) ;  

	double *measure_values ;
	measure_values = (double *) malloc(combinations_list.size() * measures.size() * 2 * sizeof(double)) ;
	assert (measure_values != NULL) ;

	get_measure_values(combinations_list,work_dir,measures,measure_values) ;

	// Summarize
	summarize_measure_values(combinations,names,combinations_hash,measures,measure_values,output_file) ;

	return 0 ;
}

/****************	Functions ***********************/

// Analyze Command Line
int read_run_params(int argc, char **argv, po::variables_map& vm) {


	po::options_description desc("Program options");
	
	try {
		desc.add_options()	
			("help", "produce help message")
			("path", po::value<string>()->required(), "input data files path")
			("prefix", po::value<string>()->required(), "input data files prefix")
			("method", po::value<string>()->required(), "classifiction method")
			("nfold", po::value<int>()->required(), "cross validation nfold")
			("workdir", po::value<string>()->required(), "Work directory")
			("measures", po::value<string>()->required(), "file of performance measures to consider")
			("out",po::value<string>()->required(), "output file")
			("seed",po::value<int>()->required(), "randomization seed")
			("features",po::value<string>()->required(), "features-flag template")
			("learn_config",po::value<string>()->required(), "parameters for learning configuration file")
			("predict_config",po::value<string>()->required(), "parameters for learning configuration file")
			("analyze_config",po::value<string>()->required(), "parameters for learning configuration file")
			;
        ;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
            cerr << desc << "\n";
            return 0;

        }
        po::notify(vm);    
	}
	catch(std::exception& e) {
        cerr << "error: " << e.what() << "; run with --help for usage information\n";
        return -1;
    }
    catch(...) {
        cerr << "Exception of unknown type!\n";
		return -1;
    }

	return 0 ;
}

// Find Correlations
void get_corrs(double *in, int nrows, int ncols, int *ftrs, double corrs[NFTRS][NFTRS]) {

	double *vec1 = (double *) malloc(nrows*sizeof(double)) ;
	double *vec2 = (double *) malloc(nrows*sizeof(double)) ;
	assert(vec1!=NULL && vec2!=NULL) ;

	for (int iftr=0; iftr<NFTRS-1; iftr++) {
		for (int irow=0; irow<nrows; irow++)
			vec1[irow] = in[XIDX(irow,ftrs[iftr],ncols)] ;

		for (int jftr=iftr+1; jftr<NFTRS; jftr++) {
			for (int irow=0; irow<nrows; irow++)
				vec2[irow] = in[XIDX(irow,ftrs[jftr],ncols)] ;

			corrs[jftr][iftr] = corrs[iftr][jftr] = pearson(vec1,vec2,nrows,-1.0) ;
		}
	}
}

// Find Required Features Combinations
void get_combinations(double corrs[NFTRS][NFTRS],vector<int> combinations[NFTRS][NFTRS][2], char names[NFTRS][NFTRS][MAX_STRING_LEN]) {

	for (int iftr=0; iftr<NFTRS; iftr++) {
		vector<int> vec1(NFTRS,1) ;
		vector<int> vec2(NFTRS,1) ;
		vec2[iftr] = 0 ;

		combinations[iftr][0][0] = vec1 ;
		combinations[iftr][0][1] = vec2 ;
		strcpy(names[iftr][0],"ALL") ;

		vector<pair<int,double> > corrs_vec ;
		for (int jftr=0; jftr<NFTRS; jftr++) {
			if (jftr != iftr) {
				pair<int, double> entry(jftr,corrs[iftr][jftr]) ;
				corrs_vec.push_back(entry) ;
			}
		}
		sort(corrs_vec.begin(),corrs_vec.end(),compare_abs()) ;

		for (int i=0; i<corrs_vec.size(); i++) {
			vec1[corrs_vec[i].first] = vec2[corrs_vec[i].first] = 0 ;
			strcpy(names[iftr][i+1],all_names[corrs_vec[i].first]) ;
			combinations[iftr][i+1][0] = vec1 ;
			combinations[iftr][i+1][1] = vec2 ;
		}
	}
}

// Run Learn
int get_predictors(vector<vector<int> >& combinations_list, string& path, string& prefix, char *smethod, int nfold, char *work_dir, int seed, string& features_template, string& learn_config) {

	condor_runner runner ;

	char runner_file[1024] ;
	sprintf(runner_file,"%s/runner.learn",work_dir) ;

	runner.set_file_name(runner_file) ;

	runner.set_field("executable","learn.$$(OpSys)") ;
	runner.set_field("requirements","OpSys==\"LINUX\" || OpSys==\"WINDOWS\"") ;
	runner.set_field("should_transfer_files","YES") ;
	runner.set_field("when_to_transfer_output","ON_EXIT") ;
	runner.set_field("initialdir",work_dir) ;
	runner.set_field("log","learn.log") ;

	map<string,string> runner_params ;
	if (read_runner_params(learn_config,runner_params) == -1) {
		fprintf(stderr,"Read-Runner-Params failed\n") ;
		return -1 ;
	}
	
	for (auto it = runner_params.begin(); it != runner_params.end(); it++) {
		if (it->first != "arguments")
			runner.set_field(it->first,it->second) ;
	}
	
	if (runner_params.find("arguments") == runner_params.end())
		runner_params["arguments"] = "" ;

	char arguments[2048] ;
	char output[1024],error[1024],transfer_out_files[1024],transfer_in_files[1024] ;

	int index = 0 ;
	for (unsigned int i=0; i<combinations_list.size(); i++) {

		string features ;
		set_features(combinations_list[i],features_template,features) ;

		for (int j=0; j<nfold; j++) {
			index ++ ;

			sprintf(output,"learn_stdout%d",index) ;
			sprintf(error,"learn_stderr%d",index) ;
			sprintf(transfer_out_files,"predictor%d,outliers%d,",index,index) ; // Note : Completion is assumed to already exist for each split
			sprintf(transfer_in_files,"completion%d",j+1) ; 

			sprintf(arguments,"--binFile %s/SplitData/%s.train%d.bin --logFile LearnLog%d --predictorFile predictor%d --completionFile completion%d --outliersFile outliers%d --featuresSelection %s --method %s --use_completions %s",
				path.c_str(),prefix.c_str(),j+1,index,index,j+1,index,features.c_str(),smethod,runner_params["arguments"].c_str()) ;

			runner.add_command() ;
			runner.set_command_field("arguments",arguments) ;
			runner.set_command_field("output",output) ;
			runner.set_command_field("error",error) ;
			runner.set_command_field("transfer_output_files",transfer_out_files) ;
			runner.set_command_field("transfer_input_files",transfer_in_files) ;
		}
			
	}

	if (runner.print() == -1) {
		fprintf(stderr,"runner.print failed\n") ;
		return -1 ;
	}

	if (runner.submit() == -1) {
		fprintf(stderr,"runner.submit failed\n") ;
		return -1 ;
	}

	if (runner.wait() == -1) {
		fprintf(stderr,"runner.wait failed\n") ;
		return -1 ;
	}

	return 0;
}

// Run Predict
int get_predictions(vector<vector<int> >& combinations_list, string& path, string& prefix, char *smethod, int nfold, char *work_dir, int seed, string& features_template, string& predict_config) {

	// Learn
	condor_runner runner ;

	char runner_file[1024] ;
	sprintf(runner_file,"%s/runner.predict",work_dir) ;

	runner.set_file_name(runner_file) ;

	runner.set_field("executable","predict.$$(OpSys)") ;
	runner.set_field("requirements","OpSys==\"LINUX\" || OpSys==\"WINDOWS\"") ;
	runner.set_field("should_transfer_files","YES") ;
	runner.set_field("when_to_transfer_output","ON_EXIT") ;
	runner.set_field("initialdir",work_dir) ;
	runner.set_field("log","predict.log") ;

	map<string,string> runner_params ;
	if (read_runner_params(predict_config,runner_params) == -1) {
		fprintf(stderr,"Read-Runner-Params failed\n") ;
		return -1 ;
	}
	
	for (auto it = runner_params.begin(); it != runner_params.end(); it++) {
		if (it->first != "arguments")
			runner.set_field(it->first,it->second) ;
	}
	
	if (runner_params.find("arguments") == runner_params.end())
		runner_params["arguments"] = "" ;

	char arguments[2048] ;
	char output[1024],error[1024],transfer_in_files[1024],transfer_out_files[1024] ;

	int index = 0 ;
	for (unsigned int i=0; i<combinations_list.size(); i++) {

		string features ;
		set_features(combinations_list[i],features_template,features) ;

		for (int j=0; j<nfold; j++) {
			index ++ ;

			sprintf(output,"predict_stdout%d",index) ;
			sprintf(error,"predict_stderr%d",index) ;
			sprintf(transfer_in_files,"predictor%d,completion%d,outliers%d",index,j+1,index) ;
			sprintf(transfer_out_files,"predictions%d",index) ;

			sprintf(arguments,"--binFile %s/SplitData/%s.test%d.bin --logFile PredictLog%d --predictorFile predictor%d --completionFile completion%d --outliersFile outliers%d --featuresSelection %s --method %s --predictOutFile predictions%d %s",
				path.c_str(),prefix.c_str(),j+1,index,index,j+1,index,features.c_str(),smethod,index,runner_params["arguments"].c_str()) ;

			runner.add_command() ;
			runner.set_command_field("arguments",arguments) ;
			runner.set_command_field("output",output) ;
			runner.set_command_field("error",error) ;
			runner.set_command_field("transfer_input_files",transfer_in_files) ;
			runner.set_command_field("transfer_output_files",transfer_out_files) ;
		}	
	}

	if (runner.print() == -1) {
		fprintf(stderr,"runner.print failed\n") ;
		return -1 ;
	}

	if (runner.submit() == -1) {
		fprintf(stderr,"runner.submit failed\n") ;
		return -1 ;
	}

	if (runner.wait() == -1) {
		fprintf(stderr,"runner.wait failed\n") ;
		return -1 ;
	}

	return 0;
}

// Run Bootstrap-Analysis
int get_performances(vector<vector<int> >& combinations_list, char *work_dir, int nfold, string& analyze_config) {

	// Unite
	int index = 0 ;
	char sindex[1024] ;
	for (unsigned int i=0; i<combinations_list.size(); i++) {
		string command = "cat" ;
		for (int j=0; j<nfold; j++) {
			index ++ ;
			sprintf(sindex,"%d",index) ;
			command += " predictions" + string(sindex) ;
		}

		sprintf(sindex,"%d",i) ;
		command += " > combined_predictions" + string(sindex) ;

		if (system(command.c_str()) != 0) {
			fprintf(stderr,"%s failed\n",command.c_str()) ;
			return -1 ;
		}
	}

	// Analyze
	condor_runner runner ;

	char runner_file[1024] ;
	sprintf(runner_file,"%s/runner.analyze",work_dir) ;

	runner.set_file_name(runner_file) ;

	runner.set_field("executable","bootstrap_analysis.$$(OpSys)") ;
	runner.set_field("requirements","OpSys==\"LINUX\" || OpSys==\"WINDOWS\"") ;
	runner.set_field("should_transfer_files","YES") ;
	runner.set_field("when_to_transfer_output","ON_EXIT") ;
	runner.set_field("initialdir",work_dir) ;
	runner.set_field("analyze","full_cv.log") ;

	map<string,string> runner_params ;
	if (read_runner_params(analyze_config,runner_params) == -1) {
		fprintf(stderr,"Read-Runner-Params failed\n") ;
		return -1 ;
	}
	
	for (auto it = runner_params.begin(); it != runner_params.end(); it++) {
		if (it->first != "arguments")
			runner.set_field(it->first,it->second) ;
	}
	
	if (runner_params.find("arguments") == runner_params.end())
		runner_params["arguments"] = "" ;

	char arguments[2048] ;
	char output[1024],error[1024],transfer_in_files[1024],transfer_out_files[1024] ;

	for (unsigned int i=0; i<combinations_list.size(); i++) {

		sprintf(output,"analyze_stdout%d",i) ;
		sprintf(error,"analyze_stderr%d",i) ;
		sprintf(transfer_in_files,"combined_predictions%d",i) ;
		sprintf(transfer_out_files,"analysis%d,analysis%d.AutoSim",i,i) ;
		sprintf(arguments,"--in combined_predictions%d --out analysis%d %s",i,i,runner_params["arguments"].c_str()) ;

		runner.add_command() ;
		runner.set_command_field("arguments",arguments) ;
		runner.set_command_field("output",output) ;
		runner.set_command_field("error",error) ;
		runner.set_command_field("transfer_input_files",transfer_in_files) ;
		runner.set_command_field("transfer_output_files",transfer_out_files) ;
			
	}

	if (runner.print() == -1) {
		fprintf(stderr,"runner.print failed\n") ;
		return -1 ;
	}

	if (runner.submit() == -1) {
		fprintf(stderr,"runner.submit failed\n") ;
		return -1 ;
	}

	if (runner.wait() == -1) {
		fprintf(stderr,"runner.wait failed\n") ;
		return -1 ;
	}

	return 0;

}

// Read measures to cosider 
void read_measures(char *measures_file, vector<measure>& measures) {

	FILE *fp = safe_fopen(measures_file,"r") ;

	char age_range[MAX_STRING_LEN] ;
	char time_window[MAX_STRING_LEN] ;
	char measure_name[MAX_STRING_LEN] ;
	double random_value ;

	int rc ;
	while ((rc = fscanf(fp,"%s %s %s %lf\n",time_window,age_range,measure_name,&random_value)) != EOF) {
		assert(rc == 4) ;

		measure current ;
		current.age_range = string(age_range) ;
		current.time_window = string(time_window) ;
		current.measure_name = string(measure_name) ;
		current.random_value = random_value ;
		measures.push_back(current) ;
	}

	return ;
}

// Get Values of Measures
void get_measure_values(vector<vector<int> >& combinations_list,char *work_dir, vector<measure>& measures, double *measure_values) {

	char file_name[1024] ;
	int time_window_col,age_range_col ;
	vector<int> irows(measures.size()) ;
	vector<int> icols(measures.size()) ;


	for (unsigned int i=0; i<combinations_list.size(); i++) {

		sprintf(file_name,"%s\\Analysis%d",work_dir,i) ;

		char *table ;
		char *header ;
		int nrows,ncols ;
		char name[1024] ;

		assert(read_text_table(file_name,&table,&header,&nrows,&ncols) != -1) ;

		// Identify cols & rows
		if (i==0) {
			for (int icol=0; icol<ncols; icol++) {
				if (strcmp(header+HIDX(icol),"Time-Window")==0)
					time_window_col = icol ;
				else if (strcmp(header+HIDX(icol),"Age-Range")==0)
					age_range_col = icol ;
				else {
					for (unsigned int j=0; j<measures.size(); j++) {
						sprintf(name,"%s-Mean",measures[j].measure_name.c_str()) ;
						if (strcmp(header+HIDX(icol),name)==0)
							icols[j] = icol ;
					}
				}
			}
			for (int irow=0; irow<nrows; irow++) {
				for (unsigned int j=0; j<measures.size(); j++) {
					if (strcmp(table+FIDX(irow,age_range_col,ncols),measures[j].age_range.c_str())==0 && 
						strcmp(table+FIDX(irow,time_window_col,ncols),measures[j].time_window.c_str())==0)
						irows[j] = irow ;
				}
			}
		}

		for (unsigned int j=0; j<measures.size(); j++) {
			measure_values[(i*measures.size() + j)*2] = atof(table + FIDX(irows[j],icols[j],ncols)) ;
			measure_values[(i*measures.size() + j)*2 + 1] = atof(table + FIDX(irows[j],icols[j]+1,ncols)) ;	
		}
		free(table) ; 
		free(header) ;
	}

	return ;
}

void summarize_measure_values(vector<int> combinations[NFTRS][NFTRS][2], char names[NFTRS][NFTRS][MAX_STRING_LEN], map<vector<int>,int>& combinations_hash, vector<measure>& measures, double *measure_values, char *output_file) {

	FILE *fp = safe_fopen(output_file,"w") ;

	int nmeasures = (int) measures.size() ;

	for (int imeasure = 0; imeasure < nmeasures; imeasure++) {

		for (int i=0; i<NFTRS; i++) {

			double max_diff = 0 ;
			int i_sig = NFTRS ;
			for (int j=0; j<NFTRS; j++) {

				int idx1 = combinations_hash[combinations[i][j][0]] ;
				int idx2 = combinations_hash[combinations[i][j][1]] ;
				
				double mean1 = measure_values[(idx1*nmeasures + imeasure)*2] ;
				double mean2 = measure_values[(idx2*nmeasures + imeasure)*2] ;

				double sdv1 = measure_values[(idx1*nmeasures + imeasure)*2 + 1] ;
				double sdv2 = measure_values[(idx2*nmeasures + imeasure)*2 + 1] ;

				fprintf(fp,"Temporal [%s,%s,%s]\t%2d\t%2d\t%5s\t%f\t%f\t%f\t%f\n",measures[imeasure].time_window.c_str(),measures[imeasure].age_range.c_str(),
					measures[imeasure].measure_name.c_str(),i,j,names[i][j],mean1,sdv1,mean2,sdv2) ;

				double diff = mean1 - mean2 ;
				if (diff > max_diff) 
					max_diff = diff ;

				double z = diff/sqrt((sdv1*sdv1 + sdv2*sdv2)/2) ;
				if (i_sig == NFTRS && z > SIG_DIFF)
					i_sig = j ;
			}

			fprintf(fp,"Final [%s,%s,%s] : %d %d %f\n",measures[imeasure].time_window.c_str(),measures[imeasure].age_range.c_str(),
				measures[imeasure].measure_name.c_str(),i,i_sig,max_diff) ;
		}
	}

	return ;
}

void set_features (vector<int>& list, string& features_template, string& features) {

	// template should be G\dCZ\S+

	assert(features_template[0] == 'G' && (features_template[1] == '0' || features_template[1] == '1')) ;
	features = features_template.substr(0,2) ;

	assert(features_template.substr(2,2) == "CZ") ;
	features += "C" ;

	char bit[1] ;
	for (int iftr=0; iftr< NFTRS; iftr++) {
		sprintf(bit,"%d",list[iftr]) ;
		features += bit ;
	}

	features += features_template.substr(4,features_template.size()-4) ;

	return ;
}

int start_here(char *stage) {

	char answer[MAX_STRING_LEN] = "dummy" ;

	while (strncmp(answer,"yes",strlen(answer)-1) != 0 && strncmp(answer,"no",strlen(answer)-1) != 0) {
		printf("Start at %s ? [yes/no]\n",stage) ;
		fgets(answer,MAX_STRING_LEN,stdin) ;
		fprintf(stderr,"Answer is : \'%s\'\n",answer) ;
	}

	return (strcmp(answer,"no")) ;
}

int read_runner_params(string& file_name, map<string,string>& params) {

	string fixed_file_name ;
	fix_path(file_name,fixed_file_name) ;
	ifstream inf(fixed_file_name);

	if (!inf) {
		fprintf(stderr,"Cannot open %s for reading",fixed_file_name.c_str()) ;
		return -1;
	}

	string curr_line;
	while (getline(inf,curr_line)) {
		if (curr_line[curr_line.size()-1] == '\r')
			curr_line.erase(curr_line.size()-1) ;

		vector<string> fields;
		split(fields, curr_line, boost::is_any_of("\t"));	

		if(fields.size() != 2) {
			fprintf(stderr,"Illeagal line \'%s\' in %s\n",curr_line.c_str(),file_name.c_str()) ;
			return -1 ;
		}

		params[fields[0]] = fields[1] ;
	}

	return 0 ;
}