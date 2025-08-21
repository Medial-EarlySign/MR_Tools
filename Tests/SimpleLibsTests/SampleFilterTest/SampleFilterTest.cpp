#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "Logger/Logger/Logger.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#include "SampleFilterTest.h"

#include <fenv.h>
#ifndef  __unix__
#pragma float_control( except, on )
#endif

int main(int argc, char *argv[])
{

#if defined(__unix__)
	feenableexcept(FE_DIVBYZERO | FE_INVALID | FE_OVERFLOW);
#endif

	int rc = 0;
	po::variables_map vm;

	MedTimer timer;
	timer.start();

	// Running Parameters
	MLOG("Reading params\n");
	rc = read_run_params(argc, argv, vm);
	assert(rc >= 0);

	if (vm.count("mimic")) {
		global_default_time_unit = global_default_windows_time_unit = MedTime::Minutes;
	}

	// Read Signals
	MLOG("Reading signals\n");

	vector<string> signals;
	rc = read_signals_list(vm, signals);
	assert(rc >= 0);

	// Read Samples
	MLOG("Reading samples\n");

	MedSamples allSamples;
	get_samples(vm, allSamples);
	vector<int> ids;
	allSamples.get_ids(ids);

	// Read Repository
	MLOG("Initializing repository\n");

	MedPidRepository rep;
	vector<string> read_sigs = signals;
	if (vm.count("drug_feats")) read_sigs.push_back("Drug");
	rc = read_repository(vm["config"].as<string>(), ids, read_sigs, rep);
	assert(rc >= 0);

	if (vm.count("mimic")) {
//		testAgeMatch2(rep, allSamples);
//		testGenderMatch2(rep, allSamples);
//		testTimeMatch2(allSamples);
//		testAgeAndGenderMatch2(rep, allSamples);
//		testCeatinineMatch2(rep, allSamples);
		testCeatinineAndAgeMatch2(rep, allSamples);

	}
	else {
//		testAgeMatch1(rep, allSamples);
//		testGenderMatch1(rep, allSamples);
//		testTimeMatch1(allSamples);
//		testAgeAndGenderMatch1(rep, allSamples);
		testCeatinineMatch1(rep, allSamples);
		testCeatinineMatchAfterFiltering(rep, allSamples);
//		testCeatinineAndAgeMatch1(rep, allSamples);
	}

	return 0;
}

// Test Functinos
void testAgeMatch1(MedRepository& rep, MedSamples& samples) {

	vector<string> initStrings = { "strata=age","strata=age,5" };
	vector<int> ageRes = { 1,5 };

	int rc;
	for (string& initString : initStrings) {

		// Match
		SampleFilter *filter = new MatchingSampleFilter;
		rc = filter->init_from_string(initString);
		assert(rc == 0);

		MedSamples matchedSamples;
		rc = filter->filter(rep, samples, matchedSamples);
		assert(rc == 0);

		for (int ageResCheck : ageRes) {

			// Test
			map<int, map<float, int>> counters;
			int sid = rep.dict.id("BYEAR");
			int len;

			for (auto& idSample : matchedSamples.idSamples) {
				int byear = (int)((SVal *)rep.get(idSample.id, sid, len))[0].val;

				for (auto& sample : idSample.samples) {
					int age_bin = (sample.time / 10000 - byear) / ageResCheck;
					counters[age_bin][sample.outcome] ++;
				}
			}

			// Print
			fprintf(stderr, "match age by %s and check by %d years:\n", initString.c_str(), ageResCheck);
			for (auto& rec : counters) {
				cerr << rec.first;
				for (auto& cnt : rec.second) {
					float r = (rec.second[1] !=0) ? (cnt.second + 0.0) / rec.second[1] :-1.0;
					fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
				}
				cerr << endl;
			}
			cerr << endl;
		}
	}
}

