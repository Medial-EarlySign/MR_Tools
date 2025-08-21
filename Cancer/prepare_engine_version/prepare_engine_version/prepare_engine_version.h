#include "stdlib.h"
#include "stdio.h"
#include "string.h"

#include <map>
#include <vector>
#include <string>
#include <assert.h>

#define NTESTS 20
#define MAX_STRING_LEN 256
#define MAX_BUF_SIZE 1024
#define NFILES 12 

using namespace std ;

class params {
public:
	double max,min ;
} ;

typedef struct {
	int left,right,status,svar,pred ;
	double sval ;
} node ;

typedef node *tree ;
typedef tree *forest ;

void read_params(string& fname, map<int,params>& parameters) ;
void copy(string& from, char *dir, char *to) ;
