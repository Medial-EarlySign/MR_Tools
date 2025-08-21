// Function for separation of variables.
#define _CRT_SECURE_NO_WARNINGS

#include "localCommonLib.h"
#include "common_header.h"

// Functions //

int read_scores(char *scores_file, map<string,vector<score> >& scores) {

	FILE *fp = safe_fopen(scores_file, "r", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",scores_file) ;
		return -1 ;
	}

	char dummy[MAX_STRING_LEN] ;
	if (fgets(dummy,MAX_STRING_LEN,fp) == NULL || feof(fp)) {
		fprintf(stderr,"Cannot read header of %s\n",scores_file);
		return -1 ;
	}

	char id[MAX_STRING_LEN] ;
	int date,bin1,bin2 ;
	double value ;
	int nscores=0 ;

	while (!feof(fp)) {
		int rc = fscanf(fp,"%s %d %lf %d %d\n",id,&date,&value,&bin1,&bin2) ;
		if (rc==EOF)
			break ;
		else if (rc != 5) {
			fprintf(stderr,"Cannot parse %s (rc = %d, first = %s)\n",scores_file,rc,id) ;
			fclose(fp) ;
			return -1 ;
		} else {
			score temp_score ;
			temp_score.days = get_day(date) ;
			temp_score.value = (int) (value/SCORE_RES) ;
			temp_score.date = date ;
			scores[id].push_back(temp_score) ;
			nscores ++ ;
		}
	}

	size_t nids = scores.size() ;
	fprintf(stderr,"Read %d scores for %zd ids from %s\n",nscores,nids,scores_file) ;

	fclose(fp) ;
	return 0 ;
}


int read_registry(char *reg_file,  map<string,vector<cancer> >& registry) {

	FILE *fp = safe_fopen(reg_file, "r", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",reg_file) ;
		return -1 ;
	}

	char id[MAX_STRING_LEN] ;
	int date,index ;
	int ncases = 0 ;

	while (!feof(fp)) {
		int rc = fscanf(fp,"%s %d %d\n",id,&date,&index) ;
		if (rc==EOF)
			break ;
		else if (rc != 3) {
			fprintf(stderr,"Cannot parse %s (Format is: ID DATE INDEX(1=Relevant/ 2=Irrelevant)\n",reg_file) ;
			fclose(fp) ;
			return -1 ;
		} else {
			cancer temp_cancer ;
			temp_cancer.days = get_day(date) ;
			temp_cancer.index = index ;
			registry[id].push_back(temp_cancer) ;
			ncases ++ ;
		}
	}

	size_t nids = registry.size() ;
	fprintf(stderr,"Read %d cancer cases for %zd ids from %s\n",ncases,nids,reg_file) ;

	fclose(fp) ;
	return 0 ;
}

void hash_to_vector(map<int, double>& probs_hash, vector<int>& ages, vector<double>& probs) {
	
	size_t nages = ages.size() ;
	fprintf(stderr,"Read %zd age-dependent probabilities\n",nages) ;
	assert(nages>0) ;

	// Complete missing ...
	sort(ages.begin(),ages.end()) ;
	probs.resize(MAX_AGE+1) ;

	for (int iage=0; iage<=ages[0]; iage++)
		probs[iage] = probs_hash[ages[0]] ;

	for (int i=0; i<ages.size(); i++)
		probs[ages[i]] = probs_hash[ages[i]];

	for (int iage=ages.back(); iage<=MAX_AGE; iage++)
		probs[iage] = probs_hash[ages.back()] ;

	for (int i=0; i<ages.size()-1; i++) {
		for (int iage=ages[i] + 1; iage < ages[i+1]; iage++) {
			probs[iage] = (probs_hash[ages[i]]*(ages[i+1]-iage) + probs_hash[ages[i+1]]*(iage-ages[i]))/(ages[i+1]-ages[i]) ;
		}
	}

	return ;
}

