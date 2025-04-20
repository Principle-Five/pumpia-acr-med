"""
Slice width for Medium ACR Phantom
"""
import math
import numpy as np
from scipy.optimize import curve_fit

import matplotlib.pyplot as plt

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import BaseInputROI, InputRectangleROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import FloatInput, PercInput, FloatOutput, StringOutput
from pumpia.image_handling.roi_structures import RectangleROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.utilities.array_utils import nth_max_widest_peak
from pumpia.utilities.feature_utils import flat_top_gauss

from pumpia_acr_med.med_acr_context import MedACRContextManagerGenerator, MedACRContext

# ROI sizes in mm
ROI_HEIGHT = 2
ROI_WIDTH = 120
BOTTOM_OFFSET = 0.5
TOP_OFFSET = -3.5


class MedACRSliceWidth(PhantomModule):
    """
    Calculates slice width for the medium ACR phantom by fitting to a flat top gaussian.

    Overall slice width is calculated by taking the geometric mean
    of the top and bottom ramp widths.
    """
    context_manager_generator = MedACRContextManagerGenerator()
    show_draw_rois_button = True
    show_analyse_button = True

    viewer = MonochromeDicomViewerIO(row=0, column=0)

    tan_theta = FloatInput(0.1, verbose_name="Tan of ramp angle")
    max_perc = PercInput(50, verbose_name="Width position (% of max)")

    ramp_dir = StringOutput(verbose_name="Ramp Direction")

    expected_width = FloatOutput(verbose_name="Expected Width (mm)", reset_on_analysis=True)
    top_ramp_width = FloatOutput(verbose_name="Top Ramp Width (mm)", reset_on_analysis=True)
    bottom_ramp_width = FloatOutput(verbose_name="Bottom Ramp Width (mm)", reset_on_analysis=True)
    slice_width = FloatOutput(verbose_name="Slice Width (mm)", reset_on_analysis=True)

    top_ramp = InputRectangleROI()
    bottom_ramp = InputRectangleROI()

    def draw_rois(self, context: MedACRContext, batch: bool = False) -> None:

        if isinstance(self.viewer.image, Instance):
            image = self.viewer.image
        elif isinstance(self.viewer.image, Series):
            if context.inserts_slice == 10:
                image = self.viewer.image.instances[10]
            else:
                image = self.viewer.image.instances[0]
        else:
            return

        pixel_size = image.pixel_size
        pixel_height = pixel_size[1]
        pixel_width = pixel_size[2]

        self.expected_width.value = pixel_size[0]

        if context.res_insert_side == "bottom" or context.res_insert_side == "top":
            self.ramp_dir.value = "Horizontal"
            box_height = ROI_HEIGHT / pixel_height
            box_width = ROI_WIDTH / pixel_width
            top_pix_offset = TOP_OFFSET / pixel_height
            bottom_pix_offset = BOTTOM_OFFSET / pixel_height

            top_xmin = bottom_xmin = round(context.xcent - box_width / 2)
            top_xmax = bottom_xmax = round(context.xcent + box_width / 2)

            if context.res_insert_side == "bottom":
                top_ymin = round(context.ycent + top_pix_offset)
                top_ymax = round(context.ycent + top_pix_offset + box_height)
                bottom_ymin = round(context.ycent + bottom_pix_offset)
                bottom_ymax = round(context.ycent + bottom_pix_offset + box_height)
            else:
                top_ymin = round(context.ycent - top_pix_offset - box_height)
                top_ymax = round(context.ycent - top_pix_offset)
                bottom_ymin = round(context.ycent - bottom_pix_offset - box_height)
                bottom_ymax = round(context.ycent - bottom_pix_offset)
        else:
            self.ramp_dir.value = "Vertical"
            box_height = ROI_HEIGHT / pixel_width
            box_width = ROI_WIDTH / pixel_height
            top_pix_offset = TOP_OFFSET / pixel_width
            bottom_pix_offset = BOTTOM_OFFSET / pixel_width

            top_ymin = bottom_ymin = round(context.ycent - box_width / 2)
            top_ymax = bottom_ymax = round(context.ycent + box_width / 2)

            if context.res_insert_side == "right":
                top_xmin = round(context.xcent + top_pix_offset)
                top_xmax = round(context.xcent + top_pix_offset + box_height)
                bottom_xmin = round(context.xcent + bottom_pix_offset)
                bottom_xmax = round(context.xcent + bottom_pix_offset + box_height)
            else:
                top_xmin = round(context.xcent - top_pix_offset - box_height)
                top_xmax = round(context.xcent - top_pix_offset)
                bottom_xmin = round(context.xcent - bottom_pix_offset - box_height)
                bottom_xmax = round(context.xcent - bottom_pix_offset)

        top_roi = RectangleROI(image,
                               top_xmin,
                               top_ymin,
                               top_xmax,
                               top_ymax,
                               slice_num=image.current_slice,
                               replace=True)
        self.top_ramp.register_roi(top_roi)

        bottom_roi = RectangleROI(image,
                                  bottom_xmin,
                                  bottom_ymin,
                                  bottom_xmax,
                                  bottom_ymax,
                                  slice_num=image.current_slice,
                                  replace=True)
        self.bottom_ramp.register_roi(bottom_roi)

    def post_roi_register(self, roi_input: BaseInputROI):
        if (roi_input.roi is not None
            and self.manager is not None
                and (roi_input is self.top_ramp or roi_input is self.bottom_ramp)):
            self.manager.add_roi(roi_input.roi)

    def link_rois_viewers(self):
        self.top_ramp.viewer = self.viewer
        self.bottom_ramp.viewer = self.viewer

    def analyse(self, batch: bool = False):
        if (self.top_ramp.roi is not None
            and self.bottom_ramp.roi is not None
                and self.viewer.image is not None):
            if self.ramp_dir.value == "Vertical":
                top_prof = self.top_ramp.roi.v_profile
                bottom_prof = self.bottom_ramp.roi.v_profile
                pix_size = self.viewer.image.pixel_size[1]
            else:
                top_prof = self.top_ramp.roi.h_profile
                bottom_prof = self.bottom_ramp.roi.h_profile
                pix_size = self.viewer.image.pixel_size[2]

            self.expected_width.value = self.viewer.image.pixel_size[0]

            divisor = 100 / self.max_perc.value
            c_coeff = 2 * math.sqrt(2 * math.log(divisor))

            top_fwhm_peak = nth_max_widest_peak(top_prof, divisor)
            bottom_fwhm_peak = nth_max_widest_peak(bottom_prof, divisor)

            top_init = (top_fwhm_peak.minimum,
                        top_fwhm_peak.maximum,
                        (top_fwhm_peak.maximum - top_fwhm_peak.minimum) / 4,
                        np.max(top_prof) - np.min(top_prof),
                        np.min(top_prof))
            top_indeces = np.indices(top_prof.shape)[0]
            top_fit, _ = curve_fit(flat_top_gauss,
                                   top_indeces,
                                   top_prof,
                                   top_init)
            top_fwhm = abs(top_fit[1] - top_fit[0]) + (c_coeff * top_fit[2])

            bottom_init = (bottom_fwhm_peak.minimum,
                           bottom_fwhm_peak.maximum,
                           (bottom_fwhm_peak.maximum - bottom_fwhm_peak.minimum) / 4,
                           np.max(bottom_prof) - np.min(bottom_prof),
                           np.min(bottom_prof))
            bottom_indeces = np.indices(bottom_prof.shape)[0]
            bottom_fit, _ = curve_fit(flat_top_gauss,
                                      bottom_indeces,
                                      bottom_prof,
                                      bottom_init)
            bottom_fwhm = abs(bottom_fit[1] - bottom_fit[0]) + (c_coeff * bottom_fit[2])

            tan_theta = self.tan_theta.value

            top_width = top_fwhm * tan_theta * pix_size
            bottom_width = bottom_fwhm * tan_theta * pix_size

            self.top_ramp_width.value = top_width
            self.bottom_ramp_width.value = bottom_width

            self.slice_width.value = math.sqrt(top_width * bottom_width)

    def load_commands(self):
        self.register_command("Show Profiles", self.show_profiles)

    def show_profiles(self):
        """
        Shows the ROI profiles
        """
        if (self.top_ramp.roi is not None
            and self.bottom_ramp.roi is not None
                and self.viewer.image is not None):
            if self.ramp_dir.value == "Vertical":
                top_prof = self.top_ramp.roi.v_profile
                bottom_prof = self.bottom_ramp.roi.v_profile
                pix_size = self.viewer.image.pixel_size[1]
            else:
                top_prof = self.top_ramp.roi.h_profile
                bottom_prof = self.bottom_ramp.roi.h_profile
                pix_size = self.viewer.image.pixel_size[2]

            tan_theta = self.tan_theta.value

            divisor = 100 / self.max_perc.value

            top_indeces = np.indices(top_prof.shape)[0]
            bottom_indeces = np.indices(bottom_prof.shape)[0]
            top_x_locs = top_indeces * tan_theta * pix_size
            bottom_x_locs = bottom_indeces * tan_theta * pix_size

            plt.clf()
            plt.plot(top_x_locs, top_prof, label="Top Profile")

            try:

                top_fwhm_peak = nth_max_widest_peak(top_prof, divisor)
                top_init = (top_fwhm_peak.minimum,
                            top_fwhm_peak.maximum,
                            (top_fwhm_peak.maximum - top_fwhm_peak.minimum) / 4,
                            np.max(top_prof) - np.min(top_prof),
                            np.min(top_prof))

                top_fit, _ = curve_fit(flat_top_gauss,
                                       top_indeces,
                                       top_prof,
                                       top_init)

                top_fitted = flat_top_gauss(top_indeces, *top_fit)
                plt.plot(top_x_locs, top_fitted,
                         label="Top Fit")

            except RuntimeError:
                pass

            plt.plot(bottom_x_locs, bottom_prof, label="Bottom Profile")

            try:
                bottom_fwhm_peak = nth_max_widest_peak(bottom_prof, divisor)
                bottom_init = (bottom_fwhm_peak.minimum,
                               bottom_fwhm_peak.maximum,
                               (bottom_fwhm_peak.maximum - bottom_fwhm_peak.minimum) / 4,
                               np.max(bottom_prof) - np.min(bottom_prof),
                               np.min(bottom_prof))

                bottom_fit, _ = curve_fit(flat_top_gauss,
                                          bottom_indeces,
                                          bottom_prof,
                                          bottom_init)
                bottom_fitted = flat_top_gauss(bottom_indeces, *bottom_fit)
                plt.plot(bottom_x_locs, bottom_fitted,
                         label="Bottom Fit")
            except RuntimeError:
                pass

            plt.legend()
            plt.xlabel("Position (Pixels)")
            plt.ylabel("Value")
            plt.title("ROI Profiles")
            plt.show()
