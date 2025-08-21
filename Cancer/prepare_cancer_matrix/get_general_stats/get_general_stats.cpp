#define _CRT_SECURE_NO_WARNINGS

#include "get_general_stats.h"

int main(int argc, char * argv[])
{

	if (argc != 4) {
		fprintf(stderr,"Usage: get_general_stats DemFile CBCFile 0=Maccabi/1=THIN\n") ;
		return -1 ;
	}

	int data_type = atoi(argv[3]) ;

	// Read demography
	map<int,dem> demography ;
	assert(read_demography(argv[1],demography) == 0) ;
	fprintf(stderr,"Read %zd entries in %s\n",demography.size(),argv[1]) ;

	// Read CBCs
	cbcs_data cbcs ;
	assert(read_cbcs(argv[2],cbcs,data_type) == 0) ;

	// All CBC dates ... CBC = Haemoglobin + Others
	map<int,vector<int> > cbc_dates ;
	for (cbcs_data::iterator it = cbcs.begin(); it != cbcs.end(); it ++) {
		int id = it->first ;
		map<int, map<int, double> >& dates = it->second ;

		vector<int> vdates ; 
		for (map<int, map<int, double> >::iterator it = dates.begin(); it != dates.end(); it++) {
			if (it->second.find(test_codes[data_type][0]) != it->second.end())
				vdates.push_back(it->first) ;
		}

		if (vdates.size() > 0) {
			cbc_dates[id] = vdates ;
			sort(cbc_dates[id].begin(),cbc_dates[id].end(),int_compare()) ;
		}
	}




	// STATISTICS !

	map<int,int> codes ;
	for (int i=0; i<NTESTS; i++)
		codes[test_codes[data_type][i]] = i ;

	// Numbers
	fprintf(stderr,"Counting\n") ;
	int cnts[2] = {0,0} ;
	for (cbcs_data::iterator it = cbcs.begin(); it != cbcs.end(); it++) {
		int id = it->first ;
		assert(demography.find(id) != demography.end()) ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;
		cnts[gender]++ ;
	}
	// Age at 2011
	fprintf(stderr,"Age Histogram\n") ;
	vector<map<int,int> > age_hist(2) ;
	for (cbcs_data::iterator it = cbcs.begin(); it != cbcs.end(); it++) {
		int id = it->first ;
		assert(demography.find(id) != demography.end()) ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;
		int age_bin = (2011 - demography[id].byear)/5 ;
		age_hist[gender][age_bin]++ ;
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of ages at 2011 for %s\n",gender_names[i]) ;
		int min_bin = 30 ;
		int max_bin = 0 ;
		for (map<int,int>::iterator it = age_hist[i].begin(); it != age_hist[i].end(); it++) {
			if (it->first > max_bin)
				max_bin = it->first ;
			if (it->first < min_bin)
				min_bin = it->first ;
		}

		for (int ibin=min_bin; ibin<=max_bin; ibin++) {
			if (age_hist[i].find(ibin) != age_hist[i].end())
				printf("%d - %d\t%d\t%.2f\n",5*ibin,5*(ibin+1),age_hist[i][ibin],(100.0*age_hist[i][ibin])/cnts[i]) ;
		}
		printf("\n") ;
	}			

	// Distribution of Values
	fprintf(stderr,"Values of tests\n") ;
	int n[2][40][NTESTS] ;
	double s[2][40][NTESTS] ;
	double s2[2][40][NTESTS] ;

	for (int i=0; i<2; i++) {
		for (int j=0; j<40; j++) {
			for (int k=0; k<NTESTS; k++) {
				n[i][j][k] = 0 ;
				s[i][j][k] = s2[i][j][k] = 0 ;
			}
		}
	}

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;

		int gender = (demography[id].gender == 'M') ? 0 : 1 ;
		int bday = get_days(10000*demography[id].byear + 101) + 183 ;

		for (int i=0; i<cbc_dates[id].size(); i++) {
			int date = cbc_dates[id][i] ;
			int age_bin = (date - bday)/365/10 ;
			assert(age_bin < 20) ;

			for (map<int,double>::iterator it = cbcs[id][date].begin(); it != cbcs[id][date].end(); it++) {
				assert(codes.find(it->first) != codes.end()) ;
				int idx = codes[it->first] ;
				double value = it->second ;
//				if (gender == 0 && idx == 0)
//					printf("Hemoglobin %d %f\n",age_bin,value) ;

				n[gender][age_bin][idx] ++ ;
				s[gender][age_bin][idx] += value ;
				s2[gender][age_bin][idx] += value*value;
			}
		}
	}

	for (int i=0; i<NTESTS; i++) {
		for (int gender=0; gender<2; gender++) {
			for (int age_bin=0; age_bin<20; age_bin++) {
				if (n[gender][age_bin][i] > 0) {
					double mean = s[gender][age_bin][i]/n[gender][age_bin][i] ;
					double sdv = (n[gender][age_bin][i]==1) ? 0 : sqrt((s2[gender][age_bin][i] - mean*s[gender][age_bin][i])/(n[gender][age_bin][i] - 1)) ;
					printf("Test %s at ages %d-%d for %s : Mean = %.2f Standard-Devaition = %.2f N = %d\n",test_names[i],10*age_bin,10*(age_bin+1),
						gender_names[gender],mean,sdv,n[gender][age_bin][i]) ;
				}
			}
			printf("\n") ;
		}
	}

	// Histograms of Values for Controls
	fprintf(stderr,"Values Histograms at 60-70\n") ;

	map<double,int> values[NTESTS][2] ;
	int ninds[NTESTS][2] ;
	for (int i=0; i<NTESTS; i++)
		ninds[i][0] = ninds[i][1] = 0 ;

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;

		int gender = (demography[id].gender == 'M') ? 0 : 1 ;
		int bday = get_days(10000*demography[id].byear + 101) + 183 ;

		int taken[NTESTS] ;
		memset(taken,0,sizeof(taken)) ;

		for (int i=0; i<cbc_dates[id].size(); i++) {
			int date = cbc_dates[id][i] ;
			int age = (date - bday)/365 ;
			if (age < 60 || age > 70)
				continue ;

			for (map<int,double>::iterator it = cbcs[id][date].begin(); it != cbcs[id][date].end(); it++) {
				assert(codes.find(it->first) != codes.end()) ;
				int idx = codes[it->first] ;
				double value = ((int) (resolutions[idx] * it->second))/resolutions[idx];
				values[idx][gender][value] ++ ;
				taken[idx] = 1 ;
			}
		}

		for (int i=0; i<NTESTS; i++)
			ninds[i][gender] += taken[i] ;
	}

	for (int itest = 0 ; itest<NTESTS ; itest ++) {
		for (int gender = 0 ; gender < 2 ; gender ++) {

			vector<double> keys ;
			int ntotal = 0 ;
			for (map<double,int>::iterator it = values[itest][gender].begin(); it != values[itest][gender].end(); it++) {
				keys.push_back(it->first) ;
				ntotal += it->second ;
			}
			sort(keys.begin(),keys.end()) ;

			for (unsigned int i=0; i<keys.size(); i++)
				printf("Values Histogram of %s for %s : %f %.3f\n",test_names[itest],gender_names[gender],keys[i],(100.0*values[itest][gender][keys[i]])/ntotal) ;
			printf("\n") ;

			printf("Total # of %s for %s = %d (for %d individuals)\n",test_names[itest],gender_names[gender],ntotal,ninds[itest][gender]) ;
		}
	}
}

