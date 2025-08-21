#define _CRT_SECURE_NO_WARNINGS


#include "predict.h"
#include "time.h"

//local functions


int main(int argc, char *argv[]) 
{
	
	
	clock_t tick1 , tick2;
	time_t time1 , time2;

	time1 = time(NULL);
	tick1 = clock();	
	
	
	predictParamStrType ps; // holds parameters given in command line
	
	getCommandParams(argc,argv,&ps);
	checkParams(ps) ;

	params2Stderr(ps) ;
	openFiles(&ps);

	assert(set_parameters(ps.extraParamsFile) != -1) ;

	int min_test_gap = 0 ; 
	int min_test_num = 0 ;

	feature_flags fflags ;
	ps.featuresSelectString += ps.extraFeaturesString ;
	assert(get_feature_flags((char *)(ps.featuresSelectString.c_str()),&fflags)!=-1) ;

	string method(ps.methodString) ;

	// Get Matrix
	xy_data xy;
	init_xy(&xy) ;

	linearLinesType lines;
	matrixLinesType linesM;
	
	// Read
	int nlines=readInputLines(ps.binFile,&lines); // includes lines allocation
	fprintf(stderr,"Read %d testing lines\n",nlines) ;
	linesM=(double (*)[MAXCOLS])lines; // to get the 2 d representation

	// Add noise to data
	if (ps.noisy_ftrs != "") {
		// Remove dependent variables
		int nrem = remove_dependent(lines,nlines,MAXCOLS) ;
		fprintf(stderr,"Removed %d entries\n",nrem) ;

		// Add noise
		if (add_noise_to_data(lines,nlines,MAXCOLS,ps.noise_level,ps.noise_direction,ps.noisy_ftrs.c_str()) == -1) {
			fprintf(stderr,"Adding noise to data failed\n") ;
			return -1 ;
		}
		fprintf(stderr,"Added Noise\n") ;
	}

	int mftrs = MAX_FTRS ;

	double *means_for_completion = (double *) malloc(2*mftrs*sizeof(double)) ;
	double *sdvs_for_completion = (double *) malloc(2*mftrs*sizeof(double)) ;
	double *b = (double *) malloc(2*mftrs*sizeof(double)) ;
	assert (means_for_completion != NULL && sdvs_for_completion != NULL && b!=NULL) ;

	// Read parameters
	double *bin_bnds,*eqsize_bin_bnds ;
	int nbins ;
 
	int prms_nftrs ;
	cleaner cln ;
	cln.mode = 1 ;
	assert(read_params(ps.outliersParamsFile,mftrs,&prms_nftrs,means_for_completion,sdvs_for_completion,cln,&bin_bnds,&eqsize_bin_bnds,&nbins)!=-1) ;
	
	// Complete dependent variables
	int ncompleted = complete_dependent(lines,nlines,MAXCOLS) ;
	fprintf(stderr,"Completed %d entries\n",ncompleted) ;
	
	perform_initial_trnasformations(lines,nlines,cln,MAXCOLS) ; // Perform initial transformations on data

	assert(get_x_matrix(linesM,nlines,ps,&xy,&fflags,mftrs,1,cln,0) != -1) ;
	assert(xy.nrows > 0) ;
	free(lines) ;

	// Pre-process
	if (method=="LM") // in linear regression we actually do parabolic regression
		assert(take_squares(&xy) != -1) ; // working in place in tx

	fprintf(stderr,"Nftrs = %d ; Prms_nftrs = %d\n",xy.nftrs,prms_nftrs) ;
	assert(xy.nftrs == prms_nftrs) ;

//	assert(clear_data_from_bounds(&xy,MISSING_VAL,cln.ftrs_min,cln.ftrs_max) != -1) ;

	assert(xy.nrows>0) ;
	double *xx ;
	assert(transpose(xy.x,&xx,xy.nrows,xy.nftrs)!=-1) ;
	free(xy.x);
	xy.x=xx;

	replace_with_approx_mean_values(&xy,means_for_completion,sdvs_for_completion) ;

	fprintf(stderr,"Processing data. Done\n") ;	
	fprintf(stderr,"Working on %d x %d\n",xy.nrows,xy.nftrs) ;

	// get the prediction model
	generalized_predictor_info_t predict_info ;
	assert(init_predictor_info(ps,&fflags,predict_info) != -1) ;

	int modelSize, methodIndex;
	void *model;
	double * preds;

	fprintf(stderr, "Method is %s\n", ps.methodString.c_str()) ; fflush(stderr);
	assert(gzread(ps.predictorFile, &modelSize, sizeof(modelSize)) == sizeof(modelSize)); //size
	assert(gzread(ps.predictorFile, &methodIndex, sizeof(methodIndex)) == sizeof(methodIndex)); //method
	assert(methodIndex == ps.methodMap[ps.methodString]) ; // method consistency

	fprintf(stderr, "modelSize is %d\n",modelSize); fflush(stderr);
	assert(model=malloc(modelSize)); //allocate blob
	assert(gzread(ps.predictorFile, model, modelSize) == modelSize); //read blob
	assert(preds=(double *)malloc(xy.nrows*sizeof(double)));

	fprintf(stderr, "read model , going into predict of %d samples\n",xy.nrows); fflush(stderr);
	assert(predict(&xy,predict_info,(unsigned char *) model,preds) != -1) ;
		
	// Output
	time_t rawtime ;
	time(&rawtime) ;
		
	fprintf(ps.predictOutFile,"Prediction\t%s\t%s\t%s %s\t%s\t%s\t%s %s\t%s",ps.header_info.c_str(),ps.binFileName.c_str(),ps.predictorFileName.c_str(),ps.completionParamsFileName.c_str(),
		ps.methodString.c_str(),ps.featuresSelectString.c_str(),__DATE__,__TIME__,ctime(&rawtime)) ;
	for (int i=0; i<xy.nrows; i++) {
		int ibin = 0 ;
		for (int j = 0; j<nbins-1; j++) {
			if (preds[i] > bin_bnds[j])
				ibin++ ;
		}

		int ibin2 = 0 ;
		for (int j = 0; j<nbins-1; j++) {
			if (preds[i] > eqsize_bin_bnds[j])
				ibin2++ ;
		}

		fprintf(ps.predictOutFile,"%d %d %.2f %d %d\n",xy.idnums[i],xy.dates[i],preds[i],ibin,ibin2) ;
	}

	tick2= clock();
	fprintf(stderr , "cpu_time %f\n", (double (tick2-tick1)/CLOCKS_PER_SEC));

	time2 = time(NULL);
	fprintf(stderr , "wallclock_time %f\n", double (time2-time1));


}
//------------------------ end of main -------------------------------------

