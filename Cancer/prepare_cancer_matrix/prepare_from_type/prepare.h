#include "stdlib.h"
#include "stdio.h"
#include "string.h"
#include "math.h"
#include <assert.h>
#include <string>
#include <map>
#include <algorithm>
#include <iostream>
#include <vector>
#include <set>
#include <unordered_map>
using namespace std;

#define DAYS_TO_HEALING (999*365)

#define ID_COL 0 
       
#define MAXLINES 12000000
#define MAXCODE 100000
#define MAX_LOCAL_LINES 100000
#define MAXCOLS 60
#define NBMI_FTRS 2

double *lines_array;
double (*lines)[MAXCOLS]; // instead of lines[MAXLINES][MAXCOLS]
double local_lines[MAX_LOCAL_LINES][MAXCOLS];

map<int,string> cbc_codes ;
map<int,string> biochem_codes ;
map<int,int> biochem_synonims ;

struct qty_smx_record {
	int startYear; // -1 if never smoked
	int endYear;   // -1 if never smoked
	int avgCigPerDay; // during the smoking period
	int lastSmxStatus; // for an ever smoker, 0 or 1 if status at endYear is quit (0) or still smoking (1)
};

set<int> id_list ;
int use_id_list = 0 ;

map<pair<int, int>, int> line_no ;
map<int, vector<int> > line_nos ;

int gender = 0 ; /* 0 = Men. 1= Women. */

char filename[1024];
char buf[4096];
char *buf1[50];
 
char headers[1000][64];
int enumlist_val[MAXCODE];
int enumlistcol = 9;
 
int idnameptr = 0;

#define NSEVERITY 4
#define MAX_CODES 9
int colonoscopy[NSEVERITY][MAX_CODES] = {{ 9350,  100,43000,41000,40000,81400, 9450,32620,42100},
										 {82100,76800,72040,82630,82110,82611,82600,72400,   -1},
										 {72000,74008,73330,69700,   -1,   -1,   -1,   -1,   -1},
										 {81403,80103,   -1,   -1,   -1,   -1,   -1,   -1,   -1}} ;

int days2month[] = {0,31,59,90,120,151,181,212,243,273,304,334} ;

// Days from 01/01/1900
int get_days(int val) {
		
	int year = val/100/100 ;
	int month = (val/100)%100 ;
	int day = val%100 ;

	// Full years
	int days = 365 * (year-1900) ;
	days += (year-1897)/4 ;
	days -= (year-1801)/100 ;
	days += (year-1601)/400 ;

	// Full Months
	days += days2month[month-1] ;
	if (month>2 && (year%4)==0 && ((year%100)!=0 || (year%400)==0))
		days ++ ;
	days += (day-1) ;

	return days;
}
 
struct compare_reads {
    bool operator()(const pair<double,double>& left, const pair<double,double>& right) {
                return (left.first < right.first) ;
    }
} ;

struct compare_bmis {
    bool operator()(const pair<int,double>& left, const pair<int,double>& right) {
                return (left.first > right.first) ;
    }
} ;

// Initialize codes for blood counts and biochemistry tests.
int init_codes() {

	cbc_codes[5041]=	"RBC" ;
	cbc_codes[5048]=	"WBC" ;
	cbc_codes[50221]=	"MPV" ;
	cbc_codes[50223]=	"Hemoglobin" ;
	cbc_codes[50224]=	"Hematocrit" ;
	cbc_codes[50225]=	"MCV" ;
	cbc_codes[50226]=	"MCH" ;
	cbc_codes[50227]=	"MCHC-M" ;
	cbc_codes[50228]=	"RDW" ;
	cbc_codes[50229]=	"Platelets" ;
	cbc_codes[50230]=	"Eosinophils #" ;
	cbc_codes[50232]=	"Neutrophils %" ;
	cbc_codes[50233]=	"Lymphocytes %" ;
	cbc_codes[50234]=	"Monocytes %" ;
	cbc_codes[50235]=	"Eosinophils %" ;
	cbc_codes[50236]=	"Basophils %" ;
	cbc_codes[50237]=	"Neutrophils #" ;
	cbc_codes[50238]=	"Lymphocytes #" ;
	cbc_codes[50239]=	"Monocytes #" ;
	cbc_codes[50240]=	"Platelets Hematocrit" ;
	cbc_codes[50241]=	"Basophils #" ;

	biochem_synonims[2039] = 2040 ;
	biochem_synonims[2313] = 2310 ;
	biochem_synonims[2566] = 2565 ;
	biochem_synonims[4131] = 4132 ;
	biochem_synonims[4296] = 4295 ;
	biochem_synonims[4521] = 4520 ;

	biochem_codes[2040]=	"Albumin" ;              
	biochem_codes[2310]=	"Ca" ;             
	biochem_codes[2435]=	"Cl" ;       
	biochem_codes[2465]=	"Cholesterol" ;            
	biochem_codes[2565]=	"Creatinine" ;         
	biochem_codes[3718]=	"HD" ;         
	biochem_codes[3719]=	"LD" ; 
//	biochem_codes[4100]=	"Phosphor" ; 
	biochem_codes[4132]=	"K+" ;      
	biochem_codes[4295]=	"Na" ;           
	biochem_codes[4478]=	"Triglycerides" ;            
	biochem_codes[4520]=	"Urea" ;                    
	biochem_codes[4550]=	"Uric Acid" ;   
	biochem_codes[2728]=    "Ferritin" ;

	for(int i=0; i<MAXCODE; i++)
		enumlist_val[i] = -1;
	
	int tests[] = {5041,5048,50221,50223,50224,50225,50226,50227,50228,50229,50230,50232,50234,50235,50236,50237,50239,50241,50233,50238,
		2040,2310,2465,2565,3718,3719,4132,4295,4478,4520,4550,2435,2728} ;
	int ntests = sizeof(tests)/sizeof(int) ;
	assert(ntests < MAXCOLS - 9) ;

	for (int i=0; i<ntests; i++) {
		assert(tests[i] < MAXCODE) ;
		enumlist_val[tests[i]] = enumlistcol;
			
		if (cbc_codes.find(tests[i]) != cbc_codes.end())
			sprintf(headers[enumlistcol],"%d [%s]", tests[i],cbc_codes[tests[i]].c_str());
		else if (biochem_codes.find(tests[i]) != biochem_codes.end())
			sprintf(headers[enumlistcol],"%d [%s]", tests[i],biochem_codes[tests[i]].c_str());
		else {
			fprintf(stderr,"Cannot find cbc code %d\n",tests[i]) ;
			return -1 ;
		}

		enumlistcol++ ;
	}

	return 0 ;
}

