// Predictors
#define _CRT_SECURE_NO_WARNINGS

#include "localCommonLib.h"

// Handling parameters for GBM
int read_gbm_params(char *file, gbm_parameters *gbm_params) {

	// Read From File
	FILE *fp = safe_fopen(file, "r", false) ;
	if (fp == NULL)
		return 1 ;

	char buffer[MAX_STRING_LEN] ;
	char name[MAX_STRING_LEN] ;
	char value[MAX_STRING_LEN] ;

	char *startbuf,*endbuf ;
	map<string,int> done ;
	gbm_params->take_all_pos = false ;

	while(!(feof(fp))) {      
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;
			       
		startbuf = buffer;             
		endbuf = buffer;

		// Name
		while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != '\t'))
			*endbuf ++ ;

		if (*endbuf != '\t' || endbuf - startbuf > MAX_STRING_LEN - 1)
			return -1 ;

		strncpy(name,startbuf, endbuf-startbuf);                     
		name[endbuf-startbuf]='\0';
		startbuf= ++endbuf ;

		// Value
		while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != '\t'))
			*endbuf ++ ;

		if (((*endbuf != '\n') && (*endbuf != '\r')) || endbuf - startbuf > MAX_STRING_LEN - 1)
			return -1 ;
		
		strncpy(value,startbuf, endbuf-startbuf);                     
		value[endbuf-startbuf]='\0';

		// Set value
		
		if (done.find(name) != done.end()) {
			fprintf(stderr,"Field %s given more than once in %s\n",name,file) ;
			return -1 ;
		}


		done[name] = 1 ;
		if (strcmp(name,"Shrinkage")==0)
			gbm_params->shrinkage = atof(value) ;
		else if (strcmp(name,"BagP")==0)
			gbm_params->bag_p = atof(value) ;		
		else if (strcmp(name,"NTrees")==0)
			gbm_params->ntrees = atoi(value) ;	
		else if (strcmp(name,"Depth")==0)
			gbm_params->depth = atoi(value) ;	
		else if (strcmp(name,"NTrees")==0)
			gbm_params->ntrees = atoi(value) ;	
		else if (strcmp(name,"TakeAllPos")==0)
			gbm_params->take_all_pos = true ;
		else if (strcmp(name,"MinObsInNode")==0)
			gbm_params->min_obs_in_node = atoi(value) ;
		else {
			fprintf(stderr,"Unknown field %s in %s\n",name,file) ;
			return -1 ;
		}
	}

	if (done.find("Shrinkage")==done.end() || done.find("BagP")==done.end() || done.find("NTrees")==done.end() || done.find("TakeAllPos")==done.end() || done.find("MinObsInNode")==done.end()) {
		fprintf(stderr,"Not all requred fields (Shrinkage,BagP,NTrees,TakeAllPos,MinObsInNode) appear in %s\n",file) ;
		return -1 ;
	}

	
	fclose(fp) ;

	return 0 ;
}

int set_gbm_parameters (char *type, gbm_parameters *gbm_params) {

	if (strcmp(type,"CRC")==0) {
		gbm_params->shrinkage = CRC_GBM_SHRINKAGE ;
		gbm_params->bag_p = CRC_GBM_BAG_P ;
		gbm_params->ntrees = CRC_GBM_NTREES ;
		gbm_params->depth = CRC_GBM_DEPTH ;
		gbm_params->take_all_pos = CRC_GBM_TAKE_ALL_POS ;
		gbm_params->min_obs_in_node = CRC_GBM_MIN_OBS_IN_NODE ;
	} else if (strcmp(type,"QuickCRC")==0) {
		gbm_params->shrinkage = CRC_GBM_SHRINKAGE ;
		gbm_params->bag_p = CRC_GBM_BAG_P ;
		gbm_params->ntrees = 40 ;
		gbm_params->depth = 6 ;
		gbm_params->take_all_pos = CRC_GBM_TAKE_ALL_POS ;
		gbm_params->min_obs_in_node = CRC_GBM_MIN_OBS_IN_NODE ;
	} else if (strcmp(type,"Minimal")==0) {
		gbm_params->shrinkage = CRC_GBM_SHRINKAGE ;
		gbm_params->bag_p = CRC_GBM_BAG_P ;
		gbm_params->ntrees = 50 ;
		gbm_params->depth = 4 ;
		gbm_params->take_all_pos = CRC_GBM_TAKE_ALL_POS ;
		gbm_params->min_obs_in_node = CRC_GBM_MIN_OBS_IN_NODE ;
	} else if (strcmp(type,"LUCA")==0) {
		gbm_params->shrinkage = LUNG_GBM_SHRINKAGE ;
		gbm_params->bag_p = LUNG_GBM_BAG_P ;
		gbm_params->ntrees = LUNG_GBM_NTREES ;
		gbm_params->depth = LUNG_GBM_DEPTH ;
		gbm_params->take_all_pos = LUNG_GBM_TAKE_ALL_POS ;
		gbm_params->min_obs_in_node = LUNG_GBM_MIN_OBS_IN_NODE ;
	} else if (strcmp(type,"ENSEMBLE")==0) {
		gbm_params->ntrees = 70;
		gbm_params->shrinkage = 0.1;
		gbm_params->bag_p=0.25;
		gbm_params->depth=12;
		gbm_params->take_all_pos = true ;
		gbm_params->min_obs_in_node = CRC_GBM_MIN_OBS_IN_NODE ;
	} else if (strcmp(type,"COMB_CRC")==0) {
		gbm_params->shrinkage = CRC_GBM_SHRINKAGE ;
		gbm_params->bag_p = CRC_GBM_BAG_P ;
		gbm_params->ntrees = CRC_GBM_NTREES ;
		gbm_params->depth = CRC_GBM_DEPTH ;
		gbm_params->take_all_pos = CRC_GBM_TAKE_ALL_POS ;
		gbm_params->min_obs_in_node = CRC_GBM_MIN_OBS_IN_NODE ;
	} else {
		fprintf(stderr,"Unknown type \'%s\' for setting GBM parameters\n",type) ;
		assert(0) ;
	}

	return 0 ;
}

