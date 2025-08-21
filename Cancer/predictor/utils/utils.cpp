#define _CRT_SECURE_NO_WARNINGS

#include "CommonLib/common_header.h"
#include <stdlib.h>
#include <stdio.h>

using namespace std;

void split_matrix(char *argv[]) ;
void get_labels(char *argv[]) ;
void split_matrix_by_list(char *argv[]) ;
void txt2bin(char *txt_file, char *bin_file) ;
void bin2txt(char *bin_file, char *txt_file) ;
void combine(char *in1, char *in2, double p, char *out) ;
void analyze_history (char *file) ;
void fold_split(char *in, int nfold, char *out_pref, int seed) ;
void rep_to_bin(char *config_file, int train_flag, char* cancer_group, char *bin_file, int zLibFlag);

int main(int argc, char *argv[]) {

	assert(argc >= 2) ;
	
	if (strcmp(argv[1],"split")==0) {
		if (argc != 7) {
			fprintf(stderr,"Usage : utils.exe split InFile TrainFileName TestFileName PoroportionOfTest Seed\n") ;
			return -1 ;
		}
		split_matrix(argv) ;
	} else if (strcmp(argv[1],"get_labels")==0) {
		if (argc != 3) {
			fprintf(stderr,"Usage : utils.exe get_labels InFile\n") ;
			return -1 ;
		} 
		get_labels(argv) ;
	} else if (strcmp(argv[1],"split_by_list")==0) {
		if (argc != 4) {
			fprintf(stderr,"Usage : utils.exe split_by_list InFile TrainFileName TestFileName TestIdsListFile\n") ;
			return -1 ;
		} 
		split_matrix_by_list(argv) ;
	} else if (strcmp(argv[1],"txt2bin")==0) {
		if (argc != 4) {
			fprintf(stderr,"Usage : utils.exe txt2bin TestFile BinFile\n") ;
			return -1 ;
		} 
		txt2bin(argv[2],argv[3]) ;
	} else if (strcmp(argv[1],"bin2txt")==0) {
		if (argc != 4) {
			fprintf(stderr,"Usage : utils.exe bin2txt BinFile TestFile\n") ;
			return -1 ;
		} 
		bin2txt(argv[2],argv[3]) ;
	} else if (strcmp(argv[1],"combine")==0) {
		if (argc != 5 && argc != 6) {
			fprintf(stderr,"Usage : utils.exe combine InFile1 InFile2 OutFile [part of control to take, default=0.5]\n") ;
			return -1 ;
		} 
		double p = (argc==6) ? atof(argv[5]) : 0.5 ;
		combine(argv[2],argv[3],p,argv[4]) ;
	} else if (strcmp(argv[1],"analyze_history")==0) {
		if (argc != 3) {
			fprintf(stderr,"Usage : utils.exe analyze_history InFile\n") ;
			return -1 ;
		} 
		analyze_history(argv[2]) ;
	}
	else if (strcmp(argv[1], "fold_split") == 0) {
		if (argc != 6) {
			fprintf(stderr, "Usage : utils.exe fold_split InFile FoldsNum OutPrefix Seed\n");
			return -1;
		}
		fold_split(argv[2], atoi(argv[3]), argv[4], atoi(argv[5]));
	} else if (strcmp(argv[1],"rep2bin")==0) {
		if (argc != 6 && argc != 7) {
			fprintf(stderr, "Usage : utils.exe rep2bin repConfigFile trainFlag cancerGroup binFile [zlib-flag; default = 1]\n");
			return -1;
		}
		int zLibFlag = (argc == 6) ? 1 : atoi(argv[6]);
		rep_to_bin(argv[2], atoi(argv[3]), argv[4], argv[5],zLibFlag);
	} else {
		fprintf(stderr,"Unknown util %s\n",argv[1]) ;
		fprintf(stderr,"Current possibilities are : split get_labels test_preds get_stats normalize ls -lr bin2txt combine analyze_history fold_split\n") ;
		return -1 ;
	} 

	return 0 ;
}