void testAgeMatch2(MedRepository& rep, MedSamples& samples) {

	vector<string> initStrings = { "strata=age","strata=age,5" };
	vector<int> ageRes = { 1,5 };

	int rc;
	for (string& initString : initStrings) {

		// Match
		SampleFilter *filter = new MatchingSampleFilter;
		rc = filter->init_from_string(initString);
		assert(rc == 0);

		MedSamples matchedSamples;
		rc = filter->filter(rep, samples, matchedSamples);
		assert(rc == 0);

		for (int ageResCheck : ageRes) {

			// Test
			map<int, map<float, int>> counters;
			int sid = rep.dict.id("Age");
			int len;

			for (auto& idSample : matchedSamples.idSamples) {
				int age = (int)((STimeVal *)rep.get(idSample.id, sid, len))[0].val;
				int age_bin = age / ageResCheck;

				for (auto& sample : idSample.samples)
					counters[age_bin][sample.outcome] ++;
			}

			// Print
			fprintf(stderr, "match age by %s and check by %d years:\n", initString.c_str(), ageResCheck);
			for (auto& rec : counters) {
				cerr << rec.first;
				for (auto& cnt : rec.second) {
					float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
					fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
				}
				cerr << endl;
			}
			cerr << endl;
		}
	}
}


void testGenderMatch1(MedRepository& rep, MedSamples& samples) {


	vector<string> initStrings = { "strata=gender","strata=signal,GENDER,1.0" };

	// Match
	int rc;
	for (string& initString : initStrings) {
	
		SampleFilter *filter = new MatchingSampleFilter;
		rc = filter->init_from_string(initString);
		assert(rc == 0);

		MedSamples matchedSamples;
		rc = filter->filter(rep, samples, matchedSamples);
		assert(rc == 0);

		// Test
		map<int, map<float, int>> counters;
		int sid = rep.dict.id("GENDER");
		int len;

		for (auto& idSample : matchedSamples.idSamples) {
			int gender = (int)((SVal *)rep.get(idSample.id, sid, len))[0].val;

			for (auto& sample : idSample.samples) 
				counters[gender][sample.outcome] ++;
		}

		// Print
		fprintf(stderr, "match gender by %s:\n",initString.c_str());
		for (auto& rec : counters) {
			cerr << rec.first;
			for (auto& cnt : rec.second) {
				float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
				fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
			}
			cerr << endl;
		}
		cerr << endl;
	}
}

void testGenderMatch2(MedRepository& rep, MedSamples& samples) {

	vector<string> initStrings = { "strata=gender","strata=signal,Gender,1.0,999999,minutes" };

	// Match
	int rc;
	for (string& initString : initStrings) {

		SampleFilter *filter = new MatchingSampleFilter;
		rc = filter->init_from_string(initString);
		assert(rc == 0);

		MedSamples matchedSamples;
		rc = filter->filter(rep, samples, matchedSamples);
		assert(rc == 0);

		// Test
		map<int, map<float, int>> counters;
		int sid = rep.dict.id("Gender");
		int len;

		for (auto& idSample : matchedSamples.idSamples) {
			int gender = (int)((STimeVal *)rep.get(idSample.id, sid, len))[0].val;

			for (auto& sample : idSample.samples)
				counters[gender][sample.outcome] ++;
		}

		// Print
		fprintf(stderr, "match gender by %s:\n", initString.c_str());
		for (auto& rec : counters) {
			cerr << rec.first;
			for (auto& cnt : rec.second) {
				float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
				fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
			}
			cerr << endl;
		}
		cerr << endl;
	}
}


void testTimeMatch1(MedSamples& samples) {
	
	vector<string> initStrings = { "strata=time,month,2","strata=time,year" };

	// Match
	int rc;
	for (string& initString : initStrings) {

		SampleFilter *filter = new MatchingSampleFilter;
		rc = filter->init_from_string(initString);
		assert(rc == 0);

		MedSamples matchedSamples;
		rc = filter->filter(samples, matchedSamples);
		assert(rc == 0);

		// Test
		map<int, map<float, int>> annual_counters;
		map<int, map<float, int>> bi_monthly_counters;

		for (auto& idSample : matchedSamples.idSamples) {
			for (auto& sample : idSample.samples) {
				int time = sample.time;
				annual_counters[time / 10000][sample.outcome] ++;
				bi_monthly_counters[(1 + time / 100)/2][sample.outcome] ++;
			}
		}

		// Print
		fprintf(stderr, "match by %s, check by year:\n", initString.c_str());
		for (auto& rec : annual_counters) {
			cerr << rec.first;
			for (auto& cnt : rec.second) {
				float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
				fprintf(stderr, "\t%.0f:%d:%.3f", cnt.first, cnt.second, r);
			}
			cerr << endl;
		}
		cerr << endl;
		
		fprintf(stderr, "match by %s, check by 2-months:\n", initString.c_str());
		for (auto& rec : bi_monthly_counters) {
			cerr << rec.first;
			for (auto& cnt : rec.second) {
				float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
				fprintf(stderr, "\t%.0f:%d:%.3f", cnt.first, cnt.second, r);
			}
			cerr << endl;
		}
		cerr << endl;
		
	}
}

