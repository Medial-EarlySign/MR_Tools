#!/usr/bin/python

# A GAN model with partial (masked) requirement of the required generated vector.
# Input : Vectors (Z1,....,Zn) in R^n and (I1,....,In) in {0,1}^n
# Output : A vector (X1,...,Xn) where Xi=Zi if Ii=1 such that p(X) is determined according to the training setls

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

import tensorflow as tf
from tensorflow.contrib.learn.python.learn.datasets import base
from tensorflow.python.framework import random_seed
from sklearn import metrics as skmetrics
import collections
import sys
import time
import re
from collections import defaultdict
from sklearn import decomposition
import os
import pandas as pd
from matrix_reader import write_to_file, DataSet


alpha_def = 0.2

# Noise
#----------------------------------------------------------------------------------------------------------------------------
def gaussian_noise_layer(input_layer, std):
	noise = tf.random_normal(shape=tf.shape(input_layer), mean=0.0, stddev=std, dtype=tf.float32)
	return input_layer + noise


#----------------------------------------------------------------------------------------------------------------------------
# The actual tf model
def tf_model(x, nHidden, actFuncs, keep_prob, nFeatures, noise_std, training,  reuse=False):

	with tf.variable_scope("deep_train/tf_model",reuse=reuse):

		# input data
		layer = x

		# add noise
		layer = tf.cond(training, lambda: tf.random_normal(shape=tf.shape(layer), mean=0.0, stddev=noise_std, dtype=tf.float32) + layer, lambda: layer)	

		# fully connected layers + dropout
		for n, func in zip(nHidden, actFuncs):
			if (func == 'relu'):
				dense = tf.layers.dense(layer,units=n,activation=tf.nn.relu, kernel_initializer=tf.contrib.layers.xavier_initializer())
			elif (func == 'leaky_relu'):
				dense = tf.layers.dense(layer, units=n, activation=tf.nn.leaky_relu, kernel_initializer=tf.contrib.layers.xavier_initializer())				
			else:
				dense = tf.layers.dense(layer, units=n, activation=tf.nn.sigmoid, kernel_initializer=tf.contrib.layers.xavier_initializer())
			layer = dense
			layer = tf.layers.dropout(layer, rate=1.0-keep_prob)
		
		#layer = tf.random_normal(shape=tf.shape(layer), mean=0.0, stddev=1.0, dtype=tf.float32)	# turn this to learn ONLY from random numbers
		last_layer = tf.layers.dense(layer, units=1, activation=tf.nn.sigmoid, kernel_initializer=tf.contrib.layers.xavier_initializer())
	return last_layer


#----------------------------------------------------------------------------------------------------------------------------
# model loss
#
def model_loss(py, y):
	#loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=py, labels=y))
	loss = tf.reduce_mean(tf.losses.log_loss(y,py))

	return tf.identity(loss, name='model_loss')

#----------------------------------------------------------------------------------------------------------------------------
# Regularization
def l2_reg(vars,beta):
	loss = 0
	total_parameters = 0

	for var in vars:
		shape = var.get_shape()
		variable_parameters = 1
		for dim in shape:
			variable_parameters *= dim.value
		total_parameters += variable_parameters

		loss += beta * tf.nn.l2_loss(var)

	print("Total # of params = %d . corrected beta = %g\n"%(total_parameters,beta/total_parameters))
	return loss/total_parameters

#----------------------------------------------------------------------------------------------------------------------------
# Discrimination AUC
def model_auc(py, y):
	labels = tf.reshape(y,[1,-1])
	preds = tf.reshape(tf.sigmoid(py), [1,-1])
		
	_auc =  tf.metrics.auc(labels, preds, name='auc')
		
	return _auc

#----------------------------------------------------------------------------------------------------------------------------
def model_training(model_loss, model_vars,  learning_rate):
	update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
	model_optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
	#gen_optimizer = tf.train.RMSPropOptimizer(learning_rate=learning_rate)
	model_step = model_optimizer.minimize(model_loss,var_list = model_vars)
	model_step = tf.group([model_step, update_ops])
	return model_step


