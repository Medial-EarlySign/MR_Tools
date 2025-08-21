// A tool for performing g-computation regression for estimation of individual effect

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "g_comp.h"

#ifndef  __unix__
#pragma float_control( except, on )
#endif

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{

	if (argc != 2)
		MTHROW_AND_ERR("Usage: %s configuration-file\n", argv[0]);

	// Configuration
	configuration config;
	config.read_from_file(argv[1]);
	config.write_to_file();

	// Read Samples or features
	MedSamples samples;
	MedFeatures inFeatures;
	bool givenFeatures = false;
	int nSamples = 0;
	if (!config.samplesFile.empty()) {
		givenFeatures = false;
		MLOG("Reading samples\n");
		if (samples.read_from_file(config.samplesFile) != 0)
			MTHROW_AND_ERR("Cannot read samples from file %s", config.samplesFile.c_str());
		nSamples = samples.nSamples();
	}
	else if (!config.featuresFile.empty()) {
		MLOG("Reading matrix\n");
		givenFeatures = true;
		if (inFeatures.read_from_file(config.featuresFile) != 0)
			MTHROW_AND_ERR("Cannot read matrix from file %s\n", config.featuresFile.c_str());
		nSamples = (int)inFeatures.samples.size();
	}
	MLOG("Done: Read %d samples\n", nSamples);

	// Folds
	if (config.nFolds != -1)
		set_folds(config.nFolds, samples, inFeatures);

	// Learn initial model of P(Outcome|X,T)
	vector<float> initial;
	if (!config.read_initial) {
		MLOG("Starting initial-model learning\n");
		if (givenFeatures)
			learn_initial_from_features(inFeatures, config, initial);
		else
			learn_initial_from_samples(samples, config, initial);
		write_vec(initial, config.initialFile);
	}
	else
		read_vec(initial, config.initialFile);


	if (config.only_initial)
		return 0;

	// Learn final model of P(Outcome|X,T) given initial model
	MLOG("Starting final model learning\n");
	if (givenFeatures)
		learn_final_from_features(inFeatures, initial, config);
	else
		learn_final_from_samples(samples, initial, config);
}

// Functions
// Cross validation learning
void learn_initial_from_features(MedFeatures& inFeatures, configuration& config, vector<float>& preds) {

	if (config.do_two_models) {
		two_models_learn_initial_from_features(inFeatures, config, preds);
		return;
	}

	// Prepare
	string treatName = config.treatmentName;
	int nFolds = getNumFolds(inFeatures);
	int nSamples = inFeatures.samples.size();

	vector<float> subPreds(nSamples);
	preds.resize(2 * nSamples);
	vector<float> labels(nSamples);

	// CV
	for (int iFold = 0; iFold < nFolds; iFold++) {
		MLOG("initial cross validation. Split %d out of %d\n", iFold + 1, nFolds);

		// Split
		MedFeatures trainMatrix, testMatrix;
		split_matrix(inFeatures, iFold, trainMatrix, testMatrix);

		// Learn + predict
		MedPredictor *pred = MedPredictor::make_predictor(config.predictorName["initial"], config.predictorParams["initial"]);
		pred->learn(trainMatrix);
		pred->predict(testMatrix);

		//fill scores on relevant fold in preds:
		int test_smp_idx = 0;
		for (int i = 0; i < nSamples; ++i) {
			if (inFeatures.samples[i].split == iFold) {
				subPreds[i] = testMatrix.samples[test_smp_idx].prediction[0];
				labels[i] = testMatrix.samples[test_smp_idx].outcome;
				test_smp_idx++;
			}
		}

		// set treatment to 0/1 and apply
		for (int treatment = 0; treatment < 2; treatment++) {
			testMatrix.data[treatName].assign(testMatrix.samples.size(), treatment);
			pred->predict(testMatrix);

			test_smp_idx = 0;
			for (int i = 0; i < nSamples; ++i) {
				if (inFeatures.samples[i].split == iFold) {
					preds[nSamples*treatment + i] = testMatrix.samples[test_smp_idx].prediction[0];
					test_smp_idx++;
				}
			}
		}
	}

	// Performance
	if (!config.performanceFile["initial"].empty())
		write_performance(subPreds, labels, config.performanceFile["initial"]);

	// Calibration
	recalibrate(subPreds, labels, config.calibrationParams["initial"],&preds);
}

