// Generative Model : Tables of P(Outcome|Incomes)

#define _CRT_SECURE_NO_WARNINGS

#include "localCommonLib.h"

void get_gen_model(xy_data *xy,  generalized_learner_info_t *learning_info, gen_model *model) {

	vector<int>& cols = learning_info->matching_col ;
	model->resolutions = learning_info->matching_res ;

	// Collect
	char id[MAX_STRING_LEN] ;
	map<vector<int>, int> all_keys ;

	for (int i=0; i<xy->nrows; i++) {			
		vector<int> key ;
		for (unsigned int j=0; j<cols.size(); j++) {
			int bin = (int) ((xy->x)[XIDX(cols[j],i,xy->nrows)]/(model->resolutions)[j] + 0.5) ;
			key.push_back(bin) ;
		}
		all_keys[key] = 1 ;

		sprintf(id,"%d",xy->idnums[i]) ;
		if ((learning_info->registry).find(id) == (learning_info->registry).end()) { // Control
			(model->nneg)[key] ++ ;
		} else { // Cancer - Look for registry in the defined time-window
			int day = get_day(xy->dates[i]) ;
			for (unsigned int icancer=0; icancer < (learning_info->registry)[id].size(); icancer++) {
				if ((learning_info->registry)[id][icancer].index == 1 && 
					(learning_info->registry)[id][icancer].days >= day + learning_info->sp_start_period && (learning_info->registry)[id][icancer].days <= day + learning_info->sp_end_period) {
					(model->npos)[key] ++ ;
					break ;
				}
			}
		}
	}

	for (auto it = all_keys.begin(); it != all_keys.end(); it ++ ) {
		(model->nneg)[it->first] += 0 ;
		(model->npos)[it->first] += 0 ;
	}

	return ;
}

// (De)Serialization

size_t get_size (gen_model *model) {

	unsigned int key_size = (unsigned int) ((model->npos).begin()->first).size() ;
	unsigned int nkeys = (unsigned int) (model->npos).size() ;

	return (2*sizeof(unsigned int) + key_size*sizeof(double) + nkeys*(key_size*sizeof(int) + 2*sizeof(int))) ;
}

int serialize (gen_model *model, unsigned char *model_data)  {

	size_t idx = 0 ;

	unsigned int key_size = (unsigned int) ((model->npos).begin()->first).size() ;
	unsigned int nkeys = (unsigned int) (model->npos).size() ;

	memcpy(model_data + idx,&key_size,sizeof(unsigned int)) ; idx += sizeof(unsigned int) ; 
	memcpy(model_data + idx,&nkeys,sizeof(unsigned int)) ; idx += sizeof(unsigned int) ; 

	for (unsigned int i=0; i<key_size; i++) {
		double res = (model->resolutions)[i] ;
		memcpy(model_data + idx,&res,sizeof(double)) ; idx += sizeof(double) ;
	}

	for (auto it = (model->npos).begin(); it != (model->npos).end(); it++) {
		for (unsigned int i=0; i<key_size; i++) {
			int ikey = (it->first)[i] ;
			memcpy(model_data+idx,&ikey,sizeof(int)); idx += sizeof(int) ; 
		}

		int val1 = (model->npos)[it->first] ;
		memcpy(model_data+idx,&val1,sizeof(int)) ; idx += sizeof(int) ;
		int val2 = (model->nneg)[it->first] ;
		memcpy(model_data+idx,&val2,sizeof(int)) ; idx += sizeof(int) ;
	}

	return (int) idx ;
}

