# -*- coding: utf-8 -*-
"""
Created on Sat May 16 19:45:33 2015

@author: Nicholas Mei (nicholas_mei@brown.edu)

Overview:

The Fly Activity Experiment Manager allows for quantitation of fly motion 
(i.e. the number of flies moving in a given frame) during various experimental 
paradigms. Importantly, this movement quantitation is done in real-time 
(or near real-time).

Features:

1) Can communicate with an arduino to control the onset time, duration, frequency,
and pulse width of LED diodes for optogenetic experiments.

2) Can directly write out 'raw' (corrected for camera lens barrel distortions)
collected video during an experiment to '.avi' format for subsequent analysis 
with other more sophisticated tracking software packages (i.e. C-Trax, Jabba, etc...).

3) Will eventually be able to produce real time activity plots of the activity
for 4 differents ROIs as well as two 'line crossing beams'.

Required software:

1) Python 2.7+ (Anaconda distribution is highly highly recommended: https://store.continuum.io/cshop/anaconda/)
2) OpenCV with python bindings RC 3.0+ (http://opencv.org/downloads.html)
3) FFMPEG 64-bit Zeranoe build (http://ffmpeg.zeranoe.com/builds/, see also: http://www.wikihow.com/Install-FFmpeg-on-Windows)
4) Needs a camera calibration file (see the Cam_calibration.py file for details)

Setup particulars:
1) Flies need to be IR backlit and cameras must have an IR filter fitted for tracking
and all components of the experimental setup to work properly.
2) Arduino's need to be loaded with the 'Opto-blink' sketch

Required Computer hardware:

Minimum (untested so I'm not 100% sure this would actually work):
2-core processor is needed (performance will probably be terrible though)
8-16 GB RAM
USB camera that is supported by OpenCV
Arduino (Uno: http://store.arduino.cc/product/A000066)

Recommended:
4+ core processor with a high clock rate
16-32 GB RAM
High quality USB camera that supports at least 30 fps that is supported by OpenCV
Arduino (Uno: http://store.arduino.cc/product/A000066)

"""
import sys
import time
import serial
import json
import timeit

import numpy as np
import matplotlib.pyplot as plt
import multiprocessing as mp
import subprocess as sp

from itertools import chain

import ROI
import cv2

#Note to self: Using interactive interpreter elements works horribly with multiprocessing...
#Ipython functionality to disable inline matplotlib plots
#from IPython import get_ipython
#ipython = get_ipython()
#ipython.magic("matplotlib qt")

#Location of your ffmpeg.exe file in order to write video out
FFMPEG_BIN = u'C:/FFMPEG/bin/ffmpeg.exe'

def correct_distortion(input_frame, calib_mtx, calib_dist):
    """
    Function that applies correction for radial "fisheye" lens distortion
    make sure you've already loaded the relevant calibration correction matrices
    with the 'read_cam_calibration_file()' function at some point...
    """
    h, w = input_frame.shape[:2]        
    #apply undistortion
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(calib_mtx,calib_dist,(w,h),1,(w,h))
    corrected_frame = cv2.undistort(input_frame, calib_mtx, calib_dist, None, newcameramtx)         
    return corrected_frame

