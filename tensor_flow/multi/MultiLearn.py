
# coding: utf-8


#------------------------------------------------------------------------------------------------------------------------------
#
# This script is aimed at getting a model file (or json), samples, and multi category labels.
# General plan is:
# (1) Generate the relevant feature matrix.
# (2) Train a direct multicategory model based on labels OR a labels (channels) model (interpreting as bits) 
# (3) Allow for basic tools of saving deep model (in a way transferable back into the infrastructure) / retraining / testing / predicting.
#
#------------------------------------------------------------------------------------------------------------------------------

import keras
import numpy as np
import pandas as pd
import scipy.sparse as sps
from keras.layers import Dense, Input , Reshape, BatchNormalization , GaussianNoise, Dropout , LeakyReLU , Activation
from keras.models import Model
from keras.optimizers import SGD
from keras.models import model_from_json , load_model
from keras import regularizers
from time import time
from keras.callbacks import TensorBoard
import keras.backend as K
import tensorflow as tf
import sys, getopt , argparse
import datetime
import os
import sys
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"; 
# The GPU id to use, usually either "0" or "1";
# os.environ["CUDA_VISIBLE_DEVICES"]="1"
python_ext_path = '/nas1/UsersData/' + os.environ['USER'] +'/MR/Libs/Internal/MedPyExport/generate_binding/Release/rh-python27'
sys.path.insert(0,python_ext_path)
print 'path: ' + python_ext_path + ' added'
import med

# weighted binary cross loss function for multiple outcomes
#----------------------------------------------------------------------------------------------------------
def weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgt):
    y_pred_f = K.flatten(y_pred)
    y_true_f = K.flatten(y_true)
    y_pred_f = K.clip(y_pred_f, min_value=epsilon, max_value=1-epsilon)
    y_pred_f = wgt * K.log(y_pred_f) * y_true_f + (1-y_true_f)*K.log(1-y_pred_f);
    return -K.mean(y_pred_f)


#def w_bin_cross(y_true, y_pred):
#    return weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgt)	
#----------------------------------------------------------------------------------------------------------	
def weighted_binary_cross(epsilon, wgt):
    def w_bin_cross(y_true, y_pred):
		return weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgt)
    return w_bin_cross


# weighted binary cross loss function for multiple outcomes
#----------------------------------------------------------------------------------------------------------
def simple_multicategory_cross_loss_inner(y_true, y_pred, epsilon, wgt):
    y_pred_f = K.flatten(y_pred)
    y_true_f = K.flatten(y_true)
    y_pred_f = K.clip(y_pred_f, min_value=epsilon, max_value=1-epsilon)
    y_pred_f = wgt * K.log(y_pred_f)*y_true_f;
    return -K.mean(y_pred_f)

#def w_bin_cross(y_true, y_pred):
#    return weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgt)	
#----------------------------------------------------------------------------------------------------------	
def simple_multicategory_cross(epsilon, wgt):
    def w_bin_cross(y_true, y_pred):
		return simple_multicategory_cross_loss_inner(y_true, y_pred, epsilon, wgt)
    return w_bin_cross


# weighted binary cross loss function for multiple outcomes
#----------------------------------------------------------------------------------------------------------
def combination_multicategory_cross_loss_inner(y_true, y_pred, epsilon, beta):
	# regular loss (on the softmax)
	y_pred_f = K.flatten(y_pred)
	y_true_f = K.flatten(y_true)
	y_pred_f = K.clip(y_pred_f, min_value=epsilon, max_value=1-epsilon)
	y_pred_0 = 1 - y_pred_f
	y_pred_f = K.log(y_pred_f)*y_true_f + K.log(y_pred_0)*(1-y_true_f)
	loss1 = K.mean(y_pred_f)
	
	# a one vs. all loss , stretching preds
	# factor is 1/(e-1)
	factor = tf.constant(0.5819767)
	y_p = factor*(K.exp(y_pred)-1)
	y_p1 = K.flatten(K.clip(y_p, min_value=epsilon, max_value=1-epsilon))
	y_p0 = 1-y_p1
	y_p1 = K.log(y_p1)
	y_p0 = K.log(y_p0)
	y_t = K.clip(y_true_f, min_value=0.0, max_value=1.0)
	loss2 = K.mean(y_p1*y_true_f + (1-y_t)*y_p0)
	
	loss = -beta*loss1 - (1-beta)*loss2
	
	return loss

