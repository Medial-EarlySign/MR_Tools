#define _CRT_SECURE_NO_WARNINGS

#include "learn.h"
#include "time.h"

/*
Main file of Learn program. 
Get a bin file and timing/method/features parameters (see details in argv definition)
Produce model for prediction
*/

int main(int argc, char *argv[]) {
	
	clock_t tick1 , tick2;
	time_t time1 , time2;

	time1 = time(NULL);
	tick1 = clock();

	learnParamStrType ps; // holds parameters given in command line
	
	getCommandParams(argc,argv,&ps);
	checkParams(ps) ;

	params2Stderr(ps);
	openFiles(&ps); // required at this stage for Condor for all files

	assert(set_parameters(ps.extraParamsFile) != -1) ;

	feature_flags fflags ;
	ps.featuresSelectString += ps.extraFeaturesString ;
	assert(get_feature_flags((char *)(ps.featuresSelectString.c_str()),&fflags)!=-1) ;

	string method(ps.methodString) ;
	gbm_parameters gbm_params ;

	if ((method=="RFGBM" || method=="RFGBM2" || method=="DoubleMatched" || method=="TwoSteps") && ps.nfold==0) {
		fprintf(stderr,"CV is required when combining\n") ;
		return -1 ;			
	} else if (method !="TwoSteps" && method !="RFGBM" && method != "RFGBM2" && method != "DoubleMatched" && ps.nfold!=0) {
		fprintf(stderr,"CV should not be performed when not combining\n") ;
		return -1 ;
	}

	set_gbm_parameters ("CRC",&gbm_params) ;
	if (method=="LUNG_GBM"){
		set_gbm_parameters ("LUCA",&gbm_params) ;
		method="GBM";
		ps.methodString="GBM";
	} else if(method=="ENSGBM")
		set_gbm_parameters ("ENSEMBLE",&gbm_params) ;

	if (ps.internal_method=="LUNG_GBM"){
		set_gbm_parameters ("LUCA",&gbm_params) ;
		ps.internal_method="GBM";
	} else if(ps.internal_method=="ENSGBM")
		set_gbm_parameters ("ENSEMBLE",&gbm_params) ;

	linearLinesType lines;	
	matrixLinesType linesM;
	
	// Read
	int nlines=readInputLines(ps.binFile,&lines); // includes lines allocation
	linesM=(matrixLinesType )(lines); // to get the 2 d representation

	bool col_mask[MAXCOLS];
	for (int i=0; i<MAXCOLS; i++)
		col_mask[i] = false ;
	for (int i=TEST_COL; i<BMI_COL;i++)
		col_mask[i]=true;

	int nftrOff = adjustColMaskByFeatureFlags(col_mask, fflags);
	fprintf(stderr, "%d features marked as not required before first clipping\n", nftrOff);

	xy_data linesXY;
	linesXY.x=lines;
	linesXY.nftrs=MAXCOLS;
	linesXY.nrows=nlines;

	// prepare for outliers  
	// Complete dependent variables
	int ncompleted = complete_dependent(lines,nlines,MAXCOLS) ; // complete lab values that are computable from other values.
	fprintf(stderr,"Completed %d entries\n",ncompleted) ;

	cleaner cln ;
	cln.ndata = MAXCOLS ;
	cln.mode = 1 ;

	if (get_orig_min_values(lines,nlines,cln,MAXCOLS) < 0)
		return -1 ;
	perform_initial_trnasformations(lines,nlines,cln,MAXCOLS) ; // Perform initial transformations on data

//	assert(get_clipping_params_central(&linesXY,CLEANING_CENTRAL_P,CLEANING_STD_FACTOR,MAX_SDVS,MISSING_VAL,&cln.data_min,&cln.data_max,col_mask)!=-1) ;
//	assert(get_clipping_params_iterative(&linesXY,CLEANING_NITER,MAX_SDVS,MISSING_VAL,&cln.data_min,&cln.data_max,col_mask)!=-1) ;
//	update_clipping_params(cln.data_min,cln.data_max,col_mask) ;
//	assert(clear_data_from_bounds(&linesXY,MISSING_VAL,cln.data_min,cln.data_max,col_mask) != -1) ;

	assert(get_cleaning_moments(&linesXY,CLEANING_NITER,MAX_SDVS_FOR_CLPS,MISSING_VAL,&cln.data_avg,&cln.data_std,col_mask) != -1) ;
	assert(get_cleaning_minmax(cln.data_avg,cln.data_std,cln.min_orig_data,MAX_SDVS_FOR_RMVL,&cln.data_min,&cln.data_max,linesXY.nftrs,col_mask) != -1) ;
	clean_from_moments(&linesXY,cln.data_avg,cln.data_std,cln.data_min,cln.data_max,MISSING_VAL,MAX_SDVS_FOR_CLPS,MAX_SDVS_FOR_NBRS) ;

	generalized_learner_info_t learn_info;
	assert (init_learner_info(ps,&gbm_params,&fflags,lines,nlines,MAXCOLS,learn_info) != -1) ;

	// Get Matrix
	xy_data xy;
	init_xy(&xy) ;
	
	int last_pos_day = get_day(ps.cancerDate)-ps.endPeriod ;
	assert(get_xy(linesM,nlines,ps,&xy,last_pos_day,&fflags,0,cln.mode)!=-1);	

	free(lines) ;
	if (ps.only_completions)
		return 0 ;

	take_flagged(&xy) ; // working in place in tx ty  barak

	// Pre-process
	int square = (method=="LM") ; // in linear regression we actually do parabolic regression

	if (square)
		assert(take_squares(&xy) != -1) ; // working in place in tx

	bool *colon_mask;
	assert(colon_mask= (bool *)malloc(sizeof(bool)*xy.nftrs));
	for(int i=0;i<xy.nftrs;i++)
		colon_mask[i]=true;
	adjust_mask(&fflags,colon_mask) ;
		
	// NO SECOND STAGE OUTLIERS CLEANING !
	cln.nftrs = xy.nftrs ;
//	assert(get_clipping_params_central(&xy,CLEANING_CENTRAL_P,CLEANING_STD_FACTOR,MAX_SDVS,MISSING_VAL,&cln.ftrs_min,&cln.ftrs_max,colon_mask)!=-1) ; 
//	assert(get_clipping_params_iterative(&xy,CLEANING_NITER,MAX_SDVS,MISSING_VAL,&cln.ftrs_min,&cln.ftrs_max,colon_mask)!=-1) ;
//	update_clipping_params(cln.ftrs_min,cln.ftrs_max,fflags,square) ;
//	assert(clear_data_from_bounds(&xy,MISSING_VAL,cln.ftrs_min,cln.ftrs_max) != -1) ;

	xy.w = (double *) malloc(xy.nrows*sizeof(double)) ;
	for (int i=0; i<xy.nrows; i++)
		xy.w[i] = 1 ;

	int npos = 0, nneg = 0 ;
	for (int i=0; i<xy.nrows; i++) {
		if (xy.y[i] == 1.0)
			npos++ ;
		else
			nneg++ ;
	}
	fprintf(stderr,"Working on %d (%d + %d) x %d\n",xy.nrows,npos,nneg,xy.nftrs) ;

	double *x ;
	assert(transpose(xy.x,&x,xy.nrows,xy.nftrs)!=-1) ;
	free(xy.x);
	xy.x=x;
	
	//missing values replacement
	int size_for_completion = xy.nftrs ;
	double *means_for_completion = (double *) malloc(size_for_completion*sizeof(double)) ;
	double *sdvs_for_completion = (double *) malloc(size_for_completion*sizeof(double)) ;
	assert(means_for_completion != NULL && sdvs_for_completion != NULL);
	get_mean_values(&xy,means_for_completion,sdvs_for_completion)  ;
	
	replace_with_approx_mean_values(&xy,means_for_completion,sdvs_for_completion) ;
	handleOutliersParams(ps.outliersParamsFile,means_for_completion,sdvs_for_completion,cln) ;
	fclose(ps.outliersParamsFile) ;
	
	// Learn
	unsigned char *model = NULL ;

	int modelSize ;

	assert((modelSize = learn_predictor(&xy,method, &learn_info,&model))>0);

	int methodIndex=ps.methodMap[ps.methodString];

	fprintf(stderr,"Got Model of size %d method %s methodIndex %d , writing it to file %s\n",modelSize,ps.methodString.c_str(), methodIndex, ps.predictorFileName.c_str()); fflush(stderr);
	assert(gzwrite(ps.predictorFile, &modelSize, sizeof(modelSize)) == sizeof(modelSize));
	assert(gzwrite(ps.predictorFile, &methodIndex, sizeof(methodIndex)) == sizeof(methodIndex));
	assert(gzwrite(ps.predictorFile, model, modelSize) == modelSize);
	gzclose(ps.predictorFile);

	tick2= clock();
	fprintf(stderr , "cpu_time %f\n", (double (tick2-tick1)/CLOCKS_PER_SEC)); fflush(stderr);

	time2 = time(NULL);
	fprintf(stderr , "wallclock_time %f\n", double (time2-time1)); fflush(stderr);

}