void testTimeMatch2(MedSamples& samples) {

	vector<string> initStrings = { "strata=time,year","strata=time,days,100" };

	// Match
	int rc;
	for (string& initString : initStrings) {

		SampleFilter *filter = new MatchingSampleFilter;
		rc = filter->init_from_string(initString);
		assert(rc == 0);

		MedSamples matchedSamples;
		rc = filter->filter(samples, matchedSamples);
		assert(rc == 0);

		// Test
		map<int, map<float, int>> annual_counters;
		map<int, map<float, int>> daily_counter;

		for (auto& idSample : matchedSamples.idSamples) {
			for (auto& sample : idSample.samples) {
				int year = med_time_converter.convert_times(MedTime::Minutes, MedTime::Years, sample.time);
				int day = med_time_converter.convert_times(MedTime::Minutes, MedTime::Days, sample.time);
				annual_counters[year][sample.outcome] ++;
				daily_counter[day/ 100][sample.outcome] ++;
			}
		}

		// Print
		fprintf(stderr, "match by %s, check by year:\n", initString.c_str());
		for (auto& rec : annual_counters) {
			cerr << rec.first;
			for (auto& cnt : rec.second) {
				float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
				fprintf(stderr, "\t%.0f:%d:%.3f", cnt.first, cnt.second, r);
			}
			cerr << endl;
		}
		cerr << endl;

		fprintf(stderr, "match by %s, check by 100-days:\n", initString.c_str());
		for (auto& rec : daily_counter) {
			cerr << rec.first;
			for (auto& cnt : rec.second) {
				float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
				fprintf(stderr, "\t%.0f:%d:%.3f", cnt.first, cnt.second, r);
			}
			cerr << endl;
		}
		cerr << endl;

	}
}


void testAgeAndGenderMatch1(MedRepository& rep, MedSamples& samples) {


	SampleFilter *filter = new MatchingSampleFilter;
	int rc = filter->init_from_string("strata=age:gender");
	assert(rc == 0);

	MedSamples matchedSamples;
	rc = filter->filter(rep, samples, matchedSamples);
	assert(rc == 0);

	// Test
	map<string, map<float, int>> counters;
	int genderSid = rep.dict.id("GENDER");
	int byearSid = rep.dict.id("BYEAR");
	int len;

	for (auto& idSample : matchedSamples.idSamples) {
		int gender = (int)((SVal *)rep.get(idSample.id, genderSid, len))[0].val;
		int byear = (int)((SVal *)rep.get(idSample.id, byearSid, len))[0].val;

		for (auto& sample : idSample.samples)
			counters[to_string(gender) + "X" + to_string(sample.time / 10000 - byear)][sample.outcome] ++;
	}

		// Print
	fprintf(stderr, "match age X gender\n");
	for (auto& rec : counters) {
		cerr << rec.first;
		for (auto& cnt : rec.second) {
			float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
			fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
		}
		cerr << endl;
	}
}

void testAgeAndGenderMatch2(MedRepository& rep, MedSamples& samples) {

	SampleFilter *filter = new MatchingSampleFilter;
	int rc = filter->init_from_string("strata=age:gender");
	assert(rc == 0);

	MedSamples matchedSamples;
	rc = filter->filter(rep, samples, matchedSamples);
	assert(rc == 0);

	// Test
	map<string, map<float, int>> counters;
	int genderSid = rep.dict.id("Gender");
	int ageSid = rep.dict.id("Age");
	int len;

	for (auto& idSample : matchedSamples.idSamples) {
		int age = (int)((STimeVal *)rep.get(idSample.id, ageSid, len))[0].val;
		int gender = (int)((STimeVal *)rep.get(idSample.id, genderSid, len))[0].val;

		for (auto& sample : idSample.samples)
			counters[to_string(gender) + "X" + to_string(age)][sample.outcome] ++;
	}

	// Print
	fprintf(stderr, "match age X gender\n");
	for (auto& rec : counters) {
		cerr << rec.first;
		for (auto& cnt : rec.second) {
			float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
			fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
		}
		cerr << endl;
	}
}


