// Functions for combining predictions of RandomForest and GBM
#define _CRT_SECURE_NO_WARNINGS

#include "localCommonLib.h"


// Combine predictions using gbm
int gbm_combine_predictions(double *x, int ncols, int nrows, int *ids, int *dates, int *flags, double *y, char *fname) {

	// Open file
	FILE *fp = safe_fopen(fname, "w", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for writing\n",fname) ;
		return -1  ;
	}

	// Normalize
	double median ;
	assert(get_median(x,nrows,&median)!=-1) ;
	fprintf(fp,"RF median %f\n",median) ;

	assert(get_median(x+nrows,nrows,&median)!=-1) ;
	fprintf(fp,"GBM median %f\n",median) ;

	// Prepare
	// GBM
    gbm_parameters final_gbm_params ;
	set_gbm_parameters ("Minimal",&final_gbm_params) ;

	// Weights
	double *w = (double *) malloc(nrows*sizeof(double)) ;
	if (w==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for (int irow=0; irow<nrows; irow++)
		w[irow] = 1.0 ;

	// Filter
	int new_nrows ;
	double *lx,*ly,*lw ;
	int *lids,*ldates ;

	if((new_nrows = prepare_learning_set(x,y,w,ids,dates,flags,&lx,&ly,&lw,&lids,&ldates,ncols,nrows)) == -1) {
		fprintf(stderr,"Cnould not prepare learning set\n") ;
		return -1 ;
	}

	// Get Combination model
	if (learn_gbm_predictor(lx,ly,lw,new_nrows,ncols,fp,&final_gbm_params)==-1) {
		fprintf(stderr,"learn_gbm_predictor failed\n") ;
		return -1 ;
	}

	fclose(fp) ;

	return 0 ;
}

int gbm_combine_predictions(double *x, int ncols, int nrows, int *ids, int *dates, int *flags, double *y, double *preds, char *fname) {

	if (gbm_combine_predictions(x,ncols,nrows,ids,dates,flags,y,fname) != 0)
		return -1 ;

	// THIS IS NOT OPTIMAL - PREDICTION ON LEARNING SET !
	if (gbm_predict(x,preds,nrows,ncols,fname) != 0) {
		fprintf(stderr,"GBM Prediction failed\n") ;
		return -1 ;
	}

	return 0 ;
}

// Cleanining of combination-params
void clear_combination_params (combination_params *comb_params) {

	free(comb_params->in_score1); 
	free(comb_params->in_score2) ;
	free(comb_params->out_score1); 
	free(comb_params->out_score2) ;

	return ;
}

// combine de-novo with recording
int write_combination_params(char *fname, combination_params *comb_params) {

	FILE *fp = NULL ;
	if (fname != NULL) {
		fp = safe_fopen(fname, "w", false) ;
		if (fp == NULL) {
			fprintf(stderr,"Cannot open %s for writing\n",fname) ;
			return -1 ;
		}
	}

	fprintf(fp,"Bound = %f\n",comb_params->bound) ;
	fprintf(fp,"BoundScore = %f\n",comb_params->bound_score) ;
	fprintf(fp,"N1 = %d\n",comb_params->n1) ;
	for (int i=0; i<comb_params->n1; i++)
		fprintf(fp,"Score1 %f %f\n",comb_params->in_score1[i],comb_params->out_score1[i]) ;
	fprintf(fp,"N2 = %d\n",comb_params->n2) ;
	for (int i=0; i<comb_params->n2; i++)
		fprintf(fp,"Score2 %f %f\n",comb_params->in_score2[i],comb_params->out_score2[i]) ;	
	
	fclose(fp) ;

	return 0 ;
}

// calculate combination parameters
int get_combination_params(double *in_preds1, double *in_preds2, int nrows, double bound_p, combination_params *comb_params) {

	vector<pair<int, double> > in1 ;
	for (int i=0; i<nrows; i++) {
		pair<int,double> in_pair ;
		in_pair.first = i ;
		in_pair.second = in_preds1[i] ;
		in1.push_back(in_pair) ;
	}

	sort(in1.begin(),in1.end(),compare_pairs()) ;

	vector<pair<int, double> > in2 ;
	for (int i=0; i<nrows; i++) {
		pair<int,double> in_pair ;
		in_pair.first = i ;
		in_pair.second = in_preds2[i] ;
		in2.push_back(in_pair) ;
	}

	sort(in2.begin(),in2.end(),compare_pairs()) ;

	vector<int> pos1(nrows) ;
	vector<int> pos2(nrows) ;

	for (int i=0; i<nrows; i++) {
		pos1[in1[i].first] = i ;
		pos2[in2[i].first] = i ;
	}

	double rf_bound ;
	vector<pair<double,double> > rf_dic ;
	vector<pair<double,double> > gbm_dic ;

	// Top 'bound' ordered by RF (in1)
	int cnt ;
	int bound_index =(int) (nrows * bound_p) ;

	for (int i=0; i<bound_index; i++) {
		if (i == 0 || in1[i].second != in1[i-1].second) {
			cnt = i ;
			pair<double,double> rf_pair(in1[i].second,(100.0 * (nrows-cnt))/nrows) ;
			rf_dic.push_back(rf_pair) ;
			rf_bound = in1[i].second ;
		}
	}

	// The rest - ordered by GBM (in2)
	double prev_score ;
	cnt = bound_index ;
	int first = 1 ;
	int nequale = 0 ;

	for (int i=0; i<nrows; i++) {
		if (pos1[in2[i].first] >= bound_index) {
			if (first == 1 || in2[i].second != prev_score) {
				first = 0 ;
				
				cnt += nequale ;
				nequale = 0 ;
				pair<double,double> gbm_pair(in2[i].second,(100.0 * (nrows-cnt))/nrows) ;
				gbm_dic.push_back(gbm_pair) ;
			}

			nequale++ ;
			prev_score = in2[i].second ;
		}
	}  

	// Set Values
	comb_params->bound = rf_bound ;
	comb_params->bound_score = 100*(1-bound_p) ;
	comb_params->n1 = (int) rf_dic.size() ;
	comb_params->n2 = (int) gbm_dic.size() ;

	comb_params->in_score1 = (double *) malloc((comb_params->n1)*sizeof(double)) ;
	comb_params->out_score1 =(double *) malloc((comb_params->n1)*sizeof(double)) ;
	comb_params->in_score2 = (double *) malloc((comb_params->n2)*sizeof(double)) ;
	comb_params->out_score2 =(double *) malloc((comb_params->n2)*sizeof(double)) ;
	if ((comb_params->in_score1)==NULL || (comb_params->in_score2)==NULL || (comb_params->out_score1)==NULL || (comb_params->out_score2)==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1;
	}

	for (int i=0; i<(comb_params->n1); i++) {
		(comb_params->in_score1)[i] = rf_dic[i].first ;
		(comb_params->out_score1)[i] = rf_dic[i].second ;
	}

	for (int i=0; i<(comb_params->n2); i++) {
		(comb_params->in_score2)[i] = gbm_dic[i].first ;
		(comb_params->out_score2)[i] = gbm_dic[i].second ;
	}

	return 0 ;
}

// Read combination params from file 
int read_combination_params(char *fname, combination_params *comb_params) {

	FILE *fp = safe_fopen(fname, "r", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",fname) ;
		return -1 ;
	}

	int ival ;
	double rval ;
	if (fscanf(fp,"Bound = %lf\n",&rval) != 1) {
		fprintf(stderr,"Cannot read Bound from file\n") ;
		return -1 ;
	}
	comb_params->bound = rval ;

	if (fscanf(fp,"BoundScore = %lf\n",&rval) != 1) {
		fprintf(stderr,"Cannot read BoundScore from file\n") ;
		return -1 ;
	}
	comb_params->bound_score = rval ;

	if (fscanf(fp,"N1 = %d\n",&ival) != 1) {
		fprintf(stderr,"Problems reading N1\n") ;
		return -1 ;
	}
	comb_params->n1 = ival ;

	comb_params->in_score1 = (double *) malloc((comb_params->n1)*sizeof(double)) ;
	comb_params->out_score1 = (double *) malloc((comb_params->n1)*sizeof(double)) ;
	if (comb_params->in_score1 == NULL && comb_params->out_score1 == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	double val1,val2 ;
	for (int i=0; i<(comb_params->n1); i++) {
		if (fscanf(fp,"Score1 %lf %lf\n",&val1,&val2) != 2) {
			fprintf(stderr,"Problem reading Score1 at %d\n",i) ;
			return -1 ;
		}
		(comb_params->in_score1)[i] = val1 ;
		(comb_params->out_score1)[i] = val2 ;
	}

	if (fscanf(fp,"N2 = %d\n",&ival) != 1) {
		fprintf(stderr,"Problems reading N2\n") ;
		return -1 ;
	}
	comb_params->n2 = ival ;

	comb_params->in_score2 = (double *) malloc((comb_params->n2)*sizeof(double)) ;
	comb_params->out_score2 = (double *) malloc((comb_params->n2)*sizeof(double)) ;
	if (comb_params->in_score2 == NULL && comb_params->out_score2 == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for (int i=0; i<(comb_params->n2); i++) {
		if (fscanf(fp,"Score2%lf %lf\n",&val1,&val2) != 2) {
			fprintf(stderr,"Problem reading Score2 at %d\n",i) ;
			return -1 ;
		}
		(comb_params->in_score2)[i] = val1 ;
		(comb_params->out_score2)[i] = val2 ;
	}

	fclose(fp) ;

	return 0 ;
}

// combine predictions
void combine_predictions(double *in_preds1, double *in_preds2, double *out_preds, int nrows, combination_params *comb_params) {

	double score ;
	for (int i=0; i<nrows; i++) {
		if (in_preds1[i] >= comb_params->bound) {
			// Get Score from Score1 (RF)
			int idx = 0 ;
			while (idx < comb_params->n1 && in_preds1[i] < comb_params->in_score1[idx])
				idx ++ ;

			if (idx == 0)
				score = 100.0 ; 
			else if (idx == comb_params->n1)
				score = comb_params->bound_score ;
			else
				score = ((in_preds1[i] - comb_params->in_score1[idx])*comb_params->out_score1[idx-1] + (comb_params->in_score1[idx-1]-in_preds1[i])*comb_params->out_score1[idx])/
						 (comb_params->in_score1[idx-1]-comb_params->in_score1[idx]) ;
		} else {
			// Get Score from Score2 (GBM)
			int idx = 0 ;
			while (idx < comb_params->n2 && in_preds2[i] < comb_params->in_score2[idx])
				idx ++ ;

			if (idx == 0)
				score =comb_params-> bound_score ; 
			else if (idx == comb_params->n2)
				score = 0 ;
			else
				score = ((in_preds2[i] - comb_params->in_score2[idx])*comb_params->out_score2[idx-1] + (comb_params->in_score2[idx-1]-in_preds2[i])*comb_params->out_score2[idx])/
						 (comb_params->in_score2[idx-1]-comb_params->in_score2[idx]) ;
		}

		out_preds[i] = score ;
	}
	return ;
}

// combine from file
int combine_predictions(double *in_preds1, double *in_preds2, double *out_preds, int nrows, char *fname) {

	combination_params comb_params ;

	if (read_combination_params(fname,&comb_params)==-1) {
		fprintf(stderr,"Cannot read combination params from %s\n",fname) ;
		return -1 ;
	}

	combine_predictions(in_preds1,in_preds2,out_preds,nrows,&comb_params) ;

	// Clean
	clear_combination_params(&comb_params) ;

	return 0 ;
}

// combine from data
int combine_predictions(double *in_preds1, double *in_preds2, double *out_preds, int nrows, double bound_p, char *fname) {

	combination_params comb_params ;
	if (get_combination_params(in_preds1,in_preds2,nrows,bound_p,&comb_params)==-1) {
		fprintf(stderr,"Cannot get combination params from data\n") ;
		return -1 ;
	}

	combine_predictions(in_preds1,in_preds2,out_preds,nrows,&comb_params) ;

	if (fname != NULL) {
		if (write_combination_params(fname,&comb_params)==-1) {
			fprintf(stderr,"Cannot write combination params to %s\n",fname) ;
			return -1 ;
		}
	}

	// Clean
	clear_combination_params(&comb_params) ;

	return 0 ;
}

// combine from data with filtering
int combine_predictions(double *in_preds1, double *in_preds2, int *ids, int *dates, int *flags, double *labels, double *out_preds, int nrows, double bound_p, char *fname) {

	// filter sets of predictions
	int *indices ;
	int temp_nrows;; 
	if ((temp_nrows = get_learning_indices(ids,dates,flags,labels,nrows,&indices)) == -1) {
		fprintf(stderr,"Cannot get learning set indices\n") ;
		return -1 ;
	}

	double *temp_preds1 = (double *) malloc(temp_nrows*sizeof(double)) ;
	double *temp_preds2 = (double *) malloc(temp_nrows*sizeof(double)) ;
	if (temp_preds1==NULL || temp_preds2==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for (int i=0; i<temp_nrows; i++) {
		temp_preds1[i] = in_preds1[indices[i]] ;
		temp_preds2[i] = in_preds2[indices[i]] ;
	}

	combination_params comb_params ;
	if (get_combination_params(temp_preds1,temp_preds2,temp_nrows,bound_p,&comb_params)==-1) {
		fprintf(stderr,"Cannot get combination params from data\n") ;
		return -1 ;
	}

	combine_predictions(in_preds1,in_preds2,out_preds,nrows,&comb_params) ;

	if (fname != NULL) {
		if (write_combination_params(fname,&comb_params)==-1) {
			fprintf(stderr,"Cannot write combination params to %s\n",fname) ;
			return -1 ;
		}
	}

	// Clean
	clear_combination_params(&comb_params) ;
	free(indices) ;
	free(temp_preds1) ; free(temp_preds2) ;

	return 0 ;
}

int combine_predictions(double *in_preds1, double *in_preds2, int nrows, double bound_p, char *fname) {

	combination_params comb_params ;
	if (get_combination_params(in_preds1,in_preds2,nrows,bound_p,&comb_params)==-1) {
		fprintf(stderr,"Cannot read combination params from %s\n",fname) ;
		return -1 ;
	}

	if (write_combination_params(fname,&comb_params)==-1) {
		fprintf(stderr,"Cannot write combination params to %s\n",fname) ;
		return -1 ;
	}

	// Clean
	clear_combination_params(&comb_params) ;

	return 0 ;
}

// (De)Serialization

size_t get_combination_params_size(combination_params *comb_params) {

	size_t size = 2 * sizeof(int) ; // N1, N2
	size += 2 * sizeof(double) ; // Bound, BoundScore
	size += 2 * comb_params->n1 * sizeof(double) ; // InScore1, OutScore
	size += 2 * comb_params->n2 * sizeof(double) ; // InScore2, OutScore2

	return size ;
}

int serialize(combination_params *comb_params, unsigned char *comb_data) {

	size_t idx = 0 ;
	memcpy(comb_data+idx,&(comb_params->bound),sizeof(double)) ; idx += sizeof(double) ;
	memcpy(comb_data+idx,&(comb_params->bound_score),sizeof(double)) ; idx += sizeof(double) ;
	memcpy(comb_data+idx,&(comb_params->n1),sizeof(int)) ; idx += sizeof(int) ;
	memcpy(comb_data+idx,&(comb_params->n2),sizeof(int)) ; idx += sizeof(int) ;

	memcpy(comb_data+idx,comb_params->in_score1,comb_params->n1*sizeof(double)) ; idx += comb_params->n1*sizeof(double) ;
	memcpy(comb_data+idx,comb_params->out_score1,comb_params->n1*sizeof(double)) ; idx += comb_params->n1*sizeof(double) ;
	memcpy(comb_data+idx,comb_params->in_score2,comb_params->n2*sizeof(double)) ; idx += comb_params->n2*sizeof(double) ;
	memcpy(comb_data+idx,comb_params->out_score2,comb_params->n2*sizeof(double)) ; idx += comb_params->n2*sizeof(double) ;

	return (int) idx ;
}

int deserialize(unsigned char *comb_data, combination_params *comb_params) {

	size_t idx = 0 ;
	memcpy(&(comb_params->bound),comb_data+idx,sizeof(double)) ; idx += sizeof(double) ;
	memcpy(&(comb_params->bound_score),comb_data+idx,sizeof(double)) ; idx += sizeof(double) ;
	memcpy(&(comb_params->n1),comb_data+idx,sizeof(int)) ; idx += sizeof(int) ;
	memcpy(&(comb_params->n2),comb_data+idx,sizeof(int)) ; idx += sizeof(int) ;
	
	comb_params->in_score1 = (double *) malloc(comb_params->n1 * sizeof(double)) ;
	comb_params->out_score1 = (double *) malloc(comb_params->n1 * sizeof(double)) ;
	comb_params->in_score2 = (double *) malloc(comb_params->n2 * sizeof(double)) ;
	comb_params->out_score2 = (double *) malloc(comb_params->n2 * sizeof(double)) ;
	if (comb_params->in_score1==NULL || comb_params->out_score1==NULL || comb_params->in_score2==NULL || comb_params->out_score2==NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}

	memcpy(comb_params->in_score1,comb_data+idx,comb_params->n1*sizeof(double)) ; idx += comb_params->n1*sizeof(double) ;
	memcpy(comb_params->out_score1,comb_data+idx,comb_params->n1*sizeof(double)) ; idx += comb_params->n1*sizeof(double) ;
	memcpy(comb_params->in_score2,comb_data+idx,comb_params->n2*sizeof(double)) ; idx += comb_params->n2*sizeof(double) ;
	memcpy(comb_params->out_score2,comb_data+idx,comb_params->n2*sizeof(double)) ; idx += comb_params->n2*sizeof(double) ;

	return (int) idx ;
}