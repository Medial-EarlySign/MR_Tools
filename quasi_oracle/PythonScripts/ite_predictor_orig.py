#!/usr/bin/python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import tempfile
import numpy as np
import time

import tensorflow as tf
from tensorflow.contrib.learn.python.learn.datasets import base
from tensorflow.python.framework import random_seed
import collections
from DataReader import read_data_set,read_and_split_data_set

FLAGS = None
# Graph
# Initialization
def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.1)
    return tf.Variable(initial,name = "softmax_w")

def bias_variable(shape):
    initial = tf.constant(1.0, shape=shape)
    return tf.Variable(initial)

def nn(x, nFeatures, nHidden, keep_prob):

    w1 = weight_variable([nFeatures,nHidden])
    b1 = bias_variable([nHidden])
    hidden1 = tf.nn.relu(tf.matmul(x,w1) + b1)
    drop_hidden1 = tf.nn.dropout(hidden1, keep_prob)

    w2 = weight_variable([nHidden,nHidden])
    b2 = bias_variable([nHidden])
    hidden2 = tf.nn.relu(tf.matmul(drop_hidden1,w2) + b2)
    drop_hidden2 = tf.nn.dropout(hidden2, keep_prob)
    
    final_w = weight_variable([nHidden,1])
    final_b = bias_variable([1])
    y = tf.nn.xw_plus_b(drop_hidden2,final_w, final_b, name = 'prediction')


    return y,tf.trainable_variables()
    
def loss_function(y,y_,w_,vars,beta):

    loss = tf.reduce_mean(tf.multiply(tf.square(y_-y),w_))

    # L2 Regularization
    reg = 0
    for var in vars:
        loss += beta * tf.nn.l2_loss(var)
        reg += tf.nn.l2_loss(var)

    return tf.identity(loss,name='loss'),reg

# Training steps
def training(loss, learning_rate,clipping_ratio=0):

    optimizer = tf.train.AdamOptimizer(learning_rate)
    
    if (1):
        global_step = tf.Variable(0, name='global_step', trainable=False)
        train_op = optimizer.minimize(loss, global_step=global_step)
    else:
        gradients, variables = zip(*optimizer.compute_gradients(loss))
        gradients, _ = tf.clip_by_global_norm(gradients, clipping_ratio)
        train_op = optimizer.apply_gradients(zip(gradients, variables))    
    
    return train_op    

# Training
def learn_model(FLAGS):
    # Import data 
    start_time = time.time()
    data = read_and_split_data_set(FLAGS.data,FLAGS.test_p)
    print("Data import took %f secs\n"%(time.time()-start_time))
    
    ### START WITH GRAPH DEFINITION ###         
    device='/device:GPU:0'
    with tf.device(device):
        # Place holders
        x = tf.placeholder(tf.float32, [None, data.train.nfeatures],name = 'data')
        y_ = tf.placeholder(tf.float32 ,  name = 'labels')
        w_ = tf.placeholder(tf.float32,  name = 'weights')
        keep_prob = tf.placeholder(tf.float32, name = 'keep_prob')
        reg_beta = tf.placeholder(tf.float32, name = 'reg_beta')
        
        # NN
        y,vars= nn(x,data.train.nfeatures,FLAGS.nhidden,keep_prob)

        # Loss function
        loss,reg = loss_function(y,y_,w_,vars,reg_beta)

        # Training step 
        train_op = training(loss,FLAGS.learning_rate)
        
        # Saver
        all_vars =  tf.global_variables()
        saver = tf.train.Saver(var_list=all_vars)
    ### DONE WITH GRAPH DEFINITION ###
    
    # Training Session
    max_test_auc = 0
    with tf.Session(config = tf.ConfigProto(allow_soft_placement = True)) as sess:
        # Initialize
        sess.run(tf.global_variables_initializer())

        # Optimize
        start_time = time.time()
        nStuck=0
        min_test_loss=-1
        for i in range(FLAGS.max_num_batches):
            # Check Progress regularly
            if i % FLAGS.checkpoint_num_batches == FLAGS.checkpoint_num_batches - 1:
                train_loss,train_reg= sess.run([loss,reg], feed_dict={x: data.train.features, y_: data.train.labels, w_ : data.train.weights, keep_prob:1.0,reg_beta:FLAGS.reg_beta})
                test_loss= sess.run(loss, feed_dict={x: data.test.features, y_: data.test.labels, w_ : data.test.weights, keep_prob:1.0,reg_beta:0.0})
                
                if (min_test_loss==-1 or test_loss < min_test_loss):
                    min_test_loss = test_loss
                    nStuck = 0
                    saver.save(sess, FLAGS.predictor)
                else:
                    nStuck += 1
                    
                print('step %d, training loss = %g (reg=%g) test loss = %g Time = %f nStuck = %d' % (i,train_loss,train_reg,test_loss,time.time()-start_time,nStuck))
                if (nStuck == FLAGS.num_stuck):
                    break
                start_time = time.time()

            # Training step 
            batch = data.train.next_batch(FLAGS.batch_size)
            train_op.run(feed_dict={x: batch[0], y_: batch[1], w_ : batch[2], keep_prob:FLAGS.keep_prob,reg_beta:FLAGS.reg_beta})

