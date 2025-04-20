"""
Collection for Medium ACR with repeat images.
"""

from pumpia.module_handling.module_collections import (OutputFrame,
                                                       WindowGroup,
                                                       BaseCollection)
from pumpia.module_handling.in_outs.groups import IOGroup
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.widgets.viewers import BaseViewer

from pumpia_acr_med.med_acr_context import MedACRContextManagerGenerator
from pumpia_acr_med.modules.sub_snr import MedACRSubSNR
from pumpia_acr_med.modules.uniformity import MedACRUniformity
from pumpia_acr_med.modules.ghosting import MedACRGhosting
from pumpia_acr_med.modules.slice_width import MedACRSliceWidth
from pumpia_acr_med.modules.slice_pos import MedACRSlicePosition
from pumpia_acr_med.modules.phantom_width import MedACRPhantomWidth


class MedACRrptCollection(BaseCollection):
    """
    Collection for medium ACR phantom with repeated scans.
    """
    context_manager_generator = MedACRContextManagerGenerator()

    viewer1 = MonochromeDicomViewerIO(row=0, column=0)
    viewer2 = MonochromeDicomViewerIO(row=0, column=1)

    snr = MedACRSubSNR(verbose_name="SNR")

    uniformity1 = MedACRUniformity(verbose_name="Uniformity")
    uniformity2 = MedACRUniformity(verbose_name="Uniformity")

    ghosting1 = MedACRGhosting(verbose_name="Ghosting")
    ghosting2 = MedACRGhosting(verbose_name="Ghosting")

    slice_width1 = MedACRSliceWidth(verbose_name="Slice Width")
    slice_width2 = MedACRSliceWidth(verbose_name="Slice Width")

    slice_pos1 = MedACRSlicePosition(verbose_name="Slice Position")
    slice_pos2 = MedACRSlicePosition(verbose_name="Slice Position")

    phantom_width1 = MedACRPhantomWidth(verbose_name="Phantom Width")
    phantom_width2 = MedACRPhantomWidth(verbose_name="Phantom Width")

    snr_output = OutputFrame(verbose_name="SNR Output")
    image1_output = OutputFrame(verbose_name="Image 1 Results")
    image2_output = OutputFrame(verbose_name="Image 2 Results")

    uniformity_window = WindowGroup([uniformity1, uniformity2], verbose_name="Uniformity")
    ghosting_window = WindowGroup([ghosting1, ghosting2], verbose_name="Ghosting")
    slice_width_window = WindowGroup([slice_width1, slice_width2], verbose_name="Slice Width")
    slice_pos_window = WindowGroup([slice_pos1, slice_pos2], verbose_name="Slice Position")
    phantom_width_window = WindowGroup([phantom_width1, phantom_width2], verbose_name="Phantom Width")

    def load_outputs(self):
        self.snr_output.register_output(self.snr.signal)
        self.snr_output.register_output(self.snr.noise)
        self.snr_output.register_output(self.snr.snr)
        self.snr_output.register_output(self.snr.cor_snr)

        self.image1_output.register_output(self.uniformity1.uniformity)
        self.image1_output.register_output(self.ghosting1.ghosting)
        self.image1_output.register_output(self.slice_width1.slice_width)
        self.image1_output.register_output(self.slice_pos1.slice_1_pos)
        self.image1_output.register_output(self.slice_pos1.slice_11_pos)
        self.image1_output.register_output(self.phantom_width1.linearity)
        self.image1_output.register_output(self.phantom_width1.distortion)

        self.image2_output.register_output(self.uniformity2.uniformity)
        self.image2_output.register_output(self.ghosting2.ghosting)
        self.image2_output.register_output(self.slice_width2.slice_width)
        self.image2_output.register_output(self.slice_pos2.slice_1_pos)
        self.image2_output.register_output(self.slice_pos2.slice_11_pos)
        self.image2_output.register_output(self.phantom_width2.linearity)
        self.image2_output.register_output(self.phantom_width2.distortion)

        IOGroup([self.uniformity1.size, self.uniformity2.size])
        IOGroup([self.uniformity1.kernel_bool, self.uniformity2.kernel_bool])
        IOGroup([self.ghosting1.size, self.ghosting2.size])
        IOGroup([self.slice_width1.tan_theta, self.slice_width2.tan_theta])
        IOGroup([self.slice_width1.max_perc, self.slice_width2.max_perc])
        IOGroup([self.phantom_width1.max_perc, self.phantom_width2.max_perc])
        IOGroup([self.phantom_width1.bool_vertical, self.phantom_width2.bool_vertical])
        IOGroup([self.phantom_width1.bool_horizontal, self.phantom_width2.bool_horizontal])
        IOGroup([self.phantom_width1.bool_up_slope, self.phantom_width2.bool_up_slope])
        IOGroup([self.phantom_width1.bool_down_slope, self.phantom_width2.bool_down_slope])

    def on_image_load(self, viewer: BaseViewer) -> None:
        if viewer is self.viewer1:
            if self.viewer1.image is not None:
                image = self.viewer1.image
                self.snr.viewer1.load_image(image)
                self.uniformity1.viewer.load_image(image)
                self.ghosting1.viewer.load_image(image)
                self.slice_width1.viewer.load_image(image)
                self.slice_pos1.viewer1.load_image(image)
                self.phantom_width1.viewer.load_image(image)
        elif viewer is self.viewer2:
            if self.viewer2.image is not None:
                image = self.viewer2.image
                self.snr.viewer2.load_image(image)
                self.uniformity2.viewer.load_image(image)
                self.ghosting2.viewer.load_image(image)
                self.slice_width2.viewer.load_image(image)
                self.slice_pos2.viewer1.load_image(image)
                self.phantom_width2.viewer.load_image(image)