// Read CBC files and create a matrix in 'lines' (patients x blood-counts)
int readfile(int type)
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
	
	int nfiles = file_nos[type] ;
	int validation = (type == 3) ? 1 : 0 ;

	for(int fileno=0; fileno<nfiles; fileno++)
	{
		if (gender==0) {
			if (validation)
				sprintf(filename, "%s",  men_validation_labfiles[fileno]);
			else
				sprintf(filename, "%s",  men_labfiles[fileno]);
		} else {
			if (validation)
				sprintf(filename, "%s",  women_validation_labfiles[fileno]);
			else
				sprintf(filename, "%s",  women_labfiles[fileno]);
		}
 
		fprintf(stderr,"Reading: %s\n", filename);
		FILE *fin = fopen(filename, "rb");
		assert(fin != NULL) ;

		{
			char *ptr;
			while(!(feof(fin)))
			{
				 
				char *usebuf = buf;
				fgets(usebuf, 4096, fin);
				int l=0;
				do 
				{
					
					ptr = strpbrk(usebuf,"\t");
					buf1[l] = usebuf;
					if (ptr!=NULL) 
					 buf1[l][(int)(ptr-usebuf)]='\0';
					 
					l++;
					if (ptr==NULL) break;
					usebuf = ptr+1;
				} while (usebuf!=NULL);

				int idnum = atoi(buf1[0])+atoi(buf1[1])*1000000;
				int labenum = atoi(buf1[2]);

				double labval  = atof(buf1[7]);
				int date = atoi(buf1[3]);

				pair<int,int> index ;
				index.first = idnum ;
				index.second = date ;

				int iline ;
				if (line_no.find(index) != line_no.end())
					iline = line_no[index] ;
				else {
					iline = idnameptr;

					line_no[index] = iline ;
					line_nos[idnum].push_back(iline) ;

					lines[iline][0] = idnum;
					lines[iline][1] = date;

					idnameptr ++;

					if (idnameptr%10000==0) fprintf(stderr,"[%d]\n", idnameptr);
					 
				}

				// Go over enumerator
				if (enumlist_val[labenum] == -1) {
					fprintf(stderr,"Unknonwn test %d\n",labenum) ;
					return -1 ;
				}

//				if (lines[iline][enumlist_val[labenum]] != -1)
//					printf("Double %d @ %d,%d : %f vs %f\n",labenum,index.first,index.second,labval,lines[iline][enumlist_val[labenum]]) ;

				lines[iline][enumlist_val[labenum]] = labval;
			}
		}
		fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);
	}

	// Additional files for lymphocytes

	for(int fileno=0; fileno<nfiles; fileno++)
	{
		if (gender==0) {
			if (validation)
				sprintf(filename, "%s",  men_validation_extra_labfiles[fileno]);
			else
				sprintf(filename, "%s",  men_extra_labfiles[fileno]);
		} else {
			if (validation)
				sprintf(filename, "%s",  women_validation_extra_labfiles[fileno]);
			else
				sprintf(filename, "%s",  women_extra_labfiles[fileno]);
		}

		fprintf(stderr,"Reading: %s\n", filename);
		FILE *fin = fopen(filename, "rb");
		assert(fin != NULL) ;

		{
			char *ptr;
			while(!(feof(fin)))
			{
				 
				char *usebuf = buf;
				fgets(usebuf, 4096, fin);
				int l=0;
				do 
				{
					
					ptr = strpbrk(usebuf,"\t");
					buf1[l] = usebuf;
					if (ptr!=NULL) 
					 buf1[l][(int)(ptr-usebuf)]='\0';
					 
					l++;
					if (ptr==NULL) break;
					usebuf = ptr+1;
				} while (usebuf!=NULL);

				int idnum = atoi(buf1[0]);
				int labenum = atoi(buf1[1]);

				double labval  = atof(buf1[3]);
				int date = atoi(buf1[2]);

				pair<int,int> index ;
				index.first = idnum ;
				index.second = date ;

				int iline ;
				if (line_no.find(index) != line_no.end())
					iline = line_no[index] ;
				else {
					iline = idnameptr;

					line_no[index] = iline ;
					line_nos[idnum].push_back(iline) ;

					lines[iline][0] = idnum;
					lines[iline][1] = date;

					idnameptr ++;

					if (idnameptr%10000==0) fprintf(stderr,"[%d]\n", idnameptr);
					 
				}

				// Go over enumerator
				if (enumlist_val[labenum] != -1)
					lines[iline][enumlist_val[labenum]] = labval;
			}
		}
		fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);
	}

	return 0 ;

	
}

int readfile(map<int,int>& ids_list,int type)
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
	
	int nfiles = file_nos[type] ;
	int validation = (type == 3) ? 1 : 0 ;

	for(int fileno=0; fileno<nfiles; fileno++)
	{
		if (gender==0) {
			if (validation)
				sprintf(filename, "%s",  men_validation_labfiles[fileno]);
			else
				sprintf(filename, "%s",  men_labfiles[fileno]);
		} else {
			if (validation)
				sprintf(filename, "%s",  women_validation_labfiles[fileno]);
			else
				sprintf(filename, "%s",  women_labfiles[fileno]);
		}
 
		fprintf(stderr,"Reading: %s\n", filename);
		FILE *fin = fopen(filename, "rb");
		assert(fin != NULL) ;

		{
			char *ptr;
			while(!(feof(fin)))
			{
				 
				char *usebuf = buf;
				fgets(usebuf, 4096, fin);
				int l=0;
				do 
				{
					
					ptr = strpbrk(usebuf,"\t");
					buf1[l] = usebuf;
					if (ptr!=NULL) 
					 buf1[l][(int)(ptr-usebuf)]='\0';
					 
					l++;
					if (ptr==NULL) break;
					usebuf = ptr+1;
				} while (usebuf!=NULL);

				int idnum = atoi(buf1[0])+atoi(buf1[1])*1000000;
				if (ids_list.find(idnum) == ids_list.end())
					continue ;

				int labenum = atoi(buf1[2]);

				double labval  = atof(buf1[7]);
				int date = atoi(buf1[3]);

				pair<int,int> index ;
				index.first = idnum ;
				index.second = date ;

				int iline ;
				if (line_no.find(index) != line_no.end())
					iline = line_no[index] ;
				else {
					iline = idnameptr;

					line_no[index] = iline ;
					line_nos[idnum].push_back(iline) ;

					lines[iline][0] = idnum;
					lines[iline][1] = date;

					idnameptr ++;

					if (idnameptr%10000==0) fprintf(stderr,"[%d]\n", idnameptr);
					 
				}

				// Go over enumerator
				if (enumlist_val[labenum] == -1) {
					fprintf(stderr,"Unknonwn test %d\n",labenum) ;
					return -1 ;
				}

//				if (lines[iline][enumlist_val[labenum]] != -1)
//					printf("Double %d @ %d,%d : %f vs %f\n",labenum,index.first,index.second,labval,lines[iline][enumlist_val[labenum]]) ;

				lines[iline][enumlist_val[labenum]] = labval;
			}
		}
		fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);
	}

	// Additional files for lymphocytes

	for(int fileno=0; fileno<nfiles; fileno++)
	{
		if (gender==0) {
			if (validation)
				sprintf(filename, "%s",  men_validation_extra_labfiles[fileno]);
			else
				sprintf(filename, "%s",  men_extra_labfiles[fileno]);
		} else {
			if (validation)
				sprintf(filename, "%s",  women_validation_extra_labfiles[fileno]);
			else
				sprintf(filename, "%s",  women_extra_labfiles[fileno]);
		}

		fprintf(stderr,"Reading: %s\n", filename);
		FILE *fin = fopen(filename, "rb");
		assert(fin != NULL) ;

		{
			char *ptr;
			while(!(feof(fin)))
			{
				 
				char *usebuf = buf;
				fgets(usebuf, 4096, fin);
				int l=0;
				do 
				{
					
					ptr = strpbrk(usebuf,"\t");
					buf1[l] = usebuf;
					if (ptr!=NULL) 
					 buf1[l][(int)(ptr-usebuf)]='\0';
					 
					l++;
					if (ptr==NULL) break;
					usebuf = ptr+1;
				} while (usebuf!=NULL);

				int idnum = atoi(buf1[0]);
				if (ids_list.find(idnum) == ids_list.end())
					continue ;

				int labenum = atoi(buf1[1]);

				double labval  = atof(buf1[3]);
				int date = atoi(buf1[2]);

				pair<int,int> index ;
				index.first = idnum ;
				index.second = date ;

				int iline ;
				if (line_no.find(index) != line_no.end())
					iline = line_no[index] ;
				else {
					iline = idnameptr;

					line_no[index] = iline ;
					line_nos[idnum].push_back(iline) ;

					lines[iline][0] = idnum;
					lines[iline][1] = date;

					idnameptr ++;

					if (idnameptr%10000==0) fprintf(stderr,"[%d]\n", idnameptr);
					 
				}

				// Go over enumerator
				if (enumlist_val[labenum] != -1)
					lines[iline][enumlist_val[labenum]] = labval;
			}
		}
		fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);
	}

	return 0 ;
}

