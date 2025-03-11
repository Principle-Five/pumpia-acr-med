"""
Collection for Medium ACR with repeat images.
"""

from pumpia.module_handling.module_collections import (OutputFrame,
                                                       BaseCollection)
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.widgets.viewers import BaseViewer

from .modules.sub_snr import MedACRSubSNR
from .acr_med_context import MedACRContextManagerGenerator


class MedACRrptCollection(BaseCollection):
    context_manager_generator = MedACRContextManagerGenerator()

    viewer1 = MonochromeDicomViewerIO(row=0, column=0)
    viewer2 = MonochromeDicomViewerIO(row=0, column=1)

    snr = MedACRSubSNR(verbose_name="SNR")

    snr_output = OutputFrame(verbose_name="SNR Output")

    def load_outputs(self):
        self.snr_output.register_output(self.snr.signal)
        self.snr_output.register_output(self.snr.noise)
        self.snr_output.register_output(self.snr.snr)
        self.snr_output.register_output(self.snr.cor_snr)

    def on_image_load(self, viewer: BaseViewer) -> None:
        if viewer is self.viewer1:
            if self.viewer1.image is not None:
                image = self.viewer1.image
                self.snr.viewer1.load_image(image)
        elif viewer is self.viewer2:
            if self.viewer2.image is not None:
                image = self.viewer2.image
                self.snr.viewer2.load_image(image)
