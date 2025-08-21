// common functions for ite projects

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "common.h"

#ifndef  __unix__
#pragma float_control( except, on )
#endif

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

// Setting folds
void set_folds(int nFolds, MedSamples& samples, MedFeatures& inFeatures) {

	if (samples.idSamples.empty())
		set_folds(nFolds, inFeatures);
	else
		set_folds(nFolds, samples);
}
void set_folds(int nFolds, MedFeatures& inFeatures) {

	map<int, int> idFold;
	int counter = 0;

	for (int i = 0; i < inFeatures.samples.size(); i++) {
		int id = inFeatures.samples[i].id;
		if (idFold.find(id) == idFold.end()) {
			idFold[id] = counter % nFolds;
			counter++;
		}
		inFeatures.samples[i].split = idFold[id];
	}
}
void set_folds(int nFolds, MedSamples& samples) {

	for (int i = 0; i < samples.idSamples.size(); i++) {
		samples.idSamples[i].split = i % nFolds;
		for (auto& sample : samples.idSamples[i].samples)
			sample.split = samples.idSamples[i].split;
	}
}

// Read/Write text vectors
void read_vec(vector<float>& d, const string& fileName) {

	d.clear();

	ifstream inf(fileName);
	if (!inf)
		MTHROW_AND_ERR("Cannot open file %s for reading\n", fileName.c_str());

	string line;
	while (getline(inf, line)) {
		try
		{
			float val = boost::lexical_cast<float>(line);
			d.push_back(val);
		}
		catch (const boost::bad_lexical_cast) {
			MTHROW_AND_ERR("cannot parse \'%s\' as float\n", line.c_str());
		}
	}
}
void write_vec(vector<float>& d, const string& fileName) {

	ofstream outf(fileName);
	if (!outf)
		MTHROW_AND_ERR("Cannot open file %s for writing\n", fileName.c_str());

	for (float val : d)
		outf << val << "\n";
}

// Utilities for learn_from_features
int getNumFolds(MedFeatures& inFeatures) {

	set<int> folds;
	for (MedSample& sample : inFeatures.samples)
		folds.insert(sample.split);

	if (folds.find(-1) != folds.end())
		MTHROW_AND_ERR("Found sample with fold=-1. Maybe you should set nFolds\n");

	int maxFold = *folds.rbegin();
	for (int i = 0; i < maxFold; i++) {
		if (folds.find(i) == folds.end())
			MTHROW_AND_ERR("Cannot find fold #%d. Maybe you should set nFolds\n", i);
	}

	if (maxFold == 0)
		MTHROW_AND_ERR("Only one fold found. Maybe you should set nFolds\n");

	return maxFold + 1;

}
void split_matrix(MedFeatures& inFeatures, int iFold, MedFeatures& trainMatrix, MedFeatures& testMatrix) {

	MedFeatures *matrixPtrs[2] = { &trainMatrix, &testMatrix };

	// Prepare
	vector<string> features;
	inFeatures.get_feature_names(features);

	for (string& ftr : features) {
		trainMatrix.attributes[ftr] = inFeatures.attributes[ftr];
		testMatrix.attributes[ftr] = inFeatures.attributes[ftr];
		trainMatrix.data[ftr].clear();
		testMatrix.data[ftr].clear();
	}

	// Fill
	for (int i = 0; i < inFeatures.samples.size(); i++) {
		MedSample& sample = inFeatures.samples[i];
		int ptrIdx = (sample.split == iFold) ? 1 : 0;

		matrixPtrs[ptrIdx]->samples.push_back(sample);
		for (string& ftr : features)
			matrixPtrs[ptrIdx]->data[ftr].push_back(inFeatures.data[ftr][i]);

		if (!inFeatures.weights.empty())
			matrixPtrs[ptrIdx]->weights.push_back(inFeatures.weights[i]);
	}
}

