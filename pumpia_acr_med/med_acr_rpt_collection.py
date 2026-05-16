"""
Collection for Medium ACR with repeat images.
"""

from pumpia.module_handling.collections import ModuleGroup, BaseCollection
from pumpia.module_handling.fields.windows import FieldWindow
from pumpia.module_handling.fields.groups import FieldGroup
from pumpia.module_handling.fields.viewer_fields import MonochromeDicomViewerField
from pumpia.widgets.viewers import MonochromeDicomViewer

from pumpia_acr_med.med_acr_context import MedACRContextManager
from pumpia_acr_med.modules.sub_snr import MedACRSubSNR
from pumpia_acr_med.modules.uniformity import MedACRUniformity
from pumpia_acr_med.modules.ghosting import MedACRGhosting
from pumpia_acr_med.modules.slice_width import MedACRSliceWidth
from pumpia_acr_med.modules.slice_pos import MedACRSlicePosition
from pumpia_acr_med.modules.phantom_width import MedACRPhantomWidth
from pumpia_acr_med.modules.resolution import MedACRResolution


class MedACRrptCollection(BaseCollection):
    """
    Collection for medium ACR phantom with repeated scans.
    """
    context_manager = MedACRContextManager()
    title = "Medium ACR Repeat Collection"

    viewer1 = MonochromeDicomViewerField(row=0, column=0)
    viewer2 = MonochromeDicomViewerField(row=0, column=1)

    snr = MedACRSubSNR(verbose_name="SNR")

    uniformity1 = MedACRUniformity(verbose_name="Uniformity")
    uniformity2 = MedACRUniformity(verbose_name="Uniformity")

    ghosting1 = MedACRGhosting(verbose_name="Ghosting")
    ghosting2 = MedACRGhosting(verbose_name="Ghosting")

    phantom_width1 = MedACRPhantomWidth(verbose_name="Phantom Width")
    phantom_width2 = MedACRPhantomWidth(verbose_name="Phantom Width")

    slice_width1 = MedACRSliceWidth(verbose_name="Slice Width")
    slice_width2 = MedACRSliceWidth(verbose_name="Slice Width")

    slice_pos1 = MedACRSlicePosition(verbose_name="Slice Position")
    slice_pos2 = MedACRSlicePosition(verbose_name="Slice Position")

    resolution1 = MedACRResolution(verbose_name="Resolution")
    resolution2 = MedACRResolution(verbose_name="Resolution")

    snr_output = FieldWindow(snr.fields.signal,
                             snr.fields.noise,
                             snr.fields.snr,
                             snr.fields.cor_snr,
                             verbose_name="SNR Output")
    image1_output = FieldWindow(uniformity1.fields.uniformity,
                                ghosting1.fields.ghosting,
                                slice_width1.fields.slice_width,
                                slice_pos1.fields.slice_1_pos,
                                slice_pos1.fields.slice_11_pos,
                                phantom_width1.fields.linearity,
                                phantom_width1.fields.distortion,
                                resolution1.fields.total_contrast,
                                verbose_name="Image 1 Results")
    image2_output = FieldWindow(uniformity2.fields.uniformity,
                                ghosting2.fields.ghosting,
                                slice_width2.fields.slice_width,
                                slice_pos2.fields.slice_1_pos,
                                slice_pos2.fields.slice_11_pos,
                                phantom_width2.fields.linearity,
                                phantom_width2.fields.distortion,
                                resolution2.fields.total_contrast,
                                verbose_name="Image 2 Results")

    uniformity_size_group = FieldGroup(uniformity1.fields.size,
                                       uniformity2.fields.size)
    uniformity_kernel_group = FieldGroup(uniformity1.fields.kernel_bool,
                                         uniformity2.fields.kernel_bool)
    ghosting_size_group = FieldGroup(ghosting1.fields.size,
                                     ghosting2.fields.size)
    slice_width_tan_theta_group = FieldGroup(slice_width1.fields.tan_theta,
                                             slice_width2.fields.tan_theta)
    slice_width_max_perc_group = FieldGroup(slice_width1.fields.max_perc,
                                            slice_width2.fields.max_perc)
    slice_width_type_group = FieldGroup(slice_width1.fields.fit_type,
                                        slice_width2.fields.fit_type)
    phantom_width_max_perc_group = FieldGroup(phantom_width1.fields.max_perc,
                                              phantom_width2.fields.max_perc)
    phantom_width_inc_vert_group = FieldGroup(phantom_width1.fields.bool_vertical,
                                              phantom_width2.fields.bool_vertical)
    phantom_width_inc_hor_group = FieldGroup(phantom_width1.fields.bool_horizontal,
                                             phantom_width2.fields.bool_horizontal)
    phantom_width_inc_up_group = FieldGroup(phantom_width1.fields.bool_up_slope,
                                            phantom_width2.fields.bool_up_slope)
    phantom_width_inc_down_group = FieldGroup(phantom_width1.fields.bool_down_slope,
                                              phantom_width2.fields.bool_down_slope)
    res_perc_group = FieldGroup(resolution1.fields.resolution_percentage,
                                resolution2.fields.resolution_percentage)
    res_auto_pos_group = FieldGroup(resolution1.fields.auto_position_lines,
                                    resolution2.fields.auto_position_lines)
    res_type_group = FieldGroup(resolution1.fields.resolution_type,
                                resolution2.fields.resolution_type)

    uniformity_window = ModuleGroup(uniformity1, uniformity2,
                                    verbose_name="Uniformity")
    ghosting_window = ModuleGroup(ghosting1, ghosting2,
                                  verbose_name="Ghosting")
    slice_width_window = ModuleGroup(slice_width1, slice_width2,
                                     verbose_name="Slice Width")
    slice_pos_window = ModuleGroup(slice_pos1, slice_pos2,
                                   verbose_name="Slice Position")
    phantom_width_window = ModuleGroup(phantom_width1, phantom_width2,
                                       verbose_name="Phantom Width")
    resolution_window = ModuleGroup(resolution1, resolution2,
                                    verbose_name="Resolution")

    def on_image_load(self, viewer: MonochromeDicomViewer) -> None:
        if viewer is self.viewer1:
            if self.viewer1.image is not None:
                image = self.viewer1.image
                self.snr.viewer1.load_image(image)
                self.uniformity1.viewer.load_image(image)
                self.ghosting1.viewer.load_image(image)
                self.slice_width1.viewer.load_image(image)
                self.slice_pos1.viewer1.load_image(image)
                self.phantom_width1.viewer.load_image(image)
                self.resolution1.viewer.load_image(image)
        elif viewer is self.viewer2:
            if self.viewer2.image is not None:
                image = self.viewer2.image
                self.snr.viewer2.load_image(image)
                self.uniformity2.viewer.load_image(image)
                self.ghosting2.viewer.load_image(image)
                self.slice_width2.viewer.load_image(image)
                self.slice_pos2.viewer1.load_image(image)
                self.phantom_width2.viewer.load_image(image)
                self.resolution2.viewer.load_image(image)
