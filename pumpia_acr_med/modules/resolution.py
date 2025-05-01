"""
Calculates the contrast of the 1 mm resolution insert.
"""
import math
import numpy as np

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import BaseInputROI, InputRectangleROI, InputLineROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import FloatOutput, StringOutput, IntInput, BoolInput
from pumpia.image_handling.roi_structures import RectangleROI, LineROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.file_handling.dicom_tags import MRTags
from pumpia.utilities.array_utils import nth_max_bounds

from pumpia_acr_med.med_acr_context import MedACRContextManagerGenerator, MedACRContext

BOX_Y_OFFSET = 28
BOX_X_OFFSET = -5
BOX_SIDE_LENGTH = 19
LINE_LENGTH = 10
LINE_GAP = 2
POINT_SEP = 1


def get_contrast(profile: np.ndarray[tuple[int], np.dtype]) -> float:
    """
    Get the contrast for a line profile from the 1mm ACR resolution insert
    """
    bounds = nth_max_bounds(profile, 2)
    if profile[math.floor(bounds.minimum)] > profile[math.ceil(bounds.minimum)]:
        start = math.floor(bounds.minimum)
    else:
        start = math.ceil(bounds.minimum)

    if profile[math.floor(bounds.maximum)] > profile[math.ceil(bounds.maximum)]:
        end = math.floor(bounds.maximum)
    else:
        end = math.ceil(bounds.maximum)

    new_prof = profile[start:end + 1]
    minimum = np.min(new_prof)
    maximum = np.max(new_prof)
    half_maximum = (maximum + minimum) / 2
    mins = list(np.argwhere(new_prof < half_maximum)[:, 0])

    if end - start in mins:
        mins.remove(end - start)
    if 0 in mins:
        mins.remove(0)

    if len(mins) == 0:
        return 0

    troughs: list[list[int]] = [[mins[0]]]
    prev_min = mins[0]

    for m in mins[1:]:
        if m == prev_min + 1:
            troughs[-1].append(m)
        else:
            troughs.append([m])
        prev_min = m

    contrasts = []
    prev_t = 0
    for trough_num, trough in enumerate(troughs):
        if trough_num + 1 < len(troughs):
            next_t = min(troughs[trough_num + 1])
        else:
            next_t = len(new_prof)
        left_peak_val = np.mean(new_prof[prev_t:min(trough)])
        right_peak_val = np.mean(new_prof[max(trough) + 1:next_t])
        peak_val = (left_peak_val + right_peak_val) / 2
        trough_val = np.mean(new_prof[min(trough):max(trough) + 1])
        contrasts.append((peak_val - trough_val) / (peak_val + trough_val))

    return min(contrasts)


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

    pixel_size_vertical = FloatOutput()
    pixel_size_horizontal = FloatOutput()
    phase_dir = StringOutput(verbose_name="Phase Encode Direction")

    phase_contrast = FloatOutput(verbose_name="Phase Encode Contrast (%)",
                                 reset_on_analysis=True)
    freq_contrast = FloatOutput(verbose_name="Frequency Encode Contrast (%)",
                                reset_on_analysis=True)
    total_contrast = FloatOutput(verbose_name="1mm Contrast (%)",
                                 reset_on_analysis=True)

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

        self.pixel_size_horizontal.value = pixel_width
        self.pixel_size_vertical.value = pixel_height

        phase_dir = image.get_tag(MRTags.InPlanePhaseEncodingDirection)
        if phase_dir is not None:
            self.phase_dir.value = phase_dir
        else:
            self.phase_dir.value = ""

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
            horizontal_contrasts.append(
                get_contrast(self.horizontal_line_1.roi.profile))  # type: ignore
        if self.horizontal_line_2.roi is not None:
            horizontal_contrasts.append(
                get_contrast(self.horizontal_line_2.roi.profile))  # type: ignore
        if self.horizontal_line_3.roi is not None:
            horizontal_contrasts.append(
                get_contrast(self.horizontal_line_3.roi.profile))  # type: ignore
        if self.horizontal_line_4.roi is not None:
            horizontal_contrasts.append(
                get_contrast(self.horizontal_line_4.roi.profile))  # type: ignore

        if self.vertical_line_1.roi is not None:
            vertical_contrasts.append(
                get_contrast(self.vertical_line_1.roi.profile))  # type: ignore
        if self.vertical_line_2.roi is not None:
            vertical_contrasts.append(
                get_contrast(self.vertical_line_2.roi.profile))  # type: ignore
        if self.vertical_line_3.roi is not None:
            vertical_contrasts.append(
                get_contrast(self.vertical_line_3.roi.profile))  # type: ignore
        if self.vertical_line_4.roi is not None:
            vertical_contrasts.append(
                get_contrast(self.vertical_line_4.roi.profile))  # type: ignore

        h_contrast = 100 * max(horizontal_contrasts)
        v_contrast = 100 * max(vertical_contrasts)

        if self.phase_dir.value == "ROW":
            self.phase_contrast.value = h_contrast
            self.freq_contrast.value = v_contrast
        else:
            self.phase_contrast.value = v_contrast
            self.freq_contrast.value = h_contrast
        self.total_contrast.value = (h_contrast + v_contrast) / 2
