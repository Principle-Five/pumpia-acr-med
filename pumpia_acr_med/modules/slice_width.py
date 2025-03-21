"""
Slice width for Medium ACR Phantom
"""
import math
import numpy as np
from scipy.optimize import curve_fit

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import BaseInputROI, InputRectangleROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import FloatInput, PercInput,  FloatOutput, StringOutput
from pumpia.image_handling.roi_structures import RectangleROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.utilities.feature_utils import nth_max_widest_peak, flat_top_gauss

from ..acr_med_context import MedACRContextManagerGenerator, MedACRContext

# ROI sizes in mm
ROI_HEIGHT = 3.5
ROI_WIDTH = 100
BOTTOM_OFFSET = 0
TOP_OFFSET = -4.5

def flat_top_gauss_offset(pos: np.ndarray,
                            a: float,
                            b: float,
                            c: float,
                            amp: float,
                            offset:float):
    return flat_top_gauss(pos,a,b,c,amp)+offset

class MedACRSliceWidth(PhantomModule):
    """
    Calculates slice width for the medium ACR phantom by fitting to a flat top gaussian
    """
    context_manager_generator = MedACRContextManagerGenerator()

    viewer = MonochromeDicomViewerIO(row=0, column=0)

    tan_theta = FloatInput(0.1, verbose_name="Tan of wedge angle")
    max_perc = PercInput(50, verbose_name="Width position (% of max)")

    ramp_dir = StringOutput(verbose_name="Wedge Direction", reset_on_analysis = False)

    expected_width = FloatOutput()
    top_ramp_width = FloatOutput()
    bottom_ramp_width = FloatOutput()
    slice_width = FloatOutput()

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
            box_height = ROI_HEIGHT/ pixel_width
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

            top_fwhm_peak = nth_max_widest_peak(top_prof, divisor)
            bottom_fwhm_peak = nth_max_widest_peak(bottom_prof, divisor)

            top_init = (top_fwhm_peak.minimum,
                        top_fwhm_peak.maximum,
                        (top_fwhm_peak.maximum-top_fwhm_peak.minimum)/4,
                        np.max(top_prof) - np.min(top_prof),
                        np.min(top_prof))
            top_indeces = np.indices(top_prof.shape)[0]
            top_fit, _ = curve_fit(flat_top_gauss_offset,
                                   top_indeces,
                                   top_prof,
                                   top_init)



            bottom_init = (bottom_fwhm_peak.minimum,
                        bottom_fwhm_peak.maximum,
                        (bottom_fwhm_peak.maximum-bottom_fwhm_peak.minimum)/4,
                        np.max(bottom_prof) - np.min(bottom_prof),
                        np.min(bottom_prof))
            bottom_indeces = np.indices(bottom_prof.shape)[0]
            bottom_fit, _ = curve_fit(flat_top_gauss_offset,
                                   bottom_indeces,
                                   bottom_prof,
                                   bottom_init)

            c_coeff = 2 * math.sqrt(2 * math.log(divisor))

            top_fwhm = abs(top_fit[1] - top_fit[0]) + c_coeff * top_fit[2]
            bottom_fwhm = abs(bottom_fit[1] - bottom_fit[0]) + c_coeff * bottom_fit[2]

            tan_theta = self.tan_theta.value

            top_width = top_fwhm * tan_theta * pix_size
            bottom_width = bottom_fwhm * tan_theta * pix_size

            self.top_ramp_width.value = top_width
            self.bottom_ramp_width.value = bottom_width

            self.slice_width.value = math.sqrt(top_width * bottom_width)