#----------------------------------------------------------------------------------------------------------------------------
# NN structure
def expand_layers(function, nhiddens, functions, name=""):

	# Set no. of layers
	if (functions is None and nhiddens is not None):
		out_nhiddens = [int(n) for n in nhiddens.split(",")]
		out_functions = [function] * len(out_nhiddens)
	elif (functions is not None and nhiddens is not None):
		out_nhiddens = [int(n) for n in nhiddens.split(",")]
		out_functions = functions.split(",")
		if (len(out_nhiddens) != len(out_functions)):
			raise ValueError('Length mismatch between functions and layers')

		
	print(name, out_functions, out_nhiddens)

	return out_nhiddens,out_functions

#----------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------

	
#----------------------------------------------------------------------------------------------------------------------------
class deep_train(object):

#----------------------------------------------------------------------------------------------------------------------------
	# Initialization of graph
	def __init__(self, FLAGS, nFeatures, apply=False):

		# When in application mode ...
		if (apply):
			return

		# Logging ?
		if (FLAGS.log is not None):
			self.logFile = open(FLAGS.log, "w")
		else:
			self.logFile = None

		# if NN structure is given as (nLayer,nHidden,function) convert to (nHiddens,functions)
		self.ns,self.funcs = expand_layers(FLAGS.function,FLAGS.nhiddens,FLAGS.functions, "tf_deep_model")

		### START WITH GRAPH DEFINITION ###
		if (len(FLAGS.gpu) > 0):
			device = '/device:GPU:%s'%(FLAGS.gpu)
		else:
			device = '/device:CPU:0'
		print('Will use %s'%device)
		print('FLAGS.gpu:=%s'%(FLAGS.gpu))
		with tf.device(device):
			self.X = tf.placeholder(tf.float32, [None, nFeatures], name='X_mat')
			self.Y = tf.placeholder(tf.float32, [None, 1], name='Y_mat')
			self.keep_prob = tf.placeholder(tf.float32, name='keep_prob')
			self.training = tf.placeholder(tf.bool, name='training')

			self.net_out = tf_model(self.X, self.ns, self.funcs, self.keep_prob, nFeatures, FLAGS.noise, self.training)
			self.net_out = tf.identity(self.net_out, name='tf_model_out')
						
			self.vars = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope="deep_train/tf_model")

			self.loss = model_loss(self.net_out, self.Y)

			self.auc = model_auc(self.net_out, self.Y)
			self.running_vars_auc = tf.get_collection(tf.GraphKeys.LOCAL_VARIABLES, scope="auc")

			self.step = model_training(self.loss, self.vars, FLAGS.learning_rate)
		### DONE WITH GRAPH DEFINITION ###

#----------------------------------------------------------------------------------------------------------------------------
# Training
	def learn(self, sess, data, vdata, tdata, FLAGS):
                   
		# Optimize
		t0 = time.time()
				
		for i in range(FLAGS.batch_num):
			batch = data.next_batch(FLAGS.batch_size)
			X_batch = batch[0]
			Y_batch = batch[1]
			sess.run([self.step], feed_dict={self.X: X_batch, self.Y: Y_batch, self.keep_prob: FLAGS.keep_prob, self.training: True})

			# AUC
			if (i > 0 and i % FLAGS.auc_freq == 0):
				if (vdata.num_examples > 0):
					wauc = self.print_log("VALID", i, vdata, sess, FLAGS)
				wauc = self.print_log("TRAIN", i, data, sess, FLAGS)

#			if ((FLAGS.csvs_freq > 0) and (i>0) and (i % FLAGS.csvs_freq == 0)):
#				self.gen_csvs(i, vdata, vdata_unorm, sess, FLAGS)
			
			if (i % FLAGS.auc_freq == 0):
				dTime = (time.time() - t0)
				sys.stdout.write("Iterations: %s   Time %f\r"%(i,dTime))
				t0 = time.time()
				sys.stdout.flush()

		print()

		print("=======================================================================================================")
		print("training ended printing results for TRAIN,VALIDATION and TEST , split %d p_validation %.4f" % (FLAGS.split, FLAGS.p_validation))
		print("=======================================================================================================")
		#sess.run(tf.local_variables_initializer())
		self.print_log("TRAIN     ", i, data, sess, FLAGS, True)
		self.print_log("VALIDATION", i, vdata, sess, FLAGS, True)
		self.print_log("TEST      ", i, tdata, sess, FLAGS, True)
		print("=======================================================================================================")