int read_age_dep(FILE *fp, vector<double>& probs) {

	unsigned int age ;

	map<int, double> probs_hash ;
	vector<int> ages ;

	double prob ;
	while (!feof(fp)) {
		int rc = fscanf(fp,"%d %lf\n",&age,&prob) ;
		if (rc==EOF)
			break ;
		else if (rc != 2) {
			fprintf(stderr,"Cannot parse age dependent incidence file\n") ;
			fclose(fp) ;
			return -1 ;
		} else {
			if (age < 0 || age > MAX_AGE) {
				fprintf(stderr,"Illegal age %d at age dependent incidence file\n",age) ;
				return -1 ;
			}

			probs_hash[age] = prob ;
			ages.push_back(age) ;
		}
	}


	hash_to_vector(probs_hash,ages,probs) ;

	return 0 ;
}

int read_demographics(char *dem_file, map<string,demographics>& dem_data) {

	FILE *fp = safe_fopen(dem_file, "r", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",dem_file) ;
		return -1 ;
	}

	char id[MAX_STRING_LEN] ;
	char gender ;
	int byear ;

	while (!feof(fp)) {
		int rc = fscanf(fp,"%s %d %c\n",&id,&byear,&gender) ;
		if (rc==EOF)
			break ;
		else if (rc != 3) {
			fprintf(stderr,"Cannot parse %s\n",dem_file) ;
			fclose(fp) ;
			return -1 ;
		} else {
			demographics temp_dem ;
			temp_dem.byear = byear ;
			temp_dem.gender = gender ;
			dem_data[id] = temp_dem ;
		}
	}

	size_t nids = dem_data.size() ;
	fprintf(stderr,"Read demographics for %zd individuals\n",nids) ;

	fclose(fp) ;
	return 0 ;
}

void smooth_probabilities(map<int,double>& probs) {

	map<int,double> smooth_probs ;

	int min_score,max_score  ;
	int first = 1;

	for (map<int,double>::iterator it=probs.begin(); it!=probs.end(); it++) {
		if (first) {
			min_score = it->first ;
			max_score = it->first ;
			first = 0 ;
		} else if (it->first < min_score)
			min_score = it->first ;
		else if (it->first > max_score)
			max_score = it->first ;
	}

	for (int score = min_score-KERNEL_RANGE; score <= max_score+KERNEL_RANGE; score++) {
		double norm = 0 ;
		double sum = 0 ;
		
		for (int i=-(KERNEL_RANGE); i<=KERNEL_RANGE; i++) {
			double weight = (3.0/4.0)*(1-(i/(1.0*KERNEL_RANGE))*(i/(1.0*KERNEL_RANGE))) ;
			norm += weight ;
			if (probs.find(score + i) != probs.end())
				sum += weight * probs[score + i] ;
		}
		smooth_probs[score] = sum/norm ;
	}

	probs.clear() ;
	for (map<int,double>::iterator it=smooth_probs.begin(); it!=smooth_probs.end(); it++)
		probs[it->first] = it->second ;

}


void get_posteriors(double *preds, double *ages, int npreds, vector<double>& age_probs, score_probs_info &score_probs) {

	for (int i=0; i<npreds; i++) {
		int ipred = (int) ((preds[i]-score_probs.min)/score_probs.score_res + 0.5) ;
		int age = (int) (ages[i] + 0.5) ;

		double in_p[2] ;
		for (int type = 0 ; type < 2; type ++ ) {
			if (ipred > score_probs.max_preds[type])
				in_p[type] = (type == 0) ? LOWER_SCORE_P_BOUND : UPPER_SCORE_P_BOUND ;
			else if (ipred < score_probs.min_preds[type])
				in_p[type] = (type == 0) ? UPPER_SCORE_P_BOUND : LOWER_SCORE_P_BOUND ;
			else {
				assert(score_probs.probs[type].find(ipred) != score_probs.probs[type].end()) ;
				in_p[type] = score_probs.probs[type][ipred] ;
			}
		}
		
		preds[i] = 100 * in_p[1] * age_probs[age] / (in_p[1] * age_probs[age] + in_p[0] * (1.0 - age_probs[age])) ; 
	}
}