// Predictors
// Least Squares
int learn_ls(double *x1, double *y1, double *w1, int nrows1, int ncols, double *b, double *norm) {

	double *corrs = (double *) malloc(ncols*sizeof(double)) ;
	double *rfactors = (double *) malloc(ncols*sizeof(double)) ;
	int *ignore = (int *) malloc(ncols*sizeof(int)) ;
	double *nx = (double *) malloc(ncols*nrows1*sizeof(double)) ;
	double *ny = (double *) malloc(nrows1*sizeof(double)) ;
	if (corrs==NULL || rfactors==NULL || ignore==NULL || nx==NULL || ny==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for (int i=0; i<ncols; i++) {
		rfactors[i] = 0.99 ;
		corrs[i] = 0.0 ;
		ignore[i] = 0 ;
	}

	double *xavg,*xstd ;
	if (tcalc_stats(x1,y1,w1,nrows1,ncols,&xavg,&xstd,norm,MISSING_VAL) == -1) {
		fprintf(stderr,"Failed Caluclating Stats\n") ;
		return -1 ;
	}
	
	memcpy(nx,x1,ncols*nrows1*sizeof(double)) ;
	memcpy(ny,y1,nrows1*sizeof(double)) ;
	tnormalize_data(nx,ny,nrows1,ncols,xavg,*norm,MISSING_VAL) ;

	double err ;
	if (lm(nx,ny,w1,nrows1,ncols,NITER,EITER,rfactors,b,&err,ignore,corrs)==-1) {
		fprintf(stderr,"LM failed\n") ;
		return -1 ;
	}

	for (int i=0; i<ncols; i++)
		(*norm) -= xavg[i]*b[i] ;

	free(nx) ; free(ny); free(xavg); free(xstd) ;
	free(corrs) ; free(ignore) ; free(rfactors) ;
	return 0 ;
}

int learn_ls(double *x, double *y, int nrows, int ncols, double *b, double *norm, int pos_duplicity) {

	double *w = (double *) malloc(nrows*sizeof(double)) ;
	if (w==NULL) {
		fprintf(stderr,"Allocation of weights failed\n") ;
		return -1 ;
	}

	for (int i=0; i<nrows; i++)
		w[i] = (y[i] > 0) ? pos_duplicity : 1 ;

	int rc = learn_ls(x,y,w,nrows,ncols,b,norm) ;
	free(w) ;

	return rc ;
}


int learn_ls(double *x1, double *y1, int nrows1, int ncols, char *fname, int pos_duplicity) {

	double *b = (double *) malloc(ncols*sizeof(double)) ;
	if (b==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}
	double norm ;

	int rc = learn_ls(x1,y1,nrows1,ncols,b,&norm,pos_duplicity) ;

	if (rc != -1) {
		FILE *fp = safe_fopen(fname, "w", false) ;
		if (fp==NULL) {
			fprintf(stderr,"Cannot open %s for writing\n",fname) ;
			return -1 ;
		}

		for (int i=0; i<ncols; i++)
			fprintf(fp,"%d %f\n",i,b[i]) ;
		fprintf(fp,"norm %f\n",norm) ;

		fclose(fp) ;
	}

	free(b) ;
	return rc ;
}

int learn_ls(double *x1, double *y1, int nrows1, int ncols, unsigned char **model, int pos_duplicity) {

	double *b = (double *) malloc((ncols+1)*sizeof(double)) ;
	if (b==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}
	double norm ;

	int rc = learn_ls(x1,y1,nrows1,ncols,b,&norm,pos_duplicity) ;

	if (rc != -1) {
		b[ncols] = norm ;
		*model = (unsigned char *) b ;
		return ((ncols+1)*sizeof(double)) ;
	} else
		return -1 ;
}

int ls_predict_from_file(double *x, double *preds, int nrows, int ncols, char *fname) {

	FILE *fp = safe_fopen (fname, "r", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",fname) ;
		return -1 ;
	}

	double *b = (double *) malloc(ncols*sizeof(double)) ;
	if (b == NULL) {
		fprintf(stderr,"Cannot allocate b\'s for linear regression\n") ;
		return -1 ;
	}

	int ival ;
	double dval ;
	for (int i=0 ; i<ncols; i++) {
		if (fscanf(fp,"%d %lf\n",&ival,&dval) != 2 || ival != i) {
			fprintf(stderr,"Problems parsing data from %s\n",fname) ;
			return -1 ;
		}
		b[i] = dval ;
	}

	double norm ;
	if (fscanf(fp,"norm %lf\n",&norm) != 1) {
		fprintf(stderr,"Problems parsing data from %s\n",fname) ;
		return -1 ;
	}

	//lm_predict(x,nrows,ncols,b,norm,preds) ;

	free(b) ;
	fclose(fp) ;

	return 0 ;
}

int ls_predict_from_model(double *x, double *preds, int nrows, int ncols, unsigned char *model) {

	double norm ;
	memcpy(&norm,model + ncols*sizeof(double),sizeof(double)) ;

	lm_predict(x,nrows,ncols,(double *) model, norm, preds) ;

	return ((ncols + 1) * sizeof(double)) ;
}

	
int get_ls_predictions(double *x1, double *y1, double *w1, int nrows1, double *x2, int nrows2, int ncols, double *preds) {

	// Learn

	double *b = (double *) malloc(ncols*sizeof(double)) ;

	if (b==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	double norm ;
	if (learn_ls(x1,y1,w1,nrows1,ncols,b,&norm)==-1) {
		fprintf(stderr,"LM failed\n") ;
		return -1 ;
	}
		
	// Predict
	lm_predict(x2,nrows2,ncols,b,norm,preds) ;

	free(b) ; 
	return 0 ;
}

int get_ls_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, int pos_duplicity) {

	// Learn

	double *b = (double *) malloc(ncols*sizeof(double)) ;

	if (b==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	double norm ;
	if (learn_ls(x1,y1,nrows1,ncols,b,&norm,pos_duplicity)==-1) {
		fprintf(stderr,"LM failed\n") ;
		return -1 ;
	}
		
	// Predict
	lm_predict(x2,nrows2,ncols,b,norm,preds) ;

	free(b) ; 
	return 0 ;
}

// GBM Ensemble
int get_gbm_ens_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, gbm_parameters *gbm_params, int ens_size) {

	// Learn
	full_gbm_ens_learn_info_t full_info_ens;

	if (get_gbm_predictor_ens(x1,y1,nrows1,ncols,ens_size,&full_info_ens,gbm_params)==-1) {
		fprintf(stderr,"GBM Ensemble learning failed\n") ;
		return -1 ;
	}
	
	// Predict
	 if (gbm_predict_ens(x2,nrows2,ncols,&full_info_ens,preds)==-1) {
		 fprintf(stderr,"GBM prediction failed\n") ;
		 return -1 ;
	 }

	 // Clear
	 clear_gbm_predictor_ens(&full_info_ens) ;

	 return 0 ;
}

int get_gbm_predictions(double *x1, double *y1, double *w1, int nrows1, double *x2, int nrows2, int ncols, double *preds, gbm_parameters *gbm_params) {

	// Learn
	full_gbm_learn_info_t gbm_struct ;

	if (get_gbm_predictor(x1,y1,w1,nrows1,ncols,gbm_params->shrinkage,gbm_params->bag_p,gbm_params->take_all_pos,gbm_params->ntrees,gbm_params->depth,
		gbm_params->min_obs_in_node,&gbm_struct)==-1) {
		fprintf(stderr,"GBM learning failed\n") ;
		return -1 ;
	}
	
	// Predict
	 if (gbm_predict(x2,nrows2,ncols,gbm_params->ntrees,&gbm_struct,preds)==-1) {
		 fprintf(stderr,"GBM prediction failed\n") ;
		 return -1 ;
	 }

	 // Clear
	 clear_gbm_info(&gbm_struct) ;

	 return 0 ;
}

int get_gbm_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, gbm_parameters *gbm_params) {

	double *w1 = (double *) malloc(nrows1*sizeof(double)) ;
	if (w1 == NULL) {
		fprintf(stderr,"Allocation of weights failed\n") ;
		return -1 ;
	}

	for (int i=0; i<nrows1; i++)
		w1[i] = 1.0 ;

	int rc = get_gbm_predictions(x1,y1,w1,nrows1,x2,nrows2,ncols,preds,gbm_params) ;

	free(w1) ;
	return rc ;
}