void testCeatinineMatch1(MedRepository& rep, MedSamples& samples) {

	SampleFilter *filter = new MatchingSampleFilter;
	string initString = "strata=signal,Creatinine,0.2,180";
	int rc = filter->init_from_string(initString);
	assert(rc == 0);

	MedSamples matchedSamples;
	rc = filter->filter(rep, samples, matchedSamples);
	assert(rc == 0);

	// Test
	map<string, map<float, int>> counters;
	int sid = rep.dict.id("Creatinine"); assert(sid != -1);
	int len;

	char bin[10];
	for (auto& idSample : matchedSamples.idSamples) {
		SDateVal *sig = (SDateVal *)rep.get(idSample.id, sid, len);
		for (auto& sample : idSample.samples) {
			int minDate = med_time_converter.convert_days(MedTime::Date, med_time_converter.convert_date(MedTime::Days, sample.time) - 180);

			sprintf(bin, "NULL");
			for (int idx = 0; idx < len; idx++) {
				if (sig[idx].date > sample.time) {
					if (idx > 0 && sig[idx - 1].date >= minDate)
						sprintf(bin, "%02d", (int)(sig[idx-1].val / 0.2 + 0.001));
					break;
				}
			}

			if (len>0 && sig[len-1].date <=  sample.time && sig[len-1].date >= minDate)
				sprintf(bin, "%02d", (int)(sig[len-1].val / 0.2 + 0.001));

			counters[string(bin)][sample.outcome] ++;
		}
	}


	// Print
	fprintf(stderr, "match by %s:\n", initString.c_str());
	for (auto& rec : counters) {
		cerr << rec.first;
		for (auto& cnt : rec.second) {
			float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
			fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
		}
		cerr << endl;
	}
	cerr << endl;
}

void testCeatinineMatch2(MedRepository& rep, MedSamples& samples) {

	SampleFilter *filter = new MatchingSampleFilter;
	string initString = "strata=signal,CHARTLAB_Creatinine,0.2,720,minutes";
	int rc = filter->init_from_string(initString);
	assert(rc == 0);

	MedSamples matchedSamples;
	rc = filter->filter(rep, samples, matchedSamples);
	assert(rc == 0);

	// Test
	map<string, map<float, int>> counters;
	int sid = rep.dict.id("CHARTLAB_Creatinine"); assert(sid != -1);
	int len;

	char bin[10];
	for (auto& idSample : matchedSamples.idSamples) {
		STimeVal *sig = (STimeVal *)rep.get(idSample.id, sid, len);
		for (auto& sample : idSample.samples) {
			int minTime = sample.time - 12 * 60;

			sprintf(bin, "NULL");
			for (int idx = 0; idx < len; idx++) {
				if (sig[idx].time > sample.time) {
					if (idx > 0 && sig[idx - 1].time >= minTime)
						sprintf(bin, "%04d", (int)(sig[idx - 1].val / 0.2 + 0.001));
					break;
				}
			}

			if (len>0 && sig[len - 1].time <= sample.time && sig[len - 1].time >= minTime)
				sprintf(bin, "%04d", (int)(sig[len - 1].val / 0.2 + 0.001));

			counters[string(bin)][sample.outcome] ++;
		}
	}


	// Print
	fprintf(stderr, "match by %s:\n", initString.c_str());
	for (auto& rec : counters) {
		cerr << rec.first;
		for (auto& cnt : rec.second) {
			float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
			fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
		}
		cerr << endl;
	}
	cerr << endl;
}