def control_expt(child_conn_obj, data_q_obj, expt_dur, led_freq, led_dur, 
                 optostim_on_time, optostim_dur, calib_mtx, calib_dist,
                 write_video, frame_height, frame_width, fps_cap):
    """
    This function contains the camera read() loop, controls
    the timing/freq/duration for when the arduino turns on and off the 
    LED stimulation, and also contains the ffmpeg video writer that writes out
    the raw video in real-time.
    
    Because a fast camera loop is better, we start this function as 
    its own process using multiprocessing (mp) see the experiment class for the
    initialization.
    
    #experiment relevant options
    expt_dur: duration of the entire experiment (in seconds)
    led_freq: frequency of LED flashes (Hz)
    led_dur: amount of time LED is on for during flash (time in ms).
             Note: also often called LED 'pulse width'
    optostim_on_time: at what time during expt to turn on the LEDs? (in seconds)
    optostim_dur: how long should the led stimulation happen? (in seconds)
    
    #video writer options
    write_video: whether or not to write libx264 .avi file
    frame_height: height in pixels of the video to be written
    frame_width: width in pixels of the video to be written
    
    #other
    fps_cap: specify a maximum framerate cap to capture at
    """    
    def run_once(f):
        def wrapper(*args, **kwargs):
            if not wrapper.has_run:
                wrapper.has_run = True
                return f(*args, **kwargs)
        wrapper.has_run = False
        return wrapper
    
    @run_once
    def turn_on_stim(led_freq, led_dur):
        arduino.write('{freq},{dur}'.format(freq=led_freq, dur=led_dur))
    
    @run_once
    def turn_off_stim():
        arduino.write('0,0')
        
    def elapsed_time(start_time):
        return time.clock()-start_time  
    
    #Initialize the arduino!
    #Doing it this way prevents the serial reset that occurs!
    arduino = serial.Serial()
    arduino.port = 'COM4'
    arduino.baudrate = 9600
    arduino.timeout = 0.1
    arduino.setDTR(False)
    arduino.open()  
    time.sleep(1)    
    
    #communicate with arduino with: arduino.write('x,y') 
    #where 'x' is desired frequency in Hz and 'y' is desired LED on time in ms
    #immediately write 0 hz and 0 on_time to prevent flashing
    arduino.write('0,0')    

    if write_video is True:          
        #Need to still figure what I want the name of the video will be...                     
        #base_fname = os.path.dirname(self.video_loc)   
        base_fname = u'C:/Users/Nicholas/Desktop/Python Scripts'
            
        ffmpeg_command = [ FFMPEG_BIN,
                          '-f', 'rawvideo',
                          '-pix_fmt', 'bgr24',
                          '-s', '{}x{}'.format(frame_width,frame_height), # size of one frame
                          '-r', '{}'.format(fps_cap), # frames per second
                          '-i', '-', # The imput comes from a pipe
                          '-an', # Tells FFMPEG not to expect any audio
                          '-vcodec', 'libx264',
                          base_fname + "/raw_video.avi"]
                                   
        #Note to self, don't try to redirect stout or sterr to sp.PIPE as filling the pipe up will cause subprocess to hang really bad :(
        video_writer = sp.Popen(ffmpeg_command, stdin=sp.PIPE)    
    
    #Wait for the start signal from the parent process to begin grabbing frames
    while True:
        msg = child_conn_obj.recv()
        
        if msg == 'Start!':
            break 
        
    #initilize the video capture object
    cam  = cv2.VideoCapture(cv2.CAP_DSHOW + 0) 
    #We don't want the camera to try to autogain as it messes up the image
    cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.0)
    cam.set(cv2.CAP_PROP_GAIN, 0.0)
    #Give some time for the capture settings to 'sink' in
    time.sleep(3)
        
    #start the clock!!
    expt_start_time = time.clock() 
    fps_cap_timer = time.clock()
    stim_bool = False
    
    #camera read and experiment control loop
    while True:
        
        #enforce an FPS cap such that camera read speed cannot be faster than the cap
        if elapsed_time(fps_cap_timer) >= 1/float(fps_cap):   
            fps_cap_timer = time.clock()
            
            ret, raw_frame = cam.read()     
            frame = correct_distortion(raw_frame, calib_mtx, calib_dist)
            
            if write_video is True:
                video_writer.stdin.write(frame.tostring())
            
            # Use the multiprocessing Queue to send a timestamp, video frame,
            # and indicator of whether optostim is occurring during frame
            # to the post-processing and analysis portion of script             
            data_q_obj.put_nowait((elapsed_time(expt_start_time), frame, stim_bool))
            
            if elapsed_time(expt_start_time) >= optostim_on_time + optostim_dur:
                turn_off_stim()
                stim_bool = False
            elif elapsed_time(expt_start_time) >= optostim_on_time:
                turn_on_stim(led_freq, led_dur)
                stim_bool = True
                
            if elapsed_time(expt_start_time) >= expt_dur:
                data_q_obj.put_nowait((elapsed_time(expt_start_time),'stop', stim_bool))
                child_conn_obj.close()
                data_q_obj.close()
                arduino.close()            
                if write_video is True:
                    video_writer.stdin.close()
                    video_writer.wait()
                break