void two_models_learn_initial_from_features(MedFeatures& inFeatures, configuration& config, vector<float>& preds) {

	// Prepare
	string treatName = config.treatmentName;
	int nFolds = getNumFolds(inFeatures);
	int nSamples = inFeatures.samples.size();

	vector<vector<float>> labels(2), subPreds(2), tempPreds(2,vector<float>(nSamples));

	// CV
	for (int iFold = 0; iFold < nFolds; iFold++) {
		MLOG("initial cross validation. Split %d out of %d\n", iFold + 1, nFolds);;

		// Split
		MedFeatures trainMatrix, testMatrix;
		split_matrix(inFeatures, iFold, trainMatrix, testMatrix);
		vector<float> treatVec = testMatrix.data[treatName];
		testMatrix.data.erase(treatName);

		// Loop on treatment
		for (int treatment = 0; treatment < 2; treatment++) {
			MedFeatures subMatrix;
			vector<int> indices;
			getSubMatrix(trainMatrix, treatName, treatment, subMatrix, indices);
			subMatrix.data.erase(treatName);

			// Learn + predict
			string name = "initial" + to_string(treatment);
			MedPredictor *pred = MedPredictor::make_predictor(config.predictorName[name], config.predictorParams[name]);
			pred->learn(subMatrix);
			pred->predict(testMatrix);

			// fill subPreds (for performance)
			for (int i = 0; i < testMatrix.samples.size(); ++i) {
				if (treatVec[i] == treatment) {
					subPreds[treatment].push_back(testMatrix.samples[i].prediction[0]);
					labels[treatment].push_back(testMatrix.samples[i].outcome);
				}
			}

			// fill preds (for future use)
			int test_smp_idx = 0;
			for (int i = 0; i < nSamples; ++i) {
				if (inFeatures.samples[i].split == iFold) {
					tempPreds[treatment][i] = testMatrix.samples[test_smp_idx].prediction[0];
					test_smp_idx++;
				}
			}
		}
	}

	// Loop on treatment
	for (int treatment = 0; treatment < 2; treatment++) {
		string name = "initial" + to_string(treatment);

		// Performance
		if (!config.performanceFile[name].empty())
			write_performance(subPreds[treatment], labels[treatment], config.performanceFile[name]);

		// Calibration
		recalibrate(subPreds[treatment], labels[treatment], config.calibrationParams[name], &tempPreds[treatment]);

		// concatanate
		preds.insert(preds.end(), tempPreds[treatment].begin(), tempPreds[treatment].end());
	}
}

void learn_initial_from_samples(MedSamples& inSamples, configuration& config, vector<float>& preds) {

	if (config.do_two_models) {
		two_models_learn_initial_from_samples(inSamples, config, preds);
		return;
	}

	// Prepare
	string treatName = config.treatmentName;
	int nFolds = getNumFolds(inSamples);
	int nSamples = inSamples.nSamples();

	vector<float> subPreds(nSamples);
	preds.resize(2 * nSamples);
	vector<float> labels(nSamples);
	
	// Read Model json
	MLOG("initial : Reading model\n");
	MedModel model;
	model.init_from_json_file_with_alterations(config.modelFile["initial"], config.modelAlts["initial"]);

	// Read repository
	unordered_set<string> signalNamesSet;
	model.get_required_signal_names(signalNamesSet);
	vector<string> signalNames;
	for (string name : signalNamesSet)
		signalNames.push_back(name);

	vector<int> ids;
	inSamples.get_ids(ids);

	MLOG("Reading Repository\n");
	MedPidRepository rep;
	if (rep.read_all(config.repFile, ids, signalNames) != 0)
		MTHROW_AND_ERR("Read repository from %s failed\n", config.repFile.c_str());

	// Perform Cross validation
	for (int iFold = 0; iFold < nFolds; iFold++) {
		MLOG("initial cross validation. Split %d out of %d\n", iFold + 1, nFolds);

		// Split
		MedSamples trainSamples, testSamples;
		split_samples(inSamples, iFold, trainSamples, testSamples);

		// Learn + apply
		model.learn(rep, &trainSamples);
		model.apply(rep, testSamples);

		//fill scores on relevant fold in preds:
		int out_idx = 0, test_idx = 0;;
		for (int i = 0; i < inSamples.idSamples.size(); i++) {
			if (inSamples.idSamples[i].split == iFold) {
				for (auto& sample : testSamples.idSamples[test_idx].samples) {
					subPreds[out_idx] = sample.prediction[0];
					labels[out_idx] = sample.outcome;
					out_idx++;
				}
				test_idx++;
			}
			else
				out_idx += (int)inSamples.idSamples[i].samples.size();
		}

		// set treatment to 0/1 and apply
		for (int treatment = 0; treatment < 2; treatment++) {
			for (auto& idSample : testSamples.idSamples) {
				for (auto& samples : idSample.samples)
					samples.attributes[treatName] = treatment;
			}
			model.apply(rep, testSamples);

			out_idx = test_idx = 0;
			for (int i = 0; i < inSamples.idSamples.size(); i++) {
				if (inSamples.idSamples[i].split == iFold) {
					for (auto& sample : testSamples.idSamples[test_idx].samples) {
						preds[nSamples*treatment + out_idx] = sample.prediction[0];
						out_idx++;
					}
					test_idx++;
				}
				else
					out_idx += (int)inSamples.idSamples[i].samples.size();
			}
		}
	}

	// Performance
	if (!config.performanceFile["initial"].empty())
		write_performance(subPreds, labels, config.performanceFile["initial"]);

	// Calibration
	recalibrate(subPreds, labels, config.calibrationParams["initial"], &preds);
}