int gbm_ens_predict(double *x, double *preds, int nrows, int ncols, char *fname) {


	// Read
	full_gbm_ens_learn_info_t gbm_ens_struct ;
	if (read_full_gbm_ens_info(&gbm_ens_struct,fname) == -1) {
		fprintf(stderr,"Reading failed\n") ;
		return -1 ;
	}

	// Predict
	if (gbm_predict_ens(x,nrows,ncols,&gbm_ens_struct,preds)==-1) {
		fprintf(stderr,"GBM prediction failed\n") ;
		return -1 ;
	}

	// Clear
	clear_gbm_predictor_ens(&gbm_ens_struct) ;

	return 0 ;
}

int gbm_ens_predict(double *x, double *preds, int nrows, int ncols, unsigned char *model) {

	int size ;

	// DeSerialize
	full_gbm_ens_learn_info_t gbm_ens_struct ;
	if ((size = gbm_ens_deserialize(model,&gbm_ens_struct))==-1) {
		fprintf(stderr,"Deserialization failed\n") ;
		return -1 ;
	}

	// Predict
	if (gbm_predict_ens(x,nrows,ncols,&gbm_ens_struct,preds)==-1) {
		fprintf(stderr,"GBM prediction failed\n") ;
		return -1 ;
	}

	// Clear
	clear_gbm_predictor_ens(&gbm_ens_struct) ;

	return size ;
}

