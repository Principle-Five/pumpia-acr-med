"""
Calculates the contrast of the 1 mm resolution insert.
"""
import math
import numpy as np

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import BaseInputROI, InputRectangleROI, InputLineROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import FloatOutput, IntInput, BoolInput
from pumpia.image_handling.roi_structures import RectangleROI, LineROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.utilities.array_utils import nth_max_bounds

from pumpia_acr_med.med_acr_context import MedACRContextManagerGenerator, MedACRContext

BOX_Y_OFFSET = 28
BOX_X_OFFSET = -5
BOX_SIDE_LENGTH = 19
LINE_LENGTH = 8
LINE_GAP = 2

# step 1: draw big box
# step 2: find centre pixel from big box profiles
# step 3: draw horizontal and vertical lines across rows/columns defined by ACR
# step 4: get contrast (max-min)/(max+min) for each line
# step 5: result is maximum contrast for rows/columns


class MedACRResolution(PhantomModule):
    """
    Calculates the contrast of the 1mm resolution insert.
    """
    context_manager_generator = MedACRContextManagerGenerator()
    show_draw_rois_button = True
    show_analyse_button = True

    viewer = MonochromeDicomViewerIO(row=0, column=0)

    override_centre = BoolInput(initial_value=False)
    x_centre_override = IntInput(initial_value=9)
    y_centre_override = IntInput(initial_value=9)

    vertical_contrast = FloatOutput(verbose_name="Vertical contrast (%)")
    horizontal_contrast = FloatOutput(verbose_name="Horizontal contrast (%)")
    total_contrast = FloatOutput(verbose_name="contrast (%)")

    main_roi = InputRectangleROI()
    horizontal_line_1 = InputLineROI()
    horizontal_line_2 = InputLineROI()
    horizontal_line_3 = InputLineROI()
    horizontal_line_4 = InputLineROI()
    vertical_line_1 = InputLineROI()
    vertical_line_2 = InputLineROI()
    vertical_line_3 = InputLineROI()
    vertical_line_4 = InputLineROI()

    def draw_rois(self, context: MedACRContext, batch: bool = False) -> None:

        if isinstance(self.viewer.image, Instance):
            image = self.viewer.image.series
        elif isinstance(self.viewer.image, Series):
            image = self.viewer.image
        else:
            return

        if context.inserts_slice == 10:
            image = image.instances[10]
        else:
            image = image.instances[0]

        self.viewer.load_image(image)

        pixel_size = image.pixel_size
        pixel_height = pixel_size[1]
        pixel_width = pixel_size[2]

        box_height = BOX_SIDE_LENGTH / pixel_height
        box_width = BOX_SIDE_LENGTH / pixel_width

        x_offset = 0
        y_offset = 0
        horizontal_dir = ["U", "L"]
        vertical_dir = ["D", "R"]

        if context.res_insert_side == "right":
            x_offset = BOX_Y_OFFSET / pixel_width
            horizontal_dir[1] = "R"
            vertical_dir[1] = "L"
        elif context.res_insert_side == "left":
            x_offset = -BOX_Y_OFFSET / pixel_width - box_width
            horizontal_dir[1] = "L"
            vertical_dir[1] = "R"
        elif context.res_insert_side == "top":
            y_offset = -BOX_Y_OFFSET / pixel_height - box_height
            horizontal_dir[0] = "D"
            vertical_dir[0] = "U"
        else:
            y_offset = BOX_Y_OFFSET / pixel_height
            horizontal_dir[0] = "U"
            vertical_dir[0] = "D"

        if context.circle_insert_side == "top":
            y_offset = BOX_X_OFFSET / pixel_height
            horizontal_dir[0] = "D"
            vertical_dir[0] = "U"
        elif context.circle_insert_side == "bottom":
            y_offset = -BOX_X_OFFSET / pixel_height - box_width
            horizontal_dir[0] = "U"
            vertical_dir[0] = "D"
        elif context.circle_insert_side == "right":
            x_offset = -BOX_X_OFFSET / pixel_width - box_width
            horizontal_dir[1] = "R"
            vertical_dir[1] = "L"
        else:
            x_offset = BOX_X_OFFSET / pixel_width
            horizontal_dir[1] = "L"
            vertical_dir[1] = "R"

        box_xmin = round(context.xcent + x_offset)
        box_ymin = round(context.ycent + y_offset)
        box_height = round(box_height)
        box_width = round(box_width)

        self.main_roi.register_roi(RectangleROI(image,
                                                box_xmin,
                                                box_ymin,
                                                box_width,
                                                box_height))

        if horizontal_dir[0] == "U":
            h_line_gap = round(-LINE_GAP * pixel_height)
        else:
            h_line_gap = round(LINE_GAP * pixel_height)
        h_line_length = LINE_LENGTH * pixel_width

        if vertical_dir[1] == "L":
            v_line_gap = round(-LINE_GAP * pixel_width)
        else:
            v_line_gap = round(LINE_GAP * pixel_width)
        v_line_length = LINE_LENGTH * pixel_height

        if self.main_roi.roi is not None:
            if self.override_centre.value:
                x_cent_loc = self.x_centre_override.value + self.main_roi.roi.xmin
                y_cent_loc = self.y_centre_override.value + self.main_roi.roi.ymin
            else:
                x_cent_loc = int(np.argmax(self.main_roi.roi.h_profile)) + self.main_roi.roi.xmin
                y_cent_loc = int(np.argmax(self.main_roi.roi.v_profile)) + self.main_roi.roi.ymin

            # -1 required to keep line length as line ROI ends are included
            if vertical_dir[0] == "U":
                v_ymin = y_cent_loc - round(v_line_length - 1)
                v_ymax = y_cent_loc
            else:
                v_ymin = y_cent_loc
                v_ymax = y_cent_loc + round(v_line_length - 1)

            if horizontal_dir[1] == "L":
                h_xmin = x_cent_loc - round(h_line_length - 1)
                h_xmax = x_cent_loc
            else:
                h_xmin = x_cent_loc
                h_xmax = x_cent_loc + round(h_line_length - 1)

            self.horizontal_line_1.register_roi(LineROI(image,
                                                        h_xmin,
                                                        y_cent_loc,
                                                        h_xmax,
                                                        y_cent_loc))
            self.horizontal_line_2.register_roi(LineROI(image,
                                                        h_xmin,
                                                        y_cent_loc + h_line_gap,
                                                        h_xmax,
                                                        y_cent_loc + h_line_gap))
            self.horizontal_line_3.register_roi(LineROI(image,
                                                        h_xmin,
                                                        y_cent_loc + 2 * h_line_gap,
                                                        h_xmax,
                                                        y_cent_loc + 2 * h_line_gap))
            self.horizontal_line_4.register_roi(LineROI(image,
                                                        h_xmin,
                                                        y_cent_loc + 3 * h_line_gap,
                                                        h_xmax,
                                                        y_cent_loc + 3 * h_line_gap))
            self.vertical_line_1.register_roi(LineROI(image,
                                                      x_cent_loc,
                                                      v_ymin,
                                                      x_cent_loc,
                                                      v_ymax))
            self.vertical_line_2.register_roi(LineROI(image,
                                                      x_cent_loc + v_line_gap,
                                                      v_ymin,
                                                      x_cent_loc + v_line_gap,
                                                      v_ymax))
            self.vertical_line_3.register_roi(LineROI(image,
                                                      x_cent_loc + 2 * v_line_gap,
                                                      v_ymin,
                                                      x_cent_loc + 2 * v_line_gap,
                                                      v_ymax))
            self.vertical_line_4.register_roi(LineROI(image,
                                                      x_cent_loc + 3 * v_line_gap,
                                                      v_ymin,
                                                      x_cent_loc + 3 * v_line_gap,
                                                      v_ymax))

    def post_roi_register(self, roi_input: BaseInputROI):
        if (roi_input.roi is not None
            and self.manager is not None
                and roi_input in self.rois):
            self.manager.add_roi(roi_input.roi)

    def link_rois_viewers(self):
        self.main_roi.viewer = self.viewer
        self.horizontal_line_1.viewer = self.viewer
        self.horizontal_line_2.viewer = self.viewer
        self.horizontal_line_3.viewer = self.viewer
        self.horizontal_line_4.viewer = self.viewer
        self.vertical_line_1.viewer = self.viewer
        self.vertical_line_2.viewer = self.viewer
        self.vertical_line_3.viewer = self.viewer
        self.vertical_line_4.viewer = self.viewer

    def analyse(self, batch: bool = False):
        horizontal_contrasts: list[float] = []
        vertical_contrasts: list[float] = []

        if self.horizontal_line_1.roi is not None:
            hl_1_bounds = nth_max_bounds(self.horizontal_line_1.roi.profile, 2)
            min_b = math.floor(hl_1_bounds.minimum)
            max_b = math.ceil(hl_1_bounds.maximum) + 1
            hl_1_max = np.max(self.horizontal_line_1.roi.profile[min_b:max_b])
            hl_1_min = np.min(self.horizontal_line_1.roi.profile[min_b:max_b])
            hl_1_con = (hl_1_max - hl_1_min) / (hl_1_max + hl_1_min)
            horizontal_contrasts.append(hl_1_con)
        if self.horizontal_line_2.roi is not None:
            hl_2_bounds = nth_max_bounds(self.horizontal_line_2.roi.profile, 2)
            min_b = math.floor(hl_2_bounds.minimum)
            max_b = math.ceil(hl_2_bounds.maximum) + 1
            hl_2_max = np.max(self.horizontal_line_2.roi.profile[min_b:max_b])
            hl_2_min = np.min(self.horizontal_line_2.roi.profile[min_b:max_b])
            hl_2_con = (hl_2_max - hl_2_min) / (hl_2_max + hl_2_min)
            horizontal_contrasts.append(hl_2_con)
        if self.horizontal_line_3.roi is not None:
            hl_3_bounds = nth_max_bounds(self.horizontal_line_3.roi.profile, 2)
            min_b = math.floor(hl_3_bounds.minimum)
            max_b = math.ceil(hl_3_bounds.maximum) + 1
            hl_3_max = np.max(self.horizontal_line_3.roi.profile[min_b:max_b])
            hl_3_min = np.min(self.horizontal_line_3.roi.profile[min_b:max_b])
            hl_3_con = (hl_3_max - hl_3_min) / (hl_3_max + hl_3_min)
            horizontal_contrasts.append(hl_3_con)
        if self.horizontal_line_4.roi is not None:
            hl_4_bounds = nth_max_bounds(self.horizontal_line_4.roi.profile, 2)
            min_b = math.floor(hl_4_bounds.minimum)
            max_b = math.ceil(hl_4_bounds.maximum) + 1
            hl_4_max = np.max(self.horizontal_line_4.roi.profile[min_b:max_b])
            hl_4_min = np.min(self.horizontal_line_4.roi.profile[min_b:max_b])
            hl_4_con = (hl_4_max - hl_4_min) / (hl_4_max + hl_4_min)
            horizontal_contrasts.append(hl_4_con)

        if self.vertical_line_1.roi is not None:
            vl_1_bounds = nth_max_bounds(self.vertical_line_1.roi.profile, 2)
            min_b = math.floor(vl_1_bounds.minimum)
            max_b = math.ceil(vl_1_bounds.maximum) + 1
            vl_1_max = np.max(self.vertical_line_1.roi.profile[min_b:max_b])
            vl_1_min = np.min(self.vertical_line_1.roi.profile[min_b:max_b])
            vl_1_con = (vl_1_max - vl_1_min) / (vl_1_max + vl_1_min)
            vertical_contrasts.append(vl_1_con)
        if self.vertical_line_2.roi is not None:
            vl_2_bounds = nth_max_bounds(self.vertical_line_2.roi.profile, 2)
            min_b = math.floor(vl_2_bounds.minimum)
            max_b = math.ceil(vl_2_bounds.maximum) + 1
            vl_2_max = np.max(self.vertical_line_2.roi.profile[min_b:max_b])
            vl_2_min = np.min(self.vertical_line_2.roi.profile[min_b:max_b])
            vl_2_con = (vl_2_max - vl_2_min) / (vl_2_max + vl_2_min)
            vertical_contrasts.append(vl_2_con)
        if self.vertical_line_3.roi is not None:
            vl_3_bounds = nth_max_bounds(self.vertical_line_3.roi.profile, 2)
            min_b = math.floor(vl_3_bounds.minimum)
            max_b = math.ceil(vl_3_bounds.maximum) + 1
            vl_3_max = np.max(self.vertical_line_3.roi.profile[min_b:max_b])
            vl_3_min = np.min(self.vertical_line_3.roi.profile[min_b:max_b])
            vl_3_con = (vl_3_max - vl_3_min) / (vl_3_max + vl_3_min)
            vertical_contrasts.append(vl_3_con)
        if self.vertical_line_4.roi is not None:
            vl_4_bounds = nth_max_bounds(self.vertical_line_4.roi.profile, 2)
            min_b = math.floor(vl_4_bounds.minimum)
            max_b = math.ceil(vl_4_bounds.maximum) + 1
            vl_4_max = np.max(self.vertical_line_4.roi.profile[min_b:max_b])
            vl_4_min = np.min(self.vertical_line_4.roi.profile[min_b:max_b])
            vl_4_con = (vl_4_max - vl_4_min) / (vl_4_max + vl_4_min)
            vertical_contrasts.append(vl_4_con)

        h_contrast = 100 * max(horizontal_contrasts)
        v_contrast = 100 * max(vertical_contrasts)

        self.horizontal_contrast.value = h_contrast
        self.vertical_contrast.value = v_contrast
        self.total_contrast.value = (h_contrast + v_contrast) / 2
