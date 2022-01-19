# Copyright (c) OpenMMLab. All rights reserved.

from mmdeploy.core import FUNCTION_REWRITER


@FUNCTION_REWRITER.register_rewriter(
    'mmpose.models.detectors.top_down.TopDown.forward')
def top_down__forward(ctx, self, img, *args, **kwargs):
    """Rewrite `forward_test` of TopDown for default backend."""
    features = self.backbone(img)
    if self.with_neck:
        features = self.neck(features)
    assert self.with_keypoint
    output_heatmap = self.keypoint_head.inference_model(
        features, flip_pairs=None)
    return output_heatmap