void get_posteriors(double *preds, double *ext_probs, int npreds, score_probs_info &score_probs) {

	for (int i=0; i<npreds; i++) {
		int ipred = (int) ((preds[i]-score_probs.min)/score_probs.score_res + 0.5) ;

		double in_p[2] ;
		for (int type = 0 ; type < 2; type ++ ) {
			if (ipred > score_probs.max_preds[type])
				in_p[type] = (type == 0) ? LOWER_SCORE_P_BOUND : UPPER_SCORE_P_BOUND ;
			else if (ipred < score_probs.min_preds[type])
				in_p[type] = (type == 0) ? UPPER_SCORE_P_BOUND : LOWER_SCORE_P_BOUND ;
			else {
				assert(score_probs.probs[type].find(ipred) != score_probs.probs[type].end()) ;
				in_p[type] = score_probs.probs[type][ipred] ;
			}
		}
		
		preds[i] = 100 * in_p[1] * ext_probs[i] / (in_p[1] * ext_probs[i] + in_p[0] * (1.0 - ext_probs[i])) ; 
	}
}

int get_score_probs(double *preds, int *dates, int *ids , int npreds, int start, int end, map<string,vector<cancer> >& registry, score_probs_info& score_probs) {

	// Get Range amd Resolution
	double min,max ;
	min = max = preds[0] ;
	for (int i=0; i<npreds; i++) {
		if (preds[i] > max)
			max = preds[i] ;
		if (preds[i] < min)
			min = preds[i] ;
	}
	
	double score_res = (max-min)/SCORE_NVALUES ;
	score_probs.min = min ;
	score_probs.score_res = score_res ;

	// Collect
	char id[MAX_STRING_LEN] ;

	for (int i=0 ; i<npreds ; i++) {
		int ipred = (int) ((preds[i]-min)/score_res + 0.5) ;
		sprintf(id,"%d",ids[i]) ;
		if (registry.find(id) == registry.end()) { // Control
			score_probs.probs[0][ipred] ++ ;
		} else { // Cancer - Look for registry in the defined time-window
			int day = get_day(dates[i]) ;
			for (unsigned int icancer=0; icancer < registry[id].size(); icancer++) {
				if (registry[id][icancer].index == 1 && registry[id][icancer].days >= day + start && registry[id][icancer].days <= day + end) {
					score_probs.probs[1][ipred] ++ ;
					break ;
				}
			}
		}
	}

	

	// Normalize and Smooth
	for (int type = 0; type < 2; type ++ ) {
		double sum = 0 ;

		for (map<int,double>::iterator mit=score_probs.probs[type].begin(); mit!=score_probs.probs[type].end(); mit++)
			sum += mit->second + 1;
		for (map<int,double>::iterator mit=score_probs.probs[type].begin(); mit!=score_probs.probs[type].end(); mit++)
			mit->second = (mit->second + 1)/sum ;

		smooth_probabilities(score_probs.probs[type]) ;

		int found = -1 ;
		for (map<int,double>::iterator mit=score_probs.probs[type].begin(); mit!=score_probs.probs[type].end(); mit++) {
			if (mit->second > UPPER_SCORE_P_BOUND) {
				if (found == -1) {
					found = 1 ;
					score_probs.min_preds[type] = score_probs.max_preds[type] = mit->first ;
				} else {
					if (mit->first > score_probs.max_preds[type])
						score_probs.max_preds[type] = mit->first ;
					if (mit->first < score_probs.min_preds[type]) 
						score_probs.min_preds[type] = mit->first ;
				}
			}
		}
		assert(found != -1) ;
	}

	return 0 ;
}

int read_score_probs(char *fname, map<int,double> *probs, int ntypes, double *def_probs, double *min_score, double *score_res, int *min_scores, int *max_scores) { 

	FILE *fp = safe_fopen(fname, "r", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",fname) ;
		return -1 ;
	}

	int type ;
	double prob ;
	int value ;

	// Read Min and Res
	assert (fscanf(fp,"min %lf\n",min_score) == 1) ;
	assert (fscanf(fp,"res %lf\n",score_res) == 1) ;
	int first[2] = {1,1} ;

	while (!feof(fp)) {
		int rc = fscanf(fp,"%d %d %lf\n",&type,&value,&prob) ;
		
		if (rc == EOF)
			return 0 ;
		if (rc != 3) {
			fprintf(stderr,"Cannot parse line in %s (rc=%d)\n",fname,rc) ;
			return -1 ;
		}

		if (type >= ntypes) {
			fprintf(stderr,"Illegal type %d in %s\n",type,fname) ;
			return -1;
		}

		if (probs[type].find(value) != probs[type].end()) {
			fprintf(stderr,"Entry %d:%d appears more than once in %s\n",type,value,fname) ;
			return -1 ;
		}
			
		probs[type][value] = prob ;
		if (first[type] == 1) {
			max_scores[type] = min_scores[type] = value ;
			first[type] = 0 ;
		} else {
			if (value > max_scores[type])
				max_scores[type] = value ;
			if (value < min_scores[type])
				min_scores[type] = value ;
		}
	}

	fclose(fp) ;
	return 0;
}



