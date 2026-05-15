"""
Calculates the contrast of the 1 mm resolution insert.
"""
import math
import numpy as np
from scipy.optimize import minimize_scalar

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import BaseInputROI, InputRectangleROI, InputLineROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import (FloatOutput,
                                                   StringOutput,
                                                   PercInput,
                                                   BoolInput,
                                                   OptionInput)
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
FFT_MULT = 10


def get_contrast(profile: np.ndarray[tuple[int], np.dtype]) -> float:
    """
    Get the contrast for a line profile from the 1mm ACR resolution insert
    """
    bounds = nth_max_bounds(profile, 2)
    if profile[math.floor(bounds.minimum)] > profile[math.floor(bounds.minimum)]:
        start = math.floor(bounds.minimum)
    else:
        start = math.floor(bounds.minimum)

    if profile[math.floor(bounds.maximum)] > profile[math.floor(bounds.maximum)]:
        end = math.floor(bounds.maximum)
    else:
        end = math.floor(bounds.maximum)

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


def fft_contrast(profile: np.ndarray[tuple[int], np.dtype],
                 pixel_width: float,
                 contrast_frequency: float) -> float:
    """
    Get the contrast for a line profile using an fft
    """
    fft_signal = np.fft.rfft(profile, FFT_MULT * profile.shape[0])
    abs_fft = np.abs(fft_signal)
    locs = np.fft.rfftfreq(FFT_MULT * profile.shape[0], d=pixel_width)
    return np.interp(contrast_frequency, locs, abs_fft) / abs_fft[0]


def square_wave_integral(x: np.ndarray | float, width: float = 1, offset: float = 0):
    """
    The integral of a square wave from 0 to x.
    The square wave is defined by

    1 (0 < x mod 2*width < width)
    0 (width < x mod 2*width < 2*width)


    Parameters
    ----------
    x : np.ndarray | float
    width : float, optional
        Width of a peak of the square wave.
        The wavelength is 2*width.
    offset : float, optional
        The offset of the square wave.
        If a mutiple of 2*width then it is equivelant to 0.

    Returns
    -------
    The integral of the square wave up to x.
    """
    x = ((x - offset) / (2 * width)) - 0.5
    zero_pt = ((0 - offset) / (2 * width)) - 0.5
    integral = (width
                * ((np.abs(0.5 + (x % 1))
                    + np.abs(0.5 - (x % 1))
                    + np.floor(x))
                    + (np.abs(0.5 + (zero_pt % 1))
                       + np.abs(0.5 - (zero_pt % 1))
                       + np.floor(zero_pt))))
    return integral


def model_signal(offset: float,
                 pixel_width: float,
                 wave_peak_width: float,
                 num_peaks: int,
                 num_samples: int) -> np.ndarray:
    points = np.arange(0, num_samples + 1, 1) * pixel_width
    raw_signal = square_wave_integral(points, wave_peak_width, offset)
    raw_signal[points < offset] = square_wave_integral(offset, wave_peak_width, offset)
    max_point = offset + 2 * wave_peak_width * num_peaks
    raw_signal[points > max_point] = square_wave_integral(max_point, wave_peak_width, offset)
    signal = np.diff(raw_signal)
    return signal


def model_neg_signal_contrast(offset: float,
                              pixel_width: float,
                              wave_peak_width: float,
                              num_peaks: int,
                              num_samples: int,) -> float:
    signal = model_signal(offset,
                          pixel_width,
                          wave_peak_width,
                          num_peaks,
                          num_samples)
    return -get_contrast(signal)


def maximum_contrast_ratio(pixel_width: float,
                           wave_peak_width: float,
                           num_peaks: int,
                           num_samples: int) -> float:
    optimum = minimize_scalar(model_neg_signal_contrast,
                              args=(pixel_width,
                                    wave_peak_width,
                                    num_peaks,
                                    num_samples),
                              bounds=(0, pixel_width))
    return -optimum.fun  # pyright: ignore[reportAttributeAccessIssue]


def model_neg_signal_fft_contrast(offset: float,
                                  pixel_width: float,
                                  wave_peak_width: float,
                                  num_peaks: int,
                                  num_samples: int,
                                  contrast_frequency: float) -> float:
    signal = model_signal(offset,
                          pixel_width,
                          wave_peak_width,
                          num_peaks,
                          num_samples)
    return -fft_contrast(signal,
                         pixel_width,
                         contrast_frequency)


