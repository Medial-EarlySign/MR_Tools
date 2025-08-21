// RfGBM = RandomForest + Gradient Boosting Method
#define _CRT_SECURE_NO_WARNINGS

#include "localCommonLib.h"

/*****************************************************/
/*                 Function							 */
/*****************************************************/

size_t get_rfgbm_size(rfgbm_info_t *rfgbm_info) {
	return get_rf_size(&(rfgbm_info->rf)) + get_gbm_info_size(&(rfgbm_info->gbm)) + get_combination_params_size(&(rfgbm_info->comb)) ;
}

int serialize(rfgbm_info_t *rfgbm_info, unsigned char *rfgbm_data) {
	int idx = 0 ;
	idx += rf_serialize(&(rfgbm_info->rf),rfgbm_data+idx) ;
	idx += gbm_serialize(&(rfgbm_info->gbm),rfgbm_data+idx) ;
	idx += serialize(&(rfgbm_info->comb),rfgbm_data+idx) ;

	return idx ;
}

int deserialize(unsigned char *rfgbm_data, rfgbm_info_t *rfgbm_info) {
	int idx = 0 ;
	idx += rf_deserialize(rfgbm_data+idx,&(rfgbm_info->rf)) ;
	idx += gbm_deserialize(rfgbm_data+idx,&(rfgbm_info->gbm)) ;
	idx += deserialize(rfgbm_data+idx,&(rfgbm_info->comb)) ;

	return idx ;
}

void clear_rfgbm_struct(rfgbm_info_t *rfgbm_info) {

	clear_gbm_info(&(rfgbm_info->gbm)) ;
	clear_random_forest(&(rfgbm_info->rf)) ;
	clear_combination_params(&(rfgbm_info->comb)) ;

	return ;
}

int learn_combination_params(xy_data *xy, rfgbm_learning_params *learning_params, combination_params *comb_params, vector<int>& matching_col, vector<double>& matching_res,  double matching_w) {

	// Do CV (Required for combinations methods)
	int npatients = 1 ;
	for (int i=1; i<xy->nrows; i++) {
		if ((xy->idnums)[i] != (xy->idnums)[i-1])
			npatients++ ;
	}
	fprintf(stderr,"Npatients = %d\n",npatients) ;

	// Shuffle
	fprintf(stderr,"Random seed = %d\n",learning_params->seed) ;
	globalRNG::srand(learning_params->seed) ;
	int *order = randomize(npatients) ;
	assert(order != NULL) ;

	double *rf_preds = (double *) malloc((xy->nrows)*sizeof(double)) ;
	double *gbm_preds = (double *) malloc((xy->nrows)*sizeof(double)) ;

	double *means_for_completion = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	double *sdvs_for_completion = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	if (means_for_completion == NULL || sdvs_for_completion == NULL || rf_preds == NULL || gbm_preds == NULL)  {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
	}

	int size = npatients/learning_params->nfold ;

	int npreds = 0 ;
	for (int ifold=0; ifold<learning_params->nfold; ifold++) {

		int test_start = ifold * size ;
		int test_end = (ifold + 1)*size - 1 ;
		if (ifold == learning_params->nfold - 1)
			test_end = npatients - 1 ;
	
		// Split
		xy_data xy1,xy2 ;
		init_xy(&xy1) ;
		init_xy(&xy2) ;

		// Splitting
		if (get_split_data(xy,npatients,&xy1,&xy2,order,test_start,test_end) == -1) {
				fprintf(stderr,"Splitting to Learning+Test sets failed\n") ;
				return -1 ;
		}

		fprintf(stderr,"Fold: %d   Training size: %d    Testing size: %d\n", ifold, xy1.nrows, xy2.nrows);

		// Filtering : According to flags and to 'only_last_in_learning
		xy_data fxy1 ;
		init_xy(&fxy1) ;

		if(filter_learning_set(&xy1,&fxy1,2) == -1) {
			fprintf(stderr,"Filtering of training set failed\n") ;
			return -1 ;
		}

		xy_data nxy ;
		init_xy(&nxy) ;

		if (adjust_learning_set(&fxy1,matching_col,matching_res,matching_w,&nxy) == -1)
			return -1 ;

		clock_t start = clock() ;

		if (get_rf_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,nxy.nftrs,rf_preds + npreds,learning_params->rf_ntrees) ==-1) {
			fprintf(stderr,"RandomForest Learn+Predict Failed\n") ;
			return -1 ;
		}
			
		if (get_gbm_predictions(nxy.x,nxy.y,nxy.w,nxy.nrows,xy2.x,xy2.nrows,nxy.nftrs,gbm_preds + npreds,learning_params->gbm_params)==-1) {
			fprintf(stderr,"GBM Learn+Predict Failed\n") ;
			return -1 ;
		}

		fprintf(stderr,"Get Prediction took %f seconds\n",(0.0 + clock() - start)/CLOCKS_PER_SEC) ;
		npreds += xy2.nrows ;

		clear_xy(&xy1) ;
		clear_xy(&xy2) ;
		clear_xy(&fxy1) ;
		clear_xy(&nxy) ;

		fprintf(stderr,"Done\n") ;
	}
	
	// Combination
	if (get_combination_params(rf_preds,gbm_preds,npreds,learning_params->combination_bound,comb_params) == -1) {
		fprintf(stderr,"Getting Combination Params From Predictions Failed\n") ;
		return -1 ;
	}
	return 0 ;
}