// Functions

// Read demography
int read_demography(char *file_name, map<int,dem>& demography) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	// Read demography
	int id ;
	int byear ;
	char gender ;

	while (! feof(fp)) {
		int rc = fscanf(fp,"%d %d %c\n",&id,&byear,&gender) ;
		if (rc == EOF)
			break ;

		if (rc != 3) {
			fprintf(stderr,"Could not read status line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		dem new_dem ;
		new_dem.byear = byear ;
		new_dem.gender = gender;
		demography[id] = new_dem ;
	}

	fclose(fp) ;
	return 0 ;
}

// Read cbcs
int read_cbcs(char *file_name, cbcs_data& cbcs, int data_type) {

	// Prepare
	map<int,int> codes ;
	for (int i=0; i<NTESTS; i++)
		codes[test_codes[data_type][i]] = 1 ;

	// Read
	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	// Read test results
	int id,code,date ;
	double value ;

	int itest = 0 ;
	while (! feof(fp)) {
		int rc = fscanf(fp,"%d %d %d %lf\n",&id,&code,&date,&value) ;
		if (rc == EOF)
			break ;

		if (rc != 4) {
			fprintf(stderr,"Could not read status line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		if (date%10000 == 0) {
			fprintf(stderr,"(Ignoring %d %d %d %lf)",id,code,date,value) ;
			continue;
		}

		if (codes.find(code) != codes.end())
			cbcs[id][get_days(date)][code] = value ; 

		if ((++itest)%2500000 == 0)
			fprintf(stderr,"Read %d tests... ",itest) ;

		// FAST DEBUG
//		if (itest == 3000000)
//			break ;
	}

	fprintf(stderr,"\n") ;
	fclose(fp) ;
	return 0 ;
}

// Days from 01/01/1900
int get_days(int date) {
		
	int year = date/100/100 ;
	int month = (date/100)%100 ;
	int day = date%100 ;

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