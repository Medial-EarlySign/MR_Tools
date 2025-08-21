// Get Data Matrix : Old Versions
int get_full_matrix_and_y(double lines[], int nlines, FILE *flog, double **x, double **y, int **idnums, int **flags, int **dates, int *nftrs, int *nrows, int start_time,
						  int end_time, int last_cancer_date, int min_test_gap, int min_test_num, int ftrs_flag, int gender_flag) {

	int ncols = MAXCOLS ;
	int npatients = 1 ;
	for (int i=1; i<nlines; i++) {
		if (lines[XIDX(i,ID_COL,ncols)] != lines[XIDX(i-1,ID_COL,ncols)])
			npatients++ ;
	}
	fprintf(stderr,"No. of patients = %d\n",npatients) ;

	int take_red, take_white,take_biochem, take_cnts, take_extra, take_ferritin ;
	if (ftrs_flag == 0) { // CBC + Counts
		take_red = take_white = take_cnts = 1 ;
		take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 1) { // Full
		take_red = take_white = take_cnts = take_biochem = take_ferritin = take_extra = 1 ;
	} else if (ftrs_flag == 2) { // Red + Counts
		take_red = take_cnts = 1 ;
		take_white = take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 3) { // Age
		take_red = take_white = take_biochem = take_ferritin = take_cnts = take_extra = 0 ;
	} else if (ftrs_flag == 4) { // White + Counts
		take_white = take_cnts = 1 ;
		take_red = take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 5) { // CBC
		take_red = take_white = 1 ;
		take_biochem = take_cnts = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 6) { // CBC + Counts + Ferritin
		take_red = take_white = take_cnts = take_ferritin = 1 ;
		take_biochem = take_extra = 0 ;
	} else if (ftrs_flag == 7) { // CBC without history + Extra
		take_red = take_white = 1 ;
		take_biochem = take_cnts = take_ferritin = 0 ;
		take_extra = 1 ;
		ngaps = 0 ;
	} else if (ftrs_flag == 8) { // CBC + Counts + Extra
		take_red = take_white = take_cnts = take_extra = 1 ;
		take_biochem = take_ferritin = 0 ;
	}

	int ntests = 0 ;
	if (take_red)
		ntests += NRED ;
	if (take_white)
		ntests += (NCBC - NRED) ;
	if (take_biochem)
		ntests += NBIOCHEM ;
	if (take_ferritin)
		ntests ++ ;

	// Age 
	*nftrs = 1 ;
	// Gender
	if (gender_flag)
		(*nftrs) ++ ;
	// Tests
	*nftrs += ntests*(ngaps+1) ;
	// Counts
	if (take_cnts)
		*nftrs += nperiods ;
	// SMX + BMI
	if (take_extra)
		*nftrs += 5 ;

	fprintf(stderr,"Nftrs = %d\n",*nftrs) ;

	int *cnts = (int *) malloc(nperiods*sizeof(int)) ;
	int *missing_tests = (int *) malloc(nlines*sizeof(int)) ;
	int *days = (int *) malloc(nlines*sizeof(int)) ;
	int *cancer_discovery = (int *) malloc(nlines*sizeof(int)) ;
	int *countable = (int *) malloc(nlines*sizeof(int)) ;

	*x = NULL ;
	*y = NULL ;
	*idnums = NULL ;
	*flags = NULL ;
	*dates = NULL ;

	if (days==NULL || cancer_discovery==NULL || missing_tests==NULL || cnts==NULL || countable == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}


	for(int i=0; i<nlines; i++) {
		days[i] = get_days((int)(lines[XIDX(i,DATE_COL,ncols)]+0.5)) ;
		cancer_discovery[i] = get_days((int)(lines[XIDX(i,CANCER_DATE_COL,ncols)]+0.5)) ;

		missing_tests[i] = 0 ;
		for (int j=0; j<NCBC; j++) {
			if (lines[XIDX(i,TEST_COL+j,ncols)] == -1)
				missing_tests[i]++ ;
		}

		countable[i] = 0 ;
		for (int j=0; j<NCBC; j++) {
			if (lines[XIDX(i,TEST_COL+j,ncols)] != -1 && ((reds[j]==1 && take_red) || (reds[j]==0 && take_white)))
				countable[i] = 1 ;
		}

		if (countable[i] == 0 && take_biochem) {
			for (int j=NCBC; j<NCBC + NBIOCHEM; j++)
				if (lines[XIDX(i,TEST_COL+j,ncols)] != -1)
					countable[i] = 1 ;
		}
	}

	int last_cancer_day = get_days(last_cancer_date) ;
	int first_cbc_day = get_days(20030101) ;

	int irow = 0 ;
	int first = 0 ;
	int nblocks = 0 ;
	int cftrs ;

	for (int iline=0; iline < nlines; iline++) {

		int idnum = (int) lines[XIDX(iline,ID_COL,ncols)];
		int prev_idnum = (int) lines[XIDX(first,ID_COL,ncols)] ;

		if (idnum != prev_idnum)
			first = iline ;

		if (lines[XIDX(iline,CANCER_COL,ncols)] < 0 || lines[XIDX(iline,CANCER_COL,ncols)] > 2) {
			fprintf(flog,"Ignoring %d@%d for cancer-registery %d\n",idnum, (int) lines[XIDX(iline,DATE_COL,ncols)], (int) lines[XIDX(iline,CANCER_COL,ncols)]) ;
			continue ;
		}

		if (lines[XIDX(iline,AGE_COL,ncols)] < MIN_AGE || lines[XIDX(iline,AGE_COL,ncols)] > MAX_AGE) {
			fprintf(flog,"Ignoring %d@%d for Age = %f\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],lines[XIDX(iline,AGE_COL,ncols)]) ;
			continue ;
		}

		if ((lines[XIDX(iline,CANCER_COL,ncols)]==1 || lines[XIDX(iline,CANCER_COL,ncols)]==2) &&
				(cancer_discovery[iline] < days[iline] + start_time || cancer_discovery[iline] > days[iline] + end_time)) {
			fprintf(flog,"Ignoring %d@%d for out-of-period cancer at %d \n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],(int) lines[XIDX(iline,CANCER_DATE_COL,ncols)]) ;
			continue ;
		}


		if (lines[XIDX(iline,CANCER_COL,ncols)]==0 && days[iline] + end_time > last_cancer_day) {
			fprintf(flog,"Ignoring %d@%d for out-of-registrar\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)]) ;
			continue ;
		}

		if (missing_tests[iline] >= MAX_MISSING_TESTS) {
			fprintf(flog,"Ignoring %d@%d for not-enough-CBC-results\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)]) ;
			continue ;
		}

		if (irow == nblocks*BLOCK_LINES) {
			nblocks++ ;

			fprintf(stderr,"Allocating block #%d (%d/%d)\n",nblocks,iline,nlines) ;
			(*x) = (double *) realloc(*x,(*nftrs)*nblocks*BLOCK_LINES*sizeof(double)) ;
			(*y) = (double *) realloc(*y,nblocks*BLOCK_LINES*sizeof(double)) ;
			(*idnums) = (int *) realloc(*idnums,nblocks*BLOCK_LINES*sizeof(int)) ;
			(*flags) = (int *) realloc(*flags,nblocks*BLOCK_LINES*sizeof(int)) ;
			(*dates) = (int *) realloc(*dates,nblocks*BLOCK_LINES*sizeof(int)) ;

			if (*x==NULL || *y==NULL || *idnums==NULL || *flags==NULL || *dates==NULL) {
				fprintf(stderr,"Reallocation at block %d failed\n",nblocks) ;
				return -1 ;
			}
		}

		(*idnums)[irow] = idnum ;
		(*dates)[irow] = (int) lines[XIDX(iline,DATE_COL,ncols)] ;

//		if ((lines[XIDX(iline,CANCER_COL,ncols)]>=1) && (lines[XIDX(iline,CANCER_COL,ncols)]<=2))
//			(*y)[irow] = 1.0 ;
//		else if (lines[XIDX(iline,CANCER_COL,ncols)]==0)
//			(*y)[irow] = 0.0 ;
//		else
//			(*y)[irow] = 2.0 ;

		(*y)[irow] = ((lines[XIDX(iline,CANCER_COL,ncols)]>=1) && (lines[XIDX(iline,CANCER_COL,ncols)]<=2)) ? 1.0 : 0.0 ;

		if (days[iline] - days[first] < min_test_gap) {
			fprintf(flog,"Flagging %d@%d for test-gap %d\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],days[iline] - days[first]) ;
			(*flags)[irow] = 0 ;
		} else if ((iline - first + 1) < min_test_num) {
			fprintf(flog,"Flagging %d@%d for test-num %d\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],iline-first+1) ;
			(*flags)[irow] = 0 ;
		} else
			(*flags)[irow] = 1 ;
	
		fprintf(flog,"Labeling %d@%d as %d %d\n",idnum, (int) lines[XIDX(iline,DATE_COL,ncols)],(int) ((*y)[irow]),(*flags)[irow]) ;

		// Fill the matrix
		int iftr = 0 ;

        // Gender
		if (gender_flag)
			(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,GENDER_COL,ncols)] ;

		// Tests
		for(int j=0; j<NCBC ;j++)	{
			if ((reds[j] == 1 && take_red) || (reds[j] == 0 && take_white)) {
				(*x)[XIDX(irow,iftr++,*nftrs)]  = (lines[XIDX(iline,TEST_COL+j,ncols)]==-1) ? MISSING_VAL : lines[XIDX(iline,TEST_COL+j,ncols)] ;
	
				for (int igap=0; igap<ngaps; igap++)
					(*x)[XIDX(irow,iftr++,*nftrs)] = get_diff(lines,TEST_COL+j,first,iline,days,days[iline]-gaps[igap],ncols) ;
			}
		}

		if (take_biochem) {
			for(int j=NCBC; j<NCBC+NBIOCHEM ;j++)	{
				get_test_values(lines,TEST_COL+j,first,iline,days,gaps,ngaps,ncols,*x,irow,&iftr,*nftrs) ;

//				(*x)[XIDX(irow,iftr++,*nftrs)]  = (lines[XIDX(iline,TEST_COL+j,ncols)]==-1) ? MISSING_VAL : lines[XIDX(iline,TEST_COL+j,ncols)] ;
//				for (int igap=0; igap<ngaps; igap++)
//					(*x)[XIDX(irow,iftr++,*nftrs)] = get_diff(lines,TEST_COL+j,first,iline,days,days[iline]-gaps[igap],ncols) ;
			}
		}

		if (take_ferritin) {
			int j = NCBC+NBIOCHEM ;
			get_test_values(lines,TEST_COL+j,first,iline,days,gaps,ngaps,ncols,*x,irow,&iftr,*nftrs) ;
			
//			(*x)[XIDX(irow,iftr++,*nftrs)]  = (lines[XIDX(iline,TEST_COL+j,ncols)]==-1) ? MISSING_VAL : lines[XIDX(iline,TEST_COL+j,ncols)] ;
//			for (int igap=0; igap<ngaps; igap++)
//				(*x)[XIDX(irow,iftr++,*nftrs)] = get_diff(lines,TEST_COL+j,first,iline,days,days[iline]-gaps[igap],ncols) ;
		}

		// Age
		(*x)[XIDX(irow,iftr++,*nftrs)] =  (days[iline] - get_days((int)(lines[XIDX(iline,BDATE_COL,ncols)])))/365.0 ;

		for (int iperiod=0; iperiod<nperiods; iperiod++) {
			cnts[iperiod]=0 ;
			for(int k1=iline-1; k1>=first; k1--) { 
				if (countable[k1] && (days[iline]-days[k1]<period_max[iperiod]) && (days[iline]-days[k1]>period_min[iperiod]))
					cnts[iperiod]++;
			}
		}

		if (take_cnts) {
			for (int iperiod=0; iperiod<nperiods; iperiod++) {
				int current_cnts ;
				if (days[iline] >= first_cbc_day + period_max[iperiod])
					 current_cnts =  cnts[iperiod] ;
				else if (days[iline] > first_cbc_day + period_min[iperiod])
					current_cnts = ((int) (0.5 + CBC_PER_YEAR * (period_max[iperiod] - period_min[iperiod])/365.0)) ;
				else
					current_cnts =  ((int) (cnts[iperiod] + 0.5 + CBC_PER_YEAR * (first_cbc_day - (days[iline] - period_max[iperiod]))/365.0)) ;

				if (current_cnts > MAX_CNTS) 
					current_cnts = MAX_CNTS ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = (double ) current_cnts ;
			}
		}

		// SMX
		if (take_extra) {
			if (lines[XIDX(iline,SMX_COL,ncols)] == -1) {
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
			} else {
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL,ncols)] ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL+1,ncols)] ;					
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL+2,ncols)] ;
			}

			// BMI
			if (lines[XIDX(iline,BMI_COL,ncols)] == -1) {
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
			} else {
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,BMI_COL,ncols)] ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,BMI_COL+1,ncols)] ;
			}
		}

		irow++ ;
		cftrs = iftr ;
	}

	*nrows = irow ;

	free(days) ;
	free(cancer_discovery) ;
	free(countable) ;

	realloc(*x,(*nftrs)*(*nrows)*sizeof(double)) ;
	realloc(*y,(*nrows)*sizeof(double)) ;

	if (*x==NULL || *y==NULL) {
		fprintf(stderr,"Reallocation at end failed\n") ;
		return -1 ;
	} else
		return 0 ;
}