void testCeatinineAndAgeMatch1(MedRepository& rep, MedSamples& samples) {

	SampleFilter *filter = new MatchingSampleFilter;
	string initString = "strata=signal,Creatinine,0.5,90,days:age,2";
	int rc = filter->init_from_string(initString);
	assert(rc == 0);

	MedSamples matchedSamples;
	rc = filter->filter(rep, samples, matchedSamples);
	assert(rc == 0);

	// Test
	map<string, map<float, int>> counters;
	int sid = rep.dict.id("Creatinine");
	int byearId = rep.dict.id("BYEAR");
	int len, byearLen;

	char bin[20];
	for (auto& idSample : matchedSamples.idSamples) {
		SDateVal *sig = (SDateVal *)rep.get(idSample.id, sid, len);
		int byear = ((SVal *)rep.get(idSample.id, byearId, byearLen))[0].val;

		for (auto& sample : idSample.samples) {
			int minDate = med_time_converter.convert_days(MedTime::Date, med_time_converter.convert_date(MedTime::Days, sample.time) - 90);

			sprintf(bin, "%03dXNULL", (sample.time / 10000 - byear) / 2);
			for (int idx = 0; idx < len; idx++) {
				if (sig[idx].date > sample.time) {
					if (idx > 0 && sig[idx - 1].date >= minDate)
						sprintf(bin, "%03dX%02d", (sample.time / 10000 - byear) / 2, (int)(sig[idx - 1].val / 0.5 + 0.001));
					break;
				}
			}

			if (len>0 && sig[len - 1].date <= sample.time && sig[len - 1].date >= minDate)
				sprintf(bin, "%03dX%02d", (sample.time / 10000 - byear) / 2,(int)(sig[len - 1].val / 0.5 + 0.001));

			counters[string(bin)][sample.outcome] ++;
		}
	}


	// Print
	fprintf(stderr, "match by %s:\n", initString.c_str());
	for (auto& rec : counters) {
		float minCount = -1;
		for (auto& cnt : rec.second) {
			if (minCount == -1 || cnt.second < minCount)
				minCount = cnt.second;
		}

		if (minCount > 100) {
			cerr << rec.first;
			for (auto& cnt : rec.second) {
				float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
				fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
			}
			cerr << endl;
		}
	}
	cerr << endl;
}

void testCeatinineAndAgeMatch2(MedRepository& rep, MedSamples& samples) {

	SampleFilter *filter = new MatchingSampleFilter;
	string initString = "strata=signal,CHARTLAB_Creatinine,0.5,600:age,2";
	int rc = filter->init_from_string(initString);
	assert(rc == 0);

	MedSamples matchedSamples;
	rc = filter->filter(rep, samples, matchedSamples);
	assert(rc == 0);

	// Test
	map<string, map<float, int>> counters;
	int sid = rep.dict.id("CHARTLAB_Creatinine");
	int ageSid = rep.dict.id("Age");
	int len, ageLen;

	char bin[20];
	for (auto& idSample : matchedSamples.idSamples) {
		STimeVal *sig = (STimeVal *)rep.get(idSample.id, sid, len);
		int age = ((STimeVal *)rep.get(idSample.id, ageSid, ageLen))[0].val;

		for (auto& sample : idSample.samples) {
			int minTime = sample.time - 600;

			sprintf(bin, "%03dXNULL", age / 2);
			for (int idx = 0; idx < len; idx++) {
				if (sig[idx].time > sample.time) {
					if (idx > 0 && sig[idx - 1].time >= minTime)
						sprintf(bin, "%03dX%02d", age / 2, (int)(sig[idx - 1].val / 0.5 + 0.001));
					break;
				}
			}

			if (len>0 && sig[len - 1].time <= sample.time && sig[len - 1].time >= minTime)
				sprintf(bin, "%03dX%02d", age/2, (int)(sig[len - 1].val / 0.5 + 0.001));

			counters[string(bin)][sample.outcome] ++;
		}
	}


	// Print
	fprintf(stderr, "match by %s:\n", initString.c_str());
	for (auto& rec : counters) {
		float minCount = -1;
		for (auto& cnt : rec.second) {
			if (minCount == -1 || cnt.second < minCount)
				minCount = cnt.second;
		}

		if (minCount > 100) {
			cerr << rec.first;
			for (auto& cnt : rec.second) {
				float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
				fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
			}
			cerr << endl;
		}
	}
	cerr << endl;
}

