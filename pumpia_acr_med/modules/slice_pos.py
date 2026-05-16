"""
Slice postition for Medium ACR Phantom.

Slice position is given in absolute offset, not the distance measured by the bars.
"""
import numpy as np
import matplotlib.pyplot as plt

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.fields.roi_fields import RectangleROIField
from pumpia.module_handling.fields.viewer_fields import MonochromeDicomViewerField
from pumpia.module_handling.fields.simple import FloatField, StringField
from pumpia.image_handling.roi_structures import RectangleROI
from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.utilities.array_utils import nth_max_positions

from pumpia_acr_med.med_acr_context import MedACRContextManager, MedACRContext

ROI_OFFSET = 55
ROI_WIDTH = 2
ROI_HEIGHT = 10
LEFT_OFFSET = -5
RIGHT_OFFSET = 1


class MedACRSlicePosition(PhantomModule):
    """
    Calculates slice position for the medium ACR phantom.

    Slice position is given in absolute offset, not the distance measured by the bars.
    """
    context_manager = MedACRContextManager()
    show_draw_rois_button = True
    show_analyse_button = True
    title = "Slice Position"

    viewer1 = MonochromeDicomViewerField(row=0, column=0)
    viewer2 = MonochromeDicomViewerField(row=0, column=1, allow_drag_drop=False)

    wedge_dir = StringField(verbose_name="Wedge Direction",
                            read_only=True)
    wedge_side = StringField(read_only=True)

    slice_1_bar_diff = FloatField(verbose_name="Slice 1 Bar Length Difference (mm)",
                                  reset_on_analysis=True,
                                  read_only=True)
    slice_1_pos = FloatField(verbose_name="Slice 1 position (mm)",
                             reset_on_analysis=True,
                             read_only=True)
    slice_11_bar_diff = FloatField(verbose_name="Slice 11 Bar Length Difference (mm)",
                                   reset_on_analysis=True,
                                   read_only=True)
    slice_11_pos = FloatField(verbose_name="Slice 11 position (mm)",
                              reset_on_analysis=True,
                              read_only=True)

    slice_1_left_wedge = RectangleROIField()
    slice_1_right_wedge = RectangleROIField()
    slice_11_left_wedge = RectangleROIField()
    slice_11_right_wedge = RectangleROIField()

    def draw_rois(self, context: MedACRContext, batch: bool = False) -> None:

        if isinstance(self.viewer1.image, Instance):
            image = self.viewer1.image.series
        elif isinstance(self.viewer1.image, Series):
            image = self.viewer1.image
        else:
            return

        if context.inserts_slice == 10:
            image1 = image.instances[10]
            image2 = image.instances[0]
        else:
            image1 = image.instances[0]
            image2 = image.instances[10]

        self.viewer1.load_image(image1)
        self.viewer2.load_image(image2)

        pixel_size = image.pixel_spacing
        if pixel_size is None:
            return
        pixel_height = pixel_size[0]
        pixel_width = pixel_size[1]

        if context.res_insert_side == "right" or context.res_insert_side == "left":
            self.wedge_dir = "Horizontal"
            box_height = ROI_WIDTH / pixel_height
            box_width = ROI_HEIGHT / pixel_width
            left_pix_offset = LEFT_OFFSET / pixel_height
            right_pix_offset = RIGHT_OFFSET / pixel_height

            if context.res_insert_side == "right":
                self.wedge_side = "left"
                left_xmin = right_xmin = round(context.xcent - box_width - ROI_OFFSET)
                left_xmax = right_xmax = round(context.xcent + box_width - ROI_OFFSET)
                left_ymin = round(context.ycent + left_pix_offset)
                left_ymax = round(context.ycent + left_pix_offset + box_height)
                right_ymin = round(context.ycent + right_pix_offset)
                right_ymax = round(context.ycent + right_pix_offset + box_height)
            else:
                self.wedge_side = "right"
                left_xmin = right_xmin = round(context.xcent - box_width + ROI_OFFSET)
                left_xmax = right_xmax = round(context.xcent + box_width + ROI_OFFSET)
                left_ymin = round(context.ycent - left_pix_offset - box_height)
                left_ymax = round(context.ycent - left_pix_offset)
                right_ymin = round(context.ycent - right_pix_offset - box_height)
                right_ymax = round(context.ycent - right_pix_offset)
        else:
            self.wedge_dir = "Vertical"
            box_height = ROI_HEIGHT / pixel_height
            box_width = ROI_WIDTH / pixel_width
            left_pix_offset = LEFT_OFFSET / pixel_width
            right_pix_offset = RIGHT_OFFSET / pixel_width

            if context.res_insert_side == "bottom":
                self.wedge_side = "top"
                left_ymin = right_ymin = round(context.ycent - box_height - ROI_OFFSET)
                left_ymax = right_ymax = round(context.ycent + box_height - ROI_OFFSET)

                left_xmin = round(context.xcent + left_pix_offset)
                left_xmax = round(context.xcent + left_pix_offset + box_width)
                right_xmin = round(context.xcent + right_pix_offset)
                right_xmax = round(context.xcent + right_pix_offset + box_width)
            else:
                self.wedge_side = "bottom"
                left_ymin = right_ymin = round(context.ycent - box_width + ROI_OFFSET)
                left_ymax = right_ymax = round(context.ycent + box_width + ROI_OFFSET)
                left_xmin = round(context.xcent - left_pix_offset - box_width)
                left_xmax = round(context.xcent - left_pix_offset)
                right_xmin = round(context.xcent - right_pix_offset - box_width)
                right_xmax = round(context.xcent - right_pix_offset)

        left_roi = RectangleROI(image1,
                                left_xmin,
                                left_ymin,
                                left_xmax - left_xmin,
                                left_ymax - left_ymin,
                                slice_num=image1.current_slice,
                                replace=True)
        self.slice_1_left_wedge.register_roi(left_roi)
        if self.slice_1_left_wedge.roi is not None:
            self.slice_11_left_wedge.register_roi(
                self.slice_1_left_wedge.roi.copy_to_image(
                    image2,
                    image2.current_slice,
                    replace=True))

        right_roi = RectangleROI(image1,
                                 right_xmin,
                                 right_ymin,
                                 right_xmax - right_xmin,
                                 right_ymax - right_ymin,
                                 slice_num=image1.current_slice,
                                 replace=True)
        self.slice_1_right_wedge.register_roi(right_roi)
        if self.slice_1_right_wedge.roi is not None:
            self.slice_11_right_wedge.register_roi(
                self.slice_1_right_wedge.roi.copy_to_image(
                    image2,
                    image2.current_slice,
                    replace=True))

    def post_roi_register(self, roi_input: RectangleROIField):
        if (roi_input.roi is not None
            and self.manager is not None
                and roi_input in self.rois):
            self.manager.add_roi(roi_input.roi)

    def link_rois_viewers(self):
        self.slice_1_left_wedge.viewer = self.viewer1
        self.slice_1_right_wedge.viewer = self.viewer1
        self.slice_11_left_wedge.viewer = self.viewer2
        self.slice_11_right_wedge.viewer = self.viewer2

    def analyse(self, batch: bool = False):
        if (self.slice_11_left_wedge.roi is not None
            and self.slice_11_right_wedge.roi is not None
            and self.slice_1_left_wedge.roi is not None
                and self.slice_1_right_wedge.roi is not None):

            if isinstance(self.slice_1_right_wedge.roi.image, (Instance, Series)):
                pixel_spacing = self.slice_1_right_wedge.roi.image.pixel_spacing
                if pixel_spacing is None:
                    return
            else:
                return

            if self.wedge_dir[0].lower() == "h":
                slice_11_left_prof = self.slice_11_left_wedge.roi.h_profile
                slice_11_right_prof = self.slice_11_right_wedge.roi.h_profile
                slice_1_left_prof = self.slice_1_left_wedge.roi.h_profile
                slice_1_right_prof = self.slice_1_right_wedge.roi.h_profile
                pix_size = pixel_spacing[1]
            else:
                slice_11_left_prof = self.slice_11_left_wedge.roi.v_profile
                slice_11_right_prof = self.slice_11_right_wedge.roi.v_profile
                slice_1_left_prof = self.slice_1_left_wedge.roi.v_profile
                slice_1_right_prof = self.slice_1_right_wedge.roi.v_profile
                pix_size = pixel_spacing[0]

            slice_11_left_nth_max = nth_max_positions(slice_11_left_prof, 2)
            slice_11_right_nth_max = nth_max_positions(slice_11_right_prof, 2)
            slice_1_left_nth_max = nth_max_positions(slice_1_left_prof, 2)
            slice_1_right_nth_max = nth_max_positions(slice_1_right_prof, 2)

            if self.wedge_side == "left" or self.wedge_side == "top":
                slice_11_left_hm = slice_11_left_nth_max[0]
                slice_11_right_hm = slice_11_right_nth_max[0]
                slice_1_left_hm = slice_1_left_nth_max[0]
                slice_1_right_hm = slice_1_right_nth_max[0]
            else:
                slice_11_left_hm = -slice_11_left_nth_max[-1]
                slice_11_right_hm = -slice_11_right_nth_max[-1]
                slice_1_left_hm = -slice_1_left_nth_max[-1]
                slice_1_right_hm = -slice_1_right_nth_max[-1]

            self.slice_1_bar_diff = (slice_1_right_hm - slice_1_left_hm) * pix_size
            self.slice_1_pos = self.slice_1_bar_diff / 2
            self.slice_11_bar_diff = (slice_11_right_hm - slice_11_left_hm) * pix_size
            self.slice_11_pos = self.slice_11_bar_diff / 2

    def load_commands(self):
        self.register_command("Show Profiles", self.show_profiles)

    def show_profiles(self):
        """
        Shows the ROI profiles
        """
        if (self.slice_11_left_wedge.roi is not None
            and self.slice_11_right_wedge.roi is not None
            and self.slice_1_left_wedge.roi is not None
                and self.slice_1_right_wedge.roi is not None):

            if isinstance(self.slice_1_right_wedge.roi.image, (Instance, Series)):
                pixel_spacing = self.slice_1_right_wedge.roi.image.pixel_spacing
                if pixel_spacing is None:
                    return
            else:
                return

            if self.wedge_dir[0].lower() == "h":
                slice_11_left_prof = self.slice_11_left_wedge.roi.h_profile
                slice_11_right_prof = self.slice_11_right_wedge.roi.h_profile
                slice_1_left_prof = self.slice_1_left_wedge.roi.h_profile
                slice_1_right_prof = self.slice_1_right_wedge.roi.h_profile
                pix_size = pixel_spacing[1]
            else:
                slice_11_left_prof = self.slice_11_left_wedge.roi.v_profile
                slice_11_right_prof = self.slice_11_right_wedge.roi.v_profile
                slice_1_left_prof = self.slice_1_left_wedge.roi.v_profile
                slice_1_right_prof = self.slice_1_right_wedge.roi.v_profile
                pix_size = pixel_spacing[0]

            locs = np.indices(slice_11_left_prof.shape)[0] * pix_size / 2

            plt.clf()
            plt.plot(locs, slice_1_left_prof, label="Slice 1 Left Wedge")
            plt.plot(locs, slice_1_right_prof, label="Slice 1 Right Wedge")
            plt.plot(locs, slice_11_left_prof, label="Slice 11 Left Wedge")
            plt.plot(locs, slice_11_right_prof, label="Slice 11 Right Wedge")

            plt.legend()
            plt.xlabel("Position (Pixels)")
            plt.ylabel("Value")
            plt.title("ROI Profiles")
            plt.show()
