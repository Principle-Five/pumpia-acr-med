"""
Calculates the contrast of the 1 mm resolution insert.
"""
import math
import numpy as np
from scipy.optimize import minimize_scalar

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.fields.roi_fields import LineROIField, RectangleROIField
from pumpia.module_handling.fields.viewer_fields import MonochromeDicomViewerField
from pumpia.module_handling.fields.simple import PercField, FloatField, BoolField, StringField
from pumpia.image_handling.roi_structures import RectangleROI, LineROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.file_handling.dicom_tags import MRTags

from pumpia_acr_med.med_acr_context import MedACRContextManager, MedACRContext

BOX_Y_OFFSET = 28
BOX_X_OFFSET = -5
BOX_SIDE_LENGTH = 19
LINE_LENGTH = 10
LINE_GAP = 2
POINT_SEP = 1
NUM_PINS = 4
FFT_MULT = 10


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


class MedACRFFTResolution(PhantomModule):
    """
    Calculates the contrast of the 1mm resolution insert.
    """
    context_manager = MedACRContextManager()
    show_draw_rois_button = True
    show_analyse_button = True
    title = "Resolution"

    viewer = MonochromeDicomViewerField(row=0, column=0)

    auto_position_lines = BoolField()
    resolution_percentage = PercField(50)

    pixel_size_vertical = FloatField(read_only=True)
    pixel_size_horizontal = FloatField(read_only=True)
    phase_dir = StringField(verbose_name="Phase Encode Direction",
                            read_only=True)

    phase_contrast = FloatField(verbose_name="Phase Encode Contrast (%)",
                                reset_on_analysis=True,
                                read_only=True)
    freq_contrast = FloatField(verbose_name="Frequency Encode Contrast (%)",
                               reset_on_analysis=True,
                               read_only=True)
    total_contrast = FloatField(verbose_name="Average Contrast (%)",
                                reset_on_analysis=True,
                                read_only=True)
    best_contrast = FloatField(verbose_name="Theoretical Best Contrast (%)",
                               reset_on_analysis=True,
                               read_only=True)

    main_roi = RectangleROIField()
    horizontal_line = LineROIField()
    vertical_line = LineROIField()

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

        pixel_size = image.pixel_spacing
        if pixel_size is None:
            return
        pixel_height = pixel_size[0]
        pixel_width = pixel_size[1]

        self.pixel_size_horizontal = pixel_width
        self.pixel_size_vertical = pixel_height

        phase_dir = image.get_value(MRTags.InPlanePhaseEncodingDirection, True)
        if phase_dir is not None:
            self.phase_dir = phase_dir
        else:
            self.phase_dir = ""

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
                                            / self.pixel_size_horizontal)
        vertical_line_length = math.floor(2
                                          * NUM_PINS
                                          * POINT_SEP
                                          / self.pixel_size_vertical)
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

    def post_roi_register(self, roi_input: LineROIField | RectangleROIField):
        if (roi_input.roi is not None
            and self.manager is not None
                and roi_input in self.rois):
            self.manager.add_roi(roi_input.roi)

    def analyse(self, batch: bool = False):
        horizontal_max_contrast: float = 0
        vertical_max_contrast: float = 0
        contrast_frequency = 1 / (2 * POINT_SEP)
        if self.auto_position_lines:
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
                                                / self.pixel_size_horizontal)
            vertical_line_length = math.floor(2
                                              * NUM_PINS
                                              * POINT_SEP
                                              / self.pixel_size_vertical)
            xmax = roi.width - horizontal_line_length
            ymax = roi.height - vertical_line_length
            line_min_vals = np.max(roi.pixel_array) * self.resolution_percentage / 100

            self.best_contrast = (100
                                  * maximum_frequency_ratio(self.pixel_size_horizontal,
                                                            POINT_SEP,
                                                            NUM_PINS,
                                                            horizontal_line_length,
                                                            contrast_frequency))

            for x in range(roi.width):
                for y in range(roi.height):
                    if x <= xmax:
                        profile = roi.pixel_array[y, x:x + horizontal_line_length]
                        if np.count_nonzero(profile >= line_min_vals) >= NUM_PINS:
                            contrast = fft_contrast(profile,
                                                    self.pixel_size_horizontal,
                                                    contrast_frequency)
                            if contrast > horizontal_max_contrast:
                                horizontal_max_contrast = contrast
                                horizontal_max_position = x, y
                    if y <= ymax:
                        profile = roi.pixel_array[y:y + vertical_line_length, x]
                        if np.count_nonzero(profile >= line_min_vals) >= NUM_PINS:
                            contrast = fft_contrast(profile,
                                                    self.pixel_size_vertical,
                                                    contrast_frequency)
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
            horizontal_max_contrast = fft_contrast(self.horizontal_line.roi.profile,  # pyright: ignore[reportArgumentType]
                                                   self.pixel_size_horizontal,
                                                   contrast_frequency)
            vertical_max_contrast = fft_contrast(self.vertical_line.roi.profile,  # pyright: ignore[reportArgumentType]
                                                 self.pixel_size_vertical,
                                                 contrast_frequency)

        h_contrast = 100 * horizontal_max_contrast
        v_contrast = 100 * vertical_max_contrast

        if self.phase_dir == "ROW":
            self.phase_contrast = h_contrast
            self.freq_contrast = v_contrast
        else:
            self.phase_contrast = v_contrast
            self.freq_contrast = h_contrast
        self.total_contrast = (h_contrast + v_contrast) / 2
