#define _CRT_SECURE_NO_WARNINGS

#include "full_cv.h"

/*
Main file of Full Cross Validation program
Get a bin file and timing/method/features parameters (see details in argv definition)
Perform cross validation and produce predictions as well as some basic stats
*/
int main(int argc, char *argv[]) {
	fullCVParamStrType ps; // holds parameters given in command line

	getCommandParams(argc,argv,&ps);
	checkParams(ps) ;

	params2Stderr(ps) ;
	openFiles(&ps); // required at this stage for Condor for all files

	feature_flags fflags ;
	ps.featuresSelectString += ps.extraFeaturesString ;
	assert(get_feature_flags((char *)(ps.featuresSelectString.c_str()),&fflags)!=-1) ;

	string method(ps.methodString) ;

	gbm_parameters gbm_params ;
	set_gbm_parameters ("CRC",&gbm_params) ;
	if(method=="LUNG_GBM"){
		set_gbm_parameters ("LUCA",&gbm_params) ;
		method="GBM";// Yaron's Dirty trick.
		ps.methodString="GBM";
	} else if(method=="ENSGBM")
		set_gbm_parameters ("ENSEMBLE",&gbm_params) ;

	linearLinesType lines;	
	matrixLinesType linesM;

	// Read
	int nlines=readInputLines(ps.binFile,&lines); // includes lines allocation
	linesM=(double (*)[MAXCOLS])lines; // to get the 2 d representation

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

	// Complete dependent variables
	int ncompleted = complete_dependent(lines,nlines,MAXCOLS) ;// complete lab values that are computable from other values.
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


	// Get Matrix
	xy_data xy;
	init_xy(&xy) ;

	int last_pos_day = get_day(ps.cancerDate)-ps.endPeriod ;
	assert(get_xy(linesM,nlines,ps,&xy,last_pos_day,&fflags,0,cln.mode)!=-1);	

	free(lines) ;

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

	// Do CV
	generalized_learner_info_t learn_info;
	ps.matching_field = "no matching" ; 
	init_learner_info(ps,&gbm_params,&fflags,lines,nlines,MAXCOLS,learn_info) ;

	double *out_labels = (double *) malloc((xy.nrows)*sizeof(double)) ;
	int *out_dates = (int *) malloc((xy.nrows)*sizeof(int)) ;
	int *out_ids = (int *) malloc((xy.nrows)*sizeof(int)) ;
	int *out_flags = (int *) malloc((xy.nrows)*sizeof(int)) ;
	int *out_censor = (int *) malloc((xy.nrows)*sizeof(int)) ;
	double *preds = (double *) malloc((xy.nrows)*sizeof(double)) ;

	if (out_labels == NULL || out_dates == NULL || out_ids == NULL || out_flags == NULL || out_censor == NULL || preds == NULL) {
		fprintf(stderr,"Allocation for CV failed\n") ;
		return -1 ;
	}

	assert(get_predictions(&xy,method,&learn_info,ps.nfold,preds,out_dates,out_ids,out_flags,out_censor,out_labels) != -1) ;

	// Get Stat
	fprintf(stderr,"Binning ... ") ;

	int *bins = (int *) malloc((xy.nrows)*sizeof(int)) ;
	int *eqsize_bins = (int *) malloc((xy.nrows)*sizeof(int)) ;
	assert(bins != NULL && eqsize_bins != NULL) ;		

	assert(get_all_stats(out_labels,preds,xy.nrows,ps.nbins,100,bins,eqsize_bins) != -1) ;

	time_t rawtime ;
	time(&rawtime) ;
	fprintf(ps.predictOutFile, "Cross Validation\t%s\t%s\t%d-%d\t%s\t%s\t%s %s\t%s",ps.header_info.c_str(),ps.binFileName.c_str(),ps.startPeriod,ps.endPeriod,method.c_str(),ps.featuresSelectString.c_str(),
		__DATE__,__TIME__,ctime(&rawtime)) ;

	for (int i=0; i< xy.nrows ; i++)			
		fprintf(ps.predictOutFile,"%d %d %.2f %d %d\n",out_ids[i],out_dates[i],preds[i],bins[i],eqsize_bins[i]) ;
	fclose(ps.predictOutFile) ;
}

//------------------------ end of main -------------------------------------

// Local Functions
void openFiles(fullCVParamStrType *ps)
{
	assert(ps->binFile = safe_gzopen(ps->binFileName.c_str(), "rb"));
	assert(ps->logFile = safe_fopen(ps->logFileName.c_str(), "w"));
	assert(ps->predictOutFile = safe_fopen(ps->predictOutFileName.c_str(), "wb"));
}

int getCommandParams(int argc,char **argv,fullCVParamStrType *ps)
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
			("predictOutFile", po::value<string>(&ps->predictOutFileName)->required(), " predictions output file")
			("start", po::value<int>(&ps->startPeriod)->required(), "start date")
			("end", po::value<int>(&ps->endPeriod)->required(), "end date")
			("cancerDate", po::value<int>(&ps->cancerDate)->required(), "cancer date")
			("featuresSelection", po::value<string>(&ps->featuresSelectString)->required(), "features selection string")
			("extraFeatures", po::value<string>(&ps->extraFeaturesString)->default_value("XZ"), "optional string for extra features")
			("method", po::value<string>(&ps->methodString)->required(), "method of classification")
			("nfold", po::value<int>(&ps->nfold)->required(), "number of folds in ceoss validation")
			("nbins", po::value<int>(&ps->nbins)->required(), "number of bins in cross validation")
			("seed", po::value<int>(&ps->seed)->default_value(SRANDSEED), "random seed for cross validation")
			("header", po::value<string>(&ps->header_info)->required(), "Information at header of predictions file")
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

void params2Stderr(fullCVParamStrType& ps)
{

	fprintf(stderr,"Input File: %s\n",ps.binFileName.c_str()) ;
	fprintf(stderr,"Log File: %s\n",ps.logFileName.c_str()) ;
	fprintf(stderr,"Preds File: %s\n",ps.predictOutFileName.c_str()) ;
	fprintf(stderr,"Time Window: %d-%d\n",ps.startPeriod,ps.endPeriod) ;
	fprintf(stderr,"Last Cancer Date: %d\n",ps.cancerDate) ;
	fprintf(stderr,"Features Flag: %s\n",ps.featuresSelectString.c_str()) ;
	fprintf(stderr,"Method: %d - %s\n",ps.methodMap[ps.methodString],ps.methodString.c_str()) ;
	fprintf(stderr,"NFold: %d\n",ps.nfold) ;
	fprintf(stderr,"Nbins: %d\n",ps.nbins) ;
	fprintf(stderr,"Seed: %d\n",ps.seed) ;

}


void checkParams(fullCVParamStrType& ps) {

	if (ps.methodMap.find(ps.methodString) == ps.methodMap.end()) {
		fprintf(stderr,"Unknown method \'%s\'\n",ps.methodString.c_str()) ;
		exit(-1) ;
	}

}