"""
Subtraction SNR module for medium ACR phantom
"""
import math
import numpy as np
import matplotlib.pyplot as plt

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.fields.roi_fields import EllipseROIField
from pumpia.module_handling.fields.viewer_fields import MonochromeDicomViewerField
from pumpia.module_handling.fields.simple import (PercField,
                                                  FloatField,
                                                  BoolField,
                                                  IntField)
from pumpia.image_handling.roi_structures import EllipseROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.file_handling.dicom_tags import MRTags

from pumpia_acr_med.med_acr_context import MedACRContextManager, MedACRContext


class MedACRSubSNR(PhantomModule):
    """
    Module for subtraction method SNR on medium ACR phantom.
    """
    context_manager = MedACRContextManager()
    show_draw_rois_button = True
    show_analyse_button = True
    title = "Subtraction SNR"

    viewer1 = MonochromeDicomViewerField(row=0, column=0)
    viewer2 = MonochromeDicomViewerField(row=0, column=1, allow_changing_rois=False)

    size = PercField(70, verbose_name="Size (%)")
    ref_bandwidth = FloatField(1, verbose_name="Reference Bandwidth (Hz/px)")
    bw_cor_bool = BoolField(verbose_name="Bandwidth Correction")
    pix_size_bool = BoolField(verbose_name="Pixel Size Correction")
    avg_cor_bool = BoolField(verbose_name="Averages Correction")
    pe_cor_bool = BoolField(verbose_name="Phase Encode Correction")

    slice_used = IntField(read_only=True)
    im_bw = FloatField(verbose_name="Image Bandwidth (Hz/px)",
                       reset_on_analysis=True,
                       read_only=True)
    pixel_size_cor = FloatField(verbose_name="Pixel Size Correction",
                                reset_on_analysis=True,
                                read_only=True)
    pe_cor = FloatField(verbose_name="Phase Encode Correction",
                        reset_on_analysis=True,
                        read_only=True)
    avg_cor = FloatField(verbose_name="Averages Correction",
                         reset_on_analysis=True,
                         read_only=True)
    signal = FloatField(reset_on_analysis=True,
                        read_only=True)
    noise = FloatField(reset_on_analysis=True,
                       read_only=True)
    snr = FloatField(verbose_name="SNR",
                     reset_on_analysis=True,
                     read_only=True)
    cor_snr = FloatField(verbose_name="Corrected SNR",
                         reset_on_analysis=True,
                         read_only=True)

    signal_roi1 = EllipseROIField("SNR ROI1")
    signal_roi2 = EllipseROIField("SNR ROI2", allow_manual_draw=False)

    def draw_rois(self, context: MedACRContext, batch: bool = False) -> None:
        if isinstance(self.viewer1.image, Instance):
            image = self.viewer1.image
        elif isinstance(self.viewer1.image, Series):
            if context.inserts_slice == 10:
                self.slice_used = 4
                image = self.viewer1.image.instances[4]
            else:
                self.slice_used = 6
                image = self.viewer1.image.instances[6]
        else:
            return

        self.viewer1.load_image(image)
        factor = self.size / 100
        a = round(factor * context.x_length / 2)
        b = round(factor * context.y_length / 2)
        self.signal_roi1.register_roi(EllipseROI(image,
                                                 round(context.xcent),
                                                 round(context.ycent),
                                                 a,
                                                 b,
                                                 slice_num=image.current_slice))

    def post_roi_register(self, roi_input: EllipseROIField):
        if (roi_input == self.signal_roi1
            and self.signal_roi1.roi is not None
                and self.manager is not None):
            self.manager.add_roi(self.signal_roi1.roi)
            if isinstance(self.viewer2.image, Instance):
                image = self.viewer2.image
            elif isinstance(self.viewer2.image, Series):
                if self.slice_used == 4:
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
                self.signal = sum_roi
            roi_noise = np.std(roi_sub) / math.sqrt(2)
            if isinstance(roi_noise, float):
                self.noise = roi_noise
            snr = sum_roi / roi_noise
            if isinstance(snr, float):
                self.snr = snr

            cor_snr = snr

            image = roi1.image
            if isinstance(image, Instance):
                px_cor = 1
                bw_cor = 1
                avg_cor = 1
                pe_cor = 1

                if (self.pix_size_bool
                    and not (image.slice_thickness is None
                             or image.pixel_spacing is None)):
                    pix_size = image.slice_thickness, *image.pixel_spacing
                    self.logger.info("pixel size = %s", pix_size)
                    px_cor = 1 / math.prod(pix_size)
                    self.pixel_size_cor = px_cor

                if self.bw_cor_bool:
                    ref_bw = self.ref_bandwidth
                    try:
                        im_bw = image.get_value(MRTags.PixelBandwidth, True)
                        self.logger.info("image bandwidth = %s", im_bw)
                        try:
                            im_bw = float(im_bw)
                        except (ValueError, TypeError):
                            im_bw = ref_bw
                    except KeyError:
                        self.logger.info("image bandwidth not found")
                        im_bw = ref_bw
                    self.im_bw = im_bw
                    bw_cor = math.sqrt(im_bw / ref_bw)

                if self.avg_cor_bool:
                    try:
                        im_av = image.get_value(MRTags.NumberOfAverages, True)
                        self.logger.info("image averages = %s", im_av)
                        try:
                            im_av = float(im_av)
                        except (ValueError, TypeError):
                            im_av = 1
                    except KeyError:
                        im_av = 1
                        self.logger.info("image averages not found")
                    avg_cor = 1 / math.sqrt(im_av)
                    self.avg_cor = avg_cor

                if self.pe_cor_bool:
                    try:
                        im_pe = float(
                            image.get_value(MRTags.NumberOfPhaseEncodingSteps, True))
                        self.logger.info("phase encode steps = %s", im_pe)
                    except (KeyError, ValueError, TypeError):
                        try:
                            if image.get_value(MRTags.InPlanePhaseEncodingDirection, True) == "ROW":
                                num = int(
                                    image.get_value(MRTags.Rows, True))
                            else:
                                num = int(
                                    image.get_value(MRTags.Columns, True))
                            im_pe = float(
                                image.get_value(MRTags.PercentSampling, True)) * num
                            self.logger.info("phase encode steps = %s", im_pe)
                        except (KeyError, ValueError, TypeError):
                            im_pe = 1
                            self.logger.info("phase encode steps not found")
                    pe_cor = 1 / math.sqrt(im_pe)
                    self.pe_cor = pe_cor

                cor_snr = snr * px_cor * bw_cor * avg_cor * pe_cor

            self.cor_snr = float(cor_snr)

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
