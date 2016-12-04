import sys
from base import Model
import tensorflow as tf
from tensorflow.python.ops import rnn_cell, seq2seq
from lncell import LayerNormalizedLSTMCell
import numpy as np
import math


class CharRNN(Model):
  def __init__(self, vocab_size=1000, batch_size=100,
               layer_depth=2, rnn_size=128, cell_type='LN_LSTM',
               seq_length=50, learning_rate=0.01, keep_prob=0.5, is_training=True):

    Model.__init__(self)

    self.is_training = is_training

    # RNN
    self.rnn_size = rnn_size
    self.layer_depth = layer_depth
    self.keep_prob = keep_prob

    if cell_type == 'GRU':
      cell = tf.nn.rnn_cell.GRUCell(rnn_size)
    elif cell_type == 'LSTM':
      cell = tf.nn.rnn_cell.LSTMCell(rnn_size, state_is_tuple=True)
    elif cell_type == 'LN_LSTM':
      cell = LayerNormalizedLSTMCell(rnn_size)
    else:
      cell = tf.nn.rnn_cell.BasicRNNCell(rnn_size)

    if is_training and keep_prob < 1:
      cell = tf.nn.rnn_cell.DropoutWrapper(cell, input_keep_prob=keep_prob)

    if cell_type == 'LSTM' or cell_type == 'LN_LSTM':
      cell = tf.nn.rnn_cell.MultiRNNCell([cell] * layer_depth, state_is_tuple=True)
    else:
      cell = tf.nn.rnn_cell.MultiRNNCell([cell] * layer_depth)

    if is_training and keep_prob < 1:
      cell = tf.nn.rnn_cell.DropoutWrapper(cell, output_keep_prob=keep_prob)

    self.cell = cell = rnn_cell.MultiRNNCell([cell] * layer_depth, state_is_tuple=True)
    self.input_data = tf.placeholder(tf.int64, [batch_size, seq_length], name="inputs")
    self.targets = tf.placeholder(tf.int64, [batch_size, seq_length], name="targets")
    self.initial_state = cell.zero_state(batch_size, tf.float32)

    with tf.device("/cpu:0"):
      self.embedding = tf.Variable(tf.random_uniform([vocab_size, rnn_size], -1.0, 1.0),
                                   name="embedding")
      inputs = tf.nn.embedding_lookup(self.embedding, self.input_data)

    with tf.variable_scope('softmax'):
      softmax_w = tf.get_variable("softmax_w", [rnn_size, vocab_size])
      softmax_b = tf.get_variable("softmax_b", [vocab_size], initializer=tf.constant_initializer(0.0))

    outputs, self.final_state = tf.nn.dynamic_rnn(cell, inputs, initial_state=self.initial_state)
    output = tf.reshape(tf.concat(1, outputs), [-1, rnn_size])

    with tf.variable_scope("output"):
      self.logits = tf.matmul(output, softmax_w) + softmax_b
      self.probs = tf.nn.softmax(self.logits)

    self.loss = tf.nn.sparse_softmax_cross_entropy_with_logits(self.logits, tf.reshape(self.targets, [-1]))
    self.cost = tf.reduce_mean(self.loss)
    self.global_step = tf.Variable(0, name='global_step', trainable=False)

    self.train_op= tf.train.AdamOptimizer(learning_rate).minimize(self.loss, global_step=self.global_step)


if __name__ == '__main__':
  model = CharRNN()