#def w_bin_cross(y_true, y_pred):
#    return weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgt)	
#----------------------------------------------------------------------------------------------------------	
def combination_multicategory_cross(epsilon, beta):
    def w_bin_cross(y_true, y_pred):
		return combination_multicategory_cross_loss_inner(y_true, y_pred, epsilon, beta)
    return w_bin_cross
	
	
	
# weighted binary cross loss function for multiple outcomes
#----------------------------------------------------------------------------------------------------------
def constrained_multicategory_loss_inner(y_true, y_pred, epsilon, beta, cmat):
	cm = tf.convert_to_tensor(cmat, dtype=tf.float32)
	y_t = tf.einsum('ij,kj->ik', y_true, cm)
	y_p = tf.einsum('ij,kj->ik', y_pred, cm)
	y_pred_clipped = K.clip(y_pred, min_value=epsilon, max_value=1-epsilon)
	y_p_clipped = K.clip(y_p, min_value=epsilon, max_value=1-epsilon)
	
	loss1 = K.mean(tf.reduce_mean(K.log(y_pred_clipped) * y_true))
	loss2 = K.mean(tf.reduce_mean(K.log(y_p_clipped) * y_t))
	
	loss = -beta * loss1 - (1 - beta)*loss2
	
	return loss 


#def w_bin_cross(y_true, y_pred):
#    return weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgt)	
#----------------------------------------------------------------------------------------------------------	
def constrained_multicategory_cross(epsilon, beta, cmat):
    def w_bin_cross(y_true, y_pred):
		return constrained_multicategory_loss_inner(y_true, y_pred, epsilon, beta, cmat)
    return w_bin_cross	
	
	
# weighted binary cross loss function for multiple outcomes
#----------------------------------------------------------------------------------------------------------
def weighted_multicategory_loss_inner(y_true, y_pred, epsilon, wgt_mat):
	y_pred_f = K.clip(y_pred, min_value=epsilon, max_value=1-epsilon)
	y_pred_f = K.log(y_pred_f)
	wm = tf.convert_to_tensor(wgt_mat, dtype=tf.float32)
	y_t = tf.einsum('ij,jk->ik', y_true, wm)
	y_pred_f = tf.reduce_mean(tf.multiply(y_t,y_pred_f))
	return -K.mean(y_pred_f)


#def w_bin_cross(y_true, y_pred):
#    return weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgt)	
#----------------------------------------------------------------------------------------------------------	
def weighted_multicategory_cross(epsilon, wgt_mat):
    def w_bin_cross(y_true, y_pred):
		return weighted_multicategory_loss_inner(y_true, y_pred, epsilon, wgt_mat)
    return w_bin_cross	
	

# weighted binary cross loss function for multiple outcomes
#----------------------------------------------------------------------------------------------------------
def channel_weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgtv):
	y_pred_f = K.flatten(y_pred)
	y_true_f = K.flatten(y_true)
	y_pred_f = K.clip(y_pred_f, min_value=epsilon, max_value=1-epsilon)
	y_wgt_f = wgtv * y_true
	y_wgt_f = K.flatten(y_wgt_f)
	y_pred_f = y_wgt_f * K.log(y_pred_f) * y_true_f + (1-y_true_f)*K.log(1-y_pred_f)
	
	return -K.mean(y_pred_f)
    

#def w_bin_cross(y_true, y_pred):
#    return weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgt)	
#----------------------------------------------------------------------------------------------------------	
def channel_weighted_binary_cross(epsilon, wgtv):
    def cw_bin_cross(y_true, y_pred):
		return channel_weighted_binary_cross_loss_inner(y_true, y_pred, epsilon, wgtv)
    return cw_bin_cross
	
	
# accuracy measures
#----------------------------------------------------------------------------------------------------------
def acc_on_0(y_true, y_pred):
    y_pred_f = 1-K.round(K.flatten(y_pred))
    y_true_f = 1-K.flatten(y_true)
    return K.sum(y_true_f * y_pred_f)/K.sum(y_true_f)

