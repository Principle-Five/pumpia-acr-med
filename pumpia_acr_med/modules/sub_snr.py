"""
Subtraction SNR module for medium ACR phantom
"""

import numpy as np

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import InputEllipseROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import PercInput, FloatOutput, IntOutput
from pumpia.image_handling.roi_structures import EllipseROI
from pumpia.file_handling.dicom_structures import Series, Instance

from ..acr_med_context import MedACRContextManagerGenerator, MedACRContext


class SubSNR(PhantomModule):
    context_manager_generator = MedACRContextManagerGenerator()
    viewer1 = MonochromeDicomViewerIO(row=0, column=0)
    viewer2 = MonochromeDicomViewerIO(row=0, column=1, allow_changing_rois=False)

    size = PercInput(70, verbose_name="Size (%)")

    slice_used = IntOutput()
    signal = FloatOutput()
    noise = FloatOutput()
    SNR = FloatOutput(verbose_name="SNR")

    signal_roi1 = InputEllipseROI("SNR ROI1")
    signal_roi2 = InputEllipseROI("SNR ROI2", allow_manual_draw=False)

    def draw_rois(self, context: MedACRContext, batch: bool = False) -> None:
        if isinstance(self.viewer1.image, Instance):
            image = self.viewer1.image
        elif isinstance(self.viewer1.image, Series):
            if context.inserts_slice == 10:
                self.slice_used.value = 4
                image = self.viewer1.image.instances[4]
            else:
                self.slice_used.value = 6
                image = self.viewer1.image.instances[6]
        else:
            return

        self.viewer1.load_image(image)
        factor = self.size.value / 100
        a = round(factor * context.x_length / 2)
        b = round(factor * context.y_length / 2)
        self.signal_roi1.register_roi(EllipseROI(image,
                                                 round(context.xcent),
                                                 round(context.ycent),
                                                 a,
                                                 b,
                                                 slice_num=image.current_slice))

    def post_roi_register(self, roi_input: InputEllipseROI):
        if (roi_input == self.signal_roi1
            and self.signal_roi1.roi is not None
                and self.manager is not None):
            self.manager.add_roi(self.signal_roi1.roi)
            if isinstance(self.viewer2.image, Instance):
                image = self.viewer2.image
            elif isinstance(self.viewer2.image, Series):
                if self.slice_used.value == 4:
                    image = self.viewer2.image.instances[4]
                else:
                    image = self.viewer2.image.instances[6]
            else:
                return

            self.viewer2.load_image(image)
            self.signal_roi2.register_roi(self.signal_roi1.roi.copy_to_image(image,
                                                                             image.current_slice,
                                                                             "SNR ROI",
                                                                             True))
            if self.signal_roi2.roi is not None:
                self.manager.add_roi(self.signal_roi2.roi)

    def link_rois_viewers(self):
        self.signal_roi1.viewer = self.viewer1
        self.signal_roi2.viewer = self.viewer2

    def analyse(self, batch: bool = False):
        if self.signal_roi1.roi is not None and self.signal_roi2.roi is not None:
            roi = self.signal_roi1.roi
            roi2 = self.signal_roi2.roi
            roi_sum = roi.pixel_values + roi2.pixel_values
            roi_sub = np.array(roi.pixel_values) - np.array(roi2.pixel_values)
            sum_roi = np.mean(roi_sum)
            if isinstance(sum_roi, float):
                self.signal.value = sum_roi
            roi_noise = np.std(roi_sub) / np.sqrt(2)
            if isinstance(roi_noise, float):
                self.noise.value = roi_noise
            snr = sum_roi / roi_noise
            if isinstance(snr, float):
                self.SNR.value = snr
