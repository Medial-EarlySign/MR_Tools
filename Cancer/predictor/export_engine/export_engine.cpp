// Prepare engine for MS_CRC_Scorer based on setup file //

#define _CRT_SECURE_NO_WARNINGS
#include "export_engine.h"

int main(int argc, char *argv[]) {

	exportParamStrType ps; // holds parameters given in command line
	
	// Parse input arguments
	getCommandParams(argc,argv,&ps);
	params2Stderr(ps) ;
	openFiles(&ps) ;

	if (! (ps.methodString == "RFGBM") && ! (ps.methodString == "DoubleMatched" && (ps.internalMethod == "RF" || ps.internalMethod == "QRF"))) {
		fprintf(stderr,"Method not implemented (yet ?). Quitting\n") ;
		return -1 ;
	}

	//Read instructions
	map<string,string> file_names ;
	assert (read_instructions(ps,file_names) != -1) ;

	// Handle Version
	assert(write_engine_version(ps.engineVersion, ps.EngineDirectory) != -1);

	//Handle Features
	map<string, pair<int,int> > features ;
	assert(read_features(file_names["Features"],features) != -1) ;
	assert (create_params_file(file_names, features, ps.combined, ps.EngineDirectory) != -1) ;

	// Handle Extra Params 
	copy(file_names["Extra"],ps.EngineDirectory,"extra_params.txt") ;
	copy(file_names["Shift"],ps.EngineDirectory,"shift_params.txt") ;

	// Handle Completion
	if (ps.combined)
		unzip_file(file_names["combinedCompletion"],ps.EngineDirectory,"combined_lm_params.bin") ;
	else {
		unzip_file(file_names["menCompletion"],ps.EngineDirectory,"men_lm_params.bin") ;
		unzip_file(file_names["womenCompletion"],ps.EngineDirectory,"women_lm_params.bin") ;
	}

	// Method Specific
	if (ps.combined) {
		assert (create_model_files(file_names,"combined",ps.EngineDirectory,ps.methodString, ps.methodMap[ps.methodString],ps.internalMethod) != -1) ;
	} else {
		assert (create_model_files(file_names,"men",ps.EngineDirectory,ps.methodString,ps.methodMap[ps.methodString],ps.internalMethod) != -1) ;
		assert (create_model_files(file_names,"women",ps.EngineDirectory,ps.methodString,ps.methodMap[ps.methodString],ps.internalMethod) != -1) ;
	}

	return 0 ;
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//				Functions:
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

int getCommandParams(int argc, char **argv, exportParamStrType *ps)
{
	string inFileName;

	po::options_description desc("Program options");
	po::variables_map vm;   
	
	init_methods_map(ps->methodMap) ;

	int helpFlag=0;
	try {
		desc.add_options()	
			("infile",po::value<string>(&inFileName),"get parameters from infile")
			("help",po::value<int>(&helpFlag)->implicit_value(1), "produce help message")
			("method", po::value<string>(&ps->methodString)->required(), "method of classification")
			("internal", po::value<string>(&ps->internalMethod)->default_value("RF"), "internal method of classification")
			("setup", po::value<string>(&ps->setUpFileName)->required(), "input set-up file")
			("dir", po::value<string>(&ps->EngineDirectory)->required(), "output directory")
			("combined",po::bool_switch(&ps->combined), "indicate that engine is gender-combined")
			("version",po::value<string>(&ps->engineVersion)->required(), "version name to be writting in Version.txt")
			;

		po::store(po::command_line_parser(argc, argv).options(desc).run(),vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);
		}
		  if (vm.count("infile"))
        {
         
			std::ifstream s(vm["infile"].as<string>());
			if(!s)
			{
				std::cerr<<"error openining infile " << vm["infile"].as<string>() <<std::endl;
				return 1;
			}
		
			po::store(po::parse_config_file(s,desc),vm);
				
        }

		po::notify(vm);

		return(0);
	}
	catch(std::exception& e) {
		cerr << "error: " << e.what() << "; run with --help for usage information\n";
		exit(-1);
	}
	catch(...) {
		cerr << "Exception of unknown type!\n";
		return -1;
	}
}

void params2Stderr(exportParamStrType& ps)
{
	fprintf(stderr,"Method: %d - %s\n",ps.methodMap[ps.methodString],ps.methodString.c_str()) ;
	fprintf(stderr,"Set Up File: %s\n",ps.setUpFileName.c_str()) ;
	fprintf(stderr,"Output Directory: %s\n",ps.EngineDirectory.c_str()) ;
	if (ps.combined)
		fprintf(stderr,"Working on combined engine\n") ;
}