int learn_predictor_and_score_probs_ranks(xy_data *xy, string method, generalized_learner_info_t *learning_info, unsigned char **model ,int *ranks ) {


		map<pair<int,int>, int> ranks_hash ;
		for (int i=0; i<(xy->nrows); i++) {
			pair<int,int> entry(xy->idnums[i],xy->dates[i]) ;
			ranks_hash[entry] = ranks[i] ;
		}



	double *preds = (double *) malloc((xy->nrows)*sizeof(double)) ;
	double *labels = (double *) malloc((xy->nrows)*sizeof(double)) ;
	int *dates = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *ids = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *flags = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *censor = (int *) malloc((xy->nrows)*sizeof(int)) ;

	if (preds == NULL || labels == NULL || dates == NULL || ids == NULL || flags == NULL || censor == NULL) {
		fprintf(stderr,"Allocation for CV failed\n") ;
		return -1 ;
	}	

	int rank_limit;
	double *preds_temp[2];	
	for (int mm=0; mm<2; mm++)
	{
	
		if (mm==0) rank_limit=0; else rank_limit=999;
		assert(preds_temp[mm]=(double *)malloc(xy->nrows*sizeof(double)));
		if (get_predictions(xy,method,learning_info,learning_info->nfold,preds_temp[mm],dates,ids,flags,censor,labels,ranks_hash,rank_limit) == -1) {
			fprintf(stderr,"Cross Validation for P(Score) Failed\n") ;
			return -1 ;
		}
	}

	for (int ii=0; ii<xy->nrows; ii++) {
		preds[ii] = (0.5*preds_temp[0][ii]) + (0.5*preds_temp[1][ii]);
	}

	score_probs_info score_probs ;
	if (get_score_probs(preds,dates,ids,xy->nrows,learning_info->sp_start_period,learning_info->sp_end_period,learning_info->registry,score_probs) == -1) {
		fprintf(stderr,"Calculating of Score probabilities failed\n") ;
		return -1 ;
	}



	//-----------------------------------------------------------------------------------------------------------------------------------

	int size ;

	/*
	learning_info->sp_nfold = 0 ;
	int size ;
	if ((size = learn_predictor(xy,method,learning_info,model))  == -1) {
		fprintf(stderr,"Predictor learning failed for method \'%s\'\n",method.c_str()) ;
		return -1 ;
	}
	*/




			int NUM_OF_GBMS = 2;
			xy_data xy_copy;
			unsigned char *model_temp ;
			int modelSize_temp ;
			int modelSize=0;

			for (int mm=0; mm<NUM_OF_GBMS; mm++) {
					int x = copy_xy (&xy_copy , xy);
					if (mm==0) {
									int rank_limit = 0;
									int x_filter = filter_learning_set_rank_score(&xy_copy,ranks,rank_limit);
					}
					else if (mm==1) {
									int rank_limit = 200;
									int x_filter = filter_learning_set_rank_score(&xy_copy,ranks,rank_limit);
					}

					take_samples(&xy_copy,2); 
					assert((modelSize_temp = learn_predictor(&xy_copy,learning_info->internal_method.c_str(), learning_info,&model_temp))>0);


					if (mm==0) {
						(*model) = (unsigned char *) malloc(modelSize_temp) ;
						memcpy((*model),model_temp,modelSize_temp) ;
						modelSize+=modelSize_temp;

					} else {
						(*model)  =  (unsigned char *) realloc ((*model),modelSize+modelSize_temp);
						memcpy((*model)+modelSize,model_temp,modelSize_temp) ;
						modelSize+=modelSize_temp;
					}

					clear_xy(&xy_copy);
			}

			size = modelSize;

			fprintf(stderr , "size : %i\n" , size);
	//-----------------------------------------------------------------------------------------------------------------------------------


	int size2 = size + (int) get_size(&score_probs) ;

	fprintf(stderr , "size2 : %i\n" , size2);

	if (((*model) = (unsigned char *) realloc (*model,size2)) == NULL) {
		fprintf(stderr,"ReAllocation of Model Failed\n") ;
		return -1 ;
	}

	if (serialize(&score_probs,(*model)+size)==-1) {
		fprintf(stderr,"Serialization of score_probs_info failed\n") ;
		return -1 ;
	}

	gen_model generative_model ;
	get_gen_model(xy,learning_info,&generative_model) ;

	int size3 = size2 + (int) get_size(&generative_model) ;

	fprintf(stderr , "size3 : %i\n" , size3);

	if (((*model) = (unsigned char *) realloc (*model,size3)) == NULL) {
		fprintf(stderr,"ReAllocation of Model Failed\n") ;
		return -1 ;
	}

	if (serialize(&generative_model,(*model)+size2)==-1) {
		fprintf(stderr,"Serialization of score_probs_info failed\n") ;
		return -1 ;
	}


	fprintf(stderr , "finish : learn_predictor_and_score_probs_ranks ........: %i\n" , size3);

	return size3 ;
}