#----------------------------------------------------------------------------------------------------------
def acc_on_1(y_true, y_pred):
    y_pred_f = K.round(K.flatten(y_pred))
    y_true_f = K.flatten(y_true)
    return K.sum(y_true_f * y_pred_f)/K.sum(y_true_f)

#----------------------------------------------------------------------------------------------------------
def ratio_0_to_1(y_true, y_pred):
    y_pred_f = K.round(K.flatten(y_pred))
    y_true_f = K.flatten(y_true)
    return K.sum((1-y_true_f) * y_pred_f)/K.sum(y_true_f * y_pred_f)

#----------------------------------------------------------------------------------------------------------
def auc(y_true, y_pred):
	y_t = K.flatten(y_true)
	y_t = K.clip(y_t, min_value=0.0, max_value=1.0)
	y_p = K.flatten(y_pred)
	y_p = K.clip(y_p, min_value=0.0, max_value=1.0)
	
	auc = tf.metrics.auc(y_t, y_p)[1]
	K.get_session().run(tf.local_variables_initializer())
	return auc
	
#----------------------------------------------------------------------------------------------------------
def spec(y_true, y_pred):
    y_pred_f = 1-K.round(K.flatten(y_pred))
    y_true_f = 1-K.flatten(y_true)
    return K.sum(y_true_f * y_pred_f)/K.sum(y_true_f)		
	
#----------------------------------------------------------------------------------------------------------
def enpv(y_true, y_pred):
    y_pred_f = 1-K.round(K.flatten(y_pred))
    y_true_f = 1-K.flatten(y_true)
    return 1-K.sum(y_true_f * y_pred_f)/K.sum(y_pred_f)
	
#----------------------------------------------------------------------------------------------------------
def espec(y_true, y_pred):
    y_pred_f = 1-K.round(K.flatten(y_pred))
    y_true_f = 1-K.flatten(y_true)
    return 1-K.sum(y_true_f * y_pred_f)/K.sum(y_true_f)		
	
#----------------------------------------------------------------------------------------------------------
def npv(y_true, y_pred):
    y_pred_f = 1-K.round(K.flatten(y_pred))
    y_true_f = 1-K.flatten(y_true)
    return K.sum(y_true_f * y_pred_f)/K.sum(y_pred_f)
	
#----------------------------------------------------------------------------------------------------------
def ppv(y_true, y_pred):
	y_pred_f = K.round(K.flatten(y_pred))
	y_true_f = K.flatten(y_true)
	y_true_f = K.clip(y_true_f, min_value=0.0, max_value=1.0)
	return K.sum(y_true_f * y_pred_f)/K.sum(y_pred_f)	
	
#----------------------------------------------------------------------------------------------------------
def pr(y_true, y_pred):
	y_pred_f = K.round(K.flatten(y_pred))
	#y_all = y_pred_f
	#y_all = K.set_value(y_all,1.0)
	return K.sum(y_pred_f)/(K.cast(K.shape(y_pred_f)[0], 'float32'))
	
#----------------------------------------------------------------------------------------------------------
def sens(y_true, y_pred):
	y_pred_f = K.round(K.flatten(y_pred))
	y_true_f = K.flatten(y_true)
	y_true_f = K.clip(y_true_f, min_value=0.0, max_value=1.0)
	return K.sum(y_true_f * y_pred_f)/K.sum(y_true_f)
	
#----------------------------------------------------------------------------------------------------------
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

