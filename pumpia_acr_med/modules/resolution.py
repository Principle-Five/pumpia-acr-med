import numpy as np

from pumpia.module_handling.modules import PhantomModule
from pumpia.module_handling.in_outs.roi_ios import BaseInputROI, InputRectangleROI, InputLineROI
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO
from pumpia.module_handling.in_outs.simple import FloatOutput
from pumpia.image_handling.roi_structures import RectangleROI, LineROI
from pumpia.file_handling.dicom_structures import Series, Instance

from pumpia_acr_med.med_acr_context import MedACRContextManagerGenerator, MedACRContext

BOX_Y_OFFSET = 28
BOX_X_OFFSET = -5
BOX_SIDE_LENGTH = 19
LINE_LENGTH = 7
LINE_GAP = 2

# step 1: draw big box
# step 2: find centre pixel from big box profiles
# step 3: draw horizontal and vertical lines across rows/columns defined by ACR
# step 4: get contrast (max-min)/(max+min) for each line
# step 5: result is maximum contrast for rows/columns


class MedACRResolution(PhantomModule):
    """
    Calculates the MTF of the 1mm resolution insert.
    """
    context_manager_generator = MedACRContextManagerGenerator()
    show_draw_rois_button = True
    show_analyse_button = True

    viewer = MonochromeDicomViewerIO(row=0, column=0)

    vertical_mtf = FloatOutput(verbose_name="Vertical MTF (%)")
    horizontal_mtf = FloatOutput(verbose_name="Horizontal MTF (%)")
    total_mtf = FloatOutput(verbose_name="MTF (%)")

    main_roi = InputRectangleROI()
    horizontal_line_1 = InputLineROI()
    horizontal_line_2 = InputLineROI()
    horizontal_line_3 = InputLineROI()
    horizontal_line_4 = InputLineROI()
    vertical_line_1 = InputLineROI()
    vertical_line_2 = InputLineROI()
    vertical_line_3 = InputLineROI()
    vertical_line_4 = InputLineROI()

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

        if horizontal_dir[0] == "U":
            h_line_gap = round(-LINE_GAP * pixel_height)
        else:
            h_line_gap = round(LINE_GAP * pixel_height)
        h_line_length = LINE_LENGTH * pixel_width

        if vertical_dir[1] == "L":
            v_line_gap = round(-LINE_GAP * pixel_width)
        else:
            v_line_gap = round(LINE_GAP * pixel_width)
        v_line_length = LINE_LENGTH * pixel_height

        if not self.main_roi.roi is None:
            x_cent_loc = int(np.argmax(self.main_roi.roi.h_profile)) + self.main_roi.roi.xmin
            y_cent_loc = int(np.argmax(self.main_roi.roi.v_profile)) + self.main_roi.roi.ymin

            if vertical_dir[0] == "U":
                v_ymin = y_cent_loc - round(v_line_length)
                v_ymax = y_cent_loc
            else:
                v_ymin = y_cent_loc
                v_ymax = y_cent_loc + round(v_line_length)

            if horizontal_dir[1] == "L":
                h_xmin = x_cent_loc - round(h_line_length)
                h_xmax = x_cent_loc
            else:
                h_xmin = x_cent_loc
                h_xmax = x_cent_loc + round(h_line_length)

            self.horizontal_line_1.register_roi(LineROI(image,
                                                        h_xmin,
                                                        y_cent_loc,
                                                        h_xmax,
                                                        y_cent_loc))
            self.horizontal_line_2.register_roi(LineROI(image,
                                                        h_xmin,
                                                        y_cent_loc + h_line_gap,
                                                        h_xmax,
                                                        y_cent_loc + h_line_gap))
            self.horizontal_line_3.register_roi(LineROI(image,
                                                        h_xmin,
                                                        y_cent_loc + 2 * h_line_gap,
                                                        h_xmax,
                                                        y_cent_loc + 2 * h_line_gap))
            self.horizontal_line_4.register_roi(LineROI(image,
                                                        h_xmin,
                                                        y_cent_loc + 3 * h_line_gap,
                                                        h_xmax,
                                                        y_cent_loc + 3 * h_line_gap))
            self.vertical_line_1.register_roi(LineROI(image,
                                                      x_cent_loc,
                                                      v_ymin,
                                                      x_cent_loc,
                                                      v_ymax))
            self.vertical_line_2.register_roi(LineROI(image,
                                                      x_cent_loc + v_line_gap,
                                                      v_ymin,
                                                      x_cent_loc + v_line_gap,
                                                      v_ymax))
            self.vertical_line_3.register_roi(LineROI(image,
                                                      x_cent_loc + 2 * v_line_gap,
                                                      v_ymin,
                                                      x_cent_loc + 2 * v_line_gap,
                                                      v_ymax))
            self.vertical_line_4.register_roi(LineROI(image,
                                                      x_cent_loc + 3 * v_line_gap,
                                                      v_ymin,
                                                      x_cent_loc + 3 * v_line_gap,
                                                      v_ymax))

    def post_roi_register(self, roi_input: BaseInputROI):
        if (roi_input.roi is not None
            and self.manager is not None
                and roi_input in self.rois):
            self.manager.add_roi(roi_input.roi)

    def link_rois_viewers(self):
        self.main_roi.viewer = self.viewer
        self.horizontal_line_1.viewer = self.viewer
        self.horizontal_line_2.viewer = self.viewer
        self.horizontal_line_3.viewer = self.viewer
        self.horizontal_line_4.viewer = self.viewer
        self.vertical_line_1.viewer = self.viewer
        self.vertical_line_2.viewer = self.viewer
        self.vertical_line_3.viewer = self.viewer
        self.vertical_line_4.viewer = self.viewer

    def analyse(self, batch: bool = False):
        pass
