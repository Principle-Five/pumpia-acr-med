"""
Ghosting module for medium ACR phantom.

This does not follow ACR guidelines
"""
from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import InputEllipseROI, InputRectangleROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import (PercInput,
                                                   FloatOutput,
                                                   IntOutput)
from pumpia.image_handling.roi_structures import EllipseROI, RectangleROI
from pumpia.file_handling.dicom_structures import Series, Instance

from pumpia_acr_med.med_acr_context import MedACRContextManagerGenerator, MedACRContext


class MedACRGhosting(PhantomModule):
    """
    Ghosting module for medium ACR phantom.
    """
    context_manager_generator = MedACRContextManagerGenerator()
    show_draw_rois_button = True
    show_analyse_button = True

    viewer = MonochromeDicomViewerIO(row=0, column=0)

    size = PercInput(70, verbose_name="Size (%)")

    slice_used = IntOutput()
    ghosting = FloatOutput(verbose_name="Ghosting (%)", reset_on_analysis=True)

    phantom_roi = InputEllipseROI("Phantom ROI")
    top_roi = InputRectangleROI("Top ROI")
    bottom_roi = InputRectangleROI("Bottom ROI")
    left_roi = InputRectangleROI("Left ROI")
    right_roi = InputRectangleROI("Right ROI")

    def draw_rois(self, context: MedACRContext, batch: bool = False) -> None:
        if isinstance(self.viewer.image, Instance):
            image = self.viewer.image
        elif isinstance(self.viewer.image, Series):
            if context.inserts_slice == 10:
                self.slice_used.value = 4
                image = self.viewer.image.instances[4]
            else:
                self.slice_used.value = 6
                image = self.viewer.image.instances[6]
        else:
            return

        self.viewer.load_image(image)
        factor = self.size.value / 100
        a = round(factor * context.x_length / 2)
        b = round(factor * context.y_length / 2)
        phant_roi = EllipseROI(image,
                               round(context.xcent),
                               round(context.ycent),
                               a,
                               b,
                               slice_num=image.current_slice)

        tb_xmin = phant_roi.xmin
        tb_xmax = phant_roi.xmax
        lr_ymin = phant_roi.ymin
        lr_ymax = phant_roi.ymax

        self.phantom_roi.register_roi(phant_roi)

        top_ymin = 3
        top_ymax = context.ymin - 3

        bottom_ymin = context.ymax + 3
        bottom_ymax = image.shape[1] - 3

        left_xmin = 3
        left_xmax = context.xmin - 3

        right_xmin = context.xmax + 3
        right_xmax = image.shape[2] - 3

        top = RectangleROI(image,
                           tb_xmin,
                           top_ymin,
                           tb_xmax - tb_xmin,
                           top_ymax - top_ymin,
                           slice_num=image.current_slice)
        self.top_roi.register_roi(top)

        bottom = RectangleROI(image,
                              tb_xmin,
                              bottom_ymin,
                              tb_xmax - tb_xmin,
                              bottom_ymax - bottom_ymin,
                              slice_num=image.current_slice)
        self.bottom_roi.register_roi(bottom)

        left = RectangleROI(image,
                            left_xmin,
                            lr_ymin,
                            left_xmax - left_xmin,
                            lr_ymax - lr_ymin,
                            slice_num=image.current_slice)
        self.left_roi.register_roi(left)

        right = RectangleROI(image,
                             right_xmin,
                             lr_ymin,
                             right_xmax - right_xmin,
                             lr_ymax - lr_ymin,
                             slice_num=image.current_slice)
        self.right_roi.register_roi(right)

    def post_roi_register(self, roi_input: InputEllipseROI):
        if (roi_input in self.rois
            and roi_input.roi is not None
                and self.manager is not None):
            self.manager.add_roi(roi_input.roi)

    def link_rois_viewers(self):
        self.phantom_roi.viewer = self.viewer
        self.top_roi.viewer = self.viewer
        self.bottom_roi.viewer = self.viewer
        self.left_roi.viewer = self.viewer
        self.right_roi.viewer = self.viewer

    def analyse(self, batch: bool = False):
        if (self.phantom_roi.roi is not None
            and self.top_roi.roi is not None
            and self.bottom_roi.roi is not None
            and self.left_roi.roi is not None
                and self.right_roi.roi is not None):

            signal = self.phantom_roi.roi.mean
            top = self.top_roi.roi.mean
            bottom = self.bottom_roi.roi.mean
            left = self.left_roi.roi.mean
            right = self.right_roi.roi.mean

            if (isinstance(signal, float)
                and isinstance(top, float)
                and isinstance(bottom, float)
                and isinstance(left, float)
                    and isinstance(right, float)):

                self.ghosting.value = 100 * abs(((top + bottom) - (left + right)) / (2 * signal))