void combine (char *in1, char *in2, double p, char *out) {
	fprintf(stderr, "'combine' utility is deprecated.\n"); fflush(stderr);
	exit(EXIT_FAILURE);

	double *lines;
	
	// Read 1.
	gzFile fin = safe_gzopen(in1, "rb");

	int nlines = readInputLines(fin, &lines);
	fprintf(stderr,"Read %d lines from %s\n",nlines,in1) ;

	// Filter 1.
	int nout = 0 ;
	int prev_id = -1 ;
	int take = 0 ;
	for (int i=0; i<nlines; i++) {
		int id = (int) lines[XIDX(i,ID_COL,MAXCOLS)] ;
		if (id != prev_id) {
			if (lines[XIDX(i,CANCER_COL,MAXCOLS)] != 0 || (lines[XIDX(i,CANCER_COL,MAXCOLS)]==0 && globalRNG::rand()/(globalRNG::max()+1.0) < p))
				take = 1 ;
			else
				take = 0 ;
			prev_id = id ;
		}
		if (take) {
			memcpy(lines + nout*MAXCOLS, lines + i*MAXCOLS, MAXCOLS*sizeof(double)) ;
			nout ++ ;
		}
	}
	fprintf(stderr,"Filtered to %d lines\n",nout) ;

	// Write to bin file
	fprintf(stderr,"Trying %s\n",out) ;
	gzFile fout = safe_gzopen((string(out) + ".gz").c_str(), "wb") ;
	gzwrite(fout, &nout, sizeof(int)) ;
	gzwrite(fout, lines, sizeof(double) * nout * MAXCOLS) ;
	free(lines);

	// Read 2.
	fin = safe_gzopen(in2, "rb") ;

	nlines = readInputLines(fin, &lines) ;
	fprintf(stderr,"Read %d lines from %s\n",nlines,in2) ;

	// Filter 2.
	int nout2 = 0 ;
	prev_id = -1 ;
	take = 0 ;
	for (int i=0; i<nlines; i++) {
		int id = (int) lines[XIDX(i,ID_COL,MAXCOLS)] ;
		if (id != prev_id) {
			if (lines[XIDX(i,CANCER_COL,MAXCOLS)] != 0 || globalRNG::rand()/(globalRNG::max()+1.0) < p)
				take = 1 ;
			else
				take = 0 ;
			prev_id = id ;
		}
		if (take) {
			memcpy(lines + nout2*MAXCOLS, lines + i*MAXCOLS, MAXCOLS*sizeof(double)) ;
			nout2 ++ ;
		}
	}

	fprintf(stderr,"Filtered to %d lines\n",nout2) ;
	assert(nout + nout2 < MAXLINES) ;

	// Add to bin file
	gzwrite(fout, lines, sizeof(double) * nout2 * MAXCOLS) ;
	free(lines);

	// Correct the number of lines
	nlines = nout + nout2;
	gzseek(fout, 0, SEEK_SET);
	gzwrite(fout, &nlines, sizeof(int));
	gzclose(fout) ;

	return ;
}
	
void bin2txt(char *bin_file, char *txt_file) {

	linearLinesType lines;

	gzFile fin = safe_gzopen(bin_file, "rb");

	int nlines = readInputLines(fin, &lines);
	fprintf(stderr,"Read %d lines\n", nlines) ;
	matrixLinesType linesM=(double (*)[MAXCOLS])lines;

	FILE *fout = safe_fopen(txt_file, "w") ;

	for (int i=0; i<nlines; i++) {
		for (int j=0; j<MAXCOLS-1; j++)
			fprintf(fout,"%f\t", linesM[i][j]) ;
		fprintf(fout,"%f\n",linesM[i][MAXCOLS-1]) ;
	}
	fprintf(stderr, "Processed %d lines\n", nlines) ;
	
	free(lines);
	gzclose(fin);
	fclose(fout);

	return ;
}
	
