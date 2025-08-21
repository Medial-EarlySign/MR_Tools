#include <stdio.h>
#include <malloc.h>

const char source_filename_patten[] = "%s\\%s\\%s";
const char path_pattern[] = "\\\\server\\temp\\summary_stats\\input";
const char cbc_input_filename_pattern[] = "cbc.txt";
const char cbc_output_filename_pattern[] = "cbc.bin";

const int MAX_STRING_LEN = 1024;

typedef struct {
	int id;
	int code;
	int date;
	double value;
} cbc_entry_t;

int read_cbcs_txt(char *input_file_name, char *output_file_name) {

	fprintf(stderr, "Reading cbc file %s; and writing binary file %s\n", input_file_name, output_file_name);

	FILE *fin = NULL, *fout = NULL;
	
	fin = fopen(input_file_name, "rb");
	if (fin == NULL) {
		fprintf(stderr, "Could not open file \'%s\' for reading\n", input_file_name);
		return -1 ;
	}

	// count number of lines
	printf("Counting number of lines for %s:\n", input_file_name );
	int lines = 0;
	int ch = fgetc(fin);
	do {
		if ( ch == '\n' ) {
			lines++;
			if( lines % 100000 == 0 ) {
				printf( "%d ...", lines);
			}
		}
		ch = fgetc(fin);
	} while( ch != EOF );
	printf("\nFound %d lines\n", lines );

	int ret = fseek(fin, 0, SEEK_SET);
	if( ret != 0 ) {
		fprintf(stderr, "Error seeking to begining of file %s\n", input_file_name);
		return -1;
	}

	fout = fopen(output_file_name, "wb");
	if (fout == NULL) {
		fprintf(stderr, "Could not open file \'%s\' for writing\n", output_file_name);
		return -1 ;
	}

	cbc_entry_t *cbc_entry = (cbc_entry_t *)malloc(lines*sizeof(cbc_entry_t));
	if( cbc_entry == NULL ) { 
		fprintf(stderr,"Could not malloc %d elements of cbc_entry_t(%zd)\n", lines, sizeof(cbc_entry_t)) ;
		return -1 ;
	}

	fprintf(stderr,"Reading %d lines from %s:\n", lines, input_file_name ) ;
	int itest = 0 ;
	while (! feof(fin)) {
		int rc = fscanf(fin,"%d %d %d %lf\n",
			&cbc_entry[itest].id, &cbc_entry[itest].code, &cbc_entry[itest].date, &cbc_entry[itest].value) ;
		if (rc == EOF)
			break ;

		if (rc != 4) {
			// Note: not all encoding types are supported (try to convert to UTF-8)
			fprintf(stderr,"Could not read status line from \'%s\'. rc = %d. line = %d\n", input_file_name, rc, itest) ;
			return -1 ;
		}

		if (cbc_entry[itest].date%10000 == 0) {
			fprintf(stderr,"(Ignoring %d %d %d %lf)",
				cbc_entry[itest].id,cbc_entry[itest].code,cbc_entry[itest].date,cbc_entry[itest].value) ;
			continue;
		}

		if ((++itest)%100000 == 0) {
			fprintf(stderr,"%d ... ",itest) ;
		}
	}

	fprintf(stderr,"\nWriting header [%s]\n", output_file_name) ;
	size_t number = fwrite(&lines, sizeof(lines), 1, fout );
	if( number != 1 ) {
		fprintf(stderr,"Error writing number of lines. number of lines = %zd\n", number) ;
		return -1;
	}

	fprintf(stderr,"Writing %d lines to [%s]\n", lines, output_file_name) ;
	number = fwrite(cbc_entry, sizeof(cbc_entry_t), lines, fout );
	if( number != lines ) {
		fprintf(stderr,"Error writing cbc_entry. number of lines = %zd\n", number) ;
		return -1;
	} 
	
	fprintf(stderr,"Done!\n") ;
	
	fclose(fin) ;
	fclose(fout) ;
	return 0 ;
}

int main( int argc, char *argv[] )
{
	if( argc != 2 ) {
		fprintf( stderr, "Usage: %s <path>\n", argv[0] );
		return -1;
	}

	char *source_path = argv[1];

	char input_filename[MAX_STRING_LEN];
	snprintf(input_filename, MAX_STRING_LEN*sizeof(char), "%s/cbc.txt",source_path) ;
	char output_filename[MAX_STRING_LEN];
	snprintf(output_filename, MAX_STRING_LEN*sizeof(char), "%s/cbc.bin",source_path) ;
	return read_cbcs_txt( input_filename, output_filename );

}