int deserialize(unsigned char *model_data, gen_model *model) {

	size_t idx = 0 ;

	unsigned int key_size,nkeys ;
	memcpy(&key_size,model_data+idx,sizeof(unsigned int)) ; idx += sizeof(unsigned int) ; 
	memcpy(&nkeys,model_data+idx,sizeof(unsigned int)) ; idx += sizeof(unsigned int) ;

	for (unsigned int j=0; j<key_size; j++) {
		double res ;
		memcpy(&res,model_data+idx,sizeof(double)) ; idx += sizeof(double) ;
		model->resolutions.push_back(res) ;
	}

	for (unsigned int i=0; i<nkeys ; i++) {
		vector<int> key ;
		for (unsigned int j=0; j<key_size; j++) {
			int ikey ;
			memcpy(&ikey,model_data+idx,sizeof(int)) ; idx += sizeof(int) ;
			key.push_back(ikey) ; 
		}

		int val1 ;
		memcpy(&val1,model_data+idx,sizeof(int)) ; idx += sizeof(int) ;
		(model->npos)[key] = val1 ;

		int val2 ;
		memcpy(&val2,model_data+idx,sizeof(int)) ; idx += sizeof(int) ;
		(model->nneg)[key] = val2 ;
	}

	return (int) idx ;
}

// Read from file
int read_generative_model(FILE *fp, gen_model *model) {

	int ival ;
	double dval ;
	
	if (fscanf(fp,"KeySize %d",&ival) != 1)
		return -1 ;
	unsigned int key_size = ival ;

	if (fscanf(fp," Nkeys %d",&ival) != 1)
		return -1 ;
	unsigned int nkeys = ival ;

	// Resoultion
	for (unsigned int i=0; i<key_size; i++) {
		if (fscanf(fp," %lf",&dval) != 1)
			return -1 ;
		model->resolutions.push_back(dval) ;
	}

	// Keys + Values
	for (unsigned int i=0; i<nkeys; i++) {
		vector<int> key ;
		for (unsigned int i=0; i<key_size; i++) {
			if (fscanf(fp," %d",&ival) != 1)
				return -1 ;
			key.push_back(ival) ;
		}

		if (fscanf(fp," %d",&ival) != 1)
			return -1 ;
		model->npos[key] = ival ;

		if (fscanf(fp," %d",&ival) != 1)
			return -1 ;
		model->nneg[key] = ival ;
	}
	
	return 0 ;
}

// Get Probs
int get_probs_from_generative_model(vector<vector<double> >& keys, gen_model *model, double *probs) {

	int key_size = (int) model->resolutions.size() ;
	map<vector<int>,double> prob_hash ;
	
	// Min/Max
	vector<int> min_keys(key_size),max_keys(key_size) ;
	int first = 1 ;
	for (auto it = (model->npos).begin(); it !=  (model->npos).end(); it++) {
		for (int j=0; j<key_size; j++) {
			if (first == 1 || (it->first)[j] < min_keys[j])
				min_keys[j] = (it->first)[j] ;
			if (first == 1 || (it->first)[j] > max_keys[j])
				max_keys[j] = (it->first)[j] ;
		}
		first = 0 ;
	}

	for (unsigned int i=0; i<keys.size(); i++) {
	
		vector<int> ikey ;
		for (int j=0; j<key_size; j++)
			ikey.push_back((int) (keys[i][j]/model->resolutions[j] + 0.5)) ;
//		printf("Checking %f %f (%d %d)\n",keys[i][0],keys[i][1],ikey[0],ikey[1]) ;

		if (prob_hash.find(ikey) == prob_hash.end()) {
			double npos = 0 , nneg = 0 ;
			int diff = 0 ;
			while (npos+nneg < MIN_N_FOR_PROBS) {
				int exceed = 1 ;
				for (int j=0; j<key_size; j++) {
					if (ikey[j] - diff >= min_keys[j] || ikey[j] + diff <= max_keys[j]) {
						exceed = 0 ;
						break ;
					}
				}
				
				if (exceed)
					return -1 ;

				int n = 1 ;
				int nvals = 2*diff + 1 ;
				for (int j=0; j<key_size; j++)
					n *= nvals ;
				
				npos = nneg = 0 ;
				for (int shift=0; shift<n; shift++) {
					vector<int> skey ;
					int val = shift ;
					for (int j=0; j<key_size; j++) {
						skey.push_back(ikey[j] + val % nvals - diff) ;
						val /= nvals ;
					}
				
					if ((model->npos).find(skey) != (model->npos).end()) {
						npos += (model->npos)[skey] ;
						nneg += (model->nneg)[skey] ;
					}
				}

				diff++ ;
			}

//			printf("%f %f %d %d => %f %f => %f\n",keys[i][0],keys[i][1],ikey[0],ikey[1],npos,nneg, npos/(npos+nneg)) ;
			prob_hash[ikey] = (npos/(npos+nneg)) ;
		}

		probs[i] = prob_hash[ikey] ;
	}

	return 0;
}
		