int learn_gbm_ens_predictor(double *x, double *y, int nrows, int ncols, char *fname, gbm_parameters *gbm_params, int ens_size) {

	// Learn
	full_gbm_ens_learn_info_t full_info_ens;

	if (get_gbm_predictor_ens(x,y,nrows,ncols,ens_size,&full_info_ens,gbm_params)==-1) {
		fprintf(stderr,"GBM Ensemble learning failed\n") ;
		return -1 ;
	}

	if (write_full_gbm_ens_info(&full_info_ens,fname)==-1) {
		fprintf(stderr,"Writing failed\n") ;
		return -1 ;
	}

	// Clear
	clear_gbm_predictor_ens(&full_info_ens) ;

	return 0 ;
}

int learn_gbm_ens_predictor(double *x, double *y, int nrows, int ncols, unsigned char **model, gbm_parameters *gbm_params, int ens_size) {

	// Learn
	full_gbm_ens_learn_info_t full_info_ens;

	if (get_gbm_predictor_ens(x,y,nrows,ncols,ens_size,&full_info_ens,gbm_params)==-1) {
		fprintf(stderr,"GBM Ensemble learning failed\n") ;
		return -1 ;
	}

	// Allocate
	size_t gbm_ens_size = get_gbm_ens_info_size(&full_info_ens) ;
	if (((*model) = (unsigned char *) malloc(gbm_ens_size))==NULL) {
		fprintf(stderr,"Allocation of GBM_Ensemble model failed\n") ;
		return -1 ;
	}

	// Serialize
	if (gbm_ens_serialize(&full_info_ens, *model) == -1) {
		fprintf(stderr,"Serialization of GBM-Ensemble model failed\n") ;
		return -1 ;
	}

	// Clear
	clear_gbm_predictor_ens(&full_info_ens) ;

	return (int)gbm_ens_size ;
}

int gbm_predict(double *x, double *preds, int nrows, int ncols, char *fname) {


	// Read
	full_gbm_learn_info_t gbm_struct ;
	if (read_full_gbm_info(&gbm_struct,fname) == -1) {
		fprintf(stderr,"Reading failed\n") ;
		return -1 ;
	}

	// Predict
	 if (gbm_predict(x,nrows,ncols,gbm_struct.ntrees,&gbm_struct,preds)==-1) {
		 fprintf(stderr,"GBM prediction failed\n") ;
		 return -1 ;
	 }

	 // Clear
	 clear_gbm_info(&gbm_struct) ;

	 return 0 ;
}

