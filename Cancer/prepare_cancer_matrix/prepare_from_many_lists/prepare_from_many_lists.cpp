// prepare.cpp : Prepare matrices for Colon Cancer prediction based on lists of id+date.
//

#define _CRT_SECURE_NO_WARNINGS

#include "prepare_from_type/params.h"
#include "prepare_from_type/prepare.h"
#include "prepare_from_many_lists.h"
#include "prepare_from_two_lists/prepare_from_two_lists.h"

int main(int argc, char * argv[])
{

	// Handle input
	assert(argc == 3) ;

	if (strcmp(argv[1],"men") == 0)
		gender = 0 ;
	else if (strcmp(argv[1],"women") == 0)
		gender = 1 ;
	else {
		fprintf(stderr,"Cannot handle gender %s\n",argv[1]) ;
		return -1 ;
	}

	int npairs = read_infile(argv[2]) ;
	assert(npairs > 0) ;

	fprintf(stderr,"Working on %d pairs\n",npairs) ;


	fprintf(stderr,"working on %s\n",(gender==0) ? "Men":"Women") ;

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
	assert(readfile(0)!= -1) ;
	fprintf(stderr,"CBC: Done\n") ;

	// Biochemistry
	assert(readallbiochem(0,0) != -1) ;
	fprintf(stderr,"BioChem: Done\n") ;

	// BMI
	readBMI() ;
	fprintf(stderr,"BMI: Done\n") ;

	// SMX
	readsmx() ;
	fprintf(stderr,"SMX: Done\n") ;

	printf("Finished reading file... making fast search\n");

	// Demographics
	read_demographics(); 
	fprintf(stderr,"Demog: Done\n") ;

	// Status
	read_status() ;
	fprintf(stderr,"Status: Done\n") ;


	for (int i=0; i<npairs; i++) {
		fprintf(stderr,"Working on pair %d : %s %s => %s\n",i,list1[i],list2[i],out[i]) ;

		// Lists
		readlists(list1[i],list2[i]) ;
		fprintf(stderr,"Lists : Done\n") ;

		// Output
		printf("Writing file....\n");
		sort_and_write_file(out[i]);
	}
	

	return 0;
}
