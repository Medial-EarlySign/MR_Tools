// A set of linear models for completing missing values and assessing values at time-points.
#define _CRT_SECURE_NO_WARNINGS

#include <vector> 
#include <map>
#include <algorithm> 
#include <random>

using namespace std ;
#include "localCommonLib.h"

int past_periods[] = {30,30*3,30*6,30*10,30*15,30*21,30*28,30*360 } ;
int npast_periods = sizeof(past_periods)/sizeof(int);
double past_rf = 0.99 ; 

int min_period = -(30*18) ;
int max_period = 30*9999 ;

int all_periods[] = {-(30*9),-(30*4),-30,30,30*4,30*9,30*18,30*360} ;

int nall_periods = sizeof(all_periods)/sizeof(int) ;
double all_rf = 0.99 ;

int past_cnt = npast_periods*(1<<npast_periods) ;
int all_cnt = nall_periods*(1<<nall_periods) ;

int read_init_params(gzFile fprms, bins_lm_model *past_models, bins_lm_model *all_models, int *cbc_flags,int *biochem_flags) {
	
	// Allocate
	int ncbcs = 0 ;
	for (int i=0; i<NCBC; i++) {
		if (cbc_flags[i]) {
			past_models[i].bs = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
			past_models[i].means = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
			past_models[i].sdvs = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
			past_models[i].ymeans = (double *) malloc ((INT64_C(1)<<npast_periods) * sizeof(double)) ;
			all_models[i].bs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[i].means = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[i].sdvs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[i].ymeans = (double *) malloc ((INT64_C(1)<<nall_periods) * sizeof(double)) ;
			if (past_models[i].bs == NULL || past_models[i].means == NULL || past_models[i].sdvs == NULL || past_models[i].ymeans == NULL || 
				all_models[i].bs == NULL || all_models[i].means == NULL || all_models[i].sdvs == NULL || all_models[i].ymeans == NULL) {
					fprintf(stderr,"Allocation failed\n") ;
					return -1 ;
			}
			ncbcs ++ ;
		}
	}
	for (int i=0; i<NBIOCHEM; i++) {
		if (biochem_flags[i]) {
			past_models[NCBC+i].bs = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
			past_models[NCBC+i].means = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
			past_models[NCBC+i].sdvs = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
			past_models[NCBC+i].ymeans = (double *) malloc ((INT64_C(1)<<npast_periods) * sizeof(double)) ;
			all_models[NCBC+i].bs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[NCBC+i].means = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[NCBC+i].sdvs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[NCBC+i].ymeans = (double *) malloc ((INT64_C(1)<<nall_periods) * sizeof(double)) ;
			if (past_models[NCBC+i].bs == NULL || past_models[NCBC+i].means == NULL || past_models[NCBC+i].sdvs == NULL || past_models[NCBC+i].ymeans == NULL || 
				all_models[NCBC+i].bs == NULL || all_models[NCBC+i].means == NULL || all_models[NCBC+i].sdvs == NULL || all_models[NCBC+i].ymeans == NULL) {
					fprintf(stderr,"Allocation failed\n") ;
					return -1 ;
			}
			
		}
	}

	int verbose = 0 ;

	// Read
	int check_val ;
	if (gzread(fprms,&check_val,sizeof(int)) != 1) {
		fprintf(stderr,"Reading Params failed\n") ;
		return -1 ;
	}
	if (check_val != ncbcs)
		fprintf(stderr,"Warning: Init Params have NCBC = %d and not %d\n\n\n",check_val,ncbcs) ;
	
	if (verbose) 
		fprintf(stderr,"NCBCS = %d\n",ncbcs) ;

	if (gzread(fprms,&check_val,sizeof(int)) != 1) {
		fprintf(stderr,"Reading Params failed\n") ;
		return -1 ;
	}
	if (check_val != npast_periods) {
		fprintf(stderr,"Init Params have npast_periods = %d and not %d\n",check_val,npast_periods) ;
		return -1 ;
	}

	if (verbose) 
		fprintf(stderr,"npast_periods = %d\n",npast_periods) ;

	if (gzread(fprms,&check_val,sizeof(int)) != 1) {
		fprintf(stderr,"Reading Params failed\n") ;
		return -1 ;
	}
	if (check_val != nall_periods) {
		fprintf(stderr,"Init Params have nall_periods = %d and not %d\n",check_val,nall_periods) ;
		return -1 ;
	}

	if (verbose) 
		fprintf(stderr,"nall_periods = %d\n",nall_periods) ;

	if (gzread(fprms,&check_val,sizeof(int)) != 1) {
		fprintf(stderr,"Reading Params failed\n") ;
		return -1 ;
	}
	if (check_val != MAX_AGE) {
		fprintf(stderr,"Init Params have max_age = %d and not %d\n",check_val,MAX_AGE) ;
		return -1 ;
	}

	if (verbose) 
		fprintf(stderr,"max_age = %d\n",check_val) ;

	int past_cnt = npast_periods*(1<<npast_periods) ;
	int all_cnt = nall_periods*(1<<nall_periods) ;
	for (int i=0; i<NCBC; i++) {
		if (cbc_flags[i]) {
			fprintf(stderr,"Reading InitParams for %d\n",i) ;

			int read_i = -1 ;
			while (read_i < i) {

				if (gzread(fprms, &read_i, sizeof(int)) != sizeof(int)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (read_i > i) {
					fprintf(stderr,"Init Params Reads params %d when expecting %d\n",check_val,i) ;
					return -1 ;
				}

				if (verbose) 
					fprintf(stderr,"i = %d\n",i) ;

				if (gzread(fprms,past_models[i].age_means,sizeof(double)*(MAX_AGE+1)) != MAX_AGE+1) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<=MAX_AGE; vi++)
						fprintf(stderr,"past age_means[%d][%d] = %f\n",i,vi,past_models[i].age_means[vi]) ;
				}

				if (gzread(fprms,&(past_models[i].sdv),sizeof(double)) != 1) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose)
					fprintf(stderr,"past sdv = %f\n",past_models[i].sdv) ;

				if (gzread(fprms,past_models[i].means,sizeof(double)*past_cnt) != past_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<past_cnt; vi++)
						fprintf(stderr,"past means[%d][%d] = %f\n",i,vi,past_models[i].means[vi]) ;
				}

				if (gzread(fprms,past_models[i].sdvs,sizeof(double)*past_cnt) != past_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<past_cnt; vi++)
						fprintf(stderr,"past sdvs[%d][%d] = %f\n",i,vi,past_models[i].sdvs[vi]) ;
				}

				if (gzread(fprms,past_models[i].bs,sizeof(double)*past_cnt) != past_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<past_cnt; vi++)
						fprintf(stderr,"past bs[%d][%d] = %f\n",i,vi,past_models[i].bs[vi]) ;
				}

				if (gzread(fprms,past_models[i].ymeans,sizeof(double)*(INT64_C(1)<<npast_periods)) != (INT64_C(1)<<npast_periods)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<(INT64_C(1)<<npast_periods); vi++)
						fprintf(stderr,"past ymeans[%d][%d] = %f\n",i,vi,past_models[i].ymeans[vi]) ;
				}

				if (gzread(fprms,all_models[i].age_means,sizeof(double)*(MAX_AGE+1)) != MAX_AGE+1) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<MAX_AGE; vi++)
						fprintf(stderr,"all age_means[%d][%d] = %f\n",i,vi,all_models[i].age_means[vi]) ;
				}

				if (gzread(fprms,&(all_models[i].sdv),sizeof(double)) != 1) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose)
					fprintf(stderr,"all sdv = %f\n",all_models[i].sdv) ;


				if (gzread(fprms,all_models[i].means,sizeof(double)*all_cnt) != all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all means[%d][%d] = %f\n",i,vi,all_models[i].means[vi]) ;
				}

				if (gzread(fprms,all_models[i].sdvs,sizeof(double)*all_cnt) != all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all sdvs[%d][%d] = %f\n",i,vi,all_models[i].sdvs[vi]) ;
				}

				if (gzread(fprms,all_models[i].bs,sizeof(double)*all_cnt) != all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all bs[%d][%d] = %f\n",i,vi,all_models[i].bs[vi]) ;
				}
			
				if (gzread(fprms,all_models[i].ymeans,sizeof(double)*(INT64_C(1)<<nall_periods)) != (INT64_C(1)<<nall_periods)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<(INT64_C(1)<<nall_periods); vi++)
						fprintf(stderr,"all ymeans[%d][%d] = %f\n",i,vi,all_models[i].ymeans[vi]) ;
				}
			}
		}
	}

	for (int i=0; i<NBIOCHEM; i++) {
		if (biochem_flags[i]) {
			int index = NCBC + i ;
			fprintf(stderr,"Reading InitParams for %d\n",index) ;

			int read_i = -1 ;
			while (read_i < i) {

				if (gzread(fprms, &read_i, sizeof(int)) != sizeof(int)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (read_i > i) {
					fprintf(stderr,"Init Params Reads params %d when expecting %d\n",check_val,i) ;
					return -1 ;
				}

				if (verbose) 
					fprintf(stderr,"i = %d\n",i) ;

				if (gzread(fprms,past_models[index].age_means,sizeof(double)*(MAX_AGE+1)) != MAX_AGE+1) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<=MAX_AGE; vi++)
						fprintf(stderr,"past age_means[%d][%d] = %f\n",i,vi,past_models[index].age_means[vi]) ;
				}

				if (gzread(fprms,&(past_models[index].sdv),sizeof(double)) != 1) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose)
					fprintf(stderr,"past sdv = %f\n",past_models[index].sdv) ;

				if (gzread(fprms,past_models[index].means,sizeof(double)*past_cnt) != past_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<past_cnt; vi++)
						fprintf(stderr,"past means[%d][%d] = %f\n",i,vi,past_models[index].means[vi]) ;
				}

				if (gzread(fprms,past_models[index].sdvs,sizeof(double)*past_cnt) != past_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<past_cnt; vi++)
						fprintf(stderr,"past sdvs[%d][%d] = %f\n",i,vi,past_models[index].sdvs[vi]) ;
				}

				if (gzread(fprms,past_models[index].bs,sizeof(double)*past_cnt) != past_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<past_cnt; vi++)
						fprintf(stderr,"past bs[%d][%d] = %f\n",i,vi,past_models[index].bs[vi]) ;
				} 

				if (gzread(fprms,past_models[index].ymeans,sizeof(double)*(INT64_C(1)<<npast_periods)) != (INT64_C(1)<<npast_periods)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<(INT64_C(1)<<npast_periods); vi++)
						fprintf(stderr,"past ymeans[%d][%d] = %f\n",i,vi,past_models[index].ymeans[vi]) ;
				}

				if (gzread(fprms,all_models[index].age_means,sizeof(double)*(MAX_AGE+1)) != MAX_AGE+1) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<MAX_AGE; vi++)
						fprintf(stderr,"all age_means[%d][%d] = %f\n",i,vi,all_models[index].age_means[vi]) ;
				}

				if (gzread(fprms,&(all_models[index].sdv),sizeof(double)) != 1) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose)
					fprintf(stderr,"all sdv = %f\n",all_models[index].sdv) ;


				if (gzread(fprms,all_models[index].means,sizeof(double)*all_cnt) != all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all means[%d][%d] = %f\n",i,vi,all_models[index].means[vi]) ;
				}

				if (gzread(fprms,all_models[index].sdvs,sizeof(double)*all_cnt) != all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all sdvs[%d][%d] = %f\n",i,vi,all_models[index].sdvs[vi]) ;
				}

				if (gzread(fprms,all_models[index].bs,sizeof(double)*all_cnt) != all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all bs[%d][%d] = %f\n",i,vi,all_models[index].bs[vi]) ;
				}
			
				if (gzread(fprms,all_models[index].ymeans,sizeof(double)*(INT64_C(1)<<nall_periods)) != (INT64_C(1)<<nall_periods)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<(INT64_C(1)<<nall_periods); vi++)
						fprintf(stderr,"all ymeans[%d][%d] = %f\n",i,vi,all_models[index].ymeans[vi]) ;
				}
			}
		}
	}

	gzclose(fprms) ; 
	return 0 ;
}