void openFiles(exportParamStrType *ps)
{
	assert(ps->setUpFile= safe_fopen(ps->setUpFileName.c_str(), "r"));
}

int read_instructions(exportParamStrType& ps, map<string,string>& file_names) {

	char name[MAX_STRING_LEN],type[MAX_STRING_LEN] ;

	map<string,int> file_cnt ;
	for (int i=0; i<N_FILE_NAMES; i++)
		file_cnt[common_file_names[i]] = 0 ;

	for (int i=0; i<N_FILE_SUFFICES; i++) {
		string suffix(common_file_suffices[i]) ;
		if (ps.combined) {
			file_cnt["combined" + suffix] = 0 ;			
		} else {
			file_cnt["men" + suffix] = 0 ;
			file_cnt["women" + suffix] = 0 ;
		}
	}

	int methodIndex = ps.methodMap[ps.methodString] ;
	for (int i=0; i<specific_nfiles[methodIndex]; i++)
		file_cnt[specific_file_names[methodIndex][i]] = 0 ;

	while (!feof(ps.setUpFile)) {
		int rc = fscanf(ps.setUpFile,"%s %s\n",type,name) ;
		if (rc == EOF)
			break ;
		assert(rc == 2) ;
	
		if (file_cnt.find(type) == file_cnt.end()) {
			fprintf(stderr,"Unknown type %s in setup file\n",type) ;
			return -1 ;
		}
		
		if (file_cnt[type] != 0) {
			fprintf(stderr,"Recurrence of type %s in setup file\n",type) ;
			return -1 ;
		}

		file_cnt[type] ++ ;
		file_names[type] = name ;
	}
	fclose(ps.setUpFile) ;

	for (auto it = file_cnt.begin(); it != file_cnt.end(); it++) {
		if (it->second == 0) {
			fprintf(stderr,"%s is missing\n",it->first.c_str()) ;
			return -1 ;
		}
	}

	return 0 ;
}


void copy(const string& from, const string& dir, const char * to)  {

	char cmd[MAX_STRING_LEN] ;
	sprintf(cmd,"cp %s %s/%s",from.c_str(),dir.c_str(),to) ;

	assert(system(cmd)==0) ;

	return ;
}

void unzip_file(const string& from, const string& dir, const char * to)  {

	char orig_out_file[MAX_STRING_LEN] ;
	sprintf(orig_out_file,"%s/%s",dir.c_str(),to) ;
	string out_file ;
	fix_path(orig_out_file,out_file) ;

	gzFile inF = gzopen(from.c_str(),"rb") ; assert(inF) ;
	FILE *outF = fopen(out_file.c_str(),"wb") ; assert(outF) ;

	char buffer[128] ;
	int nread = 0 ;
	
	while ((nread = gzread(inF,buffer,sizeof(buffer))) > 0)
		fwrite(buffer,1,nread,outF) ;

	gzclose(inF) ;
	fclose(outF) ;
	return ;
}


int read_features(string& file_name, map<string, pair<int,int> >& features)  {
	
	FILE *features_fp = safe_fopen(file_name.c_str(), "r", false) ;
	if (features_fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",file_name.c_str()) ;
		return -1 ;
	}

	char name[MAX_STRING_LEN] ;
	int col,code ;

	while (!feof(features_fp)) {
		int rc = fscanf(features_fp,"%s %d %d\n",name,&col,&code) ;
		if (rc == EOF)
			break ;
		assert(rc == 3) ;
		pair<int,int> index(col,code) ;
		features[name] = index ;
	}
	fclose(features_fp) ;

	return 0 ;
}

char buffer[MAX_BUF_SIZE] ;
int read_params(string& fname, map<int,params>& parameters) {

	FILE *fp = safe_fopen(fname.c_str(), "r", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Problems openning params file %s\n", fname.c_str()) ;
		return -1 ;
	}

	int id ;
	double val1,val2,val3,val4,val5 ;
	int nclean,iclean;

	while (!feof(fp)) {
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;

		if (sscanf(buffer, "NCleaning %d\n", &nclean) == 1) {
			iclean = 0;
		} else if (sscanf(buffer, "Cleaning %d %lg %lg %lg %lg %lg\n", &id, &val1, &val2, &val3, &val4, &val5) == 6) {
			parameters[id].min_orig_data = val1;
			parameters[id].avg = val2;
			parameters[id].std = val3;
			parameters[id].min = val4;
			parameters[id].max = val5;
			iclean++;
		}
	}

	if (iclean != nclean) { 
		fprintf(stderr,"Nclean inconsistency in %s\n",fname.c_str()) ;
		return -1 ;
	}

	fclose(fp) ;
	return 0 ; 
}