// Cross Validation learning of a classification model
void learn_from_features(MedFeatures& inFeatures, vector<float>& preds, string& predictor, string& params, string& performanceFile, string& calParams, const string& name) {

	// Get nFolds
	int nFolds = getNumFolds(inFeatures);

	preds.resize(inFeatures.samples.size());
	vector<float> labels(preds.size());
	for (int iFold = 0; iFold < nFolds; iFold++) {
		cerr << name << " cross validation. Split " << iFold + 1 << " out of " << nFolds << "\n";

		// Split
		MedFeatures trainMatrix, testMatrix;
		split_matrix(inFeatures, iFold, trainMatrix, testMatrix);

		// Learn + predict
		MedPredictor *pred = MedPredictor::make_predictor(predictor, params);
		pred->learn(trainMatrix);
		pred->predict(testMatrix);

		//fill scores on relevant fold in preds:
		int test_smp_idx = 0;
		for (size_t i = 0; i < inFeatures.samples.size(); ++i) {
			if (inFeatures.samples[i].split == iFold) {
				preds[i] = testMatrix.samples[test_smp_idx].prediction[0];
				labels[i] = testMatrix.samples[test_smp_idx].outcome;
				test_smp_idx++;
			}
		}
	}

	// Performance
	vector<float> preds0 = preds;
	if (!performanceFile.empty())
		write_performance(preds, labels, performanceFile);

	// Calibration
	recalibrate(preds, labels, calParams);

	for (int i = 0; i < preds.size(); i++)
		cout << i << " " << preds0[i] << " " << preds[i] << " " << labels[i] << "\n";
}

void learn_from_samples(MedSamples& samples, vector<float>& preds, string& modelFile, vector<string>& modelAlts, string& repFile, string& performanceFile, string& calParams, 
	const string& name)
{

	int nFolds = getNumFolds(samples);

	// Read Model json
	cerr << name << ": Reading model" << endl;
	MedModel model;
	model.init_from_json_file_with_alterations(modelFile, modelAlts);
	model.verbosity = 0;

	// Read repository
	unordered_set<string> signalNamesSet;
	model.get_required_signal_names(signalNamesSet);
	vector<string> signalNames;
	for (string name : signalNamesSet)
		signalNames.push_back(name);

	vector<int> ids;
	samples.get_ids(ids);

	MLOG("Reading Repository\n");
	MedPidRepository rep;
	if (rep.read_all(repFile, ids, signalNames) != 0)
		MTHROW_AND_ERR("Read repository from %s failed\n", repFile.c_str());

	// Perform Cross validation
	preds.resize(samples.nSamples());
	vector<float> labels(preds.size());
	for (int iFold = 0; iFold < nFolds; iFold++) {
		MLOG("%s cross validation. Split %d out of %d\n", name.c_str(), iFold + 1, nFolds);

		// Split
		MedSamples trainSamples, testSamples;
		split_samples(samples, iFold, trainSamples, testSamples);

		// Learn + apply
		model.learn(rep, &trainSamples);
		model.apply(rep, testSamples);

		//fill scores on relevant fold in preds:
		int test_idx = 0 , out_idx = 0;
		for (int i = 0; i < samples.idSamples.size(); i++) {
			if (samples.idSamples[i].split == iFold) {
				for (auto& sample : testSamples.idSamples[test_idx].samples) {
					preds[out_idx] = sample.prediction[0];
					labels[out_idx] = sample.outcome;
					out_idx++;
				}
				test_idx++;
			}
			else
				out_idx += (int)samples.idSamples[i].samples.size();
		}
	}

	vector<float> preds0 = preds;
	if (!performanceFile.empty())
		write_performance(preds, labels, performanceFile);

	// Calibration
	recalibrate(preds, labels, calParams);

	for (int i = 0; i < preds.size(); i++)
		cout << i << " " << preds0[i] << " " << preds[i] << " " << labels[i] << "\n";
}