// Learn age-matched predictor + P(Score)
int learn_predictor_and_score_probs(xy_data *xy, string method, generalized_learner_info_t *learning_info, unsigned char **model) {

	if (learning_info->incFile == NULL) {
		fprintf(stderr,"incidence file required when matching (for final map from prob to specificity)\n") ;
		return -1 ;
	}

	double *preds = (double *) malloc((xy->nrows)*sizeof(double)) ;
	double *probs = (double *) malloc((xy->nrows)*sizeof(double)) ;
	double *post_preds = (double *) malloc((xy->nrows)*sizeof(double)) ;
	double *labels = (double *) malloc((xy->nrows)*sizeof(double)) ;
	int *dates = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *ids = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *flags = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *censor = (int *) malloc((xy->nrows)*sizeof(int)) ;

	if (preds == NULL || labels == NULL || dates == NULL || ids == NULL || flags == NULL || censor == NULL || post_preds==NULL) {
		fprintf(stderr,"Allocation for CV failed\n") ;
		return -1 ;
	}	

	// Get Predictions from cross-validation
	if (get_predictions(xy,method,learning_info,learning_info->sp_nfold,preds,dates,ids,flags,censor,labels) == -1) {
		fprintf(stderr,"Cross Validation for P(Score) Failed\n") ;
		return -1 ;
	}

	// Calculate P(Score|Case) and P(Score|Control)
	score_probs_info score_probs ;
	if (get_score_probs(preds,dates,ids,xy->nrows,learning_info->sp_start_period,learning_info->sp_end_period,learning_info->registry,score_probs) == -1) {
		fprintf(stderr,"Calculating of Score probabilities failed\n") ;
		return -1;
	}

	// Get Model (Predictor + ScoreProbs)
	learning_info->sp_nfold = 0 ;
	int size ;
	if ((size = learn_predictor(xy,method,learning_info,model))  == -1) {
		fprintf(stderr,"Predictor learning failed for method \'%s\'\n",method.c_str()) ;
		return -1 ;
	}

	int size2 = size + (int) get_size(&score_probs) ;

	if (((*model) = (unsigned char *) realloc (*model,size2)) == NULL) {
		fprintf(stderr,"ReAllocation of Model Failed\n") ;
		return -1 ;
	}

	if (serialize(&score_probs,(*model)+size)==-1) {
		fprintf(stderr,"Serialization of score_probs_info failed\n") ;
		return -1 ;
	}

	// Prepare for adjustment of score from P(CRC|Score) to "Specificity"
	// Get Age Dependency from file
	gen_model temp_generative_model ;
	if (read_generative_model(learning_info->incFile,&temp_generative_model) == -1) {
		fprintf(stderr,"Reading generative model from file failed\n") ;
		return -1;
	}

	if (temp_generative_model.resolutions.size() != 1) {
		fprintf(stderr,"Key size in age matching should be one\n") ;
		return -1 ;
	}

	int age_col = learning_info->field_cols["Age"] ;
	vector<vector<double> > keys ;
	for (int i=0; i<xy->nrows; i++) {
		vector<double> key(1,xy->x[XIDX(age_col,i,xy->nrows)]) ;
		keys.push_back(key) ;
	}

	// Get Probs from score + age
	if (get_probs_from_incidence(keys,&temp_generative_model,probs) == -1) {
		fprintf(stderr,"Cannot caluclate probabilities from generative model\n") ;
		return -1 ;
	}

	memcpy(post_preds ,preds , sizeof(double)*xy->nrows);
	get_posteriors(post_preds,probs,xy->nrows,score_probs) ;

	// Build translation table
	int neg_nrows=0;
	for (int i=0; i<xy->nrows; i++) {
		if (xy->y[i]==0) 
			post_preds[neg_nrows++] = ((int) (post_preds[i]*1000 + 0.5))/1000.0 ;
	}

	sort(post_preds,post_preds+neg_nrows,rev_double_compare()) ;
	vector<pair<double,double> >  pred_to_spec ;
	
	double temp_count=0;
	double temp_sum=0;
	double prev_preds = post_preds[0];
	for (int i=0; i<neg_nrows; i++) {
		double temp_spec = 100 * (1 - (double) i/neg_nrows) ;
//		temp_spec = (double)  ((int) (temp_spec*10000 + 0.5))/100;

		if (post_preds[i]!= prev_preds) {
			double avg_spec = temp_sum/temp_count ;
//			double avg_spec = (double)  ((int) (100*temp_sum/temp_count + 0.5))/100;
			pair<double,double> temp_pair (prev_preds ,avg_spec );
			pred_to_spec.push_back(temp_pair);
			temp_count=0;
			temp_sum=0;
		} 
		temp_count++;
		temp_sum+=temp_spec;
		prev_preds = post_preds[i];
	}

	// And last entry ...
	double avg_spec = (double)  ((int) (100*temp_sum/temp_count + 0.5))/100;
	pair<double,double> temp_pair (prev_preds ,avg_spec );
	pred_to_spec.push_back(temp_pair);

	int size3 = size2 + (int) get_size(&pred_to_spec);

	if (((*model) = (unsigned char *) realloc (*model,size3)) == NULL) {
		fprintf(stderr,"ReAllocation of Model Failed\n") ;
		return -1 ;
	}

	if (serialize(&pred_to_spec,(*model)+size2)==-1) {
		fprintf(stderr,"Serialization of score_probs_info failed\n") ;
		return -1 ;
	}

	//Create age-dependancy from data
	gen_model generative_model ;
	get_gen_model(xy,learning_info,&generative_model) ;

	int size4 = size3 + (int) get_size(&generative_model) ;

	if (((*model) = (unsigned char *) realloc (*model,size4)) == NULL) {
		fprintf(stderr,"ReAllocation of Model Failed\n") ;
		return -1 ;
	}

	if (serialize(&generative_model,(*model)+size3)==-1) {
		fprintf(stderr,"Serialization of score_probs_info failed\n") ;
		return -1 ;
	}

	return size4 ;
}


