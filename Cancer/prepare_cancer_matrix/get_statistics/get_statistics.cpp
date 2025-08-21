#define _CRT_SECURE_NO_WARNINGS

#include "get_statistics.h"

int main(int argc, char * argv[])
{
	// Read registry
	map<int,reg_entry> registry ;
	assert(read_registry(reg_files[DATA_TYPE],registry) == 0) ;
	fprintf(stderr,"Read %zd entries in %s\n",registry.size(),reg_files[DATA_TYPE]) ;

	// Read censor
	map<int,status> censor ;
	assert(read_censor(censor_files[DATA_TYPE],censor) == 0) ;
	fprintf(stderr,"Read %zd entries in %s\n",censor.size(),censor_files[DATA_TYPE]) ;

	// Read demography
	map<int,dem> demography ;
	assert(read_demography(dem_files[DATA_TYPE],demography) == 0) ;
	fprintf(stderr,"Read %zd entries in %s\n",demography.size(),dem_files[DATA_TYPE]) ;

	// Read CBCs
	cbcs_data cbcs ;
	assert(read_cbcs(cbc_files[DATA_TYPE],cbcs) == 0) ;

	// All CBC dates ... CBC = Haemoglobin + Others
	map<int,vector<int> > cbc_dates ;
	for (cbcs_data::iterator it = cbcs.begin(); it != cbcs.end(); it ++) {
		int id = it->first ;
		map<int, map<int, double> >& dates = it->second ;

		vector<int> vdates ; 
		for (map<int, map<int, double> >::iterator it = dates.begin(); it != dates.end(); it++) {
			if (it->second.find(test_codes[DATA_TYPE][3]) != it->second.end())
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
		codes[test_codes[DATA_TYPE][i]] = i ;

	// Number of CRC cases
	fprintf(stderr,"Counting CRC \n") ;
	int crc_all_cnts[2] = {0,0} ;
	int crc_cbc_cnts[2] = {0,0} ;

	for (map<int,reg_entry>::iterator it = registry.begin(); it != registry.end(); it++) {
		int id = it->first ;

		if (demography.find(id) == demography.end()) {
			fprintf(stderr,"Cannot find demography entry for %d\n",id) ;
			return -1 ;
		}

		int gender = (demography[id].gender == 'M') ? 0 : 1 ;
		
		if (it->second.type == 1) {
			crc_all_cnts[gender] ++ ;

			if (cbc_dates.find(id) != cbc_dates.end() && cbc_dates[id][0] < it->second.date)
				crc_cbc_cnts[gender] ++ ;
		}
	}

	for (int i=0; i<2; i++)
		printf("%s : %d CRC cases ; %d cases with Hemoglobin prior to registry\n",gender_names[i],crc_all_cnts[i],crc_cbc_cnts[i]) ;
	printf("\n") ;

	// Number of Healthy cases
	fprintf(stderr,"Counting Controls \n") ;
	int hlt_cnts[2] = {0,0} ;
	for (cbcs_data::iterator it = cbcs.begin(); it != cbcs.end(); it++) {
		int id = it->first ;
		if (registry.find(id) == registry.end()) {
			if (demography.find(id) == demography.end()) {
				fprintf(stderr,"Cannot find demography entry for %d\n",id) ;
				return -1 ;
			}
			int gender = (demography[id].gender == 'M') ? 0 : 1 ;
			hlt_cnts[gender]++ ;
		}
	}

	for (int i=0; i<2; i++)
		printf("%s : %d Healthy subjects with Hemoglobin\n",gender_names[i],hlt_cnts[i]) ;
	printf("\n") ;

	// Age at CRC registry
	fprintf(stderr,"CRC Age Histogram\n") ;
	vector<map<int,int> > cbc_age_hist(2) ;
	for (map<int,reg_entry>::iterator it = registry.begin(); it != registry.end(); it++) {
		int id = it->first ;
		assert(demography.find(id) != demography.end()) ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (it->second.type == 1 && cbc_dates.find(id) != cbc_dates.end() && cbc_dates[id][0] < it->second.date) {
			int age_bin = ((it->second.date  - (get_days(10000*demography[id].byear + 101) + 183))/365)/5 ;
			cbc_age_hist[gender][age_bin]++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of CRC registry ages for %s\n",gender_names[i]) ;
		int min_bin = 30 ;
		int max_bin = 0 ;
		for (map<int,int>::iterator it = cbc_age_hist[i].begin(); it != cbc_age_hist[i].end(); it++) {
			if (it->first > max_bin)
				max_bin = it->first ;
			if (it->first < min_bin)
				min_bin = it->first ;
		}

		for (int ibin=min_bin; ibin<=max_bin; ibin++) {
			if (cbc_age_hist[i].find(ibin) != cbc_age_hist[i].end())
				printf("%d - %d\t%d\t%.2f\n",5*ibin,5*(ibin+1),cbc_age_hist[i][ibin],(100.0*cbc_age_hist[i][ibin])/crc_cbc_cnts[i]) ;
		}
		printf("\n") ;
	}

	// Healthy subjects age at 2011
	fprintf(stderr,"Control Age Histogram\n") ;
	vector<map<int,int> > hlt_age_hist(2) ;
	for (cbcs_data::iterator it = cbcs.begin(); it != cbcs.end(); it++) {
		int id = it->first ;
		if (registry.find(id) == registry.end()) {
			assert(demography.find(id) != demography.end()) ;
			int gender = (demography[id].gender == 'M') ? 0 : 1 ;
			int age_bin = (2011 - demography[id].byear)/5 ;
			hlt_age_hist[gender][age_bin]++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of healthy subjects ages for %s\n",gender_names[i]) ;
		int min_bin = 30 ;
		int max_bin = 0 ;
		for (map<int,int>::iterator it = hlt_age_hist[i].begin(); it != hlt_age_hist[i].end(); it++) {
			if (it->first > max_bin)
				max_bin = it->first ;
			if (it->first < min_bin)
				min_bin = it->first ;
		}

		for (int ibin=min_bin; ibin<=max_bin; ibin++) {
			if (hlt_age_hist[i].find(ibin) != hlt_age_hist[i].end())
				printf("%d - %d\t%d\t%.2f\n",5*ibin,5*(ibin+1),hlt_age_hist[i][ibin],(100.0*hlt_age_hist[i][ibin])/hlt_cnts[i]) ;
		}
		printf("\n") ;
	}			

	// CBCs statistics. CBC = Haemoglobin + Others
	// Distribution of # of tests in panel
	fprintf(stderr,"Panel Size distribution\n") ;
	int test_hist[2][NTESTS] ;
	for (int i=0; i<2; i++)
		memset(test_hist[i],0,NTESTS*sizeof(int)) ;

	int total[2] = {0,0} ;
	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		vector<int>& dates = it->second ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;
		total[gender] += (int) dates.size() ;
		for (int i=0; i<dates.size(); i++) {
			int ntests = (int) cbcs[id][dates[i]].size() ; 
			test_hist[gender][ntests-1] ++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("Distribution of panel size for %s\n",gender_names[i]) ;
		for (int ntests=1; ntests<=NTESTS; ntests++)
			printf("%d Tests at Panel: %d %.2f\n",ntests,test_hist[i][ntests-1],(100.0*test_hist[i][ntests-1])/total[i]) ;
		printf("\n") ;
	}

	// Panels histogram and missing values
	fprintf(stderr,"Histogram of panel types\n") ;

	int ncodes = 0 ;
	for (map<int,int>::iterator it = codes.begin(); it != codes.end(); it++) {
		if (it->second + 1 > ncodes)
			ncodes = it->second + 1 ;
	}

	vector<int> counts(codes.size(),0) ;

	map<vector<int>,int> panel_counts ;
	int total_counts = 0 ;
	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		vector<int>& dates = it->second ;
		for (int i=0; i<dates.size(); i++) {
			vector<int> panel(ncodes,0) ;
			for (map<int,double>::iterator cit = cbcs[id][dates[i]].begin(); cit != cbcs[id][dates[i]].end(); cit++) {
				assert(codes.find(cit->first) != codes.end()) ;
				int idx = codes[cit->first] ;
				panel[idx] = 1 ;
			}
			panel_counts[panel] ++ ;
			total_counts ++ ;

			for (int j=0; j<panel.size(); j++)
				counts[j] += panel[j] ;

		}
	}

	printf("Counts of Available CBC tests\n") ;
	for (int i=0; i<counts.size(); i++)
		printf("%s Appeared in %d panels\n",test_names[i],counts[i]) ;
	printf("\n") ;

	vector<pair<vector<int>,int> > p_counts ;
	for (map<vector<int>,int>::iterator it=panel_counts.begin(); it!=panel_counts.end(); it++) {
		vector<int> temp = it->first ;
		int num = it->second ;
		pair<vector<int>,int> count(temp,num) ;
		p_counts.push_back(count) ;
	}

	sort(p_counts.begin(),p_counts.end(),panel_compare()) ;

	printf("Histogram of panel types\n") ;
	for (vector<pair<vector<int>,int> >::iterator it=p_counts.begin(); it!=p_counts.end(); it++) {
		double perc = 100 * (it->second+0.0)/total_counts ;
		if (perc > 0.1) {
			printf("Panel ");
			for (int i=0; i<ncodes; i++)
				printf("%d",(it->first)[i]) ;
			printf(" Appears %d times - %.1f%%\n",it->second,perc) ;
		}
	}
	printf("\n") ;

	// Mark Good Subjects (available in 2003-2011)
	int min_day = get_days(20021231) ;
	int max_day = get_days(20110701) ;

	map<int,int> good_subject ;
	int ngood = 0, ntotal = 1 ;
	for (map<int,status>::iterator it = censor.begin(); it != censor.end(); it++) {
		int id = it->first ;
		int stat = it->second.stat ;
		int date = it->second.date ;

		if (stat == 1 && date < min_day) {
			good_subject[id] = 1 ;
			ngood ++ ;
		}
		ntotal ++ ;
	}
	fprintf(stderr,"Marked %d/%d as good\n",ngood,ntotal) ;

	// Distribution of panels per healthy person 
	fprintf(stderr,"Panel Number distribution\n") ;
	int nsubjects[2] = {0,0} ;
	memset(total,0,sizeof(total)) ;

	for (map<int,dem>::iterator it=demography.begin(); it != demography.end(); it++) {
		int id = it->first ;
		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		int gender = (it->second.gender == 'M') ? 0 : 1 ;
		nsubjects[gender]++ ;
	}

	for (int i=0; i<2; i++)
		nsubjects[i] = (int) (internal_factor[DATA_TYPE] * nsubjects[i]) ;

	vector<map<int,int> > npanels(2) ;

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		int ndates =  0 ;
		for (unsigned int i=0; i<it->second.size(); i++) {
			if (it->second[i] > min_day && it->second[i] < max_day)
				ndates++ ;
		}
		npanels[gender][ndates]++ ;
		total[gender]++ ;
	}

	for (int i=0; i<2; i++)
		npanels[i][0] = nsubjects[i] - total[i] ;

	for (int i=0; i<2; i++) {
		printf("Distribution of # of panels in 2003-07/2011 for uncensored control %s\n",gender_names[i]) ;

		int maxn = 0 ;
		for (map<int,int>::iterator it=npanels[i].begin(); it != npanels[i].end(); it++) {
			if (it->first > maxn)
				maxn = it->first ;
		}

		for (int n=0; n<=maxn; n++) {
			if (npanels[i].find(n) != npanels[i].end())
				printf("%d Panels : %d %.2f\n",n,npanels[i][n],(100.0*npanels[i][n])/nsubjects[i]) ;
		}
		printf("\n") ;
	}

	// Last Panel before Cancer Discovery
	fprintf(stderr,"Time to CRC Discovery\n") ;
	vector<vector<int> > time_before_registry(2) ;
	for (int i=0; i<2; i++) {
		total[i] = 0 ;
		time_before_registry[i].resize(24) ;
		for (int j=0; j<24; j++)
			time_before_registry[i][j] = 0 ;
	}

	for (map<int,reg_entry>::iterator it = registry.begin(); it != registry.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (it->second.type == 1 && cbc_dates.find(id) != cbc_dates.end() && cbc_dates[id][0] < it->second.date) {
			int time ;
			for (unsigned int i=0; i<cbc_dates[id].size(); i++) {
				if (cbc_dates[id][i] >= it->second.date)
					break ;
				time = it->second.date - cbc_dates[id][i] ;
			}
		
			int nmonths = (int) (1 + time/30) ;
			if (nmonths > 24)
				nmonths = 24 ;
			time_before_registry[gender][nmonths-1]++ ;
			total[gender]++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of time from last panel to registry for %s\n",gender_names[i]) ;
		for (int time=1; time < 24; time++)
			printf("%d months\t%d\t%.2f\n",time,time_before_registry[i][time-1],(100.0*time_before_registry[i][time-1])/total[i]) ;
		printf("24 months and more\t%d\t%.2f\n",time_before_registry[i][24-1],(100.0*time_before_registry[i][24-1])/total[i]) ;
		printf("\n") ;
	}

	// Last Panel before 06/2010
	fprintf(stderr,"Time to 01/06/2010\n") ;
	vector<vector<int> > time_to_date(2) ;
	for (int i=0; i<2; i++) {
		total[i] = 0 ;
		time_to_date[i].resize(24) ;
		for (int j=0; j<24; j++)
			time_to_date[i][j] = 0 ;
	}

	int destination_day = get_days(20100601);
	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		int time ;
		for (unsigned int i=0; i<cbc_dates[id].size(); i++) {
			if (cbc_dates[id][i] >= destination_day)
					break ;
			time = destination_day - cbc_dates[id][i] ;
		}
		
		int nmonths = (int) (1 + time/30) ;
		if (nmonths > 24)
			nmonths = 24 ;
		time_to_date[gender][nmonths-1]++ ;
		total[gender]++ ;
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of time from last panel to 06/2010 for uncensored control %s\n",gender_names[i]) ;
		for (int time=1; time < 24; time++)
			printf("%d months\t%d\t%.2f\n",time,time_to_date[i][time-1],(100.0*time_to_date[i][time-1])/total[i]) ;
		printf("24 months and more\t%d\t%.2f\n",time_to_date[i][24-1],(100.0*time_to_date[i][24-1])/total[i]) ;
		printf("\n") ;
	}

	// Cummulative data
	fprintf(stderr,"Cummulative analysis of time prior to given date\n") ;
	for (int i=0; i<2; i++) {
		total[i] = 0 ;
		time_to_date[i].resize(9) ;
		for (int j=0; j<=8; j++)
			time_to_date[i][j] = 0 ;
	}

	int destination_days[3] ;
	destination_days[0] = get_days(20110915) ;
	destination_days[1] = get_days(20100415) ;
	destination_days[2] = get_days(20091115) ;
	int ndays = 3 ;

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		int time ;
		for (int iday=0; iday<ndays; iday++) {
			for (unsigned int i=0; i<cbc_dates[id].size(); i++) {
				if (cbc_dates[id][i] >= destination_days[iday])
						break ;
				time = destination_days[iday] - cbc_dates[id][i] ;
			}
		
			int bin = (int) (time/30/3) ;
			if (bin > 8)
				bin = 8 ;
			time_to_date[gender][bin]++ ;
			total[gender]++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("tri-months from last panel to random date for uncensored control %s\n",gender_names[i]) ;
		for (int bin=0; bin < 8; bin++)
			printf("%d-%d months\t%d\t%.2f\n",3*bin,3*(bin+1),time_to_date[i][bin],(100.0*time_to_date[i][bin])/total[i]) ;
		printf("24 months and more\t%d\t%.2f\n",time_to_date[i][8],(100.0*time_to_date[i][8])/total[i]) ;
		printf("\n") ;
	}

	// Contrls mean Time-Delta
	fprintf(stderr,"Contol Time Delta\n") ;
	vector<vector<int> > time_delta(2) ;
	for (int i=0; i<2; i++) {
		total[i] = 0 ;
		time_delta[i].resize(36) ;
		for (int j=0; j<36; j++)
			time_delta[i][j] = 0 ;
	}

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		for (unsigned int i=1; i<cbc_dates[id].size() ; i++) {
			if (cbc_dates[id][i] > min_day && cbc_dates[id][i] < max_day) {
				int delta = cbc_dates[id][i] - cbc_dates[id][i-1] ;		
				int nmonths = (int) (1 + delta/30) ;
				if (nmonths > 36)
					nmonths = 36 ;
				time_delta[gender][nmonths-1]++ ;
				total[gender]++ ;
			}
		}
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of time difference between adjacent panels for uncensored control %s\n",gender_names[i]) ;
		for (int time=1; time < 36; time++)
			printf("%d months\t%d\t%.2f\n",time,time_delta[i][time-1],(100.0*time_delta[i][time-1])/total[i]) ;
		printf("36 months and more\t%d\t%.2f\n",time_delta[i][36-1],(100.0*time_delta[i][36-1])/total[i]) ;
		printf("\n") ;
	}

	// Estimate Consistent testing
	fprintf(stderr,"Estimate consistent testing\n") ;
	int year_counts[2][8] ;
	int year_flags[8] ;
	for (int i=0; i<2; i++) {
		total[i] = 0 ;
		memset(year_counts[i],0,8*sizeof(int)) ;
	}

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		memset(year_flags,0,8*sizeof(int)) ;
		for (unsigned int i=0; i<cbc_dates[id].size(); i++) {
			int year = (int)((cbc_dates[id][i] - min_day)/365) ;
			if (year >= 0 && year < 8)
				year_flags[year] = 1 ;
		}

		int count = 0 ;
		for (int year=0; year<8; year++) {
			if (year_flags[year])
				count ++ ;
		}
		
		if (count > 0) {
			total[gender] ++ ;
			year_counts[gender][count-1] ++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of number of years with a panel in 2003-2010 for uncensored control %s\n",gender_names[i]) ;
		for (int n=0; n<8; n++)
			printf("%d years\t%d\t%.2f\n",n+1,year_counts[i][n],(100.0*year_counts[i][n])/total[i]) ;
		printf("\n") ;
	}

	// For Older subjects ...
	for (int i=0; i<2; i++) {
		total[i] = 0 ;
		memset(year_counts[i],0,8*sizeof(int)) ;
	}

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end() || demography[id].byear > 1950)
			continue ;

		memset(year_flags,0,8*sizeof(int)) ;
		for (unsigned int i=0; i<cbc_dates[id].size(); i++) {
			int year = (int)((cbc_dates[id][i] - min_day)/365) ;
			if (year >= 0 && year < 8)
				year_flags[year] = 1 ;
		}

		int count = 0 ;
		for (int year=0; year<8; year++) {
			if (year_flags[year])
				count ++ ;
		}

		if (count > 0) {
			total[gender] ++ ;
			year_counts[gender][count-1] ++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of number of years with a panel in 2003-2010 for uncensored control %s born before 1950\n",gender_names[i]) ;
		for (int n=0; n<8; n++)
			printf("%d years\t%d\t%.2f\n",n+1,year_counts[i][n],(100.0*year_counts[i][n])/total[i]) ;
		printf("\n") ;
	}

	// Estimate Consistent bi-yearly testing
	fprintf(stderr,"Estimate consistent testing\n") ;
	int bi_year_counts[2][4] ;
	int bi_year_flags[4] ;
	for (int i=0; i<2; i++) {
		total[i] = 0 ;
		memset(bi_year_counts[i],0,4*sizeof(int)) ;
	}

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		memset(bi_year_flags,0,4*sizeof(int)) ;
		for (unsigned int i=0; i<cbc_dates[id].size(); i++) {
			int year = (int)((cbc_dates[id][i] - min_day)/365/2) ;
			if (year >= 0 && year < 4)
				bi_year_flags[year] = 1 ;
		}

		int count = 0 ;
		for (int year=0; year<4; year++) {
			if (bi_year_flags[year])
				count ++ ;
		}
		
		if (count > 0) {
			total[gender] ++ ;
			bi_year_counts[gender][count-1] ++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of number of bi-years with a panel in 2003-2010 for uncensored control %s\n",gender_names[i]) ;
		for (int n=0; n<4; n++)
			printf("%d bi-years\t%d\t%.2f\n",n+1,bi_year_counts[i][n],(100.0*bi_year_counts[i][n])/total[i]) ;
		printf("\n") ;
	}

	// For Older subjects ...
	for (int i=0; i<2; i++) {
		total[i] = 0 ;
		memset(bi_year_counts[i],0,4*sizeof(int)) ;
	}

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;
		int gender = (demography[id].gender == 'M') ? 0 : 1 ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end() || demography[id].byear > 1950)
			continue ;

		memset(bi_year_flags,0,4*sizeof(int)) ;
		for (unsigned int i=0; i<cbc_dates[id].size(); i++) {
			int year = (int)((cbc_dates[id][i] - min_day)/365/2) ;
			if (year >= 0 && year < 4)
				bi_year_flags[year] = 1 ;
		}

		int count = 0 ;
		for (int year=0; year<4; year++) {
			if (bi_year_flags[year])
				count ++ ;
		}

		if (count > 0) {
			total[gender] ++ ;
			bi_year_counts[gender][count-1] ++ ;
		}
	}

	for (int i=0; i<2; i++) {
		printf("Histogram of number of bi-years with a panel in 2003-2010 for uncensored control %s born before 1950\n",gender_names[i]) ;
		for (int n=0; n<4; n++)
			printf("%d years\t%d\t%.2f\n",n+1,bi_year_counts[i][n],(100.0*bi_year_counts[i][n])/total[i]) ;
		printf("\n") ;
	}

	// Distribution of Values for Controls
	fprintf(stderr,"Values for Controls\n") ;
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

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		int gender = (demography[id].gender == 'M') ? 0 : 1 ;
		int bday = get_days(10000*demography[id].byear + 101) + 183 ;

		for (int i=0; i<cbc_dates[id].size(); i++) {
			int date = cbc_dates[id][i] ;
			int age_bin = (date - bday)/365/5 ;
			assert(age_bin < 40) ;

			for (map<int,double>::iterator it = cbcs[id][date].begin(); it != cbcs[id][date].end(); it++) {
				assert(codes.find(it->first) != codes.end()) ;
				int idx = codes[it->first] ;
				double value = it->second ;
				n[gender][age_bin][idx] ++ ;
				s[gender][age_bin][idx] += value ;
				s2[gender][age_bin][idx] += value*value;
			}
		}
	}

	for (int i=0; i<NTESTS; i++) {
		for (int gender=0; gender<2; gender++) {
			for (int age_bin=0; age_bin<40; age_bin++) {
				if (n[gender][age_bin][i] > 0) {
					double mean = s[gender][age_bin][i]/n[gender][age_bin][i] ;
					double sdv = (n[gender][age_bin][i]==1) ? 0 : sqrt((s2[gender][age_bin][i] - mean*s[gender][age_bin][i])/(n[gender][age_bin][i] - 1)) ;
					printf("Uncensored control: Test %s at ages %d-%d for %s : Mean = %.2f Standard-Devaition = %.2f N = %d\n",test_names[i],5*age_bin,5*(age_bin+1),
						gender_names[gender],mean,sdv,n[gender][age_bin][i]) ;
				}
			}
			printf("\n") ;
		}
	}

	// Distribution of Values for CRC
	fprintf(stderr,"Values for CRC\n") ;

	for (int i=0; i<2; i++) {
		for (int j=0; j<40; j++) {
			for (int k=0; k<NTESTS; k++) {
				n[i][j][k] = 0 ;
				s[i][j][k] = s2[i][j][k] = 0 ;
			}
		}
	}

	for (map<int,reg_entry>::iterator it = registry.begin(); it != registry.end(); it++) {
		int id = it->first ;

		if (it->second.type == 1 && cbc_dates.find(id) != cbc_dates.end() && cbc_dates[id][0] < it->second.date) {
			int idx = -1 ;
			for (unsigned int i=0; i<cbc_dates[id].size(); i++) {
				if (cbc_dates[id][i] >= it->second.date - 30)
					break ;
				if (cbc_dates[id][i] >= it->second.date - 270)
					idx = i ;
			}

			if (idx != -1) {
				int gender = (demography[id].gender == 'M') ? 0 : 1 ;
				int bday = get_days(10000*demography[id].byear + 101) + 183 ;
				int date = cbc_dates[id][idx] ;
				int age_bin = (date - bday)/365/5 ;
				assert(age_bin < 40) ;

				for (map<int,double>::iterator it = cbcs[id][date].begin(); it != cbcs[id][date].end(); it++) {
					assert(codes.find(it->first) != codes.end()) ;
					int idx = codes[it->first] ;
					double value = it->second ;
					n[gender][age_bin][idx] ++ ;
					s[gender][age_bin][idx] += value ;
					s2[gender][age_bin][idx] += value*value;
				}
			}
		}
	}

	for (int i=0; i<NTESTS; i++) {
		for (int gender=0; gender<2; gender++) {
			for (int age_bin=0; age_bin<40; age_bin++) {
				if (n[gender][age_bin][i] > 0) {
					double mean = s[gender][age_bin][i]/n[gender][age_bin][i] ;
					double sdv = (n[gender][age_bin][i]==1) ? 0 : sqrt((s2[gender][age_bin][i] - mean*s[gender][age_bin][i])/(n[gender][age_bin][i] - 1)) ;
					printf("CRC 1-9 months to registry: Test %s at ages %d-%d for %s : Mean = %.2f Standard-Devaition = %.2f N = %d\n",test_names[i],5*age_bin,5*(age_bin+1),
						gender_names[gender],mean,sdv,n[gender][age_bin][i]) ;
				}
			}
			printf("\n") ;
		}
	}

	// Histograms of Values for Controls
	fprintf(stderr,"Values for Controls: Histograms at 65-70\n") ;

	map<double,int> values[NTESTS][2] ;
	int ninds[NTESTS][2] ;
	for (int i=0; i<NTESTS; i++)
		ninds[i][0] = ninds[i][1] = 0 ;

	for (map<int,vector<int> >::iterator it = cbc_dates.begin(); it != cbc_dates.end(); it++) {
		int id = it->first ;

		if (good_subject.find(id) == good_subject.end() || registry.find(id) != registry.end())
			continue ;

		int gender = (demography[id].gender == 'M') ? 0 : 1 ;
		int bday = get_days(10000*demography[id].byear + 101) + 183 ;

		int taken[NTESTS] ;
		memset(taken,0,sizeof(taken)) ;

		for (int i=0; i<cbc_dates[id].size(); i++) {
			int date = cbc_dates[id][i] ;
			int age = (date - bday)/365 ;
			if (age < 65 || age > 70)
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

// Read Cancer registry and mark
int read_registry (char *file_name, map<int,reg_entry>& registry) {

	// Prepare
	map<string,int> crcs ;
	for (int i=0; i<NCRC_TYPES; i++)
		crcs[crc_types[i]] = 1 ;

	// Read 
	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file\n") ;
		return -1 ;
	}

	char buffer[BUFFER_SIZE] ;
	char field[MAX_STRING_LEN] ;
	char line[REGISTRY_NFIELDS][MAX_STRING_LEN] ;
	char *startbuf,*endbuf ;

	while(!(feof(fp))) {      
		fgets(buffer, sizeof(buffer), fp);
		if (feof(fp))
			break ;
			                
		startbuf = endbuf = buffer; 
		int ifield = 0 ;
		for( ;  ;  ) {
			if ((*endbuf == '\n') || (*endbuf == '\r') || (*endbuf == ',')) {
				strncpy(field, startbuf, endbuf-startbuf);                     
				field[endbuf-startbuf]='\0';

				ifield++ ;
				if (ifield > REGISTRY_NFIELDS) {
					fprintf(stderr,"Could not read file\n") ;
					return -1 ;
				}
					
				strncpy(line[ifield-1],field,MAX_STRING_LEN) ;
				line[ifield-1][MAX_STRING_LEN-1] = '\0' ;
				startbuf=endbuf+1 ;
			}

			if ((*endbuf == '\n') || (*endbuf == '\r'))
				break ;                      
			endbuf++;
		}

		if (strcmp(line[0],"NUMERATOR") != 0) {
			char cancer_type[MAX_STRING_LEN] ;
			sprintf(cancer_type,"%s,%s,%s",line[REGISTRY_CANCER_FIELD],line[REGISTRY_CANCER_FIELD+1],line[REGISTRY_CANCER_FIELD+2]) ;

			int day,month,year ;
			if (sscanf(line[REGISTRY_DATE_FIELD],"%d/%d/%d",&month,&day,&year) != 3) {
				fprintf(stderr,"Could not parse date %s\n",line[REGISTRY_DATE_FIELD]) ;
				return -1 ;
			}
			int days = get_days(day + 100*month + 10000*year) ;
			int id = atoi(line[REGISTRY_ID_FIELD]) ;

			if (crcs.find(cancer_type) != crcs.end()) { // CRC
				if (registry.find(id) == registry.end() || registry[id].type == 0 || days < registry[id].date) {
					registry[id].type = 1 ;
					registry[id].date = days ;
				}
			} else { // NON CRC
				if (registry.find(id) == registry.end() || (registry[id].type == 0 && days < registry[id].date)) {
					registry[id].type = 0 ;
					registry[id].date = days ;
				}
			}
		}
	}
	
	fclose(fp) ;
	return 0 ;
}

// Read censor
int read_censor(char *file_name ,map<int,status>& censor) {

	FILE *fp = fopen(file_name,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Could not open file \'%s\' for reading\n",file_name) ;
		return -1 ;
	}

	// Read status
	int id ;
	int date,stat,reason ;

	while (! feof(fp)) {
		int rc = fscanf(fp,"%d %d %d %d\n",&id,&stat,&reason,&date) ;
		if (rc == EOF)
			break ;

		if (rc != 4) {
			fprintf(stderr,"Could not read status line from \'%s\'. rc = %d\n",file_name,rc) ;
			return -1 ;
		}

		status new_status ;
		new_status.date = get_days(date) ;
		new_status.reason = reason ;
		new_status.stat = stat ;
		censor[id] = new_status ;
	}

	fclose(fp) ;
	return 0 ;
}

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
int read_cbcs(char *file_name, cbcs_data& cbcs) {

	// Prepare
	map<int,int> codes ;
	for (int i=0; i<NTESTS; i++)
		codes[test_codes[DATA_TYPE][i]] = 1 ;

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