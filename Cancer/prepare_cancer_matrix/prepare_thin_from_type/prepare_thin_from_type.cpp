// prepare_thin_from_type.cpp : Prepare matrices from THIN data for predicting a given cancer.
//

#define _CRT_SECURE_NO_WARNINGS

#include "prepare_thin_from_type.h"
#include "prepare_from_type/prepare_from_type.h"

int main(int argc, char * argv[])
{

	// Parse parameters
	if (argc != 4 && argc != 5) {
		fprintf(stderr,"Usage : prepare_thin_from_type.exe cbc-in dir suffix [type]\n") ;
		return -1 ;
	}

	strcpy(thin_cbc_file,argv[1]) ;

	char dir[256] ;
	strcpy(dir,argv[2]) ;

	char suffix[256] ;
	strcpy(suffix,argv[3]) ;

	int group = (argc==5) ? atoi(argv[4]) : -1 ;

	// Initialize
	assert(init_thin_codes()!=-1) ;

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

	// CBC + Biochem
	assert(read_thin_file()!= -1) ;
	fprintf(stderr,"CBC: Done, enumlistcol=%d\n", enumlistcol) ;
	
	// Demographics
	read_demographics(); 
	fprintf(stderr,"Demog: Done\n") ;

	// BMI
	enumlistcol += NBMI_FTRS ;

	// Smoking
	read_thin_smx() ;
	fprintf(stderr,"SMX: Done\n") ;

	// Quantitative smoking
	read_thin_qty_smx() ;
	fprintf(stderr,"Qty SMX: Done\n") ; 

	// Registry
	if (group != -1) {
		vector<string> relevant ;
		read_list(relevant,group) ;
		for (unsigned int i = 0 ; i<relevant.size(); i++) 
			fprintf(stderr,"Considering %s\n",relevant[i].c_str()) ;

		read_rasham(relevant,3) ;
		fprintf(stderr,"Cancer registery : Done\n") ;
	}

	// Status
	read_status() ;
	fprintf(stderr,"Status: Done\n") ;

	// output
	sortfile();
	printf("Writing files ....\n");
	char out_file[256] ;

	char genders[2][256] = {"men","women"} ;
	for (int i=0; i<2; i++) {
		sprintf(out_file,"%s\\%s_%s.bin",dir,genders[i],suffix) ;
		fprintf(stderr,"Writing to %s\n",out_file) ;
		writefile(out_file,i);
	}

	return 0;
}