#----------------------------------------------------------------------------------------------------------
def parse_args():
	parser = argparse.ArgumentParser(description='Embedder.py arguments parser')
	parser.add_argument('--train', action='store_true', help='do training: if in_model given - continue training' )
	parser.add_argument('--test',  action='store_true', help='get model performance on a test set' )
	parser.add_argument('--predict',  action='store_true', help='calculate the predictions for the given samples' )
	parser.add_argument('--add_external_nn',  action='store_true', help='if out_med_model given, will add out_kmodel layers (if given), and if not in_kmodel layers (if given) as an ExternalNN predictor' )
	
	parser.add_argument('--rep', type=str , default = "/home/Repositories/THIN/thin_2018/thin.repository", help='repository to use' )
	parser.add_argument('--samples', type=str , default = "", help='samples to use' )
	parser.add_argument('--med_model', type=str , default = "", help='model generating the matrix' )
	parser.add_argument('--json', type=str , default = "", help='used if med_model is empty, the json defining the x matrix' )
	parser.add_argument('--out_med_model', type=str , default = "", help='if learning from json, can also output the model file' )
	parser.add_argument('--out_samples_prefix', type=str , default = "", help='if not empty will write train/validation/test samples' )
	parser.add_argument('--out_mat', type=str , default = "", help='write_model_matrix for all samples' )
	parser.add_argument('--p_validation', type=float , default=0.1 , help='size of training stage validation (from train set)' )
	parser.add_argument('--split', type=int , default=-100 , help='use split to define train/test (default: take all to train or test or predict, based on chosen action)' )
	
	parser.add_argument('--problem_type', type=str , default = "multicategory", help='multicategory (softmax to the category layer), multilabel (sigmoid for each channel) ' )
	parser.add_argument('--n_categ', type=int , default=2 , help='number of categories (for multicategory option)' )
	parser.add_argument('--n_channels', type=int , default=1 , help='number of channels (for multulabel option : will interpret y labels by their bits to get these)' )
	parser.add_argument('--winner_takes_all',  action='store_true', help='output index of the best category' )
	
	parser.add_argument('--in_kmodel', type=str, default = "", help='input keras model for continue training option' )
	parser.add_argument('--out_kmodel', type=str, default = "", help='output keras model : will prefix .h5 : bin model file, .layers : layers file we can transfer' )
	parser.add_argument('--out_preds', type=str, default = '', help='preds output file' )
	parser.add_argument('--nepochs', type=int, default=2 , help='nepochs to train' )
	
	# some model params
	parser.add_argument('--no_shuffle', action='store_true', default=False, help='dont use shuffle on matrix when training' )
	parser.add_argument('--l1', type=float, default=0.0, help='l1 regularizer : same for all layers' )
	parser.add_argument('--l2', type=float, default=0.0, help='l2 regularizer : same for all layers' )
	
	parser.add_argument('--nhidden', type=str, default="800,400,200", help='layers dimensions (last one is the encoding layer dimension)' )
	parser.add_argument('--dropout', type=str, default="0.0,0.0,0.0,0.0", help='dropout rates before every layer, and before the final prediction layer' )
	parser.add_argument('--add_bn',  action='store_true', help='add a batch normalization layer after the last layer' )
	parser.add_argument('--noise', type=float, default=0.0, help='gaussian noise used on last layer in training (after batch normalization)' )
	parser.add_argument('--wgt', type=float, default=1.0, help='weight to multiply loss coming from the positive outcome (to balance the many 0s)' )
	parser.add_argument('--wgt_mat', type=str, default="", help='a csv matrix of n_categ x n_categ, if given, will use a loss function weighted with these weights')
	parser.add_argument('--c_mat', type=str, default="", help='a csv matrix of n_constraints x n_categ, if given, will use a loss function that adds the constraints to loss')
	parser.add_argument('--beta', type=float, default=0.5, help='between 0 and 1 , how to combine the loss with the contraints loss' )
	parser.add_argument('--wgt_factor', type=float, default=1.0, help='if weights are given, factors all weights that are not 1.0 with this factor')
	parser.add_argument('--loss', type=str, default="simple", help='loss to use from: simple, combined (add beta), constrained (add c_mat), weighted (add wgt_mat)')

	parser.add_argument('--leaky', type=float, default=0.1, help='leaky ReLU rate (0.0 = ReLU)' )
	parser.add_argument('--lr', type=float, default=0.001, help='ADAM optimizer learning rate' )
	
	parser.add_argument('--batch_size', type=int, default=128, help='batch size to use' )

	# gpus : -1: all, 0/1 : gpu to use
	parser.add_argument('--gpu', nargs=1 , type=int, default=-1 , help='gpus : -1: all, 0/1 : gpu to use' )
	
	args = parser.parse_args()
	
	return args
	