void txt2bin(char *txt_file, char *bin_file) {

	gzFile fin = safe_gzopen(txt_file, "rb");
	gzFile fout = safe_gzopen((string(bin_file) + ".gz").c_str(), "wb") ;

	// traverse the txt file once to count the number of lines
	int nlines = 0;
	string txtline;
	while (gzGetLine(fin, txtline) != NULL) nlines++;
	fprintf(stderr, "Text file has %d lines\n", nlines);
	gzwrite(fout, &nlines, sizeof(int)) ; 

	// rewind input file and convert line by line
	gzrewind(fin);
	nlines = 0;
	double line[MAXCOLS];
	while (gzGetLine(fin, txtline) != NULL) {
		vector<string> fields;
		split(fields, txtline, is_any_of("\t"));
		assert(fields.size() == MAXCOLS);
		for (int i = 0; i < fields.size(); i++) {
			line[i] = atof(fields[i].c_str());
		}		
		gzwrite(fout, line, sizeof(double) * MAXCOLS); 
		nlines++;
	}
	fprintf(stderr, "Wrote %d lines to bin file\n", nlines);

	gzclose(fin);
	gzclose(fout);

	return;
}

void analyze_history(char *file) {
	
	double *lines;

	gzFile fin = safe_gzopen(file, "rb");

	int nlines = readInputLines(fin,&lines) ;
	fprintf(stderr,"Read %d lines\n",nlines) ;

	int ncols = MAXCOLS ;
	int start_time = 30 ;
	int end_time = 730 ;

	int *days = (int *) malloc(nlines*sizeof(int)) ;
	int *cancer_discovery = (int *) malloc(nlines*sizeof(int)) ;
	assert (days!=NULL || cancer_discovery!=NULL) ;

	for(int i=0; i<nlines; i++) {
		days[i] = get_day((int)(lines[XIDX(i,DATE_COL,ncols)]+0.5)) ;
		cancer_discovery[i] = get_day((int)(lines[XIDX(i,CANCER_DATE_COL,ncols)]+0.5)) ;
	}
	int last_cancer_day = get_day(20111231) ;

	int first = 0 ;
	for (int iline=0; iline < nlines; iline++) {

		int idnum = (int) lines[XIDX(iline,ID_COL,ncols)];
		int prev_idnum = (int) lines[XIDX(first,ID_COL,ncols)] ;

		if (idnum != prev_idnum)
			first = iline ;

		if (lines[XIDX(iline,CANCER_COL,ncols)] < 0 || lines[XIDX(iline,CANCER_COL,ncols)] > 3)
			continue ;
		
		int age = ((int) lines[XIDX(iline,DATE_COL,ncols)])/10000 - ((int) lines[XIDX(iline,BDATE_COL,ncols)])/10000 ;
		if (age < MIN_AGE || age > MAX_AGE)
			continue ;

		if ((lines[XIDX(iline,CANCER_COL,ncols)]==1 || lines[XIDX(iline,CANCER_COL,ncols)]==2) &&
				(cancer_discovery[iline] < days[iline] + start_time || cancer_discovery[iline] > days[iline] + end_time))
			continue ;

		if (lines[XIDX(iline,CANCER_COL,ncols)]==0 && days[iline] + end_time > last_cancer_day)
			continue ;

		printf("%d\t%d",idnum,(int)(lines[XIDX(iline,DATE_COL,ncols)]+0.5)) ;
		for (int jline=first; jline<iline; jline ++)
			printf("\t%d",days[iline]-days[jline]) ;
		printf("\n") ;
	}
}