int read_init_params(gzFile fprms, bins_lm_model *all_models, int *cbc_flags,int *biochem_flags) {
	
	// Allocate
	int ncbcs = 0 ;
	for (int i=0; i<NCBC; i++) {
		if (cbc_flags[i]) {
			all_models[i].bs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[i].means = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[i].sdvs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[i].ymeans = (double *) malloc ((INT64_C(1)<<nall_periods) * sizeof(double)) ;
			if (all_models[i].bs == NULL || all_models[i].means == NULL || all_models[i].sdvs == NULL || all_models[i].ymeans == NULL) {
					fprintf(stderr,"Allocation failed\n") ;
					return -1 ;
			}
			ncbcs ++ ;
		}
	}
	for (int i=0; i<NBIOCHEM; i++) {
		if (biochem_flags[i]) {
			all_models[NCBC+i].bs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[NCBC+i].means = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[NCBC+i].sdvs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
			all_models[NCBC+i].ymeans = (double *) malloc ((INT64_C(1)<<nall_periods) * sizeof(double)) ;
			if (all_models[NCBC+i].bs == NULL || all_models[NCBC+i].means == NULL || all_models[NCBC+i].sdvs == NULL || all_models[NCBC+i].ymeans == NULL) {
					fprintf(stderr,"Allocation failed\n") ;
					return -1 ;
			}
			
		}
	}

	int verbose = 0 ;

	// Read
	int check_val ;

	// Number of CBCs (should be as large as required).
	if (gzread(fprms, &check_val,sizeof(int)) != sizeof(int)) {
		fprintf(stderr,"Reading Params failed\n") ;
		return -1 ;
	}

	if (check_val < ncbcs)
		fprintf(stderr,"Warning: Init Params have NCBC = %d and not %d\n\n\n",check_val,ncbcs) ;
	
	if (verbose) 
		fprintf(stderr,"NCBCS = %d. Available = %d \n",ncbcs,check_val) ;

	// Number of periods
	if (gzread(fprms, &check_val,sizeof(int)) != sizeof(int)) {
		fprintf(stderr,"Reading Params failed\n") ;
		return -1 ;
	}
	if (check_val != nall_periods) {
		fprintf(stderr,"Init Params have nall_periods = %d and not %d\n",check_val,nall_periods) ;
		return -1 ;
	}

	if (verbose) 
		fprintf(stderr,"nall_periods = %d\n",nall_periods) ;

	// Maximal age
	if (gzread(fprms, &check_val,sizeof(int)) != sizeof(int)) {
		fprintf(stderr,"Reading Params failed\n") ;
		return -1 ;
	}
	if (check_val != MAX_AGE) {
		fprintf(stderr,"Init Params have max_age = %d and not %d\n",check_val,MAX_AGE) ;
		return -1 ;
	}

	if (verbose) 
		fprintf(stderr,"max_age = %d\n",check_val) ;

	// Read models
	int size ; 
	int all_cnt = nall_periods*(1<<nall_periods) ;
	for (int i=0; i<NCBC; i++) {
		if (cbc_flags[i]) {
			fprintf(stderr,"Reading InitParams for %d\n",i) ; fflush(stderr) ;

			int read_i = -1 ;
			while (read_i < i) {

				if (gzread(fprms, &read_i, sizeof(int)) != sizeof(int)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}
				fprintf(stderr,"Read Candidate %d\n",read_i) ;

				if (read_i > i) {
					fprintf(stderr,"Init Params Reads params %d when expecting %d\n",check_val,i) ;
					return -1 ;
				}

				if (verbose) {
					fprintf(stderr,"i = %d\n",i) ;
					fflush(stderr) ;
				}

				if (gzread(fprms, all_models[i].age_means, sizeof(double) * (MAX_AGE+1)) != sizeof(double) * (MAX_AGE+1)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<MAX_AGE; vi++)
						fprintf(stderr,"all age_means[%d][%d] = %f\n",i,vi,all_models[i].age_means[vi]) ;
					fflush(stderr) ;
				}

				if (gzread(fprms, &(all_models[i].sdv), sizeof(double)) != sizeof(double)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					fprintf(stderr,"all sdv = %f\n",all_models[i].sdv) ;
					fflush(stderr) ;
				}

				if (gzread(fprms, all_models[i].means, sizeof(double) * all_cnt) != sizeof(double) * all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all means[%d][%d] = %f\n",i,vi,all_models[i].means[vi]) ;
					fflush(stderr) ;
				}

				if ((size = gzread(fprms, all_models[i].sdvs, sizeof(double) * all_cnt)) != sizeof(double) * all_cnt) {
					fprintf(stderr,"Reading Params failed (%d vs %zd)\n",size,sizeof(double) * all_cnt) ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all sdvs[%d][%d] = %f\n",i,vi,all_models[i].sdvs[vi]) ;
					fflush(stderr) ;
				}

				if ((size = gzread(fprms, all_models[i].bs,sizeof(double) * all_cnt)) != sizeof(double) * all_cnt) {
					fprintf(stderr,"Reading Params failed (%d vs %zd)\n",size,sizeof(double) * all_cnt) ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all bs[%d][%d] = %f\n",i,vi,all_models[i].bs[vi]) ;
					fflush(stderr) ;
				}
			
				if (gzread(fprms, all_models[i].ymeans,sizeof(double) * (INT64_C(1)<<nall_periods)) != sizeof(double) * (INT64_C(1)<<nall_periods)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<(INT64_C(1)<<nall_periods); vi++)
						fprintf(stderr,"all ymeans[%d][%d] = %f\n",i,vi,all_models[i].ymeans[vi]) ;
					fflush(stderr) ;
				}
			}
		}
	}

	for (int i=0; i<NBIOCHEM; i++) {
		if (biochem_flags[i]) {
			int index = NCBC + i ;
			fprintf(stderr,"Reading InitParams for %d\n",index) ;

			int read_i = -1 ;
			while (read_i < index) {

				if (gzread(fprms, &read_i, sizeof(int)) != sizeof(int)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}
				fprintf(stderr,"Read %d\n",read_i) ;

				if (read_i > index) {
					fprintf(stderr,"Init Params Reads params %d when expecting %d\n",check_val,i) ;
					return -1 ;
				}

				if (verbose) 
					fprintf(stderr,"i = %d\n",index) ;

				if (gzread(fprms, all_models[index].age_means, sizeof(double) * (MAX_AGE+1)) != sizeof(double) * (MAX_AGE+1)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<MAX_AGE; vi++)
						fprintf(stderr,"all age_means[%d][%d] = %f\n",i,vi,all_models[index].age_means[vi]) ;
				}

				if (gzread(fprms, &(all_models[index].sdv), sizeof(double)) != sizeof(double)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose)
					fprintf(stderr,"all sdv = %f\n",all_models[index].sdv) ;


				if (gzread(fprms, all_models[index].means, sizeof(double) * all_cnt) != sizeof(double) * all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all means[%d][%d] = %f\n",i,vi,all_models[index].means[vi]) ;
				}

				if (gzread(fprms, all_models[index].sdvs, sizeof(double) * all_cnt) != sizeof(double) * all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all sdvs[%d][%d] = %f\n",i,vi,all_models[index].sdvs[vi]) ;
				}

				if (gzread(fprms, all_models[index].bs, sizeof(double) * all_cnt) != sizeof(double) * all_cnt) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<all_cnt; vi++)
						fprintf(stderr,"all bs[%d][%d] = %f\n",i,vi,all_models[index].bs[vi]) ;
				}
			
				if (gzread(fprms, all_models[index].ymeans, sizeof(double) * (INT64_C(1)<<nall_periods)) != sizeof(double) * (INT64_C(1)<<nall_periods)) {
					fprintf(stderr,"Reading Params failed\n") ;
					return -1 ;
				}

				if (verbose) {
					for (int vi=0; vi<(INT64_C(1)<<nall_periods); vi++)
						fprintf(stderr,"all ymeans[%d][%d] = %f\n",i,vi,all_models[index].ymeans[vi]) ;
				}
			}
		}
	}

	gzclose(fprms) ; 
	return 0 ;
}