// Print the 'lines' matrix into a file
void writefile()
{

	FILE *fout ;
	fout = fopen("matrix.bin", "wb");
	assert(fout != NULL) ;

	fwrite(&idnameptr, 1, sizeof(idnameptr), fout);
	fwrite(lines, idnameptr, sizeof(lines[0]), fout);
	// fwrite(lines.data(), idnameptr, sizeof(lines[0]), fout);
	fclose(fout);


	fout =fopen( "matrix.txt", "w");
	assert(fout != NULL) ;

	for(int i =0; i<enumlistcol-1; i++)
		fprintf(fout,"%s\t", headers[i]);
	fprintf(fout,"%s\n",headers[enumlistcol-1]) ;
	

	for(int i=0; i<idnameptr; i++) {
		for(int j=0; j<enumlistcol-1; j++)
			fprintf(fout,"%f\t", lines[i][j]);
		fprintf(fout,"%f\n",lines[i][enumlistcol-1]) ;
	}

	fclose(fout);
}


// Read colorectal cancer registery and enter into lines[ipatient][7] (1/0 flag) and lines[ipatient][8] (registery date)
void readrasham() {
	FILE *fin ;
	if (gender == 0)
		fin = fopen("\\\\server\\data\\macabi4\\training.men.crc_registry.excluding2010.2011_updated1.csv", "rb");
	else
		fin = fopen("\\\\server\\data\\macabi4\\training.women.crc_registry.excluding2010.2011.csv", "rb");
	
	assert(fin != NULL) ;

	int tot_crc = 0 ;

	int lineno=0;
	char *ptr;
	while(!(feof(fin)))
	{

	 
		char *usebuf = buf;
		fgets(usebuf, 4096, fin);
		lineno++;
		 
		if (lineno%10000==0) printf("CRC: <%d>\n", lineno);
		int l=0;
		do 
		{
			
			ptr = strpbrk(usebuf,",");
			buf1[l] = usebuf;
			if (ptr!=NULL) 
			 buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			if (ptr==NULL) break;
			usebuf = ptr+1;
			 
		} while (usebuf!=NULL);

		if (strcmp(buf1[2],"NO_CRC")!=0)
			tot_crc++ ;

		int idnum = atoi(buf1[0])/*+atoi(buf1[1])*1000000*/;

		if (line_nos.find(idnum) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[idnum].size(); i++) {
				int iline = line_nos[idnum][i] ;

				if (strcmp(buf1[2],"NO_CRC")!=0) {
					lines[iline][7]=1;


					int year=0;
					int month=0;
					int day =0;

					int chplace =0;
					sscanf(&buf1[3][chplace],"%d", &month);
					
					while(buf1[3][chplace]!='/') chplace++;
					chplace++;
				
					sscanf(&buf1[3][chplace],"%d", &day);
					while(buf1[3][chplace]!='/') chplace++;
					chplace++;
					sscanf(&buf1[3][chplace],"%d", &year);
					//printf("  %d %d %d\n", day,month,year);


					lines[iline][8]=year*100*100+month*100+day;
					 
				} else
					lines[iline][7] = 0;
			}
		}

	}

	fprintf(stderr,"TOT-CRC = %d\n",tot_crc) ;
}



// Read a vector of BMI reads (bmis) and a given date (lines[iline][1]) and get the latest relevant BMI read (and the time-difference) ;
void get_bmi_values(int iline, vector<pair<int, double> >& bmis, double *ftrs) {

	int test_day = get_days((int) lines[iline][1]) ;

	for (int i=0; i<NBMI_FTRS; i++)
		ftrs[i] = -1.0 ;

	sort(bmis.begin(),bmis.end(),compare_bmis()) ;

	// Handle same-day info
	vector<pair<int, double> > processed ;
	double sum = 0; 
	int num = 0 ;
	for (unsigned int i=0; i<bmis.size(); i++) {
		if (i>0 && bmis[i].first != bmis[i-1].first) {
			pair<int,double> new_pair(bmis[i-1].first,sum/num) ;
			processed.push_back(new_pair) ;
			sum = 0 ;
			num = 0 ;
		}
		sum += bmis[i].second ;
		num ++ ;
	}

	pair<int,double> new_pair(bmis[bmis.size()-1].first,sum/num) ;
	processed.push_back(new_pair) ;

	// Take Features
	for (unsigned int i=0; i<processed.size(); i++) {
		int bmi_day = get_days(processed[i].first) ;
		if (bmi_day < test_day) {
			ftrs[0] = test_day - bmi_day ;
			ftrs[1] = processed[i].second ;

//			if (i<processed.size() - 1) {
//				int time_diff = bmi_day - get_days(processed[i+1].first) ;
//				ftrs[2] = (processed[i].second - processed[i+1].second)/time_diff ;
//				ftrs[3] = time_diff ;
//			}

			break ;
		}
	}

	return ;
}

// Read BMI values from file, create a vector and extract a relevant-value + time diff for each line in the 'lines' matrix
void fill_bmi_values( map<int,vector< pair<int,double> > >& bmis) {

	double ftr_vals[NBMI_FTRS] ;
	for (map<int,vector< pair<int,double> > >::iterator it= bmis.begin(); it!= bmis.end(); it++) {

		int idnum = it->first ;

		for (unsigned int i = 0 ; i < line_nos[idnum].size(); i++) {
			int iline = line_nos[idnum][i] ;
			get_bmi_values(iline,it->second,ftr_vals) ;
			for (int j=0; j<NBMI_FTRS; j++)
				lines[iline][enumlistcol+j] = ftr_vals[j] ;
		}
	}

	sprintf(headers[enumlistcol],"BMI Value") ;
	sprintf(headers[enumlistcol+1],"BMI Time") ;
//	sprintf(headers[enumlistcol+2],"BMI Gradient") ;
//	sprintf(headers[enumlistcol+3],"BMI TimeDiff") ;
	enumlistcol+=NBMI_FTRS ;

	fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);
}


void read_bmi_file(char *file_name, int *ids, map<int,vector< pair<int,double> > >& bmis) {

	printf("Reading BMI file %s\n",file_name) ;
	FILE *fin = fopen(file_name, "rb");
	
	assert(fin != NULL) ;

	int lineno=0;
	char *ptr;
	int header = 1 ;
	while(!(feof(fin))) {

		char *usebuf = buf;
		fgets(usebuf, 4096, fin);

		if (header) {
			header=0; 
			continue ;
		}

		lineno++;
		int l=0;
		do {
			
			ptr = strpbrk(usebuf,",");
			buf1[l] = usebuf;
			if (ptr!=NULL) 
				buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			if (ptr==NULL) break;
			usebuf = ptr+1;
		
		} while (usebuf!=NULL);

		int idnum = atoi(buf1[ids[0]])/*+atoi(buf1[1])*1000000*/;

		int year=0;
		int month=0;
		int day =0;

		int chplace =0;
		sscanf(&buf1[ids[1]][chplace],"%d", &day);
			
		while(buf1[ids[1]][chplace]!='/') chplace++;
		chplace++;

		sscanf(&buf1[ids[1]][chplace],"%d", &month);
		while(buf1[ids[1]][chplace]!='/') chplace++;
		chplace++;

		sscanf(&buf1[ids[1]][chplace],"%d", &year);

		int date = year*100*100+month*100+day ;

		double bmi = atof(buf1[ids[2]]);

		if (line_nos.find(idnum) != line_nos.end()) {
			pair<int, double> single_bmi (date,bmi) ;
			bmis[idnum].push_back(single_bmi) ;
		}
	}
	fclose(fin) ;

	return ;
}