int create_model_files(map<string,string>& file_names, const string& gender, string& dir, string& method, int index, string& internal) {

	string file_type = gender + "Model" ;
	string file_name = file_names[file_type] ;

	gzFile fp = safe_gzopen(file_name.c_str(),"rb", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Problems openning model file\n") ;
		return -1 ;
	}

	// Read
	int modelSize ;
	if (gzread(fp,&modelSize,sizeof(modelSize))!=sizeof(modelSize)) {
		fprintf(stderr,"Problems reading model size\n") ;
		return -1 ;
	}

	int methodIndex ;
	if (gzread(fp,&methodIndex,sizeof(methodIndex))!=sizeof(methodIndex))  {
		fprintf(stderr,"Problems reading model index\n") ;
		return -1 ;
	}

	if (methodIndex != index) {
		fprintf(stderr,"Model Index inconsistent : Read %d ; Expected %d\n",methodIndex,index) ;
		return -1 ;
	}

	unsigned char *model = (unsigned char *) malloc(modelSize) ;
	if (model == NULL) {
		fprintf(stderr,"Problems allocating model\n") ;
		return -1;
	}

	if (gzread(fp,model,modelSize)!=modelSize) {
		fprintf(stderr,"Problems reading model data\n") ;
		return -1 ;
	}

	if (method == "RFGBM")
		return create_rfgbm_model_files(model,gender,dir) ;
	else if (method == "DoubleMatched" && (internal == "RF" || internal == "QRF"))
		return create_double_matched_model_files(model, gender, dir, file_names,internal);
	else {
		fprintf(stderr,"Unknown method %s\n",method.c_str()) ;
		return -1 ;
	}
}

int create_double_matched_model_files(unsigned char *model, const string& gender, string& dir, map<string,string>& file_names, string& internal) {

	// Incidence
	if (get_incidence(file_names["menIncidence"],dir,"men_incidence.bin") == -1) {
		fprintf(stderr,"Cannot read/write men incidence file\n") ;
		return -1 ;
	}
	if (get_incidence(file_names["womenIncidence"],dir,"women_incidence.bin") == -1) {
		fprintf(stderr,"Cannot read/write women incidence file\n") ;
		return -1 ;
	}

	int size=0;
	char out_file_name[MAX_STRING_LEN];

	// First Forest
	if (internal == "RF") {
		sprintf(out_file_name, "%s/%s_rf1", dir.c_str(), gender.c_str());
		if (get_and_write_rf(model, out_file_name, &size) == -1) {
			fprintf(stderr, "Exporting firt random forest failed\n");
			return -1;
		}
	} else if (internal == "QRF") {
		sprintf(out_file_name, "%s/%s_qrf1", dir.c_str(), gender.c_str());
		if (get_and_write_qrf(model, out_file_name, &size) == -1) {
			fprintf(stderr, "Exporting firt random forest failed\n");
			return -1;
		}
	}

	// Second Forest 
	if (internal == "RF") {
		sprintf(out_file_name, "%s/%s_rf2", dir.c_str(), gender.c_str());
		if (get_and_write_rf(model, out_file_name, &size) == -1) {
			fprintf(stderr, "Exporting second random forest failed\n");
			return -1;
		}
	} else if (internal == "QRF") {
		sprintf(out_file_name, "%s/%s_qrf2", dir.c_str(), gender.c_str());
		if (get_and_write_qrf(model, out_file_name, &size) == -1) {
			fprintf(stderr, "Exporting second random forest failed\n");
			return -1;
		}
	}

	// ScoreProbs
	score_probs_info score_probs ;
	int size3 ;
	if ((size3 = deserialize(model+size,&score_probs)) == -1) {
		fprintf(stderr,"Cannot DeSerialize ScoreProbs model\n"); 
		return -1;
	}

	sprintf(out_file_name, "%s/%s_score_probs.bin", dir.c_str(), gender.c_str());
	if (write_blob(out_file_name, model, size, size3) == -1) {
		fprintf(stderr, "Problems writing %s\n", out_file_name);
		return -1;
	}
	size += size3;

	// Preds2Spec
	pred_to_spec_info_t preds_to_spec ;
	int size4 ;
	if ((size4 = deserialize(model+size,&preds_to_spec)) == -1) {
		fprintf(stderr,"Cannot DeSerialize Preds2Spec\n") ;
		return -1 ;
	}

	sprintf(out_file_name, "%s/%s_pred_to_spec.bin", dir.c_str(), gender.c_str());
	if (write_blob(out_file_name, model, size, size4) == -1) {
		fprintf(stderr, "Problems writing %s\n", out_file_name);
		return -1;
	}

	free(model) ;
	return 0 ;
}