int gbm_predict(double *x, double *preds, int nrows, int ncols, unsigned char *model) {

	int size ;

	// DeSerialize
	full_gbm_learn_info_t gbm_struct ;
	if ((size = gbm_deserialize(model,&gbm_struct))==-1) {
		fprintf(stderr,"DeSerialization failed\n") ;
		return -1 ;
	}

	// Predict
	 if (gbm_predict(x,nrows,ncols,gbm_struct.ntrees,&gbm_struct,preds)==-1) {
		 fprintf(stderr,"GBM prediction failed\n") ;
		 return -1 ;
	 }

	 // Clear
	 clear_gbm_info(&gbm_struct) ;

	 return size ;
}

int final_gbm_predict(double *x, double *preds, int nrows, int ncols, char *fname) {

	// Open
	FILE *fp = safe_fopen(fname, "r", false) ;
	if (fp==NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",fname) ;
		return -1 ;
	}

	// Normalize
	double median ;

	int rc = fscanf(fp,"RF median %lf\n",&median) ;
	if (rc != 1) {
		fprintf(stderr,"Cannot read RF median from %s\n",fname) ;
		return -1 ;
	}

//	for (int i=0; i<nrows; i++)
//		x[i] /= median ;

	rc = fscanf(fp,"GBM median %lf\n",&median) ;
	if (rc != 1) {
		fprintf(stderr,"Cannot read GBM median from %s\n",fname) ;
		return -1 ;
	}

//	for (int i=0; i<nrows; i++)
//		x[i+nrows] /= median ;

	// Read
	full_gbm_learn_info_t gbm_struct ;
	read_full_gbm_info(&gbm_struct,fp) ;
	fclose(fp) ;

	// Predict
	 if (gbm_predict(x,nrows,ncols,gbm_struct.ntrees,&gbm_struct,preds)==-1) {
		 fprintf(stderr,"GBM prediction failed\n") ;
		 return -1 ;
	 }

	 // Clear
	 clear_gbm_info(&gbm_struct) ;

	 return 0 ;
}

int learn_gbm_predictor(double *x, double *y, double *w, int nrows, int ncols, char *fname, gbm_parameters *gbm_params) {

	// Learn
	full_gbm_learn_info_t gbm_struct ;

	if (get_gbm_predictor(x,y,w,nrows,ncols,gbm_params->shrinkage,gbm_params->bag_p,gbm_params->take_all_pos,gbm_params->ntrees,gbm_params->depth,gbm_params->min_obs_in_node,&gbm_struct)==-1) {
		fprintf(stderr,"GBM learning failed\n") ;
		return -1 ;
	}
	
	if (write_full_gbm_info(&gbm_struct,fname)==-1) {
		fprintf(stderr,"Writing failed\n") ;
		return -1 ;
	}

	 // Clear
	 clear_gbm_info(&gbm_struct) ;

	 return 0 ;
}

int learn_gbm_predictor(double *x, double *y, int nrows, int ncols, char *fname, gbm_parameters *gbm_params) {

	double *w = (double *) malloc(nrows*sizeof(double)) ;
	if (w == NULL) {
		fprintf(stderr,"Allocation of weights failed\n") ;
		return -1 ;
	}

	for (int i=0; i<nrows; i++)
		w[i] = 1.0 ;

	int rc = learn_gbm_predictor(x,y,w,nrows,ncols,fname,gbm_params) ;

	free(w) ;
	return rc ;
}


int learn_gbm_predictor(double *x, double *y, double *w, int nrows, int ncols, FILE *fp, gbm_parameters *gbm_params) {

	// Learn
	full_gbm_learn_info_t gbm_struct ;

	if (get_gbm_predictor(x,y,w,nrows,ncols,gbm_params->shrinkage,gbm_params->bag_p,gbm_params->take_all_pos,gbm_params->ntrees,gbm_params->depth, gbm_params->min_obs_in_node,&gbm_struct)==-1) {
		fprintf(stderr,"GBM learning failed\n") ;
		return -1 ;
	}
	
	write_full_gbm_info(&gbm_struct,fp) ;

	 // Clear
	 clear_gbm_info(&gbm_struct) ;

	 return 0 ;
}


int learn_gbm_predictor(double *x, double *y, int nrows, int ncols, FILE *fp, gbm_parameters *gbm_params) {

	double *w = (double *) malloc(nrows*sizeof(double)) ;
	if (w == NULL) {
		fprintf(stderr,"Allocation of weights failed\n") ;
		return -1 ;
	}

	for (int i=0; i<nrows; i++)
		w[i] = 1.0 ;

	int rc = learn_gbm_predictor(x,y,w,nrows,ncols,fp,gbm_params) ;

	free(w) ;
	return rc ;
}