// Cross validation of a regression model
void regression_cross_validation_on_matrix(MedFeatures& inFeatures, int nFolds, string& predictorName, string& predictorParams, string& runDir, string& outFileName,
	vector<float>& preds, vector<float>& labels) {
	
	for (int iFold = 0; iFold < nFolds; iFold++) {
		cerr << "regression cross validation. Split " << iFold + 1 << " out of " << nFolds << "\n";

		// Split
		MedFeatures trainMatrix, testMatrix;
		split_matrix(inFeatures, iFold, trainMatrix, testMatrix);

		// Learn + predict
		if (boost::algorithm::ends_with(predictorName, ".py")) {
			// Run Python scripts 
			trainMatrix.weights.assign(trainMatrix.samples.size(), 1.0);
			learn_nn_model(trainMatrix, predictorName, predictorParams, runDir, outFileName);
			apply_nn_model(testMatrix, predictorName, predictorParams, runDir, outFileName);
		}
		else {
			// Learn and Predict
			MedPredictor *predictor = MedPredictor::make_predictor(predictorName, predictorParams);
			predictor->learn(trainMatrix);
			predictor->predict(testMatrix);
		}

		//fill scores on relevant fold in preds:
		int test_smp_idx = 0;
		for (size_t i = 0; i < inFeatures.samples.size(); ++i) {
			if (inFeatures.samples[i].split == iFold) {
				preds[i] = testMatrix.samples[test_smp_idx].prediction[0];
				labels[i] = testMatrix.samples[test_smp_idx].outcome;
				test_smp_idx++;
			}
		}
	}
}

void regression_cross_validation_on_samples(MedSamples& inSamples, vector<float>& weights, MedModel& model, MedPidRepository& rep, int nFolds, string& predictorName, string& predictorParams, 
	string& runDir, string& outFileName, vector<float>& preds, vector<float>& labels) {

	for (int iFold = 0; iFold < nFolds; iFold++) {
		MLOG("regression cross validation. Split %d out of %d\n", iFold + 1, nFolds);

		// Split
		MedSamples trainSamples, testSamples;
		vector<float> trainWeights, testWeights;
		split_samples(inSamples, iFold, trainSamples, testSamples, weights, trainWeights, testWeights);

		// Learn 
		model.learn(rep, &trainSamples, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS);
		model.features.weights = trainWeights;
		if (boost::algorithm::ends_with(predictorName, ".py"))
			learn_nn_model(model.features, predictorName, predictorParams, runDir, outFileName);
		else
			model.learn(rep, &trainSamples, MED_MDL_LEARN_PREDICTOR, MED_MDL_END);

		// Apply
		model.apply(rep, testSamples, MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_APPLY_FTR_PROCESSORS);
		if (boost::algorithm::ends_with(predictorName, ".py")) {
			apply_nn_model(model.features, predictorName, predictorParams, runDir, outFileName);
			model.apply(rep, testSamples, MED_MDL_INSERT_PREDS, MED_MDL_END);
		}
		else
			model.apply(rep, testSamples, MED_MDL_APPLY_PREDICTOR, MED_MDL_END);

		//fill scores on relevant fold in preds:
		size_t test_idx = 0, out_idx = 0;
		for (int i = 0; i < inSamples.idSamples.size(); i++) {
			if (inSamples.idSamples[i].split == iFold) {
				for (auto& sample : testSamples.idSamples[test_idx].samples) {
					preds[out_idx] = sample.prediction[0];
					labels[out_idx] = sample.outcome;
					out_idx++;
				}
				test_idx++;
			}
			else
				out_idx += inSamples.idSamples[i].samples.size();
		}
	}
}

// Utilities for learn_from_samples
int getNumFolds(MedSamples& samples) {

	set<int> folds;
	for (MedIdSamples& idSamples : samples.idSamples)
		folds.insert(idSamples.split);

	if (folds.find(-1) != folds.end())
		MTHROW_AND_ERR("Found sample with fold=-1. Maybe you should set nFolds\n");

	int maxFold = *folds.rbegin();
	for (int i = 0; i < maxFold; i++) {
		if (folds.find(i) == folds.end())
			MTHROW_AND_ERR("Cannot find fold #%d. Maybe you should set nFolds\n", i);
	}

	if (maxFold == 0)
		MTHROW_AND_ERR("Only one fold found. Maybe you should set nFolds\n");

	return maxFold + 1;
}
void split_samples(MedSamples& samples, int iFold, MedSamples& trainSamples, MedSamples& testSamples) {
	for (MedIdSamples& idSamples : samples.idSamples) {
		if (idSamples.split == iFold)
			testSamples.idSamples.push_back(idSamples);
		else
			trainSamples.idSamples.push_back(idSamples);
	}
}
void split_samples(MedSamples& samples, int iFold, MedSamples& trainSamples, MedSamples& testSamples,vector<float>& weights, vector<float>& trainWeights, vector<float>& testWeights) {

	size_t wIdx = 0;
	for (MedIdSamples& idSamples : samples.idSamples) {
		if (idSamples.split == iFold) {
			testSamples.idSamples.push_back(idSamples);
			for (int i = 0; i < idSamples.samples.size(); i++)
				testWeights.push_back(weights[wIdx + i]);
		}
		else {
			trainSamples.idSamples.push_back(idSamples);
			for (int i = 0; i < idSamples.samples.size(); i++)
				trainWeights.push_back(weights[wIdx + i]);
		}
		wIdx += idSamples.samples.size();
	}
}

