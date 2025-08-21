// A collection of functions used by several projects in the solution
#define _CRT_SECURE_NO_WARNINGS

// here globals will get asctual storage
#define GLOBAL 


#include "localCommonLib.h" 
#include <stdio.h>

//Globals
int reds[NCBC+NBIOCHEM] = {1,0,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0} ;

char test_names[][MAX_STRING_LEN] = {"RBC","WBC","MPV","Hemog","Hemat","MCV","MCH","MCHC","RDW",
								     "Plat","Eos#","Neut%","Mon%","Eos%","Bas%","Neut#","Mon#","Bas#","Lymph%","Lymph#",

									 "Albumin","Ca","Cholesterol","Creatinine","HDL","LDL","K+","Na","Triglycerides","Urea","Uric Acid","Cl","Ferritin"} ;	
									

int period_min[] = {0,500,1000} ;
int period_max[] = {500,1000,1500} ;
int nperiods = 3 ;

int *gaps = NULL ;
int def_gaps[] = {540,180} ;
int ngaps ; 

int req_sets[NREQ_TEST_NUM] = {0,3,4,6,7} ;

// Patterns for selecting subsets of history
int bgn_date_ptrn_segs[] = {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1};
int end_date_ptrn_segs[] = {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1};
int max_date_ptrn_segs = 10;
int num_date_ptrn_segs = 0;

// Identify percentages in NCBC.
int cbc_percentage[NCBC]={0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,1,0};

// Columns for log-transformation
int log_cols[NCBC] = {0,1,0,0,0,0,0,0,1,0,1,0,1,1,1,1,1,1,0,1} ;
#define MIN_VAL_FOR_LOG 0.005

// functions codes

// Prepare Learning Set : 
// Take only y = 1 or 0
// Take only flagged
// Take only last for y=1
// Sample y=0 according to time.
int filter_learning_set_rank_score(xy_data *xy , int *rank_scores , int rank_limit) {

	int *inds = (int *) malloc ((xy->nrows)*sizeof(int)) ;
	if (inds==NULL) {
		fprintf(stderr,"Cannot allocate inds\n") ;
		return -1 ;
	}


	int n = 0 ;
	int current = 0 ;
	while (current < (xy->nrows)) {

		if((xy->y)[current] == 0.0 || (xy->y)[current] == 1.0 ) {   
			int temp_id = (xy->idnums)[current] ;
			int temp_date = (xy->dates)[current];

			if (rank_scores[current]<=rank_limit)  {
				inds[n++] = current ;
			}
			else {
			}
		}
		else {
		}

		current++ ;
	}

	fprintf(stderr, "filter_learning_set_high_score :%i\n" , n);
	for (int i=0; i<n; i++) {
		(xy->y)[i] = (xy->y)[inds[i]] ;
		(xy->w)[i] = (xy->w)[inds[i]] ;
		(xy->idnums)[i] = (xy->idnums)[inds[i]] ;
		(xy->dates)[i] = (xy->dates)[inds[i]] ;
		(xy->flags)[i] = (xy->flags)[inds[i]] ;
	}

	for (int j=0; j<xy->nftrs; j++) {
		for (int i=0; i<n; i++)
			(xy->x)[XIDX(j,i,n)] = (xy->x)[XIDX(j,inds[i],xy->nrows)] ;
	}

	xy->nrows = n ;

	free(inds) ;
	return 0 ;
}


