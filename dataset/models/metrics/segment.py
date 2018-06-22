""" Contains metrics for segmentation """
import numpy as np

from ... import parallel
from . import ClassificationMetrics, get_components


class SegmentationMetricsByPixels(ClassificationMetrics):
    """ Metrics to assess segmentation models pixel-wise """
    pass


class SegmentationMetricsByInstances(ClassificationMetrics):
    """ Metrics to assess segmentation models by instances (connected components) """
    def __init__(self, targets, predictions, fmt='proba', num_classes=None, axis=None, threshold=.5, iot=.5):
        super().__init__(targets, predictions, fmt, num_classes, axis, threshold, confusion=False)
        self.iot = iot
        self.target_components = get_components(self.targets, batch=True)
        self.predicted_components = get_components(self.predictions, batch=True)
        self._calc_confusion()

    def _calc_confusion(self):
        self._confusion_matrix = np.zeros((self.targets.shape[0], self.num_classes - 1, 2, 2), dtype=np.int32)

        for i in range(len(self.target_components)):
            for j in range(len(self.target_components[i])):
                for k in range(self.num_classes - 1):
                    c = self.target_components[i][j]
                    coords = [slice(i, i+1)]
                    for d in range(c.shape[0]):
                        coords.append(slice(c[d, 0], c[d, 1]))
                    targ = self.targets[coords]
                    pred = self.targets[coords] * self.predictions[coords]
                    if np.sum(pred) / targ.size >= self.iot:
                        self._confusion_matrix[i, k, 1, 1] += 1
                    else:
                        self._confusion_matrix[i, k, 0, 1] += 1

        for i in range(len(self.predicted_components)):
            for j in range(len(self.predicted_components[i])):
                for k in range(self.num_classes - 1):
                    c = self.predicted_components[i][j]
                    coords = [slice(i, i+1)]
                    for d in range(c.shape[0]):
                        coords.append(slice(c[d, 0], c[d, 1]))
                    pred = self.predictions[coords]
                    targ = self.targets[coords]
                    if np.sum(pred) / targ.size < self.iot:
                        self._confusion_matrix[i, k, 1, 0] += 1

    def true_positive(self, label=None, *args, **kwargs):
        _ = args, kwargs
        return self._count(lambda l: self._confusion_matrix[:, l-1, 1, 1], label)

    def true_negative(self, label=None, *args, **kwargs):
        raise ValueError("True negaitve is inapplicable for instance-based metrics")

    def condition_positive(self, label=None, *args, **kwargs):
        _ = args, kwargs
        return self._count(lambda l: self._confusion_matrix[:, l-1, :, 1].sum(axis=1), label)

    def prediction_positive(self, label=None, *args, **kwargs):
        _ = args, kwargs
        return self._count(lambda l: self._confusion_matrix[:, l-1, 1].sum(axis=1), label)

    def total_population(self, *args, **kwargs):
        _ = args, kwargs
        return self._return(self._confusion_matrix[:, 0].sum(axis=(1, 2)))
