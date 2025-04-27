"""
Contains context handling for medium ACR phantom
"""

import tkinter as tk
from tkinter import ttk
from typing import overload, Literal

import numpy as np

from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.module_handling.manager import Manager
from pumpia.image_handling.roi_structures import RectangleROI, PointROI
from pumpia.utilities.typing import DirectionType, SideType
from pumpia.widgets.typing import ScreenUnits, Cursor, Padding, Relief, TakeFocusValue
from pumpia.widgets.context_managers import (PhantomContextManager,
                                             AutoPhantomManager,
                                             PhantomContextManagerGenerator,
                                             side_map,
                                             inv_side_map,
                                             side_opts)
from pumpia.module_handling.context import PhantomContext

inserts_slice_map: dict[str, int] = {"1": 0,
                                     "11": 10}
inv_inserts_slice_map: dict[int, str] = {v: k for k, v in inserts_slice_map.items()}
inserts_slice_opts = list(inserts_slice_map.keys())

# offsets in mm (dicom standard units)
FOUR_BOX_OFFSET = 17
FOUR_BOX_SL = 10
FIVE_BOX_OFFSET = 28
FIVE_BOX_SL = 5


class MedACRContext(PhantomContext):
    """
    Context for Medium ACR Phantom.
    """

    def __init__(self,
                 xmin: int,
                 xmax: int,
                 ymin: int,
                 ymax: int,
                 inserts_slice: Literal[0] | Literal[10] = 0,
                 res_insert_side: SideType = "bottom",
                 circle_insert_side: SideType = "left"):
        super().__init__(xmin, xmax, ymin, ymax, 'ellipse')

        if ((res_insert_side in ["top", "bottom"]
             and circle_insert_side in ["top", "bottom"])
            or (res_insert_side in ["left", "right"]
                and circle_insert_side in ["left", "right"])):
            raise ValueError("resolution/circle insert sides must not be on the same axis")

        self.res_insert_side: SideType = res_insert_side
        self.circle_insert_side: SideType = circle_insert_side
        self.inserts_slice: Literal[0] | Literal[10] = inserts_slice