void two_models_learn_initial_from_samples(MedSamples& inSamples, configuration& config, vector<float>& preds) {

	// Prepare
	string treatName = config.treatmentName;
	int nFolds = getNumFolds(inSamples);
	int nSamples = inSamples.nSamples();

	vector<vector<float>> labels(2), subPreds(2), tempPreds(2, vector<float>(nSamples));

	// Read Model jsons
	MLOG("initial : Reading model\n");
	MedModel models[2];
	unordered_set<string> signalNamesSet;
	for (int treatment = 0; treatment < 2; treatment++) {
		string name = "initial" + to_string(treatment);
		models[treatment].init_from_json_file_with_alterations(config.modelFile[name], config.modelAlts[name]);
		models[treatment].get_required_signal_names(signalNamesSet);
	}

	// Read repository
	vector<string> signalNames;
	for (string name : signalNamesSet)
		signalNames.push_back(name);

	vector<int> ids;
	inSamples.get_ids(ids);

	MLOG("Reading Repository\n");
	MedPidRepository rep;
	if (rep.read_all(config.repFile, ids, signalNames) != 0)
		MTHROW_AND_ERR("Read repository from %s failed\n", config.repFile.c_str());

	// CV
	for (int iFold = 0; iFold < nFolds; iFold++) {
		MLOG("initial cross validation. Split %d out of %d\n", iFold + 1, nFolds);

		// Split
		MedSamples trainSamples, testSamples;
		split_samples(inSamples, iFold, trainSamples, testSamples);

		// Loop on treatment
		for (int treatment = 0; treatment < 2; treatment++) {
			MedSamples subSamples;
			vector<int> indices;
			getSubSamples(trainSamples, treatName, treatment, subSamples, indices);

			// Learn + predict
			// Learn + apply
			string name = "initial" + to_string(treatment);

			models[treatment].learn(rep, &subSamples);
			models[treatment].apply(rep, testSamples);

			// fill subPreds (for performance)
			for (auto& idSample : testSamples.idSamples) {
				for (auto& sample : idSample.samples) {
					if (sample.attributes[treatName] == treatment) {
						subPreds[treatment].push_back(sample.prediction[0]);
						labels[treatment].push_back(sample.outcome);
					}
				}
			}

			// fill preds (for future use)
			int out_idx = 0, test_idx = 0;
			for (int i = 0; i < inSamples.idSamples.size(); i++) {
				if (inSamples.idSamples[i].split == iFold) {
					for (auto& sample : testSamples.idSamples[test_idx].samples) {
						tempPreds[treatment][out_idx] = sample.prediction[0];
						out_idx++;
					}
					test_idx++;
				}
				else
					out_idx += (int)inSamples.idSamples[i].samples.size();
			} 
		}
	}

	// Loop on treatment
	for (int treatment = 0; treatment < 2; treatment++) {
		string name = "initial" + to_string(treatment);

		// Performance
		if (!config.performanceFile[name].empty())
			write_performance(subPreds[treatment], labels[treatment], config.performanceFile[name]);

		// Calibration
		recalibrate(subPreds[treatment], labels[treatment], config.calibrationParams[name], &tempPreds[treatment]);

		// concatanate
		preds.insert(preds.end(), tempPreds[treatment].begin(), tempPreds[treatment].end());
	}
}