int learn_rfgbm_predictor(xy_data *xy, rfgbm_learning_params *learning_params, rfgbm_info_t *rfgbm_info, vector<int>& matching_col, vector<double>& matching_res, double matching_w) {

	// Combination
	if (learn_combination_params(xy,learning_params,&(rfgbm_info->comb),matching_col,matching_res,matching_w) == -1) {
		fprintf(stderr,"Getting Combination Params Failed\n") ;
		return -1 ;
	}

	xy_data nxy,fxy ;
	init_xy(&nxy) ;
	init_xy(&fxy) ;

	// Prepare Learning Set
	if (filter_learning_set(xy,&fxy,2) == -1) {
		fprintf(stderr,"Learning Set Filtering Failed\n") ;
		return -1 ;
	}

	if (adjust_learning_set(&fxy,matching_col,matching_res,matching_w,&nxy) == -1)
		return -1 ;

	// Random Forest on all data
	if (learn_rf_predictor(nxy.x,nxy.y,nxy.nrows,nxy.nftrs,learning_params->rf_file_name,learning_params->rf_ntrees ) == -1) {
		fprintf(stderr,"Learning Random Forest Failed\n") ;
		return -1 ;
	}

	if (read_forest(learning_params->rf_file_name, &(rfgbm_info->rf)) == -1) {
		fprintf(stderr,"Reading Random Forest From File Failed\n") ;
		return -1 ;
	}

	// GBM on all data
	if (get_gbm_predictor(nxy.x,nxy.y,nxy.w,nxy.nrows,nxy.nftrs,learning_params->gbm_params->shrinkage, learning_params->gbm_params->bag_p, learning_params->gbm_params->take_all_pos, 
					   	  learning_params->gbm_params->ntrees, learning_params->gbm_params->depth, learning_params->gbm_params->min_obs_in_node,&(rfgbm_info->gbm))==-1) {
		fprintf(stderr,"GBM learning failed\n") ;
		return -1 ;
	}

	clear_xy(&fxy) ;
	clear_xy(&nxy) ;
	return(0);
}

int learn_rfgbm_predictor(xy_data *xy, rfgbm_learning_params *learning_params, rfgbm_info_t *rfgbm_info) {
	
	vector<int> cols ;
	vector<double> res ;
	cols.clear() ;

	return learn_rfgbm_predictor(xy,learning_params,rfgbm_info,cols,res,MATCHING_W) ;
}

