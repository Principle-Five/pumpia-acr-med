"""
Subtraction SNR module for medium ACR phantom
"""
import math
import numpy as np
import matplotlib.pyplot as plt

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import InputEllipseROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import (PercInput,
                                                   FloatInput,
                                                   BoolInput,
                                                   FloatOutput,
                                                   IntOutput)
from pumpia.image_handling.roi_structures import EllipseROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.file_handling.dicom_tags import MRTags

from ..acr_med_context import MedACRContextManagerGenerator, MedACRContext


class MedACRSubSNR(PhantomModule):
    """
    Module for subtraction method SNR on medium ACR phantom.
    """
    context_manager_generator = MedACRContextManagerGenerator()
    viewer1 = MonochromeDicomViewerIO(row=0, column=0)
    viewer2 = MonochromeDicomViewerIO(row=0, column=1, allow_changing_rois=False)

    size = PercInput(70, verbose_name="Size (%)")
    ref_bandwidth = FloatInput(1, verbose_name="Reference Bandwidth (Hz/px)")
    bw_cor_bool = BoolInput(verbose_name="Bandwidth Correction")
    pix_size_bool = BoolInput(verbose_name="Pixel Size Correction")
    avg_cor_bool = BoolInput(verbose_name="Averages Correction")
    pe_cor_bool = BoolInput(verbose_name="Phase Encode Correction")

    slice_used = IntOutput()
    im_bw = FloatOutput(verbose_name="Image Bandwidth (Hz/px)")
    pixel_size_cor = FloatOutput(verbose_name="Pixel Size Correction")
    pe_cor = FloatOutput(verbose_name="Phase Encode Correction")
    avg_cor = FloatOutput(verbose_name="Averages Correction")
    signal = FloatOutput()
    noise = FloatOutput()
    snr = FloatOutput(verbose_name="SNR")
    cor_snr = FloatOutput(verbose_name="Corrected SNR")

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
            roi1 = self.signal_roi1.roi
            roi2 = self.signal_roi2.roi
            roi_sum = roi1.pixel_values + roi2.pixel_values
            roi_sub = np.array(roi1.pixel_values) - np.array(roi2.pixel_values)
            sum_roi = np.mean(roi_sum)
            if isinstance(sum_roi, float):
                self.signal.value = sum_roi
            roi_noise = np.std(roi_sub) / math.sqrt(2)
            if isinstance(roi_noise, float):
                self.noise.value = roi_noise
            snr = sum_roi / roi_noise
            if isinstance(snr, float):
                self.snr.value = snr

            cor_snr = snr

            image = roi1.image
            if isinstance(image, Instance):
                px_cor = 1
                bw_cor = 1
                avg_cor = 1
                pe_cor = 1

                if self.pix_size_bool.value:
                    pix_size = image.pixel_size
                    px_cor = 1 / math.prod(pix_size)
                    self.pixel_size_cor.value = px_cor

                if self.bw_cor_bool.value:
                    ref_bw = self.ref_bandwidth.value
                    try:
                        im_bw = image.get_tag(MRTags.PixelBandwidth)
                        try:
                            im_bw = float(im_bw)  # type: ignore
                        except (ValueError, TypeError):
                            im_bw = ref_bw
                    except KeyError:
                        im_bw = ref_bw
                    self.im_bw.value = im_bw
                    bw_cor = math.sqrt(im_bw / ref_bw)

                if self.avg_cor_bool.value:
                    try:
                        im_av = image.get_tag(MRTags.NumberOfAverages)
                        try:
                            im_av = float(im_av)  # type: ignore
                        except (ValueError, TypeError):
                            im_av = 1
                    except KeyError:
                        im_av = 1
                    avg_cor = 1 / math.sqrt(im_av)
                    self.avg_cor.value = avg_cor

                if self.pe_cor_bool.value:
                    try:
                        im_pe = float(
                            image.get_tag(MRTags.NumberOfPhaseEncodingSteps))  # type: ignore
                    except (KeyError, ValueError, TypeError):
                        im_pe = 1

                    if im_pe == 1:
                        try:
                            if image.get_tag(MRTags.InPlanePhaseEncodingDirection) == "ROW":
                                num = int(
                                    image.get_tag(MRTags.Rows))  # type: ignore
                            else:
                                num = int(
                                    image.get_tag(MRTags.Columns))  # type: ignore
                            im_pe = float(
                                image.get_tag(MRTags.PercentSampling)) * num  # type: ignore
                        except (KeyError, ValueError, TypeError):
                            im_pe = 1
                    pe_cor = 1 / math.sqrt(im_pe)
                    self.pe_cor.value = pe_cor

                cor_snr = snr * px_cor * bw_cor * avg_cor * pe_cor

            self.cor_snr.value = float(cor_snr)

    def load_commands(self):
        self.register_command("Show Subtraction Image", self.show_sub_image)

    def show_sub_image(self):
        """
        Shows the subtraction image
        """
        if self.signal_roi1.roi is not None and self.signal_roi2.roi is not None:
            roi1 = self.signal_roi1.roi
            roi2 = self.signal_roi2.roi
            sub_array = roi1.image.array[0] - roi2.image.array[0]
            plt.imshow(sub_array, cmap='grey')
            plt.colorbar()
            plt.show()
