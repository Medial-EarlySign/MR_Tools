
// prepare_from_type.cpp : Prepare matrices for predicting a given cancer.
//

#define _CRT_SECURE_NO_WARNINGS

#include "params.h"
#include "prepare.h"
#include "prepare_from_type.h"

int main(int argc, char * argv[])
{

	// Parse parameters
	if (argc != 5 && argc != 6) {
		fprintf(stderr,"Usage : prepare_from_type.exe dir gender type IdsList/NONE [full/complete]\n") ;
		return -1 ;
	}


	if (strcmp(argv[2],"men") == 0)
		gender = 0 ;
	else if (strcmp(argv[2],"women") == 0)
		gender = 1 ;
	else {
		fprintf(stderr,"Cannot handle gender %s\n",argv[2]) ;
		return -1 ;
	}
	fprintf(stderr,"working on %s\n",argv[2]) ;

	int group = atoi(argv[3]) ;

	map<int,int> ids_list ;
	int list = -1 ;
	if (strcmp(argv[4],"NONE") != 0) {
		list = 1 ;
		if (read_ids_list(argv[4],ids_list)==-1) {
			fprintf(stderr,"Cannot read list of ids\n") ;
			return -1 ;
		}
	}

	int full = 0 ;
	if (argc == 6) {
		if (strcmp(argv[5],"full") == 0)
			full = 1 ;
		else if (strcmp(argv[5],"complete") == 0)
			full = 2 ;
		else {
			fprintf(stderr,"Usage : prepare_from_type.exe dir gender type IdsList/NONE [full/complete]\n") ;
			return -1 ;
		}
	}

	char out_prefix[256] ;
	sprintf(out_prefix,"%s\\%s_%d",argv[1],argv[2],group) ;

	// Initialize
	assert(init_codes()!=-1) ;
	
	lines_array  = (double *) malloc (MAXLINES*MAXCOLS*sizeof(double)) ;
	if (lines_array == NULL) {
		fprintf(stderr,"Cannot allocate memory for lines_arary\n") ;
		return -1 ;
	}

	lines = (double (*)[MAXCOLS]) lines_array; // casting as a 2D matrix

	for(int i=0; i<MAXLINES; i++) {
		for(int j=0; j<MAXCOLS; j++)
			lines[i][j]=-1;
	}

	fprintf(stderr,"Starting\n") ;

	// CBC
	if (list == 1)
		assert(readfile(ids_list,full) != -1) ;
	else
		assert(readfile(full)!= -1) ;
	fprintf(stderr,"CBC: Done\n") ;
	fprintf(stderr,"IDS # = %zd\n",line_nos.size()) ;

	// Biochem
	int take_new = 0 ;
	assert(readallbiochem(full,take_new) != -1) ;
	fprintf(stderr,"BioChem: Done\n") ;
	fprintf(stderr,"IDS # = %zd\n",line_nos.size()) ;

	// BMI
	readBMI() ;
	fprintf(stderr,"BMI: Done\n") ;
	fprintf(stderr,"IDS # = %zd\n",line_nos.size()) ;

	// Smoking
	readsmx() ;
	fprintf(stderr,"SMX: Done\n") ;
	fprintf(stderr,"IDS # = %zd\n",line_nos.size()) ;

	printf("Finished reading file... making fast search\n");

	// Registry
	if (group != -1) {
		vector<string> relevant ;
		read_list(relevant,group) ;
		for (unsigned int i = 0 ; i<relevant.size(); i++) 
			fprintf(stderr,"Considering %s\n",relevant[i].c_str()) ;

		read_rasham(relevant,full) ;
		fprintf(stderr,"Cancer registery : Done\n") ;
	}
	 
	// Demographics
	read_demographics(); 
	fprintf(stderr,"Demog: Done\n") ;

	// Status
	read_status() ;
	fprintf(stderr,"Status: Done\n") ;

	// output
	sortfile();
	printf("Writing file....\n");
	char out_file[256] ;

	sprintf(out_file,"%s.bin",out_prefix) ;
	fprintf(stderr,"Writing to %s\n",out_file) ;
	writefile(out_file);

//	sprintf(out_file,"%s.txt",out_prefix) ;
//	fprintf(stderr,"Writing to %s\n",out_file) ;
//	write_txtfile(out_file);

	return 0;
}