//------------------------ end of main -------------------------------------

// Local Functions

void openFiles(learnParamStrType *ps)
{
	assert(ps->binFile= safe_gzopen(ps->binFileName.c_str(), "rb"));
	assert(ps->logFile= safe_fopen(ps->logFileName.c_str(), "w"));
	fprintf(stderr,"predictor file is %s\n",ps->predictorFileName.c_str());
	assert(ps->predictorFile= safe_gzopen(ps->predictorFileName.c_str(), "wb"));
	if (ps->use_completions) {
		fprintf(stderr,"##>> will use a precomputed completion file : %s\n",ps->completionParamsFileName.c_str());
		assert(ps->completionParamsFile= safe_gzopen(ps->completionParamsFileName.c_str(), "rb"));
	} else
		assert(ps->completionParamsFile= safe_gzopen(ps->completionParamsFileName.c_str(), "wb"));
	assert(ps->outliersParamsFile= safe_fopen(ps->outliersParamsFileName.c_str(), "w"));

	if (ps->incFileName == "")
		ps->incFile = NULL ;
	else {
		fprintf(stderr,"Openning incidence file %s\n",ps->incFileName.c_str()); fflush(stderr);
		assert(ps->incFile = safe_fopen(ps->incFileName.c_str(), "r")) ;
	}

	if (ps->extraParamsFileName == "")
		ps->extraParamsFile = NULL ;
	else
		assert(ps->extraParamsFile = fopen(ps->extraParamsFileName.c_str(), "r")) ;

}