int get_and_write_rf(unsigned char *model, char *out_file_name, int *size) {
	
	random_forest rf;
	int size1;
	if ((size1 = rf_deserialize(model + (*size), &rf)) == -1) {
		fprintf(stderr, "Cannot DeSerialize RF model\n");
		return -1;
	}
	*size += size1;
	
	if (write_forest(&rf, out_file_name) == -1) {
		fprintf(stderr, "Problems writing %s\n", out_file_name);
		return -1;
	}

	return 0;
}

int get_and_write_qrf(unsigned char *model, char *out_file_name, int *size) {

	QRF_Forest qrf;
	int size1;
	if ((size1 = (int) qrf.deserialize(model + (*size))) == -1) {
		fprintf(stderr, "Cannot DeSerialize QRF model\n");
		return -1;
	}

	FILE *fp = safe_fopen(out_file_name, "wb", false);
	if (fp == NULL) {
		fprintf(stderr, "Cannot open %s for writing\n", out_file_name);
		return -1;
	}

	if (fwrite(&size1, sizeof(int), 1, fp) != 1 || fwrite(model + (*size), 1, size1, fp) != size1) {
		fprintf(stderr, "Cannot write to %s\n", out_file_name);
		return -1;
	}

	*size += size1;

	return 0;
}

int create_rfgbm_model_files(unsigned char *model, const string& gender, string& dir) {

	int size ;
	// DeSerializae 
	rfgbm_info_t rfgbm_info ;
	if ((size = deserialize(model,&rfgbm_info))==-1) {
		fprintf(stderr,"DeSerialization failed\n") ;
		return -1 ;
	}

	// Write
	char out_file_name[MAX_STRING_LEN] ;
	sprintf(out_file_name,"%s/%s_comb_params",dir.c_str(),gender.c_str()) ;
	if (write_combination_params(out_file_name,&(rfgbm_info.comb)) == -1) {
		fprintf(stderr,"Problems writing %s\n",out_file_name) ;
		return -1 ;
	}

	sprintf(out_file_name,"%s/%s_gbm_params",dir.c_str(),gender.c_str()) ;
	if(write_full_gbm_info(&(rfgbm_info.gbm),out_file_name) == -1) {
		fprintf(stderr,"Problems writing %s\n",out_file_name) ;
		return -1 ;
	}

	sprintf(out_file_name,"%s/%s_rf_params",dir.c_str(),gender.c_str()) ;
	if (write_forest(&(rfgbm_info.rf),out_file_name) == -1) {
		fprintf(stderr,"Problems writing %s\n",out_file_name) ;
		return -1 ;
	}

	clear_rfgbm_struct(&rfgbm_info) ;
	free(model) ;

	return 0 ;
}