void readBMI() {

	int fileno ;
	if (gender == 0)
		fileno = MEN_BMI_FILENO ;
	else
		fileno = WOMEN_BMI_FILENO ;

	map<int,vector< pair<int,double> > > bmis ;
	int ids[3] = {0,2,3} ;
	// Read
	for (int ifile=0; ifile<fileno; ifile++)
		read_bmi_file(bmifiles[gender][ifile],ids,bmis) ;

	// Fill
	fill_bmi_values(bmis) ;

	return ;
}

void readvalidationBMI() {

	map<int,vector< pair<int,double> > > bmis ;
	int ids[3] = {0,1,2} ;

	// Read
	read_bmi_file(validation_bmifiles[gender],ids,bmis) ;

	// Fill
	fill_bmi_values(bmis) ;

	return ;
}

// Get a vector of smoking indications and extract the value+time-diff relevant to iline :
// Value = 3 : Never Indicated as smoking. 2 : Indicated as smoking but last indication is not smoking. 1 : Last indication is smoking
// Time1 = Time since last indication
// Time2 = Time since last indication as smoking (20 years if never indicated as smoking, +5 years if only indication is as quit-smoking)
void get_smx_values(int iline, vector<pair<int, int> >& smx, double *value, double *time1, double *time2) {

	int test_day = get_days((int) lines[iline][1]) ;
	// fprintf(stderr, "get_smx_values: work on %d@%d\n", (int) lines[iline][0], (int) lines[iline][1]);

	*time1 = *time2 = *value = -1.0 ;

	for (unsigned int i=0; i<smx.size(); i++) {
		if (smx[i].first > test_day)
			break ;

		int code = smx[i].second ;
		if (code >= 1 && code <= 3)
			*time1 = test_day - smx[i].first ;

		if (code == 1) {
			*value = 1 ;
			*time2 = test_day - smx[i].first ;
		} else if (code == 2) {
			*value = 2 ;
			if (*time2 == -1.0)
				*time2 = (test_day - smx[i].first) + 5*365 ; // If no other information is available, we assume quitting 5 years ago ...
		} else if (code == 3) {
			if (*value == -1 || *value == 3)
				*value = 3 ;
			else
				*value = 2 ; // If never-smoking is indicated, but smoking was indicated before, we assume quitting.
		}
	}

	if (*value == 3)
		*time2 = 20*365 ;

	return ;
}

// get the patient quantitative smoking record and adjust the patient lines
void get_qty_smx_values(int iline, qty_smx_record& rec, double *pack_years, double *ysq) {

	int test_year = (int) lines[iline][1] / 10000 ;
	int test_age = test_year - (int) lines[iline][2] / 10000 ;

	*pack_years = *ysq = -1.0 ;

	if (rec.startYear == -1) { // never smoked
		*pack_years = 0;
		*ysq = max(test_age - 20, 0);
		return ;
	}

	*pack_years = max(test_year - rec.startYear, 0) * rec.avgCigPerDay / 20;
	if (rec.lastSmxStatus == 1) { // no indication of quitting
		*ysq = 0;
	}
	else {
		*ysq = max(test_year - rec.endYear, 0);
	}

	return ;
}

// Read smoking indications from file and add three columns to the 'lines' matrix
void read_smx_file(char *file_name, int *ids, map<int,vector< pair<int,int> > >& smx) {
	
	fprintf(stderr,"Reading SMX file %s\n",file_name) ;
	FILE *fin = fopen(file_name, "rb");
	
	assert(fin != NULL) ;

	int lineno=0;
	char *ptr;
	int header = 1 ;
	while(!(feof(fin))) {

		char *usebuf = buf;
		fgets(usebuf, 4096, fin);

		if (header) {
			header=0; 
			continue ;
		}

		lineno++;
		 
//			if (lineno%10000==0) fprintf(stderr,"SMX: <%d>\n", lineno);
		int l=0;
		do {
			
			ptr = strpbrk(usebuf,",");
			buf1[l] = usebuf;
			if (ptr!=NULL) 
				buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			if (ptr==NULL) break;
			usebuf = ptr+1;
		
		} while (usebuf!=NULL);

		int idnum = atoi(buf1[ids[0]])/*+atoi(buf1[1])*1000000*/;

		int year=0;
		int month=0;
		int day =0;

		int chplace =0;
		sscanf(&buf1[ids[1]][chplace],"%d", &day);
			
		while(buf1[ids[1]][chplace]!='/') chplace++;
		chplace++;

		sscanf(&buf1[ids[1]][chplace],"%d", &month);
		while(buf1[ids[1]][chplace]!='/') chplace++;
		chplace++;

		sscanf(&buf1[ids[1]][chplace],"%d", &year);

		int date = year*100*100+month*100+day ;

		int code = atoi(buf1[ids[2]]);

		if (line_nos.find(idnum) != line_nos.end()) {
			pair<int, int> single_smx (get_days(date),code) ;
			smx[idnum].push_back(single_smx) ;

		}
	}

	fclose(fin) ;
	return ;
}

void fill_smx_values(map<int,vector< pair<int,int> > >& smx) {
	
	for (map<int,vector< pair<int,int> > >::iterator it= smx.begin(); it!= smx.end(); it++) {

		int idnum = it->first ;
		sort(it->second.begin(),it->second.end(),compare_reads()) ;

		double val1,val2,val3;
		for (unsigned int i = 0 ; i < line_nos[idnum].size(); i++) {
			int iline = line_nos[idnum][i] ;
			get_smx_values(iline,it->second,&val1,&val2,&val3) ;
			lines[iline][enumlistcol] = val1 ;
			lines[iline][enumlistcol+1] = val2 ;
			lines[iline][enumlistcol+2] = val3 ;
		}
	}

	sprintf(headers[enumlistcol],"SMX Value") ;
	sprintf(headers[enumlistcol+1],"SMX Time1") ;
	sprintf(headers[enumlistcol+2],"SMX Time2") ;
	enumlistcol+=3 ;

	fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);

	return ;
}

// Read quantitative smoking information from file and add two columns to the 'lines' matrix:
// 1) cumulative pack years at time of test
// 2) time in years since quitting (0 if currently smoking, (age - 20) if never smoked
void read_qty_smx_file(char *file_name, map<int, qty_smx_record>& qty_smx) {
	
	fprintf(stderr,"Reading Qty SMX file %s\n", file_name) ;
	FILE *fin = fopen(file_name, "r");
	
	assert(fin != NULL) ;
	
	int idnum;
	qty_smx_record rec;
	int lineno=0;
	int rc;

	while ((rc = fscanf(fin, "%d\t%d\t%d\t%d\t%d\n", &idnum, &rec.startYear, &rec.endYear, &rec.avgCigPerDay, &rec.lastSmxStatus)) != EOF) {
		assert(rc == 5);
		lineno++;
		if (lineno % 10000 == 0) fprintf(stderr,"SMX record #%d: %d\t%d\t%d\t%d\t%d\n", lineno, idnum, rec.startYear, rec.endYear, rec.avgCigPerDay, rec.lastSmxStatus);

		if (line_nos.find(idnum) != line_nos.end()) {
			qty_smx[idnum] = rec;
		}
	}
	fprintf(stderr, "%d Qty SMX records were read\n", lineno); 

	fclose(fin) ;
	return ;
}

void fill_qty_smx_values(map<int, qty_smx_record>& qty_smx) {
	
	for (auto it= qty_smx.begin(); it!= qty_smx.end(); it++) {

		int idnum = it->first ;

		double val1, val2 ;
		for (unsigned int i = 0 ; i < line_nos[idnum].size(); i++) {
			int iline = line_nos[idnum][i] ;
			get_qty_smx_values(iline, it->second, &val1, &val2) ;
			lines[iline][enumlistcol] = val1 ;
			lines[iline][enumlistcol+1] = val2 ;
		}
	}

	sprintf(headers[enumlistcol],"SMX Pack Years") ;
	sprintf(headers[enumlistcol+1],"SMX YsQ") ; // number of Years since Quitting
	enumlistcol+=2 ;

	fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);

	return ;
}