#----------------------------------------------------------------------------------------------------------------------------
# Predicting
	def predict(self, sess, data, vdata, tdata, FLAGS):
                   
		print("=======================================================================================================")
		print("training ended printing results for TRAIN,VALIDATION and TEST , split %d p_validation %.4f" % (FLAGS.split, FLAGS.p_validation))
		print("=======================================================================================================")
		self.print_log("TRAIN     ", 0, data, sess, FLAGS, True)
		self.print_log("VALIDATION", 0, vdata, sess, FLAGS, True)
		self.print_log("TEST      ", 0, tdata, sess, FLAGS, True)
		print("=======================================================================================================")
		


#----------------------------------------------------------------------------------------------------------------------------
	def print_log(self, prefix, i, xdata, sess, FLAGS, full_test=False):
		n_take = min(xdata.num_examples, FLAGS.max_auc_batch)
		if full_test:
			n_take = min(xdata.num_examples, FLAGS.max_ever_auc_batch)
		if (n_take < 10):
			print ("%s : too few examples" % prefix)
			return -1

		batch = xdata.next_batch(n_take)
		full_X = batch[0]
		full_Y = batch[1]
		#full_Samples = batch[3]
		
		full_auc, full_loss = sess.run([self.auc , self.loss], feed_dict={self.X: full_X, self.Y: full_Y, self.keep_prob: 1.0, self.training: False})
#		full_auc, full_loss, full_pred = sess.run([self.auc , self.loss, self.net_out], feed_dict={self.X: full_X, self.Y: full_Y, self.keep_prob: 1.0, self.training: False})
		
		##print("====>", g_s2)
		if (self.logFile is not None):
			self.logFile.write("%s -- [iter %d] AUC = %.4f loss %.4f (%d/%d samples)" % (prefix, i, full_auc[1], full_loss, n_take, xdata.num_examples))
			self.logFile.flush()
		else:
			print("%s -- [iter %d] AUC = %.4f loss %.4f (%d/%d samples)" % (prefix, i, full_auc[1], full_loss, n_take, xdata.num_examples))
			sys.stdout.flush()
			
		#print(full_Samples, full_pred)
		sess.run(tf.variables_initializer(var_list=self.running_vars_auc))
		return full_auc[1]


#----------------------------------------------------------------------------------------------------------------------------
# Saving - generator  + allowed values
	def save(self, sess, path):
		saver = tf.train.Saver()	
		#saver = tf.train.Saver(var_list=self.vars)	
		print("Saving vars: ", self.vars)
		#saver = tf.train.Saver()		
		saver.save(sess, path)


#----------------------------------------------------------------------------------------------------------------------------
# Loading
	def restore(self,sess,path):
		saver = tf.train.Saver()
		saver = tf.train.import_meta_graph(path + ".meta")
		saver.restore(sess, path)
		
		print ("Restored vars: ", self.vars)
		
		# Define graph and required operators and placeholders
		self.graph = tf.get_default_graph()	
		#for op in self.graph.get_operations():
		#	print(op.name)
		#self.net_out = self.graph.get_tensor_by_name("deep_train/tf_model/tf_model_out:0")
		self.net_out = self.graph.get_tensor_by_name("tf_model_out:0")
		self.X = self.graph.get_tensor_by_name('X_mat:0')
		self.Y = self.graph.get_tensor_by_name('Y_mat:0')
		self.keep_prob = self.graph.get_tensor_by_name('keep_prob:0')
		self.training = self.graph.get_tensor_by_name('training:0')
		
	# Printing in human (& C++) readable format
	