void g_comp_split_samples(MedSamples& samples, int iFold, MedSamples& trainSamples, MedSamples& testSamples, vector<float>& preds, vector<float>& trainPreds, vector<float>& testPreds) {

	int nSamples = samples.nSamples();
	if (preds.size() != 2 * nSamples)
		MTHROW_AND_ERR("Predictions are not twice the size of samples. Quitting");

	vector<float> extraTestPreds, extraTrainPreds;

	size_t wIdx = 0;
	for (MedIdSamples& idSamples : samples.idSamples) {
		if (idSamples.split == iFold) {
			testSamples.idSamples.push_back(idSamples);
			for (int i = 0; i < idSamples.samples.size(); i++) {
				testPreds.push_back(preds[wIdx + i]);
				extraTestPreds.push_back(preds[nSamples + wIdx + i]);
			}
		}
		else {
			trainSamples.idSamples.push_back(idSamples);
			for (int i = 0; i < idSamples.samples.size(); i++) {
				trainPreds.push_back(preds[wIdx + i]);
				extraTrainPreds.push_back(preds[nSamples + wIdx + i]);
			}
		}
		wIdx += idSamples.samples.size();
	}

	testPreds.insert(testPreds.end(), extraTestPreds.begin(), extraTestPreds.end());
	trainPreds.insert(trainPreds.end(), extraTrainPreds.begin(), extraTrainPreds.end());
}

// Calibration
// Get Rid of zeros and ones
void clean_preds(vector<float>& preds) {

	float minP = -1, maxP = -1;
	for (size_t i = 0; i < preds.size(); i++) {
		if (preds[i] != 0.0 && preds[i] != 1.0) {
			if (minP == -1 || preds[i] < minP)
				minP = preds[i];
			if (maxP == -1 || preds[i] > maxP)
				maxP = preds[i];
		}
	}

	if (minP == -1 || maxP == -1)
		MTHROW_AND_ERR("Only ones and zeros left after calibration\n");

	for (size_t i = 0; i < preds.size(); i++) {
		if (preds[i] == 0.0) preds[i] = minP;
		if (preds[i] == 1.0) preds[i] = maxP;
	}
}

void recalibrate(vector<float>& preds, vector<float>& labels, const string& params, vector<float>* outPreds) {

	Calibrator cal;
	cal.init_from_string(params);


	int n = (int)preds.size();
	vector<MedSample> samples(n);
	for (int i = 0; i < n; i++) {
		samples[i].id = i;
		samples[i].time = 20000101; // Dummy date
		samples[i].outcome = labels[i];
		samples[i].outcomeTime = 20010101; // Dummy date
		samples[i].prediction.assign(1,preds[i]);
	}

	cal.Learn(samples);
	cal.Apply(samples);

	for (int i = 0; i < n; i++)
		preds[i] = samples[i].prediction[0];
	clean_preds(preds);

	if (outPreds != NULL) {
		int n = (int)outPreds->size();
		vector<MedSample> outSamples(n);
		for (int i = 0; i < n; i++) {
			outSamples[i].id = i;
			outSamples[i].time = 20000101; // Dummy date
			outSamples[i].outcome = labels[i];
			outSamples[i].outcomeTime = 20010101; // Dummy date
			outSamples[i].prediction.push_back((*outPreds)[i]);
		}

		cal.Apply(outSamples);

		for (int i = 0; i < n; i++)
			(*outPreds)[i] = outSamples[i].prediction[0];
		clean_preds(*outPreds);
	}

}


