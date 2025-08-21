// A tool for performing quasi-oracle estimation of individual effect

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "quasi_oracle.h"

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
		nSamples =(int) inFeatures.samples.size();
	}
	MLOG("Done: Read %d samples\n", nSamples);

	// Folds
	if (config.nFolds != -1)
		set_folds(config.nFolds, samples, inFeatures);

	// Learn E = P(Treatment | X) = Propensitry
	vector<float> e;
	if (!config.only_m) {
		if (!config.read_e) {
			MLOG("Starting E-learning\n");
			if (givenFeatures)
				learn_e_from_features(inFeatures, config, e);
			else
				learn_e_from_samples(samples, config, e);
			write_vec(e, config.eFile);
		}
		else {
			read_vec(e, config.eFile);
			if (e.size() != nSamples)
				MTHROW_AND_ERR("Size inconsistency between nSamples (%d) and e (size = %zu)\n", nSamples, e.size());
		}
	}

	// Learn M = P(Outcome | X) 
	vector<float> m;
	if (!config.only_e) {
		if (!config.read_m) {
			MLOG("Starting M-learning\n");
			if (givenFeatures)
				learn_m_from_features(inFeatures, config, m);
			else
				learn_m_from_samples(samples, config, m);
			write_vec(m, config.mFile);
		}
		else {
			read_vec(m, config.mFile);
			if (m.size() != nSamples)
				MTHROW_AND_ERR("Size inconsistency between nSamples (%d) and m (size = %zu)\n", nSamples, m.size());
		}
	}

	if (config.only_e || config.only_m)
		return 0;

	// Learn ITE
	MLOG("Starting ITE-learning\n");
	if (givenFeatures)
		learn_ite_from_features(inFeatures, e, m, config);
	else
		learn_ite_from_samples(samples, e, m, config);
}

// Functions
// Cross validation learning
void learn_e_from_features(MedFeatures& inFeatures, configuration& config, vector<float>& e) {

	int n = (int)inFeatures.samples.size();

	// Replace outcome with treatment
	MLOG("Preparing ...\n");
	vector<float> outcome(n);
	for (int i = 0; i < n; i++) {
		outcome[i] = inFeatures.samples[i].outcome;
		inFeatures.samples[i].outcome = inFeatures.data[config.treatmentName][i];
	}
	inFeatures.data.erase(config.treatmentName);

	// Learn 
	MLOG("Learning ...\n");
	learn_from_features(inFeatures, e, config.predictorName["e"],config.predictorParams["e"],config.performanceFile["e"],config.calibrationParams["e"], "e");

	// Replace back
	MLOG("Rearranging ...\n");
	inFeatures.data[config.treatmentName].resize(n);
	for (int i = 0; i < n; i++) {
		inFeatures.data[config.treatmentName][i] = inFeatures.samples[i].outcome;
		inFeatures.samples[i].outcome = outcome[i];
	}
}
void learn_e_from_samples(MedSamples& samples, configuration& config, vector<float>& e) {

	int n = samples.nSamples();

	// Replace outcome with treatment
	vector<float> outcome(n);
	vector<int> outcomeTime(n);
	int i = 0;
	for (MedIdSamples& idSamples : samples.idSamples) {
		for (MedSample& sample : idSamples.samples) {
			outcome[i] = sample.outcome;
			outcomeTime[i] = sample.outcomeTime;
			i++;

			sample.outcome = sample.attributes[config.treatmentName];
			if (! config.treatmentTimeName.empty())
				sample.outcomeTime = (int)sample.attributes[config.treatmentTimeName];
		}
	}


	// Learn 
	learn_from_samples(samples, e, config.modelFile["e"], config.modelAlts["e"], config.repFile, config.performanceFile["e"], config.calibrationParams["e"], "e");

	// Replace back
	i = 0;
	for (MedIdSamples& idSamples : samples.idSamples) {
		for (MedSample& sample : idSamples.samples) {
			sample.outcome = outcome[i];
			sample.outcomeTime = outcomeTime[i] ;
			i++;
		}
	}

}
void learn_m_from_features(MedFeatures& inFeatures, configuration& config, vector<float>& m) {

	// Remove Treatment
	vector<float> treatment = inFeatures.data[config.treatmentName];
	inFeatures.data.erase(config.treatmentName);

	// Learn
	learn_from_features(inFeatures, m, config.predictorName["m"], config.predictorParams["m"], config.performanceFile["m"], config.calibrationParams["m"], "m");

	// Replace back
	inFeatures.data[config.treatmentName] = treatment;

}
void learn_m_from_samples(MedSamples& samples, configuration& config, vector<float>& m) {
	learn_from_samples(samples, m, config.modelFile["m"], config.modelAlts["m"], config.repFile, config.performanceFile["m"], config.calibrationParams["m"], "m");
}