class experiment(object):
    def __init__(self, calib_loc="Camera_ELP_calibration_matrices.json", 
                 set_rois = False, debug=False, write_video=False, 
                 line_mode ='vertical', expt_dur = 60, led_freq = 5, led_dur=5,
                 optostim_on_time=60, optostim_dur = 60, fps_cap = None):
        
        self.debug = debug
        self.write_video = write_video
        self.calib_loc = calib_loc
        self.set_rois = set_rois
        
        #actual experiment settings        
        self.expt_dur = expt_dur
        self.led_freq = led_freq
        self.led_dur = led_dur
        self.optostim_on_time = optostim_on_time
        self.optostim_dur = optostim_dur   
                                            
        #load in and read webcam calibration files        
        calib_data = self.read_cam_calibration_file(self.calib_loc)
        self.calib_mtx = calib_data["camera_matrix"]
        self.calib_dist = calib_data["dist_coeff"]
        
        if fps_cap is None:        
            #Need to figure out what the effective fps of the camera is...
            #We'll use the python timeit module to achieve this
            fps_timer = timeit.Timer('[webcam.read() for x in range(30)]', 
                                     'import cv2\nwebcam=cv2.VideoCapture(cv2.CAP_DSHOW + 0)\n')        
            #time how long it takes to read 30 frames 10 times in a row
            self.fps = (5*30)/fps_timer.timeit(5)        
        else:
            self.fps = fps_cap
        
        #start webcam video capture instance. Use directshow instead of VFW
        sample_cam  = cv2.VideoCapture(cv2.CAP_DSHOW + 0)  
        #Prevent camera from doing auto-gain
        sample_cam.set(cv2.CAP_PROP_GAIN, 0.0)                    
        #grab frame of video from the webcam
        _, self.sample_frame = sample_cam.read()
        self.sample_frame = correct_distortion(self.sample_frame, self.calib_mtx, self.calib_dist)
        sample_cam.release()
        
        #Need to figure out what the dimensions of the output frames will be
        self.frame_height, self.frame_width = self.sample_frame.shape[:2]
        
        #Initialize the multiprocess communication pipe/queue and start the process
        self.parent_conn, self.child_conn = mp.Pipe()
        self.data_q = mp.Queue()      
        
        proc_args = (self.child_conn, self.data_q,
                     self.expt_dur, self.led_freq, 
                     self.led_dur, self.optostim_on_time, 
                     self.optostim_dur, self.calib_mtx, self.calib_dist, 
                     self.write_video, self.frame_height, 
                     self.frame_width, self.fps)                 
        self.control_expt_process = mp.Process(target=control_expt, args=proc_args)                                    
        #start the control_expt process!
        self.control_expt_process.start()
        
        if set_rois is True:

            self.roi_list = [('blue', 'line1'), ('red', 'line2'),
                             ('blue', 'roi1'), ('red', 'roi2'), 
                             ('green', 'roi3'), ('purple', 'roi4')]
                             
            for roi_color, roi_name in self.roi_list:                
                if 'roi' in roi_name:
                    setattr(self, roi_name, ROI.set_roi(roi_color, background_img = self.sample_frame))
                elif 'line' in roi_name:
                    setattr(self, roi_name, ROI.set_line(roi_color, background_img = self.sample_frame, line_width=5, line_mode = line_mode))
                    
                self.wait_for_roi(getattr(self, roi_name))
                 
            self.roi_dict = {roi_name:getattr(getattr(self, roi_name), 'roi') for roi_color, roi_name in self.roi_list}
            self.save_rois()
            
            #normalize the roi_list to what you would encounter when loading
            self.roi_list = [element[1] for element in self.roi_list] 
            
        else:
            self.load_rois("FlyActivityCounter_ROIs.json")
            
    def read_cam_calibration_file(self, filepath):
        """
        Function to read in a camera calibration file which contains the 
        reprojection error, camera_matrix, and distance_coefficient produced by
        the cv2.calibrateCamera() function
        """
        with open(filepath, 'r') as data_file:
            data = json.load(data_file)
            
        processed_data = {}
        if data:
            processed_data = {"reprojection_error": data["reprojection_error"], 
                              "camera_matrix": np.array(data["camera_matrix"]),
                              "dist_coeff": np.array(data["dist_coeff"])}
                              
        return processed_data                                            
        
    def save_rois(self):        
        data = {roi_name: zip(*self.roi_dict[roi_name]) for roi_color, roi_name in self.roi_list}        
            
        fname = "FlyActivityCounter_ROIs.json"
    
        #defaults to saving to same directory as where the script is located    
        with open(fname, "w") as f:
            json.dump(data, f)
    
    def load_rois(self, filepath):
        with open(filepath, 'r') as data_file:
            data = json.load(data_file)
            
            #regenerate the roi names that exist in the data_file
            self.roi_list = [str(roi_key) for roi_key in data.keys()]
            self.roi_list.sort()
            
            #regenerate the roi dictionary that allows lookup of roi coordinates
            self.roi_dict = {roi_name:tuple([np.array(element) for element in data[roi_name]]) for roi_name in self.roi_list}            
        
    def wait_for_roi(self, roi_instance):
        """
        Function that allows script to wait for user to set ROI
        """
        while True:
            plt.pause(0.000001)
            if roi_instance.roi_finalized is True:
                print "ROI is finalized"
                sys.stdout.flush()
                break
            
    def get_activity_counts(self, (roi_name, fgmask, current_frame, roi_coords)):
        # Some kernels to do morphology operations with
        kernel1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
        kernel2 = np.ones((3,3),np.uint8)   
        
        #Just crop out the ROIs instead of masking...
        rect = list(chain(*roi_coords))        
        #Image cropping works by img[y: y + h, x: x + w]
        cropped_fgmask = fgmask[rect[2]:rect[3], rect[0]:rect[1]] 
        cropped_current_frame = current_frame[rect[2]:rect[3], rect[0]:rect[1]]
            
        # Apply a medianblur filter and then morphological dilate to 
        # remove noise and consolidate detections        
        filtered = cv2.medianBlur(cropped_fgmask,7)             
        dilate = cv2.morphologyEx(filtered, cv2.MORPH_DILATE, kernel1)
            
        image, contours, hierarchy = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)      
        cv2.drawContours(cropped_current_frame, contours, -1, (255,0,0), 2)    
        
        return((len(contours), cropped_current_frame)) 
    
    def start_expt(self):
        self.parent_conn.send('Start!')      
        #give a second for the child process to get started
        time.sleep(1)
        
        # Implement a K-Nearest Neighbors background subtraction
        # Most efficient when number of foreground pixels is low
        self.bg = cv2.createBackgroundSubtractorKNN(5, 300, False)      
        
        prev_time_stamp = 0        
        self.max_q_size = 0
                               
        while True:            
            time_stamp, frame, stim_bool = self.data_q.get()
            
            #check if the experiment data collection has completed
            if frame == 'stop':
                #let's close everything down
                cv2.destroyAllWindows()
                #clean up the expt control process
                self.data_q.close()
                self.data_q.join_thread()
                self.child_conn.close()
                self.parent_conn.close()
                self.control_expt_process.terminate()
                break
            
            elif type(frame) is np.ndarray:
                
                print (time_stamp, stim_bool)            
                fps = 1/(time_stamp-prev_time_stamp)
                prev_time_stamp = time_stamp           
                print (int(self.data_q.qsize()),fps)
                sys.stdout.flush()
                
                if int(self.data_q.qsize() > self.max_q_size):
                    self.max_q_size = self.data_q.qsize()
                
                #Apply the background subtractor to the current frame of the video
                self.fgmask = self.bg.apply(frame)    
                
                results = [self.get_activity_counts((roi_name, self.fgmask, frame, self.roi_dict[roi_name])) for roi_name in self.roi_list]
                
                roi_counts, roi_frames = zip(*results)
                
                #cv2.imshow('mask', fgmask)
                for indx, proc_frame in enumerate(roi_frames):                
                    cv2.imshow('{}'.format(self.roi_list[indx]), proc_frame) 
                cv2.waitKey(5)
                

if __name__ == '__main__':     
    
    #fps cap of 20 will result in stable performance
    #higher fps cap (up to 30) is possible but will incur a linearly increasing
    #(with time) system memory cost.

    # example call where the following occurs:
    # experimental setup, 5 second delay, and then subsequent start of expt
    x = experiment(write_video=False, set_rois=False, expt_dur = 60, led_freq = 60, led_dur=5, optostim_on_time=5, optostim_dur = 35, fps_cap=20)
    time.sleep(5)
    x.start_expt()
    pass