// Second layer learning
void learn_final_from_features(MedFeatures& inFeatures, vector<float>& inPreds, configuration& config) {

	string outFileName = config.runDir + "/" + config.out;
	int nSamples = (int)inFeatures.samples.size();
	int startIndex = config.include_original ? nSamples : 0;
	int nOutSamples = startIndex + 2 * nSamples;

	// Generate complete matrix
	MedFeatures outFeatures;
	generateMatrix(inFeatures, inPreds, config.treatmentName, config.include_original, outFeatures);

	// Rename treatment feature to be different from 'Treatment' so it is not ignored by the python script
	FeatureProcessor p;
	string treatmentFtrName = p.resolve_feature_name(outFeatures, config.treatmentName);
	string newFtrName = "FTR_Treatment";
	outFeatures.data[newFtrName] = outFeatures.data[treatmentFtrName];
	outFeatures.attributes[newFtrName] = outFeatures.attributes[treatmentFtrName];
	outFeatures.data.erase(treatmentFtrName);
	outFeatures.attributes.erase(treatmentFtrName);

	// Perform regression learning
	vector<float> preds(nOutSamples), labels(nOutSamples);
	regression_cross_validation_on_matrix(outFeatures, config.nFolds, config.predictorName["final"], config.predictorParams["final"], config.runDir, outFileName, preds, labels);

	// Write ITE file (if given)
	if (!config.iteFile.empty()) {
		vector<float> ite(nSamples);
		for (int i = 0; i < nSamples; i++)
			ite[i] = preds[startIndex + nSamples + i] - preds[startIndex + i];
		write_vec(ite, config.iteFile);
	}

	//  Performance
	if (!config.performanceFile["final"].empty()) 
		write_regression_performance(labels, preds, config.performanceFile["final"]);

	// Learn full model
	if (boost::algorithm::ends_with(config.predictorName["final"], ".py")) {
		// Run Python script
		outFeatures.weights.assign(outFeatures.samples.size(), 1.0);
		learn_nn_model(outFeatures, config.predictorName["final"], config.predictorParams["final"], config.runDir, outFileName);
	}
	else {
		MedPredictor *predictor = MedPredictor::make_predictor(config.predictorName["final"], config.predictorParams["final"]);
		predictor->learn(outFeatures);
		write_predictor_to_file(predictor, outFileName);
	}
}

void learn_final_from_samples(MedSamples& inSamples, vector<float>& inPreds, configuration& config) {

	string outFileName = config.runDir + "/" + config.out;
	int nSamples = inSamples.nSamples();
	int startIndex = config.include_original ? nSamples : 0;
	int nOutSamples = startIndex + 2 * nSamples;

	// Read Model json
	MLOG("Reading final model\n");
	MedModel model;
	model.init_from_json_file_with_alterations(config.modelFile["final"], config.modelAlts["final"]);

	// Read repository
	unordered_set<string> signalNamesSet;
	model.get_required_signal_names(signalNamesSet);
	vector<string> signalNames;
	for (string name : signalNamesSet)
		signalNames.push_back(name);

	vector<int> ids;
	inSamples.get_ids(ids);

	cerr << "Reading Repository" << endl;
	MedPidRepository rep;
	if (rep.read_all(config.repFile, ids, signalNames) != 0)
		MTHROW_AND_ERR("Read repository from %s failed\n", config.repFile.c_str());

	// Perform regression CV
	vector<float> preds, labels;
	regression_cross_validation_on_samples(inSamples, rep, config, inPreds, preds, labels);

	// Write ITE file (if given)
	if (!config.iteFile.empty()) {
		vector<float> ite(nSamples);
		for (int i = 0; i < nSamples; i++)
			ite[i] = preds[startIndex + nSamples + i] - preds[startIndex + i];
		write_vec(ite, config.iteFile);
	}

	//  Performance
	if (!config.performanceFile["final"].empty())
		write_regression_performance(labels, preds, config.performanceFile["final"]);

	// Perform regression learning
	get_regression_model(inSamples, rep, config, inPreds, model, outFileName);

}