void readsmx() {

	int fileno ;
	if (gender == 0)
		fileno = MEN_SMX_FILENO ;
	else  
		fileno = WOMEN_SMX_FILENO ;

	map<int,vector< pair<int,int> > > smx ;
	int ids[3] = {0,2,3} ;

	// Read
	for (int ifile=0; ifile<fileno; ifile++)
		read_smx_file(smxfiles[gender][ifile],ids,smx) ;

	// Fill
	fill_smx_values(smx) ;

	return ;
}

void readvalidationsmx() {

	map<int,vector< pair<int,int> > > smx ;
	int ids[3] = {0,1,2} ;

	// Read
	read_smx_file(validation_smxfiles[gender],ids,smx) ;

	// Fill
	fill_smx_values(smx) ;

	return ;
}

// Read biochemistry tests data and add to the 'lines' matrix. If take_new = 0, only patients with blood counts are considered,
// otherwise, new lines are added for missing patient.

int readallbiochem(int type, int take_new)
{

	FILE *fin ;
	int nfiles = file_nos[type] ;

	int lineno=0;
	char *ptr;
	
	for (int ifile = 0; ifile < nfiles; ifile++) {
		fin = fopen(biochem_files[ifile],"r") ;
		assert(fin != NULL) ;
		fprintf(stderr,"Reading %s\n",biochem_files[ifile]) ;

		while(!(feof(fin))) {	 
			char *usebuf = buf;
			if (fgets(usebuf, 4096, fin) == NULL)
				break ;
			lineno++;
		 
//			if (lineno%50000==0) fprintf(stderr,"BioChem: <%d>\n", lineno);
			int l=0;
			
			do {			
				ptr = strpbrk(usebuf,"\t");
				buf1[l] = usebuf;
				if (ptr!=NULL) 
					buf1[l][(int)(ptr-usebuf)]='\0';
			 
				l++;
				if (ptr==NULL) break;
				usebuf = ptr+1;
			 
			} while (usebuf!=NULL);

			ptr=strpbrk(usebuf,"\n");
			assert(ptr != NULL) ;
			buf1[l-1][(int)(ptr-usebuf)] = '\0';

			int idnum = atoi(buf1[2]) ;
			int date = atoi(buf1[6]);
			int labenum = atoi(buf1[7]);
			double labval  = atof(buf1[8]);

			pair<int,int> index ;
			index.first = idnum ;
			index.second = date ;

			int iline ;
			if (line_no.find(index) != line_no.end())
				iline = line_no[index] ;
			else if (take_new || line_nos.find(idnum) != line_nos.end()) {
				iline = idnameptr;

				line_no[index] = iline ;
				line_nos[idnum].push_back(iline) ;

				lines[iline][0] = idnum;
				lines[iline][1] = date;

				idnameptr ++;

				if (idnameptr%10000==0) printf("[%d]\n", idnameptr);
				 
			} else
				continue ;

			// Go over enumerator

			if (biochem_synonims.find(labenum) != biochem_synonims.end())
				labenum = biochem_synonims[labenum] ;

			if (enumlist_val[labenum] == -1) {
				fprintf(stderr,"Unknonwn test %d\n",labenum) ;
				return -1 ;
			}
			lines[iline][enumlist_val[labenum]] = labval;
		}
	}

// Ferritin

	for (int ifile = 0; ifile < nfiles; ifile++) {
		fin = fopen(ferritin_files[ifile],"r") ;
		assert(fin != NULL) ;
		fprintf(stderr,"Reading %s\n",ferritin_files[ifile]) ;

		while(!(feof(fin))) {	 
			char *usebuf = buf;
			if (fgets(usebuf, 4096, fin) == NULL)
				break ;
			lineno++;
		 
			int l=0;
			
			do {			
				ptr = strpbrk(usebuf,"\t");
				buf1[l] = usebuf;
				if (ptr!=NULL) 
					buf1[l][(int)(ptr-usebuf)]='\0';
			 
				l++;
				if (ptr==NULL) break;
				usebuf = ptr+1;
			 
			} while (usebuf!=NULL);

			ptr=strpbrk(usebuf,"\n");
			assert(ptr != NULL) ;
			buf1[l-1][(int)(ptr-usebuf)] = '\0';

			int idnum = atoi(buf1[0]) ;
			int date = atoi(buf1[1]);
			double labval  = atof(buf1[2]);

			pair<int,int> index ;
			index.first = idnum ;
			index.second = date ;

			int iline ;
			if (line_no.find(index) != line_no.end())
				iline = line_no[index] ;
			else if (take_new || line_nos.find(idnum) != line_nos.end()) {
				iline = idnameptr;

				line_no[index] = iline ;
				line_nos[idnum].push_back(iline) ;

				lines[iline][0] = idnum;
				lines[iline][1] = date;

				idnameptr ++;

				if (idnameptr%10000==0) printf("[%d]\n", idnameptr);
				 
			} else
				continue ;

			// Go over enumerator
			lines[iline][enumlist_val[2728]] = labval;
		}
	}
	fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);


	return 0;
}

// Read cancer registery and updates lines[i][7] and lines[i][8] : cancer but not CRC , or cancer BEFORE CRC => 3,cancer-date
void readfullrasham()
{
	FILE *fin = fopen("\\\\server\\data\\macabi4\\training_all_types_cancer_excluding_20102011.csv", "rb");
	assert(fin != NULL) ;

	int tot_cancer = 0 ;
	int tot_crc = 0 ;
	int tot_before_crc = 0 ;

	int lineno=0;
	char *ptr;
	while(!(feof(fin))) {

	 	char *usebuf = buf;
		fgets(usebuf, 4096, fin);
		lineno++;
		 
		if (lineno%10000==0) printf("FULL: <%d>\n", lineno);
		int l=0;
		do {			
			ptr = strpbrk(usebuf,",");
			buf1[l] = usebuf;
			if (ptr!=NULL) 
				buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			if (ptr==NULL) 
				break;
			usebuf = ptr+1;
			 
		} while (usebuf!=NULL);

		tot_cancer++ ;
		int idnum = atoi(buf1[0]);
	
		if (line_nos.find(idnum) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[idnum].size(); i++) {
				int iline = line_nos[idnum][i] ;

				int year=0;
				int month=0;
				int day =0;

				int chplace =0;
				sscanf(&buf1[1][chplace],"%d", &month);
				
				while(buf1[1][chplace]!='/') chplace++;
				chplace++;

				sscanf(&buf1[1][chplace],"%d", &day);
				while(buf1[1][chplace]!='/') chplace++;
				chplace++;

				sscanf(&buf1[1][chplace],"%d", &year);

				int date = year*100*100+month*100+day ;
				if (lines[iline][7] == 0) {
					lines[iline][7] = 3 ;
					lines[iline][8] = date ;
				} else if (lines[iline][7] == 1 && lines[iline][8] == date) {
					tot_crc ++ ;
				} else if (lines[iline][7] == 1 && lines[iline][8] > date) {
					lines[iline][7] = 3 ;
					lines[iline][8] = date ;
					tot_before_crc ++ ;
				}
			}
		}
	}

	fprintf(stderr,"Full Reg.: TOT-CANCER = %d\n",tot_cancer) ;
	fprintf(stderr,"Full Reg.: TOT-CRC = %d\n",tot_crc) ;
	fprintf(stderr,"Full Reg.: TOT-BEFORE-CRC = %d\n",tot_before_crc) ;
}