# Predicting
def apply_model(FLAGS):            
    data = read_data_set(FLAGS.data)
    
    # Restore variables from disk and check performance
    with tf.Session(config = tf.ConfigProto(allow_soft_placement = True)) as sess:
        saver = tf.train.import_meta_graph(FLAGS.predictor+".meta")
        saver.restore(sess, FLAGS.predictor)

        # Define graph and required operators and placeholders
        graph = tf.get_default_graph()
        x = graph.get_tensor_by_name("data:0")
        y_ = graph.get_tensor_by_name("labels:0")
        w_ = graph.get_tensor_by_name("weights:0")
        keep_prob = graph.get_tensor_by_name("keep_prob:0")
        y = graph.get_tensor_by_name("prediction:0")
        loss = graph.get_tensor_by_name("loss:0")
        reg_beta = graph.get_tensor_by_name("reg_beta:0")

        # Get Predictions and print to file
        sess.run(tf.local_variables_initializer())
        yVals = sess.run(y,feed_dict={x: data.features, y_: data.labels, keep_prob: 1.0})

        # Print predictions to file
        with open(FLAGS.preds,"w") as out_file:
            for i in range(len(yVals)):
                out_file.write("%f\n"%yVals[i,0])

def main(_):
    
    # Random initialization
    tf.set_random_seed(FLAGS.seed)
    np.random.seed(FLAGS.seed)
    
    # Mode
    if (FLAGS.preds is None):
        learn_model(FLAGS)
    else:
        apply_model(FLAGS)                    
                    
####################################################

if __name__ == "__main__":

    # configuration file
    
    # Read command arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, required=True, help='train/validation data')
    parser.add_argument('--preds',type=str, help='prediction output file')
    parser.add_argument('--predictor',type=str, default="", help='predictor output file')
    
    parser.add_argument('--seed',type=int,default=134,help='random seed')
    
    parser.add_argument('--test_p', type=float, default=0.25 ,help='test data portion')
    parser.add_argument('--max_num_batches',type=int,default=1000,help='maximal # of optimization steps')
    parser.add_argument('--checkpoint_num_batches',type=int,default=50,help='# of optimization steps between printing')    
    parser.add_argument('--batch_size',type=int,default=200,help='size of batch for SGD')
    parser.add_argument('--num_stuck', type=int, default=10, help='# of iteration without test-set improvement before stopping')    
    
    parser.add_argument('--reg_beta',type=float,default=0.0,help='L2 regulation')
    parser.add_argument('--learning_rate',type=float,default=0.001,help='learning rate')
    parser.add_argument('--nhidden',type=int,default=100,help='# of cells in hidden layer')

    parser.add_argument('--keep_prob',type=float,default=1.0,help='1-dropout rate')

    
    FLAGS, unparsed = parser.parse_known_args()

    tf.app.run()
