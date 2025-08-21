// Prepare engine for MS_CRC_Scorer based on setup file //

#define _CRT_SECURE_NO_WARNINGS

#include "stdlib.h"
#include "stdio.h"
#include "string.h"

#include <map>
#include <vector>
#include <string>
#include <assert.h>

using namespace std ;

#define NTESTS 20
#define MAX_STRING_LEN 256
#define MAX_BUF_SIZE 1024
#define NFILES 12 

typedef struct {
	int left,right,status,svar,pred ;
	double sval ;
} node ;

typedef node *tree ;
typedef tree *forest ;

int read_rf_model (FILE *fin, forest *rf, int **nnodes, int *ntrees) ;
void copy_rf_model(string& from, char *to) ;

int main(int argc, char *argv[]) {

	// Open input file
	assert(argc == 3) ;

	string from(argv[1]) ;
	copy_rf_model(from,argv[2]) ;
	return 0 ;
}

void copy_rf_model(string& from, char *to) {

	fprintf(stderr,"RF Analysis: %s\n",from.c_str()) ;

	FILE *in_fp = fopen(from.c_str(),"r") ;
	assert(in_fp != NULL) ;

	forest rf ;
	int ntrees ;
	int *nnodes ;
	assert(read_rf_model(in_fp,&rf,&nnodes,&ntrees) == 0) ;
	fclose(in_fp) ;

	FILE *out_fp = fopen(to,"wb") ;
	assert(out_fp != NULL) ;

	fwrite(&ntrees,sizeof(int),1,out_fp) ;
	for (int i=0; i<ntrees; i++) {
		fwrite(nnodes+i,sizeof(int),1,out_fp) ;
		fwrite(rf[i],sizeof(node),nnodes[i],out_fp) ;
		free(rf[i]) ;
	}

	free(rf) ; 
	free(nnodes) ;

	fclose(out_fp) ;

	return ;
}