int get_probs_from_incidence(vector<vector<double> >& keys, gen_model *model, double *probs) {

	int key_size = (int) model->resolutions.size() ;
	if (key_size != 1) {
		fprintf(stderr,"Function requires a single-values key\n") ;
		return -1 ;
	}

	vector<pair<int,double> > probs_vec ;
	for (auto it = (model->npos).begin(); it !=  (model->npos).end(); it++) {
		int age = (it->first)[0] ;
		double p = (0.0 + (model->npos)[it->first])/((model->npos)[it->first] + (model->nneg)[it->first]) ;
		pair<int,double> prob(age,p) ;
		probs_vec.push_back(prob) ;
	}

	sort(probs_vec.begin(),probs_vec.end(),compare_pairs_by_idx()) ;

	for (unsigned int i=0; i<keys.size(); i++) {
		double age = keys[i][0] ;
		
		int idx = 0 ;
		while (idx < probs_vec.size() && age > probs_vec[idx].first)
			idx ++ ;

		if (idx == 0)
			probs[i] = probs_vec[0].second ;
		else if (idx == probs_vec.size())
			probs[i] = probs_vec.back().second ;
		else
			probs[i] = probs_vec[idx-1].second + (age - probs_vec[idx-1].first) * (probs_vec[idx].second  - probs_vec[idx-1].second ) / (probs_vec[idx].first - probs_vec[idx-1].first) ;
	}

	return 0;
}
		
int get_probs_from_generative_model_gaussian_kernel(vector<vector<double> >& keys, gen_model *model, double *probs) {

	int key_size = (int) model->resolutions.size() ;
	map<vector<int>,double> prob_hash ;


	for (unsigned int i=0; i<keys.size(); i++) {
	
		vector<int> ikey ;
		for (int j=0; j<key_size; j++)
			ikey.push_back((int) (keys[i][j]/model->resolutions[j] + 0.5)) ;
		printf("Checking %f %f (%d %d)\n",keys[i][0],keys[i][1],ikey[0],ikey[1]) ;

		if (prob_hash.find(ikey) == prob_hash.end()) {
			double npos = 0 , nneg = 0 ;
			for (auto it = (model->npos).begin(); it !=  (model->npos).end(); it++) {
				int s2 = 0 ;
				for (int j=0; j<key_size; j++)
					s2 += (ikey[j] - (it->first)[j]) * (ikey[j] - (it->first)[j]) ; 
				double weight = 10000 * exp ((0.0-s2) / GEN_DIST_VAR) ;
				npos += weight * model->npos[(it->first)] ;
				nneg += weight * model->nneg[(it->first)] ;
				printf("%d %d => %d %d x %f -> %f %f\n",(it->first)[0],(it->first)[1],model->npos[(it->first)],model->nneg[(it->first)],weight,npos,nneg) ;
			}
			printf("%f %f %d %d => %f %f => %f\n",keys[i][0],keys[i][1],ikey[0],ikey[1],npos,nneg, npos/(npos+nneg)) ;
			prob_hash[ikey] = (npos/(npos+nneg)) ;
		}

		
		probs[i] = prob_hash[ikey] ;
	}

	return 0;
}