void get_labels(char *argv[]) {
	
	gzFile fin = safe_gzopen(argv[2], "rb");

	double *lines;
	int nlines = readInputLines(fin,&lines) ;
	assert(nlines != -1) ;
	fprintf(stderr,"Read %d lines from %s\n", nlines, argv[2]);
	
	int ncols = MAXCOLS ;
	for (int i=0; i<nlines; i++)
		printf("%d %d %d %d\n",(int) lines[XIDX(i,ID_COL,ncols)],(int) lines[XIDX(i,DATE_COL,ncols)],(int) lines[XIDX(i,CANCER_COL,ncols)],(int) lines[XIDX(i,CANCER_DATE_COL,ncols)]) ;

	return ;
}

void fold_split(char *in, int nfold, char *out_pref, int seed)  {
	// Read data
	gzFile fin=safe_gzopen(in, "rb");

	double *lines_array;
	int nlines = readInputLines(fin,&lines_array) ;
	double (* lines)[MAXCOLS] = (double (*)[MAXCOLS]) lines_array;
	assert(nlines != -1) ;
	fprintf(stderr,"Read %d lines from %s\n",nlines, in);

	// Count ids
	int nids = 1 ;
	for (int i=1;i<nlines; i++) {
		if (lines[i][0] != lines[i-1][0])
			nids ++ ;
	}
	fprintf(stderr,"Read %d ids\n",nids) ;

	// Shuffle
	fprintf(stderr,"Random seed = %d\n",seed) ;
	globalRNG::srand(seed) ;
	int *order = randomize(nids) ;
	assert(order != NULL) ;

	int *pointers = (int *) malloc(nids*sizeof(int)) ;
	int *numlines = (int *) malloc(nids*sizeof(int)) ;
	double *shuffled = (double *) malloc(nlines*MAXCOLS*sizeof(double)) ;
	assert(pointers!= NULL && numlines != NULL && shuffled != NULL) ;

	int idnum = 0 ;
	pointers[idnum] = 0 ;
	numlines[idnum] = 1 ;
	for (int i=1; i<nlines; i++) {
		if (lines[i][0] != lines[i-1][0]) {
			idnum ++ ;
			pointers[idnum] = i ;
			numlines[idnum] = 0 ;
		}
		
		numlines[idnum]++ ;
	}

	int outline = 0 ;
	for (int i=0; i<nids; i++) {
		for (int j=0; j<numlines[order[i]]; j++) {
			memcpy(shuffled+outline*MAXCOLS,lines[pointers[order[i]]+j],sizeof(lines[0])) ;
			outline ++ ;
		}
	}
	assert(outline==nlines) ;

	for (int i=0; i<nlines; i++)
		memcpy(lines[i],shuffled+i*MAXCOLS,sizeof(lines[0])) ;

	free(pointers) ;
	free(numlines) ;
	free(shuffled) ;

	// Split

	int size = nids/nfold ;
	int *points = (int *) malloc(nfold*sizeof(int)) ;
	assert(points != NULL) ;
	
	idnum = 0 ;
	int ifold = 0 ;
	points[ifold] = 0 ;
	for (int i=1; i<nlines; i++) {
		if (lines[i][0] != lines[i-1][0])
			idnum ++ ;
		
		if (idnum == size) {
			points[++ifold] = i ;
			idnum = 0 ;
		}
	}

	for (int i=0; i<nfold; i++) {
		fprintf(stderr,"Working on %d/%d\n",i+1,nfold) ;
		int start = points[i] ;
		int end = (i<nfold-1) ? points[i+1] : nlines ;
		int test_size = end - start ;

		char fname[256] ;
		sprintf(fname,"%s.test%d.bin.gz",out_pref,i+1) ;
		gzFile out_fp = safe_gzopen(fname,"wb") ;

		fprintf(stderr,"Test Set Size : %d nlines\n",test_size) ;
		gzwrite(out_fp, &test_size, sizeof(test_size));
		gzwrite(out_fp, lines + start, test_size * sizeof(lines[0]));
		gzclose(out_fp);

		sprintf(fname,"%s.train%d.bin.gz",out_pref,i+1) ;
		out_fp = safe_gzopen(fname,"wb") ;

		int train_size = nlines - test_size ;
		fprintf(stderr,"Train Set Size : %d nlines\n",train_size) ;
		gzwrite(out_fp, &train_size, sizeof(train_size));
		if (start > 0)
			gzwrite(out_fp, lines, start * sizeof(lines[0])) ;
		if (end < nlines)
			gzwrite(out_fp, lines+end, (nlines-end) * sizeof(lines[0])) ;
		gzclose(out_fp);
	}
}

