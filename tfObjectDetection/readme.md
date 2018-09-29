# Custom object detection using Tensorflow Object Detection API

## Problem to solve
Given a collection of images with a target object in many different shapes, lights, poses and numbers, train a model so that given a new image, a bounding box will be drawn around each of the target objects if they are present in the image.

## Steps to take
  - [Step 1 - Label the images](#step-1---label-the-images)
  - [Step 2 - Install Tensorflow Object Detection API](#step-2---install-tensorflow-object-detection-api)
  - [Step 3 - Prepare the labeled images as input](#step-3---prepare-the-labeled-images-as-tensorflow-input)
  - [Step 4 - Configure an object detection pipeline for training](#step-4---configure-an-object-detection-pipeline-for-training)
  - [Step 5 - Train and evalute the pipeline](#step-5---train-and-evalute-the-pipeline)
  - [Step 6 - Export the trained model for inferencing.](#step-6---export-the-trained-model-for-inferencing)
  - [Common errors and solutions](#common-errors-and-solutions)

### Step 1 - Label the images
You can use tools such as [VoTT](https://github.com/Microsoft/VoTT) or [LabelImg](https://github.com/tzutalin/labelImg) to label images.  Here we use VoTT to output data in Pascal VOC format. 
- Open the folder which contains your collection of images
- Put in labels.  You can train the model to recognize multiple types of objects, but here we will only recognize one type of objects, say, helmets.  
- Go through each image:
    - Draw a bounding box for each occurance of the target object, helmet, in that image, 
    - The default label is already applied, click on any other applicable label  
- Export to Pascal VOC format, the output folder will look like this:
```
    +Annotations (contains the label info in xml for each image)  
    +ImageSets  
      +Main  
        -{label}_train.txt  
        -{label}_val.txt  
    +JPEGImages (contains the image files)  
    -pascal_label_map.pbtxt (map of label and id)
```

### Step 2 - Install Tensorflow Object Detection API
Instead of starting from scratch, pick an Azure [Data Science VM](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/microsoft-ads.linux-data-science-vm-ubuntu), or [Deep Learning VM](https://azuremarketplace.microsoft.com/en-ca/marketplace/apps/microsoft-ads.dsvm-deep-learning) which has GPU attached.  This saves a lot of setup steps because the VMs come with a plethora of machine learning frameworks and tools installed, including Tensorflow.  We will use a Ubuntu 16.04 based DSVM here.  As for the VM size, you can start with a small size such as DS2_v3.  But when it's time to train, you'll need to scale it to a larger size, otherwise it will probably take many days to train on hundreds of images. 
-  Install Tensorflow [Object Detection API](https://github.com/tensorflow/models/tree/master/research/object_detection)
    -  ```git clone https://github.com/tensorflow/models.git```
    -  Most of the dependencies in the [installation doc](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/installation.md) are already installed on the DSVM.  However, make sure to follow the steps in each of the sections after the Dependencies section to perform the additional installation.  If these steps are not followed, you will see errors along the way.
-  Make sure the Tensorflow version installed on DSVM is compatible with git cloned Object Detection API.
    -  To check Tensorflow version, run ```python3 -c 'import tensorflow as tf; print(tf.__version__)'```
    -  To check Tensorflow installation location, run ```python3 -c 'help("tensorflow")'```
    -  Since the git cloned API is always the latest, run ```pip3 install --upgrade tensorflow-gpu``` to update Tensorflow to the latest.

### Step 3 - Prepare the labeled images as Tensorflow input
Tensorflow Object Detection API takes TFRecords as input, so we need to convert Pascal VOC data to TFRecords.  The script to do the convertion is located in the [object_detection/dataset_tools folder](https://github.com/tensorflow/models/tree/master/research/object_detection/dataset_tools).  You need to modify one of the files such as ```create_pascal_tf_record.py``` or ```create_pet_tf_record.py``` to convert your data.  Pick a script that converts data format close to yours.  Here we pick ```create_pascal_tf_record.py``` as our template, and modified [it](https://github.com/liupeirong/machinelearning/blob/master/TensorflowCustomObjectDetection/create_helmet_tf_record.py) to convert our VoTT output above.  Don't worry about making a mistake here, you will quickly see an error when you run the following command if you made a mistake.  Run the script to convert input data to TFRecords: 
```bash
python object_detection/dataset_tools/{my_create_tf_record}.py --set=train --data_dir=path/to/VoTToutputFolder --output_dir=path/to/TFRecordsOutput
python object_detection/dataset_tools/{my_create_tf_record}.py --set=val --data_dir=path/to/VoTToutputFolder --output_dir=path/to/TFRecordsOutput
``` 

### Step 4 - Configure an object detection pipeline for training
Instead of creating a model from scratch, a common practice is to train a pre-trained model listed in [Tensorflow Detection Model Zoo](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/detection_model_zoo.md) on your own dataset. These models are trained on well known datasets which may not include the type of object you are trying to detect, but we can leverage transfer learning to train these models to detect new types of object.  If you don't have GPU, pick a faster model over a more accurate one.  Here, we choose ssd_mobilenet_v1_coco. 

-  Download the pre-trained ssd_mobilenet_v1_coco from [Tensorflow Detection Model Zoo](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/detection_model_zoo.md).  It should include the following files:  
```
   -checkpoint  
   -frozen_inference_graph.pb  
   -model.ckpt.data-00000-of-00001  
   -model.ckpt.index  
   -model.ckpt.meta  
   -pipeline.config  
   -saved_model/saved_model.pb
```

-  Since we have a lot of artifacts, including input image data, TFRecords, pre-trained model, and training output, it's a good idea to organize the directory similar to what's suggested on [Tensorflow Object Detection github](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/running_locally.md#recommended-directory-structure-for-training-and-evaluation).  Our directory looks like this:
```
   +helmet_detection  
     +data (contains the output from VoTT)  
     +tfrecords (contains generated tfrecords)  
     +models  
       +ssd_mobilenet_v1_coco (contains downloaded ssd_mobilenet_v1_coco model)  
         +train (contains the training output files)
```

-  Edit pipeline.config with the following main modifications.  See our [sample config](https://github.com/liupeirong/machinelearning/blob/master/TensorflowCustomObjectDetection/pipeline.config).
   -  ```num_classes``` should be 1 if you are detecting one type of objects
   -  ```fine_tune_checkpoint``` should be path/to/downloaded_ssd_mobilenet_v1_coco/model.ckpt
   -  ```label_map_path``` should be path/to/pacal_label_map.pbtxt in the input data
   -  ```train_input_reader.tf_record_input_reader.input_path``` should be path/to/train_tfrecord
   -  ```eval_input_reader.tf_record_input_reader.input_path``` should be path/to/val_tfrecord
   
### Step 5 - Train and evalute the pipeline
From the tensorflow/models/research/ directory, run the following command to train the model: 
```bash  
python object_detection/model_main.py --pipeline_config_path=path/to/modified_pipeline.config --model_dir=path/to/training_output --alsologtostderr
```
On a GPU, this may take a couple hours for precision to go above, say, 80%, or loss to go below, say 1.  On a CPU, it could take much longer.  Run tensorboard to observe how precision and loss change as the model learns: 
```bash
tensorboard --logdir=path/to/training_output
```
If your images are of low quality, or the target object is very hard to detect in the images, or you have few images (less than 50), the mean average precision and total loss may appear erratic and unable to converge even after training for long time.  Start with easy to detect object and good quality images.   

### Step 6 - Export the trained model for inferencing
-  Pick a checkpoint in the training output folder which contains the following 3 files:  
```
    -model.ckpt-{checkpoint#}.data-00000-of-00001  
    -model.ckpt-{checkpoint#}.index  
    -model.ckpt-{checkpoint#}.meta  
```
-  From the tensorflow/models/research folder, run
  ```bash
  python object_detection/export_inference_graph.py --input_type=image_tensor --pipeline_config_path=path/to/pipeline.config --trained_checkpoint_prefix=path/to/training_output_dir/model.ckpt-{checkpoint#} --output_directory=path/to/output_model_files_for_inference
  ```
-  Modify [object_detection/object_detection_tutorial.ipynb](https://github.com/tensorflow/models/blob/master/research/object_detection/object_detection_tutorial.ipynb) to use our trained model and our test image.  Here's our [sample notebook](https://github.com/liupeirong/machinelearning/blob/master/TensorflowCustomObjectDetection/helmet_detection.ipynb). 
  
## Common errors and solutions
I've encountered the following main issues in this process of custom object detection.  With some research, I found that the community has found resolutions or workaround. 

1. Many errors can result by forgetting to run the following from tensorflow/models/research folder.  Make sure this is set in every shell session: 
```bash
export PYTHONPATH=$PYTHONPATH:`pwd`:`pwd`/slim
```
2. Error message "Value Error: First Step Cannot Be Zero"  
Resolution: https://github.com/tensorflow/models/issues/3794
3. Error message "_tensorflow.python.framework.errors_impl.DataLossError: Unable to open table file /usr/local/lib/python2.7/dist-packages/tensorflow/models/model/model.ckpt.data-00000-of-00001"  
Resolution: https://github.com/tensorflow/models/issues/2231. fine_tune_checkpoint=file_path/model.ckpt
4. Error message "TypeError: can't pickle dict_values objects"  
Resolution: https://github.com/tensorflow/models/issues/4780  