#----------------------------------------------------------------------------------------------------------
def print_layers(model, fname):
	print "Printing model layers"	
	f_w = open(fname, "w")
	print "NLAYERS=",len(model.layers)
	for layer in model.layers:
		conf = layer.get_config()
		lwgt = layer.get_weights()
		name = conf['name']
		print "print_layers() name=",name
		if (name.startswith("dense")):
			w = np.array(lwgt[0])
			b = np.array(lwgt[1])
			dw = w.shape
			db = b.shape
			print "LAYER type=dense;name=%s;activation=%s;in_dim=%d;out_dim=%d;n_bias=%d"%(conf['name'],conf['activation'],dw[0],dw[1],dw[1])
			f_w.write("LAYER\ttype=dense;name=%s;activation=%s;in_dim=%d;out_dim=%d;n_bias=%d\n"%(conf['name'],conf['activation'],dw[0],dw[1],dw[1]))
			
			# write matrix
			for i in range(0,dw[0]):
				for j in range(0, dw[1]):
					f_w.write("%f" % w[i][j])
					if (j < dw[1]-1): f_w.write(",")
				f_w.write("\n")
				
			# write bias
			for j in range(0, dw[1]):
				f_w.write("%f" % b[j])
				if (j < dw[1]-1): f_w.write(",")
			f_w.write("\n")
						
		if (name.startswith("leaky")):
			print "LAYER type=leaky;name=%s;leaky_alpha=%f" % (conf['name'], conf['alpha'])
			f_w.write("LAYER\ttype=leaky;activation=leaky;name=%s;leaky_alpha=%f\n" % (conf['name'], conf['alpha']))
			
		if (name.startswith("dropout")):
			print "LAYER type=dropout;name=%s;drop_rate=%f" % (conf['name'], conf['rate'])
			f_w.write("LAYER\ttype=dropout;name=%s;drop_rate=%f\n" % (conf['name'], conf['rate']))
			
		if (name.startswith("batch_normalization")):
			w = np.array(lwgt)
			dw = w.shape
			print "LAYER type=batch_normalization;name=%s;dim=%d" % (conf['name'], dw[1])
			f_w.write("LAYER\ttype=batch_normalization;name=%s;dim=%d\n" % (conf['name'], dw[1]))
			for i in range(0,dw[0]):
				for j in range(0, dw[1]):
					f_w.write("%f" % w[i][j])
					if (j < dw[1]-1): f_w.write(",")
				f_w.write("\n")
		if (name.startswith("activation")):
			print "LAYER type=activation;activation=%s;out_dim=%d" % (conf['activation'], dw[1])
			f_w.write("LAYER\ttype=activation;activation=%s;out_dim=%d\n" % (conf['activation'], dw[1]))
		
	f_w.close()

	
#------------------------------------------------------------------------------------------------------------
# generating a keras model implemented by the given parameters
def get_model(args, xlen):
	
	# prep parameters
	layers_dim = [int(n) for n in args.nhidden.split(",")]
	n_layers = len(layers_dim)
	print "get_model(): layers_dim", layers_dim, n_layers
	
	dropouts = [float(x) for x in args.dropout.split(",")]
	for i in range(len(dropouts), n_layers + 1):
		dropouts.append(0)
		
	print "get_model(): dropouts ", args.dropout , dropouts

	if (args.problem_type == "multicategory"):
		ydim = args.n_categ
	elif (args.problem_type == "multilabel"):
		ydim = args.n_channels
	else:
		sys.exit("ERROR: problem_type ", args.problem_type, " unknown")
		
	print "get_model(): type ", args.problem_type , " ydim ", ydim
	
	inputs_raw = Input(shape=(xlen,))
	inputs = inputs_raw
	if (dropouts[0] > 0):
		inputs = Dropout(dropouts[0])(inputs)
	k = 1
	middle = inputs
	for dim in layers_dim:
		print "building layer with dim ", dim
		middle = Dense(dim, activation='linear', kernel_regularizer=regularizers.l1_l2(l2=args.l2,l1=args.l1))(middle)
		middle = LeakyReLU(alpha=args.leaky)(middle)
		#if (args.add_bn):
		#	middle = BatchNormalization()(middle)
		if (dropouts[k] > 0):
			middle = Dropout(dropouts[k])(middle)
		k = k + 1
	
	last = Dense(ydim, activation='linear', kernel_regularizer=regularizers.l1_l2(l2=args.l2,l1=args.l1))(middle)
	middle = LeakyReLU(alpha=args.leaky)(middle)	

	if (args.add_bn):
		last = BatchNormalization()(last)
		if (args.noise > 0):
			last = GaussianNoise(args.noise)(last)
	
	
	if (args.problem_type == "multicategory"):
		last = Activation('softmax')(last)
	elif (args.problem_type == "multilabel"):
		last = Activation('sigmoid')(last)

	final = last
	
	model = Model(inputs=inputs_raw, outputs=final)

		
	return model
	