int learn_gbm_predictor(double *x, double *y, double *w, int nrows, int ncols, unsigned char **model, gbm_parameters *gbm_params) {

	// Learn
	full_gbm_learn_info_t gbm_struct ;

	if (get_gbm_predictor(x,y,w,nrows,ncols,gbm_params->shrinkage,gbm_params->bag_p,gbm_params->take_all_pos,gbm_params->ntrees,gbm_params->depth,gbm_params->min_obs_in_node,&gbm_struct)==-1) {
		fprintf(stderr,"GBM learning failed\n") ;
		return -1 ;
	}

	// Allocate
	size_t gbm_size = get_gbm_info_size(&gbm_struct) ;
	if (((*model) = (unsigned char *) malloc(gbm_size))==NULL) {
		fprintf(stderr,"Allocation of GBM model failed\n") ;
		return -1 ;
	}

	// Serialize
	if (gbm_serialize(&gbm_struct, *model) == -1) {
		fprintf(stderr,"Serialization of GBM model failed\n") ;
		return -1 ;
	}

	 // Clear
	 clear_gbm_info(&gbm_struct) ;

	 return (int)gbm_size ;
}

int learn_gbm_predictor(double *x, double *y, int nrows, int ncols, unsigned char **model, gbm_parameters *gbm_params) {

	double *w = (double *) malloc(nrows*sizeof(double)) ;
	if (w == NULL) {
		fprintf(stderr,"Allocation of weights failed\n") ;
		return -1 ;
	}

	for (int i=0; i<nrows; i++)
		w[i] = 1.0 ;

	int rc = learn_gbm_predictor(x,y,w,nrows,ncols,model,gbm_params) ;

	free(w) ;
	return rc ;
}

// QRF
int learn_qrf_predictor(double *tx, double *y, int nrows, int ncols, unsigned char **model, int ntrees, int ntry, int maxq, int nthreads) 
{

	// Transpose matrix ; 
	double *x  ;
	if (transpose(tx,&x,nrows,ncols,1)==-1) {
		fprintf(stderr,"Transpose failed\n") ; fflush(stderr);
		return -1 ;
	}

	// Select subset
	int npos=0, nneg=0 ;
	for (int i=0; i<nrows; i++) {
		if (y[i] > 0)
			npos++ ;
		else
			nneg++ ;
	}

	int samp_pos = (int) (npos * RF_POS_FACTOR);
	int samp_neg = (int) (samp_pos * RF_FACTOR) ;
	if (samp_neg > nneg)
		samp_neg = nneg ;

	if (samp_neg < MIN_SAMP_NEG)
		samp_neg = MIN_SAMP_NEG ;

	fprintf(stderr,"SampSize = (%d,%d)\n",samp_neg,samp_pos); fflush(stderr);

	int sampsize[2];
	sampsize[0] = samp_neg;
	sampsize[1] = samp_pos;

	QRF_Forest qf;

	qf.nthreads = nthreads;
	qf.mode = QRF_MODE;
	fprintf(stderr, "QRF_Forest before get_forest: min_node_size=%d\n", qf.min_node_size); fflush(stderr);
	if (qf.get_forest(x, y, ncols, nrows, sampsize, ntry , ntrees, maxq) < 0) {
		fprintf(stderr,"get QRF forest failed...\n"); fflush(stderr);
		return -1;
	}
	
	unsigned char *serialized = NULL;
	int size;
	if ((size = (int) qf.serialize(serialized)) < 0) {
		fprintf(stderr,"serializing QRF forest failed...\n"); fflush(stderr);
		return -1;
	}

	*model = serialized;
	
	free(x);
	return(size);
}



int get_qrf_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, int ntrees, int ntry, int maxq, int nthreads) {

	unsigned char *model;
	if (learn_qrf_predictor(x1,y1,nrows1,ncols,&model,ntrees,ntry,maxq,nthreads) ==-1) {
		fprintf(stderr,"learn_qrf_predictor failes\n"); fflush(stderr);
		return -1 ;
	}


	if (qrf_predict(x2,preds,nrows2,ncols,model,nthreads) ==-1) {
		fprintf(stderr,"qrf_predict failed\n"); fflush(stderr);
		return -1 ;
	}

	free(model);

	return 0 ;

}