// Learning ite
void learn_ite_from_features(MedFeatures &inFeatures, vector<float>& e, vector<float>& m, configuration& config) {

	int n = (int) e.size();
	string outFileName = config.runDir + "/" + config.out;

	// Get T,W
	vector<float> y(n);
	inFeatures.weights.resize(n);   
	for (int i = 0; i < n; i++) {
		y[i] = inFeatures.samples[i].outcome;
		
		float wgt = inFeatures.data[config.treatmentName][i] - e[i];
		if (fabs(wgt) < MIN_ABS_WGT) wgt = (wgt>0) ? MIN_ABS_WGT : -MIN_ABS_WGT;
		inFeatures.samples[i].outcome = (y[i] - m[i]) / wgt;
		inFeatures.weights[i] = wgt * wgt;  
	}
	vector<float> treatment = inFeatures.data[config.treatmentName];
	inFeatures.data.erase(config.treatmentName);

	// Cross validation for performance evaluation
	// Get nFolds
	int nFolds = getNumFolds(inFeatures);


	vector<float> preds(inFeatures.samples.size()),labels(inFeatures.samples.size());
	regression_cross_validation_on_matrix(inFeatures, nFolds, config.predictorName["ite"], config.predictorParams["ite"], config.runDir, outFileName, preds, labels);

	// Write ITE file (if given)
	if (!config.iteFile.empty())
		write_vec(preds, config.iteFile);

	//  Performance
	if (!config.performanceFile["ite"].empty())
		write_regression_performance(preds, y, treatment, m, e, config.performanceFile["ite"]);

	// Learn full model
	if (boost::algorithm::ends_with(config.predictorName["ite"], ".py")) {
		// Run Python script
		learn_nn_model(inFeatures, config.predictorName["ite"], config.predictorParams["ite"], config.runDir, outFileName);
	}
	else {
		MedPredictor *predictor = MedPredictor::make_predictor(config.predictorName["ite"], config.predictorParams["ite"]);
		predictor->learn(inFeatures);
		write_predictor_to_file(predictor, outFileName);
	}

	// Reinstall
	inFeatures.data[config.treatmentName] = treatment;
	for (int i = 0; i < n; i++)
		inFeatures.samples[i].outcome = y[i];

}
void learn_ite_from_samples(MedSamples& samples, vector<float>& e, vector<float>& m, configuration& config) {

	int n = (int)e.size();
	int nFolds = getNumFolds(samples);
	string outFileName = config.runDir + "/" + config.out;
	

	// Get T,W
	vector<float> treatment(n);
	vector<float> y(n), weights(n);
	int i = 0;
	for (MedIdSamples& idSamples : samples.idSamples) {
		for (MedSample& sample : idSamples.samples) {
			y[i] = sample.outcome;
			treatment[i] = sample.attributes[config.treatmentName];
			float wgt = treatment[i] - e[i];
			if (fabs(wgt) < MIN_ABS_WGT) wgt = (wgt>0) ? MIN_ABS_WGT : -MIN_ABS_WGT;
			sample.outcome = (y[i] - m[i]) / wgt;
			weights[i] = wgt * wgt;

			i++;
		}
	}

	// Read Model json
	MedModel model;
	MLOG("ite: Reading model\n");
	model.init_from_json_file_with_alterations(config.modelFile["ite"], config.modelAlts["ite"]);

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
	if (rep.read_all(config.repFile, ids, signalNames) != 0)
		MTHROW_AND_ERR("Read repository from %s failed\n", config.repFile.c_str());

	// Perform Cross validation
	vector<float> preds(samples.nSamples());
	vector<float> labels(preds.size());
	regression_cross_validation_on_samples(samples, weights, model, rep, nFolds, config.predictorName["ite"], config.predictorParams["ite"], config.runDir, outFileName, preds, labels);

	// Write ITE file (if given)
	if (!config.iteFile.empty())
		write_vec(preds, config.iteFile);

	//  Performance
	if (!config.performanceFile["ite"].empty())
		write_regression_performance(preds, y, treatment, m, e, config.performanceFile["ite"]);

	// Learn full model
	model.learn(rep, &samples, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS);
	model.features.weights = weights;
	if (boost::algorithm::ends_with(config.predictorName["ite"], ".py")) {
		string tfOutFileName = outFileName + "_tensorflow";
		learn_nn_model(model.features, config.predictorName["ite"], config.predictorParams["ite"], config.runDir, tfOutFileName);

		// Delete predictor from model (it may cause serialization problems)
		if (model.predictor != NULL) {
			delete model.predictor;
			model.predictor = NULL;
		}
	}
	else
		model.learn(rep, &samples, MED_MDL_LEARN_PREDICTOR, MED_MDL_END);

	// Write model to file
	model.write_to_file(outFileName);

	// Reinstall
	i = 0;
	for (MedIdSamples& idSamples : samples.idSamples) {
		for (MedSample& sample : idSamples.samples)
			sample.outcome = y[i++];
	}
}

// Performance
void write_regression_performance(vector<float>& preds, vector<float>& y, vector<float>& t, vector<float>& m, vector<float>& e, const string& performanceFile) {

	int n = (int)preds.size();

	// Generate vectors
	vector<float> v1(n), v2(n);
	for (int i = 0; i < n; i++) {
		v1[i] = y[i] - m[i];
		v2[i] = (t[i] - e[i])*preds[i];
	}

	write_regression_performance(v1, v2, performanceFile);

}

float get_weighted_pearson_corr(vector<float>& v1, vector<float>& v2, vector<float>& w) {
	
	double sx, sy, sxy, sxx, syy, n;
	sx = sy = sxy = sxx = syy = n = 0;
	int len = (int) v1.size();

	double fact = 1e-5;
	for (int i = 0; i < len; i++) {
		sx += fact * v1[i] * w[i];
		sy += fact * v2[i] * w[i];
		sxx += fact * v1[i] * v1[i] * w[i] ;
		syy += fact * v2[i] * v2[i] * w[i];
		sxy += fact * v1[i] * v2[i] * w[i];
		n += w[i];
	}

	sx /= fact * n;
	sy /= fact * n;
	sxx /= fact * n;
	syy /= fact * n;
	sxy /= fact * n;

	double c1 = sxy - sx * sy;
	double c2 = sxx - sx * sx;
	double c3 = syy - sy * sy;

	double epsilon = 1e-8;
	if (c2 < epsilon || c3 < epsilon)
		return 0;
	return (float)(c1 / (sqrt(c2)*sqrt(c3)));
}