// Read cancer registery and create a flag+date, ignoring the CRC regisetry (not looking at current value of lines[i][7,8])
void readonlyfullrasham()
{
	FILE *fin = fopen("\\\\server\\data\\macabi4\\training_all_types_cancer_excluding_20102011.csv", "rb");
	assert(fin != NULL) ;

	for (int i=0; i<idnameptr; i++) {
		lines[i][7] = 0 ;
		lines[i][8] = -1 ;
	}

	int tot_cancer = 0 ;

	int lineno=0;
	char *ptr;
	while(!(feof(fin))) {

	 	char *usebuf = buf;
		fgets(usebuf, 4096, fin);
		lineno++;
		 
		if (lineno%10000==0) printf("FULL: <%d>\n", lineno);
		int l=0;
		do {			
			ptr = strpbrk(usebuf,",");
			buf1[l] = usebuf;
			if (ptr!=NULL) 
				buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			if (ptr==NULL) 
				break;
			usebuf = ptr+1;
			 
		} while (usebuf!=NULL);

		int idnum = atoi(buf1[0]);
	
		if (line_nos.find(idnum) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[idnum].size(); i++) {
				int iline = line_nos[idnum][i] ;

				int year=0;
				int month=0;
				int day =0;

				int chplace =0;
				sscanf(&buf1[1][chplace],"%d", &month);
				
				while(buf1[1][chplace]!='/') chplace++;
				chplace++;

				sscanf(&buf1[1][chplace],"%d", &day);
				while(buf1[1][chplace]!='/') chplace++;
				chplace++;

				sscanf(&buf1[1][chplace],"%d", &year);

				int date = year*100*100+month*100+day ;
				lines[iline][7] = 1 ;
				lines[iline][8] = date ;
				tot_cancer++ ;

			}
		}
	}

	fprintf(stderr,"Full Reg.: TOT-CANCER = %d\n",tot_cancer) ;
}

// Read colonoscopy results file (OBSOLOETE)
void readcolonoscopy()
{
	FILE *fin = fopen("\\\\server\\data\\ColonCancer\\colonoscopy.txt", "r");
	assert(fin != NULL) ;

	map<int,int> colonoscopy_hash ;
	for (int isev=0; isev<NSEVERITY; isev++) {
		for (int icode=0; icode<MAX_CODES; icode++) {
			if (colonoscopy[isev][icode] != -1)
				colonoscopy_hash[colonoscopy[isev][icode]] = isev ;
		}
	}

	int tot_before = 0 ;
	int tot_known = 0 ;
	int tot_new = 0 ;

	int lineno=0;
	char *ptr;
	while(!(feof(fin))) {

	 	char *usebuf = buf;
		fgets(usebuf, 4096, fin);
		lineno++;

		if (lineno == 1)
			continue ;
		 
		if (lineno%10000==0) printf("COLONSCOPY: <%d>\n", lineno);
		int l=0;
		do {			
			ptr = strpbrk(usebuf,"\t");
			buf1[l] = usebuf;
			if (ptr!=NULL) 
				buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			if (ptr==NULL) 
				break;
			usebuf = ptr+1;
			 
		} while (usebuf!=NULL);

		int idnum = atoi(buf1[0]);

		if (line_nos.find(idnum) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[idnum].size(); i++) {
				int iline = line_nos[idnum][i] ;
	
				int date = atoi(buf1[1]) ;

				for (int j=2; j<l-1; j++) {
					int code = atoi(buf1[j]) ;
					if (colonoscopy_hash.find(code) != colonoscopy_hash.end() && colonoscopy_hash[code] > 0) {
						if (lines[iline][7] == 1) {
							if (lines[iline][8] <= date)
								tot_known ++ ;
							else {
								tot_before ++ ;
								lines[iline][7] = 2 ;
								lines[iline][8] = date ;
							}
						} else if (lines[iline][7] == 3) {
							if (lines[iline][8] >= date) {
								tot_before ++ ;
								lines[iline][7] = 2 ;
								lines[iline][8] = date ;
							} else
								tot_known ++ ;
						} else if (lines[iline][7] == 2) {
							if (lines[iline][8] >= date)
								lines[iline][8] = date ;
						} else if (lines[iline][7] != -1) {
							tot_new ++ ;
							lines[iline][7] = 2 ;
							lines[iline][8] = date ;
						}
					}
				}
			}
		}
	}

	fprintf(stderr,"Full Reg.: TOT-BEFORE = %d\n",tot_before) ;
	fprintf(stderr,"Full Reg.: TOT-KNOWN = %d\n",tot_known) ;
	fprintf(stderr,"Full Reg.: TOT-NEW = %d\n",tot_new) ;
}

 int compare( const void *arg1, const void *arg2 )
{
	double *db1ptr = (double *)arg1;
	double *db2ptr = (double *)arg2;

	if (db1ptr[0]>db2ptr[0]) return(1);
	if (db1ptr[0]<db2ptr[0]) return(-1);
	if (db1ptr[1]>db2ptr[1]) return(1);
	if (db1ptr[1]<db2ptr[1]) return(-1);
	return(0);

}

 void sortfile()
 {

	 qsort(lines, idnameptr, sizeof(lines[0]), compare);
 }

// Read demographics file and fill age at lines[i][2]
void read_demographics()
{
	FILE *fin ;
	fin = fopen(DEM_FILE, "rb");

	assert(fin != NULL) ;

	int id,byear ;
	char gender ;
	while(!(feof(fin))) {
		int rc = fscanf(fin,"%d %d %c\n",&id,&byear,&gender) ;
		if (rc == EOF)
			break ;
		assert(rc == 3) ;

		if (line_nos.find(id) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[id].size(); i++) {
				int iline = line_nos[id][i] ;

				lines[iline][2] = byear*100*100+1*100+1;
				lines[iline][3] = 2010-byear;	

				assert(gender == 'M' || gender == 'F') ;
				if (gender == 'M')
					lines[iline][4] = 0 ;
				else 
					lines[iline][4] = 1 ;

			}
		}
	}
}

// Read status file and fill 
void read_status()
{

	FILE *fin ;
	fin = fopen(STT_FILE, "rb");

	assert(fin != NULL) ;

	int id,status,reason,date ;
	while(!(feof(fin))) {
		int rc = fscanf(fin,"%d %d %d %d\n",&id,&status,&reason,&date) ;
		if (rc == EOF)
			break ;
		assert(rc==4) ;

		if (line_nos.find(id) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[id].size(); i++) {
				int iline = line_nos[id][i] ;

				lines[iline][5] = status;
				lines[iline][6] = date;	

			}
		}
	}
}


// Configurable version - reading files given as vector of names
// CBCs
int read_cbcs(vector<string >& file_names)
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
	
	int nfiles =  (int) file_names.size();

	for(int fileno=0; fileno<nfiles; fileno++)
	{
 
		fprintf(stderr,"Reading: %s\n", file_names[fileno].c_str());
		FILE *fin = fopen(file_names[fileno].c_str(), "rb");
		if (fin==NULL) {
			fprintf(stderr,"Cannot open %s for reading\n",file_names[fileno].c_str()) ;
			return -1 ;
		}

		{
			char *ptr;
			while(!(feof(fin)))
			{
				 
				char *usebuf = buf;
				fgets(usebuf, 4096, fin);
				int l=0;
				do 
				{
					
					ptr = strpbrk(usebuf,"\t");
					buf1[l] = usebuf;
					if (ptr!=NULL) 
					 buf1[l][(int)(ptr-usebuf)]='\0';
					 
					l++;
					if (ptr==NULL) break;
					usebuf = ptr+1;
				} while (usebuf!=NULL);

				int idnum = atoi(buf1[0])+atoi(buf1[1])*1000000;

				if (use_id_list && id_list.find(idnum) == id_list.end())
					continue ;

				int labenum = atoi(buf1[2]);

				double labval  = atof(buf1[7]);
				int date = atoi(buf1[3]);

				pair<int,int> index ;
				index.first = idnum ;
				index.second = date ;

				int iline ;
				if (line_no.find(index) != line_no.end())
					iline = line_no[index] ;
				else {
					iline = idnameptr;

					line_no[index] = iline ;
					line_nos[idnum].push_back(iline) ;

					lines[iline][0] = idnum;
					lines[iline][1] = date;

					idnameptr ++;

					assert(idnameptr < MAXLINES) ;
					if (idnameptr%10000==0) fprintf(stderr,"[%d]\n", idnameptr);
					 
				}

				// Go over enumerator

//				if (lines[iline][enumlist_val[labenum]] != -1)
//					printf("Double %d @ %d,%d : %f vs %f\n",labenum,index.first,index.second,labval,lines[iline][enumlist_val[labenum]]) ;

				if (enumlist_val[labenum] != -1) {
					lines[iline][enumlist_val[labenum]] = labval;
				}
			}
		}
		fclose(fin) ;
		fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);
	}


	return 0 ;

	
}