// Cross validation for second layer learning
void regression_cross_validation_on_samples(MedSamples& samples, MedPidRepository& rep, configuration& config, vector<float>& inPreds, vector<float>& outPreds, vector<float>& labels) {

	// Samples
	int nSamples = samples.nSamples();
	int outNSamples = 2 * nSamples + (config.include_original ? nSamples : 0);
	string outFileName = config.runDir + "/tensor_flow_" + config.out;

	outPreds.resize(outNSamples);
	labels.resize(outNSamples);

	// Splits
	map<int, int> idSplit;
	for (auto& idSamples : samples.idSamples)
		idSplit[idSamples.id] = idSamples.split;

	MedModel model;
	model.init_from_json_file_with_alterations(config.modelFile["final"], config.modelAlts["final"]);

	MedFeatures fullTrainMatrix,fullTestMatrix;
	for (int iFold = 0; iFold < config.nFolds; iFold++) {
		MLOG("Final layer cross-validation. Split %d out of %d\n", iFold + 1, config.nFolds);

		// Split
		MedSamples trainSamples, testSamples;
		vector<float> trainPreds, testPreds;
		g_comp_split_samples(samples, iFold, trainSamples, testSamples, inPreds, trainPreds, testPreds);

		// Get training matrix
		model.learn(rep, &trainSamples, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS);
		generateMatrix(model.features, trainPreds, config.treatmentName, config.include_original, fullTrainMatrix);

		// Get test matrix
		model.apply(rep, testSamples, MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_APPLY_FTR_PROCESSORS);
		generateMatrix(model.features, testPreds, config.treatmentName, config.include_original, fullTestMatrix);

		// Learn + predict
		if (boost::algorithm::ends_with(config.predictorName["final"], ".py")) {
			// Run Python scripts 
			fullTrainMatrix.weights.assign(fullTrainMatrix.samples.size(), 1.0);
			learn_nn_model(fullTrainMatrix, config.predictorName["final"], config.predictorParams["final"], config.runDir, outFileName);
			apply_nn_model(fullTestMatrix, config.predictorName["final"], config.predictorParams["final"], config.runDir, outFileName);
		}
		else {
			// Learn and Predict
			model.predictor->learn(fullTrainMatrix);
			model.predictor->predict(fullTestMatrix);
		}


		//fill scores on relevant fold in preds:
		int in_idx = 0, out_idx = 0;
		int nTestSamples = testSamples.nSamples();
		int nPerSample = config.include_original ? 3 : 2;

		for (auto& idSample : samples.idSamples) {
			int n = (int)idSample.samples.size();
			if (idSample.split == iFold) {
				for (int i = 0; i < n ; i++) {
					for (int j = 0; j < nPerSample; j++) {
						outPreds[nSamples*j + out_idx + i] = fullTestMatrix.samples[nTestSamples*j + in_idx + i].prediction[0];
						labels[nSamples*j + out_idx + i] = fullTestMatrix.samples[nTestSamples*j + in_idx + i].outcome;
					}
				}
				in_idx += n;
			}
			out_idx += n;
		}
	}
}

// Learning for second layer
void get_regression_model(MedSamples& inSamples, MedPidRepository& rep, configuration& config, vector<float>& inPreds, MedModel& model, string& outFileName) {

	// Samples
	int nSamples = inSamples.nSamples();
	int outNSamples = 2 * nSamples + (config.include_original ? nSamples : 0);

	MedFeatures fullFeatures;

	// Generate features
	model.init_from_json_file_with_alterations(config.modelFile["final"], config.modelAlts["final"]);

	// Get training matrix
	model.learn(rep, &inSamples, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS);
	generateMatrix(model.features, inPreds, config.treatmentName, config.include_original, fullFeatures);

	// Learn
	if (boost::algorithm::ends_with(config.predictorName["final"], ".py")) {
		// Run Python script
		fullFeatures.weights.assign(fullFeatures.samples.size(), 1.0);
		string tOutFileName = outFileName + "_tensorflow";
		learn_nn_model(fullFeatures, config.predictorName["final"], config.predictorParams["final"], config.runDir, tOutFileName);
		
		if (model.predictor != NULL) {
			delete model.predictor;
			model.predictor = NULL;
		}
	}
	else
		model.predictor->learn(fullFeatures);
	model.write_to_file(outFileName);

	
}


