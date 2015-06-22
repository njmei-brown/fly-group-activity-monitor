fly-activity-assay
====================
Set of functions and scripts to do real time fly activity quantitation with the added option to control optogenetic stimulation

Overview:
---------

The Fly Activity Assay allows for quantitation of fly motion 
(i.e. the number of flies moving in a given frame) during various experimental 
paradigms. Importantly, this movement quantitation is done in real-time 
(or near real-time).

Features:
---------

1. Can communicate with an arduino to control the onset time, duration, frequency,
and pulse width of LED diodes for optogenetic experiments.

2. Can directly write out 'raw' (corrected for camera lens barrel distortions)
collected video during an experiment to '.avi' format for subsequent analysis 
with other more sophisticated tracking software packages (i.e. C-Trax, Jabba, etc...).

3. Can produce real time activity plots for 4 differents ROIs.

Required software:
------------------

1. Python 2.7+ (Anaconda distribution is highly highly recommended: https://store.continuum.io/cshop/anaconda/)

2. OpenCV with python bindings RC 3.0+ (http://opencv.org/downloads.html)

3. FFMPEG 64-bit Zeranoe build (http://ffmpeg.zeranoe.com/builds/, see also: http://www.wikihow.com/Install-FFmpeg-on-Windows)

4. Needs a camera calibration file (see the Cam_calibration.py file for details)

Setup particulars:
------------------

1. Flies need to be IR backlit and cameras must have an IR filter fitted for tracking
and all components of the experimental setup to work properly.

2. Arduino's need to be loaded with the 'Opto-blink' sketch

Required Computer hardware:
---------------------------

**Minimum (untested but should work in theory...):**

* 2-core processor is needed (higher clock rate is better)

* 8-16 GB RAM

* USB camera that is supported by OpenCV

* Arduino (Uno: http://store.arduino.cc/product/A000066)

**Recommended:**

* 4-core processor (higher clock rate is better) - will ensure fast FFMPEG encoding

* 16-32 GB RAM

* High quality USB camera that supports at least 30 fps that is supported by OpenCV

* Arduino (Uno: http://store.arduino.cc/product/A000066)