#------------------------------------------------------------------------------------------------------------
def model_features_to_np(features):

	feature_names = list(features.get_feature_names())
	ncols = len(feature_names)

	nrows = features.data[feature_names[0]].size
	data = np.zeros((nrows, ncols), dtype=float)
	print("Got ", nrows, " x ", ncols)

	k = 0
	for name in feature_names:
		data[:, k] = features.data[name]
		k = k + 1
		
	fsamples = med.Samples()
	fsamples.import_from_sample_vec(features.samples)
	df_samples = fsamples.to_df()
	y = df_samples['outcome']
	
	return data, feature_names, y


#------------------------------------------------------------------------------------------------------------
def categ_to_sparse(ycateg, ydim, w):
	row = np.arange(ycateg.shape[0])
	if (w.shape[0] == row.shape[0]):
		print "!!! Adding weights !!!"
		data = w
	else:	
		data = np.full(row.shape, 1)
	ycsr = sps.csr_matrix((data, (row, ycateg)), shape=(ycateg.shape[0], ydim), dtype=np.float32)
	return ycsr
		

#------------------------------------------------------------------------------------------------------------
def categ_to_multilabel(ycateg, nchan):
	yint = ycateg.astype(np.int)
	ychan = np.zeros((ycateg.shape[0], nchan), dtype=np.float32)
	for i in range(nchan):
		yc = (yint & (1<<i)) > 0
		ychan[:,i] = yc.astype(np.float32)
		
	ychan
	
	return ychan

	
#------------------------------------------------------------------------------------------------------------
def get_medmodel_matrix(args, model, rep, samples):
	x = np.array((), dtype=float)
	y = np.array((), dtype=float)
	w = np.array((), dtype=float)
	if (samples.nSamples() > 0):
		model.apply(rep, samples, med.ModelStage.APPLY_FTR_GENERATORS, med.ModelStage.APPLY_FTR_PROCESSORS)	
		x, feature_names , y  = model_features_to_np(model.features)
		if (args.problem_type == "multicategory"):
			df = samples.to_df()
			if ("attr_weight" in df.columns):
				w = df["attr_weight"]
				if (args.wgt_factor != 1.0):
					print "read weights, now factoring them"
					c = (w != 1.0)
					c = c.astype(float)
					w = w + (args.wgt_factor - 1)*np.multiply(c,w)
			y = categ_to_sparse(y, args.n_categ, w)
		elif (args.problem_type == "multilabel"):
			y = categ_to_multilabel(y, args.n_channels)
	else:
		feature_names = []		
			
	return x,y,feature_names