// BioChem
int read_biochems(vector<string>& file_names, int take_new) 
{
	FILE *fin ;
	int nfiles = (int) file_names.size() ;

	int lineno=0;
	char *ptr;
	
	for (int ifile = 0; ifile < nfiles; ifile++) {
		fin = fopen(file_names[ifile].c_str(),"r") ;
		if (fin==NULL) {
			fprintf(stderr,"Cannot open %s for reading\n",file_names[ifile].c_str()) ;
			return -1 ;
		}
		fprintf(stderr,"Reading %s\n",file_names[ifile].c_str()) ;

		while(!(feof(fin))) {	 
			char *usebuf = buf;
			if (fgets(usebuf, 4096, fin) == NULL)
				break ;
			lineno++;
		 
//			if (lineno%50000==0) fprintf(stderr,"BioChem: <%d>\n", lineno);
			int l=0;
			
			do {			
				ptr = strpbrk(usebuf,"\t");
				buf1[l] = usebuf;
				if (ptr!=NULL) 
					buf1[l][(int)(ptr-usebuf)]='\0';
			 
				l++;
				if (ptr==NULL) break;
				usebuf = ptr+1;
			 
			} while (usebuf!=NULL);

			ptr=strpbrk(usebuf,"\n");
			assert(ptr != NULL) ;
			buf1[l-1][(int)(ptr-usebuf)] = '\0';

			int idnum = atoi(buf1[2]) ;
			int date = atoi(buf1[6]);
			int labenum = atoi(buf1[7]);
			double labval  = atof(buf1[8]);

			pair<int,int> index ;
			index.first = idnum ;
			index.second = date ;

			int iline ;
			if (line_no.find(index) != line_no.end())
				iline = line_no[index] ;
			else if (take_new || line_nos.find(idnum) != line_nos.end()) {
				iline = idnameptr;

				line_no[index] = iline ;
				line_nos[idnum].push_back(iline) ;

				lines[iline][0] = idnum;
				lines[iline][1] = date;

				idnameptr ++;

				if (idnameptr%10000==0) printf("[%d]\n", idnameptr);
				 
			} else 
				continue ;

			// Go over enumerator

			if (biochem_synonims.find(labenum) != biochem_synonims.end())
				labenum = biochem_synonims[labenum] ;

			if (enumlist_val[labenum] == -1) {
				fprintf(stderr,"Unknonwn test %d\n",labenum) ;
				return -1 ;
			}
			lines[iline][enumlist_val[labenum]] = labval;
		}

		fclose(fin) ;
	}

	fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);

	return 0;
}

// BMI
int read_bmis(vector<string>& file_names) {

	FILE *fin ;

	int fileno = (int) file_names.size() ;

	map<int,vector< pair<int,double> > > bmis ;

	// Read
	for (int ifile=0; ifile<fileno; ifile++) {

		printf("Reading BMI file %s\n",file_names[ifile].c_str()) ;
		fin = fopen(file_names[ifile].c_str(), "rb");
	
		if (fin==NULL) {
			fprintf(stderr,"Cannot open %s for reading\n",file_names[ifile].c_str()) ;
			return -1 ;
		}

		int lineno=0;
		char *ptr;
		int header = 1 ;
		while(!(feof(fin))) {

			char *usebuf = buf;
			fgets(usebuf, 4096, fin);

			if (header) {
				header=0; 
				continue ;
			}

			lineno++;
		 
//			if (lineno%10000==0) printf("BMI: <%d>\n", lineno);
			int l=0;
			do {
			
				ptr = strpbrk(usebuf,",");
				buf1[l] = usebuf;
				if (ptr!=NULL) 
					buf1[l][(int)(ptr-usebuf)]='\0';
			 
				l++;
				if (ptr==NULL) break;
				usebuf = ptr+1;
		
			} while (usebuf!=NULL);

			int idnum = atoi(buf1[0])/*+atoi(buf1[1])*1000000*/;

			int year=0;
			int month=0;
			int day =0;

			int chplace =0;
			sscanf(&buf1[2][chplace],"%d", &day);
			
			while(buf1[2][chplace]!='/') chplace++;
			chplace++;

			sscanf(&buf1[2][chplace],"%d", &month);
			while(buf1[2][chplace]!='/') chplace++;
			chplace++;

			sscanf(&buf1[2][chplace],"%d", &year);

			int date = year*100*100+month*100+day ;

			double bmi = atof(buf1[3]);

			if (line_nos.find(idnum) != line_nos.end()) {
				pair<int, double> single_bmi (date,bmi) ;
				bmis[idnum].push_back(single_bmi) ;
			}
		}
		fclose(fin) ;
	}

	// Fill
	double ftr_vals[NBMI_FTRS] ;
	for (map<int,vector< pair<int,double> > >::iterator it= bmis.begin(); it!= bmis.end(); it++) {

		int idnum = it->first ;

		for (unsigned int i = 0 ; i < line_nos[idnum].size(); i++) {
			int iline = line_nos[idnum][i] ;
			get_bmi_values(iline,it->second,ftr_vals) ;
			for (int j=0; j<NBMI_FTRS; j++)
				lines[iline][enumlistcol+j] = ftr_vals[j] ;
		}
	}

	sprintf(headers[enumlistcol],"BMI Value") ;
	sprintf(headers[enumlistcol+1],"BMI Time") ;
//	sprintf(headers[enumlistcol+2],"BMI Gradient") ;
//	sprintf(headers[enumlistcol+3],"BMI TimeDiff") ;
	enumlistcol+=NBMI_FTRS ;

	fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);

	return 0 ;
}