void split_matrix(char *argv[]) {

	fprintf(stderr, "split_matrix is not supported for now; consider using VBF format with appropriate list of IDs\n"); fflush(stderr);
	exit(EXIT_FAILURE);

	double ratio = atof(argv[5]) ;
	int val = 1234 * atoi(argv[6]) ;
	globalRNG::srand(val) ;

	char in_file[256] ;
	strcpy(in_file,argv[2]) ;

	char train_file[256] ;
	strcpy(train_file,argv[3]) ;

	char test_file[256] ;
	strcpy(test_file,argv[4]) ;

	gzFile train_fp = safe_gzopen(train_file, "wb") ;
	gzFile test_fp = safe_gzopen(test_file, "wb") ;

	int n_test = 0;
	int n_train = 0;
	// write dummy line numbers as place holders
	gzwrite(test_fp, &n_test, sizeof(n_test));
	gzwrite(train_fp, &n_train, sizeof(n_train));

	// Read data
	gzFile fin = safe_gzopen(in_file, "rb");

	double *lines_array;
	int nlines = readInputLines(fin, &lines_array) ;
	double (* lines)[MAXCOLS] = (double (*)[MAXCOLS]) lines_array;
	assert(nlines != -1) ;
	
	fprintf(stderr,"Read %d lines from %s\n",nlines,in_file);

	int idnum = -1 ;
	int is_test ;

	for (int i=0; i<nlines; i++) {
		int new_idnum = (int) lines[i][ID_COL] ;
		if (new_idnum != idnum) {
			idnum = new_idnum ;
//			printf("%d\n",idnum) ;

			if (globalRNG::rand()/(globalRNG::max()+1.0) < ratio)
				is_test = 1 ;
			else
				is_test = 0 ;
		}
		if (is_test) {
			gzwrite(test_fp, lines[i], sizeof(double) * MAXCOLS);
			n_test++;
		}
		else {
			gzwrite(train_fp, lines[i], sizeof(double) * MAXCOLS);
			n_train++;
		}
	}

	/***
	The code below fails to work due to gzseek() limitations - files must be traversed twice,
	counting n_test and n_train in the first traversal and writing them to output files
	immediately after openning them.
	***/

	gzseek(test_fp, 0, SEEK_SET);
	gzwrite(test_fp, &n_test, sizeof(n_test));
	gzclose(test_fp);

	gzseek(train_fp, 0, SEEK_SET);
	gzwrite(train_fp, &n_train, sizeof(n_test));
	gzclose(train_fp);

	return ;
}