class MedACRContextManager(PhantomContextManager):
    """
    Context Manager for Medium ACR Phantom.
    """
    @overload
    def __init__(self,
                 parent: tk.Misc,
                 manager: Manager,
                 mode: Literal["auto", "manual"] = "auto",
                 sensitivity: int = 3,
                 top_perc: int = 95,
                 iterations: int = 2,
                 cull_perc: int = 80,
                 bubble_offset: int = 0,
                 bubble_side: SideType = "top",
                 direction: DirectionType = "Vertical",
                 text: float | str = "Medium ACR Context",
                 *,
                 border: ScreenUnits = ...,
                 borderwidth: ScreenUnits = ...,  # undocumented
                 class_: str = "",
                 cursor: Cursor = "",
                 height: ScreenUnits = 0,
                 labelanchor: Literal["nw", "n", "ne",
                                      "en", "e", "es",
                                      "se", "s", "sw",
                                      "ws", "w", "wn"] = ...,
                 labelwidget: tk.Misc = ...,
                 name: str = ...,
                 padding: Padding = ...,
                 relief: Relief = ...,  # undocumented
                 style: str = "",
                 takefocus: TakeFocusValue = "",
                 underline: int = -1,
                 width: ScreenUnits = 0,
                 ) -> None: ...

    @overload
    def __init__(self,
                 parent: tk.Misc,
                 manager: Manager,
                 mode: Literal["auto", "manual"] = "auto",
                 sensitivity: int = 3,
                 top_perc: int = 95,
                 iterations: int = 2,
                 cull_perc: int = 80,
                 bubble_offset: int = 0,
                 bubble_side: SideType = "top",
                 direction: DirectionType = "Vertical",
                 text: float | str = "Medium ACR Context",
                 **kw) -> None: ...

    def __init__(self,
                 parent: tk.Misc,
                 manager: Manager,
                 mode: Literal["auto", "manual"] = "auto",
                 sensitivity: int = 3,
                 top_perc: int = 95,
                 iterations: int = 2,
                 cull_perc: int = 80,
                 bubble_offset: int = 0,
                 bubble_side: SideType = "top",
                 direction: DirectionType = "Vertical",
                 text: float | str = "Medium ACR Context",
                 **kw) -> None:
        kw["shape"] = "ellipse"
        super().__init__(parent,
                         manager=manager,
                         direction=direction,
                         text=text,
                         **kw)
        self.auto_phantom_manager = AutoPhantomManager(self,
                                                       manager=manager,
                                                       mode=mode,
                                                       sensitivity=sensitivity,
                                                       top_perc=top_perc,
                                                       iterations=iterations,
                                                       cull_perc=cull_perc,
                                                       bubble_offset=bubble_offset,
                                                       bubble_side=bubble_side,
                                                       direction=direction,
                                                       text="Bound Box Options",
                                                       **kw)

        self.inserts_frame = ttk.Labelframe(self, text="Inserts")

        self.inserts_slice_var = tk.StringVar(self, inv_inserts_slice_map[0])
        self.inserts_slice_combo = ttk.Combobox(self.inserts_frame,
                                                textvariable=self.inserts_slice_var,
                                                values=inserts_slice_opts,
                                                height=4,
                                                state="readonly")
        self.inserts_slice_label = ttk.Label(self.inserts_frame, text="Inserts Slice")
        self.inserts_slice_label.grid(column=0, row=0, sticky="nsew")
        self.inserts_slice_combo.grid(column=1, row=0, sticky="nsew")

        self.res_insert_var = tk.StringVar(self, inv_side_map["bottom"])
        self.res_insert_combo = ttk.Combobox(self.inserts_frame,
                                             textvariable=self.res_insert_var,
                                             values=side_opts,
                                             height=4,
                                             state="readonly")
        self.res_insert_label = ttk.Label(self.inserts_frame, text="Resolution Insert Side")
        self.res_insert_label.grid(column=0, row=1, sticky="nsew")
        self.res_insert_combo.grid(column=1, row=1, sticky="nsew")

        self.circle_insert_var = tk.StringVar(self, inv_side_map["left"])
        self.circle_insert_combo = ttk.Combobox(self.inserts_frame,
                                                textvariable=self.circle_insert_var,
                                                values=side_opts,
                                                height=4,
                                                state="readonly")
        self.circle_insert_label = ttk.Label(self.inserts_frame, text="Circle Insert Side")
        self.circle_insert_label.grid(column=0, row=2, sticky="nsew")
        self.circle_insert_combo.grid(column=1, row=2, sticky="nsew")

        self.show_boxes_var = tk.BooleanVar(self)
        self.show_boxes_button = ttk.Checkbutton(self.inserts_frame,
                                                 text="Show Boxes",
                                                 variable=self.show_boxes_var)
        self.show_boxes_button.grid(column=0, row=3, columnspan=2, sticky="nsew")

        if self.direction[0].lower() == "h":
            self.auto_phantom_manager.grid(column=0, row=0, sticky="nsew")
            self.inserts_frame.grid(column=1, row=0, sticky="nsew")
        else:
            self.auto_phantom_manager.grid(column=0, row=0, sticky="nsew")
            self.inserts_frame.grid(column=0, row=1, sticky="nsew")

    def get_context(self, image: Series | Instance) -> MedACRContext:
        if isinstance(image, Instance):
            image = image.series

        if image.num_slices != 11:
            raise ValueError("Expected ACR Image with 11 slices")

        if self.auto_phantom_manager.mode_var.get() == "fine tune":
            inserts_slice = inserts_slice_map[self.inserts_slice_var.get()]
        else:

            min_slice = np.argmin(image.z_profile)

            if min_slice == 4:
                inserts_slice = 0
            else:
                inserts_slice = 10

            self.inserts_slice_var.set(inv_inserts_slice_map[inserts_slice])

        inserts_image = image.instances[inserts_slice]

        boundary_context = self.auto_phantom_manager.get_context(inserts_image)

        res_insert_side: SideType
        circle_insert_side: SideType

        if self.auto_phantom_manager.mode_var.get() == "fine tune":
            res_insert_side = side_map[self.res_insert_var.get()]
            circle_insert_side = side_map[self.circle_insert_var.get()]
            return MedACRContext(boundary_context.xmin,
                                 boundary_context.xmax,
                                 boundary_context.ymin,
                                 boundary_context.ymax,
                                 inserts_slice,  # type: ignore
                                 res_insert_side,
                                 circle_insert_side)

        pixel_size = inserts_image.pixel_size
        pixel_height = pixel_size[1]
        pixel_width = pixel_size[2]

        inserts_image_array = inserts_image.array[0]

        xcent = boundary_context.xcent
        ycent = boundary_context.ycent

        four_box_offset_x = FOUR_BOX_OFFSET / pixel_width
        four_box_offset_y = FOUR_BOX_OFFSET / pixel_height

        four_box_width = FOUR_BOX_SL / pixel_width
        four_box_height = FOUR_BOX_SL / pixel_height

        five_box_offset_x = FIVE_BOX_OFFSET / pixel_width
        five_box_offset_y = FIVE_BOX_OFFSET / pixel_height

        five_box_width = FIVE_BOX_SL / pixel_width
        five_box_height = FIVE_BOX_SL / pixel_height

        top_box_xmin = round(xcent - four_box_width / 2)
        top_box_xmax = round(xcent + four_box_width / 2) + 1
        top_box_ymin = round(ycent - four_box_offset_y - four_box_height)
        top_box_ymax = round(ycent - four_box_offset_y) + 1

        bottom_box_xmin = round(xcent - four_box_width / 2)
        bottom_box_xmax = round(xcent + four_box_width / 2) + 1
        bottom_box_ymin = round(ycent + four_box_offset_y)
        bottom_box_ymax = round(ycent + four_box_offset_y + four_box_height) + 1

        left_box_xmin = round(xcent - four_box_offset_x - four_box_width)
        left_box_xmax = round(xcent - four_box_offset_x) + 1
        left_box_ymin = round(ycent - four_box_height / 2)
        left_box_ymax = round(ycent + four_box_height / 2) + 1

        right_box_xmin = round(xcent + four_box_offset_x)
        right_box_xmax = round(xcent + four_box_offset_x + four_box_width) + 1
        right_box_ymin = round(ycent - four_box_height / 2)
        right_box_ymax = round(ycent + four_box_height / 2) + 1

        res_insert_opp = np.argmax([np.mean(inserts_image_array[top_box_ymin:top_box_ymax,
                                                                top_box_xmin:top_box_xmax]),
                                   np.mean(inserts_image_array[bottom_box_ymin:bottom_box_ymax,
                                                               bottom_box_xmin:bottom_box_xmax]),
                                   np.mean(inserts_image_array[left_box_ymin:left_box_ymax,
                                                               left_box_xmin:left_box_xmax]),
                                   np.mean(inserts_image_array[right_box_ymin:right_box_ymax,
                                                               right_box_xmin:right_box_xmax])])

        res_insert_opp = int(res_insert_opp)

        if res_insert_opp == 0 or res_insert_opp == 1:
            five_box_xmin = round(xcent - five_box_offset_x - five_box_width)
            five_box_xmax = round(xcent - five_box_offset_x) + 1
            six_box_xmin = round(xcent + five_box_offset_x)
            six_box_xmax = round(xcent + five_box_offset_x + five_box_width) + 1

            if res_insert_opp == 0:
                res_insert_side = "bottom"
                five_box_ymin = six_box_ymin = round(ycent - five_box_offset_y - five_box_height)
                five_box_ymax = six_box_ymax = round(ycent - five_box_offset_y) + 1
            else:
                res_insert_side = "top"
                five_box_ymin = six_box_ymin = round(ycent + five_box_offset_y)
                five_box_ymax = six_box_ymax = round(ycent + five_box_offset_y
                                                     + five_box_height) + 1

            five_box_mean = np.mean(inserts_image_array[five_box_ymin:five_box_ymax,
                                                        five_box_xmin:five_box_xmax])
            six_box_mean = np.mean(inserts_image_array[six_box_ymin:six_box_ymax,
                                                       six_box_xmin:six_box_xmax])

            if five_box_mean > six_box_mean:
                circle_insert_side = "right"
            else:
                circle_insert_side = "left"

        elif res_insert_opp == 2 or res_insert_opp == 3:
            five_box_ymin = round(ycent - five_box_offset_y - five_box_height)
            five_box_ymax = round(ycent - five_box_offset_y) + 1
            six_box_ymin = round(ycent + five_box_offset_y)
            six_box_ymax = round(ycent + five_box_offset_y + five_box_height) + 1

            if res_insert_opp == 2:
                res_insert_side = "right"
                five_box_xmin = six_box_xmin = round(xcent - five_box_offset_x - five_box_width)
                five_box_xmax = six_box_xmax = round(xcent - five_box_offset_x) + 1
            else:
                res_insert_side = "left"
                five_box_xmin = six_box_xmin = round(xcent + five_box_offset_x)
                five_box_xmax = six_box_xmax = round(xcent + five_box_offset_x + five_box_width) + 1

            five_box_mean = np.mean(inserts_image_array[five_box_ymin:five_box_ymax,
                                                        five_box_xmin:five_box_xmax])
            six_box_mean = np.mean(inserts_image_array[six_box_ymin:six_box_ymax,
                                                       six_box_xmin:six_box_xmax])

            if five_box_mean > six_box_mean:
                circle_insert_side = "bottom"
            else:
                circle_insert_side = "top"

        if self.show_boxes_var.get():
            init_box_width = top_box_xmax - top_box_xmin
            init_box_height = top_box_ymax - top_box_ymin

            top_roi = RectangleROI(image,
                                   top_box_xmin,
                                   top_box_ymin,
                                   init_box_width,
                                   init_box_height,
                                   slice_num=inserts_slice,
                                   replace=True,
                                   name="Top")
            self.manager.add_roi(top_roi)

            bottom_roi = RectangleROI(image,
                                      bottom_box_xmin,
                                      bottom_box_ymin,
                                      init_box_width,
                                      init_box_height,
                                      slice_num=inserts_slice,
                                      replace=True,
                                      name="Bottom")
            self.manager.add_roi(bottom_roi)

            left_roi = RectangleROI(image,
                                    left_box_xmin,
                                    left_box_ymin,
                                    init_box_width,
                                    init_box_height,
                                    slice_num=inserts_slice,
                                    replace=True,
                                    name="Left")
            self.manager.add_roi(left_roi)

            right_roi = RectangleROI(image,
                                     right_box_xmin,
                                     right_box_ymin,
                                     init_box_width,
                                     init_box_height,
                                     slice_num=inserts_slice,
                                     replace=True,
                                     name="Right")
            self.manager.add_roi(right_roi)

            sec_box_width = five_box_xmax - five_box_xmin  # type: ignore
            sec_box_height = five_box_ymax - five_box_ymin  # type: ignore

            five_roi = RectangleROI(image,
                                    five_box_xmin,
                                    five_box_ymin,
                                    sec_box_width,
                                    sec_box_height,
                                    slice_num=inserts_slice,
                                    replace=True,
                                    name="Diagonal 1")
            self.manager.add_roi(five_roi)

            six_roi = RectangleROI(image,
                                   six_box_xmin,
                                   six_box_ymin,
                                   sec_box_width,
                                   sec_box_height,
                                   slice_num=inserts_slice,
                                   replace=True,
                                   name="Diagonal 2")
            self.manager.add_roi(six_roi)

            cent = PointROI(image,
                            round(boundary_context.xcent),
                            round(boundary_context.ycent),
                            slice_num=inserts_slice,
                            name="Centre",
                            replace=True)
            self.manager.add_roi(cent)

        self.res_insert_var.set(inv_side_map[res_insert_side])
        self.circle_insert_var.set(inv_side_map[circle_insert_side])

        return MedACRContext(boundary_context.xmin,
                             boundary_context.xmax,
                             boundary_context.ymin,
                             boundary_context.ymax,
                             inserts_slice,  # type: ignore
                             res_insert_side,
                             circle_insert_side)


