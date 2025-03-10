import tkinter as tk
from tkinter import ttk
from typing import overload, Literal

import numpy as np

from pumpia.file_handling.dicom_structures import Series, Instance
from pumpia.module_handling.manager import Manager
from pumpia.utilities.typing import DirectionType, SideType
from pumpia.widgets.typing import ScreenUnits, Cursor, Padding, Relief, TakeFocusValue
from pumpia.widgets.context_managers import (BaseContextManager,
                                             AutoPhantomManager,
                                             side_map,
                                             inv_side_map,
                                             side_opts)
from pumpia.module_handling.context import BaseContext, PhantomContext

inserts_slice_map: dict[str, int] = {"1": 0,
                                     "11": 10}
inv_inserts_slice_map: dict[int, str] = {v: k for k, v in inserts_slice_map.items()}
inserts_slice_opts = list(inserts_slice_map.keys())

four_box_offset = 17
four_box_width = 10
five_box_offset = 28
five_box_width = 5


class MedACRContext(PhantomContext):
    """
    Context for Medium ACR Phantom.
    """

    def __init__(self,
                 xmin: int,
                 xmax: int,
                 ymin: int,
                 ymax: int,
                 first_slice_pos: Literal[0] | Literal[10] = 0,
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
        self.first_slice_pos: Literal[0] | Literal[10] = first_slice_pos


class MedACRContextManager(BaseContextManager):
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
        super().__init__(parent, manager=manager, direction=direction, text=text, **kw)
        self.auto_phantom_manager = AutoPhantomManager(self,
                                                       manager=manager,
                                                       mode=mode,
                                                       sensitivity=sensitivity,
                                                       top_perc=top_perc,
                                                       iterations=iterations,
                                                       cull_perc=cull_perc,
                                                       bubble_offset=bubble_offset,
                                                       bubble_side=bubble_side,
                                                       shape='ellipse',
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

        min_slice = np.argmin(image.z_profile)

        if min_slice == 4:
            inserts_slice = 0
        else:
            inserts_slice = 10

        boundary_context = self.auto_phantom_manager.get_context(image.instances[inserts_slice])

        pixel_size = image.pixel_size
        pixel_height = pixel_size[1]
        pixel_width = pixel_size[2]

        xcent = boundary_context.xcent
        ycent = boundary_context.ycent

        four_box_offset_x = 17 * pixel_width
        four_box_offset_y = 17 * pixel_height

        four_box_width = 10 * pixel_width
        four_box_height = 10 * pixel_height

        five_box_offset_x = 28 * pixel_width
        five_box_offset_y = 28 * pixel_height

        five_box_width = 5 * pixel_width
        five_box_height = 5 * pixel_height