// Getting value dependent matrix
void getSubMatrix(MedFeatures& matrix, const string& ftr, const float value, MedFeatures& outMatrix, vector<int>& indices) {

	// Sanity
	if (matrix.data.find(ftr) == matrix.data.end())
		MTHROW_AND_ERR("Cannot find \'%s\' in matrix\n", ftr.c_str());

	// Clear
	outMatrix.samples.clear();
	outMatrix.data.clear();
	outMatrix.samples.clear();
	indices.clear();

	// Attributes
	for (auto& attr : matrix.attributes)
		outMatrix.attributes[attr.first] = attr.second;

	// Samples + Data
	vector<float> & ftrValues = matrix.data[ftr];
	for (unsigned int i = 0; i < matrix.samples.size(); i++) {
		if (ftrValues[i] == value) {
			outMatrix.samples.push_back(matrix.samples[i]);
			for (auto& rec : matrix.data)
				outMatrix.data[rec.first].push_back(matrix.data[rec.first][i]);
			indices.push_back(i);
		}
	}
}

// Getting value dependent samples
void getSubSamples(MedSamples& inSamples, const string& attr, const float value, MedSamples& outSamples, vector<int>& indices) {

	// Clear
	indices.clear();

	// select
	vector<MedSample> samples;
	int idx = 0;
	for (auto& idSample : inSamples.idSamples) {
		for (auto& sample : idSample.samples) {
			if (sample.attributes.find(attr) == sample.attributes.end()) {
				MTHROW_AND_ERR("Cannot find attribute %s for samples %d/%d\n", attr.c_str(), sample.id, sample.time);
			} 
			else if (sample.attributes[attr] == value) {
				samples.push_back(sample);
				indices.push_back(idx);
			}

			idx++;
		}
	}

	outSamples.import_from_sample_vec(samples);
}

// Generate counter-factual matrix
void generateMatrix(MedFeatures& inFeatures, vector<float>& preds, string treatName, bool include_original, MedFeatures& outFeatures) {

	size_t nSamples = inFeatures.samples.size();
	FeatureProcessor p;
	string treatmentFtrName = p.resolve_feature_name(inFeatures, treatName);
	MLOG("Name of treatment feature = %s\n", treatmentFtrName.c_str());

	// Sanity
	if (preds.size() != 2 * nSamples)
		MTHROW_AND_ERR("Predictions (%d) are not twice the size of samples (%d). Quitting\n", preds.size(), nSamples);

	// Initialize
	vector<string> ftr_names;
	inFeatures.get_feature_names(ftr_names);

	outFeatures.samples.clear();
	for (string& name : ftr_names) {
		outFeatures.attributes[name] = inFeatures.attributes[name];
		outFeatures.data[name].clear();
	}

	// Original
	size_t index = 0;
	if (include_original) {
		outFeatures.samples.insert(outFeatures.samples.end(), inFeatures.samples.begin(), inFeatures.samples.end());
		for (string& name : ftr_names)
			outFeatures.data[name].insert(outFeatures.data[name].end(), inFeatures.data[name].begin(), inFeatures.data[name].end());
		index = nSamples;
	}

	// Counter factuals
	size_t preds_idx = 0;
	for (int treatment = 0; treatment < 2; treatment++) {
		outFeatures.samples.insert(outFeatures.samples.end(), inFeatures.samples.begin(), inFeatures.samples.end());
		for (string& name : ftr_names)
			outFeatures.data[name].insert(outFeatures.data[name].end(), inFeatures.data[name].begin(), inFeatures.data[name].end());

		for (size_t i = 0; i < nSamples; i++) {
			outFeatures.samples[index + i].outcome = preds[preds_idx + i];
			outFeatures.data[treatmentFtrName][index + i] = treatment;
		}

		index += nSamples; 
		preds_idx += nSamples;
	}

}