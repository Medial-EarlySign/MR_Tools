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

int main(int argc, char *argv[]) {

	// Open input file
	assert(argc == 2) ;

	FILE *fin = fopen(argv[1],"rb") ;
	assert(fin!=NULL) ;

	int ntrees ;
	if (fread(&ntrees,sizeof(int),1,fin) != 1)
		return 1 ;

	int nnodes ;
	for (int i=0; i<ntrees; i++) {
		if (fread(&nnodes,sizeof(int),1,fin) != 1)
			return 1 ;

		tree tr = (tree) malloc(nnodes*sizeof(node)) ;
		if (tr == NULL)
			return 1 ;

		if (fread(tr,sizeof(node),nnodes,fin) != nnodes)
			return 1 ;

		for (int j=0; j<nnodes; j++) 
			printf("%d %d %d %d %d %d %d %f\n",i,j,tr[j].left,tr[j].right,tr[j].status,tr[j].pred,tr[j].svar,tr[j].sval) ;
	}

	return 0 ;
}

int read_forest(char *file_name, rf_forest *rf, int *ntrees) {

	FILE *fp = fopen(file_name,"rb") ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",file_name) ;
		return -1 ;
	}

	
	double rvalue ;
	int nrnodes ;

	if (fread(&rvalue,sizeof(double),1,fp)!=1) {
		fprintf(stderr,"Cannot read ntrees from %s\n",file_name) ;
		return -1 ;
	}
	(*ntrees) = (int) rvalue ;

	if (fread(&nrnodes,sizeof(int),1,fp)!=1)  {
		fprintf(stderr,"Cannot read nrnose from %s\n",file_name) ;
		return -1 ;
	}

	int size = (*ntrees)*nrnodes ;

	int *nnodes = (int *) malloc((*ntrees)*sizeof(int)) ;
	int *status = (int *) malloc(size*sizeof(int)) ;
	int *tree = (int *) malloc(2*size*sizeof(int)) ;
	int *pred = (int *) malloc(size*sizeof(int)) ;
	int *var = (int *) malloc(size*sizeof(int)) ;
	double *value = (double *) malloc(size*sizeof(double)) ;

	if (nnodes == NULL || status == NULL || tree == NULL || pred == NULL || var == NULL || value == NULL) {
		fprintf(stderr,"Allocation failed\n") ;
		return -1 ;
	}

	if (fread(nnodes,sizeof(int),*ntrees,fp)!=(*ntrees) || 
		fread(status,sizeof(int),size,fp)!= size ||
		fread(tree,sizeof(int),2*size,fp)!=2*size ||
		fread(pred,sizeof(int),size,fp)!=size ||
		fread(var,sizeof(int),size,fp)!=size ||
		fread(value,sizeof(double),size,fp)!=size) {
			fprintf(stderr,"Reading from %s failed\n",file_name) ;
			return -1 ;
	}
	fclose(fp) ;

	*rf = (rf_forest) malloc((*ntrees)*sizeof(rf_tree)) ;
	if ((*rf) == NULL) {
		fprintf(stderr,"Allocation of forest failed\n") ;
		return -1 ;
	}

	for (int i=0; i<*ntrees; i++) {

		(*rf)[i] = (rf_tree) malloc(nnodes[i]*sizeof(rf_node)) ;
		if ((*rf)[i] == NULL) {
			fprintf(stderr,"Allocation of tree %d failed\n") ;
			return -1 ;
		}

		for (int j=0; j<nnodes[i]; j++) {
			(*rf)[i][j].left = tree[2*nrnodes*i + j] ;
			(*rf)[i][j].right = tree[2*nrnodes*i + nrnodes + j] ;
			(*rf)[i][j].svar = var[nrnodes*i+j] ;
			(*rf)[i][j].sval = value[nrnodes*i+j] ;
			(*rf)[i][j].status = status[nrnodes*i+j] ;
			(*rf)[i][j].pred = pred[nrnodes*i+j] ;
		}
	}

	free(nnodes) ;
	free(tree) ;
	free(var) ;
	free(value) ;
	free(status) ;
	free(pred) ;

	return 0 ;
}