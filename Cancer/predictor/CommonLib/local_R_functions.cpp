// Functions for calling R functions (mainly RandomForest)
#define _CRT_SECURE_NO_WARNINGS

#include "localCommonLib.h"
#include "time.h"
//#define RF_NTREES 2500

int R_learn_classification_strat(double *tx, double *y, int nrows, int ncols, int nneg, int npos, char *ftree , int ntrees) {

	// Create Learner Scripts
	FILE *ofp = NULL;
	int ret = 0;

	if ((ofp = safe_fopen(LEARN_BATCH, "w", false)) == NULL) {
		fprintf( stderr,"error (%d) (%s) writing to file %s", errno, strerror(errno), LEARN_BATCH );
		return -1;
	}

	int int_size = sizeof(int) ;
	int dbl_size = sizeof(double) ;

	fprintf(ofp,"library(randomForest) ;\n") ;
	fprintf(ofp,"set.seed(%d) ;\n",RF_SEED) ;
	fprintf(ofp,"data.all <- read.table(\"%s\",header=T) ;\n",LRN_FILE) ;
	fprintf(ofp,"data <- subset(data.all , select = -Label) ;\n") ;
	fprintf(ofp,"labels <- data.all$Label ;\n") ;

	fprintf(ofp,"labels.factor <- as.factor(labels) ;\n") ;
	fprintf(ofp,"mdl <- randomForest(data,labels.factor,sampsize=c(%d,%d),ntree=%d)\n",nneg,npos,ntrees) ;
	fprintf(ofp,"size <- mdl$forest$ntree * mdl$forest$nrnodes ;\n") ;
	fprintf(ofp,"tot.size <- 2*%d + mdl$forest$ntree*%d + size*5*%d + size*%d;\n",int_size,int_size,int_size,dbl_size) ;
	fprintf(ofp,"con <- file(\"%s\",open=\"wb\") ;\n",ftree) ;
	fprintf(ofp,"writeBin(as.integer(tot.size),con) ;\n") ;
	fprintf(ofp,"writeBin(as.integer(mdl$forest$ntree),con) ;\n") ;
	fprintf(ofp,"writeBin(as.integer(mdl$forest$nrnodes),con) ;\n") ;
	fprintf(ofp,"writeBin(mdl$forest$ndbigtree,con) ;\n") ;
	fprintf(ofp,"writeBin(as.vector(mdl$forest$nodestatus),con) ;\n") ;
	fprintf(ofp,"writeBin(as.vector(mdl$forest$treemap),con) ;\n") ;
	fprintf(ofp,"writeBin(as.vector(mdl$forest$nodepred),con) ;\n") ;
	fprintf(ofp,"writeBin(as.vector(mdl$forest$bestvar),con) ;\n") ;
	fprintf(ofp,"writeBin(as.vector(mdl$forest$xbestsplit),con) ;\n") ;
	fprintf(ofp,"close(con) ;\n") ;

	fclose(ofp) ;

	// Print Data
	if (tprint_matrix(tx,y,nrows,ncols,LRN_FILE) == -1)
		return -1 ;

	time_t my_time;
	time(&my_time);

#ifdef _WIN32
        unsigned long id = GetCurrentProcessId();
#else
        unsigned long id = getpid();
#endif


	// Run script
	char cmd[MAX_STRING_LEN] ;
#ifdef _WIN32
	sprintf(cmd,"%s %s %s\\%s.%lld.%d",R_EXEC,LEARN_BATCH,STD_DIR,STD_FILE,my_time,id) ;
#else
	sprintf(cmd,"%s %s %s/%s.%d.%d",R_EXEC,LEARN_BATCH,STD_DIR,STD_FILE,my_time,id) ;
#endif
	if (system(cmd) != 0) {
		fprintf(stderr,"%s failed\n",cmd) ;
		return -1 ;
	}
	return 0 ;
}

int R_learn_classification_strat(double *tx, double *y, int nrows, int ncols, int nneg, int npos, int ntrees) {
	return R_learn_classification_strat(tx,y,nrows,ncols,nneg,npos,TREE_FILE,  ntrees ) ;
}
