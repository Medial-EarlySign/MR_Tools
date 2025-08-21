// New Method

#define _CRT_SECURE_NO_WARNINGS

#include "localCommonLib.h"

int learn_double_matched_predictor(xy_data *xy, generalized_learner_info_t *learning_info, unsigned char **model) {

	if (learning_info->matching_col.size() != 0) {
		fprintf(stderr,"No Matching Cols allowed in DoubleMatched\n") ;
		return -1 ;
	}

	// Get prediction on data matched on first-field (Hemoglobin, matching-w = 0.015) ;
	learning_info->matching_col.push_back(learning_info->field_cols["Hemog"]) ;
	learning_info->matching_res.push_back(0.5); 
	learning_info->matching_w = 0.015 ;

	fprintf(stderr,"Getting matched predictions\n") ;
	map<pair<int,int>, double> preds_hash ;
	if (get_predictions(xy,learning_info->internal_method.c_str(),learning_info,learning_info->nfold,preds_hash) == -1) {
		fprintf(stderr,"Get Predictions Failed\n") ;
		return -1 ;
	}

	// Learn Hemoglobin-matched predictor
	fprintf(stderr,"Learning on matched data\n") ;

	unsigned char *initial_model ;
	learning_info->sp_nfold = 0 ;

	int size1 = learn_predictor(xy,learning_info->internal_method.c_str(),learning_info,&initial_model) ;
	if (size1 == -1) {
		fprintf(stderr,"Learning of matched predictor failed\n") ;
		return -1 ;
	}
	
	// Add predictions to matrix
	if (((xy->x) = (double *) realloc(xy->x,(xy->nrows)*(xy->nftrs + 1)*sizeof(double))) == NULL) {
		fprintf(stderr,"Reallocation Failed\n") ;
		return -1 ;
	}

	for (int i=0; i<(xy->nrows); i++) {
		pair<int,int> entry(xy->idnums[i],xy->dates[i]) ;
		if (preds_hash.find(entry) == preds_hash.end()) {
			fprintf(stderr,"Cannot find prediction for (%d,%d)\n",xy->idnums[i],xy->dates[i]) ;
			return -1 ;
		}

		(xy->x)[(xy->nrows)*(xy->nftrs) + i] = preds_hash[entry] ;
	}

	(xy->nftrs) ++ ;

	// Learn secondary model on enlarged-matix, matched on second-field (age, matching-w = 0.01) ;
	fprintf(stderr,"Learning on un-matched data\n") ;
	
	unsigned char *seconday_model ;
	learning_info->matching_col[0] = learning_info->field_cols["Age"] ;
	learning_info->matching_res[0] = 1.0 ;
	learning_info->matching_w = 0.01 ;
	learning_info->sp_nfold = learning_info->nfold ;

	int size2 = learn_predictor_and_score_probs(xy,learning_info->internal_method.c_str(),learning_info,&seconday_model) ;
	if (size2 == -1) {
		fprintf(stderr,"Learning of matched predictor failed\n") ;
		return -1 ;
	}

	// Combine
	(*model) = (unsigned char *) malloc(size1 + size2) ;
	if ((*model) == NULL) {
		fprintf(stderr,"Allocation of combined model failed\n") ;
		return -1 ;
	}

	memcpy(*model,initial_model,size1) ;
	memcpy((*model)+size1,seconday_model,size2) ;

	free(initial_model) ;
	free(seconday_model) ;
	return (size1+size2) ;
}

int double_matched_predict(double *x, double *preds, int nrows, int ncols, generalized_predictor_info_t& pred_info, unsigned char *model) {	
	
	generalized_predictor_info_t temp_pred_info ;
	temp_pred_info.method = pred_info.internal_method ;
	temp_pred_info.nthreads = pred_info.nthreads ;

	int size1 = predict(x,nrows,ncols,temp_pred_info,model,preds) ;
	if (size1 == -1)
		return -1 ;

	// Add predictions to matrix
	double *nx = (double *) malloc(nrows*(ncols+1)*sizeof(double)) ;
	if (nx == NULL) {
		fprintf(stderr,"Reallocation Failed\n") ;
		return -1 ;
	}
	
	memcpy(nx,x,nrows*ncols*sizeof(double)) ;
	for (int i=0; i<nrows; i++)
		nx[nrows*ncols + i] = preds[i] ;
	ncols ++ ;

	int size2= predict(nx,nrows,ncols,temp_pred_info,model+size1,preds) ;
	if (size2 == -1)
		return -1 ;

	free(nx) ;
	return (size1+size2) ;

}