int get_all_full_matrix_and_y(double lines[], int nlines, FILE *flog, double **x, double **y, int **idnums, int **flags, int **dates, int *nftrs, int *nrows, int start_time,
						  int end_time, int last_cancer_date, int min_test_gap, int min_test_num, int ftrs_flag, int gender_flag) {


	int ncols = MAXCOLS ;
	int npatients = 1 ;
	for (int i=1; i<nlines; i++) {
		if (lines[XIDX(i,ID_COL,ncols)] != lines[XIDX(i-1,ID_COL,ncols)])
			npatients++ ;
	}
	fprintf(stderr,"No. of patients = %d\n",npatients) ;

	int take_red, take_white,take_biochem, take_cnts, take_extra, take_ferritin ;
	if (ftrs_flag == 0) { // CBC + Counts
		take_red = take_white = take_cnts = 1 ;
		take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 1) { // Full
		take_red = take_white = take_cnts = take_biochem = take_ferritin = take_extra = 1 ;
	} else if (ftrs_flag == 2) { // Red + Counts
		take_red = take_cnts = 1 ;
		take_white = take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 3) { // Age
		take_red = take_white = take_biochem = take_ferritin = take_cnts = take_extra = 0 ;
	} else if (ftrs_flag == 4) { // White + Counts
		take_white = take_cnts = 1 ;
		take_red = take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 5) { // CBC
		take_red = take_white = 1 ;
		take_biochem = take_cnts = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 6) { // CBC + Counts + Ferritin
		take_red = take_white = take_cnts = take_ferritin = 1 ;
		take_biochem = take_extra = 0 ;
	} else if (ftrs_flag == 7) { // CBC without history + Extra
		take_red = take_white = 1 ;
		take_biochem = take_cnts = take_ferritin = 0 ;
		take_extra = 1 ;
		ngaps = 0 ;
	} else if (ftrs_flag == 8) { // CBC + Counts + Extra
		take_red = take_white = take_cnts = take_extra = 1 ;
		take_biochem = take_ferritin = 0 ;
	}

	int ntests = 0 ;
	if (take_red)
		ntests += NRED ;
	if (take_white)
		ntests += (NCBC - NRED) ;
	if (take_biochem)
		ntests += NBIOCHEM ;
	if (take_ferritin)
		ntests ++ ;

	// Age 
	*nftrs = 1 ;
	// Gender
	if (gender_flag)
		(*nftrs) ++ ;
	// Tests
	*nftrs += ntests*(ngaps+1) ;
	// Counts
	if (take_cnts)
		*nftrs += nperiods ;
	// SMX + BMI
	if (take_extra)
		*nftrs += 5 ;

	fprintf(stderr,"Nftrs = %d\n",*nftrs) ;

	int *cnts = (int *) malloc(nperiods*sizeof(int)) ;
	int *missing_tests = (int *) malloc(nlines*sizeof(int)) ;
	int *days = (int *) malloc(nlines*sizeof(int)) ;
	int *cancer_discovery = (int *) malloc(nlines*sizeof(int)) ;
	int *countable = (int *) malloc(nlines*sizeof(int)) ;

	*x = NULL ;
	*y = NULL ;
	*idnums = NULL ;
	*flags = NULL ;
	*dates = NULL ;

	if (days==NULL || cancer_discovery==NULL || missing_tests==NULL || cnts==NULL || countable == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}


	for(int i=0; i<nlines; i++) {
		days[i] = get_days((int)(lines[XIDX(i,DATE_COL,ncols)]+0.5)) ;
		cancer_discovery[i] = get_days((int)(lines[XIDX(i,CANCER_DATE_COL,ncols)]+0.5)) ;

		missing_tests[i] = 0 ;
		for (int j=0; j<NCBC; j++) {
			if (lines[XIDX(i,TEST_COL+j,ncols)] == -1)
				missing_tests[i]++ ;
		}

		countable[i] = 0 ;
		for (int j=0; j<NCBC; j++) {
			if (lines[XIDX(i,TEST_COL+j,ncols)] != -1 && ((reds[j]==1 && take_red) || (reds[j]==0 && take_white)))
				countable[i] = 1 ;
		}

		if (countable[i] == 0 && take_biochem) {
			for (int j=NCBC; j<NCBC + NBIOCHEM; j++)
				if (lines[XIDX(i,TEST_COL+j,ncols)] != -1)
					countable[i] = 1 ;
		}
	}

	int last_cancer_day = get_days(last_cancer_date) ;
	int first_cbc_day = get_days(20030101) ;

	int irow = 0 ;
	int first = 0 ;
	int nblocks = 0 ;
	int cftrs ;

	for (int iline=0; iline < nlines; iline++) {

		int idnum = (int) lines[XIDX(iline,ID_COL,ncols)];
		int prev_idnum = (int) lines[XIDX(first,ID_COL,ncols)] ;

		if (idnum != prev_idnum)
			first = iline ;

		if (lines[XIDX(iline,CANCER_COL,ncols)] < 0 || lines[XIDX(iline,CANCER_COL,ncols)] > 3) {
			fprintf(flog,"Ignoring %d@%d for cancer-registery %d\n",idnum, (int) lines[XIDX(iline,DATE_COL,ncols)], (int) lines[XIDX(iline,CANCER_COL,ncols)]) ;
			continue ;
		}

		if (lines[XIDX(iline,AGE_COL,ncols)] < MIN_AGE || lines[XIDX(iline,AGE_COL,ncols)] > MAX_AGE) {
			fprintf(flog,"Ignoring %d@%d for Age = %f\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],lines[XIDX(iline,AGE_COL,ncols)]) ;
			continue ;
		}

		if ((lines[XIDX(iline,CANCER_COL,ncols)]==1 || lines[XIDX(iline,CANCER_COL,ncols)]==2) &&
				(cancer_discovery[iline] < days[iline] + start_time || cancer_discovery[iline] > days[iline] + end_time)) {
			fprintf(flog,"Ignoring %d@%d for out-of-period cancer at %d \n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],(int) lines[XIDX(iline,CANCER_DATE_COL,ncols)]) ;
			continue ;
		}


		if (lines[XIDX(iline,CANCER_COL,ncols)]==0 && days[iline] + end_time > last_cancer_day) {
			fprintf(flog,"Ignoring %d@%d for out-of-registrar\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)]) ;
			continue ;
		}

		if (missing_tests[iline] >= MAX_MISSING_TESTS) {
			fprintf(flog,"Ignoring %d@%d for not-enough-CBC-results\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)]) ;
			continue ;
		}

		if (irow == nblocks*BLOCK_LINES) {
			nblocks++ ;

			fprintf(stderr,"Allocating block #%d (%d/%d)\n",nblocks,iline,nlines) ;
			(*x) = (double *) realloc(*x,(*nftrs)*nblocks*BLOCK_LINES*sizeof(double)) ;
			(*y) = (double *) realloc(*y,nblocks*BLOCK_LINES*sizeof(double)) ;
			(*idnums) = (int *) realloc(*idnums,nblocks*BLOCK_LINES*sizeof(int)) ;
			(*flags) = (int *) realloc(*flags,nblocks*BLOCK_LINES*sizeof(int)) ;
			(*dates) = (int *) realloc(*dates,nblocks*BLOCK_LINES*sizeof(int)) ;

			if (*x==NULL || *y==NULL || *idnums==NULL || *flags==NULL || *dates==NULL) {
				fprintf(stderr,"Reallocation at block %d failed\n",nblocks) ;
				return -1 ;
			}
		}

		(*idnums)[irow] = idnum ;
		(*dates)[irow] = (int) lines[XIDX(iline,DATE_COL,ncols)] ;

		if ((lines[XIDX(iline,CANCER_COL,ncols)]>=1) && (lines[XIDX(iline,CANCER_COL,ncols)]<=2))
			(*y)[irow] = 1.0 ;
		else if (lines[XIDX(iline,CANCER_COL,ncols)]==0)
			(*y)[irow] = 0.0 ;
		else
			(*y)[irow] = 2.0 ;

//		(*y)[irow] = ((lines[XIDX(iline,CANCER_COL,ncols)]>=1) && (lines[XIDX(iline,CANCER_COL,ncols)]<=2)) ? 1.0 : 0.0 ;

		if (days[iline] - days[first] < min_test_gap) {
			fprintf(flog,"Flagging %d@%d for test-gap %d\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],days[iline] - days[first]) ;
			(*flags)[irow] = 0 ;
		} else if ((iline - first + 1) < min_test_num) {
			fprintf(flog,"Flagging %d@%d for test-num %d\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],iline-first+1) ;
			(*flags)[irow] = 0 ;
		} else
			(*flags)[irow] = 1 ;
	
		fprintf(flog,"Labeling %d@%d as %d %d\n",idnum, (int) lines[XIDX(iline,DATE_COL,ncols)],(int) ((*y)[irow]),(*flags)[irow]) ;

		// Fill the matrix
		int iftr = 0 ;

        // Gender
		if (gender_flag)
			(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,GENDER_COL,ncols)] ;			

		// Tests
		for(int j=0; j<NCBC ;j++)	{
			if ((reds[j] == 1 && take_red) || (reds[j] == 0 && take_white)) {
				double present_value,diff_value ;
				if (lines[XIDX(iline,TEST_COL+j,ncols)]==-1)
					present_value = MISSING_VAL ;
				else
					present_value = lines[XIDX(iline,TEST_COL+j,ncols)] ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = present_value ;

				for (int igap=0; igap<ngaps; igap++) {
					diff_value = get_diff(lines,TEST_COL+j,first,iline,days,days[iline]-gaps[igap],ncols) ;
					(*x)[XIDX(irow,iftr++,*nftrs)] = diff_value ;
				}
			}
		}

		if (take_biochem) {
			for(int j=NCBC; j<NCBC+NBIOCHEM ;j++)	{
				get_test_values(lines,TEST_COL+j,first,iline,days,gaps,ngaps,ncols,*x,irow,&iftr,*nftrs) ;
			}
		}

		if (take_ferritin) {
			int j = NCBC+NBIOCHEM ;
			get_test_values(lines,TEST_COL+j,first,iline,days,gaps,ngaps,ncols,*x,irow,&iftr,*nftrs) ;
		}

		// Age
		(*x)[XIDX(irow,iftr++,*nftrs)] =  (days[iline] - get_days((int)(lines[XIDX(iline,BDATE_COL,ncols)])))/365.0 ;

		for (int iperiod=0; iperiod<nperiods; iperiod++) {
			cnts[iperiod]=0 ;
			for(int k1=iline-1; k1>=first; k1--) { 
				if (countable[k1] && (days[iline]-days[k1]<period_max[iperiod]) && (days[iline]-days[k1]>period_min[iperiod]))
					cnts[iperiod]++;
			}
		}

		if (take_cnts) {
			for (int iperiod=0; iperiod<nperiods; iperiod++) {
				int current_cnts ;
				if (days[iline] >= first_cbc_day + period_max[iperiod])
					 current_cnts =  cnts[iperiod] ;
				else if (days[iline] > first_cbc_day + period_min[iperiod])
					current_cnts = ((int) (0.5 + CBC_PER_YEAR * (period_max[iperiod] - period_min[iperiod])/365.0)) ;
				else
					current_cnts =  ((int) (cnts[iperiod] + 0.5 + CBC_PER_YEAR * (first_cbc_day - (days[iline] - period_max[iperiod]))/365.0)) ;

				if (current_cnts > MAX_CNTS) 
					current_cnts = MAX_CNTS ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = (double ) current_cnts ;
			}
		}

		// SMX
		if (take_extra) {
			if (lines[XIDX(iline,SMX_COL,ncols)] == -1) {
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
			} else {
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL,ncols)] ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL+1,ncols)] ;					
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL+2,ncols)] ;
			}

			// BMI
			if (lines[XIDX(iline,BMI_COL,ncols)] == -1) {
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
			} else {
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,BMI_COL,ncols)] ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,BMI_COL+1,ncols)] ;
			}
		}

		irow++ ;
		cftrs = iftr ;
	}

	*nrows = irow ;

	free(days) ;
	free(cancer_discovery) ;
	free(countable) ;

	realloc(*x,(*nftrs)*(*nrows)*sizeof(double)) ;
	realloc(*y,(*nrows)*sizeof(double)) ;

	if (*x==NULL || *y==NULL) {
		fprintf(stderr,"Reallocation at end failed\n") ;
		return -1 ;
	} else
		return 0 ;
}

