# Introduction
This repository contains code to analyse the medium ACR phantom using the [PumpIA](https://github.com/Principle-Five/pumpia) framework.
It uses the subtraction SNR method and therefore expects a repeat image, however all modules except the SNR module will run with a single image.

It is currently not validated and is provided as is, see the license for more information.

The collection contains the following tests:
- SNR
- Uniformity
- Slice Width
- Slice Position
- Phantom Width (Geometric linearity and distortion)
- Ghosting
- Resolution (Contrast of 1mm insert)

# Usage

Users should make themselves familiar with the [PumpIA user interface](https://principle-five.github.io/pumpia/usage/user_interface.html)

To run the collection:
1. Clone the repository
2. Use an environment manager to install the requirements from `requirements.txt` or install the requirements using the command `pip install -r requirements.txt` when in the repository directory
3. Run the `run_med_acr_rpt_collection.py` script

To use the collection:
1. Load the folder with the relevant images
2. Drag and drop the series containing the ACR images into the left viewer of the `Main` tab
3. Drag and drop the series containing repeat images into the right viewer of the `Main` tab
4. Generate the ROIs and run analysis. If the image has been analysed then the old ROIs may still be visible on the image, it is recommended to regenerate them as in some tests other information is loaded in this process.
5. Correct the context if required (see below)
    - Re-run generating ROIs
6. Move any ROIs as required, this should be done through their relevant modules.
    - Re-run analysis
7. Copy the results in the relevant format. Horizontal is tab separated, vertical is new line separated.

## Correcting Context

The context used for this collection is based on the Auto Phantom Context Manager provided with PumpIA, however it is expanded to find the rotation of the phantom.
It has 3 new options:
- Inserts Slice
- Resolution Insert Side
- Circle Insert Side

The inserts slice is the slice with the resolution inserts in, this is either the first or last slice (1 or 11).

The Resolution Insert Side and Circle Insert Side options must not be on the same axis. i.e. top and bottom or left and right.
The orthogonality of these options allows for the orientation and any flipping to be known.

If manual control is required then it is recommended to set the resolution insert side first as this is usually more obvious, and then set the circle insert side.

To avoid the program resetting any selected values the option `Full Manual Control` must be selected. This does not reset when a new image is loaded.

# Modules
## Subtraction SNR

Calculates SNR based on the subtraction method.
The ROI size is determined from the size input as a percentage of the phantom height and width.
The ROI is always centred on the phantom.
The following corrections can be applied:
- Bandwidth
- Pixel Size (includes slice width)
- Number of Averages
- Number of Phase Encode Steps

A button for showing the subtraction image is included.

## Uniformity

This is calculated using the integral uniformity method.
The size of the ROI is determined in the same way as the SNR module.

There is the option of applying a low pass kernel convolution to the image prior to calculation, this is defaulted to on.
The kernel is defined by

|    |    |    |
|----|----|----|
|1/16|2/16|1/16|
|2/16|4/16|2/16|
|1/16|2/16|1/16|

## Ghosting

This calculate ghosting from a signal ROI in the middle of the phantom and ROIs above, below, left, and right of the phantom.
ROI sizes do not follow the ACR guidance, the size of the signal ROI can be given.

## Slice Width

Slice width is measured by fitting a curve to the profile of the ROIs.

This curve can be selected as either a flat top gaussian given by the following, where P is the rank:

$$A * exp\bigg(-\bigg(\frac{(x-x_0)^2}{2\sigma^2}\bigg)^P\bigg) + offset$$

or a split gaussian given by:

```math
\left\{
\begin{array}{ c l }
A + offset & a \lt x\lt b \\
A * exp \bigg(-\frac{(x-a)^2}{2\sigma^2}\bigg) + offset & x \lt a \\
A * exp \bigg(-\frac{(x-b)^2}{2\sigma^2}\bigg) + offset & b \lt x
\end{array}
\right.
```

The percentage of A that the width is taken at can be provided ny the user, the default is 50%.
Users can also override the $tan$ of the ramp angle, this is not recommended and is defaulted to 0.1 as defined in ACR guidance.

A button is provided to show the profiles of the ROIs used and the fits calculated using the selected method.

## Slice Position

This follows the ACR guidance.
A button is provided to show the profiles of the ROIs used.

## Phantom Width

The phantom width is used to calculate the geometric linearity and distortion of the image.
Users can select any line profiles they don't want included in the calculations (e.g. if there is a large bubble).

## Resolution

The 1mm resolution insert is used.
The contrast for line profiles horizontally and vertically across the holes are calculated using the following method:

1. For each line the contrast is calculated by working out the contrast betwen the gaps betwen the pins and the pins either side of the gap.
2. This gives 3 contrast values for each line (one for each gap between the pins), the worst case is taken as the contrast for the line.
3. The best line verically/horizontally is reported as the contrast result, this is in line with ACR guidance.

An average of the horizontal and vertical contrasts is reported on the main tab.

Contrast is calculated using:

$$Contrast(\\%) = \frac{max-min}{max+min} * 100$$

Users can override the position of the central hole in the surrounding ROI, this is normally calculated by taking the position of the maximum of the surrounding ROI's x and y profiles.
The central hole is the one which is part of both a horizontal and vertical line.

# Calculating The Context

The context for this phantom is calculated as follows (selecting `show boxes` allows some of this working to be seen):
1. A profile of the slice averages is found, the minimum value is the geometric accuracy slice.
2. The boundary of the phantom is found
3. Four boxes are offset horizontally and vertically from the centre and their average value used to find the location of the resolution inserts (opposite the maximum value)
4. Two boxes are drawn between the centre and the corners opposite the resolution inserts. The one with the minimum value is where the circle insert is.
