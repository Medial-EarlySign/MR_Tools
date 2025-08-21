// prepare_validation.cpp : Prepare matrices for validation.
//

#define _CRT_SECURE_NO_WARNINGS

#include "prepare_from_type/params.h"
#include "prepare_from_type/prepare.h"
#include "prepare_from_type/prepare_from_type.h"

#include <time.h>

int main(int argc, char * argv[])
{

	// Parse parameters
	if (argc != 4 && argc != 5) {
		fprintf(stderr,"Usage : prepare_for_validation.exe prefix configuration group [id]\n%s%s%s%s%s",
					"Args:\n",
					"prefix - output file name is prefix.bin\n",
					"configuration - name of configuration file, holding types and names of medical record files\n",
					"group - type of cancer (use -1 for creating a validation file)\n",
					"id - list of identifiers to include in output file\n");
		return -1 ;
	}

	// Read file names from configuration file
	map<string,vector<string> > file_names ;
	assert(read_input_file_names(argv[2],file_names) != -1) ;

	// Initialize
	assert(init_codes()!=-1) ;

	lines_array  = (double *) malloc (MAXLINES*MAXCOLS*sizeof(double)) ;
	if (lines_array == NULL) {
		fprintf(stderr,"Cannot allocate memory for lines_arary\n") ;
		return -1 ;
	}

	lines = (double (*)[MAXCOLS]) lines_array; // casting as a 2D matrix

	// memset(lines, 255,  sizeof(lines)); not needed ?

	for(int i=0; i<MAXLINES; i++) {
		for(int j=0; j<MAXCOLS; j++)
			lines[i][j]=-1;
	}

	fprintf(stderr,"Starting\n") ;
	int group = atoi(argv[3]) ;
	
	// Read Ids list
	if (argc==5)
		assert(read_ids(argv[4]) != -1) ;

	// CBC
	if (file_names.find("cbc") != file_names.end())
		assert(read_cbcs(file_names["cbc"])!=-1) ;
	fprintf(stderr,"CBC: Done\n") ;

	// Biochem
	if (file_names.find("biochem") != file_names.end())
		assert(read_biochems(file_names["biochem"], 0)!=-1) ;
	fprintf(stderr,"BioChem: Done\n") ;
	
	// BMI
	if (file_names.find("bmi") != file_names.end())
		assert(read_bmis(file_names["bmi"])!=-1) ;
	fprintf(stderr,"BMI: Done\n") ;

	// Smoking
	if (file_names.find("smx") != file_names.end())
		assert(read_smxs(file_names["smx"])!=-1) ;
	fprintf(stderr,"SMX: Done\n") ;
	fprintf(stderr,"IDS # = %zd\n",line_nos.size()) ;

	printf("Finished reading file... making fast search\n");

	// Registry
	if (group != -1) {
		vector<string> relevant ;
		read_list(relevant, group) ;
		for (unsigned int i = 0 ; i<relevant.size(); i++) 
			fprintf(stderr,"Considering %s\n",relevant[i].c_str()) ;

		string reg_fn = "";
		if (file_names.find("reg") != file_names.end()) {
			reg_fn = file_names["reg"][0];
		}
		else {
			fprintf(stderr, "No registry file name in configuration file while group=%d\n", group);
			exit(-1);
		}

		read_rasham(relevant, 4, reg_fn) ; // unlimited cancer dates
		fprintf(stderr,"Cancer registery : Done\n") ;
	}

	// Demographics
	if (file_names.find("demog") != file_names.end())
		assert(read_demographics(file_names["demog"])!=-1) ;
	fprintf(stderr,"Demog: Done\n") ;

	// Status
	if (file_names.find("status") != file_names.end())
		assert(read_status(file_names["status"])!=-1) ;
	fprintf(stderr,"Status: Done\n") ;

	// output
	sortfile();
	printf("Writing file....\n");
	char out_file[256] ;

	sprintf(out_file,"%s.bin",argv[1]) ;
	fprintf(stderr,"Writing to %s\n",out_file) ;

	writefile(out_file);

//	sprintf(out_file,"%s_validation.txt",argv[1]) ;
//	fprintf(stderr,"Writing to %s\n",out_file) ;

//	write_txtfile(out_file);

	return 0;
}