int learn_rfgbm_predictor(xy_data *xy, rfgbm_learning_params *learning_params, unsigned char **rfgbm_data, vector<int>& matching_col, vector<double>& matching_res, double matching_w) {
	
	// Learn
	rfgbm_info_t rfgbm_info ;
	if (learn_rfgbm_predictor(xy,learning_params,&rfgbm_info,matching_col,matching_res,matching_w)==-1) 
		return -1 ;

	// Serialize
	size_t size = get_rfgbm_size(&rfgbm_info) ;
	if (((*rfgbm_data) = (unsigned char *) malloc (size))==NULL) {
		fprintf(stderr,"Allocation of model failed\n") ;
		return -1 ;
	}

	if (serialize(&rfgbm_info,*rfgbm_data)==-1) {
		fprintf(stderr,"Serialization of rfgbm failed\n") ;
		return -1 ;
	}

	return (int) size ;
}

int learn_rfgbm_predictor(xy_data *xy, rfgbm_learning_params *learning_params, unsigned char **rfgbm_data) {

	vector<int> cols ;
	vector<double> res ;
	cols.clear() ;

	return learn_rfgbm_predictor(xy,learning_params,rfgbm_data,cols,res,MATCHING_W) ;
}

int predict_rfgbm(double *x,int nrows, int ncols, rfgbm_info_t *rfgbm_info, double *preds) {

	double *rf_preds = (double *) malloc(nrows*sizeof(double)) ;
	double *gbm_preds = (double *) malloc(nrows*sizeof(double)) ;

	if (rf_preds==NULL || gbm_preds==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	fprintf(stderr,"RF predictions.\n") ;
	if(rf_predict(x,rf_preds,nrows,ncols,&(rfgbm_info->rf)) == -1) {
		fprintf(stderr,"RandomForest prediction failed\n") ;
		return -1 ;
	}

	fprintf(stderr,"GBM predictions.\n") ;
	if (gbm_predict(x,nrows,ncols,rfgbm_info->gbm.ntrees,&(rfgbm_info->gbm),gbm_preds)==-1) {
		 fprintf(stderr,"GBM prediction failed\n") ;
		 return -1 ;
	 }

	combine_predictions(rf_preds,gbm_preds,preds,nrows,&(rfgbm_info->comb)) ;

	free(rf_preds) ;
	free(gbm_preds) ;
	return 0 ;
}

int rfgbm_predict(double *x, double *preds, int nrows, int ncols, unsigned char *model) {

	int size ;
	// DeSerializae 
	rfgbm_info_t rfgbm_info ;
	if ((size = deserialize(model,&rfgbm_info))==-1) {
		fprintf(stderr,"DeSerialization failed\n") ;
		return -1 ;
	}

	// Predict
	if (predict_rfgbm(x,nrows,ncols,&rfgbm_info,preds)==-1) {
		fprintf(stderr,"rfgbm prediction failed\n") ;
		return -1 ;
	}

	// Clearing
	clear_rfgbm_struct(&rfgbm_info) ;

	return size ;
}

int get_rfgbm_predictions(xy_data *xy1, rfgbm_learning_params *rfgbm_params, xy_data *xy2 ,double *preds, vector<int>& matching_col, vector<double>& matching_res, double matching_w) {

	// Learn
	rfgbm_info_t rfgbm_info ;
	if (learn_rfgbm_predictor(xy1,rfgbm_params,&rfgbm_info,matching_col,matching_res,matching_w)==-1)  {
		fprintf(stderr,"Learning RfGBM Predictor Failed\n") ;
		return -1 ;
	}

	// Predict
	if (predict_rfgbm(xy2->x,xy2->nrows,xy2->nftrs,&rfgbm_info,preds)==-1) {
		fprintf(stderr,"Prediction with RfGBM Failed\n") ;
		return -1 ;
	}

	// Clearing
	clear_rfgbm_struct(&rfgbm_info) ;

	return 0 ;
}

int get_rfgbm_predictions(xy_data *xy1, rfgbm_learning_params *rfgbm_params, xy_data *xy2 ,double *preds) {

	vector<int> col ;
	vector<double> res ;
	col.clear() ;

	return get_rfgbm_predictions(xy1,rfgbm_params,xy2,preds,col,res,MATCHING_W) ;
}