#------------------------------------------------------------------------------------------------------------
# given a model file or json , rep & samples , generates the features matrix as df, also enables the creation
# of validation sets, use splits , etc.
#------------------------------------------------------------------------------------------------------------
def prep_data_from_model(args):

	need_mat_learn = False
	
	model = med.Model()
	if (args.json != ""):
		print("Initializing Model from json file ", args.json)
		model.init_from_json_file(args.json)
		need_mat_learn = True
	elif (args.med_model != ""):
		print("Reading Model from file ", args.med_model)
		model.read_from_file(args.med_model)
	else:
		sys.exit("ERROR: Must provide a model file or a json file")
	
	rep = med.PidRepository()
	rep.init(args.rep)
	model.fit_for_repository(rep)
	signalNamesSet = model.get_required_signal_names()
	print("Required Signals: ", signalNamesSet)
	
	print("Reading Samples")
	samples = med.Samples()
	samples.read_from_file(args.samples)
	df = samples.to_df()
	#print("==========================>", df)
	df_off_split = df[df['split'] != args.split]
	df_in_split = df[df['split'] == args.split]
	samples_off_split = med.Samples()
	samples_in_split = med.Samples()
	if (len(df_off_split) > 0):
		samples_off_split.from_df(df_off_split)
	if (len(df_in_split) > 0):
		samples_in_split.from_df(df_in_split)

	print("split ", args.split, " off split ssmples: ", len(df_off_split), " in split samples: ", len(df_in_split));
	
	ids = samples.get_ids()
	
	print("Reading Repository")

	rep.read_all(args.rep, ids, signalNamesSet)
	
	if (need_mat_learn):
		print("Learning model up to feature generators...")
		model.learn(rep, samples_off_split, med.ModelStage.LEARN_REP_PROCESSORS, med.ModelStage.APPLY_FTR_PROCESSORS)
		
	if (args.out_mat != ""):
		print("Writing matrix on all samples (in and off split) to ", args.out_mat)
		model.apply(rep, samples, med.ModelStage.APPLY_FTR_GENERATORS, med.ModelStage.APPLY_FTR_PROCESSORS)	
		model.write_feature_matrix(args.out_mat)

	print("Splitting off split samples to train/validation with p_validation", args.p_validation)
	samples_test = samples_in_split
	if ((args.test or args.predict) and (not args.train) and (args.split < 0) and (len(df_in_split) == 0)):
		samples_test = samples_off_split
	samples_validation = med.Samples()
	samples_train = med.Samples()
	if (args.train):
		samples_off_split.split_train_test(samples_train, samples_validation, args.p_validation)

	if (args.out_samples_prefix != ""):
		print("Writing samples files")
		s = ""
		if (args.split >= 0):
			s = "_S" + args.split
		samples_train.write_to_file(out_samples_prefix + s + "_train.samples")
		samples_validation.write_to_file(out_samples_prefix + s + "_validation.samples")
		samples_test.write_to_file(out_samples_prefix + s + "_test.samples")
	
	print ("(*) preparing train matrix")
	x_train, y_train, feature_names_t = get_medmodel_matrix(args, model, rep, samples_train)
	print ("(*) preparing validation matrix")
	x_validation, y_validation, feature_names_v = get_medmodel_matrix(args, model, rep, samples_validation)
	print ("(*) preparing test matrix")
	x_test, y_test, feature_names = get_medmodel_matrix(args, model, rep, samples_test)
	
	print("Got : train: ", x_train.shape, y_train.shape, "test: ", x_test.shape, y_test.shape, " validation: ", x_validation.shape, y_validation.shape, " nfeatures: ", len(feature_names))
	
	if (not (args.test or args.predict)):
		feature_names = feature_names_t
		
	return model, x_train, x_validation, x_test, y_train, y_validation, y_test, feature_names, samples_test
	