// Random Forest
int learn_rf_predictor(double *x1, double *y1, int nrows1, int ncols, char *ftree , int ntrees) {

	// Select subset
	int npos=0, nneg=0 ;
	for (int i=0; i<nrows1; i++) {
		if (y1[i] > 0)
			npos++ ;
		else
			nneg++ ;
	}

	int samp_pos = (int) (npos * RF_POS_FACTOR);
	int samp_neg = (int) (samp_pos * RF_FACTOR) ;
	if (samp_neg > nneg)
		samp_neg = nneg ;

	if (samp_neg < MIN_SAMP_NEG)
		samp_neg = MIN_SAMP_NEG ;

	fprintf(stderr,"SampSize = (%d,%d)\n",samp_neg,samp_pos) ;
	
	// Learn 
	if (R_learn_classification_strat(x1,y1,nrows1,ncols,samp_neg,samp_pos,ftree,ntrees)==-1) {
		fprintf(stderr,"R-learner failed\n") ;
		return -1 ;
	}

	return 0 ;

}

int learn_rf_predictor(double *x, double *y, int nrows, int ncols, int ntrees) {
	return learn_rf_predictor(x,y,nrows,ncols,TREE_FILE,  ntrees) ;
}

int learn_rf_predictor(double *x, double *y, int nrows, int ncols, char *file_name, unsigned char **model, int ntrees) {

	if (learn_rf_predictor(x,y,nrows,ncols,file_name, ntrees)==-1) {
		fprintf(stderr,"Learning RF predictor failed\n") ;
		return -1 ;
	}

	int size ;
	if ((size = read_blob(file_name,model))==-1) {
		fprintf(stderr,"Reading RF model from \'%s\' failed\n",file_name) ;
		return -1 ;
	}

	return size ;
}

int learn_rf_predictor(double *x, double *y, int nrows, int ncols, unsigned char **model, int ntrees) {
	return learn_rf_predictor(x,y,nrows,ncols,TREE_FILE,model, ntrees) ;
}

int get_rf_predictions(double *x1, double *y1, int nrows1, double *x2, int nrows2, int ncols, double *preds, int ntrees) {

	if (learn_rf_predictor(x1,y1,nrows1,ncols,ntrees) ==-1) {
		fprintf(stderr,"R-learner failed\n") ;
		return -1 ;
	}

	if (rf_predict(x2,preds,nrows2,ncols)==-1) {
		fprintf(stderr,"rf-predictor failed\n") ;
		return -1 ;
	}

	return 0 ;

}


