import sys
from pathlib import Path
import math

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes


from pumpia.module_handling.module_collections import BaseModule
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.roi_ios import InputLineROI
from pumpia.module_handling.in_outs.simple import IntInput, BoolInput, FloatInput

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from pumpia_acr_med.med_acr_context import MedACRContextManagerGenerator


def square_wave_integral(x: np.ndarray | float, amp: float = 1, width: float = 1, offset: float = 0):
    """
    The integral of a square wave from 0 to x.
    The square wave is defined by

    amp (0 < x < width)
    0 (width < x < 2*width)


    Parameters
    ----------
    x : np.ndarray | float
    amp : float, optional
        Amplitude of the square wave.
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
    integral = (amp
                * width
                * (np.abs(0.5 + (x % 1))
                   + np.abs(0.5 - (x % 1))
                   + np.floor(x))
                + (amp
                   * width
                   * (np.abs(0.5 + (zero_pt % 1))
                      + np.abs(0.5 - (zero_pt % 1))
                      + np.floor(zero_pt))))
    return integral


def model_signal(pixel_width: float,
                 offset: float,
                 amplitude: float,
                 wave_peak_width: float,
                 num_peaks: int,
                 sample_length: float) -> np.ndarray:
    num_samples = round(sample_length // pixel_width)

    points = np.arange(0, num_samples + 1, 1) * pixel_width
    raw_signal = square_wave_integral(points, amplitude, wave_peak_width, offset)
    raw_signal[points < offset] = square_wave_integral(offset, amplitude, wave_peak_width, offset)
    max_point = offset + 2 * wave_peak_width * num_peaks
    raw_signal[points > max_point] = square_wave_integral(max_point, amplitude, wave_peak_width, offset)
    signal = np.diff(raw_signal)

    return signal


class ContextTest(BaseModule):
    context_manager_generator = MedACRContextManagerGenerator()

    line = InputLineROI()
    num_peaks = IntInput(4)
    num_samples_per_peak = IntInput(1)
    roll = IntInput(0)
    padding = IntInput(0)
    show_absolute = BoolInput()
    show_real = BoolInput(False)
    show_imaginary = BoolInput(False)

    pixel_width = FloatInput(0.9765625)
    offset = FloatInput()
    amplitude = FloatInput(1)
    wave_peak_width = FloatInput(1)
    num_pins = IntInput(4, verbose_name="Number of Peaks")
    sample_length = FloatInput(8)

    num_widths = IntInput(100, verbose_name="Number of Widths")
    min_width = FloatInput(0.6, verbose_name="Minimum Width")
    max_width = FloatInput(1, verbose_name="Maximum Width")
    num_offsets = IntInput(100, verbose_name="Number of Offsets")
    min_offset = FloatInput(-1, verbose_name="Minimum Offset")
    max_offset = FloatInput(1, verbose_name="Maximum Offset")

    main = MonochromeDicomViewerIO(0, 0)

    def load_commands(self):
        self.register_command("Show Profile", self.show_fft)
        self.register_command("Show Pure FFT", self.pure_signal_fft)
        self.register_command("Model Image Signal", self.model_phantom)
        self.register_command("Heatmap", self.pixel_offset_heatmap)

    def show_fft(self):
        """
        Shows the ROI profiles
        """
        if self.line.roi is not None:
            if self.main.image is not None:
                x_size = self.main.image.pixel_size[2]
                y_size = self.main.image.pixel_size[1]
                line_len = math.sqrt((self.line.roi.x_len * x_size)**2 + (self.line.roi.y_len * y_size)**2)
                d = line_len / (self.line.roi.profile.shape[0] - 1)
                points = np.arange(0, self.line.roi.profile.shape[0], 1) * d

                line_fft = np.fft.rfft(self.line.roi.profile, self.line.roi.profile.shape[0] * 2)
                line_fft = line_fft / line_fft[0]
                abs_fft = np.abs(line_fft)
                real_fft = np.real(line_fft)
                imag_fft = np.imag(line_fft)
                locs = np.fft.rfftfreq(self.line.roi.profile.shape[0] * 2, d)

                fig = plt.gcf()
                fig.clear()
                axes: tuple[Axes, Axes] = fig.subplots(2, 1)
                sig_ax, fft_ax = axes

                sig_ax.plot(points, self.line.roi.profile)

                if self.show_absolute.value:
                    fft_ax.plot(locs, abs_fft, label="Absolute")
                if self.show_real.value:
                    fft_ax.plot(locs, real_fft, label="Real")
                if self.show_imaginary.value:
                    fft_ax.plot(locs, imag_fft, label="Imaginary")

                fft_ax.legend()
                fft_ax.set_xlabel("Frequency (mm-1)")
                fft_ax.set_ylabel("Value")
                fft_ax.set_title("ROI FFT")
                fig.tight_layout()
                fig.show()

    def pure_signal_fft(self):
        n = self.num_samples_per_peak.value
        n_peaks = self.num_peaks.value
        padding = self.padding.value
        roll = self.roll.value
        zeros = [0] * n
        ones = [1] * n
        signal = list(np.roll(((ones + zeros) * n_peaks), roll))
        # point_5s = [0.5] * n
        # signal = list(np.roll(((ones + zeros) * (n_peaks // 2) + (point_5s + zeros) + (ones + zeros) * (n_peaks // 2 - 1)), roll))
        combo = ([0] * padding) + signal + ([0] * padding)
        line = np.array(combo)
        line_fft = np.fft.rfft(line)
        line_fft = line_fft / line_fft[0]
        abs_fft = np.abs(line_fft)
        real_fft = np.real(line_fft)
        imag_fft = np.imag(line_fft)
        locs = np.fft.rfftfreq(line.shape[0]) * n

        fig = plt.gcf()
        fig.clear()
        axes: tuple[Axes, Axes] = fig.subplots(2, 1)
        sig_ax, fft_ax = axes

        sig_ax.plot(combo)

        if self.show_absolute.value:
            fft_ax.plot(locs, abs_fft, label="Absolute")
        if self.show_real.value:
            fft_ax.plot(locs, real_fft, label="Real")
        if self.show_imaginary.value:
            fft_ax.plot(locs, imag_fft, label="Imaginary")

        fft_ax.legend()
        fft_ax.set_xlabel("Frequency (mm-1)")
        fft_ax.set_ylabel("Value")
        fft_ax.set_title("ROI FFT")
        fig.tight_layout()
        fig.show()

    def model_phantom(self):
        pixel_width = self.pixel_width.value
        offset = self.offset.value
        amplitude = self.amplitude.value
        wave_peak_width = self.wave_peak_width.value
        num_peaks = self.num_pins.value
        sample_length = self.sample_length.value

        num_samples = round(sample_length // pixel_width)

        points = np.arange(0, num_samples + 1, 1) * pixel_width

        signal = model_signal(pixel_width,
                              offset,
                              amplitude,
                              wave_peak_width,
                              num_peaks,
                              sample_length)

        fft_signal = np.fft.rfft(signal, 10 * signal.shape[0])
        fft_signal = fft_signal / fft_signal[0]

        abs_fft = np.abs(fft_signal)
        real_fft = np.real(fft_signal)
        imag_fft = np.imag(fft_signal)
        locs = np.fft.rfftfreq(10 * signal.shape[0], d=pixel_width)

        fig = plt.gcf()
        fig.clear()
        axes: tuple[Axes, Axes] = fig.subplots(2, 1)
        sig_ax, fft_ax = axes

        sig_ax.plot(points[:-1], signal)

        if self.show_absolute.value:
            fft_ax.plot(locs, abs_fft, label="Absolute")
        if self.show_real.value:
            fft_ax.plot(locs, real_fft, label="Real")
        if self.show_imaginary.value:
            fft_ax.plot(locs, imag_fft, label="Imaginary")

        fft_ax.legend()
        fft_ax.set_xlabel("Frequency (mm-1)")
        fft_ax.set_ylabel("Value")
        fft_ax.set_title("ROI FFT")
        fig.tight_layout()
        fig.show()

    def pixel_offset_heatmap(self):
        num_widths = self.num_widths.value
        min_widths = self.min_width.value
        max_widths = self.max_width.value
        num_offsets = self.num_offsets.value
        min_offsets = self.min_offset.value
        max_offsets = self.max_offset.value

        pixel_width_indices: np.ndarray = np.arange(0, num_widths, 1)
        offset_indices: np.ndarray = np.arange(0, num_offsets, 1)

        results = np.zeros((num_widths, num_offsets))

        max_points = np.zeros(num_widths)
        pixel_widths = np.zeros(num_widths)

        for p_i in pixel_width_indices:
            pixel_width = min_widths + (p_i * (max_widths - min_widths) / num_widths)
            if pixel_width > 0:
                max_points[p_i] = ((8 // pixel_width) * 0.5
                                   - (3.5 / pixel_width)
                                   ) % 1 - 0.5
                pixel_widths[p_i] = pixel_width
                for o_i in offset_indices:
                    offset = min_offsets + (o_i * (max_offsets - min_offsets) / num_offsets)
                    signal = model_signal(pixel_width,
                                          offset,
                                          1,
                                          1,
                                          4,
                                          8)
                    fft_signal = np.fft.rfft(signal, 2 * signal.shape[0])
                    abs_fft = np.abs(fft_signal)
                    if abs_fft[0] != 0:
                        abs_fft = abs_fft / abs_fft[0]
                        locs = np.fft.rfftfreq(2 * signal.shape[0], d=pixel_width)
                        results[p_i, o_i] = np.interp(0.5, locs, abs_fft)

        results = results[::-1]
        fig = plt.gcf()
        fig.clear()
        heatmap_axes = fig.subplots(1, 1)

        heatmap = heatmap_axes.imshow(results, interpolation='none',
                                      extent=(min_offsets, max_offsets, min_widths, max_widths),
                                      aspect='auto')
        heatmap_axes.plot(max_points, pixel_widths)
        heatmap_axes.set_ylabel("Pixel Width (mm)")
        heatmap_axes.set_xlabel("Offset (mm)")
        heatmap_axes.set_title("0.5$mm^{-1}$ Frequency Ratio")
        fig.colorbar(heatmap, ax=heatmap_axes)
        fig.show()


if __name__ == "__main__":
    ContextTest.run()
