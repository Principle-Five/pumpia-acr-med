"""
Integral uniformity module for medium ACR phantom
"""
import numpy as np
from scipy.signal import convolve2d

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import InputEllipseROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import (PercInput,
                                                   BoolInput,
                                                   FloatOutput,
                                                   IntOutput)
from pumpia.image_handling.roi_structures import EllipseROI
from pumpia.file_handling.dicom_structures import Series, Instance

from ..med_acr_context import MedACRContextManagerGenerator, MedACRContext

LOW_PASS_KERNEL = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]]) / 16


class MedACRUniformity(PhantomModule):
    """
    Integral uniformity module for medium ACR phantom.
    """
    context_manager_generator = MedACRContextManagerGenerator()
    show_draw_rois_button = True
    show_analyse_button = True

    viewer = MonochromeDicomViewerIO(row=0, column=0)

    size = PercInput(70, verbose_name="Size (%)")
    kernel_bool = BoolInput(verbose_name="Apply Low Pass Kernel")

    slice_used = IntOutput()
    uniformity = FloatOutput(verbose_name="Uniformity (%)", reset_on_analysis=True)

    uniformity_roi = InputEllipseROI("Uniformity ROI")

    def draw_rois(self, context: MedACRContext, batch: bool = False) -> None:
        if isinstance(self.viewer.image, Instance):
            image = self.viewer.image
        elif isinstance(self.viewer.image, Series):
            if context.inserts_slice == 10:
                self.slice_used.value = 4
                image = self.viewer.image.instances[4]
            else:
                self.slice_used.value = 6
                image = self.viewer.image.instances[6]
        else:
            return

        self.viewer.load_image(image)
        factor = self.size.value / 100
        a = round(factor * context.x_length / 2)
        b = round(factor * context.y_length / 2)
        self.uniformity_roi.register_roi(EllipseROI(image,
                                                    round(context.xcent),
                                                    round(context.ycent),
                                                    a,
                                                    b,
                                                    slice_num=image.current_slice))

    def post_roi_register(self, roi_input: InputEllipseROI):
        if (roi_input == self.uniformity_roi
            and self.uniformity_roi.roi is not None
                and self.manager is not None):
            self.manager.add_roi(self.uniformity_roi.roi)

    def link_rois_viewers(self):
        self.uniformity_roi.viewer = self.viewer

    def analyse(self, batch: bool = False):
        if self.uniformity_roi.roi is not None:
            roi = self.uniformity_roi.roi
            if self.kernel_bool.value:
                array = roi.image.array[0]
                array = convolve2d(array, LOW_PASS_KERNEL, mode="same")
                mask = roi.mask
                pixel_values = list(array[mask])
            else:
                pixel_values = roi.pixel_values

            max_val = max(pixel_values)
            min_val = min(pixel_values)
            uniformity = 100 * (1 - ((max_val - min_val) / (max_val + min_val)))  # type: ignore
            self.uniformity.value = uniformity