def maximum_frequency_ratio(pixel_width: float,
                            wave_peak_width: float,
                            num_peaks: int,
                            num_samples: int,
                            contrast_frequency: float) -> float:
    optimum = minimize_scalar(model_neg_signal_fft_contrast,
                              args=(pixel_width,
                                    wave_peak_width,
                                    num_peaks,
                                    num_samples,
                                    contrast_frequency),
                              bounds=(0, pixel_width))
    return -optimum.fun  # pyright: ignore[reportAttributeAccessIssue]


class MedACRResolution(PhantomModule):
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
    resolution_type = OptionInput[str](options_map={"FFT Method": "FFT",
                                                    "Contrast Method": "contrast"},
                                       initial="FFT Method")

    pixel_size_vertical = FloatOutput()
    pixel_size_horizontal = FloatOutput()
    phase_dir = StringOutput(verbose_name="Phase Encode Direction")

    phase_contrast = FloatOutput(verbose_name="Phase Encode Contrast (%)",
                                 reset_on_analysis=True)
    freq_contrast = FloatOutput(verbose_name="Frequency Encode Contrast (%)",
                                reset_on_analysis=True)
    total_contrast = FloatOutput(verbose_name="Average Contrast (%)",
                                 reset_on_analysis=True)
    best_contrast = FloatOutput(verbose_name="Theoretical Best Contrast (%)",
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

        horizontal_line_length = math.floor(2
                                            * NUM_PINS
                                            * POINT_SEP
                                            / self.pixel_size_horizontal.value)
        vertical_line_length = math.floor(2
                                          * NUM_PINS
                                          * POINT_SEP
                                          / self.pixel_size_vertical.value)
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
        contrast_frequency = 1 / (2 * POINT_SEP)
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
            horizontal_line_length = math.floor(2
                                                * NUM_PINS
                                                * POINT_SEP
                                                / self.pixel_size_horizontal.value)
            vertical_line_length = math.floor(2
                                              * NUM_PINS
                                              * POINT_SEP
                                              / self.pixel_size_vertical.value)
            xmax = roi.width - horizontal_line_length
            ymax = roi.height - vertical_line_length
            line_min_vals = np.max(roi.pixel_array) * self.resolution_percentage.value / 100

            if self.resolution_type.value == "FFT":
                self.best_contrast.value = 100 * maximum_frequency_ratio(self.pixel_size_horizontal.value,
                                                                         POINT_SEP,
                                                                         NUM_PINS,
                                                                         horizontal_line_length,
                                                                         contrast_frequency)
            else:
                self.best_contrast.value = 100 * maximum_contrast_ratio(self.pixel_size_horizontal.value,
                                                                        POINT_SEP,
                                                                        NUM_PINS,
                                                                        horizontal_line_length)

            for x in range(roi.width):
                for y in range(roi.height):
                    if x <= xmax:
                        profile = roi.pixel_array[y, x:x + horizontal_line_length]
                        if np.count_nonzero(profile >= line_min_vals) >= NUM_PINS:
                            if self.resolution_type.value == "FFT":
                                contrast = fft_contrast(profile,
                                                        self.pixel_size_horizontal.value,
                                                        contrast_frequency)
                            else:
                                contrast = get_contrast(profile)
                            if contrast > horizontal_max_contrast:
                                horizontal_max_contrast = contrast
                                horizontal_max_position = x, y
                    if y <= ymax:
                        profile = roi.pixel_array[y:y + vertical_line_length, x]
                        if np.count_nonzero(profile >= line_min_vals) >= NUM_PINS:
                            if self.resolution_type.value == "FFT":
                                contrast = fft_contrast(profile,
                                                        self.pixel_size_vertical.value,
                                                        contrast_frequency)
                            else:
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

        else:
            if (self.horizontal_line.roi is None
                    or self.vertical_line.roi is None):
                return
            elif self.resolution_type.value == "FFT":
                horizontal_max_contrast = fft_contrast(self.horizontal_line.roi.profile,  # pyright: ignore[reportArgumentType]
                                                       self.pixel_size_horizontal.value,
                                                       contrast_frequency)
                vertical_max_contrast = fft_contrast(self.vertical_line.roi.profile,  # pyright: ignore[reportArgumentType]
                                                     self.pixel_size_vertical.value,
                                                     contrast_frequency)
            else:
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
