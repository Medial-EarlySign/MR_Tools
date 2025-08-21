// Functions for checking sensitivity of model to noise

#define _CRT_SECURE_NO_WARNINGS

#include "localCommonLib.h"

double get_noise_size(double *lines, int nlines, int ncols, int icol) {

	double sum=0,sum2=0 ;
	int num =0 ;

	for (int iline=0; iline<nlines; iline ++) {
		if (lines[XIDX(iline,icol,ncols)] != -1) {
			num ++ ;
			sum += lines[XIDX(iline,icol,ncols)] ;
			sum2 += lines[XIDX(iline,icol,ncols)] * lines[XIDX(iline,icol,ncols)] ;
		}
	}

	if (num > 1) {
		double mean = sum/num ;
		return sqrt((sum2 - mean*sum)/(num - 1)) ;
	} else
		return -1 ;
}

int add_noise_to_data(double *lines, int nlines, int ncols, double noise_level, int noise_direction, const char *noisy_ftrs) {

	assert(strlen(noisy_ftrs) == NCBC) ;

	for (int i=0; i<NCBC; i++) {
		if (noisy_ftrs[i] == '1') {

			double size = get_noise_size(lines,nlines,ncols,TEST_COL+i) ;
			if (size <= 0) {
				fprintf(stderr,"Problems calculating reference noise-size for column %d\n",i) ;
				return -1 ;
			}

			for (int iline =0 ; iline<nlines; iline ++) {
				if (lines[XIDX(iline,TEST_COL+i,ncols)] != -1) {
					double noise = (size * noise_level) * (noise_direction/2.0 - 0.5 + ((globalRNG::rand() + 0.0)/globalRNG::max())) ;
					int counter = 0 ;
					while (counter < 10 && lines[XIDX(iline,TEST_COL+i,ncols)] + noise < 0) {
						noise = (size * noise_level) * (noise_direction/2.0 - 0.5 + ((globalRNG::rand() + 0.0)/globalRNG::max())) ;
						counter ++ ;
					}

					if ( lines[XIDX(iline,TEST_COL+i,ncols)] + noise >= 0)
						lines[XIDX(iline,TEST_COL+i,ncols)] += noise ;
				}
			}
		}
	}

	return 0 ;
}