int write_engine_version(string& version, string &dir) {

	char version_file[MAX_STRING_LEN];
	sprintf(version_file, "%s/Version.txt", dir.c_str());
	
	FILE *out_fp = safe_fopen(version_file, "w", false);
	if (out_fp == NULL) {
		fprintf(stderr, "Cannot open Version.txt for writing\n");
		return -1;
	}

	fprintf(out_fp, "%s\n", version.c_str());
	fclose(out_fp);

	return 0;

}
int create_params_file(map<string,string>& file_names,  map<string, pair<int,int> >& features, bool combined, string& dir) {

	// Read Param
	map<int, params> data, men_data, women_data; 

	if (combined) {
		if (read_params(file_names["combinedOutliers"], data) == -1) {
			fprintf(stderr,"Reading outliers file failed\n") ;
			return -1 ;
		}
	} else {
		if (read_params(file_names["menOutliers"],men_data) == -1 || read_params(file_names["womenOutliers"],women_data) == -1) {
			fprintf(stderr,"Reading outliers file failed\n") ;
			return -1 ;
		}
	}

	char codes_file[MAX_STRING_LEN] ;
	sprintf(codes_file,"%s/codes.txt",dir.c_str()) ;

	FILE *out_fp = safe_fopen(codes_file,"w", false) ;
	if (out_fp == NULL)  {
		fprintf(stderr,"Cannot open codes for writing\n") ;
		return -1 ;
	}

	for (auto it = features.begin(); it != features.end(); it++) {
		string name = it->first;
		int col = it->second.first;
		int code = it->second.second;

		if (combined) {
			if (data.find(col) == data.end()) {
				fprintf(stderr, "Cannot find cleaning params for %s\n", name.c_str());
				return -1;
			}
			fprintf(out_fp, "%d\t%s\t%g\t%g\t%g\t%g\t%g\n", code, name.c_str(),
				data[col].min_orig_data, data[col].avg, data[col].std, data[col].min, data[col].max);
		}
		else {
			if (men_data.find(col) == men_data.end() || women_data.find(col) == women_data.end()) {
				fprintf(stderr, "Cannot find cleaning params for %s\n", name.c_str());
				return -1;
			}
			fprintf(out_fp, "%d\t%s\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\n", code, name.c_str(),
				men_data[col].min_orig_data, men_data[col].avg, men_data[col].std, men_data[col].min, men_data[col].max,
				women_data[col].min_orig_data, women_data[col].avg, women_data[col].std, women_data[col].min, women_data[col].max);
		}
	}

	fclose(out_fp) ;

	return 0 ;
}

int get_incidence(string &in, string& dir, const string& out) {

	FILE *ifp = safe_fopen(in.c_str(),"r", false) ;
	if (ifp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",in.c_str()) ;
		return -1 ;
	}

	string file = dir + "/" + out ;

	FILE *ofp = safe_fopen(file.c_str(), "wb", false) ;
	if (ofp == NULL) {
		fprintf(stderr,"Cannot open %s for wrinting\n",file.c_str()) ;
		return -1 ;
	}

	int ival ;
	double fval ;
	if (fscanf(ifp,"KeySize %d\n",&ival) != 1 || ival != 1) {
		fprintf(stderr,"Cannot parse %s\n",in.c_str()) ;
		return -1 ;
	}

	int nkeys ;
	if (fscanf(ifp,"Nkeys %d\n",&nkeys) != 1) {
		fprintf(stderr,"Cannot parse %s\n",in.c_str()) ;
		return -1 ;
	}

	if (fscanf(ifp,"%lf\n",&fval) != 1 || fval != 1.0) {
		fprintf(stderr,"Cannot parse %s\n",in.c_str()) ;
		return -1 ;
	}

	int *ages = (int *) malloc(nkeys*sizeof(int)) ;
	double *probs = (double *) malloc(nkeys*sizeof(double)) ;
	if (ages==NULL || probs==NULL) {
		fprintf(stderr,"Cannot Allocate\n") ;
		return -1 ;
	}

	int ikeys = 0;
	int age,np,nn ;
	while (! feof (ifp)) {
		int rc = fscanf(ifp,"%d %d %d\n",&age,&np,&nn) ;
		if (rc == EOF)
			break ;
		
		if (rc != 3) {
			fprintf(stderr,"Cannot parse %s\n",in.c_str()) ;
			return -1 ;
		}

		if (ikeys == nkeys) {
			fprintf(stderr,"Cannot parse %s\n",in.c_str()) ;
			return -1 ;
		}
		ages[ikeys] = age ;
		probs[ikeys] = (np+0.0)/(np+nn) ;

		ikeys ++ ;
	}

	if (ikeys != nkeys) {
		fprintf(stderr,"Cannot parse %s\n",in.c_str()) ;
		return -1 ;
	}

	if (fwrite(&nkeys,sizeof(int),1,ofp) != 1 || fwrite(ages,sizeof(int),nkeys,ofp) != nkeys || fwrite(probs,sizeof(double),nkeys,ofp) != nkeys) {
		fprintf(stderr,"Cannot write to %s\n",out.c_str()) ;
		return -1 ;
	}

	return 0 ;
}

int write_blob(char *out_file_name, unsigned char *model, int from, int size) {

	FILE *fp = safe_fopen(out_file_name, "wb", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for binary writing\n",out_file_name) ;
		return -1 ;
	}

	if (fwrite(&size,sizeof(int),1,fp) != 1 || fwrite(model+from,size,1,fp) != 1) {
		fprintf(stderr,"Cannot write to binary file %s\n",out_file_name) ;
		return -1 ;
	}

	fclose(fp) ;
	return 0 ;
}