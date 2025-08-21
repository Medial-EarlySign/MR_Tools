// Test MeScorer exception handling.

#include "CommonLib/CommonLib.h"
#include <windows.h>
#include <tchar.h>
#include <stdio.h>
#include <time.h>

#define WIDTH 7
#define DIV 1024

double values[] = {5.6,11.9,11.0,3,40.2,88.6,29.3,33.0,13.6,342,0.5,57.1,7.6,4.2,0.9,6.8,0.9,0.1,28.6,3.4} ;


#define _CRT_SECURE_NO_WARNINGS

int main(int argc, char *argv[]) {

 MEMORYSTATUSEX statex;

  statex.dwLength = sizeof (statex);

  GlobalMemoryStatusEx (&statex);

  _tprintf (TEXT("There is  %*ld percent of memory in use.\n"),
            WIDTH, statex.dwMemoryLoad);
  _tprintf (TEXT("There are %*I64d total KB of physical memory.\n"),
            WIDTH, statex.ullTotalPhys/DIV);
  _tprintf (TEXT("There are %*I64d free  KB of physical memory.\n"),
            WIDTH, statex.ullAvailPhys/DIV);
  _tprintf (TEXT("There are %*I64d total KB of paging file.\n"),
            WIDTH, statex.ullTotalPageFile/DIV);
  _tprintf (TEXT("There are %*I64d free  KB of paging file.\n"),
            WIDTH, statex.ullAvailPageFile/DIV);
  _tprintf (TEXT("There are %*I64d total KB of virtual memory.\n"),
            WIDTH, statex.ullTotalVirtual/DIV);
  _tprintf (TEXT("There are %*I64d free  KB of virtual memory.\n"),
            WIDTH, statex.ullAvailVirtual/DIV);

  // Show the amount of extended memory available.

  _tprintf (TEXT("There are %*I64d free  KB of extended memory.\n"),
            WIDTH, statex.ullAvailExtendedVirtual/DIV);

	if (argc != 2) {
		fprintf(stderr, "Usage: Tester[.exe] EngineDirectory\n");
		return -1;
	}

	// Parse Parameters
	string engineDir(argv[1]);

	// Initialize Engine
	clock_t tick1 = clock() ; 
	time_t time1 = time(NULL) ;

	int rc;
	ScorerSetUp setUpInfo;

	if ((rc = setUpInfo.setEngineDir(engineDir.c_str())) < 0) {
		fprintf(stderr, "Failed seting setup directory. rc = %d\n", rc);
		return -1;
	}

	MS_CRC_Scorer scorer;
	if ((rc = scorer.load(setUpInfo)) != 0) {
		fprintf(stderr, "Scorer SetUp failed. rc = %d\n", rc);
		return 100 + rc;
	}

	clock_t tick2 = clock() ;
	time_t time2 = time(NULL) ;
	fprintf(stderr,"Loading time: %f ; CPU: %f\n",double(time2-time1),double(tick2-tick1)/CLOCKS_PER_SEC) ;
	tick1 = clock() ; 
	time1 = time(NULL) ;

	// Data
	inData data ;
	data.BirthYear = 1966 ;
	data.Gender = 'F' ;
	for (int iDate = 1; iDate <= 12; iDate+=3) {
		int date = 20100000 + 100*iDate + 15 ;
		for (int iCode=0; iCode<20; iCode++) {
			ScorerBloodTest bloodTest ;
			bloodTest.Date = date ;
			bloodTest.Code = iCode ;
			bloodTest.Value = values[iCode] ;
			data.BloodTests.push_back(bloodTest) ;
		}
	}


	vector<ScorerBloodData *> allBloodData ;
	ScorerResult result ;

	int ii =0, jj = 0  ;
	while (jj < 500000*40) {
		jj ++ ;
		if (jj % 500000 == 0) {

		  GlobalMemoryStatusEx (&statex);

		  _tprintf (TEXT("There is  %*ld percent of memory in use.\n"),
					WIDTH, statex.dwMemoryLoad);
		  _tprintf (TEXT("There are %*I64d total KB of physical memory.\n"),
					WIDTH, statex.ullTotalPhys/DIV);
		  _tprintf (TEXT("There are %*I64d free  KB of physical memory.\n"),
					WIDTH, statex.ullAvailPhys/DIV);

		}

		try {
			ScorerBloodData  *newBloodData = new ScorerBloodData;
		
			// Allocate
			if ((newBloodData->Id = (char *) malloc(2)) == NULL) {
				fprintf(stderr, "Allocation failed int createBloodData\n");
				return -1; 
			}

			// Fill
			newBloodData->BirthYear = data.BirthYear;
			newBloodData->Gender = data.Gender;
			strcpy(newBloodData->Id, "1");

			int cnt = 0;
			for (unsigned int i = 0; i < data.BloodTests.size(); i++)
					newBloodData->BloodTests.push_back(data.BloodTests[i]);

			allBloodData.push_back(newBloodData) ;
//			if (scorer.calculate(*newBloodData,result) < 0)
//				return -1 ;
		} catch (...) {
			fprintf(stderr,"Problem handled outside\n") ;
			return -1 ;
		}
	}

	fprintf(stderr,"DONE\n") ;

}