#####################################################################################################################	
def main(argv):
	args = parse_args()
	print("arguments---->", args)

	# generate train, test & validation matrices
	medmodel, x_train, x_validation, x_test, y_train, y_validation, y_test, feature_names, samples_test = prep_data_from_model(args)
	
	# read saved keras model if given
	if (args.in_kmodel != ""):
		fjson = args.in_kmodel + ".json";
		print "Initializing keras model from file " , fjson
		json_file = open(fjson , 'r')			
		loaded_model_json = json_file.read()
		json_file.close()
		model = model_from_json(loaded_model_json)
		model.load_weights(args.in_kmodel+".h5")
	else:
		model = get_model(args, len(feature_names))
	
	model.summary()
	
	if (args.gpu > 0):
		print "using gpu ", args.gpu[0]
		os.environ["CUDA_VISIBLE_DEVICES"]= str(args.gpu[0])

	opt = keras.optimizers.Adam(lr=args.lr)
	#opt = keras.optimizers.SGD(lr=args.lr, momentum=0.9)
	
	if (args.problem_type == "multilabel"):
		print "===> Using weighted_binary_cross() loss function"
		my_loss = weighted_binary_cross(epsilon=1e-8, wgt=args.wgt)
	elif (args.problem_type == "multicategory"):
		if (args.loss=="constrained" and args.c_mat != ""):
			print "===> Using contrained_multicategory_cross() loss function"
			c_mat = np.genfromtxt(args.c_mat, delimiter=',', dtype=np.float32)
			my_loss = constrained_multicategory_cross(epsilon=1e-8, beta=args.beta, cmat=c_mat)			
		
		elif (args.loss == "simple"):
			print "===> Using simple_multicategory_cross() loss function"
			my_loss = simple_multicategory_cross(epsilon=1e-8, wgt=args.wgt)
		elif (args.loss == "combined"):
			print "===> Using simple_multicategory_cross() loss function"
			my_loss = combination_multicategory_cross(epsilon=1e-5, beta=args.beta)	
			my_loss = combination_multicategory_cross(epsilon=1e-5, beta=args.beta)	
		elif (args.loss == "weighted" and args.wgt_mat != ""):
			print "===> Using weighted_multicategory_cross() loss function"
			wmat = np.genfromtxt(args.wgt_mat, delimiter=',', dtype=np.float32)
			my_loss = weighted_multicategory_cross(epsilon=1e-8, wgt_mat=wmat)
		else:
			print "ERROR: no valid loss function was chosen"
			sys.exit()
	
	
	if (args.train or args.test):
		model.compile(loss=my_loss, optimizer=opt, metrics=[auc, ppv, pr, sens])
	
	if (args.train):
		tf.keras.backend.set_learning_phase(0)
		print "Training with x_train ", x_train.shape, " y_train ", y_train.shape, " x_validation ", x_validation.shape, " y_validation ", y_validation.shape
		sess = tf.Session()
		sess.run(tf.local_variables_initializer())
		history = model.fit(x_train, y_train, verbose=1, epochs=args.nepochs, batch_size=args.batch_size, validation_data=(x_validation, y_validation), shuffle=not args.no_shuffle)
		
	if (args.test or args.predict):
		if (y_test.shape[0] == 0):
			x_test = x_train
			y_test = y_train
	
	if (args.test):	
		sess = tf.Session()
		sess.run(tf.local_variables_initializer())
		tf.keras.backend.set_learning_phase(0)
		print "Testing with x_test ", x_test.shape, " y_test ", y_test.shape
		evals = model.evaluate(x_test, y_test, verbose=1)
		print("Eval: ", evals)
			
	if (args.predict):
		print("=======> Running Predict on ", x_test.shape)
		sess = tf.Session()
		sess.run(tf.local_variables_initializer())
		tf.keras.backend.set_learning_phase(0)
		ypreds = model.predict(x_test, verbose=1)
		if(args.winner_takes_all):
			ypreds=np.argmax(ypreds,axis=1)
			np.savetxt(args.out_preds, ypreds, delimiter=",",fmt='%d')
			sdf = samples_test.to_df()
			sdf["pred_0"] = ypreds
			samples_test.from_df(sdf)
			samples_test.write_to_file(args.out_preds+".preds")
		else:	
			print(ypreds)
			np.savetxt(args.out_preds, ypreds, delimiter=",")
			
	if (args.train and args.out_kmodel != ''):
		print "Writing model to files"
		print("History: ", history, history.history)
		f_h = open(args.out_kmodel + ".history", "a")
		print >> f_h , history.history
		# write model to file
		model.summary()
		model_json = model.to_json()
		model_json
		with open(args.out_kmodel + ".json", "w") as json_file:
			json_file.write(model_json)
		model.save(args.out_kmodel + ".h5")
		print_layers(model, args.out_kmodel+".layers")
		with open(args.out_kmodel + '_command_line.txt', 'w') as f:
			f.write(' '.join(sys.argv[1:]))
			f.write('\n')

	if (args.out_med_model != ''):
		
		if (args.add_external_nn):
			f_kmodel = ""
			if (args.out_kmodel != ""):
				f_kmodel = args.out_kmodel+".layers"
			elif (args.in_kmodel != ""):
				f_kmodel = args.in_kmodel+".layers"
			if (f_kmodel != ""):
				print "Adding layers file ", f_kmodel , " to med model"
				medmodel.set_predictor("external_nn", "init_file="+f_kmodel)
			else:
				sys.exit("ERROR: add_external_nn is on but no out_kmodel or in_kmodel given")
		#TODO: insert keras model as ExternalNN model in medmodel !!!!
		medmodel.write_to_file(args.out_med_model)
		
	elif (args.add_external_nn):
		sys.exit("ERROR: add_external_nn is on but no out_med_model given")
			
	sys.exit()
	
if __name__ == "__main__":
   main(sys.argv[1:])