size_t get_size (pred_to_spec_info_t *pred_to_spec) {
	size_t size = sizeof(int) +  2*sizeof(double)*pred_to_spec->size() ;
	return size ;
}


int serialize (pred_to_spec_info_t *pred_to_spec, unsigned char *model) {

	size_t idx = 0 ;
	int size = (int) pred_to_spec->size(); 
	memcpy(model + idx, &size, sizeof(int)) ; idx += sizeof(int) ;


	for (int i=0; i<size; i++) {
		memcpy(model + idx, &((*pred_to_spec)[i].first),sizeof(double)) ; idx += sizeof(double) ; 
		memcpy(model + idx, &((*pred_to_spec)[i].second),sizeof(double)) ; idx += sizeof(double) ; 
	}

	return (int) idx;
}

int write_pred_to_spec (pred_to_spec_info_t *pred_to_spec, char *file_name) {


	FILE *fp = safe_fopen(file_name, "w", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open file \'%s\' for writing\n",file_name) ;
		return -1 ;
	}

	fprintf(fp,"Size %zd\n",pred_to_spec->size());
	for (int i=0; i<pred_to_spec->size(); i++)
		fprintf(fp,"Map %lg %lg\n",(*pred_to_spec)[i].first,(*pred_to_spec)[i].second) ;
	fclose(fp) ;

	return 0 ;
}

