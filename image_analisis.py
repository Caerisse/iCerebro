from __future__ import print_function
from __future__ import division
import torch
import numpy as np
import torchvision
from torchvision import models, transforms
import time
import os
from PIL import Image
import urllib.request


class ImageAnalisis:
    def __init__(
        self, 
        classification_model_name: str = 'resnext101_32x8d', 
        detection_model_name: str = 'fasterrcnn_resnet50_fpn',
    ):

        input_size = 224

        # Classification Model
        if classification_model_name == 'resnet18':
            self.model_classification = models.resnet18(pretrained=True)
        elif classification_model_name == 'resnet34':
            self.model_classification = models.resnet34(pretrained=True)
        elif classification_model_name == 'resnet50':
            self.model_classification = models.resnet50(pretrained=True)
        elif classification_model_name == 'resnet101':
            self.model_classification = models.resnet101(pretrained=True)
        elif classification_model_name == 'resnet152':
            self.model_classification = models.resnet152(pretrained=True)
        elif classification_model_name == 'alexnet':
            self.model_classification = models.alexnet(pretrained=True)
        elif classification_model_name == 'squeezenet1_0':
            self.model_classification = models.squeezenet1_0(pretrained=True)
        elif classification_model_name == 'vgg16':
            self.model_classification = models.vgg16(pretrained=True)
        elif classification_model_name == 'densenet161':
            self.model_classification = models.densenet161(pretrained=True)
        elif classification_model_name == 'densenet201':
            self.model_classification = models.densenet201(pretrained=True)
        elif classification_model_name == 'inception_v3':
            import spacy
            input_size = 299
            self.model_classification = models.inception_v3(pretrained=True)
        elif classification_model_name == 'googlenet':
            import spacy
            self.model_classification = models.googlenet(pretrained=True)
        elif classification_model_name == 'shufflenet_v2_x1_0':
            self.model_classification = models.shufflenet_v2_x1_0(pretrained=True)
        elif classification_model_name == 'mobilenet_v2':
            self.model_classification = models.mobilenet_v2(pretrained=True)
        elif classification_model_name == 'resnext50_32x4d':
            self.model_classification = models.resnext50_32x4d(pretrained=True)
        elif classification_model_name == 'resnext101_32x8d':
            self.model_classification = models.resnext101_32x8d(pretrained=True)
        elif classification_model_name == 'wide_resnet50_2':
            self.model_classification = models.wide_resnet50_2(pretrained=True)
        elif classification_model_name == 'mnasnet1_0':
            self.model_classification = models.mnasnet1_0(pretrained=True)
        else:
            raise ValueError('Incompatible classification model name')


        # Detection Model
        if detection_model_name == 'fasterrcnn_resnet50_fpn':
            self.model_detection = models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
        elif detection_model_name == 'maskrcnn_resnet50_fpn':
            self.model_detection = models.detection.maskrcnn_resnet50_fpn(pretrained=True)
        elif detection_model_name == 'keypointrcnn_resnet50_fpn':
            self.model_detection = models.detection.keypointrcnn_resnet50_fpn(pretrained=True)
        else:
            raise ValueError('Incompatible detection model name')


        # Detect if we have a GPU available
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.model_classification = self.model_classification.to(device)
        self.model_detection = self.model_detection.to(device)


        # Put models in evaluation mode
        self.model_classification.eval()
        self.model_detection.eval()


        # Define tensor transform
        self.transform_classification = transforms.Compose([
            transforms.Resize(input_size),
            transforms.CenterCrop(input_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        self.transform_detection = transforms.Compose([
            transforms.ToTensor()
        ])

        # Load Labels
        with open('imagenet_labels.txt') as f:
            self.labels = [line.strip()[10:] for line in f.readlines()]

        self.COCO_INSTANCE_CATEGORY_NAMES = [
            '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
            'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign',
            'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
            'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A',
            'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
            'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
            'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table',
            'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
            'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book',
            'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        self.COCO_PERSON_KEYPOINT_NAMES = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear', 'left_shoulder',
            'right_shoulder', 'left_elbow', 'right_elbow', 'left_wrist', 'right_wrist',
            'left_hip', 'right_hip', 'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]

    def classify(self, image_path, logger=None):
        t = time.process_time()

        if logger:
            logger.info("Image classify started")

        img = Image.open(image_path)
        img_t = self.transform_classification(img)
        batch_t = torch.unsqueeze(img_t, 0)

        out = self.model_classification(batch_t)

        _, indices = torch.sort(out, descending=True)
        percentage = torch.nn.functional.softmax(out, dim=1)[0] * 100

        if logger:
            for i in indices[0][:5]:
                logger.info("    Classify as {}, confidence {:.2f}".format(self.labels[i],percentage[i].item()))

            elapsed_time = time.process_time() - t
            logger.info("Image classify elapsed time: {:.0f} seconds".format(elapsed_time))

        return [[self.labels[i],percentage[i].item()] for i in indices[0][:5]]

    def detect(self, image_path, detection_threshold: float = 0.7, logger=None):
        t = time.process_time()

        if logger:
            logger.info("Object detection started")

        img = Image.open(image_path)
        img_t = self.transform_detection(img)

        predictions = self.model_detection([img_t])

        pred_class = [self.COCO_INSTANCE_CATEGORY_NAMES[i] for i in list(predictions[0]['labels'].numpy())]
        pred_boxes = [[(i[0], i[1]), (i[2], i[3])] for i in list(predictions[0]['boxes'].detach().numpy())]
        pred_score = list(predictions[0]['scores'].detach().numpy())

        pred_t = [pred_score.index(x) for x in pred_score if x > detection_threshold]
        if pred_t == []:
            if logger:
                elapsed_time = time.process_time() - t
                logger.info("Object detection elapsed time: {:.0f} seconds".format(elapsed_time))
                logger.info("Nothing detected above threshold")
            return None

        pred_t = pred_t[-1]

        pred_class = pred_class[:pred_t+1]
        pred_boxes = pred_boxes[:pred_t+1]
        pred_score = pred_score[:pred_t+1]
        pred_masks = [None for _ in range(pred_t+1)]
        pred_keypoints = [None for _ in range(pred_t+1)]

        if 'masks' in predictions[0]:
            pred_masks = (predictions[0]['masks']>0.5).squeeze().detach().cpu().numpy()
            pred_masks =  pred_masks[:pred_t+1]
        if 'keypoints' in predictions[0]:
            pred_keypoints_locations = list(predictions[0]['keypoints'].detach().numpy())
            pred_keypoints_locations = pred_keypoints_locations[:pred_t+1]
            pred_keypoints_scores = list(predictions[0]['keypoints_scores'].detach().numpy())
            pred_keypoints_scores = pred_keypoints_scores[:pred_t+1]
            for i in range(pred_t+1):
                pred_keypoints[i] = [
                    {
                        'label': label, 
                        'score': pred_keypoints_scores[i][j],
                        'location': pred_keypoints_locations[i][j][0:2],
                        'visibility': pred_keypoints_locations[i][j][2],
                    } 
                    for j, label in enumerate(self.COCO_PERSON_KEYPOINT_NAMES)
                ]


        out = []
        for i in range(len(pred_class)):
            if logger:
                logger.info("    Detected {}, confidence {:.2f}".format(
                    pred_class[i], pred_score[i]* 100)
                )
            out.append(
                {
                    'label': pred_class[i],
                    'boxes': pred_boxes[i],
                    'score': pred_score[i],
                    'masks': pred_masks[i],
                    'keypoints': pred_keypoints[i],
                }
            )
        if logger:     
            elapsed_time = time.process_time() - t
            logger.info("Object detection elapsed time: {:.0f} seconds".format(elapsed_time))

        return out

    def image_analisis(self, image_links, detection_threshold: float = 0.7, logger=None):
        checked_imgs = False
        temp_comments = []
        image_analisis_tags = []

        try:
            for link in image_links:
                urllib.request.urlretrieve(link, "temp_img.jpg")
                self.classify("temp_img.jpg", logger)
                self.detect("temp_img.jpg", detection_threshold, logger)
            checked_imgs = True
        finally:
            return checked_imgs, temp_comments, image_analisis_tags


















