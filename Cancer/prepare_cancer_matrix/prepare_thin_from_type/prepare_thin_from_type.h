#include "prepare_from_type/params.h"
#include "prepare_from_type/prepare.h"

char thin_cbc_file[256] ;

// Initialize codes for blood counts and biochemistry tests.
int init_thin_codes() {

	cbc_codes[1]=	"RBC" ;
	cbc_codes[2]=	"WBC" ;
	cbc_codes[3]=	"MPV" ;
	cbc_codes[4]=	"Hemoglobin" ;
	cbc_codes[5]=	"Hematocrit" ;
	cbc_codes[6]=	"MCV" ;
	cbc_codes[7]=	"MCH" ;
	cbc_codes[8]=	"MCHC-M" ;
	cbc_codes[9]=	"RDW" ;
	cbc_codes[10]=	"Platelets" ;
	cbc_codes[11]=	"Eosinophils #" ;
	cbc_codes[12]=	"Neutrophils %" ;
	cbc_codes[19]=	"Lymphocytes %" ;
	cbc_codes[13]=	"Monocytes %" ;
	cbc_codes[14]=	"Eosinophils %" ;
	cbc_codes[15]=	"Basophils %" ;
	cbc_codes[16]=	"Neutrophils #" ;
	cbc_codes[20]=	"Lymphocytes #" ;
	cbc_codes[17]=	"Monocytes #" ;
	cbc_codes[18]=	"Basophils #" ;
	cbc_codes[21]=  "Albumin" ;
	cbc_codes[22]=  "Calcium" ;
	cbc_codes[23]=	"Cholesterol" ;
	cbc_codes[24]=	"Creatinine" ;
	cbc_codes[25]=	"HD" ;
	cbc_codes[26]=	"LD" ;
	cbc_codes[27]=	"Pottasium" ;
	cbc_codes[28]=	"Sodium" ;
	cbc_codes[29]=	"Triglycerides" ;
	cbc_codes[30]=	"Urea" ;
	cbc_codes[31]=	"Uric Acid" ;
	cbc_codes[32]=	"Chloride" ;
	cbc_codes[33]=	"Ferritin" ;

	for(int i=0; i<MAXCODE; i++)
		enumlist_val[i] = -1;
	
	int tests[] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33} ;
	int ntests = sizeof(tests)/sizeof(int) ;
	assert(ntests < MAXCOLS - 9) ;

	for (int i=0; i<ntests; i++) {
		assert(tests[i] < MAXCODE) ;
		enumlist_val[tests[i]] = enumlistcol;
			
		if (cbc_codes.find(tests[i]) != cbc_codes.end())
			sprintf(headers[enumlistcol],"%d [%s]", tests[i],cbc_codes[tests[i]].c_str());
		else {
			fprintf(stderr,"Cannot find cbc code %d\n",tests[i]) ;
			return -1 ;
		}

		enumlistcol++ ;
	}

	return 0 ;
}

// Read CBC files and create a matrix in 'lines' (patients x (blood-counts + biochem) )
int read_thin_file()
{
	sprintf(headers[0],"ID");
	sprintf(headers[1],"Date");
	sprintf(headers[2],"Born Date");
	sprintf(headers[3],"Current age");
	sprintf(headers[4],"Sex");
	sprintf(headers[5],"Macabi Status");
	sprintf(headers[6],"Macabi date");
	sprintf(headers[8],"Cacner date");
	sprintf(headers[7],"is cancer");
	
	char filename[256] ;
	strcpy(filename,thin_cbc_file) ;
 
	fprintf(stderr,"Reading: %s\n", filename);
	FILE *fin = fopen(filename, "rb");
	assert(fin != NULL) ;

	int id,code,date ;
	double value ;
	while(!(feof(fin))) {

		int rc = fscanf(fin,"%d %d %d %lf\n",&id,&code,&date,&value) ;
		if (rc == EOF)
			break ;

		if (rc != 4) {
			fprintf(stderr,"Problems parsing line in data file\n") ;
			return -1 ;
		}

		pair<int,int> index ;
		index.first = id ;
		index.second = date ;

		int iline ;
		if (line_no.find(index) != line_no.end())
			iline = line_no[index] ;
		else {
			iline = idnameptr;

			line_no[index] = iline ;
			line_nos[id].push_back(iline) ;

			lines[iline][0] = id;
			lines[iline][1] = date;
			idnameptr ++;

			if (idnameptr%10000==0) fprintf(stderr,"[%d]\n", idnameptr);
			 
		}

		// Go over enumerator
		if (enumlist_val[code] == -1) {
			fprintf(stderr,"Unknown test %d\n",code) ;
			return -1 ;
		}
//		if (lines[iline][enumlist_val[code]] != -1)
//			printf("Double %d @ %d,%d : %f vs %f\n",code,index.first,index.second,value,lines[iline][enumlist_val[code]]) ;

		lines[iline][enumlist_val[code]] = value;
	}

	fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);
	return 0 ;
	
}

// Read smoking indications from file and add three columns to the 'lines' matrix
void read_thin_smx() {

	map<int,vector< pair<int,int> > > smx ;
	int ids[3] = {0,1,2} ;

	// Read
	read_smx_file(thin_smx_file,ids,smx) ;

	// Fill
	fill_smx_values(smx) ;
}

void read_thin_qty_smx() {
	map<int, qty_smx_record> qty_smx;
	read_qty_smx_file(thin_qty_smx_file, qty_smx);
	fill_qty_smx_values(qty_smx);
}