int get_full_matrix(double lines[], int nlines, FILE *flog, double **x, int **idnums, int **dates, int *nftrs, int *nrows, int min_test_gap, int min_test_num,
					int ftrs_flag, int gender_flag, int mftrs) {

	int npatients = 1 ;
	int ncols =  MAXCOLS ;

	for (int i=1; i<nlines; i++) {
		if (lines[XIDX(i,ID_COL,ncols)] != lines[XIDX(i-1,ID_COL,ncols)])
			npatients++ ;
	}
	fprintf(stderr,"No. of patients = %d\n",npatients) ;

	int take_red, take_white,take_biochem, take_cnts, take_extra, take_ferritin ;
	if (ftrs_flag == 0) { // CBC + Counts
		take_red = take_white = take_cnts = 1 ;
		take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 1) { // Full
		take_red = take_white = take_cnts = take_biochem = take_ferritin = take_extra = 1 ;
	} else if (ftrs_flag == 2) { // Red + Counts
		take_red = take_cnts = 1 ;
		take_white = take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 3) { // Age
		take_red = take_white = take_biochem = take_ferritin = take_cnts = 0 ;
	} else if (ftrs_flag == 4) { // White + Counts
		take_white = take_cnts = 1 ;
		take_red = take_biochem = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 5) { // CBC
		take_red = take_white = 1 ;
		take_biochem = take_cnts = take_ferritin = take_extra = 0 ;
	} else if (ftrs_flag == 6) { // CBC + Counts + Ferritin
		take_red = take_white = take_cnts = take_ferritin = 1 ;
		take_biochem = take_extra = 0 ;
	} else if (ftrs_flag == 7) { // CBC without history + Extra
		take_red = take_white = 1 ;
		take_biochem = take_cnts = take_ferritin = 0 ;
		take_extra = 1 ;
		ngaps = 0 ;
	} else if (ftrs_flag == 8) { // CBC + Counts + Extra
		take_red = take_white = take_cnts = take_extra = 1 ;
		take_biochem = take_ferritin = 0 ;
	}

	int ntests = 0 ;
	if (take_red)
		ntests += NRED ;
	if (take_white)
		ntests += (NCBC - NRED) ;
	if (take_biochem)
		ntests += NBIOCHEM ;
	if (take_ferritin)
		ntests ++ ;

	// Age 
	*nftrs = 1 ;
	// Gender
	if (gender_flag)
		(*nftrs) ++ ;
	// Tests
	*nftrs += ntests*(ngaps+1) ;
	// Counts
	if (take_cnts)
		*nftrs += nperiods ;
	// SMX + BMI
	if (take_extra)
		*nftrs += 5 ;

	if (*nftrs > mftrs) {
		fprintf(stderr,"Too many features : %d > %d\n",*nftrs,mftrs) ;
		return -1 ;
	}

	int *cnts = (int *) malloc(nperiods*sizeof(int)) ;
	int *days = (int *) malloc(nlines*sizeof(int)) ;
	int *missing_tests = (int *) malloc(nlines*sizeof(int)) ;
	int *countable = (int *) malloc(nlines*sizeof(int)) ;
	*x = NULL ;
	*idnums = NULL ;
	*dates = NULL ;

	if (days==NULL || missing_tests==NULL || cnts==NULL || countable ==NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	for(int i=0; i<nlines; i++) {
		days[i] = get_days((int)(lines[XIDX(i,DATE_COL,ncols)]+0.5)) ;

		missing_tests[i] = 0 ;
		for (int j=0; j<NCBC; j++) {
			if (lines[XIDX(i,TEST_COL+j,ncols)] == -1)
				missing_tests[i]++ ;
		}

		countable[i] = 0 ;
		for (int j=0; j<NCBC; j++) {
			if (lines[XIDX(i,TEST_COL+j,ncols)] != -1 && ((reds[j]==1 && take_red) || (reds[j]==0 && take_white)))
				countable[i] = 1 ;
		}

		if (countable[i] == 0 && take_biochem) {
			for (int j=NCBC; j<NCBC + NBIOCHEM; j++)
				if (lines[XIDX(i,TEST_COL+j,ncols)] != -1)
					countable[i] = 1 ;
		}
	}

	int irow = 0 ;
	int first = 0 ;
	int nblocks = 0 ;
	int cftrs = 0 ;

	int first_cbc_day = get_days(20030101) ;

	for (int iline=0; iline < nlines; iline++) {

		int idnum = (int) lines[XIDX(iline,ID_COL,ncols)];
		int prev_idnum = (int) lines[XIDX(first,ID_COL,ncols)] ;

		if (idnum != prev_idnum)
			first = iline ;

		if (lines[XIDX(iline,AGE_COL,ncols)] < MIN_AGE || lines[XIDX(iline,AGE_COL,ncols)] > MAX_AGE) {
			fprintf(flog,"Test: Ignoring %d@%d for Age = %f\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],lines[XIDX(iline,AGE_COL,ncols)]) ;
			continue ;
		}

		if (missing_tests[iline] >= MAX_MISSING_TESTS) {
			fprintf(flog,"Test : Ignoring %d@%d for not-enough-CBC-results\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)]) ;
			continue ;
		}

/*
		if (days[iline] - days[first] < min_test_gap) {
			fprintf(flog,"Test: Ignoring %d @ %d for test-gap %d\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)] - days[first]) ;
			continue ;
		}

		if ((iline - first + 1) < min_test_num) {
			fprintf(flog,"Test: Ignoring %d @ %d for test-num %d\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)],iline-first+1) ;
			continue;
		}
*/

		if (irow == nblocks*BLOCK_LINES) {
			nblocks++ ;

			fprintf(stderr,"Allocating block #%d (%d/%d)\n",nblocks,iline,nlines) ;
			(*x) = (double *) realloc(*x,(*nftrs)*nblocks*BLOCK_LINES*sizeof(double)) ;
			(*idnums) = (int *) realloc(*idnums,nblocks*BLOCK_LINES*sizeof(int)) ;
			(*dates) = (int *) realloc(*dates,nblocks*BLOCK_LINES*sizeof(int)) ;

			if (*x==NULL || *idnums==NULL || *dates==NULL) {
				fprintf(stderr,"Reallocation at block %d failed\n",nblocks) ;
				return -1 ;
			}
		}

		(*idnums)[irow] = idnum ;
		(*dates)[irow] = (int) (lines[XIDX(iline,DATE_COL,ncols)] + 0.5) ;

		// Fill the matrix
		int iftr = 0 ;

        // Gender
		if (gender_flag)
			(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,GENDER_COL,ncols)] ;

		// Tests
		for(int j=0; j<NCBC ;j++)	{
			if ((reds[j] == 1 && take_red) || (reds[j] == 0 && take_white)) {
				(*x)[XIDX(irow,iftr++,*nftrs)]  = (lines[XIDX(iline,TEST_COL+j,ncols)]==-1) ? MISSING_VAL : lines[XIDX(iline,TEST_COL+j,ncols)] ;
	
				for (int igap=0; igap<ngaps; igap++)
					(*x)[XIDX(irow,iftr++,*nftrs)] = get_diff(lines,TEST_COL+j,first,iline,days,days[iline]-gaps[igap],ncols) ;
			}
		}

		if (take_biochem) {
			for(int j=NCBC; j<NCBC+NBIOCHEM ;j++)	{
				get_test_values(lines,TEST_COL+j,first,iline,days,gaps,ngaps,ncols,*x,irow,&iftr,*nftrs) ;

//				(*x)[XIDX(irow,iftr++,*nftrs)]  = (lines[XIDX(iline,TEST_COL+j,ncols)]==-1) ? MISSING_VAL : lines[XIDX(iline,TEST_COL+j,ncols)] ;
//				for (int igap=0; igap<ngaps; igap++)
//					(*x)[XIDX(irow,iftr++,*nftrs)] = get_diff(lines,TEST_COL+j,first,iline,days,days[iline]-gaps[igap],ncols) ;
			}
		}

		if (take_ferritin) {
			int j = NCBC+NBIOCHEM ;
			get_test_values(lines,TEST_COL+j,first,iline,days,gaps,ngaps,ncols,*x,irow,&iftr,*nftrs) ;
			
//			(*x)[XIDX(irow,iftr++,*nftrs)]  = (lines[XIDX(iline,TEST_COL+j,ncols)]==-1) ? MISSING_VAL : lines[XIDX(iline,TEST_COL+j,ncols)] ;
//			for (int igap=0; igap<ngaps; igap++)
//				(*x)[XIDX(irow,iftr++,*nftrs)] = get_diff(lines,TEST_COL+j,first,iline,days,days[iline]-gaps[igap],ncols) ;
		}

		// Age
		(*x)[XIDX(irow,iftr++,*nftrs)] =  (days[iline] - get_days((int)(lines[XIDX(iline,BDATE_COL,ncols)])))/365.0 ;

		for (int iperiod=0; iperiod<nperiods; iperiod++) {
			cnts[iperiod]=0 ;
			for(int k1=iline-1; k1>=first; k1--) { 
				if (countable[k1] && (days[iline]-days[k1]<period_max[iperiod]) && (days[iline]-days[k1]>period_min[iperiod]))
					cnts[iperiod]++;
			}
		}

		if (take_cnts) {
			for (int iperiod=0; iperiod<nperiods; iperiod++) {		
				if (days[iline] >= first_cbc_day + period_max[iperiod])
					(*x)[XIDX(irow,iftr++,*nftrs)] =  cnts[iperiod] ;
				else if (days[iline] > first_cbc_day + period_min[iperiod])
					(*x)[XIDX(irow,iftr++,*nftrs)] = (double) ((int) (0.5 + CBC_PER_YEAR * (period_max[iperiod] - period_min[iperiod])/365.0)) ;
				else
					(*x)[XIDX(irow,iftr++,*nftrs)] =  (double) ((int) (cnts[iperiod] + 0.5 + CBC_PER_YEAR * (first_cbc_day - (days[iline] - period_max[iperiod]))/365.0)) ;
			}
		}

		if (take_extra) {	
			// SMX
			if (lines[XIDX(iline,SMX_COL,ncols)] == -1) {	
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
			} else {
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL,ncols)] ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL+1,ncols)] ;					
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,SMX_COL+2,ncols)] ;
			}

			// BMI
			if (lines[XIDX(iline,BMI_COL,ncols)] == -1) {
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = MISSING_VAL ;
			} else {
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,BMI_COL,ncols)] ;
				(*x)[XIDX(irow,iftr++,*nftrs)] = lines[XIDX(iline,BMI_COL+1,ncols)] ;
			}
		}
		fprintf(flog,"Test : Extracting %d@%d\n",idnum,(int) lines[XIDX(iline,DATE_COL,ncols)]) ;

		irow++ ;
		cftrs=iftr ;
	}

	*nrows = irow ;

	free(days) ;
	free(countable) ;

	realloc(*x,(*nftrs)*(*nrows)*sizeof(double)) ;

	if (*x==NULL) {
		fprintf(stderr,"Reallocation at end failed\n") ;
		return -1 ;
	} else
		return 0 ;
}