// Local Functions

void params2Stderr(predictParamStrType& ps)
{
	fprintf(stderr,"Input File: %s\n",ps.binFileName.c_str()) ;
	fprintf(stderr,"Log File: %s\n",ps.logFileName.c_str()) ;
	fprintf(stderr,"Features Flag: %s\n",ps.featuresSelectString.c_str()) ;
	fprintf(stderr,"Predictor File: %s\n",ps.predictorFileName.c_str()) ;
	fprintf(stderr,"Completion File: %s\n",ps.completionParamsFileName.c_str()) ;
	fprintf(stderr,"Outliers File: %s\n",ps.outliersParamsFileName.c_str()) ;

	if (ps.extraParamsFileName != "")
		fprintf(stderr,"Extra Prams File : %s\n",ps.extraParamsFileName.c_str()) ;

}

int getCommandParams(int argc,char **argv,predictParamStrType *ps)
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
			("info",po::value<string>(&ps->header_info)->default_value(""),"user description string")
		    ("autoCompletionFlag",po::value<int>(&ps->autoCompletionFlag)->default_value(0)->implicit_value(1), "should predict learn completion params from data")	
			("binFile", po::value<string>(&ps->binFileName)->required(), " bin input file of lab tests")
			("logFile", po::value<string>(&ps->logFileName)->required(), " log output file")
			("predictorFile", po::value<string>(&ps->predictorFileName)->required(), " predictor model output file")
			("completionFile", po::value<string>(&ps->completionParamsFileName), " completion model output file")
			("outliersFile", po::value<string>(&ps->outliersParamsFileName)->required(), " outliers model output file")	
			("predictOutFile", po::value<string>(&ps->predictOutFileName)->required(), " predictions output file")	
			("featuresOutFile", po::value<string>(&ps->ftrsOutFileName)->default_value(""), " features output file [currently only for 2-stages prediction]")
			("featuresSelection", po::value<string>(&ps->featuresSelectString)->required(), "features selection string")
			("extraFeatures", po::value<string>(&ps->extraFeaturesString)->default_value("XZ"), "optional string for extra features")
			("method", po::value<string>(&ps->methodString)->required(), "method of classification")
			("noiseDir", po::value<int>(&ps->noise_direction)->default_value(0), "Direction of noise to add to features")
			("noiseLevel", po::value<double>(&ps->noise_level)->default_value(0.1), "Level of noise to add to features")
			("noisyFeatures", po::value<string>(&ps->noisy_ftrs)->default_value(""), "Features to add noise to : [0,1]^20")
			("historyPattern",po::value<int>(&ps->history_pattern)->default_value(0), "Indicate subset of history of CBCs to take [1-4]")
			("maxHistoryDays",po::value<int>(&ps->max_history_days)->default_value(-1), "Maximum days of history used for prediction") // Overrides historyPattern
			("model_prior_field", po::value<string>(&ps->model_prior_field)->default_value("no field"), "fields with priors given in model (Age/Parameter Name ; comma separated)")
			("external_prior_field", po::value<string>(&ps->external_prior_field)->default_value("no field"), "fields with priors given in file (Age/Parameter Name ; comma separated)")
			("two_stages", po::bool_switch(&ps->two_stages), "model is a two-stages predictor")
			("incidence",po::value<string>(&ps->incFileName)->default_value(""),"external_prior_field related incidence file")
			("internal_method", po::value<string>(&ps->internal_method)->default_value("RF"), "method of actual classification in complex method")
			("external_method", po::value<string>(&ps->external_method)->default_value("RF"), "method of actual classification in complex method")
			("extra_params",po::value<string>(&ps->extraParamsFileName)->default_value(""),"file for learning parameters")
			("nthreads",po::value<int>(&ps->nthreads)->default_value(QRF_LEARN_NTHREADS),"number of threads for threaded applications")
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
		assert(ps->autoCompletionFlag||vm.count("completionFile")>0);
		
		
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