int read_rf_model (FILE *fin, forest *rf, int **nnodes, int *ntrees) {

	char buffer[MAX_BUF_SIZE] ;
	char field[MAX_STRING_LEN] ;

	char *startbuf,*endbuf ;

	// Header (Number of trees)
	fgets(buffer, sizeof(buffer), fin);
	if (feof(fin))
		return 1 ;

	startbuf = buffer;             
	endbuf = buffer;
			
	while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
		*endbuf ++ ;

	if (*endbuf != ' ' || endbuf - startbuf > MAX_STRING_LEN - 1)
		return 1 ;

	startbuf= ++endbuf ;
	while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != '\t'))
		*endbuf ++ ;

	if (((*endbuf != '\n') && (*endbuf != '\r')) || endbuf - startbuf > MAX_STRING_LEN - 1)
		return 1 ;
	
	strncpy(field,startbuf, endbuf-startbuf);                     
	field[endbuf-startbuf]='\0';
	*ntrees = atoi(field) ;

	(*rf) = (forest) malloc((*ntrees)*sizeof(tree)) ;
	if ((*rf) == NULL)
		return 1 ;

	(*nnodes) = (int *) malloc((*ntrees)*sizeof(int)) ;
	if ((*nnodes) == NULL)
		return 1 ;

	for (int i=0; i<(*ntrees); i++) {
		// Tree Header (Number of nodes)
		fgets(buffer, sizeof(buffer), fin);
		if (feof(fin))
			return 1 ;

		startbuf = buffer;             
		endbuf = buffer;
			
		while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
			*endbuf ++ ;

		if (*endbuf != ' ' || endbuf - startbuf > MAX_STRING_LEN - 1)
			return 1 ;

		startbuf= ++endbuf ;
		while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != '\t'))
			*endbuf ++ ;

		if (((*endbuf != '\n') && (*endbuf != '\r')) || endbuf - startbuf > MAX_STRING_LEN - 1)
			return 1 ;
	
		strncpy(field,startbuf, endbuf-startbuf);                     
		field[endbuf-startbuf]='\0';
		(*nnodes)[i] = atoi(field) ;	

		(*rf)[i] = (tree) malloc((*nnodes)[i]*sizeof(node)) ;
		if ((*rf)[i] == NULL)
			return 1 ;

		// Header
		fgets(buffer, sizeof(buffer), fin);
		if (feof(fin))
			return 1 ;
	
		for (int j=0; j<(*nnodes)[i]; j++) {
			fgets(buffer, sizeof(buffer), fin);
			if (feof(fin))
				return 1 ;

			// Node information
			startbuf = buffer;             
			endbuf = buffer;
			
			// Id
			while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
				*endbuf ++ ;

			if (*endbuf != ' ' || endbuf - startbuf > MAX_STRING_LEN - 1)
				return 1 ;

			strncpy(field,startbuf, endbuf-startbuf);                     
			field[endbuf-startbuf]='\0';
			int id = atoi(field) ;	
		
			startbuf= ++endbuf ;
			while (*endbuf == ' ')
				*endbuf ++ ;

			// Left daughter
			while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
				*endbuf ++ ;

			if (*endbuf != ' ' || endbuf - startbuf > MAX_STRING_LEN - 1)
				return 1 ;

			strncpy(field,startbuf, endbuf-startbuf);                     
			field[endbuf-startbuf]='\0';
			int left = atoi(field) ;

			startbuf= ++endbuf ;
			while (*endbuf == ' ')
				*endbuf ++ ;

			// Right daughter
			while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
				*endbuf ++ ;

			if (*endbuf != ' ' || endbuf - startbuf > MAX_STRING_LEN - 1)
				return 1 ;

			strncpy(field,startbuf, endbuf-startbuf);                     
			field[endbuf-startbuf]='\0';
			int right = atoi(field) ;	

			startbuf= ++endbuf ;
			while (*endbuf == ' ')
				*endbuf ++ ;

			// Split Variable
			while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
				*endbuf ++ ;

			if (*endbuf != ' ' || endbuf - startbuf > MAX_STRING_LEN - 1)
				return 1 ;

			strncpy(field,startbuf, endbuf-startbuf);                     
			field[endbuf-startbuf]='\0';
			int svar = atoi(field) ;	

			startbuf= ++endbuf ;
			while (*endbuf == ' ')
				*endbuf ++ ;

			// Split Value
			while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
				*endbuf ++ ;

			if (*endbuf != ' ' || endbuf - startbuf > MAX_STRING_LEN - 1)
				return 1 ;

			strncpy(field,startbuf, endbuf-startbuf);                     
			field[endbuf-startbuf]='\0';
			double sval = atof(field) ;	

			startbuf= ++endbuf ;
			while (*endbuf == ' ')
				*endbuf ++ ;

			// Status
			while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
				*endbuf ++ ;

			if (*endbuf != ' ' || endbuf - startbuf > MAX_STRING_LEN - 1)
				return 1 ;

			strncpy(field,startbuf, endbuf-startbuf);                     
			field[endbuf-startbuf]='\0';
			int status = atoi(field) ;	

			startbuf= ++endbuf ;
			while (*endbuf == ' ')
				*endbuf ++ ;

			// Prediction
			while ((*endbuf != '\n') && (*endbuf != '\r') && (*endbuf != ' '))
				*endbuf ++ ;

			if (((*endbuf != '\n') && (*endbuf != '\r')) || endbuf - startbuf > MAX_STRING_LEN - 1)
				return 1 ;

			strncpy(field,startbuf, endbuf-startbuf);                     
			field[endbuf-startbuf]='\0';
			int pred = atoi(field) ;	

			if (id != j+1)
				return 1 ;

			(*rf)[i][j].left = left ;
			(*rf)[i][j].right = right ;
			(*rf)[i][j].svar = svar ;
			(*rf)[i][j].sval = sval ;
			(*rf)[i][j].status = status ;
			(*rf)[i][j].pred = pred ;
		}
	}

	return 0 ;
}