int get_past_model(double lines[], int nlines, int col, bins_lm_model *model, int npatients, int ncols, float missing_val) {

	int *days = (int *) malloc(nlines*sizeof(int)) ;
	double *x = (double *) malloc(nlines*(npast_periods)*sizeof(double)) ;
	int *types = (int *) malloc(nlines*sizeof(int)) ;
	double *y = (double *) malloc(nlines*sizeof(double)) ;
	int *cols = (int *) malloc(npast_periods * sizeof(int)) ;
	model->bs = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
	model->means = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
	model->sdvs = (double *) malloc ((npast_periods) * (1<<npast_periods) * sizeof(double)) ;
	model->ymeans = (double *) malloc ((INT64_C(1)<<npast_periods) *  sizeof(double)) ;
	if (days==NULL || x==NULL || y==NULL || types==NULL || cols==NULL || model->bs==NULL || model->means==NULL || model->sdvs==NULL || model->ymeans==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	memset(model->bs,0,npast_periods * (1<<npast_periods) * sizeof(double)) ;
	memset(model->means,0,npast_periods * (1<<npast_periods) * sizeof(double)) ;
	memset(model->sdvs,0,npast_periods * (1<<npast_periods) * sizeof(double)) ;
	memset(model->ymeans,0,(INT64_C(1)<<npast_periods) *  sizeof(double)) ;

	// Get Age Means and Sdvs : Collect
	double sums[MAX_AGE+1] ; 
	int nums[MAX_AGE+1] ;
	int num = 0 ;
	double sum=0, sum2=0 ;

	for (int i=0; i<=MAX_AGE; i++) {
		nums[i] = 0 ;
		sums[i] = 0 ;
	}

	for (int i=0; i<nlines; i++) {
		int age = ((int) lines[XIDX(i,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(i,BDATE_COL,ncols)])/10000  ;
		if (age <= MAX_AGE && lines[XIDX(i,col,ncols)]!=missing_val) {
			nums[age] ++ ;
			sums[age] += lines[XIDX(i,col,ncols)] ;

			num ++ ;
			sum += lines[XIDX(i,col,ncols)] ;
			sum2 += lines[XIDX(i,col,ncols)] * lines[XIDX(i,col,ncols)] ;
		}
	}

	// Get Age Means and Sdvs : Calculate
	int most_common_age = 0 ;
	for (int iage=1; iage<=MAX_AGE; iage++) {
		if (nums[iage] > nums[most_common_age])
			most_common_age = iage ;
	}

	if (nums[most_common_age] < MINIMAL_NUM_PER_AGE) {
		fprintf(stderr,"Not enough tests for test %d (most common age = %d has only %d samples)\n",col,most_common_age,nums[most_common_age]) ;
		return -1 ;
	}

	for (int iage=most_common_age; iage<=MAX_AGE; iage++) {
		if (nums[iage] < MINIMAL_NUM_PER_AGE) {
//			fprintf(stderr,"Adjusting age %d (num = %d, sum = %f)\n",iage,nums[iage],sums[iage]) ;
			int missing_num = MINIMAL_NUM_PER_AGE - nums[iage] ;
			nums[iage] = MINIMAL_NUM_PER_AGE ;
			sums[iage] += sums[iage-1] * ((0.0 + missing_num)/nums[iage-1]) ;
		}

		model->age_means[iage] = sums[iage]/nums[iage] ;
	}

	for (int iage=most_common_age-1; iage>=0; iage--) {
		if (nums[iage] < MINIMAL_NUM_PER_AGE) {
//			fprintf(stderr,"Adjusting age %d (num = %d, sum = %f)\n",iage,nums[iage],sums[iage]) ;
			int missing_num = MINIMAL_NUM_PER_AGE - nums[iage] ;
			nums[iage] = MINIMAL_NUM_PER_AGE ;
			sums[iage] += sums[iage+1] * ((0.0 + missing_num)/nums[iage+1]) ;
		}

		model->age_means[iage] = sums[iage]/nums[iage] ;
	}

	double mean = sum/num ;
	model->sdv = sqrt((sum2 - mean*sum)/(num-1)) ;

	// Prepare days
	for(int i=0; i<nlines; i++)
		days[i] = get_day((int)(lines[XIDX(i,DATE_COL,ncols)]+0.5)) ;

	// Collect data
	int irow = 0 ;
	int first = 0 ;
	for (int iline=0; iline < nlines; iline++) {

		int idnum = (int) lines[XIDX(iline,ID_COL,ncols)];
		int prev_idnum = (int) lines[XIDX(first,ID_COL,ncols)] ;

		if (idnum != prev_idnum)
			first = iline ;


		int age = ((int) lines[XIDX(iline,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(iline,BDATE_COL,ncols)])/10000  ;
		if (age < MIN_AGE || age > MAX_AGE)
			continue ;

		if (lines[XIDX(iline,col,ncols)] == missing_val)
			continue ;

		// Add line + type to data matrix
		int type = 0 ;
		int jline = first ;
		int iperiod = npast_periods ;
		int jperiod = npast_periods ;
		double type_sum = 0 ;
		int type_num = 0 ;
		for (int jline = first; jline < iline ; jline ++) {
			int gap = days[iline] - days[jline] ;
			while (iperiod > 0 && gap <= past_periods[iperiod-1])
				iperiod -- ;
		
			if (iperiod != jperiod) {
				if (type_num) {
					type += 1<<jperiod ;
					x[XIDX(irow,jperiod,npast_periods)] = type_sum/type_num ;
				}
				type_sum = 0 ;
				type_num = 0 ;
				jperiod = iperiod ;
			}

			if (iperiod != npast_periods && lines[XIDX(jline,col,ncols)] != missing_val) {
				int age = ((int) lines[XIDX(jline,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(jline,BDATE_COL,ncols)])/10000  ;
				type_sum += lines[XIDX(jline,col,ncols)] - model->age_means[age] ;
				type_num ++ ;
			}
		}
		if (type_num) {
			type += 1<<jperiod ;
			x[XIDX(irow,jperiod,(npast_periods))] = type_sum/type_num ;
		}

		y[irow] = lines[XIDX(iline,col,ncols)] - model->age_means[age];
		types[irow++] = type ;
	} 

	free(days) ;

	// Build model for each class 
	// Collect Data
	for (int type=1; type < (1<<npast_periods); type++) {
		int nrows = 0 ;
		for (int i=0; i<irow; i++) {
			if ((types[i] & type) == type)
				nrows++ ;
		}
		
		int ncols = 0 ;
		for (int iperiod=0; iperiod<npast_periods; iperiod++) {
			if (type & (1<<iperiod))
				cols[ncols++] = iperiod ;
		}
		
		double *tx = (double *) malloc(nrows*ncols*sizeof(double)) ;
		double *ty = (double *) malloc(nrows*sizeof(double)) ;
		if (tx==NULL || ty==NULL) {
			fprintf(stderr,"Allocation failed\n") ;
			return -1 ;
		}

		int jrow = 0 ;
		for (int i=0; i<irow; i++) {
			if ((types[i] & type) == type) {
				ty[jrow] = y[i] ;
				for (int j=0; j<ncols; j++)
					tx[XIDX(j,jrow,nrows)] = x[XIDX(i,cols[j],nall_periods)] ;

				jrow ++ ;
			}
		}

		if (nrows < ncols) {
			fprintf(stderr,"Not enough samples of type %d (%d, required - %d)\n",type,nrows,ncols) ;
			return -1 ;
		}

		// Normalize
		double sum,sum2 ; 
		for (int j=0; j<ncols; j++) {
			sum = sum2 = 0 ;
			for (int i=0; i<nrows; i++) {
				double val = tx[XIDX(j,i,nrows)] ;
				sum += val ;
				sum2 += val*val ;
			}
			double xmean = sum/nrows ;
			(model->means)[npast_periods*type + j] = xmean ;
			(model->sdvs)[npast_periods*type + j] = sqrt ((sum2 - xmean*sum)/(nrows-1)) ;
		}

		sum = 0 ;
		for (int i=0; i<nrows; i++)
			sum += ty[i] ;
		(model->ymeans)[type] = sum/nrows ;

		for (int j=0; j<ncols; j++) {
			for (int i=0; i<nrows; i++) {
				tx[XIDX(j,i,nrows)] = (tx[XIDX(j,i,nrows)] - (model->means)[npast_periods*type + j])/(model->sdvs)[npast_periods*type + j] ;
			}
		}

		for (int i=0; i<nrows; i++)
			ty[i] -= (model->ymeans)[type] ;

		// Learn Linear Model
		double err ;
		if (lm(tx,ty,nrows,ncols,NITER,EITER,past_rf,(model->bs) + npast_periods*type,&err) == -1) {
			fprintf(stderr,"LM failed\n") ;
			return -1 ;
		}

		free(tx) ; free(ty) ;
	}

	free(x); free(y); free(types) ; free(cols) ;
	return 0 ;
}

int get_all_model(double lines[], int nlines, int col, bins_lm_model *model, int npatients, int ncols, float missing_val) {

	int *days = (int *) malloc(nlines*sizeof(int)) ;
	double *x = (double *) malloc(nlines*(nall_periods)*sizeof(double)) ;
	int *types = (int *) malloc(nlines*sizeof(int)) ;
	double *y = (double *) malloc(nlines*sizeof(double)) ;
	int *firsts = (int *) malloc(npatients*sizeof(int)) ;
	int *lasts = (int *) malloc(npatients*sizeof(int)) ;
	int *cols = (int *) malloc(nall_periods * sizeof(int)) ;
	model->bs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
	model->means = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
	model->sdvs = (double *) malloc ((nall_periods) * (1<<nall_periods) * sizeof(double)) ;
	model->ymeans = (double *) malloc ((INT64_C(1)<<nall_periods) *  sizeof(double)) ;
	if (days==NULL || x==NULL || y==NULL || types==NULL || cols==NULL || model->bs==NULL || model->means==NULL || model->sdvs==NULL || model->ymeans==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	memset(model->bs,0,nall_periods * (1<<nall_periods) * sizeof(double)) ;
	memset(model->means,0,nall_periods * (1<<nall_periods) * sizeof(double)) ;
	memset(model->sdvs,0,nall_periods * (1<<nall_periods) * sizeof(double)) ;
	memset(model->ymeans,0,(INT64_C(1)<<nall_periods) *  sizeof(double)) ;

	// Get Age Means and Sdvs : Collect
	double sums[MAX_AGE+1] ; 
	int nums[MAX_AGE+1] ;
	int num = 0 ;
	double sum=0, sum2=0 ;
	
	for (int i=0; i<=MAX_AGE; i++) {
		nums[i] = 0 ;
		sums[i] = 0 ;
	}

	for (int i=0; i<nlines; i++) {
		int age = ((int) lines[XIDX(i,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(i,BDATE_COL,ncols)])/10000  ;
		if (age <= MAX_AGE && lines[XIDX(i,col,ncols)]!=missing_val) {
			nums[age] ++ ;
			sums[age] += lines[XIDX(i,col,ncols)] ;

			num ++ ;
			sum += lines[XIDX(i,col,ncols)] ;
			sum2 += lines[XIDX(i,col,ncols)]*lines[XIDX(i,col,ncols)] ;
		}
	}

	// Get Age Means and Sdv : Calculate
	int most_common_age = 0 ;
	for (int iage=1; iage<=MAX_AGE; iage++) {
		if (nums[iage] > nums[most_common_age])
			most_common_age = iage ;
	}

	if (nums[most_common_age] < MINIMAL_NUM_PER_AGE) {
		fprintf(stderr,"Not enough tests for test %d (most common age = %d has only %d samples)\n",col,most_common_age,nums[most_common_age]) ;
		return -1 ;
	}

	for (int iage=most_common_age; iage<=MAX_AGE; iage++) {
		if (nums[iage] < MINIMAL_NUM_PER_AGE) {
//			fprintf(stderr,"Adjusting age %d (num = %d, sum = %f)\n",iage,nums[iage],sums[iage]) ;
			int missing_num = MINIMAL_NUM_PER_AGE - nums[iage] ;
			nums[iage] = MINIMAL_NUM_PER_AGE ;
			sums[iage] += sums[iage-1] * ((0.0 + missing_num)/nums[iage-1]) ;
		}

		model->age_means[iage] = sums[iage]/nums[iage] ;
	}

	for (int iage=most_common_age-1; iage>=0; iage--) {
		if (nums[iage] < MINIMAL_NUM_PER_AGE) {
//			fprintf(stderr,"Adjusting age %d (num = %d, sum = %f)\n",iage,nums[iage],sums[iage]) ;
			int missing_num = MINIMAL_NUM_PER_AGE - nums[iage] ;
			nums[iage] = MINIMAL_NUM_PER_AGE ;
			sums[iage] += sums[iage+1] * ((0.0 + missing_num)/nums[iage+1]) ;
		}

		model->age_means[iage] = sums[iage]/nums[iage] ;
	}

	double mean = sum/num ;
	model->sdv = sqrt((sum2 - mean*sum)/(num-1)) ;
	
	// Prepare days
	for(int i=0; i<nlines; i++)
		days[i] = get_day((int)(lines[XIDX(i,DATE_COL,ncols)]+0.5)) ;

	// Collect data
	int ipatient=0; 
	int first = 0 ;
	firsts[0] = 0 ;
	for (int i=1; i<nlines; i++) {
		if (lines[XIDX(i,ID_COL,ncols)] != lines[XIDX(i-1,ID_COL,ncols)]) {
			lasts[ipatient++] = i -1 ;
			firsts[ipatient] = i ;
		}
	}
	lasts[ipatient] = nlines -1 ;
	
	int irow = 0 ;
	for (int i=0; i<npatients; i++) {
		int first = firsts[i] ;
		int last = lasts[i] ;
		
		for (int iline = first; iline <= last; iline ++) {

			int age = ((int) lines[XIDX(iline,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(iline,BDATE_COL,ncols)])/10000  ;
			if (age < MIN_AGE || age > MAX_AGE)
				continue ;
	
			if (lines[XIDX(iline,col,ncols)] == missing_val)
				continue ;

			// Add line + type to data matrix
			int type = 0 ;
			int iperiod = nall_periods ;
			int jperiod = nall_periods ;
			double type_sum = 0 ;
			int type_num = 0 ;
			for (int jline = first; jline <= last ; jline ++) {
				if (jline == iline)
					continue ;

				int gap = days[iline] - days[jline] ;
				if (gap < min_period || gap > max_period)
					continue ;

				while (iperiod > 0 && gap <= all_periods[iperiod-1])
					iperiod -- ;
		
				if (iperiod != jperiod) {
					if (type_num) {
						type += 1<<jperiod ;
						x[XIDX(irow,jperiod,nall_periods)] = type_sum/type_num ;
					}
					type_sum = 0 ;
					type_num = 0 ;
					jperiod = iperiod ;
				}

				if (iperiod != nall_periods && lines[XIDX(jline,col,ncols)] != missing_val) {
					int age = ((int) lines[XIDX(jline,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(jline,BDATE_COL,ncols)])/10000  ;
					type_sum += lines[XIDX(jline,col,ncols)] - model->age_means[age] ;
					type_num ++ ;
				}
			}
			if (type_num) {
				type += 1<<jperiod ;
				x[XIDX(irow,jperiod,nall_periods)] = type_sum/type_num ;
			}

			y[irow] = lines[XIDX(iline,col,ncols)] - model->age_means[age] ;
			types[irow++] = type ;
		} 
	}

	free(days) ;
	free(firsts) ; free(lasts) ;

	// Build model for each class 
	// Collect Data
	for (int type=1; type < (1<<nall_periods); type++) {
		int nrows = 0 ;
		for (int i=0; i<irow; i++) {
			if ((types[i] & type) == type)
				nrows++ ;
		}
		
		int ncols = 0 ;
		for (int iperiod=0; iperiod<nall_periods; iperiod++) {
			if (type & (1<<iperiod))
				cols[ncols++] = iperiod ;
		}

		double *tx = (double *) malloc(nrows*ncols*sizeof(double)) ;
		double *ty = (double *) malloc(nrows*sizeof(double)) ;
		if (tx==NULL || ty==NULL) {
			fprintf(stderr,"Allocation failed\n") ;
			return -1 ;
		}

		int jrow = 0 ;
		for (int i=0; i<irow; i++) {
			if ((types[i] & type) == type) {
				ty[jrow] = y[i] ;
				for (int j=0; j<ncols; j++)
					tx[XIDX(j,jrow,nrows)] = x[XIDX(i,cols[j],nall_periods)] ;
				jrow ++ ;
			}
		}

		if (nrows < ncols) {
			fprintf(stderr,"Not enough samples of type %d (%d, required - %d)\n",type,nrows,ncols) ;
			return -1 ;
		}

		// Normalize
		double sum,sum2 ; 
		for (int j=0; j<ncols; j++) {
			sum = sum2 = 0 ;
			for (int i=0; i<nrows; i++) {
				double val = tx[XIDX(j,i,nrows)] ;
				sum += val ;
				sum2 += val*val ;
			}
			double xmean = sum/nrows ;
			(model->means)[nall_periods*type + j] = xmean ;
			(model->sdvs)[nall_periods*type + j] = sqrt ((sum2 - xmean*sum)/(nrows-1)) ;
		}

		sum = 0 ;
		for (int i=0; i<nrows; i++)
			sum += ty[i] ;
		(model->ymeans)[type] = sum/nrows ;

		for (int j=0; j<ncols; j++) {
			for (int i=0; i<nrows; i++) {
				tx[XIDX(j,i,nrows)] = (tx[XIDX(j,i,nrows)] - (model->means)[nall_periods*type + j])/(model->sdvs)[nall_periods*type + j] ;
			}
		}

		for (int i=0; i<nrows; i++)
			ty[i] -= (model->ymeans)[type] ;

		// Learn Linear Model				
		double err ;
		if (lm(tx,ty,nrows,ncols,NITER,EITER,all_rf,(model->bs) + nall_periods*type,&err)  == -1) {
			fprintf(stderr,"LM failed\n") ;
			return -1 ;
		}

		free(tx) ; free(ty) ;
	}

	free(x); free(y); free(types) ; free(cols) ;
	return 0 ;
}

int write_bins_lm_model (bins_lm_model *model, int cnt1, int cnt2, gzFile fp) {

	if (gzwrite(fp, model->age_means, sizeof(double) * (MAX_AGE+1)) != sizeof(double) * (MAX_AGE+1)) {
		fprintf(stderr,"Writing Params failed\n") ;
		return -1 ;
	}

	if (gzwrite(fp, &(model->sdv), sizeof(double)) != sizeof(double)) {
		fprintf(stderr,"Writing Params failed\n") ;
		return -1 ;
	}

	if (gzwrite(fp, model->means, sizeof(double) * cnt1) != sizeof(double) * cnt1) {
		fprintf(stderr,"Writing Params failed\n") ;
		return -1 ;
	}

	if (gzwrite(fp, model->sdvs, sizeof(double) * cnt1) != sizeof(double) * cnt1) {
		fprintf(stderr,"Writing Params failed\n") ;
		return -1 ;
	}

	if (gzwrite(fp, model->bs, sizeof(double) * cnt1) != sizeof(double) * cnt1) {
		fprintf(stderr,"Writing Params failed\n") ;
		return -1 ;
	}

	if (gzwrite(fp, model->ymeans, sizeof(double) * cnt2) != sizeof(double) * cnt2) {
		fprintf(stderr,"Writing Params failed\n") ;
		return -1 ;
	}

	return 0 ;
}

double get_value_from_all_model(double lines[], int col , int first, int last, int *days, int day, int ncols, bins_lm_model *model, double *x, float missing_val, int no_random) {

	int type = 0 ;
	int iperiod = nall_periods ;
	int jperiod = nall_periods ;
	double type_sum = 0 ;
	int type_num = 0 ;
	for (int jline = first; jline <= last ; jline ++) {
			
		int gap = day - days[jline] ;
		if (gap < min_period || gap > max_period)
			continue ;

		while (iperiod > 0 && gap <= all_periods[iperiod-1])
			iperiod -- ;
		
		if (iperiod != jperiod) {
			if (type_num) {
				type += 1<<jperiod ;
				x[jperiod] = type_sum/type_num ;
			}
			type_sum = 0 ;
			type_num = 0 ;
			jperiod = iperiod ;
		}

		if (iperiod != nall_periods && lines[XIDX(jline,col,ncols)] != missing_val) {
			int age = ((int) lines[XIDX(jline,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(jline,BDATE_COL,ncols)])/10000 ;
			if (age > MAX_AGE)
				age = MAX_AGE ;
			type_sum += lines[XIDX(jline,col,ncols)] - model->age_means[age] ;
			type_num ++ ;
		}
	}
			
	if (type_num) {
		type += 1<<jperiod ;
		x[jperiod] = type_sum/type_num ;
	}
	
	int age = ((int) lines[XIDX(last,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(last,BDATE_COL,ncols)])/10000  - (days[last]-day)/365 ;
	if (age > MAX_AGE)
		age = MAX_AGE ;

	if (type) {
		double pred = 0 ;
		int j = 0 ;
		for (iperiod=0; iperiod<nall_periods; iperiod++) {
			if (type & (1<<iperiod)) {
				pred += model->bs[nall_periods*type + j] * (x[iperiod] - model->means[nall_periods*type + j])/model->sdvs[nall_periods*type + j] ;
				j ++ ;
			}
		}
	
		return (pred + model->ymeans[type] + model->age_means[age]) ;
	} else {
		int id = (int) lines[XIDX(last,ID_COL,ncols)] ;
		int date = (int) lines[XIDX(last,DATE_COL,ncols)] ;
		
		double value = model->age_means[age];
		if (!no_random) {
			globalRNG::srand(id + date);
			value += model->sdv * (0.1*globalRNG::rand() / (globalRNG::max() + 1.0) - 0.05);
		}
		return value;
	}
}

double get_value_from_past_model(double lines[], int col , int first, int last, int *days, int day, int ncols, bins_lm_model *model, double *x, float missing_val, int no_random) {

	int type = 0 ;
	int iperiod = npast_periods ;
	int jperiod = npast_periods ;
	double type_sum = 0 ;
	int type_num = 0 ;
	for (int jline = first; jline <=last ; jline ++) {
				
		int gap = day - days[jline] ;

		while (iperiod > 0 && gap <= past_periods[iperiod-1])
			iperiod -- ;
		
		if (iperiod != jperiod) {
			if (type_num) {
				type += 1<<jperiod ;
				x[jperiod] = type_sum/type_num ;
			}
			type_sum = 0 ;
			type_num = 0 ;
			jperiod = iperiod ;
		}

		if (iperiod != npast_periods && lines[XIDX(jline,col,ncols)] != missing_val) {
			int age = ((int) lines[XIDX(jline,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(jline,BDATE_COL,ncols)])/10000  ;
			if (age > MAX_AGE)
				age = MAX_AGE ;
			type_sum += lines[XIDX(jline,col,ncols)] - model->age_means[age] ;
			type_num ++ ;
		}
	}
			
	if (type_num) {
		type += 1<<jperiod ;
		x[jperiod] = type_sum/type_num ;
	}
	
	int age = ((int) lines[XIDX(last,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(last,BDATE_COL,ncols)])/10000 ;
	if (age > MAX_AGE)
		age = MAX_AGE ;

	if (type) {
		double pred = 0 ;
		int j = 0 ;
		for (iperiod=0; iperiod<npast_periods; iperiod++) {
			if (type & (1<<iperiod)) {
				pred += model->bs[npast_periods*type + j] * (x[iperiod] - model->means[npast_periods*type + j])/model->sdvs[npast_periods*type + j] ;
				j ++ ;
			}
		}

		return (pred + model->ymeans[type] + model->age_means[age]) ;
	} else {
		int id = (int) lines[XIDX(last,ID_COL,ncols)] ;
		int date = (int) lines[XIDX(last,DATE_COL,ncols)] ;
		double value = model->age_means[age];
		if (!no_random) {
			globalRNG::srand(id + date);
			value += model->sdv * (0.1*globalRNG::rand() / (globalRNG::max() + 1.0) - 0.05);
		}
		return value;
	}

}

int build_bins_lm_models(double *lines, int nlines,int ncols, feature_flags *fflags, bins_lm_model *all_models, int npatients, float missing_val, gzFile fprms) {

	// Write Linear Completion Parameters
	int ncbc = 0 ;
	
	if (fprms != NULL) {
		
		for (int i=0; i<NCBC; i++) {
			if (fflags->cbcs[i]) 
				ncbc++ ;
		}
				
		if (gzwrite(fprms, &ncbc, sizeof(int)) != sizeof(int)) {
			fprintf(stderr,"Writing Params failed\n") ;
			return -1 ;
		}

		if (gzwrite(fprms, &nall_periods, sizeof(int)) != sizeof(int)) {
			fprintf(stderr,"Writing Params failed\n") ;
			return -1 ;
		}

		int max_age = MAX_AGE ;
		if (gzwrite(fprms, &max_age, sizeof(int)) != sizeof(int)) {
			fprintf(stderr,"Writing Params failed\n") ;
			return -1 ;
		}

	}

	// Build Local Predictors
	int rc = 0;

#pragma omp parallel for
	for (int i = 0; i < NCBC; i++) {
		if (fflags->cbcs[i]) {
			fprintf(stderr, "Building \'all\' model for test %d\n", i);
			if (get_all_model(lines, nlines, TEST_COL + i, all_models + i, npatients, MAXCOLS, missing_val) != 0)
				rc = -1;
		}
	}
	if (rc != 0)
		return rc;

	if (fprms != NULL) {
		for (int i = 0; i < NCBC; i++) {
			if (fflags->cbcs[i]) {
				if (gzwrite(fprms, &i, sizeof(int)) != sizeof(int)) {
					fprintf(stderr, "Writing Params failed\n");
					return -1;
				}

				if (write_bins_lm_model(all_models+i,all_cnt,(INT64_C(1)<<nall_periods),fprms)==-1)
					return -1 ;
			}
		}
	}

	rc = 0;
#pragma omp parallel for
	for (int i = 0; i < NBIOCHEM; i++) {
		if (fflags->biochems[i]) {
			fprintf(stderr, "Building \'all\' model for biochem test %d\n", i);
			if (get_all_model(lines, nlines, TEST_COL + NCBC + i, all_models + NCBC + i, npatients, MAXCOLS, missing_val) != 0)
				rc = -1;
		}
	}
	if (rc != 0)
		return rc;

	if (fprms != NULL) {
		for (int i = 0; i < NBIOCHEM; i++) {
			if (fflags->biochems[i]) {
				int index = NCBC + i;
				if (gzwrite(fprms, &index, sizeof(int)) != sizeof(int)) {
					fprintf(stderr, "Writing Params failed\n");
					return -1;
				}

				if (write_bins_lm_model(all_models+NCBC+i,all_cnt,(INT64_C(1)<<nall_periods),fprms)==-1)
					return -1 ;
			}
		}
	}

	gzclose(fprms) ;

	return 0 ;
}

int build_bins_lm_models(double *lines, int nlines,int ncols, feature_flags *fflags, bins_lm_model *past_models, bins_lm_model *all_models, int npatients, float missing_val, gzFile fprms) {

	// Write Linear Completion Parameters
	int ncbc = 0 ;
	if (fprms != NULL) {
		
		for (int i=0; i<NCBC; i++) {
			if (fflags->cbcs[i]) 
				ncbc++ ;
		}

		if (gzwrite(fprms,&ncbc,sizeof(int)) != 1) {
			fprintf(stderr,"Writing Params failed\n") ;
			return -1 ;
		}

		if (gzwrite(fprms,&npast_periods,sizeof(int)) != 1) {
			fprintf(stderr,"Writing Params failed\n") ;
			return -1 ;
		}

		if (gzwrite(fprms,&nall_periods,sizeof(int)) != 1) {
			fprintf(stderr,"Writing Params failed\n") ;
			return -1 ;
		}

		int max_age = MAX_AGE ;
		if (gzwrite(fprms,&max_age,sizeof(int)) != 1) {
			fprintf(stderr,"Writing Params failed\n") ;
			return -1 ;
		}

	}

	// Build Local Predictors
	for (int i=0; i<NCBC; i++) {
		if (fflags->cbcs[i]) {
			if (fprms != NULL) {
				if (gzwrite(fprms,&i,sizeof(int)) != 1) {
					fprintf(stderr,"Writing Params failed\n") ;
					return -1 ;
				}
			}

			fprintf(stderr,"Building \'past\' model for test %d\n",i) ;
			if (get_past_model(lines,nlines,TEST_COL+i,past_models+i,npatients,MAXCOLS,missing_val) != 0)
				return -1 ;

			if (fprms != NULL) {
				if (write_bins_lm_model(past_models+i,past_cnt,(INT64_C(1)<<npast_periods),fprms)==-1)
					return -1 ;
			}

			fprintf(stderr,"Building \'all\' model for test %d\n",i) ;
			if (get_all_model(lines,nlines,TEST_COL+i,all_models+i,npatients,MAXCOLS,missing_val) != 0)
				return -1 ;

			if (fprms != NULL) {
				if (write_bins_lm_model(all_models+i,all_cnt,(INT64_C(1)<<nall_periods),fprms)==-1)
					return -1 ;
			}
		}
	}
	for (int i=0; i<NBIOCHEM; i++) {
		if (fflags->biochems[i]) {
			int index = NCBC + i ;
			if (fprms != NULL) {
				if (gzwrite(fprms,&index,sizeof(int)) != 1) {
					fprintf(stderr,"Writing Params failed\n") ;
					return -1 ;
				}
			}

			fprintf(stderr,"Building \'past\' model for biochem test %d\n",i) ;
			if (get_past_model(lines,nlines,TEST_COL+NCBC+i,past_models+NCBC+i,npatients,MAXCOLS,missing_val) != 0)
				return -1 ;

			if (fprms != NULL) {
				if (write_bins_lm_model(past_models+NCBC+i,past_cnt,(INT64_C(1)<<npast_periods),fprms)==-1)
					return -1 ;
			}

			fprintf(stderr,"Building \'all\' model for biochem test %d\n",i) ;
			if (get_all_model(lines,nlines,TEST_COL+NCBC+i,all_models+NCBC+i,npatients,MAXCOLS,missing_val) != 0)
				return -1 ;

			if (fprms != NULL) {
				if (write_bins_lm_model(all_models+NCBC+i,all_cnt,(INT64_C(1)<<nall_periods),fprms)==-1)
					return -1 ;
			}
		}
	}

	return 0 ;
}

// Functions for new version of completion
double get_default_value(double lines[], int col , int first, int last, int uselast, int *days, int day, int ncols, bins_lm_model *model, double *x)
{
	int age = ((int) lines[XIDX(last,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(last,BDATE_COL,ncols)])/10000  - (days[last]-day)/365 ;
	if (age > MAX_AGE)
		age = MAX_AGE ;

	return  model->age_means[age] ;
}

double get_value_from_all_model_no_current(double lines[], int col , int first, int last, int uselast, int *days, int day, int ncols, bins_lm_model *model, double *x, float missing_val) {

	int type = 0 ;
	int iperiod = nall_periods ;
	int jperiod = nall_periods ;
	double type_sum = 0 ;
	int type_num = 0 ;
	for (int jline = first; jline <= uselast ; jline ++) {
			
		int gap = day - days[jline] ;
		if (gap < min_period || gap > max_period)
			continue ;

		while (iperiod > 0 && gap <= all_periods[iperiod-1])
			iperiod -- ;
		
		if (iperiod != jperiod) {
			if (type_num) {
				type += 1<<jperiod ;
				x[jperiod] = type_sum/type_num ;
			}
			type_sum = 0 ;
			type_num = 0 ;
			jperiod = iperiod ;
		}

		if (iperiod != nall_periods && lines[XIDX(jline,col,ncols)] != missing_val) {
			int age = ((int) lines[XIDX(jline,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(jline,BDATE_COL,ncols)])/10000 ;
			if (age > MAX_AGE)
				age = MAX_AGE ;
			type_sum += lines[XIDX(jline,col,ncols)] - model->age_means[age] ;
			type_num ++ ;
		}
	}
			
	if (type_num) {
		type += 1<<jperiod ;
		x[jperiod] = type_sum/type_num ;
	}
	
	int age = ((int) lines[XIDX(last,DATE_COL,ncols)])/10000 -  ((int) lines[XIDX(last,BDATE_COL,ncols)])/10000  - (days[last]-day)/365 ;
	if (age > MAX_AGE)
		age = MAX_AGE ;

	if (type) {
		double pred = 0 ;
		int j = 0 ;
		for (iperiod=0; iperiod<nall_periods; iperiod++) {
			if (type & (1<<iperiod)) {
				pred += model->bs[nall_periods*type + j] * (x[iperiod] - model->means[nall_periods*type + j])/model->sdvs[nall_periods*type + j] ;
				j ++ ;
			}
		}
		return (pred + model->ymeans[type] + model->age_means[age]) ;
	} else {
		int id = (int) lines[XIDX(last,ID_COL,ncols)] ;
		int date = (int) lines[XIDX(last,DATE_COL,ncols)] ;
		return  model->age_means[age]  ;
	}
}

int get_max_periods() {
	return nall_periods ;
}