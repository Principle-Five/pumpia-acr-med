"""
Collection for Medium ACR with repeat images.
"""

from pumpia.module_handling.module_collections import (OutputFrame,
                                                       WindowGroup,
                                                       BaseCollection)
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.widgets.viewers import BaseViewer

from .acr_med_context import MedACRContextManagerGenerator
from .modules.sub_snr import MedACRSubSNR
from .modules.uniformity import MedACRUniformity
from .modules.slice_width import MedACRSliceWidth


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

    slice_width1 = MedACRSliceWidth(verbose_name="Slice Width")
    slice_width2 = MedACRSliceWidth(verbose_name="Slice Width")

    snr_output = OutputFrame(verbose_name="SNR Output")
    image1_output = OutputFrame(verbose_name="Image 1 Results")
    image2_output = OutputFrame(verbose_name="Image 2 Results")

    uniformity_window = WindowGroup([uniformity1, uniformity2], verbose_name="Uniformity")
    slice_width_window = WindowGroup([slice_width1, slice_width2], verbose_name="Slice Width")

    def load_outputs(self):
        self.snr_output.register_output(self.snr.signal)
        self.snr_output.register_output(self.snr.noise)
        self.snr_output.register_output(self.snr.snr)
        self.snr_output.register_output(self.snr.cor_snr)

        self.image1_output.register_output(self.uniformity1.uniformity)
        self.image1_output.register_output(self.slice_width1.slice_width)

        self.image2_output.register_output(self.uniformity2.uniformity)
        self.image2_output.register_output(self.slice_width2.slice_width)

    def on_image_load(self, viewer: BaseViewer) -> None:
        if viewer is self.viewer1:
            if self.viewer1.image is not None:
                image = self.viewer1.image
                self.snr.viewer1.load_image(image)
                self.uniformity1.viewer.load_image(image)
                self.slice_width1.viewer.load_image(image)
        elif viewer is self.viewer2:
            if self.viewer2.image is not None:
                image = self.viewer2.image
                self.snr.viewer2.load_image(image)
                self.uniformity2.viewer.load_image(image)
                self.slice_width2.viewer.load_image(image)
