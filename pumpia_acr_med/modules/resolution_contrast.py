"""
Calculates the contrast of the 1 mm resolution insert.
"""
import math
import numpy as np

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import BaseInputROI, InputRectangleROI, InputLineROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import FloatOutput, StringOutput, PercInput, BoolInput
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
NUM_PINS = 4


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


class MedACRContrastResolution(PhantomModule):
    """
    Calculates the contrast of the 1mm resolution insert.
    """
    context_manager_generator = MedACRContextManagerGenerator()
    show_draw_rois_button = True
    show_analyse_button = True
    name = "Resolution"

    viewer = MonochromeDicomViewerIO(row=0, column=0)

    auto_position_lines = BoolInput(True)
    resolution_percentage = PercInput(50)

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
    horizontal_line = InputLineROI()
    vertical_line = InputLineROI()

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

        horizontal_line_length = math.ceil(2 * NUM_PINS * POINT_SEP / self.pixel_size_horizontal.value)
        vertical_line_length = math.ceil(2 * NUM_PINS * POINT_SEP / self.pixel_size_vertical.value)
        self.horizontal_line.register_roi(LineROI(image,
                                                  box_xmin,
                                                  box_ymin,
                                                  box_xmin + horizontal_line_length,
                                                  box_ymin))
        self.vertical_line.register_roi(LineROI(image,
                                                box_xmin,
                                                box_ymin,
                                                box_xmin,
                                                box_ymin + vertical_line_length))

    def post_roi_register(self, roi_input: BaseInputROI):
        if (roi_input.roi is not None
            and self.manager is not None
                and roi_input in self.rois):
            self.manager.add_roi(roi_input.roi)

    def link_rois_viewers(self):
        self.main_roi.viewer = self.viewer
        self.horizontal_line.viewer = self.viewer
        self.vertical_line.viewer = self.viewer

    def analyse(self, batch: bool = False):
        horizontal_max_contrast: float = 0
        vertical_max_contrast: float = 0
        if self.auto_position_lines.value:
            if self.viewer.image is not None:
                image = self.viewer.image
            else:
                return

            if self.main_roi.roi is not None:
                roi = self.main_roi.roi
            else:
                return

            horizontal_max_position: tuple[int, int] = 0, 0
            vertical_max_position: tuple[int, int] = 0, 0
            horizontal_line_length = math.ceil(2 * NUM_PINS * POINT_SEP / self.pixel_size_horizontal.value)
            vertical_line_length = math.ceil(2 * NUM_PINS * POINT_SEP / self.pixel_size_vertical.value)
            xmax = roi.width - horizontal_line_length
            ymax = roi.height - vertical_line_length
            line_min_vals = np.max(roi.pixel_array) * self.resolution_percentage.value / 100

            for x in range(roi.width):
                for y in range(roi.height):
                    if x <= xmax:
                        profile = roi.pixel_array[y, x:x + horizontal_line_length]
                        if np.count_nonzero(profile >= line_min_vals) >= NUM_PINS:
                            contrast = get_contrast(profile)
                            if contrast > horizontal_max_contrast:
                                horizontal_max_contrast = contrast
                                horizontal_max_position = x, y
                    if y <= ymax:
                        profile = roi.pixel_array[y:y + vertical_line_length, x]
                        if np.count_nonzero(profile >= line_min_vals) >= NUM_PINS:
                            contrast = get_contrast(profile)
                            if contrast > vertical_max_contrast:
                                vertical_max_contrast = contrast
                                vertical_max_position = x, y

            # -1 required to keep line length as line ROI ends are included
            self.horizontal_line.register_roi(LineROI(image,
                                                      horizontal_max_position[0] + roi.xmin,
                                                      horizontal_max_position[1] + roi.ymin,
                                                      horizontal_max_position[0] + horizontal_line_length + roi.xmin - 1,
                                                      horizontal_max_position[1] + roi.ymin))
            self.vertical_line.register_roi(LineROI(image,
                                                    vertical_max_position[0] + roi.xmin,
                                                    vertical_max_position[1] + roi.ymin,
                                                    vertical_max_position[0] + roi.xmin,
                                                    vertical_max_position[1] + vertical_line_length + roi.ymin - 1))
            self.update_viewers()

        else:
            if (self.horizontal_line.roi is None
                    or self.vertical_line.roi is None):
                return
            horizontal_max_contrast = get_contrast(self.horizontal_line.roi.profile)  # pyright: ignore[reportArgumentType]
            vertical_max_contrast = get_contrast(self.vertical_line.roi.profile)  # pyright: ignore[reportArgumentType]

        h_contrast = 100 * horizontal_max_contrast
        v_contrast = 100 * vertical_max_contrast

        if self.phase_dir.value == "ROW":
            self.phase_contrast.value = h_contrast
            self.freq_contrast.value = v_contrast
        else:
            self.phase_contrast.value = v_contrast
            self.freq_contrast.value = h_contrast
        self.total_contrast.value = (h_contrast + v_contrast) / 2