/// Write performance
void write_performance(vector<float>& preds, vector<float>& labels, const string& performanceFile) {

	// AUC
	float auc = medial::performance::auc(preds, labels);

	ofstream outf(performanceFile);
	if (!outf.is_open())
		MTHROW_AND_ERR("Cannot open %s for writing\n", performanceFile.c_str());

	outf << "AUC = " << auc << "\n";
}
void write_regression_performance(vector<float>& v1, vector<float>& v2, const string& performanceFile) {

	ofstream outf(performanceFile);
	if (!outf.is_open())
		MTHROW_AND_ERR("Cannot open %s for writing\n", performanceFile.c_str());

	// Variance of v1
	int n = (int)v1.size();
	double sum = 0;
	for (int i = 0; i < n; i++)
		sum += v1[i];
	double mean = sum / n;

	double var = 0;
	for (int i = 0; i < n; i++)
		var += (v1[i] - mean)*(v1[i] - mean);

	// Error
	double error = 0;
	for (int i = 0; i < n; i++)
		error += (v1[i] - v2[i])*(v1[i] - v2[i]);

	outf << "explained var = " << 1.0 - error / var << "\n";
	outf << "pearson = " << medial::performance::pearson_corr_without_cleaning(v1, v2) << "\n";
}

// Write Predictor to File
void write_predictor_to_file(MedPredictor *pred, const string& outFile) {
	size_t predictor_size = pred->get_predictor_size();
	vector<unsigned char> buffer(predictor_size);
	pred->predictor_serialize(&(buffer[0]));

	if (write_binary_data(outFile, &(buffer[0]), predictor_size) != 0)
		MTHROW_AND_ERR("Error writing model to file %s\n", outFile.c_str());
}

// Run Python scripts for ite (NN)
void prepare_for_nn_model(MedFeatures &inFeatures, string& in_params, string& dir, string& out_params, string suffix) {

	// parse params
	vector<string> fields;
	in_params.erase(remove_if(in_params.begin(), in_params.end(), ::isspace), in_params.end());
	boost::split(fields, in_params, boost::is_any_of(";"));

	map<string, string> parameters;
	vector<string> subFields;
	for (string& field : fields) {
		boost::split(subFields, field, boost::is_any_of("="));
		if (subFields.size() != 2)
			MTHROW_AND_ERR("Cannot parse entry \'%s\' in params\n", field.c_str());
		parameters[subFields[0]] = subFields[1];
	}

	// Write features to csv
	if (parameters.find("data") == parameters.end())
		MTHROW_AND_ERR("data entry required in python-script parameters\n");

	string dataFile = dir + "/" + parameters["data"] + "." + suffix;
	inFeatures.write_as_csv_mat(dataFile);
	parameters["data"] = dataFile;

	for (auto& rec : parameters)
		out_params += " --" + rec.first + " " + rec.second;

}
void learn_nn_model(MedFeatures &inFeatures, string& scriptName, string& params, string& dir, string& predictorFileName) {

	string runParams = scriptName + " --predictor " + predictorFileName;
	prepare_for_nn_model(inFeatures, params, dir, runParams, "train");

	// Learn Model
	my_run(runParams);
}
void apply_nn_model(MedFeatures &inFeatures, string& scriptName, string& params, string& dir, string& predictorFileName) {

	string predsFile = predictorFileName + ".preds";
	string runParams = scriptName + " --predictor " + predictorFileName + " --preds " + predsFile;
	prepare_for_nn_model(inFeatures, params, dir, runParams, "test");

	// Apply Model
	my_run(runParams);

	// Read predictions and insert into features
	vector<float> preds;
	read_vec(preds, predsFile);

	for (int i = 0; i < preds.size(); i++)
		inFeatures.samples[i].prediction.assign(1, preds[i]);

}
void my_run(string& command) {
	MLOG("Running \'%s\'\n", command.c_str());
	if (system(command.c_str()) != 0)
		MTHROW_AND_ERR("Running \'%s\' failed\n", command.c_str());
}

