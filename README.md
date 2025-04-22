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
4. Generate the ROIs and run analysis
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

# Calculating The Context

The context for this phantom is calculated as follows (selecting `show boxes` allows some of this working to be seen):
1. A profile of the slice averages is found, the minimum value is the geometric accuracy slice.
2. The boundary of the phantom is found
3. Four boxes are offset horizontally and vertically from the centre and their average value used to find the location of the resolution inserts (opposite the maximum value)
4. Two boxes are drawn between the centre and the corners opposite the resolution inserts. The one with the minimum value is where the circle insert is.