int getCommandParams(int argc,char **argv,learnParamStrType *ps)
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
			("binFile", po::value<string>(&ps->binFileName)->required(), " bin input file of lab tests")
			("logFile", po::value<string>(&ps->logFileName)->required(), " log output file")
			("predictorFile", po::value<string>(&ps->predictorFileName)->required(), " predictor model output file")
			("completionFile", po::value<string>(&ps->completionParamsFileName)->required(), " completion model output file")
			("use_completions", po::bool_switch(&ps->use_completions), "use precomuted completion models from file")
			("only_completions", po::bool_switch(&ps->only_completions), "stop after creating completion models and writing to file")
			("outliersFile", po::value<string>(&ps->outliersParamsFileName)->required(), " outliers model output file")
			("start", po::value<int>(&ps->startPeriod)->required(), "start date")
			("end", po::value<int>(&ps->endPeriod)->required(), "end date")
			("cancerDate", po::value<int>(&ps->cancerDate)->required(), "cancer date")
			("featuresSelection", po::value<string>(&ps->featuresSelectString)->required(), "features selection string")
			("extraFeatures", po::value<string>(&ps->extraFeaturesString)->default_value("XZ"), "optional string for extra features")
			("method", po::value<string>(&ps->methodString)->required(), "method of classification")
			("nfold", po::value<int>(&ps->nfold)->default_value(0), "number of folds in cross validation")
			("seed", po::value<int>(&ps->seed)->default_value(SRANDSEED), "random seed for cross validation")
			("matching_w", po::value<double>(&ps->matching_w)->default_value(MATCHING_W), "Relative weight of controls in selecting optimal matching ratio")
			("matching_field", po::value<string>(&ps->matching_field)->default_value("no field"), "Field for matching (Age/Parameter Name ; comma separated)")
			("matching_res",po::value<string>(&ps->matching_res)->default_value("no res"), "Resolution for matching (comma separated)")
			("score_probs_nfold", po::value<int>(&ps->sp_nfold)->default_value(0), "number of folds for calculating score-probs")
			("score_probs_start", po::value<int>(&ps->sp_start_period)->default_value(0), "start of period for calculating score-probs")
			("score_probs_end", po::value<int>(&ps->sp_end_period)->default_value(0), "end of period for calculating score-probs")
			("two_stage_nfold", po::value<int>(&ps->ts_nfold)->default_value(0), "number of folds for calculating matched predictions")
			("internal_method", po::value<string>(&ps->internal_method)->default_value("RF"), "method of actual classification in complex method")
			("external_method", po::value<string>(&ps->external_method)->default_value("RF"), "method of external classification in complex method")
			("incidence",po::value<string>(&ps->incFileName)->default_value(""),"external_prior_field related incidence file")
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
				std::cerr<<"error reading infile "<<vm["infile"].as<string>() <<std::endl;
				exit(-1);
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

