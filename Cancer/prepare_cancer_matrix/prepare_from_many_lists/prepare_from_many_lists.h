#define MAX_PAIRS 500
#define MAX_STRING_LEN 256

char list1[MAX_PAIRS+1][MAX_STRING_LEN] ;
char list2[MAX_PAIRS+1][MAX_STRING_LEN] ;
char out[MAX_PAIRS+1][MAX_STRING_LEN] ;

int read_infile(char *file_name) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL)
		return -1 ;

	int ipair = 0 ;
	while (!feof(fp)) {

		int rc = fscanf(fp,"%s %s %s\n",list1[ipair],list2[ipair],out[ipair]) ;
		if (rc == EOF)
			break ;

		if (rc != 3)
			return -1 ;

		ipair++ ;
	}

	return ipair ;
}