#define _CRT_SECURE_NO_WARNINGS

#include "CommonLib/common_header.h"
using namespace std;

int main(int argc, char *argv[]) {

	if (argc != 5 && argc != 4) {
		fprintf(stderr,"Usage : shift_preds.exe inPreds outPreds [origScore targetScore] OR [ShiftFile]\n") ;
		return -1;
	}
	
	gzFile fin = safe_gzopen(argv[1], "r");
	gzFile fout = safe_gzopen(argv[2], "wT");

	double origScore,targetScore ;
	if (argc == 5) {
		origScore = atof(argv[3]);
		targetScore = atof(argv[4]);
	} else {
		FILE *fs = safe_fopen(argv[3], "r");
		assert(fscanf(fs,"%lf %lf\n",&origScore,&targetScore) == 2) ;
		fclose(fs) ;
	}

	assert (origScore > 0.0 && origScore <= 100.0);
	assert (targetScore >= 0.0 && targetScore <= 100.0);

	double lowRatio = targetScore / origScore ;
	double highRatio = (100.0 - targetScore) / (100.0 - origScore) ;

	string lineStr;
	bool header = true;
	int  id, date;
	double score;

	while (gzGetLine(fin, lineStr) != NULL) { 
		if (header) {
			gzprintf(fout, "%s\n", lineStr.c_str());
			header = false;
			continue;
		}

		int rc = sscanf(lineStr.c_str(), "%d %d %lf", &id, &date, &score);
		assert(rc == 3);

		score = (score < origScore) ? 
			(lowRatio * score) : (targetScore + highRatio * (score - origScore));
		gzprintf(fout, "%d %d %.2f 0 0\n", id, date, score);
	}

	gzclose(fin) ;
	gzclose(fout) ;
	return 0;
}