int prepare_learning_set(double *inx, double *iny, double *inw, int *inids, int *indates, int *flags, 
						 double **x, double **y, double **w, int **ids, int **dates, int nftrs, int inrows)
{

	// Indentify indices
	int *indices ;
	int orows;; 
	if ((orows = get_learning_indices(inids,indates,flags,iny,inrows,&indices)) == -1) {
		fprintf(stderr,"Cannot get learning set indices\n") ;
		return -1 ;
	}

	// Allocate
	double *tx = (double *) malloc (orows*nftrs*sizeof(double)) ; 
	(*y) = (double *) malloc (orows*sizeof(double)) ;
	(*w) = (double *) malloc (orows*sizeof(double)) ;
	(*ids) = (int *) malloc (orows*sizeof(int)) ;
	(*dates) = (int *) malloc (orows*sizeof(int)) ;
	if (tx==NULL || (*y)==NULL || (*w)==NULL || (*ids)==NULL || (*dates)==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	// Filter
	for (int irow=0; irow<orows; irow++) {
		for (int j=0; j<nftrs; j++)
			tx[XIDX(irow,j,nftrs)] = inx[XIDX(j,indices[irow],inrows)] ;
		(*ids)[irow] = inids[indices[irow]] ;
		(*dates)[irow] = indates[indices[irow]] ;
		(*w)[irow] = inw[indices[irow]] ;
		(*y)[irow++] = iny[indices[irow]] ;
	}

	// Rearrange
	if (transpose(tx,x,orows,nftrs) == -1) {
		fprintf(stderr,"Transpose failed\n") ;
		return -1 ;
	}

	return orows ;
}

// Get indices for filtering - 
// Take only y = 1 or 0
// Take only flagged
// Take only last for y=1
// Sample y=0 according to time.

int get_learning_indices(int *ids, int *dates, int *flags, double *y, int nrows, int **indices) {

	// Identify Good Samples
	int orows = 0 ;
	map <int,vector<int> > samples ;

	for (int i=0 ; i<nrows; i++) {
		if (y[i] != 0 && y[i] != 1)
			continue ;

		if (! flags[i])
			continue ;

		samples[ids[i]].push_back(i) ;
		orows ++ ;
	}

	// Allocate
	(*indices) = (int *) malloc(orows*sizeof(int)) ;
	if ((*indices)==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	// Get Vector of years of positive samples
	int *pos_years = (int *) malloc (orows*sizeof(int)) ;
	if (pos_years == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	int npos = 0 ;
	for (map<int, vector<int> >::iterator it = samples.begin(); it != samples.end(); it++) {
		int idx = (it->second).back() ;
		if (y[idx] == 1)
			pos_years[npos++] = dates[idx]/10000 ;
	}

	// Shuffle
	int *order = randomize(npos) ;
	if (order==NULL) {
		fprintf(stderr,"Shuffle failed\n") ;
		return -1 ;
	}

	for (int i=0; i<npos; i++) {
		int temp = pos_years[i] ;
		pos_years[i] = pos_years[order[i]] ;
		pos_years[order[i]] = temp ;
	}

	// Select according to pos-years

	int irow = 0 ;
	int ipos = 0 ;	

	for (map<int, vector<int> >::iterator it = samples.begin(); it != samples.end(); it++) {
		int idx = (it->second).back() ;
		if (y[idx]== 0) { // Sample according to time
			idx = -1 ;
			for (unsigned int i=0; i<(it->second).size(); i++) {
				int year = dates[(it->second)[i]]/10000 ;
				if (year == pos_years[ipos]) {
					idx = (it->second)[i] ;
					ipos = (ipos+1)%npos ;
					break ;
				}
			}
		}

		(*indices)[irow++] = idx ;
	}

	return orows ;
}


// Read File
int read_file(FILE *fin, double *lines) {
	int nlines ;

	fread(&nlines, 1, sizeof(nlines), fin);
	fread(lines, nlines*MAXCOLS, sizeof(double), fin);
	fclose(fin);

	return nlines ;
}

// Filter learning set - take only patients labeled as 0/1 and last "nlast" flagged sample of each case
int filter_learning_set(xy_data *xy, xy_data *fxy, int nlast) {

	if (copy_xy(fxy,xy) == -1) {
		fprintf(stderr,"Copy XY failed\n") ;
		return -1 ;
	}

	if (take_samples(fxy,nlast) == -1) {
		fprintf(stderr,"Take sampled failed\n") ;
		return -1;
	}

	int npos=0, nneg=0 ; 
	for (int i=0; i<fxy->nrows; i++) {
		if (fxy->y[i] == 1.0)
			npos++ ;
		else
			nneg++ ;
	}
	fprintf(stderr,"After filtering: Working on %d (%d + %d) x %d\n",fxy->nrows,npos,nneg,fxy->nftrs) ;

	return 0 ;
}

int month_id(int month) {

	int year = (int) month/100 - 1900 ;
	month = month%100 ;

	int id = (year*12 + month)/3 ; 
	return id ;
}

// Take "npos" last samples from labeled patients and sample from unlableled ones to create same calender-years distributions
int take_samples(xy_data *xy, int nlast) {

	char *use = (char *) calloc ((xy->nrows),sizeof(char)) ;
	if (use == NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}
	map<int, int> useidnum;
	
	// Get Vector of pos years
	int *years = (int *) malloc ((xy->nrows)*sizeof(int)) ;
	if (years == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}


	// Select	
	int npos = 0 ;
	int first = 0 ;
	int next = first ;

	while (next < xy->nrows) {
		if ((xy->idnums)[next] != (xy->idnums)[first]) {
			int id = -1 ;
			if ((xy->y)[first] > 0) {
				for(int it=0; it<nlast; it++) { 

					int id = next-(it+1);
					if ((id<0) || (xy->idnums)[id] != (xy->idnums)[first]) 
						continue;
					 
					 
					if (use[id]==0) {				
						years[npos++] = (xy->dates)[id]/10000 ; 
						use[id] = 1;						
					}
				}				 
			}
			first = next ;	
		}			
		next++ ;	
	}

	// Select
	int ipos = 0 ;
	int *order = randomize(npos) ;
	if (order==NULL) {
		fprintf(stderr,"Shuffle failed\n") ;
		return -1 ;
	}

	for (int i=0; i<npos; i++) {
		int temp = years[i] ;
		years[i] = years[order[i]] ;
		years[order[i]] = temp ;
	}

	for(int reit=0; reit<100; reit++) {

		first = 0 ;
		next = first ;

		while (next < xy->nrows) {
			if ((xy->idnums)[next] != (xy->idnums)[first]) {
				if ((xy->y)[first]==0) {
					int id = -1 ;
					int i= (globalRNG::rand()%(next-first))+first;				
					int year = (xy->dates)[i]/10000;
					if ((year == years[ipos]) && (use[i]==0) && (useidnum.find((xy->idnums)[first])==useidnum.end())) {
						id = i ;
						ipos = (ipos+1)%npos ;
						//break ;
					}
				 
				
					if (id != -1) {
						useidnum[(xy->idnums)[first]]=1;
						use[id]=1;
					}
				}
				first = next ;
			}
			next++ ;
		}
	}	

	// Get Indices
	int *inds = (int *) malloc((xy->nrows)*sizeof(int)) ;
	if (inds == NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}

	int irow = 0 ;
	for (int i=0; i<xy->nrows; i++) {
		if (use[i])
			inds[irow++] = i ;
	}

	// Change xy.
	for (int i=0; i<irow; i++) {
		(xy->y)[i] = (xy->y)[inds[i]] ;
		(xy->w)[i] = (xy->w)[inds[i]] ;
		(xy->idnums)[i] = (xy->idnums)[inds[i]] ;
		(xy->dates)[i] = (xy->dates)[inds[i]] ;
		(xy->flags)[i] = (xy->flags)[inds[i]] ;
	}

	for (int j=0; j<xy->nftrs; j++) {
		for (int i=0; i<irow; i++)
			(xy->x)[XIDX(j,i,irow)] = (xy->x)[XIDX(j,inds[i],xy->nrows)] ;
	}

	xy->nrows = irow ;

	free(years) ;
	free(use);
	free(order) ;
	free(inds) ;

	return 0 ;
}

void take_flagged(xy_data *xy) {

	int irow = 0 ;
	for (int id=0; id<xy->nrows; id++) {
		if ((xy->flags)[id]) {
			for (int j=0; j<xy->nftrs; j++)
				(xy->x)[XIDX(irow,j,xy->nftrs)] = (xy->x)[XIDX(id,j,xy->nftrs)] ;
			(xy->idnums)[irow] = (xy->idnums)[id] ;
			(xy->dates)[irow] = (xy->dates)[id] ;
			(xy->flags)[irow] = (xy->flags)[id] ;
			(xy->y)[irow++] = (xy->y)[id] ;
		}
	}

	xy->nrows=irow ;
}



// Split Data
int get_split_data(xy_data *xy, int npatients, xy_data *xy1, xy_data *xy2, int *order, int start, int end) {

	// Splitting flags
	int *group = (int *) malloc ((xy->nrows)*sizeof(int)) ;
	if (group==NULL) {
		fprintf(stderr,"Flags allocation failed\n") ;
		return -1 ;
	}

	int ipatient = 0 ;

	xy1->nrows = xy2->nrows = 0  ;
	xy1->nftrs = xy2->nftrs = xy->nftrs ;

	for (int i=0; i<(xy->nrows); i++) {
		if (order[ipatient] < start || order[ipatient] > end) {
			group[i] = 1 ;
			(xy1->nrows)++ ;
		} else {
			group[i] = 2 ;
			(xy2->nrows)++ ;
		}

		if (i != (xy->nrows)-1 && xy->idnums[i+1] != xy->idnums[i])
			ipatient++ ;
	}

	// Allocate
	(xy1->x) = (double *) malloc((xy1->nrows)*(xy1->nftrs)*sizeof(double)) ;
	(xy1->y) = (double *) malloc((xy1->nrows)*sizeof(double)) ;
	(xy1->w) = (double *) malloc((xy1->nrows)*sizeof(double)) ;
	(xy1->idnums) = (int *) malloc((xy1->nrows)*sizeof(int)) ;
	(xy1->dates) = (int *) malloc((xy1->nrows)*sizeof(int)) ;
	(xy1->flags) = (int *) malloc((xy1->nrows)*sizeof(int)) ;
	(xy1->censor) = (int *) malloc((xy1->nrows)*sizeof(int)) ;

	(xy2->x) = (double *) malloc((xy2->nrows)*(xy1->nftrs)*sizeof(double)) ;
	(xy2->y) = (double *) malloc((xy2->nrows)*sizeof(double)) ;
	(xy2->w) = NULL ;
	(xy2->idnums) = (int *) malloc((xy2->nrows)*sizeof(int)) ;
	(xy2->dates) = (int *) malloc((xy2->nrows)*sizeof(int)) ;
	(xy2->flags) = (int *) malloc((xy2->nrows)*sizeof(int)) ;
	(xy2->censor) = (int *) malloc((xy2->nrows)*sizeof(int)) ;

	if ((xy1->x)==NULL || (xy2->x)==NULL || (xy1->y)==NULL || (xy2->y)==NULL || (xy1->w)==NULL || (xy1->idnums)==NULL || (xy2->idnums)==NULL || (xy1->dates)==NULL || (xy2->dates)==NULL || 
		(xy1->flags)==NULL || (xy2->flags)==NULL || (xy1->censor)==NULL || (xy2->censor)==NULL) {
			fprintf(stderr,"Allocation failed\n") ;
			return -1 ;
	}

	// Copy
	int nrows1=0 ;
	int nrows2=0 ;

	for (int irow=0; irow<(xy->nrows); irow++) {
		if (group[irow] == 1) {		
			for (int icol=0; icol<xy->nftrs; icol++)
				(xy1->x)[XIDX(icol,nrows1,xy1->nrows)] = (xy->x)[XIDX(icol,irow,xy->nrows)] ;
			(xy1->w)[nrows1] = (xy->w)[irow] ;
			(xy1->y)[nrows1] = (xy->y)[irow] ;
			(xy1->idnums)[nrows1] = (xy->idnums)[irow] ;
			(xy1->dates)[nrows1] = (xy->dates)[irow] ;
			(xy1->flags)[nrows1] = (xy->flags)[irow] ;
			(xy->censor)[nrows1] = (xy->censor)[irow] ;
			nrows1++ ;

		} else {
			for (int icol=0; icol<(xy->nftrs); icol++)
				(xy2->x)[XIDX(icol,nrows2,xy2->nrows)] = (xy->x)[XIDX(icol,irow,xy->nrows)] ;
			(xy2->y)[nrows2] = (xy->y)[irow] ;
			(xy2->idnums)[nrows2] = (xy->idnums)[irow] ;
			(xy2->dates)[nrows2] = (xy->dates)[irow] ;
			(xy2->flags)[nrows2] = (xy->flags)[irow] ;
			(xy2->censor)[nrows2] = (xy->censor)[irow] ;
			nrows2++ ;
		}
	}

	return 0 ;
}

// Imputation according to mean values
void get_mean_values(xy_data *xy, double *means, double *sdvs) {

	for (int i=0; i<xy->nftrs; i++) {
		int n = 0 ; 
		double sum = 0 ;
		double sum2 = 0 ;
		for (int j=0; j<xy->nrows; j++) {
			double value = (xy->x)[XIDX(i,j,xy->nrows)] ;
			if (value != MISSING_VAL) {
				n ++ ;
				sum += value ;
				sum2 += value * value ;
			}
		}

		assert(n>1) ;

		means[i] = sum/n ;
		sdvs[i] = sqrt((sum2 - means[i]*sum)/(n-1)) ;
	}

	return ;
}

void replace_with_approx_mean_values(xy_data *xy, double *means, double *sdvs) {

	for (int j=0; j<xy->nrows; j++) {
		globalRNG::srand(xy->idnums[j] + xy->dates[j]) ;

		for (int i=0; i<xy->nftrs; i++) {		
			if ((xy->x)[XIDX(i,j,xy->nrows)] == MISSING_VAL)
				(xy->x)[XIDX(i,j,xy->nrows)] = means[i] + (globalRNG::rand()/(globalRNG::max()+1.0) * 0.1 * sdvs[i])  - 0.05*sdvs[i] ;
		}	
	}

	return ;
}


double get_pairing_ratio(map<int,int>& hist1, map<int,int>& hist2, int n, double w) {

	// Get ratio for w->0
	double min_ratio = -1, max_ratio = -1;
	for (int i=0; i<=n; i++) {
		if (hist1.find(i) != hist1.end() && hist2.find(i) != hist2.end()) {
			double iratio = (hist2[i] + 0.0)/hist1[i] ;
			if (min_ratio == -1 || iratio < min_ratio)
				min_ratio = iratio ;
			if (max_ratio == -1 || iratio > max_ratio)
				max_ratio = iratio ;
		}
	}

	double r_step = (max_ratio - min_ratio)/R_NSTEP ;

	// Find Optimal ratio
	int opt_cnt1,opt_cnt2 ;
	double opt_r = 0 ;
	for (int ir=0; ir<R_NSTEP; ir++) {
		double r = min_ratio + ir*r_step ;

		int cnt1=0, cnt2=0 ; 
		for (int i=0; i<=n; i++) {
			if (hist2.find(i) == hist2.end())
				cnt1 += hist1[i] ;
			else if (hist1.find(i) == hist1.end())
				cnt2 += hist2[i] ;
			else {
				double iratio = (hist2[i] + 0.0)/hist1[i] ;
				if (iratio > r)
					cnt2 += (hist2[i] - (int) (hist1[i]*r + 0.5)) ;
				else
					cnt1 += (hist1[i] - (int) (hist2[i]/r + 0.5)) ;
			}
		}

		if (opt_r == 0 || (cnt1 + w*cnt2) < (opt_cnt1 + w*opt_cnt2)) {
			opt_r = r ;
			opt_cnt1 = cnt1 ;
			opt_cnt2 = cnt2 ;
		}
	}

	return opt_r;
}

int get_paired_matrix(xy_data *in, int col, double res, double matching_w, xy_data *out) {

	vector<int> cols ;
	vector<double> resolutions ;
	
	cols.push_back(col) ;
	resolutions.push_back(res) ;

	return get_paired_matrix(in,cols,resolutions,matching_w,out) ;
}

int get_paired_matrix(xy_data *in, vector<int>& cols, vector<double>& resolutions, double matching_w, xy_data *out) {

	if (cols.size() != resolutions.size()) {
		fprintf(stderr,"cols and resolutions length mismatch\n") ;
		return -1 ;
	}

	init_xy(out) ;
	out->nftrs = in->nftrs ;

	// Count bins
	vector<int> min_bins ;
	vector<int> nbins ;
	int tot_nbins = 1 ;
	for (unsigned int i=0; i<cols.size(); i++) {
		int min_bin,max_bin ;
		for (int j=0; j<in->nrows; j++) {
			int bin = (int) ((in->x)[XIDX(cols[i],j,in->nrows)]/resolutions[i] + 0.5) ;
			if (j == 0 || bin < min_bin)
				min_bin = bin ;
			if (j == 0 || bin > max_bin)
				max_bin = bin ;
		}

		min_bins.push_back(min_bin) ;
		nbins.push_back(max_bin-min_bin + 1) ;
		tot_nbins *= nbins.back() ;
	}

	// Histogram of column
	map<int, int> crc_bins ;
	map<int, int> non_crc_bins ;

	for (int i=0; i<in->nrows; i++) {
		int bin = 0 ;
		for (unsigned int j=0; j<cols.size(); j++) {
			bin *= nbins[j] ;
			bin += ((int) ((in->x)[XIDX(cols[j],i,in->nrows)]/resolutions[j] + 0.5) - min_bins[j]) ;
		}

		if (in->y[i] > 0)
			crc_bins[bin]++ ;
		else
			non_crc_bins[bin]++ ;
	}

	double r = get_pairing_ratio(crc_bins,non_crc_bins,tot_nbins,matching_w) ;

	// Get Probabilities
	map <int,double> crc_p ;
	map <int,double> non_crc_p ;
	for (int i=0; i<tot_nbins; i++) {
		if (crc_bins.find(i) == crc_bins.end() || non_crc_bins.find(i) == non_crc_bins.end()) {
			crc_p[i] = 0.0 ;
			non_crc_p[i] = 0.0 ;
		} else {
			double inr = (non_crc_bins[i] + 0.0)/(crc_bins[i]) ;
			if (inr > r) {
				crc_p[i] = 1.0 ;
				non_crc_p[i] = r/inr ;
			} else {
				crc_p[i] = inr/r ;
				non_crc_p[i] = 1.0 ;
			}
		}
	}

	// Select
	int *ids = (int *) malloc ((in->nrows)*sizeof(int)) ;
	if (ids == NULL) {
		fprintf(stderr,"Ids allocation failed\n") ;
		return -1 ;
	}

	out->nrows = 0 ;
	for (int i=0; i<in->nrows; i++) {
		int bin = 0 ;
		for (unsigned int j=0; j<cols.size(); j++) {
			bin *= nbins[j] ;
			bin += ((int) ((in->x)[XIDX(cols[j],i,in->nrows)]/resolutions[j] + 0.5) - min_bins[j]) ;
		}

		double p = globalRNG::rand()/(globalRNG::max()+1.0) ;
		if (((in->y)[i] > 0 && p < crc_p[bin]) || ((in->y)[i] <= 0 && p < non_crc_p[bin]))
			ids[(out->nrows)++] = i ;
	}

	// Allocate
	if (((out->x) = (double *) malloc((out->nrows)*(in->nftrs)*sizeof(double)))==NULL || ((out->y) = (double *) malloc((out->nrows)*sizeof(double)))==NULL ||
		((out->w) = (double *) malloc((out->nrows)*sizeof(double)))==NULL) {
			fprintf(stderr,"Allocation failed\n") ;
			return -1 ;
	}

	// Copy
	for (int i=0; i<(out->nrows); i++) {
		(out->y)[i] = (in->y)[ids[i]] ;
		(out->w)[i] = (in->w)[ids[i]] ;
		for (int j=0; j<in->nftrs; j++)
			(out->x)[XIDX(j,i,out->nrows)] = (in->x)[XIDX(j,ids[i],in->nrows)] ;
	}

	free(ids) ;
	return 0 ;
}


int adjust_learning_set(xy_data *xy, vector<int>& matching_col, vector<double>& matching_res, double matching_w, xy_data *nxy) {

	init_xy(nxy) ;

	if (matching_col.size()) {
		fprintf(stderr,"Pairing :\n") ;
		if (get_paired_matrix(xy,matching_col,matching_res,matching_w,nxy) == -1) {
			fprintf(stderr,"Cannot get paired matrix\n") ;
			return -1 ;
		}
		int npos = 0, nneg = 0 ;
		for (int i=0; i<nxy->nrows; i++) {
			if ((nxy->y)[i] > 0)
				npos ++ ;
			else
				nneg ++ ;
		}
		fprintf(stderr,"Nrows: %d->%d (%d + %d)\n",xy->nrows,nxy->nrows,npos,nneg) ;
	} else {
		if (copy_xy(nxy,xy) == -1) {
			fprintf(stderr,"Cannot copy matrix\n") ;
			return -1 ;
		}
	}

	return 0;
}

// Handle feature info
int get_feature_flags(char *info, feature_flags *fflags) {

	fflags->gender = 0 ;
	fflags->age = 1 ;
	fflags->minmax = 0 ;
	fflags->bmi = 1 ;
	fflags->smx = 1 ;
	fflags->qty_smx = 1 ;
	fflags->cnts = 1 ;
	fflags->binary_history = 0 ;

	for (int i=0; i<NCBC; i++)
		fflags->cbcs[i] = 1 ;
	for (int i=0; i<NBIOCHEM; i++)
		fflags->biochems[i] = 0 ;
	for (int i=0; i<NEXTRA; i++)
		fflags->extra[i] = 0 ;

	if (strcmp(info,"cbc")==0) { // CBC + Counts
		fflags->bmi = 0 ;
		fflags->smx = 0 ;
		fflags->qty_smx = 0;
	} else if (strcmp(info,"full")==0) { // Full
		for (int i=0; i<NBIOCHEM; i++)
			fflags->biochems[i] = 1 ;
	} else if (strcmp(info,"red")==0) { // Red + Counts
		fflags->bmi = 0 ;
		fflags->smx = 0 ;
		fflags->qty_smx = 0 ;
		for (int i=0; i<NCBC; i++) {
			if (reds[i] == 0)
				fflags->cbcs[i] = 0 ;
		}
	} else if (strcmp(info,"white")==0) { // White + Counts
		fflags->bmi = 0 ;
		fflags->smx = 0 ;
		for (int i=0; i<NCBC; i++) {
			if (reds[i] == 1)
				fflags->cbcs[i] = 0 ;
		}
	} else if (strcmp(info,"age")==0) { // Only Age
		fflags->bmi = 1 ;
		fflags->smx = 1 ;
		fflags->cnts = 1 ;
		for (int i=0; i<NCBC; i++)
			fflags->cbcs[i] = 0 ;
	}  else if (strcmp(info,"cbc_and_extra")==0) { // CBC + Counts + SMX + QTY_SMX + BMI
		/* All Defualt Values*/
	} else if (strcmp(info,"ce")==0) { // CBC
		fflags->bmi = 0 ;
		fflags->smx = 0 ;
		fflags->qty_smx = 0 ;
		fflags->cnts = 0 ;
	} else if (strcmp(info,"age_and_extra")==0) { // Age + SMX + QTY_SMX + BMI
		for (int i=0; i<NCBC; i++)
			fflags->cbcs[i] = 1 ;
	} else { // Format : G#C#B#C#B#S#Q#F#A#M#H#X#
		if (strlen(info) != 2 + (1 + NCBC) + (1 + NBIOCHEM) + 16 && strlen(info) != 2 + (1 + 1) + (1 + NBIOCHEM) + 16 &&
			strlen(info) != 2 + (1 + NCBC) + (1 + 1) + 16 && strlen(info) != 2 + (1 + 1) + (1 + 1) + 16 &&
			strlen(info) != 2 + (1 + NCBC) + (1 + NBIOCHEM) + 14 + (1 + NEXTRA) && strlen(info) != 2 + (1 + 1) + (1 + NBIOCHEM) + 14 + (1 + NEXTRA) &&
			strlen(info) != 2 + (1 + NCBC) + (1 + 1) + 14 + (1 + NEXTRA)  && strlen(info) != 2 + (1 + 1) + (1 + 1) + 14 + (1 + NEXTRA)) {
				fprintf(stderr,"Features string length is %zd\n",strlen(info)) ;
				return -1 ;
		}

		int idx = 0 ;

		if (info[idx++] != 'G')
			return -1 ;
		if (info[idx] != '1' && info[idx] != '0')
			return -1 ;
		fflags->gender = info[idx++] - '0' ;

		if (info[idx++] != 'C')
			return -1 ;
		if (info[idx] == 'Z') {
			for (int i=0; i<NCBC; i++)
				fflags->cbcs[i] = 0 ;
			idx ++ ;
		} else if (info[idx] == 'O') {
			for (int i=0; i<NCBC; i++)
				fflags->cbcs[i] = 1 ;
			idx ++ ;
		} else {
			for (int i=0; i<NCBC; i++) {
				if (info[idx] != '1' && info[idx] != '0')
					return -1 ;
				fflags->cbcs[i] = info[idx++] - '0' ;
			}
		}

		if (info[idx++] != 'B')
			return -1 ;
		if (info[idx] == 'Z') {
			for (int i=0; i<NBIOCHEM; i++)
				fflags->biochems[i] = 0 ;
			idx ++ ;
		} else if (info[idx] == 'O') {
			for (int i=0; i<NBIOCHEM; i++)
				fflags->biochems[i] = 1 ;
			idx ++ ;
		} else {
			for (int i=0; i<NBIOCHEM; i++) {
				if (info[idx] != '1' && info[idx] != '0')
					return -1 ;
				fflags->biochems[i] = info[idx++] - '0' ;
			}
		}

		if (info[idx++] != 'C')
			return -1 ;
		if (info[idx] != '1' && info[idx] != '0')
			return -1 ;
		fflags->cnts = info[idx++] - '0' ;

		if (info[idx++] != 'B')
			return -1 ;
		if (info[idx] != '1' && info[idx] != '0')
			return -1 ;
		fflags->bmi = info[idx++] - '0' ;

		if (info[idx++] != 'S')
			return -1 ;
		if (info[idx] != '1' && info[idx] != '0')
			return -1 ;
		fflags->smx = info[idx++] - '0' ;

		if (info[idx++] != 'Q')
			return -1 ;
		if (info[idx] != '1' && info[idx] != '0')
			return -1 ;
		fflags->qty_smx = info[idx++] - '0' ;

		if (info[idx++] != 'A')
			return -1 ;
		if (info[idx] != '1' && info[idx] != '0')
			return -1 ;
		fflags->age = info[idx++] - '0' ;

		if (info[idx++] != 'M')
			return -1 ;
		if (info[idx] != '1' && info[idx] != '0')
			return -1 ;
		fflags->minmax = info[idx++] - '0' ;

		if (info[idx++] != 'H')
			return -1 ;
		if (info[idx] != '1' && info[idx] != '0')
			return -1 ;
		fflags->binary_history = info[idx++] - '0' ;

		if (info[idx++] != 'X')
			return -1 ;
		if (info[idx] == 'Z') {
			for (int i=0; i<NEXTRA; i++)
				fflags->extra[i] = 0 ;
			idx ++ ;
		} else if (info[idx] == 'O') {
			for (int i=0; i<NEXTRA; i++)
				fflags->extra[i] = 1 ;
			idx ++ ;
		} else {
			for (int i=0; i<NEXTRA; i++) {
				if (info[idx] != '1' && info[idx] != '0')
					return -1 ;
				fflags->extra[i] = info[idx++] - '0' ;
			}
		}

	}

	fprintf(stderr,"Gender Flag = %d\n",fflags->gender) ;
	fprintf(stderr,"Age Flag = %d\n",fflags->age) ;
	fprintf(stderr,"BMI Flag = %d\n",fflags->bmi) ;
	fprintf(stderr,"SMX Flag = %d\n",fflags->smx) ;
	fprintf(stderr,"QTY_SMX Flag = %d\n",fflags->qty_smx) ;
	fprintf(stderr,"CBC Flags = ") ;
	for (int i=0; i<NCBC; i++)
		fprintf(stderr,"%d",fflags->cbcs[i]) ;
	fprintf(stderr,"\n") ;
	fprintf(stderr,"Biochem Flags = ") ;
	for (int i=0; i<NBIOCHEM; i++)
		fprintf(stderr,"%d",fflags->biochems[i]) ;
	fprintf(stderr,"\n") ;
	fprintf(stderr,"Extra Flags = ") ;
	for (int i=0; i<NEXTRA; i++)
		fprintf(stderr,"%d",fflags->extra[i]) ;
	fprintf(stderr,"\n") ;
	fprintf(stderr,"Counts Flag = %d\n",fflags->cnts) ;
	fprintf(stderr,"MinMax Flag = %d\n",fflags->minmax) ;
	fprintf(stderr,"BinaryHistory Flag = %d\n",fflags->binary_history) ;

	return 0 ;
}


void adjust_mask(feature_flags *fflags , bool *mask) {
	
	int icol = fflags->gender ;
	for (int i=0; i<NCBC; i++) {
		if (fflags->cbcs[i]) {
			mask[icol+1] = false ;
			icol += (3 + ngaps) ;
		}
	}

	for (int i=0; i<NBIOCHEM; i++) {
		if (fflags->biochems[i]) {
		    mask[icol+1] = false ;
		    icol += (3 + ngaps) ;
		}
	}

	return ;
}


int get_nftrs(feature_flags *fflags) {

	int ntests = 0 ;
	for (int i=0; i<NCBC; i++)
		ntests += fflags->cbcs[i] ;
	for (int i=0; i<NBIOCHEM; i++)
		ntests += fflags->biochems[i] ;

	int nftrs = 0 ;
	nftrs += fflags->age ;
	nftrs += fflags->gender ;
	nftrs += ntests * (3 + ngaps) ;

	if (fflags->cnts)
		nftrs += nperiods ;

	if (fflags->bmi)
		nftrs += BMI_NCOLS ;

	if (fflags->smx)
		nftrs += SMX_NCOLS ;

	if (fflags->qty_smx)
		nftrs += QTY_SMX_NCOLS ;

	if (fflags->minmax)
		nftrs += ntests * 2 ;

	if (fflags->binary_history)
		nftrs ++ ;

	for (int i=0; i<NEXTRA; i++)
		nftrs += fflags->extra[i] ;

	return nftrs ;
}

void get_global_values(double lines[], int col , int first, int last, int ncols, double *out, int *days,float missing_val) {

	out[0] = out[1] = MISSING_VAL ;

	for (int iline = first; iline < last; iline ++) {
		if (lines[XIDX(iline,col,ncols)] != missing_val && days[iline] < days[last] - MINMAX_GAP) {
			if (out[0] == MISSING_VAL || lines[XIDX(iline,col,ncols)] < out[0])
				out[0] = lines[XIDX(iline,col,ncols)] ;
			if (out[1] == MISSING_VAL || lines[XIDX(iline,col,ncols)] > out[1])
				out[1] = lines[XIDX(iline,col,ncols)] ;
		}
	}

	return ;
}

double get_weighted_test_value(double lines[], int col , int first, int last, int *days, int day, int ncols, int *nvals, float missing_val) {

	double sum = 0 ;
	double norm = 0 ;
	double w ;
	*nvals = 0 ;

	int i ;
	for (i=first; i<=last; i++) {

		if (lines[XIDX(i,col,ncols)] != missing_val) {
			if (days[i] == day)
				w = MAX_W ;
			else 		
				w = 1 / (days[i] + 0.0 - day) ;

			w = w*w ;
			norm += w;
			sum += (lines[XIDX(i,col,ncols)]) * w ;
			(*nvals) ++ ;
		}
	}

	if (*nvals)
		return (sum/norm) ;
	else
		return MISSING_VAL ;
}


void get_test_values(double lines[], int col, int first, int last, int *days, int *gaps, int ngaps, int ncols, double *x, int *iftr, int nftrs, float missing_val) {

	int nvalues,nvalues2 = 0 ;
	double last_val ;

	// Get Current Value
	if (lines[XIDX(last,col,ncols)] != missing_val)		
		last_val = lines[XIDX(last,col,ncols)] ;
	else 
		last_val = get_weighted_test_value(lines,col,first,last,days,days[last],ncols,&nvalues,missing_val) ;

	x[(*iftr)++] = last_val ;

	// Get Previous values
	for (int igap=0; igap<ngaps; igap++) {
		if (nvalues < 2)
			x[(*iftr)++] = MISSING_VAL ;
		else {
			double val = get_weighted_test_value(lines,col,first,last,days,days[last]-gaps[igap],ncols,&nvalues2,missing_val) ;
			if (val == MISSING_VAL)
				x[(*iftr)++] = MISSING_VAL ;
			else
				x[(*iftr)++] = last_val - val ;
		}
	}
}

#define ADDDAYS 20
#define MAXDAYS 720

// Fill the matrix
int get_x_line(double lines[], int iline, int first, int ncols, // Input Data
	int *days, int *countable, // Calculated extra input data
	bins_lm_model *all_models, // Models for estimating CBC values
	double *tempx, int *cnts, // Work space
	feature_flags *fflags, // Features flags
	int nftrs,
	double *x, // Output Data
	float missing_val,
	int no_random
			   ) 
{

	int first_cbc_day = get_day(FIRST_CBC_DATE) ;
	int iftr = 0 ;

	// Gender
	if (fflags->gender)
		x[iftr++] = lines[XIDX(iline,GENDER_COL,ncols)] ;			

	// Tests
	double global[2] ;

	int ncbc=0;
	for(int j=0; j<NCBC ;j++)	{
		if (fflags->cbcs[j]) {
			
			ncbc++;
			get_features(lines,days,first,iline,j,ncols,x,&iftr,all_models+j,tempx,missing_val,no_random) ;

			if (fflags->minmax) {
				get_global_values(lines,TEST_COL+j,first,iline,ncols,global,days,missing_val) ;
				x[iftr++] = global[0] ;
				x[iftr++] = global[1] ;
			}

		}
	}

	for(int j=0; j<NBIOCHEM ;j++)	{
		if (fflags->biochems[j]) {  
			get_features(lines,days,first,iline,NCBC+j,ncols,x,&iftr,all_models+NCBC+j,tempx,missing_val,no_random) ;

			if (fflags->minmax) {
				get_global_values(lines,TEST_COL+NCBC+j,first,iline,ncols,global,days,missing_val) ;
				x[iftr++] = global[0] ;
				x[iftr++] = global[1] ;
			}

		}
	}

	// Age
	if (fflags->age)
		//		x[iftr++] =  (days[iline] - get_day((int)(lines[XIDX(iline,BDATE_COL,ncols)])))/365.0 ;
		x[iftr++] = ((int)lines[XIDX(iline, DATE_COL, ncols)]) / 10000 - ((int)lines[XIDX(iline, BDATE_COL, ncols)]) / 10000;

	// Counts
	if (fflags->cnts)
		x[iftr++] = iline-first;

	// Smoking
	if (fflags->smx) {
		if (lines[XIDX(iline,SMX_COL,ncols)] == missing_val) {
			for (int k=0; k<SMX_NCOLS; k++)
				x[iftr++] = MISSING_VAL ;
		} else {
			x[iftr++] = lines[XIDX(iline,SMX_COL,ncols)] ;
			if (SMX_NCOLS > 1)
				x[iftr++] = lines[XIDX(iline,SMX_COL+1,ncols)] ;					
			if (SMX_NCOLS > 2)
				x[iftr++] = lines[XIDX(iline,SMX_COL+2,ncols)] ;
			for (int k=3; k<SMX_NCOLS; k++)
				x[iftr++] = MISSING_VAL ;
		}
	}

	// Quantitative smoking
	if (fflags->qty_smx) {
		for (int k = 0; k < QTY_SMX_NCOLS; k++) {
			double val = lines[XIDX(iline,QTY_SMX_COL + k,ncols)]; 
			x[iftr++] = (val == missing_val) ? MISSING_VAL : val;
		}
	}

	// BMI
	if (fflags->bmi) {
		if (lines[XIDX(iline,BMI_COL,ncols)] == missing_val) {
			for (int k=0; k<BMI_NCOLS; k++)
				x[iftr++] = MISSING_VAL ;
		} else {
			x[iftr++] = lines[XIDX(iline,BMI_COL,ncols)] ;
			x[iftr++] = lines[XIDX(iline,BMI_COL+1,ncols)] ;
			for (int k=2; k<BMI_NCOLS; k++)
				x[iftr++] = MISSING_VAL ;
		}
	}

	// Binary History Flag
	if (fflags->binary_history) 
		x[iftr++] = (iline == first) ? 0 : 1 ;

	// Extra Features
	for (int i=0; i<NEXTRA; i++) {
		if (fflags->extra[i])
			x[iftr++] = lines[XIDX(iline,EXTRA_COL+i,ncols)] ;
	}
	 
	if (iftr!=nftrs) {
		fprintf(stderr, "ASSERT: iftr=%d   nftrs=%d\n", iftr, nftrs);
		assert(iftr==nftrs);
	}
	return iftr ;

}

// Get features for a given parameter
void get_features(double *lines, int *days, int first, int iline, int icol, int ncols, double *x, int *iftr, bins_lm_model *all_model, double *tempx, float missing_val, int no_random) {


	// First values - last given value and time gap since that value
	double present_value=0;
	int found=0;
	
	int found_line = iline;
	for (int j1=iline; j1>=first; j1--) {

		if (lines[XIDX(j1,TEST_COL+icol,ncols)]!=missing_val) {
			found=1;
			found_line = j1;
			present_value = lines[XIDX(j1,TEST_COL+icol,ncols)]; 
				
			// Gap from time value was actually measures to current time
			int days_gap = (days[iline]-days[j1])/180+1; 
			if (days[iline]-days[j1]<10) 
				days_gap = 0;
			
			if (days_gap>4) {
				days_gap = 4;
				present_value = get_default_value(lines,TEST_COL+icol,first,iline, found_line-1, days,days[iline],ncols,all_model,tempx);
			}

			x[(*iftr)++] = present_value;
			x[(*iftr)++] = days_gap; 

			break;
		}
	}

	// No Value given
	if (found==0) {
		present_value = get_default_value(lines,TEST_COL+icol,first,iline,found_line-1, days, days[iline],ncols,all_model,tempx);
		x[(*iftr)++] = present_value;
		x[(*iftr)++] = 5 ; 
	}

	// Additional values - median of base values + 2 interpolated values
	double base_value=0;
	double base_value2=0,base_value3=0 ;
	double diff=0;
			 
	found=0;
	int new_found_line=first;

	vector<pair<int, double> > values ;
	for(int j1=first; j1<found_line; j1++) {
		if (lines[XIDX(j1,TEST_COL+icol,ncols)]!=missing_val) {

			found=1;
			new_found_line = j1;

			int days_gap = days[found_line]-days[new_found_line];
			if ((values.size()) && (days_gap<MAXDAYS))
				break;

			pair<int,double> value(days_gap,lines[XIDX(j1,TEST_COL+icol,ncols)]) ;
			values.push_back(value) ;
			
			if (values.size()>=100 || days_gap<MAXDAYS) 
				break;		 
		}
	}

	if (found==1) {
		sort(values.begin(),values.end(),compare_pairs()) ;
		int idx1 = ((int) values.size())/2 ;
		int idx2 = ((int) values.size() - 1)/2 ;
		base_value = (values[idx1].second + values[idx2].second)/2.0;
		diff = (values[idx1].first + values[idx2].first)/2 ;

		if (diff>MAXDAYS) 
			diff=MAXDAYS;
		
		x[(*iftr)++] =(present_value-base_value)/(diff+ADDDAYS);

		for (int igap=0; igap<ngaps; igap++) {
			double value = get_value_from_all_model_no_current(lines,TEST_COL+icol,first,iline, iline-1,days,days[iline]-gaps[igap],ncols,all_model,tempx,missing_val);
			x[(*iftr)++] = (present_value-value) ;
		}
	} else {
		double value = get_default_value(lines,TEST_COL+icol,first,iline, found_line-1, days,days[iline],ncols,all_model,tempx);
		diff = MAXDAYS ;

		x[(*iftr)++] =(present_value-value)/(diff+ADDDAYS);
		for (int igap=0; igap<ngaps; igap++) {
			base_value = get_value_from_all_model(lines,TEST_COL+icol,first,iline,days,days[iline]-gaps[igap],ncols,all_model,tempx,missing_val,no_random);
			x[(*iftr)++] = (present_value-base_value) ;
		}
	}
				 
	return ;
}

// Check that a sample is valid
int is_valid_sample(double *line, feature_flags *fflags, int *req_tests, int nreq_tests, float missing_val) {

	for (int i=0; i<nreq_tests; i++) {
		if (line[TEST_COL+req_tests[i]] == missing_val)
			return 0 ;
	}

	return 1 ;
}

// Clup and Filter lines - clip values and remove lines with too many outliers
int clip_and_filter_x_line(double *line, feature_flags *fflags, double *min, double *max, float missing_val) {

	int nclipped = 0 ;		


	for(int j=0; j<NCBC ;j++)	{
		if (fflags->cbcs[j]) {
			if (line[TEST_COL+j]!=missing_val) {
				if (line[TEST_COL+j] < min[TEST_COL+j] - EPS) {
					line[TEST_COL+j] = min[TEST_COL+j] ;
					nclipped ++ ;
				} else if (line[TEST_COL+j] > max[TEST_COL+j] + EPS) {
					line[TEST_COL+j] = max[TEST_COL+j] ;
					nclipped ++ ;
				}
			}
		}
	}

	for (int j=0; j<NBIOCHEM; j++) {
		if (fflags->biochems[j]) {
			if (line[TEST_COL+NCBC+j]!=missing_val) {
				if (line[TEST_COL+NCBC+j] < min[TEST_COL+NCBC+j] - EPS) {
					line[TEST_COL+NCBC+j] = min[TEST_COL+NCBC+j] ;
					if(j<NBASIC_BIOCHEM) //DEBUG dont count missing for last 7 biochems
						nclipped ++ ;
				} else if (line[TEST_COL+NCBC+j] > max[TEST_COL+NCBC+j] + EPS) {
					line[TEST_COL+NCBC+j] = max[TEST_COL+NCBC+j] ;
					if(j<NBASIC_BIOCHEM) //DEBUG dont count missing for last 7 biochems
						nclipped ++ ;
				}
			}
		}
	}

	if (nclipped > MAX_CLIPPED)
		return 1 ;
	else
		return 0 ;
}

void filter_x_lines_by_age(double lines[], int *days, int *countable, int *nlines, int ncols) {

	int n = *nlines ;

	int out_n = 0 ;
	for (int i=0 ; i<n; i++) {
		int age = ((int) lines[XIDX(i, DATE_COL, ncols)])/10000 - ((int) lines[XIDX(i, BDATE_COL, ncols)])/10000 ;
		if (age >= MIN_LAB_AGE) {
			for (int j=0; j<ncols; j++)
				lines[XIDX(out_n,j,ncols)] = lines[XIDX(i,j,ncols)] ;
			days[out_n] = days[i] ;
			countable[out_n] = countable[i] ;
			out_n ++ ;
		} 
	}

	*nlines = out_n ;
	return ;
}

void clip_and_filter_x_lines(double lines[], int *days, int *countable, int *nlines, int ncols, feature_flags *fflags, cleaner& cln, float missing_val) {

	int n = *nlines ;

	if (cln.mode == 0) {		

		if (clip_and_filter_x_line(lines+(n-1)*ncols,fflags,cln.data_min,cln.data_max,missing_val) == 1) {
			*nlines = 0 ;
		} else {

			int out_n = 0 ;
			for (int i=0 ; i<n-1; i++) {
				if (clip_and_filter_x_line(lines+i*ncols,fflags,cln.data_min,cln.data_max,missing_val) == 0) {
					for (int j=0; j<ncols; j++)
						lines[XIDX(out_n,j,ncols)] = lines[XIDX(i,j,ncols)] ;
					days[out_n] = days[i] ;
					countable[out_n] = countable[i] ;
					out_n ++ ;
				} 
			}

			for (int j=0; j<ncols; j++)
				lines[XIDX(out_n,j,ncols)] = lines[XIDX(n-1,j,ncols)] ;
			days[out_n] = days[n-1] ;
			countable[out_n] = countable[n-1] ;

			*nlines = out_n + 1 ;
		}
	
	} else {
		map<int,pair<int,int> > ftrs_counters ;
		vector<int> lines_counters ;
		cln_from_moments(lines,ncols,0,n-1,cln.data_avg,cln.data_std,cln.data_min,cln.data_max,missing_val,MAX_SDVS_FOR_CLPS,MAX_SDVS_FOR_NBRS,ftrs_counters,lines_counters) ;

		if (lines_counters[n-1] >MAX_CLIPPED) {
			*nlines=0 ;
		} else {
			int out_n = 0 ;
			for (int i=0 ; i<n-1; i++) {
				if (lines_counters[i]<=MAX_CLIPPED) {
					for (int j=0; j<ncols; j++)
						lines[XIDX(out_n,j,ncols)] = lines[XIDX(i,j,ncols)] ;
					days[out_n] = days[i] ;
					countable[out_n] = countable[i] ;
					out_n ++ ;
				} 
			}

			for (int j=0; j<ncols; j++)
				lines[XIDX(out_n,j,ncols)] = lines[XIDX(n-1,j,ncols)] ;
			days[out_n] = days[n-1] ;
			countable[out_n] = countable[n-1] ;
			*nlines = out_n + 1 ;
		}
	}

	return ;


}

int check_date_ptrn(int *days, int num_dates, int num_date_ptrn_segs, int *bgn_date_ptrn_segs, int *end_date_ptrn_segs, int *date_ptrn_inds, int max_history_days_opt) { 

	// None of the history options were specified, therefore all blood tests are included
	if (num_date_ptrn_segs == 0 && max_history_days_opt == -1) {	
			for (int i = 0; i < num_dates; i++) date_ptrn_inds[i] = i;
			return num_dates;
	}

	int num_date_ptrn_inds = 0;
	int curr = days[num_dates - 1];
	int idate = 0;

	// If max_history_days is specified, all tests up to max_history_days back are included, and history_ptrn is ignored
	if (max_history_days_opt > -1) {	
		while (idate < num_dates && curr - days[idate] > max_history_days_opt) idate++; // jump over all tests out of time range
		while (idate < num_dates) {
			date_ptrn_inds[num_date_ptrn_inds] = idate;
			idate++;
			num_date_ptrn_inds++;
		}
		return num_date_ptrn_inds;				
	}

	if (num_dates < num_date_ptrn_segs) 
		return 0;

	// Using history_ptrn option
	// Going backwards over dates, starting with current date, trying to match each record into date pattern segments
	idate = num_dates - 1;
	int iseg = 0;

	while (iseg < num_date_ptrn_segs && idate >= 0) {
		int date_diff = curr - days[idate];
		/* fprintf(stderr, "iseg=%d, idate=%d, date_diff=%d\n", iseg, idate, date_diff); */
		if (date_diff > end_date_ptrn_segs[iseg]) {
			/* fprintf(stderr, "No matching date in segment %d\n", iseg); */
			return 0;	
		}
		if (date_diff < bgn_date_ptrn_segs[iseg]) {
			/* fprintf(stderr, "Skipping index %d - segment already matched or out of any segment\n", idate); */
			idate--;
		}
		if (date_diff >= bgn_date_ptrn_segs[iseg] && date_diff <= end_date_ptrn_segs[iseg]) {
			/* printf(stderr, "Adding index %d for segment %d\n", idate, iseg); */
			date_ptrn_inds[num_date_ptrn_segs - num_date_ptrn_inds - 1] = idate;
			num_date_ptrn_inds++;
			iseg++;
			idate--;
		}
	}

	if (num_date_ptrn_inds < num_date_ptrn_segs) { // not all segments were matched
		/* fprintf(stderr, "Only %d out of %d segments were filled\n", num_date_ptrn_inds, num_date_ptrn_segs);  */
		return 0;
	}

	/* fprintf(stderr, "All %d segments were filled by %d dates\n", num_date_ptrn_segs, num_date_ptrn_inds); */
	return num_date_ptrn_segs;
}


// Create X and Y.
// First parameter = indicator if in prediction mode . If so, no Y is created.
int get_x_and_y(int prediction, matrixLinesType lines, int nlines, bins_lm_model *all_models, const programParamStrType& ps,xy_data *xy,  
				int last_pos_day, feature_flags *fflags, int take_all_flag, int filter_flag, cleaner& cln, int date_ptrn_opt, int max_history_days_opt, int apply_age_filter) 
{

	float missing_val = MISSING_VAL ;

	int ncols = MAXCOLS ;
	int npatients = 1 ;

	for (int i=1; i<nlines; i++) {
		if (lines[i][ID_COL] != lines[i-1][ID_COL])
			npatients++ ;
	}
	fprintf(stderr,"No. of patients = %d\n",npatients) ;

	xy->nftrs = get_nftrs(fflags) ;
	fprintf(stderr,"No. of features = %d\n",xy->nftrs) ;

	// Prepare required fields (In Prediction Mode)
	int local_nreq_test_num = 0 ;
	int local_req_sets[NTESTS] ;
	if (prediction) {
		for (int i=0; i<NREQ_TEST_NUM; i++) {
			int itest = req_sets[i] ;
			if ((itest < NCBC && fflags->cbcs[itest]) || (itest < NCBC + NBIOCHEM && itest>=NCBC && fflags->biochems[itest-NCBC]))
				local_req_sets[local_nreq_test_num++] = itest ;
			else
				fprintf(stderr,"WARNING: Test %d required but not in features list. Ignored\n",itest) ;
		}

		if (local_nreq_test_num != NREQ_TEST_NUM)
			fprintf(stderr,"Original required sets altered due to features list\n") ;	
	}

	int max_periods = get_max_periods() ;

	// Set date pattern segments according to chosen date_ptrn option (In Predictin Mode)
	switch (date_ptrn_opt) {
	case 0: // use all tests; segments not used
		break;  
	case 4:
		bgn_date_ptrn_segs[3] = 721;
		end_date_ptrn_segs[3] = 1080;
		num_date_ptrn_segs++;
	case 3:
		bgn_date_ptrn_segs[2] = 361;
		end_date_ptrn_segs[2] = 720;
		num_date_ptrn_segs++;
	case 2:	
		bgn_date_ptrn_segs[1] = 91;
		end_date_ptrn_segs[1] = 360;
		num_date_ptrn_segs++;
	case 1:
		bgn_date_ptrn_segs[0] = 0;
		end_date_ptrn_segs[0] = 0;
		num_date_ptrn_segs++;
		break;
	default:
		fprintf(stderr, "Wrong date_ptrn option %d in get_x_matrix\n", date_ptrn_opt);
		return -1;
	}

	// Print info about history related options
	fprintf(stderr, "Max. days of history option set to %d\n", max_history_days_opt);
	if (date_ptrn_opt > 0) {
		fprintf(stderr, "Segments for date_ptrn option %d (%d):", date_ptrn_opt, num_date_ptrn_segs);
		for (int iseg = 0; iseg < num_date_ptrn_segs; iseg++) {
			fprintf(stderr, "\t%d - %d", bgn_date_ptrn_segs[iseg], end_date_ptrn_segs[iseg]);
		}
		fprintf(stderr, "\n");	
	}
	else fprintf(stderr, "History pattern option set to 0\n");
	
	
	int *cnts = (int *) malloc(nperiods*sizeof(int)) ;
	int *missing_tests = (int *) malloc(nlines*sizeof(int)) ;
	int *days = (int *) malloc(nlines*sizeof(int)) ;
	int *cancer_discovery = (int *) malloc(nlines*sizeof(int)) ;
	int *countable = (int *) malloc(nlines*sizeof(int)) ;
	double *tempx = (double *) malloc(max_periods*sizeof(double)) ;

	xy->x = NULL ;
	xy->y = NULL ;
	xy->idnums = NULL ;
	xy->flags = NULL ;
	xy->dates = NULL ;
	xy->censor = NULL ;

	if (days==NULL || cancer_discovery==NULL || missing_tests==NULL || cnts==NULL || countable == NULL || tempx==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for(int i=0; i<nlines; i++) {
		days[i] = get_day((int)(lines[i][DATE_COL]+0.5)) ;

		if (! prediction)
			cancer_discovery[i] = get_day((int)(lines[i][CANCER_DATE_COL]+0.5)) ;

		missing_tests[i] = 0 ;
		for (int j=0; j<NCBC; j++) {
			if (lines[i][TEST_COL+j] == missing_val && fflags->cbcs[j])
				missing_tests[i]++ ;
		}

		countable[i] = 0 ;
		for (int j=0; j<NCBC; j++) {
			if (lines[i][TEST_COL+j] != missing_val && fflags->cbcs[j])
				countable[i] = 1 ;
		}

		for (int j=0; j<NBIOCHEM; j++) {
			if (lines[i][TEST_COL+NCBC+j]!= missing_val && fflags->biochems[j])
				countable[i] = 1 ;
		}
	}

	int irow = 0 ;
	int first = 0 ;
	int nblocks = 0 ;

	for (int iline=0; iline < nlines; iline++) {

		int idnum = (int) lines[iline][ID_COL];
		int prev_idnum = (int) lines[first][ID_COL] ;

		if (idnum != prev_idnum)
			first = iline ;

		// Filtering
		// Age Filtering
		if (!prediction || apply_age_filter) {
			int age = ((int) lines[iline][DATE_COL])/10000 - ((int) lines[iline][BDATE_COL])/10000 ;
			if (age < MIN_AGE || age > MAX_AGE) {
				fprintf(ps.logFile,"Ignoring %d@%d for Age = %d\n",idnum,(int) lines[iline][DATE_COL],age) ;
				continue ;
			}
		}

		// Learning Mode - Registry Dependent Filtering
		int cancer_type,cancer_stage ;
		if (!prediction) {	
			if (lines[iline][CANCER_COL] < 0) {
				fprintf(ps.logFile,"Ignoring %d@%d for cancer-registery %f\n",idnum, (int) lines[iline][DATE_COL], lines[iline][CANCER_COL]) ;
				continue ;
			}

			cancer_type = (int) (lines[iline][CANCER_COL] + 0.01) ;
			cancer_stage = (int) (10 * (lines[iline][CANCER_COL] - cancer_type) + 0.5) ;
			if (cancer_type < 0 || cancer_type > 3 || ((!take_all_flag) && cancer_type > 2)) {
				fprintf(ps.logFile,"Ignoring %d@%d for cancer-registery %d\n",idnum, (int) lines[iline][DATE_COL], cancer_type) ;
				continue ;
			}

			// removing tests that are done after the date for which the available registry is expected to provide a nearly complete information
			// note: this was done before only for negative cases; applied to positive cases as well in order to prevenet imbalance in take_samples()
			if (days[iline] > last_pos_day) {
				fprintf(ps.logFile,"Ignoring %d@%d for out-of-registrar\n",idnum,(int) lines[iline][DATE_COL]) ;
				continue ;
			}

			if (missing_tests[iline] >= MAX_MISSING_TESTS) {
				fprintf(ps.logFile,"Ignoring %d@%d for not-enough-CBC-results\n",idnum,(int) lines[iline][DATE_COL]) ;
				continue ;
			}
		}



		// Check if dates from first to iline meet the requested pattern and select the relevant dates
		int *date_ptrn_inds = (int *) malloc( (iline - first + 1) * sizeof(int) );
		
		
		int num_date_ptrn_inds = check_date_ptrn(days + first, iline - first + 1, num_date_ptrn_segs, bgn_date_ptrn_segs, end_date_ptrn_segs, date_ptrn_inds, max_history_days_opt);
		if (num_date_ptrn_inds == 0) {
			fprintf(ps.logFile, "Ignoring %d@%d for not-matching-required-date-pattern\n", idnum, (int) lines[iline][DATE_COL]) ;
			continue;
		}

		fprintf(ps.logFile, "Using %d@%d for passing-all-filters\n", idnum, (int) lines[iline][DATE_COL]) ;

		// Re-allocation
		if (irow+1 >= nblocks*BLOCK_LINES) {
			nblocks++ ;

			fprintf(stderr,"Allocating block #%d (%d/%d)\n",nblocks,iline,nlines) ;
			(xy->x) = (double *) realloc(xy->x,(xy->nftrs)*nblocks*BLOCK_LINES*sizeof(double)) ;
			(xy->idnums) = (int *) realloc(xy->idnums,nblocks*BLOCK_LINES*sizeof(int)) ;
			(xy->dates) = (int *) realloc(xy->dates,nblocks*BLOCK_LINES*sizeof(int)) ;
			if (xy->x==NULL || xy->idnums==NULL || xy->dates==NULL) {
				fprintf(stderr,"Reallocation at block %d failed\n",nblocks) ;
				return -1 ;
			}			

			if (! prediction) {
				(xy->y) = (double *) realloc(xy->y,nblocks*BLOCK_LINES*sizeof(double)) ;
				(xy->flags) = (int *) realloc(xy->flags,nblocks*BLOCK_LINES*sizeof(int)) ;
				(xy->censor) = (int *) realloc(xy->censor,nblocks*BLOCK_LINES*sizeof(int)) ;

				if (xy->y==NULL || xy->flags==NULL || xy->censor==NULL) {
					fprintf(stderr,"Reallocation at block %d failed\n",nblocks) ;
					return -1 ;
				}
			}
		}

		// Filling
		(xy->idnums)[irow] = idnum ;
		(xy->dates)[irow] = (int) lines[iline][DATE_COL] ;

		int tmp_nlines = num_date_ptrn_inds; // (nline -first + 1) if all dates are used, i.e. date_ptrn_opt is 0

		double *tmp_lines = (double *) malloc( tmp_nlines * ncols * sizeof(double) );
		int *tmp_days = (int *) malloc( tmp_nlines * sizeof(int) );
		int *tmp_countable = (int *) malloc( tmp_nlines * sizeof(int) );

		if (tmp_lines==NULL || tmp_days==NULL || tmp_countable==NULL) {
			fprintf(stderr,"Allocation of temporary arrays at irow %d for lines %d -- %d (%zd,%zd,%zd) failed\n", irow, first, iline,tmp_nlines * ncols * sizeof(double)
				,tmp_nlines * sizeof(int),tmp_nlines * sizeof(int)) ;
			return -1 ;
		}

		for (int tmp_i = 0; tmp_i < tmp_nlines; tmp_i++) {

			int src_i = first + date_ptrn_inds[tmp_i]; // (first + tmp_i) if date_ptrn_opt is 0
			memcpy(tmp_lines + tmp_i * ncols,lines + src_i , ncols * sizeof(double));
			tmp_days[tmp_i] = days[src_i];
			tmp_countable[tmp_i] = countable[src_i];

		}
		free(date_ptrn_inds);

		// Filter tmp_lines - remove lab tests from age under 18
		int in_nlines = tmp_nlines;
		filter_x_lines_by_age(tmp_lines,tmp_days,tmp_countable,&tmp_nlines,ncols) ;
		if (tmp_nlines == 0)
			fprintf(ps.logFile,"Ignoring %d@%d for illegal ages at lab dates\n",idnum,(int) lines[iline][DATE_COL]) ;
		else if (tmp_nlines != in_nlines) {
			fprintf(ps.logFile,"Changing history of %d@%d for illegal ages at lab dates\n",idnum,(int) lines[iline][DATE_COL]) ;
		}

		// Filter tmp_lines - remove lines with too many outliers
		if (tmp_nlines > 0 && filter_flag) {
			int in_nlines = tmp_nlines ;
			clip_and_filter_x_lines(tmp_lines,tmp_days,tmp_countable,&tmp_nlines,ncols,fflags,cln,missing_val) ;

			if (tmp_nlines == 0)
				fprintf(ps.logFile,"Ignoring %d@%d for too many clippings\n",idnum,(int) lines[iline][DATE_COL]) ;
			else if (tmp_nlines != in_nlines) {
				fprintf(ps.logFile,"Changing history of %d@%d for too many clippings\n",idnum,(int) lines[iline][DATE_COL]) ;
			}
		}


		// Fill the matrix
		if (tmp_nlines > 0) {
			// Complete dependent values, again ...
			complete_dependent_transformed(tmp_lines, tmp_nlines, ncols, cln, missing_val);

			if (!prediction || is_valid_sample(tmp_lines+(tmp_nlines-1)*ncols,fflags,local_req_sets,local_nreq_test_num,missing_val)) {
				int iftr = get_x_line(tmp_lines, tmp_nlines - 1, 0, ncols, tmp_days, tmp_countable, all_models, tempx, cnts, fflags, xy->nftrs, (xy->x) + irow*(xy->nftrs),missing_val,prediction) ;

				// Flagging and Labeling
				if (! prediction) {
					int status = (int) (lines[iline][STATUS_COL] + 0.5) ;
					(xy->censor)[irow] = (status == 2) ? ((int) lines[iline][STATUS_DATE_COL]) : -1 ;

					if ((cancer_type>=1) && (cancer_type<=2))
						(xy->y)[irow] = 1.0 ;
					else if (cancer_type==0)
						(xy->y)[irow] = 0.0 ;
					else
						(xy->y)[irow] = 2.0 ;

					// Flagging
					if ((cancer_type==1 || cancer_type==2) && (cancer_discovery[iline] < days[iline] + ps.startPeriod || cancer_discovery[iline] > days[iline] + ps.endPeriod)) {
						fprintf(ps.logFile,"Flagging %d@%d for out-of-period cancer at %d \n",idnum,(int) lines[iline][DATE_COL],(int) lines[iline][CANCER_DATE_COL]) ;
						(xy->flags)[irow] = 0 ;
					} 
					else
						(xy->flags)[irow] = 1 ;

					fprintf(ps.logFile,"Labeling %d@%d as %d %d\n",idnum, (int) lines[iline][DATE_COL],(int) ((xy->y)[irow]),(xy->flags)[irow]) ;
				}				

				irow ++ ;
			} else
				fprintf(ps.logFile,"Ignoring %d@%d for invalid sample\n",idnum,(int) lines[iline][DATE_COL]) ;
		}

		// Free temporary arrays
		free(tmp_lines);
		free(tmp_days);
		free(tmp_countable);		
	}

	xy->nrows = irow ;

	free(days) ;

	(xy->x) = (double *) realloc(xy->x,(xy->nftrs)*(xy->nrows)*sizeof(double)) ;

	if (!prediction) {
		free(cancer_discovery) ;
		free(countable) ;
		(xy->y) = (double *) realloc(xy->y,(xy->nrows)*sizeof(double)) ;
	}

	if ((xy->nrows)>0 && (xy->x==NULL || ((!prediction) && xy->y==NULL))) {
		fprintf(stderr,"Reallocation at end failed\n") ;
		return -1 ;
	} else
		return 0 ;
}



int get_xy(matrixLinesType lines, int nlines, programParamStrType& ps,xy_data *xy,int last_pos_day, feature_flags *fflags, int take_all_flag, int cln_mode) 
{

	int npatients = 1 ;

	for (int i=1; i<nlines; i++) {
		if (lines[i][ID_COL] != lines[i-1][ID_COL])
			npatients++ ;
	}
	fprintf(stderr,"No. of patients = %d\n",npatients) ;

	// Build Local Predictors
	bins_lm_model all_models[NCBC+NBIOCHEM] ;

	if (ps.use_completions) {
		// read from file
		fprintf(stderr,"##>> use_completions is on, hence reading models directly from file\n");
		if (read_init_params(ps.completionParamsFile,all_models,fflags->cbcs,fflags->biochems) == -1) {
			fprintf(stderr,"Cannot read initial params\n") ;
			return -1 ;
		}
	} else {
		if (build_bins_lm_models((linearLinesType)&lines[0][0],nlines,MAXCOLS,fflags,all_models,npatients,MISSING_VAL,ps.completionParamsFile) == -1) {
			fprintf(stderr,"Failed building bins_lm_models\n") ;
			return -1 ;
		}
	}


	if (ps.only_completions) {
		fprintf(stderr,"##>> only_completions is on. Exiting\n") ;
		return 0 ;
	}


	cleaner dummy ;
	dummy.mode = cln_mode ;
	dummy.data_avg = dummy.data_std = dummy.data_min = dummy.data_max = dummy.ftrs_min = dummy.ftrs_max = NULL;
	return get_x_and_y(0,lines,nlines,all_models,ps,xy,last_pos_day,fflags,take_all_flag,0,dummy,0,-1,0) ; 
}

void get_all_cols(feature_flags *fflags, map<string,int>& cols) {

	int itest = 0 ;
	int icol = fflags->gender;
	for (int i=0; i<NCBC; i++) {
		if (fflags->cbcs[i]) {
			cols[test_names[itest]] = icol ;
			icol += (ngaps + 3 + 2*fflags->minmax) ;
		}
		itest++ ;
	}

		for (int i=0; i<NBIOCHEM; i++) {
		if (fflags->biochems[i]) {
			cols[test_names[itest]] = icol ;
			icol += (ngaps + 3 + 2*fflags->minmax) ;
		}
		itest++ ;
	}

	itest++ ;

	if (fflags->age)
		cols["Age"] = icol ;

	return ;
}

int get_cv_gbm_predictions(xy_data *xy, double *preds , int nfold, gbm_parameters *gbm_params, int age_col) {

	// Do CV (Required for combinations methods)
	int npatients = 1 ;
	for (int i=1; i<xy->nrows; i++) {
		if ((xy->idnums)[i] != (xy->idnums)[i-1])
			npatients++ ;
	}
	fprintf(stderr,"Npatients = %d\n",npatients) ;

	int bin_size = ((xy->nrows)+nfold-1)/nfold ;

	int *order = randomize(xy->nrows) ;
	if (order == NULL) {
		fprintf(stderr,"shuffling failed\n") ;
		return -1 ;
	}

	for (int ifold=0; ifold<nfold; ifold++) {
		fprintf(stderr,"Fold No. %d/%d ... ",ifold+1,nfold) ;

		int test_start = ifold * bin_size ;
		int test_end = (ifold + 1)*bin_size - 1 ;
		if (ifold == nfold - 1)
			test_end = (xy->nrows) - 1 ;

		// Split
		xy_data xy1,xy2 ;
		init_xy(&xy1) ;
		init_xy(&xy2) ;

		// Splitting
		if (get_split_data(xy,npatients,&xy1,&xy2,order,test_start,test_end) == -1) {
			fprintf(stderr,"Splitting to Learning+Test sets failed\n") ;
			return -1 ;
		}

		// Create age-paired matrix
		xy_data pxy ;
		init_xy(&pxy) ;

		fprintf(stderr,"Age Pairing :\n") ;
		if (get_paired_matrix(&xy1,age_col,1.0,MATCHING_W,&pxy) == -1) {
			fprintf(stderr,"Cannot get paired matrix\n") ;
			return -1 ;
		}
		fprintf(stderr,"Nrows: %d->%d\n",xy1.nrows,pxy.nrows) ;

		// Learn
		fprintf(stderr,"Learning ...\n") ;
		gbm_tree *trees = allocate_gbm_trees(gbm_params->ntrees) ;
		if (trees==NULL) {
			fprintf(stderr,"GBM allocation failed\n") ;
			return -1 ;
		}

		double initF ;
		int **rcSplits ;
		int *rcSplitSizes ;
		int ncSplits ;

		int npos = 0, nneg = 0 ;
		for (int i=0; i<pxy.nrows; i++) {
			if ((pxy.y)[i] > 0)
				npos ++ ;
			else
				nneg ++ ;
		}
		fprintf(stderr,"Learning on %d + %d\n",npos,nneg) ;
		if (get_gbm_predictor(pxy.x,pxy.y,pxy.w,pxy.nrows,pxy.nftrs,gbm_params->shrinkage,gbm_params->bag_p,gbm_params->take_all_pos,gbm_params->ntrees,gbm_params->depth,
			gbm_params->min_obs_in_node, trees,&initF,&rcSplits,&rcSplitSizes,&ncSplits)==-1) {
				fprintf(stderr,"GBM learning failed\n") ;
				return -1 ;
		}

		// Predict	
		fprintf(stderr,"Predicting\n") ;
		if (gbm_predict(xy2.x,xy2.nrows,xy2.nftrs,trees,gbm_params->ntrees,initF,rcSplits,preds+test_start)==-1) {
			fprintf(stderr,"GBM prediction failed\n") ;
			return -1 ;
		}

		clear_xy(&pxy) ;
		clear_xy(&xy1) ;
		clear_xy(&xy2) ;
	}
	free(order) ;

	return 0 ;
}


int get_x_matrix(matrixLinesType lines, int nlines,programParamStrType& ps, xy_data *xy, feature_flags *fflags, int mftrs, int filter_flag, cleaner& cln, int apply_age_filter) {

	float missing_val = MISSING_VAL ;

	// Sanity check
	if (get_nftrs(fflags) > mftrs) {
		fprintf(stderr,"Too many features : %d > %d\n",get_nftrs(fflags),mftrs) ;
		return -1 ;
	}

	int npatients = 1 ;
	for (int i=1; i<nlines; i++) {
		if (lines[i][ID_COL] != lines[i-1][ID_COL])
			npatients++ ;
	}
	fprintf(stderr,"No. of patients = %d\n",npatients) ;

	// Read/Build Local Predictors
	bins_lm_model all_models[NCBC+NBIOCHEM] ;
	int ncbc=0;
	if (ps.autoCompletionFlag) {
		for (int i=0; i<NCBC; i++) {
			if (fflags->cbcs[i]) {
				ncbc++;
				fprintf(stderr,"Building \'all\' model for test %d\n",i) ;
				if (get_all_model((linearLinesType)lines,nlines,TEST_COL+i,all_models+i,npatients,MAXCOLS,missing_val) != 0)
					return -1 ;
			}
		}
		for (int i=0; i<NBIOCHEM; i++) {
			if (fflags->biochems[i]) {
				fprintf(stderr,"Building biochem \'all\' model for test %d\n",i) ;
				if (get_all_model((linearLinesType)lines,nlines,TEST_COL+NCBC+i,all_models+NCBC+i,npatients,MAXCOLS,missing_val) != 0)
					return -1 ;
			}
		}
	} else  {
		if (read_init_params(ps.completionParamsFile,all_models,fflags->cbcs,fflags->biochems) == -1) {
			fprintf(stderr,"Cannot read initial params\n") ;
			return -1 ;
		}
	}


	return get_x_and_y(1,lines,nlines,all_models,ps,xy,0,fflags,0,filter_flag,cln,ps.history_pattern,ps.max_history_days,apply_age_filter) ; 
}



int get_paired_and_age_predictions(xy_data *xy1, xy_data *xy2, double *preds, gbm_parameters *gbm_params, int age_col) {


	gbm_parameters local_gbm_params ;
	set_gbm_parameters ("QuickCRC",&local_gbm_params) ;

	double *in_preds = (double *) malloc((xy1->nrows)*sizeof(double)) ;
	if (in_preds == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	// Get Cross-Validation GBM predictions 
	int nfolds = 10 ;
	fprintf(stderr,"Internal Cross Validation ...\n") ;
	if (get_cv_gbm_predictions(xy1,in_preds,nfolds,&local_gbm_params,age_col) == -1) {
		fprintf(stderr,"GBM internal cross validation failed\n") ;
		return -1 ;
	}

	// Full GBM on Paired-prediction + Original X
	double *extended = (double *) malloc((xy1->nrows)*((xy1->nftrs)+1)*sizeof(double)) ;
	if (extended == NULL) {
		fprintf(stderr,"LM Allocation failed\n") ;
		return -1 ;
	}

	memcpy(extended,xy1->x,(xy1->nrows)*(xy1->nftrs)*sizeof(double)) ;
	memcpy(extended+(xy1->nrows)*(xy1->nftrs),in_preds,(xy1->nrows)*sizeof(double)) ;

	gbm_tree *comb_trees = allocate_gbm_trees(gbm_params->ntrees) ;
	if (comb_trees==NULL) {
		fprintf(stderr,"GBM allocation failed\n") ;
		return -1 ;
	}

	double comb_initF ;
	int **comb_rcSplits ;
	int *comb_rcSplitSizes ;
	int comb_ncSplits ;

	for (int i=0; i<(xy1->nrows); i++)
		(xy1->w)[i] = 1.0 ;

	fprintf(stderr,"Combination GBM\n") ;
	int r_ncols = xy1->nftrs + 1;
	if (get_gbm_predictor(extended,xy1->y,xy1->w,xy1->nrows,r_ncols,gbm_params->shrinkage,gbm_params->bag_p,gbm_params->take_all_pos,gbm_params->ntrees,gbm_params->depth,
		gbm_params->min_obs_in_node,comb_trees,&comb_initF,&comb_rcSplits,&comb_rcSplitSizes,&comb_ncSplits)==-1) {
			fprintf(stderr,"GBM learning failed\n") ;
			return -1 ;
	}

	// Learn GBM on full age-paired matrix
	gbm_tree *trees = allocate_gbm_trees(local_gbm_params.ntrees) ;
	if (trees==NULL) {
		fprintf(stderr,"GBM allocation failed\n") ;
		return -1 ;
	}

	double initF ;
	int **rcSplits ;
	int *rcSplitSizes ;
	int ncSplits ;

	// Create age-paired matrix
	xy_data pxy ;
	init_xy(&pxy) ;

	if (get_paired_matrix(xy1,age_col,1.0,MATCHING_W,&pxy) == -1) {
		fprintf(stderr,"Cannot get paired matrix\n") ;
		return -1 ;
	}
	fprintf(stderr,"Nrows: %d->%d\n",xy1->nrows,pxy.nrows) ;


	fprintf(stderr,"Full Set GBM\n") ;
	if (get_gbm_predictor(pxy.x,pxy.y,pxy.w,pxy.nrows,pxy.nftrs,local_gbm_params.shrinkage,local_gbm_params.bag_p,local_gbm_params.take_all_pos,local_gbm_params.ntrees,
		local_gbm_params.depth,local_gbm_params.min_obs_in_node,trees,&initF,&rcSplits,&rcSplitSizes,&ncSplits)==-1) {
			fprintf(stderr,"GBM learning failed\n") ;
			return -1 ;
	}

	// Predict : 
	// GBM
	fprintf(stderr,"Predicting !\n") ;
	if (gbm_predict(xy2->x,xy2->nrows,xy2->nftrs,trees,local_gbm_params.ntrees,initF,rcSplits,preds)==-1) {
		fprintf(stderr,"GBM prediction failed\n") ;
		return -1 ;
	}

	// Second GBM
	double *extended2 = (double *) malloc((xy2->nrows)*(xy2->nftrs+1)*sizeof(double)) ;
	if (extended2 == NULL) {
		fprintf(stderr,"LM Allocation failed\n") ;
		return -1 ;
	}

	memcpy(extended2,xy2->x,(xy2->nrows)*(xy2->nftrs)*sizeof(double)) ;
	memcpy(extended2+(xy2->nrows)*(xy2->nftrs),preds,(xy2->nrows)*sizeof(double)) ;

	fprintf(stderr,"Combination Predicting !\n") ;
	if (gbm_predict(extended2,xy2->nrows,r_ncols,comb_trees,gbm_params->ntrees,comb_initF,comb_rcSplits,preds)==-1) {
		fprintf(stderr,"GBM prediction failed\n") ;
		return -1 ;
	}

	// Clear
	for (int i=0; i<ncSplits; i++)
		free(rcSplits[i]) ;
	free(rcSplits) ;
	free(rcSplitSizes) ;
	free_gbm_trees(trees) ;

	for (int i=0; i<comb_ncSplits; i++)
		free(comb_rcSplits[i]) ;
	free(comb_rcSplits) ;
	free(comb_rcSplitSizes) ;
	free_gbm_trees(comb_trees) ;

	free(extended2) ;
	free(extended) ;

	free(in_preds) ;
	clear_xy(&pxy) ;

	return 0 ;
}

// Optimize Age-dependent factors in probs
void optimize_age_dependence(double *labels, double *preds, int *ages, int n, double *factors) {

	double scores[MAX_AGE+1][AGE_DEP_RESOLUTION] ;

	for (int i=0; i<=MAX_AGE; i++) {
		for (int j=0; j<AGE_DEP_RESOLUTION; j++)
			scores[i][j] = 0 ;
	}

	// Score per age
	for (int i=0; i<n; i++) {
		for (int j=0; j<AGE_DEP_RESOLUTION; j++) {
			double prob = exp(2*preds[i])/(1+exp(2*preds[i])) ;
			prob *= (j+1.0)/AGE_DEP_RESOLUTION ;
			double score = 0.5*log(prob/(1-prob)) ;
			scores[ages[i]][j] += exp (-(2*labels[i]-1)*score) ;
		}
	}


	// Dynamic Programming
	double optimal_scores[MAX_AGE+1][AGE_DEP_RESOLUTION] ;
	int optimal_values[MAX_AGE+1][AGE_DEP_RESOLUTION] ;

	optimal_scores[MIN_AGE][0] = scores[MIN_AGE][0] ;
	optimal_values[MIN_AGE][0] = 0 ;

	for (int i=1; i<AGE_DEP_RESOLUTION ; i++) {
		if (scores[MIN_AGE][i] < optimal_scores[MIN_AGE][i-1]) {
			optimal_scores[MIN_AGE][i] = scores[MIN_AGE][i] ;
			optimal_values[MIN_AGE][i] = i ;
		} else {
			optimal_scores[MIN_AGE][i] = optimal_scores[MIN_AGE][i-1] ;
			optimal_values[MIN_AGE][i] = optimal_values[MIN_AGE][i-1] ;
		}
	}

	for (int j=MIN_AGE+1; j<=MAX_AGE; j++) {
		optimal_scores[j][0] = optimal_scores[j-1][0] + scores[j][0];
		optimal_values[j][0] = 1 ;

		for (int i=1; i<AGE_DEP_RESOLUTION ; i++) {
			double new_score = optimal_scores[j-1][i] + scores[j][i] ;
			if (new_score < optimal_scores[j][i-1]) {
				optimal_scores[j][i] = new_score ;
				optimal_values[j][i] = i ;
			} else {
				optimal_scores[j][i] = optimal_scores[j][i-1] ;
				optimal_values[j][i] = optimal_values[j][i-1] ;
			}
		}		
	}

	int idx = 0 ;
	double min_score = optimal_scores[MAX_AGE][idx] ;
	for (int i=1; i<AGE_DEP_RESOLUTION; i++) {
		if (optimal_scores[MAX_AGE][i] < min_score) {
			idx = i ;
			min_score = optimal_scores[MAX_AGE][i] ;
		}
	}

	int optimal_value = idx ;
	for (int j=MAX_AGE; j>=MIN_AGE; j--) {
		optimal_value = optimal_values[j][optimal_value] ;
		factors[j] = (optimal_value+1.0)/AGE_DEP_RESOLUTION ;
	}

	return;
}

int age_factor(double *probs, double *x, int nrows, int age_col, char *fname) {

	FILE *fp = safe_fopen(fname, "r", false) ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",fname) ;
		return -1 ;
	}

	double factors[MAX_AGE+1] ;
	int ival ;
	double dval ;
	int max_age = MIN_AGE ;
	int min_age = MAX_AGE ;

	while (! feof(fp)) {
		int rc = fscanf(fp,"%d %lf\n",&ival,&dval) ;
		if (rc == EOF)
			break ;

		if ( rc != 2 || ival < MIN_AGE || ival > MAX_AGE) {
			fprintf(stderr,"Cannot read from %s\n",fname) ;
			return -1 ;
		}

		if (dval > 0) {
			factors[ival]=dval ;

			if (ival > max_age)
				max_age = ival ;
			if (ival < min_age)
				min_age = ival ;
		}
	}
	fclose(fp) ;

	for (int i=MIN_AGE; i<min_age; i++)
		factors[i] = factors[min_age] ;
	for (int i=max_age+1; i<=MAX_AGE; i++)
		factors[i] = factors[max_age] ;

	for (int i=0; i<nrows; i++) {
//		int age = (int) (x[XIDX(age_col,i,nrows)] + 0.5) ;
		int age = (int)x[XIDX(age_col, i, nrows)];
		if (age > MAX_AGE)
			age = MAX_AGE ;
		else if (age < MIN_AGE) 
			age = MIN_AGE ;

		double prob = probs[i]*factors[age] ;
		probs[i] = 0.5*log(prob/(1-prob)) ; 
	}

	return 0 ;
}

// Handle dependency between paramteres
double round(double in, int accuracy) {
	return (((int) (accuracy*in + 0.5))/(0.0+accuracy)) ;
}

// Add dependent parameters
int complete_dependent(double *line, double missing) {

	int completed_test[NCBC] ;
	memset(completed_test,0,NCBC*sizeof(int)) ;

	int ncompleted = 0 ;
	int completed = 1 ;
	while (completed) {
		completed = 0 ;

		// MCV[5] = 10 * HCT[4] / RBC[0]
		if (line[0]!=missing && line[4]!=missing && line[5]==missing && line[0]!=0) {
			completed++ ;
			line[5] = round(10*line[4]/line[0],1000) ;
		} else if (line[0]!=missing && line[4]==missing && line[5]!=missing) {
			completed++ ;
			line[4] = round(line[0]*line[5]/10,1000) ;
		} else if (line[0]==missing && line[4]!=missing && line[5]!=missing && line[5]!=0) {
			completed++ ;
			line[0] = round(10*line[4]/line[5],1000) ;
		}

		// MCH[6] = 10 * HGB[3] / RBC [0]
		if (line[0]!=missing && line[3]!=missing && line[6]==missing && line[0]!=0) {
			completed++ ;
			line[6] = round(10*line[3]/line[0],1000) ;
		} else if (line[0]!=missing && line[3]==missing && line[6]!=missing) {
			completed++ ;
			line[3] = round(line[0]*line[6]/10,1000) ;
		} else if (line[0]==missing && line[3]!=missing && line[6]!=missing && line[6]!=0) {
			completed++ ;
			line[0] = round(10*line[3]/line[6],1000) ;
		}

		// MCHC[7] = 100 * HGB[3] / HCT[4]
		if (line[3]!=missing && line[4]!=missing && line[7]==missing && line[4]!=0) {
			completed++ ;
			line[7] = round(100*line[3]/line[4],1000) ;
		} else if (line[3]!=missing && line[4]==missing && line[7]!=missing && line[7]!=0) {
			completed++ ;
			line[4] = round(100*line[3]/line[7],1000) ;
		} else if (line[3]==missing && line[4]!=missing && line[7]!=missing) {
			completed++ ;
			line[3] = round(line[4]*line[7]/100,1000) ;
		}

		// WBC[1] = EOS#[10] + NEU#[15] + MON#[16] + BAS#[17] + LYMPH#[19]
		if (line[1]!=missing && line[10]!=missing && line[15]!=missing && line[16]!=missing && line[17]!=missing && line[19]==missing && !completed_test[19]) {
			completed++ ;
			line[19] = round(line[1] - line[10] - line[15] - line[16] - line[17],1000) ;
			if (line[19] < 0) {
				line[19] = missing ;
				completed_test[19] = 1 ;
			}
		} else if (line[1]!=missing && line[10]!=missing && line[15]!=missing && line[16]!=missing && line[17]==missing && line[19]!=missing && !completed_test[17]) {
			completed++ ;
			line[17] = round(line[1] - line[10] - line[15] - line[16] - line[19],1000) ;
			if (line[17] < 0) {
				line[17] = missing ;
				completed_test[17] = 1 ;
			}
		} else if (line[1]!=missing && line[10]!=missing && line[15]!=missing && line[16]==missing && line[17]!=missing && line[19]!=missing && !completed_test[16]) {
			completed++ ;
			line[16] = round(line[1] - line[10] - line[15] - line[17] - line[19],1000) ;
			if (line[16] < 0) {
				line[16] = missing ;
				completed_test[16] = 1 ;
			}
		} else if (line[1]!=missing && line[10]!=missing && line[15]==missing && line[16]!=missing && line[17]!=missing && line[19]!=missing && !completed_test[15]) {
			completed++ ;
			line[15] = round(line[1] - line[10] - line[16] - line[17] - line[19],1000) ;
			if (line[15] < 0) {
				line[15] = missing ;
				completed_test[15] = 1 ;
			}
		} else if (line[1]!=missing && line[10]==missing && line[15]!=missing && line[16]!=missing && line[17]!=missing && line[19]!=missing && !completed_test[10]) {
			completed++ ;
			line[10] = round(line[1] - line[15] - line[16] - line[17] - line[19],1000) ;
			if (line[10] < 0) {
				line[10] = missing ;
				completed_test[10] = 1 ;
			}
		} else if (line[1]==missing && line[10]!=missing && line[15]!=missing && line[16]!=missing && line[17]!=missing && line[19]!=missing) {
			completed++ ;
			line[1] = round(line[10] + line[15] + line[16] + line[17] + line[19],1000) ;
		}

		if (line[1] != 0) {

			// LYMPH%[18] = 100*LYMPH#[19]/WBC[1]
			if (line[1]!=missing && line[19]!=missing && line[18]==missing) {
				completed++ ;
				line[18] = round(100*line[19]/line[1],1000) ;
			} else if (line[1]!=missing && line[19]==missing && line[18]!=missing) {
				completed++ ;
				line[19] = round(line[1]*line[18]/100,1000) ;
			} else if (line[1]==missing && line[19]!=missing && line[18]!=missing && line[18]!=0) {
				completed++ ;
				line[1] = round(100*line[19]/line[18],1000) ;
			}

			// NEU%[11] = 100*NEU#[15]/WBC[1]
			if (line[1]!=missing && line[15]!=missing && line[11]==missing) {
				completed++ ;
				line[11] = round(100*line[15]/line[1],1000) ;
			} else if (line[1]!=missing && line[15]==missing && line[11]!=missing) {
				completed++ ;
				line[15] = round(line[1]*line[11]/100,1000) ;
			} else if (line[1]==missing && line[15]!=missing && line[11]!=missing && line[11]!=0) {
				completed++ ;
				line[1] = round(100*line[15]/line[11],1000) ;
			}

			// MON%[12] = 100*MON#[16]/WBC[1]
			if (line[1]!=missing && line[16]!=missing && line[12]==missing) {
				completed++ ;
				line[12] = round(100*line[16]/line[1],1000) ;
			} else if (line[1]!=missing && line[16]==missing && line[12]!=missing) {
				completed++ ;
				line[16] = round(line[1]*line[12]/100,1000) ;
			} else if (line[1]==missing && line[16]!=missing && line[12]!=missing && line[12]!=0) {
				completed++ ;
				line[1] = round(100*line[16]/line[12],1000) ;
			}

			// EOS%[13] = 100*EOS#[10]/WBC[1]
			if (line[1]!=missing && line[10]!=missing && line[13]==missing) {
				completed++ ;
				line[13] = round(100*line[10]/line[1],1000) ;
			} else if (line[1]!=missing && line[10]==missing && line[13]!=missing) {
				completed++ ;
				line[10] = round(line[1]*line[13]/100,1000) ;
			} else if (line[1]==missing && line[10]!=missing && line[13]!=missing && line[13]!=0) {
				completed++ ;
				line[1] = round(100*line[10]/line[13],1000) ;
			}

			// BAS%[14] = 100*BAS#[17]/WBC[1]
			if (line[1]!=missing && line[17]!=missing && line[14]==missing) {
				completed++ ;
				line[14] = round(100*line[17]/line[1],1000) ;
			} else if (line[1]!=missing && line[17]==missing && line[14]!=missing) {
				completed++ ;
				line[17] = round(line[1]*line[14]/100,1000) ;
			} else if (line[1]==missing && line[17]!=missing && line[14]!=missing && line[14]!=0) {
				completed++ ;
				line[1] = round(100*line[17]/line[14],1000) ;
			}
		}

		ncompleted += completed ;

	}

	return ncompleted;
}


int complete_dependent (double *lines, int nlines, int ncols, double missing) {

	int ncomlpeted = 0 ;
	for (int i=0; i<nlines; i++)
		ncomlpeted += complete_dependent(lines+i*ncols+TEST_COL,missing) ;

	return ncomlpeted;
}

int complete_dependent_transformed(double *lines, int nlines, int ncols, cleaner& cln, double missing) {

	int ncompleted = 0;
	double line[NCBC];

	for (int i = 0; i < nlines; i++) {
		// Exp
		for (int j = 0; j < NCBC; j++) {
			int idx = i*ncols + j + TEST_COL;
			if (lines[idx] != MISSING_VAL && log_cols[j])
				line[j] = exp(lines[idx]);
			else
				line[j] = lines[idx];
		}

		// Complete
		ncompleted += complete_dependent(line, missing);

		// Log
		for (int j = 0; j < NCBC; j++) {
			int idx = i*ncols + j + TEST_COL;
			if (line[j] != MISSING_VAL && log_cols[j]) {
				if (line[j] > 0)
					line[j] = log(line[j]);
				else if (lines[idx] == 0)
					line[j] = log(cln.min_orig_data[TEST_COL + j] / 2.0);
			}
			lines[idx] = line[j];
		}
	}

	return ncompleted;

}

// Remove all dependent parameters.
int remove_dependent(double *line, double missing) {

	int nrem = 0 ;

	// MCV[5] = 10 * HCT[4] / RBC[0]
	if (line[0]!=missing && line[4]!=missing && line[5]!=missing) {
		line[5] = missing ;
		nrem ++ ;
	}

	// MCH[6] = 10 * HGB[3] / RBC [0]
	if (line[0]!=missing && line[3]!=missing && line[6]!=missing) {
		line[6] = missing ;
		nrem ++ ;
	}

	// MCHC[7] = 100 * HGB[3] / HCT[4]
	if (line[3]!=missing && line[4]!=missing && line[7]!=missing) {
		line[7] = missing ;
		nrem ++ ;
	}

	// WBC[1] = EOS#[10] + NEU#[15] + MON#[16] + BAS#[17] + LYMPH#[19]
	if (line[1]!=missing && line[10]!=missing && line[15]!=missing && line[16]!=missing && line[17]!=missing && line[19]!=missing) {
		line[1] = missing ;
		nrem ++ ;
	}

	// LYMPH%[18] = 100*LYMPH#[19]/WBC[1]
	if (line[1]!=missing && line[19]!=missing && line[18]!=missing) {
		line[18] = missing ;
		nrem ++ ;
	}

	// NEU%[11] = 100*NEU#[15]/WBC[1]
	if (line[1]!=missing && line[15]!=missing && line[11]!=missing) {
		line[11] = missing ;
		nrem ++ ;
	}

	// MON%[12] = 100*MON#[16]/WBC[1]
	if (line[1]!=missing && line[16]!=missing && line[12]!=missing)  {
		line[12] = missing ;
		nrem ++ ;
	}

	// EOS%[13] = 100*EOS#[10]/WBC[1]
	if (line[1]!=missing && line[10]!=missing && line[13]!=missing) {
		line[13] = missing ;
		nrem ++ ;
	}

	// BAS%[14] = 100*EOS#[17]/WBC[1]
	if (line[1]!=missing && line[17]!=missing && line[14]!=missing) {
		line[14] = missing ;
		nrem ++ ;
	}

	return nrem ;
}

int remove_dependent (double *lines, int nlines, int ncols, double missing) {

	int nrem = 0 ;
	for (int i=0; i<nlines; i++)
		nrem += remove_dependent(lines+i*ncols+TEST_COL,missing) ;

	return nrem;
}

// Get minimal non-zero value with sufficient observations for log-transformed columns
int get_orig_min_values(double *lines, int nlines, cleaner& cln, int ncols, double missing) { 

	cln.min_orig_data = (double *) malloc (ncols*sizeof(double)) ;
	if (cln.min_orig_data == NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}

	memset(cln.min_orig_data,0,ncols*sizeof(double)) ;

	// Get minimal non-zero value
	for (int j=0; j<NCBC; j++) {
		if (log_cols[j]) {
			map<double,int> val_count ;
			for (int i=0; i<nlines; i++) {
				int idx = i*ncols + j + TEST_COL;
				if (lines[idx] != MISSING_VAL && lines[idx] > 0)
					val_count[lines[idx]] ++ ;
			}

			int found = 0 ;
			for (auto it = val_count.begin(); it != val_count.end(); it++) {
				if (it->second > CNT_FOR_MIN_VAL) {
					found = 1;
					cln.min_orig_data[TEST_COL + j] = it->first ;
					break ;
				}
			}

			if (! found)
				cln.min_orig_data[TEST_COL + j] = val_count.begin()->first ;
		}
	} 

	return 0 ;
}
	
// Perform initial transformations on data (missing => MISSING_VAL + possible log)
void perform_initial_trnasformations(double *lines, int nlines, cleaner& cln, int ncols, double missing_val) {

	// missing -> MISSING
	for (int i=0; i<nlines ; i++) {
		for (int j=TEST_COL; j<ncols; j++) {
			int idx = i*ncols + j ;
			if (lines[idx] == missing_val)
				lines[idx] = MISSING_VAL ;
		}
	}

	// Take care of accuracy
	for (int i = 0; i < nlines; i++) {
		for (int j = TEST_COL; j < ncols; j++) {
			int idx = i*ncols + j;
			if (lines[idx] != MISSING_VAL)
				lines[idx] = ((int)(0.5 + lines[idx] * 1000)) / 1000.0;
		}
	}

	// Log
	for (int j=0; j<NCBC; j++) {
		if (log_cols[j]) {
			for (int i=0; i<nlines; i++) {
				int idx = i*ncols + j + TEST_COL;
				if (lines[idx] != MISSING_VAL) {
					if (lines[idx] > 0) 
						lines[idx] = log(lines[idx]);
					else if (lines[idx] == 0)
						lines[idx] = log(cln.min_orig_data[TEST_COL + j]/2.0) ;
				}
			}
		}
	}

	return ;
}


void get_registry_from_lines(double *lines, int nlines, int ncols, map<string,vector<cancer> >& registry) {

	char id[MAX_STRING_LEN] ;
	for (int i=0; i<nlines; i++) {

		int cancer_type = (int) (lines[XIDX(i,CANCER_COL,ncols)] + 0.01) ;
		if (cancer_type != 0) {
			cancer temp_cancer ;
			temp_cancer.days = get_day((int) lines[XIDX(i,CANCER_DATE_COL,ncols)]) ;
			temp_cancer.index = (cancer_type == 1 || cancer_type == 2) ? 1 : 2 ;
			sprintf(id,"%d",(int) lines[XIDX(i,ID_COL,ncols)]) ;
			registry[id].push_back(temp_cancer) ;
		}
	}

	return ;
}

int learn_twosteps_predictor(xy_data *xy, generalized_learner_info_t *learn_info, unsigned char **model) {
		

		int modelSize=0 ;

		double *temp_preds = (double *)malloc(sizeof(double)*xy->nrows);
		int *temp_dates =  (int *)malloc(sizeof(int)*xy->nrows); 
		int *temp_ids = (int *)malloc(sizeof(int)*xy->nrows);
		int *temp_flags = (int *)malloc(sizeof(int)*xy->nrows);
		double *temp_labels = (double *)malloc(sizeof(double)*xy->nrows);
		int *final_rank_high = (int *)malloc(sizeof(int)*xy->nrows);
		int *temp_censor = (int *)malloc(sizeof(int)*xy->nrows);

		if (temp_preds==NULL || temp_dates==NULL || temp_ids==NULL || temp_flags==NULL || temp_labels==NULL || final_rank_high==NULL || temp_censor==NULL) {
			fprintf(stderr,"cant allocate temp_preds/temp_dates/temp_ids/temp_flags/temp_labels/final_rank_high/temp_censor......\n") ;
			return -1 ;
		}


		for (int ii=0; ii<xy->nrows; ii++)  
			final_rank_high[ii]=-1;

		int age_col = learn_info->field_cols["Age"];
		int match_age_exists = 0;
		for (int ii=0; ii< learn_info->matching_col.size(); ii++) {
			if (learn_info->matching_col[ii]==age_col)  match_age_exists=1;
		}

		if (match_age_exists==0) {
			learn_info->matching_col.push_back(age_col);
			learn_info->matching_res.push_back(1.0);
			learn_info->matching_w  = 0.01 ;
		}

		learn_info->rf_ntrees = 1000 ;

		int rc ;
		if (rc = get_predictions(xy,learn_info->internal_method.c_str(),learn_info,learn_info->nfold,temp_preds,temp_dates,temp_ids,temp_flags,temp_censor,temp_labels)==-1) {
			fprintf(stderr,"Get-Predictions Failed\n") ;
			return -1 ;
		}
		
		if (match_age_exists==0) {
			learn_info->matching_col.pop_back();
			learn_info->matching_res.pop_back();
		}


		int prev_id = temp_ids[0];
		map<pair<int, int>, int> score_rank ;
		vector<pair<int,double> > id_scores ;
		for (int ii=0; ii<xy->nrows; ii++) {
			
			if (temp_ids[ii]!= prev_id) {
				sort(id_scores.begin(),id_scores.end(),rev_compare_pairs()) ;
				for (unsigned int i=0; i<id_scores.size(); i++) {
					pair<int,int> score_id(prev_id,temp_dates[id_scores[i].first]) ;
					score_rank[score_id] = i ;
					//temp_rank[ id_scores[i].first ] = i;
				}
				id_scores.clear();
			} 

			pair<int,double> current_score(ii,temp_preds[ii]) ;
			id_scores.push_back(current_score) ;

			prev_id = temp_ids[ii];
		}

		//apply to the last id
		sort(id_scores.begin(),id_scores.end(),rev_compare_pairs()) ;
		for (unsigned int i=0; i<id_scores.size(); i++) {
			pair<int,int> score_id(temp_ids[id_scores[i].first],temp_dates[id_scores[i].first]) ;
			score_rank[score_id] = i ;
			//temp_rank[ id_scores[i].first ] = i;
		}


		for (int ii=0; ii<xy->nrows; ii++) {
			pair<int,int> score_id(xy->idnums[ii] , xy->dates[ii]) ;
			assert(score_rank.find(score_id) != score_rank.end() );
			final_rank_high[ii] =score_rank[ score_id ];
		}


		if (match_age_exists==1) {
			

			if (learn_info->external_method == "DoubleMatched") {


					learn_info->matching_col.clear();
					learn_info->matching_res.clear();

					// Get prediction on data matched on first-field (Hemoglobin, matching-w = 0.015) ;
					learn_info->matching_col.push_back(learn_info->field_cols["Hemog"]) ;
					learn_info->matching_res.push_back(0.5); 
					learn_info->matching_w = 0.015 ;


					fprintf(stderr,"Getting matched predictions\n") ;
					map<pair<int,int>, double> preds_hash ;
					if (get_predictions(xy,learn_info->internal_method.c_str(),learn_info,learn_info->nfold,preds_hash) == -1) {
						fprintf(stderr,"Get Predictions Failed\n") ;
						return -1 ;
					}

					// Learn Hemoglobin-matched predictor
					fprintf(stderr,"Learning on matched data\n") ;

					unsigned char *initial_model ;
					learn_info->sp_nfold = 0 ;


					int size1 = learn_predictor(xy,learn_info->internal_method.c_str(),learn_info,&initial_model) ;
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

					learn_info->matching_col.pop_back();
					learn_info->matching_res.pop_back();
					fprintf(stderr, "second alloc \n");
					modelSize+=size1;
					(*model)  =  (unsigned char *) realloc ((*model),modelSize);
					memcpy((*model),initial_model,size1) ;


					learn_info->matching_col[0] = learn_info->field_cols["Age"] ;
					learn_info->matching_res[0] = 1.0 ;
					learn_info->matching_w = 0.01 ;

			}

			 unsigned char *probs_model ;
			 int probs_size = learn_predictor_and_score_probs_ranks(xy,  learn_info->internal_method.c_str(), learn_info, &probs_model , final_rank_high);
			 int prev_size = modelSize;
			 modelSize +=probs_size;
			 (*model)  =  (unsigned char *) realloc ((*model),modelSize);
			 memcpy((*model)+prev_size,probs_model,probs_size) ;
		} 
		else {

			int NUM_OF_GBMS = 2;
			xy_data xy_copy;
			unsigned char *model_temp ;
			int modelSize_temp ;

			for (int mm=0; mm<NUM_OF_GBMS; mm++) {
					int x = copy_xy (&xy_copy , xy);
					if (mm==0) {
									int rank_limit = 0;
									int x_filter = filter_learning_set_rank_score(&xy_copy,final_rank_high,rank_limit);
					}
					else if (mm==1) {
									int rank_limit = 200;
									int x_filter = filter_learning_set_rank_score(&xy_copy,final_rank_high,rank_limit);
					}

					take_samples(&xy_copy,2); 
					assert((modelSize_temp = learn_predictor(&xy_copy,learn_info->internal_method.c_str(), learn_info,&model_temp))>0);


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
		}
		return modelSize;

}

// Generalized Learning
int learn_predictor(xy_data *xy, string method, generalized_learner_info_t *learning_info, unsigned char **model) {


	fprintf(stderr , "method : %s\n" , method.c_str());

	if (learning_info->ts_nfold)
		return learn_two_stages_predictor(xy,method,learning_info,model) ;

	if (learning_info->sp_nfold)
		return learn_predictor_and_score_probs(xy,method,learning_info,model) ;

	int size ;
	
	if (method == "RFGBM") { // RfGBM
		rfgbm_learning_params rfgbm_params ;
		rfgbm_params.combination_bound = learning_info->combination_bound ;
		rfgbm_params.gbm_params = learning_info->gbm_params ;
		rfgbm_params.nfold = learning_info->nfold ;
		rfgbm_params.seed = learning_info->seed ;
		rfgbm_params.rf_ntrees = learning_info->rf_ntrees;
		strcpy(rfgbm_params.rf_file_name,TREE_FILE) ;
		if (learning_info->matching_col.size() == 0 )
			return learn_rfgbm_predictor(xy,&rfgbm_params,model) ;
		else
			return learn_rfgbm_predictor(xy,&rfgbm_params,model,learning_info->matching_col,learning_info->matching_res,learning_info->matching_w) ;
	} else if (method == "RFGBM2") { // RfGBM
		rfgbm2_learning_params rfgbm_params ;
		rfgbm_params.comb_gbm_params = learning_info->comb_gbm_params ;
		rfgbm_params.gbm_params = learning_info->gbm_params ;
		rfgbm_params.nfold = learning_info->nfold ;
		rfgbm_params.seed = learning_info->seed ;
		rfgbm_params.rf_ntrees = learning_info->rf_ntrees;
		strcpy(rfgbm_params.rf_file_name,TREE_FILE) ;
		if (learning_info->matching_col.size() == 0 )
			return learn_rfgbm2_predictor(xy,&rfgbm_params,model) ;
		else
			return learn_rfgbm2_predictor(xy,&rfgbm_params,model,learning_info->matching_col,learning_info->matching_res, learning_info->matching_w) ;
	} else if (method == "DoubleMatched") {
		return learn_double_matched_predictor(xy,learning_info,model) ;
	} else if (method == "TwoSteps") {
		return learn_twosteps_predictor(xy,learning_info,model) ;	
	} else {
		// Filter Learning Set
		xy_data fxy ;
		init_xy(&fxy) ;


		if (filter_learning_set(xy,&fxy,2) == -1) {
			fprintf(stderr,"Learning Set Filtering Failed\n") ;
			return -1 ;
		}

		// Age Match if required
		xy_data nxy ;
		init_xy(&nxy) ;
		if (adjust_learning_set(&fxy,learning_info->matching_col,learning_info->matching_res,learning_info->matching_w,&nxy)==-1)
			return -1 ;

		if (method == "RF") {
			size = learn_rf_predictor(nxy.x,nxy.y,nxy.nrows,nxy.nftrs,learning_info->rf_file_name,model,learning_info->rf_ntrees ) ;
		} else if (method == "GBM") {
			size = learn_gbm_predictor(nxy.x,nxy.y,nxy.nrows,nxy.nftrs,model,learning_info->gbm_params) ;
		} else if (method == "LM") {
			size = learn_ls(nxy.x,nxy.y,nxy.nrows,nxy.nftrs,model,DUP_SIZE) ;
		} else if (method == "ENSGBM") {
			size = learn_gbm_ens_predictor(nxy.x,nxy.y,nxy.nrows,nxy.nftrs,model,learning_info->gbm_params,learning_info->gbm_ens_size) ;
		} else if (method == "LP") {
			size = learn_linear_plus_predictor(nxy.x,nxy.y,nxy.nrows,nxy.nftrs,model) ;
		} else if (method == "QRF") {
			size = learn_qrf_predictor(nxy.x,nxy.y,nxy.nrows,nxy.nftrs,model,learning_info->qrf_ntrees, learning_info->qrf_ntry, learning_info->qrf_max_quant, learning_info->nthreads);
		} else {
			fprintf(stderr,"Unknown method \'%s\'\n",method.c_str()) ;
			return -1 ;
		}

		clear_xy(&fxy) ;
		clear_xy(&nxy) ;
	}

	return size ;
}

// Generalized Prediction
int predict (double*x, int nrows, int ncols, generalized_predictor_info_t& predict_info,  unsigned char *model, double *preds) {

	if (predict_info.method == "RFGBM") {
		return rfgbm_predict(x,preds,nrows,ncols,model) ;
	} else if (predict_info.method == "RF") {
		return rf_predict(x,preds,nrows,ncols,model) ;
	} else if (predict_info.method == "TwoSteps") {
		return twosteps_predict(x,preds,nrows,ncols,predict_info.internal_method,model ,predict_info.external_method  ) ;
	} else if (predict_info.method == "GBM") {
		return gbm_predict(x,preds,nrows,ncols,model) ;
	} else if (predict_info.method == "LM") {
		return ls_predict_from_model(x,preds,nrows,ncols,model) ;
	} else if (predict_info.method == "ENSGBM") {
		return gbm_ens_predict(x,preds,ncols,nrows,model) ;
	} else if (predict_info.method == "LP") {
		return linear_plus_predict(x,preds,nrows,ncols,model) ;
	} else if (predict_info.method == "RFGBM2") {
		return rfgbm2_predict(x,preds,nrows,ncols,model) ;
	} else if (predict_info.method == "DoubleMatched") {
		return double_matched_predict(x,preds,nrows,ncols,predict_info,model) ;
	} else if (predict_info.method == "QRF") {
		return qrf_predict(x,preds,nrows,ncols,model,predict_info.nthreads) ;
	} else {
		fprintf(stderr,"Unknown method \'%s\'\n",predict_info.method.c_str()) ;
		return -1 ;
	}
}


int predict_and_get_posterior(xy_data *xy, int age_col, generalized_predictor_info_t& pred_info, unsigned char *model, FILE *incFile, double *preds) {

	double *x = xy->x ;
	int nrows = xy->nrows ;
	int ncols = xy->nftrs ;

	int size = predict(x,nrows,ncols,pred_info,model,preds) ;
	if (size == -1)
		return -1 ;

	score_probs_info score_probs ;
	int size2 ;
	if ((size2 = deserialize(model+size,&score_probs)) == -1) {
		fprintf(stderr,"Serialization of Score Probs failed\n") ;
		return -1 ;
	}

	// Extract Ages
	double *ages = (double *) malloc(nrows*sizeof(double)) ;
	if (ages == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for (int i=0; i<nrows; i++)
		ages[i] = x[XIDX(age_col,i,nrows)] ;


	// Get age-dependent incidence
	vector<double> age_probs ;
	if (incFile)
		// Get age-probs from fo;e
		assert (read_age_dep(incFile,age_probs) != -1) ;
	else {
		// Get age-probs from model
		int size3 ;
		gen_model generative_model ;

		if ((size3 = deserialize(model+size+size2,&generative_model)) == -1) {
			fprintf(stderr,"Serialization of hash-probs failed\n") ;
			return -1 ;
		}

		map<int, double> age_hash ;
		vector<int> ages_vec ;

		for (auto it=(generative_model.npos).begin(); it!=(generative_model.npos).end(); it++) {
			if ((it->first).size() != 1) {
				fprintf(stderr,"Illegal probs-hash\n") ;
				return -1 ;
			}
//			int age = (int) ((it->first)[0] + 0.5) ;
			int age = (int)(it->first)[0];
			age_hash[age] = ((generative_model.npos)[it->first] + 0.0)/((generative_model.npos)[it->first] + (generative_model.nneg)[it->first]) ;
			ages_vec.push_back(age) ;
		}

		hash_to_vector(age_hash,ages_vec,age_probs);
	}

	get_posteriors(preds,ages,nrows,age_probs,score_probs) ;

	return 0 ;
}


int twosteps_predict(double *x, double *preds, int nrows, int ncols, string internal_method, unsigned char *model , string external_method ) {
		
	int full_size=0;
	double *nx;

	if (external_method == "DoubleMatched") {	

		generalized_predictor_info_t temp_pred_info ;
		temp_pred_info.method = internal_method ;

		int size1 = predict(x,nrows,ncols,temp_pred_info,model,preds) ;
		if (size1 == -1)
			return -1 ;

		// Add predictions to matrix
		nx = (double *) malloc(nrows*(ncols+1)*sizeof(double)) ;
		if (nx == NULL) {
			fprintf(stderr,"Reallocation Failed\n") ;
			return -1 ;
		}

		memcpy(nx,x,nrows*ncols*sizeof(double)) ;
		for (int i=0; i<nrows; i++)
			nx[nrows*ncols + i] = preds[i] ;
		ncols ++ ;

		x=nx;
		full_size+=size1;
	}


	generalized_predictor_info_t temp_pred_info ;
	temp_pred_info.method = internal_method ;
	
	double *preds_temp[2];			
	int NUM_OF_GBMS = 2;
	for (int mm=0; mm<NUM_OF_GBMS; mm++) {
		assert(preds_temp[mm]=(double *)malloc(nrows*sizeof(double)));
		int size = predict(x,nrows ,ncols, temp_pred_info,(unsigned char *)model+full_size,preds_temp[mm]);
		if (size == -1) {
			fprintf(stderr,"predictor %d failed\n",mm) ;
			return -1 ;
		}
		full_size+=size;
	}

	for (int ii=0; ii<nrows; ii++)
		preds[ii]=0;

	double min=999, max = -999;
	for (int ii=0; ii<nrows; ii++) {
		if (preds_temp[0][ii]<min) min=preds_temp[0][ii];
		if (preds_temp[0][ii]>max) max=preds_temp[0][ii];
	}

	for (int ii=0; ii<nrows; ii++) {
			//preds[ii] = preds_temp[0][ii]*((preds_temp[1][ii]-min)/(max-min))  +   preds_temp[1][ii]*(1-((preds_temp[1][ii]-min)/(max-min)));
			preds[ii] = (0.5*preds_temp[0][ii]) + (0.5*preds_temp[1][ii]);
	}
					
	return full_size;
}



int predict(xy_data *xy, generalized_predictor_info_t& predict_info, unsigned char *model, double *preds) {	

	double *x = xy->x ;
	int nrows = xy->nrows ;
	int ncols = xy->nftrs ;

	// Sanity 
	if (predict_info.incFile != NULL && predict_info.external_prior_cols.empty()) {
		fprintf(stderr,"External Prior Fields must be given with incidence file\n") ; fflush(stderr);
		return -1 ;
	}

	map<int,int> external_cols_hash ;
	for (unsigned int i=0; i<predict_info.external_prior_cols.size(); i++)
		external_cols_hash[i] = 1 ;
	
	for (unsigned int i=0; i<predict_info.model_prior_cols.size(); i++) {
		if (external_cols_hash.find(predict_info.model_prior_cols[i]) != external_cols_hash.end()) {
			fprintf(stderr,"Col %d is common to external and model fields\n",predict_info.model_prior_cols[i]) ; fflush(stderr);
			return -1 ;
		}
	}

	fprintf(stderr, "Printing Features\n");
	if (predict_info.ftrsFile != NULL) {
		for (int i = 0; i < xy->nrows; i++) {
			fprintf(predict_info.ftrsFile, "%d\t%d", (xy->idnums[i]), xy->dates[i]);
			for (int j = 0; j < xy->nftrs; j++)
				fprintf(predict_info.ftrsFile, "\t%f", (xy->x)[(xy->nrows)*j + i]);
			fprintf(predict_info.ftrsFile, "\n");
		}
	}

	int size = predict(x,nrows,ncols,predict_info,model,preds) ;

	if (size == -1)
		return -1 ;

	// 2nd stage
	if (predict_info.two_stages) {	
		// Add predictions to matrix
		if (((xy->x) = (double *) realloc(xy->x,(xy->nrows)*(xy->nftrs + 1)*sizeof(double))) == NULL) {
			fprintf(stderr,"Reallocation Failed\n") ; fflush(stderr);
			return -1 ;
		}

		for (int i=0; i<(xy->nrows); i++)
			(xy->x)[(xy->nrows)*(xy->nftrs) + i] = preds[i] ;

		(xy->nftrs) ++ ;

		// Predict 
		predict_info.two_stages = 0 ;

		return (predict(xy->x,xy->nrows,xy->nftrs,predict_info,model+size,preds)) ;
	}

	// Posteriors
	if (! (predict_info.external_prior_cols.empty() && predict_info.model_prior_cols.empty())) {
		score_probs_info score_probs ;
		int size2 ;
		if ((size2 = deserialize(model+size,&score_probs)) == -1) {
			fprintf(stderr,"Serialization of Score Probs failed\n") ; fflush(stderr);
			return -1 ;
		}

		double *probs = (double *) malloc(nrows*sizeof(double)) ;
		if (probs == NULL) {
			fprintf(stderr,"Allocation failed\n") ; fflush(stderr);
			return -1 ;
		}

		// Get Translation table from model
		vector<pair<double,double> >  pred_to_spec ;
		int size3;
		if ((size3 = deserialize(model+size+size2,&pred_to_spec)) == -1) {
			fprintf(stderr,"Serialization of hash-probs failed\n") ; fflush(stderr);
			return -1 ;
		}

		// Shift by model
		if (! predict_info.model_prior_cols.empty()) {
			// Extract posteriors entries
			vector<vector<double> > keys ;
			for (int i=0; i<nrows; i++) {
				vector<double> key ;
				for (unsigned int j=0; j<predict_info.model_prior_cols.size(); j++)
					key.push_back(x[XIDX(predict_info.model_prior_cols[j],i,nrows)]) ;
				keys.push_back(key) ;
			}

			// Get Model
			gen_model generative_model ;
			int size4 ;
			if ((size4 = deserialize(model+size+size2+size3,&generative_model)) == -1) {
				fprintf(stderr,"Serialization of hash-probs failed\n") ; fflush(stderr);
				return -1 ;
			}

			// Get Probs (Special treatment for single-valued keys)
			if (keys[0].size() == 1) {
				if (get_probs_from_incidence(keys,&generative_model,probs) == -1) {
					fprintf(stderr,"Cannot caluclate probabilities from generative model\n") ; fflush(stderr);
					return -1 ;
				}
			} else {
				if (get_probs_from_generative_model(keys,&generative_model,probs) == -1) {
					fprintf(stderr,"Cannot caluclate probabilities from generative model\n") ; fflush(stderr);
					return -1 ;
				}
			}

			get_posteriors(preds,probs,nrows,score_probs) ;
		}

		// Shift by file
		if (! predict_info.external_prior_cols.empty()) {
			fprintf(stderr,"predict(): in shift by file\n"); fflush(stderr);

			// Extract posteriors entries
			vector<vector<double> > keys ;
			for (int i=0; i<nrows; i++) {
				vector<double> key ;
				for (unsigned int j=0; j<predict_info.external_prior_cols.size(); j++) 
					key.push_back(x[XIDX(predict_info.external_prior_cols[j],i,nrows)]) ;
				keys.push_back(key) ;
			}

			// Get Model
			gen_model generative_model ;
			if (read_generative_model(predict_info.incFile,&generative_model) == -1) {
				fprintf(stderr,"Reading generative model from file failed\n") ; fflush(stderr);
				return -1;
			}

			if (generative_model.resolutions.size() != predict_info.external_prior_cols.size()) {
				fprintf(stderr,"Key size mismatch for generative model\n") ; fflush(stderr);
				return -1 ;
			}

			// Get Probs (Special treatment for single-valued keys)
			if (keys[0].size() == 1) {
				if (get_probs_from_incidence(keys,&generative_model,probs) == -1) {
					fprintf(stderr,"Cannot caluclate probabilities from generative model\n") ; fflush(stderr);
					return -1 ;
				}
			} else {
				if (get_probs_from_generative_model(keys,&generative_model,probs) == -1) {
					fprintf(stderr,"Cannot caluclate probabilities from generative model\n") ; fflush(stderr);
					return -1 ;
				}
			}

			get_posteriors(preds,probs,nrows,score_probs) ;
		}

		// Transplate from P(CRC) to "Specificity"
		for (int i=0; i<nrows; i++)
			preds[i] = get_spec_from_prob_gaussian_kernel(preds[i],pred_to_spec) ;

		free(probs) ;
	}
	return 0 ;
}

// Generalized Cross Validation
int get_predictions(xy_data *xy, string method, generalized_learner_info_t *learning_info, int nfold, double *preds) {

	double *labels = (double *) malloc((xy->nrows)*sizeof(double)) ;
	int *dates = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *ids = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *flags = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *censor = (int *) malloc((xy->nrows)*sizeof(int)) ;

	if (labels == NULL || dates == NULL || ids == NULL || flags == NULL || censor == NULL) {
		fprintf(stderr,"Allocation for CV failed\n") ;
		return -1 ;
	}

	int rc ;
	if (rc = get_predictions(xy,method,learning_info,nfold,preds,dates,ids,flags,censor,labels)==-1) {
		fprintf(stderr,"Get-Predictions Failed\n") ;
		return -1;
	}

	free(labels) ;
	free(dates) ;
	free(ids) ;
	free(flags) ;
	free(censor) ;

	return 0 ;
}

int get_predictions(xy_data *xy, string method, generalized_learner_info_t *learning_info, int nfold, map<pair<int,int>, double>& preds_hash) {

	double *labels = (double *) malloc((xy->nrows)*sizeof(double)) ;
	double *preds = (double *) malloc((xy->nrows)*sizeof(double)) ;
	int *dates = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *ids = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *flags = (int *) malloc((xy->nrows)*sizeof(int)) ;
	int *censor = (int *) malloc((xy->nrows)*sizeof(int)) ;

	if (preds == NULL || labels == NULL || dates == NULL || ids == NULL || flags == NULL || censor == NULL) {
		fprintf(stderr,"Allocation for CV failed\n") ;
		return -1 ;
	}

	int rc ;
	if (rc = get_predictions(xy,method,learning_info,nfold,preds,dates,ids,flags,censor,labels)==-1)
		fprintf(stderr,"Get-Predictions Failed\n") ;

	if (rc != -1) {
		for (int i=0; i<(xy->nrows); i++) {
			pair<int,int> entry(ids[i],dates[i]) ;
			preds_hash[entry] = preds[i] ;
		}
	}

	free(preds) ;
	free(labels) ;
	free(dates) ;
	free(ids) ;
	free(flags) ;
	free(censor) ;

	return rc ;
}




int get_predictions(xy_data *xy, string method, generalized_learner_info_t *learning_info, int nfold, double *preds, int *dates, int *ids, int *flags, int *censor, double *labels , map<pair<int,int>, int>& ranks_hash, int rank_limit) {

	fprintf(stderr , "inside get_predictions : %s %i %i \n" , method.c_str() , xy->nrows , nfold);

	int npatients = 1 ;
	for (int i=1; i<xy->nrows; i++) {
		if (xy->idnums[i] != xy->idnums[i-1])
			npatients++ ;
	}
	fprintf(stderr,"Npatients = %d\n",npatients) ;

	// Shuffle
	fprintf(stderr,"Random seed = %d\n",learning_info->seed) ;
	globalRNG::srand(learning_info->seed) ;
	int *order = randomize(npatients) ;
	assert(order != NULL) ;


	double *means_for_completion = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	double *sdvs_for_completion = (double *) malloc((xy->nftrs)*sizeof(double)) ;

	if (means_for_completion == NULL || sdvs_for_completion == NULL) {
		fprintf(stderr,"Allocation for CV failed\n") ;
		return -1 ;
	}

	int size = (nfold > 0) ? npatients/nfold : 0 ;

	int npreds = 0 ;
	double sump = 0 ;
	for (int ifold=0; ifold<nfold; ifold++) {

		int test_start = ifold * size ;
		int test_end = (ifold + 1)*size - 1 ;
		if (ifold == nfold - 1)
			test_end = npatients - 1 ;

		// Split
		xy_data xy1,xy2 ;

		if (get_split_data(xy,npatients,&xy1,&xy2,order,test_start,test_end) == -1) {
			fprintf(stderr,"Data Splitting in CV Failed\n") ;
			return -1 ;
		}

		memcpy(dates+npreds,xy2.dates,(xy2.nrows)*sizeof(int)) ;
		memcpy(ids+npreds,xy2.idnums,(xy2.nrows)*sizeof(int)) ;
		memcpy(flags+npreds,xy2.flags,(xy2.nrows)*sizeof(int)) ;
		memcpy(censor+npreds,xy2.censor,(xy2.nrows)*sizeof(int)) ;
		memcpy(labels+npreds,xy2.y,(xy2.nrows)*sizeof(double)) ;

		fprintf(stderr,"Fold: %d   Training size: %d    Testing size: %d\n", ifold, xy1.nrows, xy2.nrows);

		// Get Predictions
		double *ipreds = (double *) malloc(xy2.nrows*sizeof(double)) ;
		if (ipreds == NULL) {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
		}

		
		int *x1_ranks = (int *) malloc(xy1.nrows*sizeof(int)) ;
		for (int ii=0; ii<xy1.nrows;  ii++)  {

			pair<int,int> entry(xy1.idnums[ii],xy1.dates[ii]) ;
			if (ranks_hash.find(entry) == ranks_hash.end()) {
				fprintf(stderr,"Cannot find prediction for (%d,%d)\n",xy1.idnums[ii],xy1.dates[ii]) ;
				return -1 ;
			}
			x1_ranks[ii] = ranks_hash[entry] ;
		}

		fprintf(stderr , "rank_limit : %i\n" , rank_limit);
		//return -1;

		int x_filter = filter_learning_set_rank_score(&xy1,x1_ranks,rank_limit);

		
		if (take_samples(&xy1,2) == -1) {
			fprintf(stderr,"Take sampled failed\n") ;
			return -1;
		}

		clock_t start = clock() ;

		get_mean_values(&xy1,means_for_completion,sdvs_for_completion) ;
		replace_with_approx_mean_values(&xy1,means_for_completion,sdvs_for_completion) ;
		replace_with_approx_mean_values(&xy2,means_for_completion,sdvs_for_completion) ;

		// Get Prediction
		if (method == "RFGBM") {
			rfgbm_learning_params rfgbm_params ;
			rfgbm_params.combination_bound = learning_info->combination_bound ;
			rfgbm_params.gbm_params = learning_info->gbm_params ;
			rfgbm_params.nfold = learning_info->nfold ;
			rfgbm_params.seed = learning_info->seed ;

			if (learning_info->matching_col.size() == 0) {
				if (get_rfgbm_predictions(&xy1,&rfgbm_params,&xy2,preds+npreds) == -1) {
					fprintf(stderr,"Get-RfGBM-Predictions Failed\n") ;
					return -1 ;
				}
			} else {
				if (get_rfgbm_predictions(&xy1,&rfgbm_params,&xy2,preds+npreds,learning_info->matching_col,learning_info->matching_res,learning_info->matching_w) == -1) {
					fprintf(stderr,"Get-RfGBM-Predictions Failed\n") ;
					return -1 ;
				}
			}

		} else {

			// Age Pairing
			xy_data nxy ;
			init_xy(&nxy) ;

			if (adjust_learning_set(&xy1,learning_info->matching_col,learning_info->matching_res,learning_info->matching_w,&nxy)==-1)
				return -1 ;

			if (method == "RF") {
				if (get_rf_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds,learning_info->rf_ntrees ) == -1) {
					fprintf(stderr,"Get-RF-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "GBM") {
				if (get_gbm_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds,learning_info->gbm_params)) {
					fprintf(stderr,"Get-GBM-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "LM") {
				if (get_ls_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds,DUP_SIZE)==-1) {
					fprintf(stderr,"Get-LM-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "ENSGBM") {
				if (get_gbm_ens_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds,learning_info->gbm_params,learning_info->gbm_ens_size)==-1) {
					fprintf(stderr,"Get-EnsGBM-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "LP") {
				if (get_linear_plus_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds)==-1) {
					fprintf(stderr,"Get-Linear-Plus-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "QRF") {
				if (get_qrf_predictions(nxy.x, nxy.y, nxy.nrows, xy2.x, xy2.nrows, xy2.nftrs, preds+npreds, learning_info->qrf_ntrees, learning_info->qrf_ntry, learning_info->qrf_max_quant,learning_info->nthreads) == -1) {
					fprintf(stderr,"Get-QRF-Predictions Failed\n") ;
					return -1 ;
				}
			}

			clear_xy(&nxy) ;
		}

		npreds += xy2.nrows ;
		clear_xy(&xy1) ;
		clear_xy(&xy2) ;

		fprintf(stderr,"Done\n") ;
	}

	free(means_for_completion) ;
	free(sdvs_for_completion) ;

	fprintf(stderr,"Cross Validation: Done\n") ;
	return 0 ;
}



int get_predictions(xy_data *xy, string method, generalized_learner_info_t *learning_info, int nfold, double *preds, int *dates, int *ids, int *flags, int *censor, double *labels) {

	fprintf(stderr , "inside get_predictions : %s %i %i\n" , method.c_str() , xy->nrows , nfold);

	int npatients = 1 ;
	for (int i=1; i<xy->nrows; i++) {
		if (xy->idnums[i] != xy->idnums[i-1])
			npatients++ ;
	}
	fprintf(stderr,"Npatients = %d\n",npatients) ;

	// Shuffle
	fprintf(stderr,"Random seed = %d\n",learning_info->seed) ;
	globalRNG::srand(learning_info->seed) ;
	int *order = randomize(npatients) ;
	assert(order != NULL) ;


	double *means_for_completion = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	double *sdvs_for_completion = (double *) malloc((xy->nftrs)*sizeof(double)) ;

	if (means_for_completion == NULL || sdvs_for_completion == NULL) {
		fprintf(stderr,"Allocation for CV failed\n") ;
		return -1 ;
	}

	int size = (nfold > 0) ? npatients/nfold : 0 ;

	int npreds = 0 ;
	double sump = 0 ;
	for (int ifold=0; ifold<nfold; ifold++) {

		int test_start = ifold * size ;
		int test_end = (ifold + 1)*size - 1 ;
		if (ifold == nfold - 1)
			test_end = npatients - 1 ;

		// Split
		xy_data xy1,xy2 ;

		if (get_split_data(xy,npatients,&xy1,&xy2,order,test_start,test_end) == -1) {
			fprintf(stderr,"Data Splitting in CV Failed\n") ;
			return -1 ;
		}

		memcpy(dates+npreds,xy2.dates,(xy2.nrows)*sizeof(int)) ;
		memcpy(ids+npreds,xy2.idnums,(xy2.nrows)*sizeof(int)) ;
		memcpy(flags+npreds,xy2.flags,(xy2.nrows)*sizeof(int)) ;
		memcpy(censor+npreds,xy2.censor,(xy2.nrows)*sizeof(int)) ;
		memcpy(labels+npreds,xy2.y,(xy2.nrows)*sizeof(double)) ;

		fprintf(stderr,"Fold: %d   Training size: %d    Testing size: %d\n", ifold, xy1.nrows, xy2.nrows);

		// Get Predictions
		double *ipreds = (double *) malloc(xy2.nrows*sizeof(double)) ;
		if (ipreds == NULL) {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
		}


		if (method != "RFGBM")  {
			if (take_samples(&xy1,2) == -1) {
				fprintf(stderr,"Take sampled failed\n") ;
				return -1;
			}

			int npos = 0, nneg = 0 ;
			for (int i=0; i<xy1.nrows; i++) {
				if (xy1.y[i] > 0)
					npos ++ ;
				else
					nneg ++ ;
			}

			fprintf(stderr,"After take-samples : %d + %d\n",npos,nneg) ;
			if ((npos+0.0)/(npos+nneg) > 0.25) {
				fprintf(stderr,"Adjusting matching-w to 1.0\n") ; 
				learning_info->matching_w = 1.0 ;
			}
		}
			

		clock_t start = clock() ;

		get_mean_values(&xy1,means_for_completion,sdvs_for_completion) ;
		replace_with_approx_mean_values(&xy1,means_for_completion,sdvs_for_completion) ;
		replace_with_approx_mean_values(&xy2,means_for_completion,sdvs_for_completion) ;

		// Get Prediction
		if (method == "RFGBM") {
			rfgbm_learning_params rfgbm_params ;
			rfgbm_params.combination_bound = learning_info->combination_bound ;
			rfgbm_params.gbm_params = learning_info->gbm_params ;
			rfgbm_params.nfold = learning_info->nfold ;
			rfgbm_params.seed = learning_info->seed ;

			if (learning_info->matching_col.size() == 0) {
				if (get_rfgbm_predictions(&xy1,&rfgbm_params,&xy2,preds+npreds) == -1) {
					fprintf(stderr,"Get-RfGBM-Predictions Failed\n") ;
					return -1 ;
				}
			} else {
				if (get_rfgbm_predictions(&xy1,&rfgbm_params,&xy2,preds+npreds,learning_info->matching_col,learning_info->matching_res,learning_info->matching_w) == -1) {
					fprintf(stderr,"Get-RfGBM-Predictions Failed\n") ;
					return -1 ;
				}
			}

		} else {

			// Age Pairing
			xy_data nxy ;
			init_xy(&nxy) ;

			if (adjust_learning_set(&xy1,learning_info->matching_col,learning_info->matching_res,learning_info->matching_w,&nxy)==-1)
				return -1 ;

			if (method == "RF") {
				if (get_rf_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds, learning_info->rf_ntrees) == -1) {
					fprintf(stderr,"Get-RF-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "GBM") {
				if (get_gbm_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds,learning_info->gbm_params)) {
					fprintf(stderr,"Get-GBM-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "LM") {
				if (get_ls_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds,DUP_SIZE)==-1) {
					fprintf(stderr,"Get-LM-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "ENSGBM") {
				if (get_gbm_ens_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds,learning_info->gbm_params,learning_info->gbm_ens_size)==-1) {
					fprintf(stderr,"Get-EnsGBM-Predictions Failed\n") ;
					return -1 ;
				}
			} else if (method == "LP") {
				if (get_linear_plus_predictions(nxy.x,nxy.y,nxy.nrows,xy2.x,xy2.nrows,xy2.nftrs,preds+npreds)==-1) {
					fprintf(stderr,"Get-Linear-Plus-Predictions Failed\n") ;
					return -1 ;
				}
			}  else if (method == "QRF") {
				if (get_qrf_predictions(nxy.x, nxy.y, nxy.nrows, xy2.x, xy2.nrows, xy2.nftrs, preds+npreds, learning_info->qrf_ntrees, learning_info->qrf_ntry, learning_info->qrf_max_quant,learning_info->nthreads) == -1) {
					fprintf(stderr,"Get-QRF-Predictions Failed\n") ;
					return -1 ;
				} 
			} else {
				fprintf(stderr,"Unknown method %s in get_predictions\n",method.c_str()) ;
				return -1 ;
			}

			clear_xy(&nxy) ;
		}

		npreds += xy2.nrows ;
		clear_xy(&xy1) ;
		clear_xy(&xy2) ;

		fprintf(stderr,"Done\n") ;
	}

	free(means_for_completion) ;
	free(sdvs_for_completion) ;

	fprintf(stderr,"Cross Validation: Done\n") ;
	return 0 ;
}

// Read a list of ids, optionally with dates (id@date format or separated by space, tab, or comma)
void readIdDateList(string& idFileName, map<int, set<int> >& res) {

	cerr << "Going to open ID list file " << idFileName << " for reading ..." << endl;
	gzFile idFile = safe_gzopen(idFileName.c_str(), "r");

	// char *txtline = (char *) malloc(MAX_STRING_LEN * sizeof(char));
	// assert(txtline != NULL);

	string lineStr;
	while (gzGetLine(idFile, lineStr) != NULL) {
		vector<string> fields;
		split(fields, lineStr, is_any_of("@ \t,"));
		assert(fields.size() == 1 || fields.size() == 2); // 'id' or 'id@date'	
		// for (auto it = fields.begin(); it != fields.end(); ++it) cerr << *it << " ";
		// cerr << endl;

		if (res.find(atoi(fields[0].c_str())) == res.end()) {
			res[atoi(fields[0].c_str())] = set<int>();
		}
		if (fields.size() == 2) {
			res[atoi(fields[0].c_str())].insert(atoi(fields[1].c_str()));
		}
	}

	return ;
}

set<string> readRegDirsFromGroupsFile(int group, const string& grpFileName = "") {
	set<string> res;
	string groups_fn = (grpFileName == "") ? GRP_FILE : grpFileName;
	gzFile grpFile = safe_gzopen(groups_fn.c_str(), "r");
	cerr << "Reading registry directions from file " << groups_fn 
		 << " with group number " << group << endl;
	string lineStr;
	while (gzGetLine(grpFile, lineStr) != NULL) {
		vector<string> fields;
		size_t pos = lineStr.find_first_of(' '); // a space is separating between the group number and the cancer description text, which may contain spaces as well
		assert(pos != string::npos);
		int grpNum = atoi(lineStr.substr(0, pos).c_str());
		// cerr << "Group number is " << grpNum << " for line: " << line_str << endl;
		if (grpNum == group) {
			res.insert(lineStr.substr(pos+1)); // rest of line
			fprintf(stderr, "inserting \"%s\" into cancer directions\n", lineStr.substr(pos+1).c_str());
		}
	}

	return(res);
}

// Read list of signals into "signals" vector
void readSignals(const string& signalsFileName, vector<string>* signals) {
	cerr << "Going to open signal list file " << signalsFileName << " for reading ..." << endl;
	gzFile signalsFile = safe_gzopen(signalsFileName.c_str(), "r");
	string lineStr;
	while (gzGetLine(signalsFile, lineStr) != NULL) {
		(*signals).push_back(lineStr);
		// cerr << "DEBUG: Reading signal " << lineStr << endl;
	}
	return;
}

// Read cancer registry and mark patients affected by target cancer(s) as specified by directions
map<int, vector<reg_entry> > readCancerRegistry(set<string>& regDirs, const string& regFileName = "") {
	map<int, vector<reg_entry> > res;
	gzFile regFile = (regFileName == "") ? safe_gzopen(REG_FILE, "r") : safe_gzopen(regFileName.c_str(), "r");
			
	string lineStr;
	while (gzGetLine(regFile, lineStr) != NULL) {		
		vector<string> fields;
		// fprintf(stderr, "Working on registry line:\n%s", txtline);
		split(fields, lineStr, is_any_of("\t")); 
		assert(fields.size() == 8);

		if (fields[0] == "NR") continue; // skip header line, if exists

		int idnum = atoi(fields[0].c_str());

		int date = atoi(fields[1].c_str());

		string cancerDesc = fields[2];
		// cerr << "cancerDesc is: " << cancerDesc << endl;
		int ingroup = (regDirs.find(cancerDesc) != regDirs.end());
		// cerr << "cancerDesc ingroup is: " << ingroup << endl;

		int mec_stage = (fields[3] == "") ? 9 : atoi(fields[3].c_str());

		reg_entry ent;
		ent.date = date;
		ent.type = (ingroup ? 1 : 3) + (mec_stage/10.0);
		
		// inserting register entry, putting the earliest entry of an individual at the beginning
		if (res.find(idnum) == res.end()) {
			res[idnum] = vector<reg_entry>();
			res[idnum].push_back(ent);
		}
		else {
			if (ent.date < res[idnum][0].date) { // swapping
					res[idnum].push_back(res[idnum][0]);
					res[idnum][0] = ent;
			}
			else {
				res[idnum].push_back(ent);
			}
		}
		assert(res[idnum][0].date <= ent.date); // make sure that the first entry is the earliest
	}

	return(res);
}
class demography{
public:
	int id; 
	int date;
	friend bool operator <(const demography& r,const demography& l) {// comparison op
		return(r.id<l.id ||(r.id==l.id &&r.date<l.date));
	}
};

int buildBinFromRepository(MedRepository &repository,map<int, set<int>>&idList ,string groups,matrixLinesType *linesM){
	#ifndef _SIGNALNAMES_
#define _SIGNALNAMES_
	
char *signalNames[]=// demography would get special treatment here we hold only the medical signals
	{"RBC","WBC","MPV","Hemoglobin","Hematocrit","MCV","MCH","MCHC-M","RDW","Platelets","Eosinophils#",
		"Neutrophils%","Monocytes%","Eosinophils%","Basophils%","Neutrophils#","Monocytes#","Basophils#",
	"Lymphocytes%","Lymphocytes#",
	"Albumin","Ca","Cholesterol","Creatinine","HDL","LDL","K+","Na","Triglycerides","Urea","Uric_Acid","Cl","Ferritin",
	"Glucose","HbA1C","GGT","ALT","AST","Amylase","LDH"};
	
#define NUMSIGNALS (sizeof(signalNames)/sizeof(char *))
/*char *signalNames[]=// demography would get special treatment here we hold only the medical signals
	{"RBC","WBC","MPV","Hemoglobin","Hematocrit","MCV","MCH","MCHC-M","RDW","Platelets","Eosinophils#",
		"Neutrophils%","Monocytes%","Eosinophils%","Basophils%","Neutrophils#","Monocytes#","Basophils#",
	"Lymphocytes%","Lymphocytes#",
	"Albumin","Ca","Cholesterol","Creatinine","HDL","LDL","K+","Na","Triglycerides","Urea","Glucose","Cl","Ferritin"};
	//That was provisory to put glucose instead of Uric Acid
	*/
#endif
	map <class demography,structuredLine> dataMatrix;// map id and date to data
	
	int len;
	fprintf(stderr,"DEBUG  groups: %s\n",groups.c_str());
	vector<int> members;
	repository.dict.get_set_members(groups, members);
	cerr << "There are " << members.size() <<  " members in group " << groups << ":" << endl;
	for (int im=0; im < members.size(); im++) cerr << members[im] << endl;

	int genderId = repository.dict.id("GENDER");
	int byearId = repository.dict.id("BYEAR");
	int censorId = repository.dict.id("Censor");
	int cancerLocId = repository.dict.id("Cancer_Location");
	vector<int> signalIds;
	for (int i = 0; i < NUMSIGNALS; i++)
		signalIds.push_back(repository.dict.id(signalNames[i]));

	assert (idList.size()>0);
//	int debugCount=0;  //to limit number of ids while debugging
	for( auto k=idList.begin();k!=idList.end();k++){ // go over the ids
//		if((debugCount++)==500000)break;//to limit number of ids while debugging
		int  thisID=(k->first);
		SVal *valRecord=(SVal *)repository.get(thisID,genderId,len);
		if (len == 0) {
			cerr << "OMIT: id " << thisID << " from id_list is not in repository" << endl;
			continue;
		}
		assert(len == 1);
		double thisGender=valRecord[0].val;
	    valRecord=(SVal *)repository.get(thisID,byearId,len); 
		assert(len == 1);
		double thisByear=valRecord[0].val;

		SDateVal *dateValRecord=(SDateVal *)repository.get(thisID,censorId,len); 
		assert(len == 1);
		double thisStatus=(int)dateValRecord[0].val/1000;
		double thisStatusDate=dateValRecord[0].date;
		dateValRecord=(SDateVal *)repository.get(thisID, cancerLocId,len);
		double thisCancer=0;
		double thisCancerDate=-1;
		if(len>0){// first cancer determins the cancer. 1: in desired group. 3: other 0: no cancer
			thisCancerDate=dateValRecord[0].date;
			// fprintf(stderr, "%d: %d@%d %s\n", thisID, (int)dateValRecord[0].val, (int)dateValRecord[0].date, groups.c_str());
			if(repository.dict.is_in_set((int)dateValRecord[0].val,groups))
				thisCancer=1;
			else
				thisCancer=3;
		}

		set<demography> omitReported;
		for (int signalIndex=0;signalIndex<NUMSIGNALS;signalIndex++){// go over signals of this id according to signalNames
			//DEBUG use only glucose signal
			//int signalIndex=30;
			int thisSignalId=signalIds[signalIndex];
			
			SDateVal *res=(SDateVal *)repository.get(thisID, thisSignalId,len);
			
			//fprintf(stderr,"name: %s len: %d\n",thisSignal.c_str(),len);//DEBUG
			for(int count=0;count<len;count++){

				demography demo;
				demo.id=thisID;
				demo.date=res[count].date;
				
				if ((idList[thisID].size() > 0) &&
					(idList[thisID].find(demo.date) == idList[demo.id].end())) {
					if (omitReported.find(demo) != omitReported.end()) {
						cerr << "OMIT: " << thisID << "@" << demo.date << " is not in repository" << endl;
						omitReported.insert(demo);
					}
					continue;
				}

				if(dataMatrix.find(demo)==dataMatrix.end()) {
					structuredLine newLine;
					for (int kk=0; kk<MAXCOLS; kk++) newLine.alignDummy[kk] = -1.0;
					dataMatrix[demo] = newLine;
				}
				dataMatrix[demo].cbc[signalIndex]=res[count].val;// dirty trick, index goes beyond cbc to biochemistry etc.
				//replicate demography and cancer
				dataMatrix[demo].id=thisID;
				dataMatrix[demo].date=demo.date;

				dataMatrix[demo].birthDate=thisByear*10000+101;// change from year o yyyymmdd
				dataMatrix[demo].dummyAge= 2010 - thisByear;
				dataMatrix[demo].gender=thisGender - 1; // in repository, male=1 and female=2; in bin file, male=0 and female=1
 				dataMatrix[demo].status=thisStatus;
				dataMatrix[demo].statusDate=thisStatusDate;
				dataMatrix[demo].cancer=thisCancer;
				dataMatrix[demo].cancerDate=thisCancerDate;
			}					
		}				
	}
	// move from map to linear lines matrix
	int nlines=(int)dataMatrix.size();
	*linesM=(matrixLinesType )malloc(sizeof(**linesM)*nlines);
	assert(linesM);
	fprintf(stderr,"\nDEBUG nlines=%d \n",nlines);fflush(stderr);
	assert(linesM>0);
	int ki=0;
	for( auto kk=dataMatrix.begin();kk!=dataMatrix.end();kk++){
		memcpy(*linesM+ki,&(kk->second),sizeof(**linesM));
		/*
		fprintf(stderr,"\nDEBUG k=%d  %f %f %f %f \n",k,kk->second.id,kk->second.date,kk->second.plt,kk->second.cbc[3]);fflush(stderr);
		fprintf(stderr,"DEBUG XXX %f %f %f\n",(*linesM)[k][0],(*linesM)[k][1],(*linesM)[k][2]); 
		*/
		ki++;
	}
	//fprintf(stderr,"\nDEBUG k=%d \n",k);fflush(stderr);

	return(nlines);

};

// Process a virtual bin file which holds paths of bin file and (optionally) registry, id@date list, cancer type identifier, etc.
int processVirtualBinFile(gzFile binFile, linearLinesType *lines) {

	// Maximal numbers of entries of each kind
	map<string,int> multiple_entry_fields ;
	multiple_entry_fields["#id_list"] = 1 ;

	// cerr << "Starting processVirtualBinFile on file " << binFile->_base << endl;
	
	string lineStr;
	int num_vbf_lines = 0;
	map<string, vector<string> > cfg;
	while (gzGetLine(binFile, lineStr) != NULL) {

		vector<string> fields;
		split(fields, lineStr, is_any_of("\t ")); 
		num_vbf_lines ++;
		// for (int i = 0; i < fields.size(); i++) cerr << "Field #" << i << ": " << fields[i] << endl;

		if (num_vbf_lines == 1) {
			assert(fields.size() == 1 && fields[0] == "#VBF"); // verify the magic number
		}
		else {
			assert(fields.size() == 2);

			assert(cfg.find(fields[0]) == cfg.end() || multiple_entry_fields.find(fields[0]) != multiple_entry_fields.end()); // each config item must appear at most once
			cfg[fields[0]].push_back(fields[1]) ;
		}
		
	}	
	// cerr << "Read " << num_vbf_lines << " config lines from virtual bin file" << endl;

	map<int, set<int>> id_list; 
	bool filter_id = false;
	if (cfg.find("#id_list") != cfg.end()) {
		filter_id = true;
		for (unsigned int iid=0; iid<cfg["#id_list"].size(); iid++)
			readIdDateList(cfg["#id_list"][iid],id_list);
		cerr << "Finished reading id_list with " << id_list.size() << " numerators" << endl;
	}

	map<int, vector<reg_entry> > reg;
	bool use_reg = false;
	if (cfg.find("#reg") != cfg.end()) {
		use_reg = true;
		assert(cfg.find("#group") != cfg.end());
		int group=atoi(cfg["#group"][0].c_str());
		string groups_fn = ""; // defaults to GRP_FILE
		if (cfg.find("#groups_file") != cfg.end()) groups_fn = cfg["#groups_file"][0];
		set<string> regDirs = readRegDirsFromGroupsFile(group, groups_fn);
		reg = readCancerRegistry(regDirs, cfg["#reg"][0].c_str());
		cerr << "Finished reading registry with " << reg.size() << " numerators" << endl;
	}
	
	vector<string> signals;
	if (cfg.find("#signal_list") != cfg.end()) {
		readSignals(cfg["#signal_list"][0], &signals);
		cerr << "Finished reading signal_list with " << signals.size() << " signals" << endl;
	}

	if (cfg.find("#rep") != cfg.end()) {
		MedRepository repository;
		assert(!use_reg);
		assert(cfg.find("#bin") == cfg.end());
		string repName=cfg["#rep"][0].c_str();

		// Build vector of ids to read
		vector<int> ids;
		for (auto rec : id_list) {
			ids.push_back(rec.first);
		}

		if (repository.read_all(repName, ids, signals) == -1) {
			fprintf(stderr, "Read repository failed\n");
			return -1;
		}
		matrixLinesType linesM;

		if(cfg.find("#groups")==cfg.end())cfg["#groups"].push_back("DONT EXIST");
		int nlines=buildBinFromRepository(repository,id_list,cfg["#groups"][0],&linesM);
		/*
		for(int kkk=0;kkk<10;kkk++)fprintf(stderr,"DEBUG XXX %f %f %f\n",linesM[kkk][0],linesM[kkk][1],linesM[kkk][2]); 
		fprintf(stderr,"\nDEBUG nlines=%d \n",nlines);fflush(stderr);
		*/
		*lines=(linearLinesType) linesM;
		return(nlines);
	}

	assert(cfg.find("#bin") != cfg.end());
	gzFile newBinFile = safe_gzopen(cfg["#bin"][0].c_str(), "rb");
	int nlines = readInputLines(newBinFile, lines);
	matrixLinesType linesM = (double (*)[MAXCOLS]) *lines; 
	int nfilt = 0;

	if (filter_id == false && use_reg == false) {
		nfilt = nlines;
	}
	else {
		for (int iline = 0; iline < nlines; iline++) {
			// cerr << linesM[iline][ID_COL] << ", " 
			//	<< linesM[iline][DATE_COL] << endl;	
			int id = int(linesM[iline][ID_COL]);
			int date = int(linesM[iline][DATE_COL]);
			if (use_reg) {
				linesM[iline][CANCER_COL] = 0;
				if (reg.find(id) != reg.end()) {
					reg_entry& ent = reg[id][0];
					linesM[iline][CANCER_COL] = ent.type;
					linesM[iline][CANCER_DATE_COL] = ent.date;
				}
			}
			if (filter_id) {
				// cerr << "Working on " << id << "@" << date << " in line " << iline << endl;
				if (id_list.find(id) != id_list.end() &&
					(id_list[id].empty() || 
					id_list[id].find(date) != id_list[id].end())) {
					// cerr << "Moving line " << iline << " to line " << nfilt << endl;
					memmove(*lines + nfilt * MAXCOLS, *lines + iline * MAXCOLS, MAXCOLS * sizeof(double));
					// cerr << linesM[nfilt][ID_COL] << ", "  << linesM[nfilt][DATE_COL] << endl;	
					nfilt++;
				}
				else {
					// cerr << id << "@" << date << " not in id_list " << endl;
				}
			}
			else {
				nfilt++;
			}
			// cerr << "Finished working on line " << iline << endl;
		}
		if (nfilt < nlines) {
			*lines = (linearLinesType) realloc(*lines, nfilt * MAXCOLS * sizeof(double));
			assert(lines != NULL);
		}
	}

	return(nfilt);
}

// Read bin file
int readInputLines(gzFile binFile, linearLinesType *lines) // includes lines allocation
{
	// read the number of lines (first 4 bytes in the bin file)
	int nlines;
	int bytes_read = gzread(binFile, &nlines, sizeof(nlines));
	assert(bytes_read == 4);

	if (nlines == 1178752547) { // magic number of virtual bin file
		gzseek(binFile, 0, SEEK_SET);
		fprintf(stderr, "Reading a virtual bin file ...\n");
		nlines = processVirtualBinFile(binFile, lines);
		fprintf(stderr, "Finished reading a virtual bin file, nlines=%d\n", nlines);
		assert(nlines > 0);
		return(nlines);
	}

	fprintf(stderr,"Going to read %d lines\n",nlines) ;
	assert(nlines > 0 && nlines <= MAXLINES); 

	// allocate the needed number of lines
	*lines  = (linearLinesType ) malloc (nlines * MAXCOLS * sizeof(double)) ;
	if (*lines == NULL) {
		fprintf(stderr,"Cannot allocate lines\n") ;
		return -1 ;
	}
	fprintf(stderr,"Memory for %d lines was allocated\n", nlines);

	// read lines in possibly several blocks to bypass gzread limitation of 2GB
	long numReadLines = 0;
	int numLinesInBlock = int(2000000000 / MAXCOLS / sizeof(double));
	int blockSize = sizeof(double) * MAXCOLS * numLinesInBlock;
	bool reachedEOF = false;
	while (numReadLines < nlines && ! reachedEOF) {
		int maxRead = (blockSize < (nlines - numReadLines) * sizeof(double) * MAXCOLS) ? blockSize : (nlines - numReadLines) * sizeof(double) * MAXCOLS;
		fprintf(stderr, "Trying to read at most %d bytes ...\n", maxRead);
		int nread = gzread(binFile,  (*lines) + MAXCOLS * numReadLines, maxRead);
		fprintf(stderr, "Read %d bytes\n", nread); fflush(stderr);
		if (nread < maxRead) {
            if (gzeof (binFile)) {
				fprintf(stderr, "EOF reached\n");
				reachedEOF = true;
            }
            else {
				fprintf(stderr, "Incompatible partial read and EOF status, nread=%d, blockSize=%d\n", nread, blockSize);
				int err;
                const char * error_string;
                error_string = gzerror (binFile, &err);
                if (err) {
                    fprintf (stderr, "Error in gzread() after already reading %d lines in %d blocks: %s\n", numReadLines, numReadLines/numLinesInBlock, error_string); fflush(stderr);
                    return -1;
                }
            }
        }
		numReadLines += nread / sizeof(double) / MAXCOLS;
	}

	fprintf(stderr, "Read %d lines\n", numReadLines);
	assert(numReadLines == nlines);

	return(nlines);
}

vector<bool> featureFlagsAsBoolVecForClipping(feature_flags& fflags) {
	vector<bool> res(MAXCOLS, false);
		
	res[AGE_COL] = (fflags.age == 1);
	res[GENDER_COL] = (fflags.gender == 1);
		
	for (int i = 0; i < NCBC; ++i) {
		res[TEST_COL + i] = (fflags.cbcs[i] == 1);
	}
		
	for (int i = 0; i < NBIOCHEM; ++i) {
		res[TEST_COL + NCBC + i] = (fflags.biochems[i] == 1);
	}
		
	for (int i = 0; i < BMI_NCOLS; ++i) {
		res[BMI_COL + i] = (fflags.bmi == 1);
	}
		
	for (int i = 0; i < SMX_NCOLS; ++i) {
		res[SMX_COL + i] = (fflags.smx == 1);
	}
		
	for (int i = 0; i < QTY_SMX_NCOLS; ++i) {
		res[QTY_SMX_COL + i] = (fflags.qty_smx == 1);
	}

	return(res);
}


int adjustColMaskByFeatureFlags(bool* col_mask, feature_flags fflags) {
	vector<bool> v = featureFlagsAsBoolVecForClipping(fflags);
	
	int nftrOff = 0;
	for (int i = 0; i < MAXCOLS; ++i) {
		if (col_mask[i] == true && v[i] == false) {
			col_mask[i] = false;
			++nftrOff;
		}
	}

	return(nftrOff);
}

// Clearing outliers - Get Min and Max vectors - using moments on central data
int get_clipping_params_central(double *xtable, int npatient, int nvar, double missing, double *min, double *max, double central_p, double std_factor, double max_std, bool colon_mask[])
{

	// Moments
	double *avg = (double *) malloc (nvar*sizeof(double)) ;
	double *std = (double *) malloc (nvar*sizeof(double)) ;
	if (avg==NULL || std==NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}

	// Statistics on middle part
	if (calc_partial_stats(xtable,npatient,nvar,central_p,avg,std,missing) == -1) {
		fprintf(stderr,"Cannot calucluate partial moments\n") ;
		return -1 ;
	}
	fprintf(stderr,"DEBUG %d nftrs\n",nvar);
	for (int i=0; i<nvar; i++) {
		
		if (colon_mask[i]) {
			fprintf(stderr,"DEBUG %d %f %f  sd\n",i,avg[i],std[i]);
			if (std[i] == -1.0) {
				fprintf(stderr,"Warning : Cannot calculate moments for required variable %d\n",i) ;
				min[i] = -DBL_MAX ;
				max[i] = DBL_MAX ;
			} else {
				min[i] = avg[i] - max_std*std_factor*std[i] ;
				max[i] = avg[i] + max_std*std_factor*std[i] ;
			}
		} else {
			min[i] = -DBL_MAX ;
			max[i] = DBL_MAX ;
		}
	}

	free(avg) ; 
	free(std) ;

	return 0 ;
}

// Clearing outliers - Get Min and Max vectors - using iterative clearing of the data
int get_clipping_params_iterative(double *_xtable, int npatient, int nvar, double missing, double *min, double *max, int niter, double max_std, bool colon_mask[])
{

	// Moments
	double *avg = (double *) malloc (nvar*sizeof(double)) ;
	double *std = (double *) malloc (nvar*sizeof(double)) ;
	if (avg==NULL || std==NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}

	// Copy xtable
	double *xtable = (double *) malloc(nvar*npatient*sizeof(double)) ;
	if (xtable == NULL) {
		fprintf(stderr,"Allocation Failed for %d x %d\n",nvar,npatient) ;
		return -1 ;
	}
	memcpy(xtable,_xtable,nvar*npatient*sizeof(double)) ;

	// iterative cleaning
	if (clear_data(xtable,avg,std,npatient,nvar,niter,max_std,colon_mask,missing) == -1) {
		fprintf(stderr,"Cannot calucluate partial moments\n") ;
		return -1 ;
	}

	fprintf(stderr,"DEBUG %d nftrs\n",nvar);
	for (int i=0; i<nvar; i++) {
		
		if (colon_mask[i]) {
			fprintf(stderr,"DEBUG %d %f %f  sd\n",i,avg[i],std[i]);
			if (std[i] == -1.0) {
				fprintf(stderr,"Warning : Cannot calculate moments for required variable %d\n",i) ;
				min[i] = -DBL_MAX ;
				max[i] = DBL_MAX ;
			} else {
				min[i] = avg[i] - max_std*std[i] ;
				max[i] = avg[i] + max_std*std[i] ;
			}
		} else {
			min[i] = -DBL_MAX ;
			max[i] = DBL_MAX ;
		}
	}

	free(avg) ; 
	free(std) ;
	free(xtable) ;

	return 0 ;
}

// Clearing outliers - Envelope for xy_data.
int get_clipping_params_central(xy_data *xy, double central_p, double std_factor, double max_std, double missing, double **min, double **max, bool colon_mask[]) 
{

	*min = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	*max = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	if ((*min)==NULL || (*max)==NULL)
		return -1 ;

	int rc = get_clipping_params_central(xy->x,xy->nrows,xy->nftrs,missing,*min,*max,central_p,std_factor,max_std,colon_mask) ;
	if (rc ==-1) {
		fprintf(stderr,"Clearing failed\n") ;
		return -1 ;
	}

	return rc ;
}

int get_clipping_params_iterative(xy_data *xy, int niter, double max_std, double missing, double **min, double **max, bool colon_mask[]) 
{

	*min = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	*max = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	if ((*min)==NULL || (*max)==NULL)
		return -1 ;

	int rc = get_clipping_params_iterative(xy->x,xy->nrows,xy->nftrs,missing,*min,*max,niter,max_std,colon_mask) ;
	if (rc ==-1) {
		fprintf(stderr,"Clearing failed\n") ;
		return -1 ;
	}

	return rc ;
}

// Clearning outliers - get moments
int get_cleaning_moments(double *_xtable, int npatient, int nvar, double missing, double *avg, double *std, int niter, double max_std, bool colon_mask[])
{

	// Copy xtable
	double *xtable = (double *) malloc(nvar*npatient*sizeof(double)) ;
	if (xtable == NULL) {
		fprintf(stderr,"Allocation Failed for %d x %d\n",nvar,npatient) ;
		return -1 ;
	}
	memcpy(xtable,_xtable,nvar*npatient*sizeof(double)) ;

	// iterative cleaning
	if (clear_data(xtable,avg,std,npatient,nvar,niter,max_std,colon_mask,missing) == -1) {
		fprintf(stderr,"Cannot calucluate partial moments\n") ;
		return -1 ;
	}

	free(xtable) ;

	return 0 ;
}

int get_cleaning_moments(xy_data *xy, int niter, double max_std, double missing, double **avg, double **std, bool colon_mask[]) {

	*avg = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	*std = (double *) malloc((xy->nftrs)*sizeof(double)) ;
	if ((*avg)==NULL || (*std)==NULL)
		return -1 ;

	// MASKED
	int rc = get_cleaning_moments(xy->x,xy->nrows,xy->nftrs,missing,*avg,*std,niter,max_std,colon_mask) ;

	if (rc ==-1) {
		fprintf(stderr,"Clearing failed\n") ;
		return -1 ;
	}

	// NON-MASKED
	for (int i=0; i<xy->nftrs; i++) {
		if (! colon_mask[i]) {
			(*avg)[i] = 0 ;
			(*std)[i] = DBL_MAX/max_std ;
		}
	}

	return rc ;
}

int get_cleaning_minmax(double *avg, double *std, double *min_orig_data, double max_std, double **min, double **max, int nftrs, bool colon_mask[]) {
	
	*min = (double *) malloc(nftrs*sizeof(double)) ;
	*max = (double *) malloc(nftrs*sizeof(double)) ;
	if ((*min)==NULL || (*max)==NULL)
		return -1 ;


	for (int i=0; i<nftrs; i++) {
		if (colon_mask[i]) {
			(*max)[i] = avg[i] + max_std * std[i] ;
			(*min)[i] = avg[i] - max_std * std[i] ;

			// CBCS
			if (i >= TEST_COL && i < TEST_COL+NCBC) {
				int idx = i - TEST_COL ;
				// Min
				if (log_cols[idx] && (*min)[i] < log(min_orig_data[i]/2.0))
					(*min)[i] = log(min_orig_data[i]/2.0) ;
				else if (!log_cols[idx] && (*min)[i] < 0)
					(*min)[i] = 0.0 ;

				// MAX 
				if (cbc_percentage[idx]) {
					if (log_cols[idx] && (*max)[i] > log(100.0))
						(*max)[i] = log(100.0) ;
					else if (!log_cols[idx] && (*max)[i] > 100.0)
						(*max)[i] = 100.0 ;
				}
			}

			// BioChem
			if (i >= TEST_COL+NCBC && i < TEST_COL+NCBC+NBIOCHEM && (*min)[i] < 0) {
				(*min)[i] = 0.0 ;
			}
		} else {
			(*min)[i] = -DBL_MAX ;
			(*max)[i] =  DBL_MAX ;
		}
	}

	return 0 ;

}

void clean_from_moments(xy_data *xy, double *avg, double *std, double *min, double *max, double missing, double max_sdvs_for_clps, double max_sdvs_for_nbrs) {

	int start = 0 ;
	int id = (int) (xy->x)[XIDX(start,ID_COL,xy->nftrs)] ;

	map<int,pair<int,int> > ftrs_counters ; 
	vector<int> lines_counters  ;
	
	int nremoved = 0, nclipped = 0 ;

	while (start < xy->nrows) {
		int stop = start ;

		while ((xy->x)[XIDX(stop,ID_COL,xy->nftrs)] == id && stop<xy->nrows)
			stop ++ ;

		cln_from_moments(xy->x,xy->nftrs,start,stop-1,avg,std,min,max,missing,max_sdvs_for_clps,max_sdvs_for_nbrs,ftrs_counters,lines_counters) ;

		for (auto it:ftrs_counters) {
			nremoved += it.second.first ;
			nclipped += it.second.second ;
		}

		start = stop ;
		id = (int) (xy->x)[XIDX(start,ID_COL,xy->nftrs)] ;
	}

	fprintf(stderr,"Cleaning : %d Removed ; %d Clipped\n",nremoved,nclipped) ;
}

void cln_from_moments(double *x, int nftrs, int from, int to, double *avg, double *std, double *min, double *max, double missing, double max_sdvs_for_clps, double max_sdvs_for_nbrs, map<int,pair<int,int> >& ftrs_counters, 
					 vector<int>& lines_counters) {

	lines_counters.resize((to-from+1),0) ;

	for( int j = 0; j < nftrs; j++) {

		map<int,int> candidates ;
		ftrs_counters[j] = pair<int,int>(0,0) ;

		for( int i = from; i <= to ; i++ ) {

			double val = x[XIDX(i,j,nftrs)] ;
			if (val == missing)
				continue ;
			

			// Remove ?
			if (val < min[j] - CLEANING_EPS || val > max[j] + CLEANING_EPS) {
				ftrs_counters[j].first ++ ;
				lines_counters[i-from] ++ ;				
				x[XIDX(i,j,nftrs)] = avg[j] ;
//				fprintf(stderr,"Removing %d %d %d %f [%f,%f] : [%f,%f] -> %f\n",(int) x[XIDX(i,ID_COL,nftrs)],(int) x[XIDX(i,DATE_COL,nftrs)],j-TEST_COL,val,min[j],max[j],min[j] - CLEANING_EPS, 
//					max[j] + CLEANING_EPS,avg[j]) ;
				continue;
			}

			// Collect clipping candidates
			if (std[j] != -1.0) {
				if (val > avg[j] + max_sdvs_for_clps * std[j] + CLEANING_EPS)
					candidates[i] = 1 ;
				else if (val < avg[j] - max_sdvs_for_clps * std[j] - CLEANING_EPS)
					candidates[i] = -1 ;
			}
		}
		
		// Check candidates
		for (auto candidate:candidates) {
			int i = candidate.first ;
			int dir = candidate.second ;

			// Get weighted values
			double sum=0, norm = 0 ;
			double priorSum=0, priorNorm = 0 ;
			double postSum=0, postNorm = 0 ;
		
			int days = get_day(((int) x[XIDX(i,DATE_COL,nftrs)])) ;
			for (int idx=from; idx<= to; idx++) {
				if (idx != i && x[XIDX(idx,j,nftrs)] != missing) {
					int diff = abs(get_day((int) x[XIDX(idx,DATE_COL,nftrs)]) - days)/7 ;
					double w = 1.0/(diff+1) ;

					sum += w * x[XIDX(idx,j,nftrs)] ;
					norm += w ;

					if (idx>i) {
						postSum += w * x[XIDX(idx,j,nftrs)] ;
						postNorm += w ;
					} else {
						priorSum += w * x[XIDX(idx,j,nftrs)] ;
						priorNorm += w ;
					}
				}
			}

			// Check it up
			int found_nbr = 0;
			if (norm > 0) {
				double win_val = sum/norm ;
				if ((dir == 1 && win_val > avg[j] + max_sdvs_for_nbrs * std[j]) || (dir == -1 && win_val < avg[j] - max_sdvs_for_nbrs * std[j]))
					found_nbr = 1 ;
			}

			if (! found_nbr && priorNorm > 0) {
				double win_val = priorSum/priorNorm ;
				if ((dir == 1 && win_val > avg[j] + max_sdvs_for_nbrs * std[j]) || (dir == -1 && win_val < avg[j] - max_sdvs_for_nbrs * std[j]))
					found_nbr = 1 ;
			}

			if (! found_nbr && postNorm > 0) {
				double win_val = postSum/postNorm ;
				if ((dir == 1 && win_val > avg[j] + max_sdvs_for_nbrs * std[j]) || (dir == -1 && win_val < avg[j] - max_sdvs_for_nbrs * std[j]))
					found_nbr = 1 ;
			}
			
			// Should we clip ?
			if (! found_nbr) {
				lines_counters[i - from] ++;
				ftrs_counters[j].second ++ ;
				if (dir == 1) {
//					fprintf(stderr,"Clipping %d %d %d %f\n",(int) x[XIDX(i,ID_COL,nftrs)],(int) x[XIDX(i,DATE_COL,nftrs)],j-TEST_COL,x[XIDX(i,j,nftrs)]) ;
					x[XIDX(i,j,nftrs)] = avg[j] + max_sdvs_for_clps * std[j] ;					
				} else {
//					fprintf(stderr,"Clipping %d %d %d %f\n",(int) x[XIDX(i,ID_COL,nftrs)],(int) x[XIDX(i,DATE_COL,nftrs)],j-TEST_COL,x[XIDX(i,j,nftrs)]) ;
					x[XIDX(i,j,nftrs)] = avg[j] - max_sdvs_for_clps * std[j] ;
				}
			}
		}
	}
}

// Initial clipping update - Minimal value of min is 0, max for percentage is 100.
void update_clipping_params(double *min, double *max, bool *colon_mask) {

	for (int i=0; i<MAXCOLS; i++) {
		if (colon_mask[i]) {
			if ((i>=TEST_COL && i<TEST_COL+NCBC) && log_cols[i-TEST_COL]) {
				if (min[i] < log(MIN_VAL_FOR_LOG))
					min[i] = log(MIN_VAL_FOR_LOG) ;
			} else {
				if (min[i] < 0)
					min[i] = 0.0 ;
			}
			if ((i>=TEST_COL && i<TEST_COL+NCBC) && cbc_percentage[i-TEST_COL])
				if (log_cols[i-TEST_COL])
					max[i] = log(100.0) ;
				else
					max[i] = 100.0 ;
		}
	}

	return ;
}

void update_clipping_params(double *min, double *max, feature_flags& fflags, int square) {

	// Correct - Features must be non-negatives, percentage <= 100
	int iftr = fflags.gender ;
	for (int icbc=0; icbc<NCBC; icbc++) {
		if (fflags.cbcs[icbc]) {
			if (log_cols[icbc] && min[iftr] < log(MIN_VAL_FOR_LOG))
				min[iftr] = log(MIN_VAL_FOR_LOG) ;
			else if ((! log_cols[icbc]) && min[iftr] < 0)
				min[iftr] = 0 ;

			if (cbc_percentage[icbc]) {
				if (log_cols[icbc])
					max[iftr] = log(100.0) ;
				else
					max[iftr] = 100 ;
			}

			iftr += (ngaps + 3) ;
		}
	}

	for (int ibio=0; ibio<NBIOCHEM; ibio++) {
		if (fflags.biochems[ibio]) {
			if (min[iftr] < 0)
				min[iftr] = 0 ;
			iftr += (ngaps + 3) ;
		}
	}

	if (square) {
		iftr += fflags.gender ;
		for (int icbc=0; icbc<NCBC; icbc++) {
			if (fflags.cbcs[icbc]) {
				if (log_cols[icbc] && min[iftr] < log(MIN_VAL_FOR_LOG))
					min[iftr] = log(MIN_VAL_FOR_LOG) ;
				else if ((! log_cols[icbc]) && min[iftr] < 0)
					min[iftr] = 0 ;

				if (cbc_percentage[icbc]) {
					if (log_cols[icbc])
						max[iftr] = log(100.0) ;
					else
						max[iftr] = 100 ;
				}

				iftr += (ngaps + 3) ;
			}
		}

		for (int ibio=0; ibio<NBIOCHEM; ibio++) {
			if (fflags.biochems[ibio] < 0) {
				if (min[iftr] < 0)
					min[iftr] = 0 ;
				iftr += (ngaps + 3) ;
			}
		}

	}


	return ;
}

int take_squares(xy_data *xy) {

	if ((xy->x = (double *) realloc(xy->x,xy->nrows*(xy->nftrs)*2*sizeof(double))) == NULL) {
		fprintf(stderr,"Reallocation failed\n") ;
		return -1 ;
	}

	for (int i=xy->nrows-1; i>=0; i--) {
		for (int j=0; j<xy->nftrs; j++) {
			(xy->x)[XIDX(i,j,2*(xy->nftrs))] = (xy->x)[XIDX(i,j,xy->nftrs)] ;
			if ((xy->x)[XIDX(i,j,xy->nftrs)] == MISSING_VAL)
				(xy->x)[XIDX(i,j+(xy->nftrs),2*(xy->nftrs))] = MISSING_VAL ;
			else
				(xy->x)[XIDX(i,j+(xy->nftrs),2*(xy->nftrs))] = (xy->x)[XIDX(i,j,xy->nftrs)] * (xy->x)[XIDX(i,j,xy->nftrs)] ;
		}
	}

	(xy->nftrs) *= 2 ;
	return 0 ;
}

int clear_data_from_bounds(xy_data *xy, double missing, double *minx, double *maxx) {
	
	int nclear = 0 ;
	for( int i = 0; i < xy->nrows; i++ ) {
		for( int j = 0; j < xy->nftrs; j++) {
			

			if ((xy->x)[XIDX(i,j,xy->nftrs)]==missing) continue;
			if ((xy->x)[XIDX(i,j,xy->nftrs)] > maxx[j] ) {
				(xy->x)[XIDX(i,j,xy->nftrs)] = maxx[j] ;
				nclear++ ;
			}
			if ((xy->x)[XIDX(i,j,xy->nftrs)] < minx[j] ) {
				(xy->x)[XIDX(i,j,xy->nftrs)] = minx[j] ;
				nclear++ ;
			}
		}
	}

	fprintf(stderr,"Cleared %d entries\n",nclear) ;
	return 0 ;
}

int process_and_filter_data(double *x, double **nx, int *nrows, int *nftrs, double *avg, double *std, double max_std, int take_squares, int *idnums, int *dates, FILE *flog) {

	int new_nftrs = (*nftrs);
	if (take_squares)
		new_nftrs *= 2;

	if (((*nx) = (double *) malloc ((*nrows) * new_nftrs * sizeof(double)))==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for (int i=0; i<(*nrows); i++) {
		for (int j=0; j<(*nftrs); j++) {
			(*nx)[XIDX(i,j,new_nftrs)] = x[XIDX(i,j,*nftrs)] ;
			if (take_squares) {
				if (x[XIDX(i,j,*nftrs)] ==	MISSING_VAL) {
					(*nx)[XIDX(i,j+(*nftrs),new_nftrs)] = MISSING_VAL ;
				} else {
					(*nx)[XIDX(i,j+(*nftrs),new_nftrs)] = x[XIDX(i,j,*nftrs)] * x[XIDX(i,j,*nftrs)] ;
				}
			}
		}
	}

	*nftrs = new_nftrs ;

	int nclear = 0 ;
	int out_nrows = 0 ;
	for( int i = 0; i < (*nrows); i++ ) {
		int nclipped = 0 ;
		for( int j = 0; j < new_nftrs; j++) {

			if ((*nx)[XIDX(i,j,new_nftrs)]!=MISSING_VAL && (*nx)[XIDX(i,j,new_nftrs)] > avg[j] +  max_std * std[j] ) {
				(*nx)[XIDX(out_nrows,j,new_nftrs)] = avg[j] +  max_std * std[j] ;
				nclear++ ;
				nclipped ++ ;
			} else if ((*nx)[XIDX(i,j,new_nftrs)]!=MISSING_VAL &&  (*nx)[XIDX(i,j,new_nftrs)] < avg[j] - max_std * std[j] ) {
				(*nx)[XIDX(out_nrows,j,new_nftrs)] = avg[j] - max_std * std[j] ;
				nclear++ ;
				nclipped++ ;
			} else
				(*nx)[XIDX(out_nrows,j,new_nftrs)] = (*nx)[XIDX(i,j,new_nftrs)] ;

			if (nclipped > MAX_CLIPPED)
				break ;

		}

		if (nclipped <= MAX_CLIPPED) {
			idnums[out_nrows] = idnums[i] ;
			dates[out_nrows] = dates[i] ;
			out_nrows++ ;
		} else
			fprintf(flog,"Ignoring %d@%d for too many clipping\n",idnums[i],dates[i]) ;
	}

	fprintf(stderr,"Cleared %d entries\n",nclear) ;
	fprintf(stderr,"Changed from %d to %d lines\n",*nrows,out_nrows) ;
	*nrows = out_nrows ;

	return 0 ;
}

void handleOutliersParams(FILE *fileDes, double *means_for_completion, double *sdvs_for_completion, cleaner& cln) {

	// Completion
	for (int i=0; i<cln.nftrs; i++) 
		fprintf(fileDes,"Completion %d %lf %lf\n",i,means_for_completion[i],sdvs_for_completion[i]) ;


	// Min and Max Values
	if (cln.mode == 0) {
		fprintf(fileDes,"NBounds1 %d\n",cln.ndata) ;
		for (int i=0; i<MAXCOLS; i++)
			fprintf(fileDes,"Bounds1 %d %g %g\n",i,cln.data_min[i],cln.data_max[i]) ;

		fprintf(fileDes,"NBounds2 %d\n",cln.nftrs) ;
		for (int i=0; i<cln.nftrs; i++)
			fprintf(fileDes,"Bounds2 %d %g %g\n",i,cln.ftrs_min[i],cln.ftrs_max[i]) ;
	} else {
		// Cleaning
		fprintf(fileDes,"NCleaning %d\n",cln.ndata) ;
		for (int i=0; i<cln.ndata; i++)
			fprintf(fileDes,"Cleaning %d %g %g %g %g %g\n",i,cln.min_orig_data[i], cln.data_avg[i],cln.data_std[i],cln.data_min[i],cln.data_max[i]) ;
	}
}

void init_methods_map (map <string, int>& methodMap) {

	methodMap["RF"]=0;
	methodMap["GBM"]=1;
	methodMap["RFGBM"]=2;
	methodMap["LM"]=3;
	methodMap["LUNG_GBM"]=4;
	methodMap["ENSGBM"]=6;
	methodMap["LP"]=8;

	methodMap["RFGBM2"] = 9 ;
	methodMap["DoubleMatched"] = 10 ;
	methodMap["TwoSteps"] = 11 ;

	methodMap["QRF"] = 12;
}

void clear_xy(xy_data *xy)  {
	if (xy->censor != NULL)
		free(xy->censor) ;

	if (xy->dates != NULL)
		free(xy->dates) ;

	if (xy->flags != NULL)
		free(xy->flags) ;

	if (xy->idnums != NULL)
		free(xy->idnums) ;

	if (xy->w != NULL)
		free(xy->w) ;

	if (xy->x != NULL)
		free(xy->x) ;

	if (xy->y != NULL)
		free(xy->y) ;
}

void init_xy(xy_data *xy) {
	xy->censor = NULL ;
	xy->dates = NULL ;
	xy->flags = NULL ;
	xy->idnums = NULL ;
	xy->w = NULL ;
	xy->x = NULL ;
	xy->y = NULL ;
}

int allocate_xy(xy_data *xy) {

	xy->censor = (int *) malloc(xy->nrows * sizeof(int)) ;
	xy->dates = (int *) malloc(xy->nrows * sizeof(int)) ;
	xy->flags = (int *) malloc(xy->nrows * sizeof(int)) ;
	xy->idnums = (int *) malloc(xy->nrows * sizeof(int)) ;
	xy->w = (double *) malloc(xy->nrows * sizeof(double)) ;
	xy->y = (double *) malloc(xy->nrows * sizeof(double)) ;
	xy->x = (double *) malloc(xy->nrows * xy->nftrs * sizeof(double)) ;

	if (xy->censor==NULL || xy->dates==NULL || xy->flags==NULL || xy->idnums==NULL || xy->w==NULL || xy->y==NULL || xy->x==NULL)
		return -1 ;
	else
		return 0 ;
}

int copy_xy(xy_data *dest, xy_data *orig) {

	dest->nrows = orig->nrows ;
	dest->nftrs = orig->nftrs ;

	(dest->x) = (double *) malloc((orig->nrows)*(orig->nftrs)*sizeof(double)) ;
	if (dest->x == NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}
	memcpy(dest->x,orig->x,(orig->nrows)*(orig->nftrs)*sizeof(double)) ;

	if (orig->censor != NULL) {
		(dest->censor) = (int *) malloc((orig->nrows)*sizeof(int)) ;
		if (dest->censor == NULL) {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
		}
		memcpy(dest->censor,orig->censor,(orig->nrows)*sizeof(int)) ;
	} else
		dest->censor = NULL ;

	if (orig->dates != NULL) {
		(dest->dates) = (int *) malloc((orig->nrows)*sizeof(int)) ;
		if (dest->dates == NULL) {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
		}
		memcpy(dest->dates,orig->dates,(orig->nrows)*sizeof(int)) ;
	} else
		dest->dates = NULL ;

	if (orig->flags != NULL) {
		(dest->flags) = (int *) malloc((orig->nrows)*sizeof(int)) ;
		if (dest->flags == NULL) {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
		}
		memcpy(dest->flags,orig->flags,(orig->nrows)*sizeof(int)) ;
	} else
		dest->flags = NULL ;
	

	if (orig->idnums != NULL) {
		(dest->idnums) = (int *) malloc((orig->nrows)*sizeof(int)) ;
		if (dest->idnums == NULL) {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
		}
		memcpy(dest->idnums,orig->idnums,(orig->nrows)*sizeof(int)) ;
	} else
		dest->idnums = NULL ;


	if (orig->w != NULL) {
		(dest->w) = (double *) malloc((orig->nrows)*sizeof(double)) ;
		if (dest->w == NULL) {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
		}
		memcpy(dest->w,orig->w,(orig->nrows)*sizeof(double)) ;
	} else
		dest->w = NULL ;
	
	if (orig->y != NULL) {
		(dest->y) = (double *) malloc((orig->nrows)*sizeof(double)) ;
		if (dest->y == NULL) {
			fprintf(stderr,"Allocation Failed\n") ;
			return -1 ;
		}
		memcpy(dest->y,orig->y,(orig->nrows)*sizeof(double)) ;
	} else
		dest->y = NULL ;
	

	return 0 ;

}

int init_predictor_info( programParamStrType& ps,feature_flags *fflags, generalized_predictor_info_t& predictor_info) {

	get_all_cols(fflags,predictor_info.field_cols) ;

	if (get_cols(ps.external_prior_field,predictor_info.field_cols,predictor_info.external_prior_cols) == -1)
		return -1 ;

	if (get_cols(ps.model_prior_field,predictor_info.field_cols,predictor_info.model_prior_cols) == -1) 
		return -1 ;

	predictor_info.incFile = ps.incFile ;
	predictor_info.method = ps.methodString ;
	predictor_info.two_stages = ps.two_stages ;
	predictor_info.internal_method = ps.internal_method ;
	predictor_info.external_method = ps.external_method ;
	predictor_info.nthreads = ps.nthreads ;
	predictor_info.ftrsFile = ps.ftrsOutFile;

	return 0 ;
}

int init_learner_info(programParamStrType& ps, gbm_parameters *gbm_params, feature_flags *fflags, double *lines, int nlines, int ncols, generalized_learner_info_t& learn_info) {

	learn_info.gbm_params=gbm_params;
	learn_info.gbm_ens_size=GBM_ENS_SIZE;
	strcpy(learn_info.rf_file_name,TREE_FILE);
	learn_info.nfold=ps.nfold;
	learn_info.seed=ps.seed;
	learn_info.combination_bound=COMBINATION_BOUND;
	learn_info.sp_nfold = ps.sp_nfold ;
	learn_info.sp_end_period = ps.sp_end_period ;
	learn_info.sp_start_period = ps.sp_start_period ;
	learn_info.matching_col.clear() ;
	learn_info.ts_nfold = ps.ts_nfold ;
	learn_info.matching_w = ps.matching_w ;
	learn_info.internal_method = ps.internal_method ;
	learn_info.external_method = ps.external_method ;
	learn_info.rf_ntrees = RF_NTREES ;
	learn_info.incFile = ps.incFile;
	learn_info.qrf_ntrees = QRF_NTREES;
	learn_info.qrf_ntry = QRF_NTRY;
	learn_info.qrf_max_quant = QRF_MAXQ;
	learn_info.nthreads = ps.nthreads ;

	get_all_cols(fflags,learn_info.field_cols) ;

	if (ps.matching_field != "no field") {
		istringstream matching_fields(ps.matching_field) ;
		istringstream matching_resolutions(ps.matching_res) ;
		
		string token ;

		while (getline(matching_fields,token,',')) {
			if (learn_info.field_cols.find(token) == learn_info.field_cols.end()) {
				fprintf(stderr,"Could not find matching column for %s\n",token.c_str()) ;
				return -1;
			}
			learn_info.matching_col.push_back(learn_info.field_cols[token]) ;
		}

		while (getline(matching_resolutions,token,','))
			learn_info.matching_res.push_back(atof(token.c_str())) ;

		if (learn_info.matching_col.size() != learn_info.matching_res.size()) {
			fprintf(stderr,"Size mismatch between matching_col and matching_res\n") ;
			return -1 ;
		}

		for (unsigned int i=0; i<learn_info.matching_col.size(); i++)
			fprintf(stderr,"Matching by column %d (%f)\n",learn_info.matching_col[i],learn_info.matching_res[i]) ;
	}

	// Combination GBM for RfGBM2
	gbm_parameters comb_gbm_params ;
	set_gbm_parameters("COMB_CRC",&comb_gbm_params) ;
	learn_info.comb_gbm_params = &comb_gbm_params ;

	// Registry
	if (learn_info.sp_nfold > 0 || ps.methodString == "DoubleMatched" ||  ps.methodString == "TwoSteps" )
		get_registry_from_lines(lines,nlines,ncols,learn_info.registry) ;

	return 0 ;
}

int get_cols(string fields, map<string,int>& cols_map, vector<int> &cols) {

	cols.clear() ;
	istringstream _fields(fields) ;

	string token ;
	if (fields != "no field") {
		while (getline(_fields,token,',')) {
			if (cols_map.find(token) == cols_map.end()) {
				fprintf(stderr,"Could not find matching column for %s\n",token.c_str()) ;
				return -1;
			}
			cols.push_back(cols_map[token]) ;
		}
	}

	return 0 ;
}

// Learn two-stages predictor. First on matched dataset, second on original-dataset + first step prdictions
int learn_two_stages_predictor(xy_data *xy, string method, generalized_learner_info_t *learning_info, unsigned char **model) {

	xy_data txy ;

	// Get Matched predictions
	copy_xy(&txy,xy) ;
	
	fprintf(stderr,"Getting matched predictions\n") ;
	map<pair<int,int>, double> preds_hash ;
	if (get_predictions(&txy,method,learning_info,learning_info->ts_nfold,preds_hash) == -1) {
		fprintf(stderr,"Get Predictions Failed\n") ;
		return -1 ;
	}
	
	clear_xy(&txy) ;
	
	// Add predictions to matrix
	copy_xy(&txy,xy) ;
	if (((txy.x) = (double *) realloc(txy.x,(txy.nrows)*(txy.nftrs + 1)*sizeof(double))) == NULL) {
		fprintf(stderr,"Reallocation Failed\n") ;
		return -1 ;
	}

	for (int i=0; i<(txy.nrows); i++) {
		pair<int,int> entry(txy.idnums[i],txy.dates[i]) ;
		if (preds_hash.find(entry) == preds_hash.end()) {
			fprintf(stderr,"Cannot find prediction for (%d,%d)\n",txy.idnums[i],txy.dates[i]) ;
			return -1 ;
		}

		(txy.x)[(txy.nrows)*(txy.nftrs) + i] = preds_hash[entry] ;
	}

	(txy.nftrs) ++ ;

	// Learn matched predictor
	fprintf(stderr,"Learning on matched data\n") ;
	
	unsigned char *initial_model ;
	learning_info->ts_nfold = 0 ;
	
	int size1 = learn_predictor(xy,method,learning_info,&initial_model) ;
	if (size1 == -1) {
		fprintf(stderr,"Learning of matched predictor failed\n") ;
		return -1 ;
	}

	// Learn secondary model
	fprintf(stderr,"Learning on un-matched data\n") ;
	
	unsigned char *seconday_model ;
	learning_info->matching_col.clear() ;

	int size2 = learn_predictor(&txy,method,learning_info,&seconday_model) ;
	if (size2 == -1) {
		fprintf(stderr,"Learning of matched predictor failed\n") ;
		return -1 ;
	}
	clear_xy(&txy) ;

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

int get_cnt_nperiods() {
	return nperiods ;
}

double get_spec_from_prob_gaussian_kernel(double prob, vector<pair<double,double> >& pred_to_spec) {

	// Identidy closest IDX
	int idx = 0 ;

	while (idx < pred_to_spec.size() && prob < pred_to_spec[idx].first)
		idx ++ ;
	
	// Get Spec
	if (idx == 0)
		return 100 ;
	else if (idx == pred_to_spec.size())
		return 0 ;
	else {
		int shift = 0 ;
		double sum = 0 , norm = 0 ;

		double z = abs(prob - pred_to_spec[idx].first)/SIGMA_FOR_SPEC_SMOOTHING ;
		double weight = exp(-(z*z)/2) ;
		sum += pred_to_spec[idx].second * weight ;
		norm += weight ;
		
		z = abs(prob - pred_to_spec[idx-1].first)/SIGMA_FOR_SPEC_SMOOTHING ;
		weight = exp(-(z*z)/2) ;
		sum += pred_to_spec[idx-1].second * weight ;
		norm += weight ;
		
		int didx = 1 ;
		while (idx-didx > 0 && idx+didx < pred_to_spec.size()) {
			double z1 = abs(prob - pred_to_spec[idx-1-didx].first)/SIGMA_FOR_SPEC_SMOOTHING ;
			double z2 = abs(prob - pred_to_spec[idx+didx].first)/SIGMA_FOR_SPEC_SMOOTHING ;
			if (z1 > MAX_Z_FOR_SPEC_SMOOTHING || z2 > MAX_Z_FOR_SPEC_SMOOTHING)
				break ;
	
			weight = exp(-(z1*z1)/2) ;
			sum += pred_to_spec[idx-1-didx].second * weight ;
			norm += weight ;
			
			weight = exp(-(z2*z2)/2) ;
			sum += pred_to_spec[idx+didx].second * weight ;
			norm += weight ;
			
			didx++ ;
		}

		return sum/norm ;
	}
}

double get_spec_from_prob(double prob, vector<pair<double,double> >& pred_to_spec) {

	// Identidy closest IDX

	int idx = 0 ;
	prob = ((int) (prob*1000 + 0.5))/1000.0 ;

	while (idx < pred_to_spec.size() && prob < pred_to_spec[idx].first)
		idx ++ ;

	// Get Spec
	if (idx == 0)
		return 100 ;
	else if (idx == pred_to_spec.size())
		return 0 ;
	else
		return (abs(prob - pred_to_spec[idx].first)*pred_to_spec[idx].second + abs(prob - pred_to_spec[idx-1].first)*pred_to_spec[idx-1].second)/abs(pred_to_spec[idx-1].first-pred_to_spec[idx].first);

}

// Set learning parameters
int set_parameters(FILE *fp) {

	char txtline[MAX_STRING_LEN] ;
	if (fp != NULL) {
		while (fgets(txtline, MAX_STRING_LEN, fp) != NULL) {
			size_t txtlen = strnlen(txtline, MAX_STRING_LEN);
			assert (txtlen > 0);
			assert (txtline[txtlen - 1] == '\n'); // verify full line

			// Get Rid of CRLF
			if (txtlen >= 2 && txtline[txtlen - 2] == '\r') {
				txtline[txtlen - 2] = '\n' ;
				txtlen -- ;
			}

			vector<string> fields;
			string str = string(txtline, txtline + (txtlen - 1));
			split(fields, str, is_any_of("\t ")); 

			if (fields[0] == "Gaps") {
				if (gaps != NULL || set_gaps(fields) == -1) {
					fprintf(stderr,"Failed setting gaps\n") ;
					return -1 ;
				}
			} else {
				fprintf(stderr,"Unknown learning parameter %s\n",fields[0].c_str()) ;
				return -1 ;
			}
		}
		fclose(fp) ;
	}

	// Complete missing parameters
	if (gaps == NULL) {
		vector<string> fields ;
		int n = sizeof(def_gaps)/sizeof(int) ;

		fields.push_back("Gaps") ;
		char field[MAX_STRING_LEN] ;
		for (int i=0; i<n; i++) {
			sprintf(field,"%d",def_gaps[i]) ;			
			fields.push_back(field) ;
		}

		set_gaps(fields) ;
	}

	return 0 ;
}

int set_gaps (vector<string>& fields) {

	ngaps = (int) fields.size() -1 ;
	gaps = (int *) malloc (ngaps*sizeof(int)) ;
	if (gaps == NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}

	int igap = 0 ;
	for (int i=0; i<ngaps; i++) {
		if (fields[i+1] == "")
			continue ;

		int gap = atoi(fields[i+1].c_str()) ;
		if (gap <= 0) {
			fprintf(stderr,"Cannot parse gap \'%s\'\n",fields[i+1].c_str()) ;
			return -1 ;
		}
		gaps[igap++] = gap ;
	}

	ngaps = igap ;

	return 0 ;
}