void testCeatinineMatchAfterFiltering(MedRepository& rep, MedSamples& samples) {

	SampleFilter *filter = SampleFilter::make_filter(SMPL_FILTER_REQ_SIGNAL, "signalName=Creatinine;timeWindow=180");
	assert(filter != NULL);
	MedSamples filteredSamples;
	int rc = filter->filter(rep, samples, filteredSamples);
	assert(rc == 0);

	string initString = "strata=signal,Creatinine,0.2,180";
	SampleFilter *matcher = SampleFilter::make_filter(SMPL_FILTER_MATCH, initString);
	assert(filter != NULL);

	MedSamples matchedSamples;
	rc = matcher->filter(rep, filteredSamples, matchedSamples);
	assert(rc == 0);

	// Test
	map<string, map<float, int>> counters;
	int sid = rep.dict.id("Creatinine"); assert(sid != -1);
	int len;

	char bin[10];
	for (auto& idSample : matchedSamples.idSamples) {
		SDateVal *sig = (SDateVal *)rep.get(idSample.id, sid, len);
		for (auto& sample : idSample.samples) {
			int minDate = med_time_converter.convert_days(MedTime::Date, med_time_converter.convert_date(MedTime::Days, sample.time) - 180);

			sprintf(bin, "NULL");
			for (int idx = 0; idx < len; idx++) {
				if (sig[idx].date > sample.time) {
					if (idx > 0 && sig[idx - 1].date >= minDate)
						sprintf(bin, "%02d", (int)(sig[idx - 1].val / 0.2 + 0.001));
					break;
				}
			}

			if (len>0 && sig[len - 1].date <= sample.time && sig[len - 1].date >= minDate)
				sprintf(bin, "%02d", (int)(sig[len - 1].val / 0.2 + 0.001));

			counters[string(bin)][sample.outcome] ++;
		}
	}


	// Print
	fprintf(stderr, "match by %s:\n", initString.c_str());
	for (auto& rec : counters) {
		cerr << rec.first;
		for (auto& cnt : rec.second) {
			float r = (rec.second[1] != 0) ? (cnt.second + 0.0) / rec.second[1] : -1.0;
			fprintf(stderr, "\t%.1f:%d:%.3f", cnt.first, cnt.second, r);
		}
		cerr << endl;
	}
	cerr << endl;
}


// Functions 
// Analyze Command Line
int read_run_params(int argc, char *argv[], po::variables_map& vm) {
	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("config", po::value<string>()->required(), "repository file name")
			("ids", po::value<string>(), "file of ids to consider")
			("samples", po::value<string>()->required(), "samples file name")
			("sigs", po::value<string>()->default_value("NONE"), "list of signals to consider")
			("features", po::value<string>()->default_value("NONE"), "file of signals to consider")
			("mimic", "work on mimic data");
			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);

		MLOG("=========================================================================================\n");
		MLOG("Command Line:");
		for (int i = 0; i<argc; i++) MLOG(" %s", argv[i]);
		MLOG("\n");
		MLOG("..........................................................................................\n");
	}
	catch (exception& e) {
		cerr << "error: " << e.what() << "; run with --help for usage information\n";
		return -1;
	}
	catch (...) {
		cerr << "Exception of unknown type!\n";
		return -1;
	}

	return 0;
}

int read_repository(string config_file, vector<int>& ids, vector<string>& signals, MedPidRepository& rep) {

	vector<string> sigs = signals;

	sigs.push_back("BYEAR");


	MLOG("Before reading config file %s\n", config_file.c_str());


	if (rep.read_all(config_file, ids, sigs) < 0) {
		MLOG("Cannot init repository %s\n", config_file.c_str());
		return -1;
	}

	size_t nids = rep.index.pids.size();
	size_t nsigs = rep.index.signals.size();
	MLOG("Read %d Ids and %d signals\n", (int)nids, (int)nsigs);

	return 0;
}

int read_signals_list(po::variables_map& vm, vector<string>& signals) {

	string sigs = vm["sigs"].as<string>();
	if (sigs != "NONE") {
		signals.clear();
		boost::split(signals, sigs, boost::is_any_of(","));
		return 0;
	}

	string file_name = vm["features"].as<string>();
	if (file_name == "NONE")
		return 0;

	ifstream inf(file_name);

	if (!inf) {
		MLOG("Cannot open %s for reading\n", file_name.c_str());
		return -1;
	}

	string curr_line;
	while (getline(inf, curr_line)) {
		if (curr_line[curr_line.size() - 1] == '\r')
			curr_line.erase(curr_line.size() - 1);

		if (curr_line[0] != '#')
			signals.push_back(curr_line);
	}

	return 0;
}

int read_ids_list(po::variables_map& vm, vector<int>& ids) {

	string file_name = vm["ids"].as<string>();
	ifstream inf(file_name);

	if (!inf) {
		MLOG("Cannot open %s for reading\n", file_name.c_str());
		return -1;
	}

	string curr_line;
	while (getline(inf, curr_line)) {
		if (curr_line[curr_line.size() - 1] == '\r')
			curr_line.erase(curr_line.size() - 1);

		ids.push_back(stoi(curr_line));
	}

	return 0;
}

int get_samples(po::variables_map& vm, MedSamples& samples) {

	string file_name = vm["samples"].as<string>();
	return samples.read_from_file(file_name);
}
