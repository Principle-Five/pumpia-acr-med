"""
Phantom width of medium ACR phantom
"""
import math
import statistics

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import BaseInputROI, InputLineROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import BoolInput, PercInput, FloatOutput
from pumpia.image_handling.roi_structures import LineROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.utilities.array_utils import nth_max_bounds

from pumpia_acr_med.med_acr_context import MedACRContext, MedACRContextManagerGenerator

# distances in mm
HALF_LINE_LENGTH = 100
COS_SIN_PI_4 = math.cos(math.pi / 4)


class MedACRPhantomWidth(PhantomModule):
    """
    Calculates medium ACR phantom width
    """
    context_manager_generator = MedACRContextManagerGenerator()
    show_draw_rois_button = True
    show_analyse_button = True
    name = "Phantom Width"

    viewer = MonochromeDicomViewerIO(row=0, column=0)

    max_perc = PercInput(50, verbose_name="Width position (% of max)")

    bool_vertical = BoolInput(verbose_name="Include vertical in Average")
    bool_up_slope = BoolInput(verbose_name="Include up slope in Average")
    bool_horizontal = BoolInput(verbose_name="Include horizontal in Average")
    bool_down_slope = BoolInput(verbose_name="Include down slope in Average")

    width_vertical = FloatOutput(verbose_name="vertical Width", reset_on_analysis=True)
    width_up_slope = FloatOutput(verbose_name="up slope Width", reset_on_analysis=True)
    width_horizontal = FloatOutput(verbose_name="horizontal Width", reset_on_analysis=True)
    width_down_slope = FloatOutput(verbose_name="down slope Width", reset_on_analysis=True)

    average_width = FloatOutput(verbose_name="Average Phantom Width", reset_on_analysis=True)
    linearity = FloatOutput(verbose_name="Geometric Linearity", reset_on_analysis=True)
    distortion = FloatOutput(verbose_name="Geometric Distortion (%)", reset_on_analysis=True)

    line_vertical = InputLineROI(name="vertical Line")
    line_up_slope = InputLineROI(name="up slope Line")
    line_horizontal = InputLineROI(name="horizontal Line")
    line_down_slope = InputLineROI(name="down slope Line")

    def draw_rois(self, context: MedACRContext, batch: bool = False) -> None:
        if isinstance(self.viewer.image, Instance):
            image = self.viewer.image
        elif isinstance(self.viewer.image, Series):
            if context.inserts_slice == 10:
                image = self.viewer.image.instances[6]
            else:
                image = self.viewer.image.instances[4]
        else:
            return
        self.viewer.load_image(image)

        pixel_size = image.pixel_size
        pixel_height = pixel_size[1]
        pixel_width = pixel_size[2]

        xcent = context.xcent
        ycent = context.ycent

        ydiff = HALF_LINE_LENGTH / pixel_height
        xdiff = 0
        x1 = round(xcent - xdiff)
        x2 = round(xcent + xdiff)
        y1 = round(ycent - ydiff)
        y2 = round(ycent + ydiff)
        roi = LineROI(image,
                      x1,
                      y1,
                      x2,
                      y2,
                      replace=True)
        self.line_vertical.register_roi(roi)

        ydiff = HALF_LINE_LENGTH / pixel_height * COS_SIN_PI_4
        xdiff = HALF_LINE_LENGTH / pixel_width * COS_SIN_PI_4
        x1 = round(xcent - xdiff)
        x2 = round(xcent + xdiff)
        y1 = round(ycent - ydiff)
        y2 = round(ycent + ydiff)
        roi = LineROI(image,
                      x1,
                      y1,
                      x2,
                      y2,
                      replace=True)
        self.line_down_slope.register_roi(roi)

        ydiff = 0
        xdiff = HALF_LINE_LENGTH / pixel_width
        x1 = round(xcent - xdiff)
        x2 = round(xcent + xdiff)
        y1 = round(ycent - ydiff)
        y2 = round(ycent + ydiff)
        roi = LineROI(image,
                      x1,
                      y1,
                      x2,
                      y2,
                      replace=True)
        self.line_horizontal.register_roi(roi)

        ydiff = HALF_LINE_LENGTH / pixel_height * COS_SIN_PI_4
        xdiff = -HALF_LINE_LENGTH / pixel_width * COS_SIN_PI_4
        x1 = round(xcent - xdiff)
        x2 = round(xcent + xdiff)
        y1 = round(ycent - ydiff)
        y2 = round(ycent + ydiff)
        roi = LineROI(image,
                      x1,
                      y1,
                      x2,
                      y2,
                      replace=True)
        self.line_up_slope.register_roi(roi)

    def post_roi_register(self, roi_input: BaseInputROI):
        if (roi_input.roi is not None
            and self.manager is not None
                and roi_input in self.rois):
            self.manager.add_roi(roi_input.roi)

    def link_rois_viewers(self):
        self.line_vertical.viewer = self.viewer
        self.line_up_slope.viewer = self.viewer
        self.line_horizontal.viewer = self.viewer
        self.line_down_slope.viewer = self.viewer

    def analyse(self, batch: bool = False):
        if (self.viewer.image is not None
            and self.line_vertical.roi is not None
            and self.line_up_slope.roi is not None
            and self.line_horizontal.roi is not None
                and self.line_down_slope.roi is not None):

            image = self.viewer.image

            if isinstance(image, Series):
                slice_index = image.num_slices // 2
                image = image.instances[slice_index]

            pixel_size = image.pixel_size
            pixel_height = pixel_size[1]
            pixel_width = pixel_size[2]

            prof_vertical = self.line_vertical.roi.profile
            prof_up_slope = self.line_up_slope.roi.profile
            prof_horizontal = self.line_horizontal.roi.profile
            prof_down_slope = self.line_down_slope.roi.profile

            divisor = 100 / self.max_perc.value

            lengths = []

            unit_length_vertical = pixel_height
            width_vertical = nth_max_bounds(prof_vertical, divisor).difference * unit_length_vertical
            self.width_vertical.value = width_vertical
            if self.bool_vertical.value:
                lengths.append(width_vertical)

            unit_length_up_slope = math.dist([pixel_height * COS_SIN_PI_4, pixel_width * COS_SIN_PI_4], [0, 0])
            width_up_slope = nth_max_bounds(prof_up_slope, divisor).difference * unit_length_up_slope
            self.width_up_slope.value = width_up_slope
            if self.bool_up_slope.value:
                lengths.append(width_up_slope)

            unit_length_horizontal = pixel_width
            width_horizontal = nth_max_bounds(prof_horizontal, divisor).difference * unit_length_horizontal
            self.width_horizontal.value = width_horizontal
            if self.bool_horizontal.value:
                lengths.append(width_horizontal)

            unit_length_down_slope = math.dist([pixel_height * COS_SIN_PI_4, pixel_width * COS_SIN_PI_4], [0, 0])
            width_down_slope = nth_max_bounds(prof_down_slope, divisor).difference * unit_length_down_slope
            self.width_down_slope.value = width_down_slope
            if self.bool_down_slope.value:
                lengths.append(width_down_slope)

            mean = statistics.fmean(lengths)
            self.average_width.value = mean
            self.linearity.value = mean - 165
            self.distortion.value = 100 * statistics.stdev(lengths) / mean