void params2Stderr(learnParamStrType& ps)
{
	fprintf(stderr,"Input File: %s\n",ps.binFileName.c_str()) ;
	fprintf(stderr,"Log File: %s\n",ps.logFileName.c_str()) ;
	fprintf(stderr,"Time Window: %d-%d\n",ps.startPeriod,ps.endPeriod) ;
	fprintf(stderr,"Last Cancer Date: %d\n",ps.cancerDate) ;
	fprintf(stderr,"Features Flag: %s\n",ps.featuresSelectString.c_str()) ;
	fprintf(stderr,"Method: %d - %s\n",ps.methodMap[ps.methodString],ps.methodString.c_str()) ;
	fprintf(stderr,"NFold: %d\n",ps.nfold) ;
	fprintf(stderr,"Seed: %d\n",ps.seed) ;

	if (ps.extraParamsFileName != "")
		fprintf(stderr,"Extra Prams File : %s\n",ps.extraParamsFileName.c_str()) ;

}

void checkParams(learnParamStrType& ps) {

	if (ps.methodMap.find(ps.methodString) == ps.methodMap.end()) {
		fprintf(stderr,"Unknown method \'%s\'\n",ps.methodString.c_str()) ;
		exit(-1) ;
	}

	if (ps.methodMap.find(ps.internal_method) == ps.methodMap.end()) {
		fprintf(stderr,"Unknown method \'%s\'\n",ps.internal_method.c_str()) ;
		exit(-1) ;
	}


	if (ps.ts_nfold > 0 && ps.matching_field == "no field") {
		fprintf(stderr,"two_stage_nfold requires matching_field\n") ;
		exit(-1) ;
	}

	if (ps.sp_nfold > 0 && (ps.sp_end_period <= ps.sp_start_period)) {
		fprintf(stderr,"Error in Score-Probs calculating parameters. When score_probs_nfold given, score_probs_end_preiod and start_period should be given and ordered\n") ;
		exit(-1) ;
	}

	if (ps.sp_nfold > 0 && ps.ts_nfold) {
		fprintf(stderr,"Either two_stage_nfold or score_probs_nfold should be given\n") ;
		exit(-1) ;
	}
}