class MedACRContextManagerGenerator(PhantomContextManagerGenerator[MedACRContextManager]):
    """
    Generator for MedACRContextManager.
    """
    context_manager_type = MedACRContextManager

    @overload
    def __init__(self,
                 *,
                 mode: Literal["auto", "manual"] = "auto",
                 sensitivity: int = 3,
                 top_perc: int = 95,
                 iterations: int = 2,
                 cull_perc: int = 80,
                 bubble_offset: int = 0,
                 bubble_side: SideType = "top",
                 direction: DirectionType = "Vertical",
                 text: float | str = "Medium ACR Context",
                 border: ScreenUnits = ...,
                 borderwidth: ScreenUnits = ...,  # undocumented
                 class_: str = "",
                 cursor: Cursor = "",
                 height: ScreenUnits = 0,
                 labelanchor: Literal["nw", "n", "ne",
                                      "en", "e", "es",
                                      "se", "s", "sw",
                                      "ws", "w", "wn"] = ...,
                 labelwidget: tk.Misc = ...,
                 name: str = ...,
                 padding: Padding = ...,
                 relief: Relief = ...,  # undocumented
                 style: str = "",
                 takefocus: TakeFocusValue = "",
                 underline: int = -1,
                 width: ScreenUnits = 0,
                 ) -> None: ...

    @overload
    def __init__(self,
                 **kw) -> None: ...

    def __init__(self,
                 **kw) -> None:
        kw["shape"] = "ellipse"
        super().__init__(**kw)