// Smoking
int read_smxs(vector<string>& file_names) {
	FILE *fin ;

	int fileno = (int) file_names.size() ;

	map<int,vector< pair<int,int> > > smx ;

	// Read
	for (int ifile=0; ifile<fileno; ifile++) {

		printf("Reading SMX file %s\n",file_names[ifile].c_str()) ;
		fin = fopen(file_names[ifile].c_str(), "rb");
	
		if (fin==NULL) {
			fprintf(stderr,"Cannot open %s for reading\n",file_names[ifile].c_str()) ;
			return -1 ;
		}

		int lineno=0;
		char *ptr;
		int header = 1 ;
		while(!(feof(fin))) {

			char *usebuf = buf;
			fgets(usebuf, 4096, fin);

			if (header) {
				header=0; 
				continue ;
			}

			lineno++;
		 
//			if (lineno%10000==0) fprintf(stderr,"SMX: <%d>\n", lineno);
			int l=0;
			do {
			
				ptr = strpbrk(usebuf,",");
				buf1[l] = usebuf;
				if (ptr!=NULL) 
					buf1[l][(int)(ptr-usebuf)]='\0';
			 
				l++;
				if (ptr==NULL) break;
				usebuf = ptr+1;
		
			} while (usebuf!=NULL);

			int idnum = atoi(buf1[0])/*+atoi(buf1[1])*1000000*/;

			int year=0;
			int month=0;
			int day =0;

			int chplace =0;
			sscanf(&buf1[2][chplace],"%d", &day);
			
			while(buf1[2][chplace]!='/') chplace++;
			chplace++;

			sscanf(&buf1[2][chplace],"%d", &month);
			while(buf1[2][chplace]!='/') chplace++;
			chplace++;

			sscanf(&buf1[2][chplace],"%d", &year);

			int date = year*100*100+month*100+day ;

			int code = atoi(buf1[3]);

			if (line_nos.find(idnum) != line_nos.end()) {
				pair<int, int> single_smx (get_days(date),code) ;
				smx[idnum].push_back(single_smx) ;
			}
		}
		fclose(fin) ;
	}

	// Fill
	for (map<int,vector< pair<int,int> > >::iterator it= smx.begin(); it!= smx.end(); it++) {

		int idnum = it->first ;
		sort(it->second.begin(),it->second.end(),compare_reads()) ;

		double val1,val2,val3,val4,val5 ;
		for (unsigned int i = 0 ; i < line_nos[idnum].size(); i++) {
//			printf("%d ::\n",idnum) ;
			int iline = line_nos[idnum][i] ;
			get_smx_values(iline,it->second,&val1,&val2,&val3) ;
			lines[iline][enumlistcol] = val1 ;
			lines[iline][enumlistcol+1] = val2 ;
			lines[iline][enumlistcol+2] = val3 ;
			// extrapolating qty smx for MHS (assuming avg smx start age of 20 and avg of 10 cig per day)
			// val4 - number of pack years
			// val5 - years since quitting
			int test_year = (int) lines[iline][1] / 10000 ;
			int test_age = test_year - (int) lines[iline][2] / 10000 ;
			val4 = -1.0; val5 = -1.0;
			if (val1 == 3) { // never smoker at time of test
				val5 = max(test_age - 20, 0);
				val4 = 0;
			}
			if (val1 == 2) { // ex-smoker at time of test
				val5 = val3/365;
				val4 = max(test_age - int(val5) - 20, 0) * 10 / 20;
			}
			if (val1 == 1) { // current smoker
				val5 = 0;
				val4 = max(test_age - 20, 0) * 10 / 20;
			}

			lines[iline][enumlistcol+3] = val4 ;
			lines[iline][enumlistcol+4] = val5 ;
		}
	}

	sprintf(headers[enumlistcol],"SMX Value") ;
	sprintf(headers[enumlistcol+1],"SMX Time1") ;
	sprintf(headers[enumlistcol+2],"SMX Time2") ;
	sprintf(headers[enumlistcol+3],"SMX Pack Years") ;
	sprintf(headers[enumlistcol+4],"SMX YsQ") ; // number of Years since Quitting
	enumlistcol+=5 ;

	fprintf(stderr, "TOTAL COLS: %d    TOTAL LINES: %d\n", enumlistcol,idnameptr);

	return 0;
}

// Demographics
int read_demographics(vector<string>& file_names) {
	FILE *fin ;

	int fileno = (int) file_names.size() ;

	map<int,vector< pair<int,int> > > smx ;

	// Read
	for (int ifile=0; ifile<fileno; ifile++) {

		printf("Reading Demographics file %s\n",file_names[ifile].c_str()) ;
		fin = fopen(file_names[ifile].c_str(), "rb");
	
		if (fin==NULL) {
			fprintf(stderr,"Cannot open %s for reading\n",file_names[ifile].c_str()) ;
			return -1 ;
		}

		int id,byear ;
		char gender ;
		while(!(feof(fin))) {
			int rc = fscanf(fin,"%d %d %c\n",&id,&byear,&gender) ;
			if (rc == EOF)
				break ;
			assert(rc == 3) ;

			if (line_nos.find(id) != line_nos.end()) {
				for (unsigned int i=0; i<line_nos[id].size(); i++) {
					int iline = line_nos[id][i] ;

					lines[iline][2] = byear*100*100+1*100+1;
					lines[iline][3] = 2010-byear;	

					assert(gender == 'M' || gender == 'F') ;
					if (gender == 'M')
						lines[iline][4] = 0 ;
					else 
						lines[iline][4] = 1 ;

				}
			}
		}

		fclose(fin) ;
	}

	return 0 ;
}

// Status
int read_status(vector<string>& file_names) {

	FILE *fin ;

	int fileno = (int) file_names.size() ;

	map<int,vector< pair<int,int> > > smx ;

	// Read
	for (int ifile=0; ifile<fileno; ifile++) {

		printf("Reading Status file %s\n",file_names[ifile].c_str()) ;
		fin = fopen(file_names[ifile].c_str(), "rb");
	
		if (fin==NULL) {
			fprintf(stderr,"Cannot open %s for reading\n",file_names[ifile].c_str()) ;
			return -1 ;
		}

		int id,status,reason,date ;
		while(!(feof(fin))) {
			int rc = fscanf(fin,"%d %d %d %d\n",&id,&status,&reason,&date) ;
			if (rc == EOF)
				break ;
			assert(rc==4) ;

			if (line_nos.find(id) != line_nos.end()) {
				for (unsigned int i=0; i<line_nos[id].size(); i++) {
					int iline = line_nos[id][i] ;

					lines[iline][5] = status;
					lines[iline][6] = date;	

				}
			}
		}

		fclose(fin) ;
	}

	return 0 ;
}

// Read configuration files : Each line contains a file type (cbc/biochem/bmi/smx/demographics/status) and a file name
int read_input_file_names(char *config_file_name, map<string,vector<string> >& file_names) {

	FILE *fp = fopen(config_file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading",config_file_name) ;
		return -1 ;
	}

	while(!(feof(fp))) {

		char *usebuf = buf;
		if (fgets(usebuf, 4096, fp) == NULL)
			break ;

		fprintf(stderr, "Working on line: %s\n", usebuf);

		// Comment
		if (usebuf[0] == '#') 
			continue ;

		int l=0;
		do {
			
			char *ptr = strpbrk(usebuf,"\t");
			buf1[l] = usebuf;
			if (ptr!=NULL) 
				buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			if (ptr==NULL) break;
			usebuf = ptr+1;
		
		} while (usebuf!=NULL);

		if (l != 2) {
			fprintf(stderr,"Cannot parse line in %s, line has %d tokens\n", config_file_name, l) ;
			return -1 ;
		}

		if (strcmp(buf1[0],"cbc")!=0 && strcmp(buf1[0],"biochem")!=0 && strcmp(buf1[0],"bmi")!=0 && strcmp(buf1[0],"smx")!=0 && strcmp(buf1[0],"demog")!=0 && 
			strcmp(buf1[0],"status")!=0 && strcmp(buf1[0],"reg")!=0) {
			fprintf(stderr,"Unknown file type \'%s\' in %s\n",buf1[0],config_file_name) ;
			return -1 ;
		}

		char *ptr = strpbrk(buf1[1],"\r") ;
		char *ptr2 = strpbrk(buf1[1],"\n") ;
		if ((ptr==NULL && ptr2!=NULL) || (ptr2!= NULL && ptr2 < ptr))
			ptr = ptr2 ;
		if (ptr != NULL)
			buf1[1][(int)(ptr-buf1[1])] = '\0' ;
		
		// fprintf(stderr, "line splitted into tokens: %s\t%s\n", buf1[0], buf1[1]);
		if (file_names.find(buf1[0]) == file_names.end()) {
			vector<string> temp_names ;
			file_names[buf1[0]] = temp_names ;
		}
		file_names[buf1[0]].push_back(buf1[1]) ;
	}

	fclose(fp) ;

	return 0 ;
}

// Read Ids
int read_ids(char *file_name) {

	use_id_list = 1 ;

	// Read
	FILE *fp = fopen(file_name,"r") ;
		if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading",file_name) ;
		return -1 ;
	}
	
	int id ;

	while (!feof(fp)) {
		int rc = fscanf(fp,"%d\n",&id) ;
		if (rc == EOF)
			return 0 ;

		if (rc != 1) {
			fprintf(stderr,"Cannot parse line %d in %s\n",__LINE__, file_name) ;
			return -1 ;
		}
		id_list.insert(id) ;
	}
	fclose(fp) ;


	return 0 ;
}


