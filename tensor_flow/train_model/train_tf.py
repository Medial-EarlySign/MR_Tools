#!/usr/bin/python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

#sys.path.insert(0,'/nas1/UsersData/avi/MR/Libs/Internal/MedPyExport/generate_binding/Release/rh-python27')

import argparse
import sys
import tempfile
import numpy as np
import time
import csv

import tensorflow as tf
from tensorflow.python.framework import random_seed
import collections

import os
from matrix_reader import read_data_set,read_and_split_data_set,prep_data_from_model,write_to_file,DataSet
import train_model

FLAGS = None

# Main
def main(_):
	# Random initializationq
	tf.set_random_seed(FLAGS.seed)
	np.random.seed(FLAGS.seed)

	# Device
	os.environ['CUDA_VISIBLE_DEVICES'] = FLAGS.gpu
	print('FLAGS.gpu:=%s'%(FLAGS.gpu))

	# prepare data
	
	start_time = time.time()

	# generate from model case
	if (FLAGS.get_mat):
		data,vdata,test_data = prep_data_from_model(FLAGS.model, FLAGS.rep, FLAGS.samples, FLAGS.p_validation,FLAGS.split,FLAGS.write_mat)
		if (FLAGS.validation_samples != ''):
			vdata,dummy_data,test_data = prep_data_from_model(FLAGS.model, FLAGS.rep, FLAGS.validation_samples, 0,FLAGS.split,FLAGS.write_mat)
	
	else:
		# read from file case
		data = read_data_set(FLAGS.data,'')
		vdata = data

	if FLAGS.sub_sample > 0:
            data.sub_sample(FLAGS.sub_sample)
	# case validation samples are provided	
	if (FLAGS.validation_data != ''):
		vdata = read_data_set(FLAGS.validation_data)
        
	print("Got %d samples in data, %d samples in vdata" % (data.num_examples, vdata.num_examples))
	print("Data import took %f secs\n"%(time.time()-start_time))

	# AUC
	if (data.num_examples < FLAGS.max_auc_batch):
		FLAGS.max_auc_batch = data.num_examples

	# Defining the generator tf model
	tf_model = train_model.deep_train(FLAGS,data.nfeatures)

	#  Training Session
	config = tf.ConfigProto(allow_soft_placement=True)
	config.intra_op_parallelism_threads = 50
	config.inter_op_parallelism_threads = 50

#	with tf.Session(config = tf.ConfigProto(allow_soft_placement = True)) as sess:
	if (FLAGS.mode == 'learn'):
		with tf.Session(config = config) as sess:

			sess.run(tf.global_variables_initializer())
			sess.run(tf.local_variables_initializer())
		
			if (FLAGS.mode == 'learn'):
				tf_model.learn(sess, data, vdata, test_data, FLAGS)

				# Save model
				if (FLAGS.model_out is not None):
					tf_model.save(sess,os.path.join(FLAGS.work_output_dir, FLAGS.model_out))

				if (FLAGS.model_text is not None):
					tf_model.export(sess,os.path.join(FLAGS.work_output_dir, FLAGS.model_text))		
				
	if (FLAGS.mode == 'predict'):
		with tf.Session(config=config) as sess:
			sess.run(tf.global_variables_initializer())
			sess.run(tf.local_variables_initializer())
			tf_model.restore(sess, FLAGS.model_out)
			tf_model.predict(sess, data, vdata, test_data, FLAGS)
#			tf_model.export(sess, 'debug_text')
		
			   
####################################################

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == "__main__":

	# configuration file
	#
	#  Read command arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('--data', type=str, required=False, help='train data')
	parser.add_argument('--validation_data', type=str, default = '', required=False, help='validation set')
	parser.add_argument('--split',type=int,default=-1000,help='split to work on')
	parser.add_argument('--write_mat',type=int,default=0,help='split to work on')
	parser.add_argument('--mode',type=str,default="learn",help='modes are: learn (will train on given split) , predict (will predict on given split)')
	
	parser.add_argument('--seed',type=int,default=134,help='random seed')

	parser.add_argument('--batch_num',type=int,default=10000,help='# of optimization steps')
	parser.add_argument('--batch_size',type=int,default=200,help='size of batch for SGD')
	parser.add_argument('--learning_rate',type=float,default=0.001,help='learning rate')
	parser.add_argument('--print_freq', type=int, default=0, help='frequency of info printing : 0 : no printings')
	parser.add_argument('--auc_freq', type=int, default=100, help='frequency of AUC printing')
	parser.add_argument('--max_auc_batch', type=int, default=10000, help='maximal size of batch for AUC prints while training (each auc_freq)')
	parser.add_argument('--max_ever_auc_batch', type=int, default=800000, help='maximal size of batch for AUC when testing all data')
	parser.add_argument('--missing_value', type=float, default=-65336, help='missing value in train matrices')

	parser.add_argument('--reg_beta',type=float,default=0.0,help='L2 regulation for generator')
	parser.add_argument('--nhiddens',type=str,help='# of cells in hidden layer for generator - comma separated vector')
	parser.add_argument('--nlayers',type=int,default=2,help='# of hidden layers for generator')
	parser.add_argument('--functions', type=str, help='activation function (sig/relu/leaky_relu) for generator - comma separated vector')
	parser.add_argument('--function', type=str, default='leaky_relu', help='activation function (sig/relu/leaky_relu) for generator - comma separated vector')
	parser.add_argument('--keep_prob',type=float,default=1.0,help='1-dropout rate for generator')
	parser.add_argument('--noise',type=float,default=0.0,help='noise level std, added to input upon entry to dicriminator')

	parser.add_argument('--out',type=str,default="res",help='name of output file')
	parser.add_argument('--work_output_dir',type=str,default="./",help='path to default output dir')
	parser.add_argument('--model_out', type=str, default="tfmodel", help='name of model-output file')
	parser.add_argument('--model_text', type=str, default="text_model", help='name of textual model-output file')
	parser.add_argument('--log', type=str, help='name of log file')
	parser.add_argument('--gpu', type=str, default='0',help='which gpu to use')
	
	parser.add_argument('--rep', type=str, help='repository to work with' )
	parser.add_argument('--samples', type=str, help='samples for chosen action (learn, predict, get_mat, get_json_mat)' )
	parser.add_argument('--validation_samples', type=str, default='', help='validation samples for chosen action (learn, predict, get_mat, get_json_mat)' )
	parser.add_argument('--p_validation',type=float,default=0.25, help='when no validation samples given, in learn stage we randomize a portion of the pids to test. ')
	parser.add_argument('--model', type=str, help='model for predict, get_mat' )
	parser.add_argument('--get_mat', action='store_true', default=False, help='get matrix for model on samples/rep, output csv' )
	parser.add_argument('--sub_sample', type=int,default=0, help='samples subsample')

	FLAGS, unparsed = parser.parse_known_args()

	if (unparsed):
		print("Left with unparsed arguments:")
		print(unparsed)
		exit(0)

	tf.app.run()