void openFiles(predictParamStrType *ps)
{
	assert(ps->binFile= safe_gzopen(ps->binFileName.c_str(), "rb"));
	assert(ps->logFile= safe_fopen(ps->logFileName.c_str(), "w"));
	assert(ps->predictorFile= safe_gzopen(ps->predictorFileName.c_str(), "rb"));
	assert(ps->completionParamsFile= safe_gzopen(ps->completionParamsFileName.c_str(), "rb"));
	assert(ps->outliersParamsFile= safe_fopen(ps->outliersParamsFileName.c_str(), "r"));
	assert(ps->predictOutFile= safe_fopen(ps->predictOutFileName.c_str(), "w"));

	if (ps->incFileName == "")
		ps->incFile = NULL ;
	else
		assert(ps->incFile = safe_fopen(ps->incFileName.c_str(), "r")) ;

	if (ps->extraParamsFileName == "")
		ps->extraParamsFile = NULL ;
	else
		assert(ps->extraParamsFile = fopen(ps->extraParamsFileName.c_str(), "r")) ;

	if (ps->ftrsOutFileName == "")
		ps->ftrsOutFile = NULL;
	else
		assert(ps->ftrsOutFile = fopen(ps->ftrsOutFileName.c_str(), "w"));
	
}

int read_params(FILE *fp, int mftrs, int *nftrs, double *means_for_completion, double *sdvs_for_completion, cleaner& cln, double **bin_bnds, double **eqsized_bin_bnds, int *nbins) {

	// Bins
	*nbins = 0 ;
	*bin_bnds = *eqsized_bin_bnds = NULL ;

	int ibin,tot,pos ;
	double bnd,prob ;

	while(fscanf(fp,"Bin %d : Bnd = %lf ; Tot = %d ; Pos = %d ; Prob = %lf\n", &ibin,&bnd,&tot,&pos,&prob) == 5) {
		if (ibin != *nbins) {
			fprintf(stderr,"Bins problem in reading bin %d\n",ibin) ;
			return -1 ;
		}

		if (((*bin_bnds) = (double *) realloc((*bin_bnds),(ibin+1)*sizeof(double)))==NULL) {
			fprintf(stderr,"Allocation problem at bin %d\n",ibin) ;
			return -1 ;
		}

		(*bin_bnds)[ibin] = bnd ;
		(*nbins)++ ;
	}

	(*nbins) ++ ;

	int temp_nbins = 0 ;
	while(fscanf(fp,"EqSizedBin %d : Bnd = %lf ; Tot = %d ; Pos = %d ; Prob = %lf\n", &ibin,&bnd,&tot,&pos,&prob) == 5) {
		if (ibin != temp_nbins) {
			fprintf(stderr,"Bins problem in reading eq-sized bin %d\n",ibin) ;
			return -1 ;
		}

		if (((*eqsized_bin_bnds) = (double *) realloc((*eqsized_bin_bnds),(ibin+1)*sizeof(double)))==NULL) {
			fprintf(stderr,"Allocation problem at bin %d\n",ibin) ;
			return -1 ;
		}

		(*eqsized_bin_bnds)[ibin] = bnd ;
		temp_nbins++ ;
	}

	temp_nbins++ ;
	if (temp_nbins != *nbins) {
		fprintf(stderr,"Bins Inconsistency: %d vs %d\n",temp_nbins,*nbins) ;
		return -1 ;
	}

	// Allocate
	cln.data_min = (double *) malloc(MAX_FTRS*sizeof(double)) ;
	cln.data_max = (double *) malloc(MAX_FTRS*sizeof(double)) ;
	assert (cln.data_min != NULL && cln.data_max != NULL) ;
	
	if (cln.mode == 0) {
		cln.ftrs_min = (double *) malloc(2*mftrs*sizeof(double)) ;
		cln.ftrs_max = (double *) malloc(2*mftrs*sizeof(double)) ;
		assert (cln.ftrs_min != NULL && cln.ftrs_max != NULL) ;
	} else {
		cln.min_orig_data = (double *) malloc(MAX_FTRS * sizeof(double)) ;
		cln.data_avg = (double *) malloc(MAX_FTRS*sizeof(double)) ;
		cln.data_std = (double *) malloc(MAX_FTRS*sizeof(double)) ;
		assert (cln.min_orig_data != NULL && cln.data_avg != NULL && cln.data_std != NULL) ;
	}

	// Commons Values
	int cnt = 0 ;
	int iftr ;
	double val1,val2 ;

	while (fscanf(fp,"Completion %d %lf %lf\n",&iftr,&val1,&val2)==3) {
		if (iftr != cnt) {
			fprintf(stderr,"Completion values problem in reading feature %d\n",iftr) ;
			return -1 ;
		}

		if (cnt == mftrs) {
			fprintf(stderr,"Too many completion values given\n") ;
			return -1 ;
		}

		means_for_completion[iftr] = val1 ;
		sdvs_for_completion[iftr] = val2 ;
		cnt++ ;
	}

	*nftrs = cnt ;

	// Moments
	if (cln.mode == 0) {
		if (fscanf(fp,"NBounds1 %d\n",&cnt) != 1) {
			fprintf(stderr,"Cannot read NBounds1\n") ;
			return -1 ;
		}
	
		if (cnt != MAXCOLS) {
			fprintf(stderr,"Inconsistent NBounds1\n") ;
			return  -1 ;
		}

		cln.ndata = cnt ;

		double min,max ;
		for (int i=0; i<cnt; i++) {
			if (fscanf(fp,"Bounds1 %d %lg %lg\n",&iftr,&min,&max) !=3 || iftr != i) {
				fprintf(stderr,"Problem reading Bounds1 no. %d \n",i) ;
				return -1 ;
			}
			cln.data_min[iftr] = min ;
			cln.data_max[iftr] = max ;
		}

		// second bounds
		if (fscanf(fp,"NBounds2 %d\n",&cnt) != 1) {
			fprintf(stderr,"Cannot read NBounds1\n") ;
			return -1 ;
		}
	
		if (cnt != *nftrs) {
			fprintf(stderr,"Inconsistent NBounds1\n") ;
			return  -1 ;
		}
		cln.nftrs = cnt ;

		for (int i=0; i<cnt; i++) {
			if (fscanf(fp,"Bounds2 %d %lg %lg\n",&iftr,&min,&max) !=3 || iftr != i) {
				fprintf(stderr,"Problem reading Bounds2 no. %d\n",i) ;
				return -1 ;
			}
			cln.ftrs_min[iftr] = min ;
			cln.ftrs_max[iftr] = max ;
		}
	} else {

		if (fscanf(fp,"NCleaning %d\n",&cnt) != 1) {
			fprintf(stderr,"Cannot read NCleaning\n") ;
			return -1 ;
		}
	
		if (cnt != MAXCOLS) {
			fprintf(stderr,"Inconsistent NCleaning\n") ;
			return  -1 ;
		}

		double _min_orig,_avg,_std,_min,_max ;
		for (int i=0; i<cnt; i++) {
			if (fscanf(fp,"Cleaning %d %lg %lg %lg %lg %lg\n",&iftr,&_min_orig,&_avg,&_std,&_min,&_max) != 6 || iftr != i) {
				fprintf(stderr,"Problem reading Bounds1 no. %d \n",i) ;
				return -1 ;
			}
			cln.min_orig_data[iftr] = _min_orig ;
			cln.data_avg[iftr] = _avg ;
			cln.data_std[iftr] = _std ;
			cln.data_min[iftr] = _min ;
			cln.data_max[iftr] = _max ;
		}
	}

	return 0 ;
}

void checkParams(predictParamStrType& ps) {

	if (ps.methodMap.find(ps.methodString) == ps.methodMap.end()) {
		fprintf(stderr,"Unknown method \'%s\'\n",ps.methodString.c_str()) ;
		exit(-1) ;
	}

	if (ps.methodMap.find(ps.internal_method) == ps.methodMap.end()) {
		fprintf(stderr,"Unknown method \'%s\'\n",ps.internal_method.c_str()) ;
		exit(-1) ;
	}

	if ((ps.external_prior_field != "no field" || ps.model_prior_field != "no field") && ps.two_stages) {
		fprintf(stderr,"Cannot handle model/external prior-fields together with two_stages\n") ;
		exit(-1) ;
	}
}