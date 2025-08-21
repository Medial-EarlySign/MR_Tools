#!/usr/bin/python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import tempfile
import numpy as np
import time

import csv
import collections

FLAGS = None

# Data
Datasets = collections.namedtuple('Datasets', ['train', 'test'])

class DataSet(object):

	# Initialization of a data set
	def __init__(self, data, header, treatment_name, name=None):

		features_cols = []
		label_col = -1
		weights_col = -1
		treatments_col = -1
		
		for col in range(len(header)):
			if (header[col] == "outcome"):
				label_col = col
			elif (header[col] == "weight"):
				weights_col = col
			elif (header[col] == treatment_name):
				treatments_col = col
			elif (header[col] != "serial" and header[col] != "id" and header[col] != "time" and header[col] != "outcome_time" and header[col] != "split" and header[col][:5] != "pred_"):
				features_cols.append(col)

		print(label_col,weights_col,features_cols,treatments_col)
		self.features = np.array(data[:,features_cols])
		self.labels = np.array(data[:,label_col]).reshape([-1,1])
		if (weights_col == -1):
			self.weights=np.ones(self.labels.shape)
		else:
			self.weights = np.array(data[:,weights_col]).reshape([-1,1])
		self.treatment = np.array(data[:,treatments_col])

		self.nfeatures = len(features_cols)
		self.num_examples = len(data)
		
		self.features_mean = self.features.mean(axis=0)
		self.features_std = self.features.std(axis=0)
		for i in range(len(self.features_std)):
			if (self.features_std[i] == 0):
				self.features_std[i] = 1.0 ;

		self._epochs_completed = 0
		self._index_in_epoch = 0
		
	# Restart batching
	def init_batches(self):
		self._index_in_epoch = 0
		
	# Generate next batch
	def next_batch(self, batch_size,shuffle=True):
		start = self._index_in_epoch
		# Shuffle for the first epoch
		if self._epochs_completed == 0 and start == 0:
			perm0 = np.arange(self.num_examples)
			if (shuffle):
				np.random.shuffle(perm0)
			self._features = self.features[perm0]
			self._labels = self.labels[perm0]
			self._weights = self.weights[perm0]
			self._treatment = self.treatment[perm0]
		# Go to the next epoch
		if start + batch_size > self.num_examples:
			# Finished epoch
			self._epochs_completed += 1
			# Get the rest examples in this epoch
			rest_num_examples = self.num_examples - start
			features_rest_part = self._features[start:self.num_examples]
			labels_rest_part = self._labels[start:self.num_examples]
			weights_rest_part = self._weights[start:self.num_examples]
			treatment_rest_part = self._treatment[start:self.num_examples]
			# Shuffle the data
			if shuffle:
				perm = np.arange(self.num_examples)
				np.random.shuffle(perm)
				self._features = self.features[perm]
				self._labels = self.labels[perm]
				self._weights = self.weights[perm]
				self._treatment = self.treatment[perm]
			# Start next epoch
			start = 0
			self._index_in_epoch = batch_size - rest_num_examples
			end = self._index_in_epoch
			features_new_part = self._features[start:end]
			labels_new_part = self._labels[start:end]
			weights_new_part = self._weights[start:end]
			treatment_new_part = self._treatment[start:end]
			return np.concatenate((features_rest_part, features_new_part), axis=0) , np.concatenate((labels_rest_part, labels_new_part), axis=0) \
				, np.concatenate((weights_rest_part, weights_new_part), axis=0), np.concatenate((treatment_rest_part, treatment_new_part), axis=0)
		else:
			self._index_in_epoch += batch_size
			end = self._index_in_epoch
			return self._features[start:end], self._labels[start:end], self._weights[start:end], self._treatment[start:end]

# Read csv from file
def read_csv_data_set(file, treatment_name):
	print("Reading csv file %s"%file)

	header = []
	list = []
	with open(file) as csv_file:
		data_file = csv.reader(csv_file)
		for row in data_file:
			if (len(header)==0):
				header = row
			else:
				list.append(row)
	print("Arranging")
	data = np.array(list).astype(float)
	return DataSet(data,header,treatment_name)

def read_and_split_csv_data_set(file,prob, treatment_name):
	print("Reading csv file %s"%file)

	header = []
	list1 = []
	list2 = []
	with open(file) as csv_file:
		data_file = csv.reader(csv_file)
		for row in data_file:
			if (len(header)==0):
				header = row
			elif (np.random.rand() > prob):
				list1.append(row)
			else:
				list2.append(row)
	print("Arranging")
	data1 = np.array(list1).astype(float)
	data2 = np.array(list2).astype(float)
	return DataSet(data1,header,treatment_name),DataSet(data2,header,treatment_name)

# Read Data set and split to train and test
def read_and_split_data_set(data_file, test_p, treatment_name):

	# Read
	train,test = read_and_split_csv_data_set(data_file,test_p,treatment_name)
	
	print("Train",train.features.shape,train.labels.shape,train.weights.shape,train.treatment.shape)
	print("Test",test.features.shape,test.labels.shape,test.weights.shape,test.treatment.shape)
	
	return Datasets(train=train,test=test)
	
# Read Data set and split to train and test
def read_data_set(data_file, treatment_name):

	# Read
	test = read_csv_data_set(data_file,treatment_name)
	
	print("Test",test.features.shape,test.labels.shape,test.weights.shape,test.treatment.shape)
	
	return test