void split_matrix_by_list(char *argv[]) {

	gzFile train_fp = safe_gzopen("Train.bin.gz", "wb") ;
	gzFile test_fp = safe_gzopen("Test.bin.gz", "wb") ;
	gzFile list_fp = safe_gzopen(argv[2], "r") ;

	int n_test = 0;
	int n_train = 0;
	gzwrite(test_fp, &n_test, sizeof(int));
	gzwrite(train_fp, &n_train, sizeof(int));

	// Read list
	int id ;
	map<int, int> list ;
	string strLine;
	while (gzGetLine(list_fp, strLine) != NULL) {
		assert(sscanf(strLine.c_str(), "%d\n",&id) == 1) ;
		list[id] = 1 ;
	}

	// Read input
	gzFile fin = safe_gzopen(argv[3], "rb");

	double *lines_array;
	int nlines = readInputLines(fin, &lines_array) ;
	double (* lines)[MAXCOLS] = (double (*)[MAXCOLS]) lines_array;
	assert(nlines != -1) ;

	fprintf(stderr,"Read %d lines from %s\n",nlines, argv[3]);

	// write test and train lines alternately
	int n = 0 ;
	for (int i=0; i<nlines; i++) {
		int id = (int) lines[i][ID_COL] ;
		if (list.find(id) != list.end()) {
			gzwrite(test_fp, lines[i], sizeof(double) * MAXCOLS);
			n_test++ ;
		}
		else {
			gzwrite(train_fp, lines[i], sizeof(double) * MAXCOLS);
			n_train++;
		}
	}

	fprintf(stderr,"Printed %d lines to testing set and %d line to training set\n",n_test,n_train) ;

	// write line numbers
	gzseek(test_fp, 0, SEEK_SET);
	gzwrite(test_fp, &n_test, sizeof(n_test));
	gzclose(test_fp);

	gzseek(train_fp, 0, SEEK_SET);
	gzwrite(train_fp, &n_test, sizeof(n_test));
	gzclose(train_fp);

	return ;
}

void rep_to_bin(char *config_file, int train_flag, char *cancer_group, char *bin_file, int zLibFlag) {

	// Read Repository
	MedRepository repository;
		
	int rc = repository.read_all(string(config_file));
	assert(rc >= 0);

	// Get Id List
	map <int, set<int> > id_list;
	int len;
	int trainId = repository.dict.id("TRAIN");
	assert(train_flag == 0 || trainId >= 0);

	for (int id : repository.index.pids) {
		if (train_flag == 0)
			id_list[id] = set<int>();
		else {
			SVal *train = (SVal *)repository.get(id, trainId, len);
			if (train[0].val == train_flag)
				id_list[id] = set<int>();
		}
	}

	// Get Lines
	matrixLinesType linesM;
	int nlines = buildBinFromRepository(repository, id_list, string(cancer_group), &linesM);

	linearLinesType lines = (linearLinesType)linesM;

	// Write to file
	gzFile newZBinFile;
	FILE *newBinFile;
	if (zLibFlag)
		newZBinFile = safe_gzopen(bin_file, "wb");
	else
		newBinFile = fopen(bin_file, "wb");

	// number of lines
	int bytes_written;
	if (zLibFlag)
		bytes_written = gzwrite(newZBinFile, &nlines, sizeof(int));
	else
		bytes_written = fwrite(&nlines, 1, sizeof(int), newBinFile );
	assert(bytes_written = 4);

	// write lines in possibly several blocks to bypass gzread limitation of 2GB
	long numWriteLines = 0;
	int numLinesInBlock = int(2000000000 / MAXCOLS / sizeof(double));
	int blockSize = sizeof(double) * MAXCOLS * numLinesInBlock;
	
	while (numWriteLines < nlines) {
		int maxWrite = (blockSize < (nlines - numWriteLines) * sizeof(double) * MAXCOLS) ? blockSize : (nlines - numWriteLines) * sizeof(double) * MAXCOLS;
		fprintf(stderr, "Trying to write at most %d bytes ...\n", maxWrite);
		int nwrite;
		if (zLibFlag)
			nwrite = gzwrite(newZBinFile, lines + MAXCOLS * numWriteLines, maxWrite);
		else
			nwrite = fwrite(lines + MAXCOLS *numWriteLines, 1, maxWrite, newBinFile);
		fprintf(stderr, "Written %d bytes\n", nwrite); fflush(stderr);
		assert(nwrite == maxWrite);

		numWriteLines += nwrite / sizeof(double) / MAXCOLS;
	}

	assert(numWriteLines == nlines);
	
	if (zLibFlag)
		gzclose(newZBinFile);
	else
		fclose(newBinFile);
}