int deserialize(unsigned char *model, pred_to_spec_info_t *pred_to_spec) {

	size_t idx = 0 ;
	int size ;
	memcpy(&size, model + idx, sizeof(int)) ; idx += sizeof(int) ;

	double pred;
	double spec;
	for (int i=0; i<size; i++) {
			memcpy(&pred, model + idx, sizeof(double)) ; idx += sizeof(double) ;
			memcpy(&spec, model + idx, sizeof(double)) ; idx += sizeof(double) ;
			pred_to_spec->push_back(pair<double, double>(pred, spec));
	}
	return (int) idx ;
}


// (De)Serialization of score_probs_info
size_t get_size (score_probs_info *score_probs) {

	size_t size = 2*sizeof(double) ;
	for (int i=0; i<2; i++) 
		size += sizeof(int) + 2*sizeof(double) + score_probs->probs[i].size() * (sizeof(int) + sizeof(double)) ;

	return size ;
}

int serialize (score_probs_info *score_probs, unsigned char *model) {

	size_t idx = 0 ;
	memcpy(model + idx, &(score_probs->min),sizeof(double)) ; idx += sizeof(double) ; 
	memcpy(model + idx, &(score_probs->score_res),sizeof(double)) ;idx += sizeof(double) ;	
	
	for (int i=0; i<2; i++) {
		int size = (int) score_probs->probs[i].size() ;
		memcpy(model + idx, &size, sizeof(int)) ; idx += sizeof(int) ;

		double min = score_probs->min_preds[i] ;
		memcpy(model + idx, &min, sizeof(double)) ; idx += sizeof(double) ;
		double max = score_probs->max_preds[i] ;
		memcpy(model + idx, &max, sizeof(double)) ; idx += sizeof(double) ;

		for(map<int,double>::iterator it=score_probs->probs[i].begin(); it!=score_probs->probs[i].end(); it++) {
			int value = it->first ;
			double prob = it->second ;
			memcpy(model + idx, &value, sizeof(int)) ; idx += sizeof(int) ;
			memcpy(model + idx, &prob, sizeof(double)) ; idx += sizeof(double) ;
		}
	}

	return (int) idx ;
}

int write_score_probs (score_probs_info *score_probs, char *file_name) {

	FILE *fp = safe_fopen(file_name, "w", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open file \'%s\' for writing\n",file_name) ;
		return -1 ;
	}

	fprintf(fp,"Min %lg\n",score_probs->min) ;
	fprintf(fp,"Res %lg\n",score_probs->score_res) ;

	for (int i=0; i<2; i++) {
		fprintf(fp,"MinScore %d %lg\n",i,score_probs->min_preds[i]) ;
		fprintf(fp,"MaxScore %d %lg\n",i,score_probs->max_preds[i]) ;

		fprintf(fp,"Size %d %zd\n",i,score_probs->probs[i].size()) ;
		for(map<int,double>::iterator it=score_probs->probs[i].begin(); it!=score_probs->probs[i].end(); it++)
			fprintf(fp,"ScoreProb %d %d %lg\n",i,it->first,it->second);
	}
	fclose(fp) ;

	return 0 ;
}


int deserialize(unsigned char *model, score_probs_info *score_probs) {

	size_t idx = 0 ;
	memcpy(&(score_probs->min),model + idx, sizeof(double)); idx += sizeof(double) ;
	memcpy(&(score_probs->score_res),model + idx, sizeof(double)) ; idx += sizeof(double) ;

	int size ;
	int value ;
	double prob ;
	double min,max ;
	for (int i=0; i<2; i++) {
		memcpy(&size, model + idx, sizeof(int)) ; idx += sizeof(int) ;	
		memcpy(&min, model + idx, sizeof(double)); idx += sizeof(double) ;
		memcpy(&max, model + idx, sizeof(double)); idx += sizeof(double) ;

		score_probs->min_preds[i] = min ;
		score_probs->max_preds[i] = max ;
		for (int j=0; j<size; j++) {
			memcpy(&value, model + idx, sizeof(int)) ; idx += sizeof(int) ;
			memcpy(&prob, model + idx, sizeof(double)) ; idx += sizeof(double) ;
			score_probs->probs[i][value] = prob ;
		}
	}

	return (int) idx ;
}




		