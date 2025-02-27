"""
Author: taowen
Date: 2017-11-15

"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Just show warnings and errors
import numpy as np
import tensorflow as tf
import cv2
from PIL import Image
from model import net

# import tensorflow.contrib.eager as tfe
# tfe.enable_eager_execution()

# import tensorflow.contrib.slim as slim

import sys
sys.path.append("../")

from generate_dataset import decoder_tfRecords

# checkpoint_directory = './checkpoints/'

checkpoint_directory = './ckpt/'
log_directory = '../../log/video_interpolation/'
tfrecords_path = '../../Data/UCF101_dataset_train.tfrecords'

if not os.path.exists(checkpoint_directory):
    os.makedirs(checkpoint_directory)

BATCH_SIZE = 32
START_LEARNING_RATE = 1e-3
MAX_EPOCHES = 100000
height = 128
width = 128
depth = 3

swd = "./batch_test/"

frames, ground_truth = decoder_tfRecords(tfrecords_path)

img_batch, label_batch = tf.train.shuffle_batch(
    [frames, ground_truth],
    batch_size=BATCH_SIZE,
    capacity=5000,
    num_threads=4,
    min_after_dequeue=1000
)

# with tf.Session() as sess:
#     init_op = tf.initialize_all_variables()
#     sess.run(init_op)
#     coord=tf.train.Coordinator()
#     threads= tf.train.start_queue_runners(sess = sess,coord=coord)
#     for i in range(100,110):
#         example, l = sess.run([img_batch,label_batch])
#         # example = example/255.
#         # l = l/255.
#         for j in range(BATCH_SIZE):
#             # frame1 = Image.fromarray(example[j][:,:,0:3]/255., 'RGB')
#             # frame3 = Image.fromarray(example[j][:,:,3:6]/255., 'RGB')
#             # frame`2 = Image.fromarray(l[j]/255., 'RGB')
#             frame1 = example[j][:,:,0:3]
#             frame2 = example[j][:, :, 3:6]
#             frame3 = l[j]
#             # sigle_label = l[j]
#
#             cv2.imwrite(swd + 'batch_' + str(i) + '_' + 'size_' + str(j) + '_' + 'frame1' + '.png', frame1*255)
#             cv2.imwrite(swd + 'batch_' + str(i) + '_' + 'size_' + str(j) + '_' + 'frame2' + '.png', frame2*255)
#             cv2.imwrite(swd + 'batch_' + str(i) + '_' + 'size_' + str(j) + '_' + 'frame3' + '.png', frame3*255)
#
#             # print(example, l)
#
#     coord.request_stop()
#     coord.join(threads)


inputs = tf.placeholder(tf.float32, [None, height, width, depth*2], name='inputs')
labels = tf.placeholder(tf.float32, [None, height, width, depth], name='labels')

global_steps = tf.Variable(0, dtype=tf.int32, trainable=False, name='global_steps')
learning_rate = tf.train.exponential_decay(START_LEARNING_RATE, global_steps, 10000, 0.95, staircase=True)

# _, loss_l2 = net(inputs, labels)
predection = net(inputs)

loss_l2 = tf.nn.l2_loss(predection-labels)

loss_l2 = loss_l2/BATCH_SIZE

tf.summary.scalar('loss', loss_l2)
tf.summary.scalar('leaning rate', learning_rate)

optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss_l2, global_step=global_steps)

# for var in tf.trainable_variables():
#     tf.summary.histogram(var.name, var)

init = tf.global_variables_initializer()

merged = tf.summary.merge_all()


gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.4)

with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
    sess.run(init)
    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(coord=coord)
    writer = tf.summary.FileWriter(log_directory, sess.graph)

    ckpt = tf.train.get_checkpoint_state(checkpoint_directory)
    saver = tf.train.Saver()
    if ckpt and ckpt.model_checkpoint_path:
        print ckpt.model_checkpoint_path
        saver.restore(sess, ckpt.model_checkpoint_path)
    start = global_steps.eval()
    print "Start from:", start
    img_batch, label_batch = sess.run([img_batch, label_batch])
    for i in range(start, MAX_EPOCHES):
        _, _, loss, summary = sess.run([optimizer, predection, loss_l2, merged], feed_dict={inputs:img_batch, labels:label_batch})
        writer.add_summary(summary, i)

        global_steps.assign(i).eval()
        if i % 500 == 0:
            saver.save(sess, checkpoint_directory+'trained_ckpt_model',
                       global_step=global_steps)

        print 'Iteration = %s, loss = %s' % (str(i), str(loss))
writer.close()