// Get Statistics
int get_all_stats(double *labels, double *predictions, int nsamples, int nbins, int resolution, int *bins, int *eqsize_bins) {

	// Order Predictions
	struct pred_val *values = (struct pred_val *) malloc(nsamples * sizeof(struct pred_val)) ;
	if (values == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for (int i=0; i<nsamples; i++) {
		values[i].pred = predictions[i] ;
		values[i].ind = i ;
	}

	qsort(values,nsamples,sizeof(struct pred_val), compare_pred_vals) ;

	// Alocate
	double *init_x ;
	double *init_y ;

	if ((init_x = (double *) malloc (sizeof (double)*nsamples)) == NULL) {
		fprintf (stderr,"error : cannot allocate x for %d samples\n",nsamples) ;
		return -1 ;
	}

	if ((init_y = (double *) malloc (sizeof (double)*nsamples)) == NULL) {
		fprintf (stderr,"error : cannot allocate y for %d samples\n",nsamples) ;
		return -1 ;
	}

	// P and N
	int pos = 0;
	int neg = 0 ;

	for (int i=0; i<nsamples; i++) {
		if (labels[i] > 0.0) {
			pos++ ;
		} else {
			neg++ ;
		}
	}	

	// Calculate FP and TP
	double *fp ;
	double *tp ;

	if ((fp = (double *) malloc (sizeof (double)*nsamples)) == NULL) {
		fprintf (stderr,"error : cannot allocate fp for %d samples\n",nsamples) ;
		return -1 ;
	}

	if ((tp = (double *) malloc (sizeof (double)*nsamples)) == NULL) {
		fprintf (stderr,"error : cannot allocate tp for %d samples\n",nsamples) ;
		return -1 ;
	}

	for (int i=nsamples-1; i>=0; i--) {		
		if (labels[values[i].ind] > 0.0) {
			if (i==nsamples-1) {
				tp[i] = 1 ;
				fp[i] = 0 ;
			} else {
				tp[i] = tp[i+1] + 1 ;
				fp[i] = fp[i+1] ;
			}

//			printf("Precision = %.3f // Recall = %.3f // Spec = %.3f // TP = %d // FP = %d // FN = %d // TN = %d\n",
//				tp[i]/(tp[i]+fp[i]),tp[i]/pos,(neg-fp[i])/neg,(int)tp[i],(int)fp[i],(int)(pos-tp[i]),(int)(neg-fp[i])) ;
		} else {
			if (i==nsamples-1) {
				tp[i] = 0 ;
				fp[i] = 1 ;
			} else {
				tp[i] = tp[i+1] ;
				fp[i] = fp[i+1] + 1 ;
			}
		}
	}

	// Calculate X and Y

	for (int i=0; i<nsamples; i++) {
		init_x[i] = fp[i]/neg ;
		init_y[i] = tp[i]/pos ;
	}

	// Take care of required resolution
	double *x ;
	double *y ;

	if ((x = (double *) malloc (sizeof (double)*resolution)) == NULL) {
		fprintf (stderr,"error : cannot allocate x for %d bins\n",resolution) ;
		return -1 ;
	}

	if ((y = (double *) malloc (sizeof (double)*resolution)) == NULL) {
		fprintf (stderr,"error : cannot allocate y for %d bins\n",resolution) ;
		return -1 ;
	}
	memset(y,0,sizeof(double)*resolution) ;

	int *num ;
	if ((num = (int *) malloc (sizeof (int)*resolution)) == NULL) {
		fprintf (stderr,"error : cannot allocate counter for %d bins\n",resolution) ;
		return -1 ;
	}
	memset(num,0,sizeof(int)*resolution) ;

	double min_x = 0 ;
	double max_x = 0 ;
	for (int i=0; i<nsamples; i++) {
		if (i==0 || min_x > init_x[i])
			min_x = init_x[i] ;
		if (i==0 || max_x < init_x[i])
			max_x = init_x[i] ;
	}

	double x_bin_size = (max_x-min_x)/resolution ;
	for (int i=0; i<nsamples; i++) {
		int x_bin ;
		if (init_x[i] == max_x) {
			x_bin = resolution - 1 ;
		} else {
			x_bin = (int)((init_x[i]-min_x)/x_bin_size) ;
		}

		num[x_bin]++ ;
		y[x_bin]+=init_y[i] ;
	}
		
	for (int i=0; i<resolution; i++) {
		x[i] = min_x + i*x_bin_size ;
		if (y[i] > 0) {
			y[i] /= num[i] ;
		} else if (i==0) {
			y[i] = 0 ;
		} else {
			y[i] = y[i-1] ;
		}
	}

	// Calculate AUC
	/*
	double auc = 0 ;
	for (int i=0; i<resolution-1; i++)
		auc += x_bin_size * (y[i] + y[i+1])/2 ;
	printf("AUC = %.3f\n",auc) ;
	*/

	// Get Histograms - Equale Pos-Size
	int bin_size = pos/nbins ;
	int extra_size = pos - bin_size*nbins ;

	int bin_pos = 0, bin_tot = 0, ibin = 0 ;
	for (int i=0; i<nsamples; i++) {
		bin_tot++ ;
		if (labels[values[i].ind] > 0)
			bin_pos++ ;
		bins[values[i].ind] = ibin ;

		if ((ibin==0 && bin_pos == (bin_size + extra_size)) || (ibin>0 && bin_pos == bin_size)) {
			double p = (bin_pos + 0.0)/bin_tot ;

			printf("Bin %d : Tot = %d ; Pos = %d ; Prob = %f\n", ibin, bin_tot, bin_pos, p) ;

			ibin++ ;
			bin_tot = bin_pos = 0 ;
			if (ibin == nbins -1) {
				for (int j = i + 1 ; j < nsamples ; j++)
					bins[values[j].ind] = ibin ;
				break ;
			}
		}
	}

	// Get Histograms - Equale Tot-Size
	bin_size = nsamples/nbins ;
	extra_size = nsamples - bin_size*nbins ;

	bin_pos = bin_tot = ibin = 0 ;
	for (int i=0; i<nsamples; i++) {
		bin_tot++ ;
		if (labels[values[i].ind] > 0)
			bin_pos++ ;
		eqsize_bins[values[i].ind] = ibin ;

		if ((ibin==0 && bin_tot == (bin_size + extra_size)) || (ibin>0 && bin_tot == bin_size)) {
			double p = (bin_pos + 0.0)/bin_tot ;

			printf("EqSize-Bin %d : Tot = %d ; Pos = %d ; Prob = %f\n", ibin, bin_tot, bin_pos, p) ;

			ibin++ ;
			bin_tot = bin_pos = 0 ;
			if (ibin == nbins -1) {
				for (int j = i + 1 ; j < nsamples ; j++)
					eqsize_bins[values[j].ind] = ibin ;
				break ;
			}
		}
	}

	free(values) ;
	free(init_x) ;
	free(init_y) ;
	free(tp) ;
	free(fp) ;
	free(x) ;
	free(y) ;
	free(num) ;

	return 0 ;
}