#----------------------------------------------------------------------------------------------------------------------------
	def export(self,sess,fname):

		print("Printing model layers")
		f_w = open(fname, "w")

		# Layers
		#p = re.compile('deep_train\/tf_model\/dense(\S*)\/(\S+):0')
		p = re.compile('deep_train\/tf_model\/(\S*)\/(\S+):0')
		print("self.vars is :: ", self.vars)
		data = defaultdict(dict)
		for var in self.vars:
			matcher = p.match(var.name)
			if (matcher is None):
				raise ValueError("Cannot parser variable name %s\n"%var.name)

			if (matcher.group(1) == ""):
				layer_name = "layer_0"
			else:
				layer_name = "layer"+matcher.group(1)
			data[layer_name][matcher.group(2)] = var.eval()

		final_layer_index = len(data.keys())-1
		for index,layer in enumerate(sorted(data.keys())):
			inDim,outDim = data[layer]['kernel'].shape
			print("LAYER\ttype=dense;name=%s;activation=linear;in_dim=%d;out_dim=%d;n_bias=%d"%(layer,inDim,outDim,outDim))
			f_w.write("LAYER\ttype=dense;name=%s;activation=linear;in_dim=%d;out_dim=%d;n_bias=%d\n" % (layer, inDim, outDim, outDim))
			np.savetxt(f_w, data[layer]['kernel'], delimiter=',')
			np.savetxt(f_w, data[layer]['bias'].reshape(1,-1), delimiter=',')

			if (index != final_layer_index):
				if (self.funcs[index] == "leaky_relu"):
					print("LAYER\ttype=leaky;activation=leaky;name=leaky_relu_%d;leaky_alpha=%f" % (index, alpha_def))
					f_w.write("LAYER\ttype=leaky;activation=leaky;name=leaky_relu_%d;leaky_alpha=%f\n" % (index, alpha_def))
				elif (self.funcs[index] == "relu"):
					print("LAYER\ttype=leaky;activation=relu;name=relu_%d" % index)
					f_w.write("LAYER\ttype=leaky;activation=relu;name=relu_%d\n" % index)
				else:
					print("LAYER\ttype=leaky;activation=sigmoid;name=sigmoid_%d" % index)
					f_w.write("LAYER\ttype=leaky;activation=sigmoid;name=sigmoid_%d\n" % index)
			else:
				# last sigmoid
				print("LAYER\ttype=leaky;activation=sigmoid;name=sigmoid_%d" % index)
				f_w.write("LAYER\ttype=leaky;activation=sigmoid;name=sigmoid_%d\n" % index)			
'''		
#----------------------------------------------------------------------------------------------------------------------------
	def gen_csvs(self, niter, data, data_real, sess, FLAGS):
		print("generating results in iter ", niter)
		# Generate output
		idx = np.random.randint(data.num_examples, size=FLAGS.nout)
		rem_idx = np.random.randint(data.num_examples, size=FLAGS.nout)
		to_process = data.features[idx,:]
		if data_real is None:
			x = data.features[idx,:]
		else:
			x = data_real.features[idx,:]
		em = data.exists_mask[idx,:]
		rem = data.exists_mask[rem_idx,:]
		
		if (FLAGS.mask is None):
			masks = np.random.binomial(size=x.shape, n=1, p=FLAGS.ind_p) #p=0) #p=FLAGS.ind_p)
		else:
			masks = np.tile(FLAGS.mask,[x.shape[0],1])
		
		masks = em * masks
		# masks[:,:] = 1 # add only for sanity test
		GAN_data,Z_data = self.generate_from_masks_final(sess,to_process,masks, FLAGS.use_normal_noise)
		
		
		fake_channels = em - masks
		#
		# at this point we have:
		# x     : original selected full data
		# em    : mask of known channels on x
		# masks : submask of em, the channels that were used to predict
		#
		
		not_em = np.ones_like(em) - em
		not_fake = np.ones_like(fake_channels) - fake_channels
		
		# Save
		name = os.path.join(FLAGS.work_output_dir, FLAGS.out + ".iter_" + str(niter))
		x = em*x + FLAGS.missing_value*not_em
		write_to_file(data.header, data.samples[idx,:], x, name + ".real.csv")
		gan_em = em*GAN_data + FLAGS.missing_value*not_em
		write_to_file(data.header, data.samples[idx,:], gan_em, name + ".fake.csv")		
		fake = fake_channels*GAN_data + FLAGS.missing_value*not_fake
		write_to_file(data.header, data.samples[idx,:], fake, name + ".only_fake.csv")		
		write_to_file(data.header, data.samples[idx,:], fake_channels,name + ".fake_mask.csv")
		
		# generating a comparison report per feature
		# for each feature we calculate the distribution of values when rounded to 0.01 and print a table of numbers and probabilities
		
		self.get_comparisons(niter, data.header, idx, x, fake, sess, FLAGS)
		
		self.export(sess, name+".exported_model")
		#ncols = GAN_data.shape[1]
		#for i in range(ncols):
		#	for j in range(i+1,ncols):
		#		print("%d\t%d\tCorrelation\t%f\t%f"%(i,j,np.corrcoef(data.features[:, i],data.features[:, j])[0,1],np.corrcoef(GAN_data[:, i],GAN_data[:, j])[0,1]))
		#	print()
	
		# sys.exit() # add only for sanity test

'''

                  
        
