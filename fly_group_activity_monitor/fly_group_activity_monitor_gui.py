#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 05 23:08:12 2015

The MIT License (MIT)

Copyright (C) 2015 Nicholas Mei <nicholas_mei@brown.edu>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
import os
import time
from functools import partial
import multiprocessing as mp
import numpy as np
import cv2
import json

#If we are using python 2.7 or under
if sys.version_info[0] < 3:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
      
#If we are using python 3.0 or above
elif sys.version_info[0] > 3:
    import tkinter as tk
    import tkinter.filedialog as filedialog
    import tkinter.messagebox as messagebox
    
import fly_activity_experiment_manager as fly_expt_man
import roi

#getting multiprocess to work with class methods is too much of a pain
#so we define the run_expt and preview_camera function outside of the class
#see: http://stackoverflow.com/questions/8804830/python-multiprocessing-pickling-error
def run_expt(expt_conn, write_video, write_csv, use_arduino, expt_dur, 
             led_freq, led_dur, stim_on_time, stim_dur, fps_cap, roi_list, 
             roi_dict, gui_cam_calib_data, default_save_dir):
    
    expt = fly_expt_man.experiment(expt_conn, write_video, write_csv, 
                                   use_arduino, expt_dur, led_freq, led_dur,
                                   stim_on_time, stim_dur, fps_cap, roi_list, 
                                   roi_dict, gui_cam_calib_data, default_save_dir)
    
    expt.start_expt()
    
def correct_distortion(raw_frame, calibration_data):
    mtx = calibration_data["camera_matrix"]
    dist = calibration_data["dist_coeff"]          
    h,  w = raw_frame.shape[:2]           
    #apply undistortion
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx,dist,(w,h),1,(w,h))
    unwarped = cv2.undistort(raw_frame, mtx, dist, None, newcameramtx)         
    # crop the image
    #x,y,w,h = roi
    #unwarped = unwarped[y:y+h, x:x+w]    
    return unwarped

def preview_camera(calibration_data = None):   
    cam = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cam.read()
        if ret:                    
            if calibration_data:            
                unwarped = correct_distortion(frame, calibration_data)           
                #image comparisons
                cv2.imshow('Calibrated camera preview: press "Esc" to close',unwarped) 
            else:
                cv2.imshow('Camera preview: press "Esc" to close', frame)
            key = cv2.waitKey(30) & 0xff
            if key == 27:
                break
        else:
            print("Could not find a valid camera! Try checking camera!")
            break
    cam.release()
    cv2.destroyAllWindows()
    
def calibrate_camera(perform_save, num_samples = 100):
    """
    This function does live collection of chessboard calibration points and takes
    a specified number of calibration samples. It calculates the appropriate transformation
    matrices then saves them into a JSON file for easy loading later.
    
    Adapted using examples from:
    http://docs.opencv.org/3.0-beta/doc/py_tutorials/py_calib3d/py_calibration/py_calibration.html
    http://www.janeriksolem.net/2014/05/how-to-calibrate-camera-with-opencv-and.html   
    """
    # termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)   
    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((6*6,3), np.float32)
    objp[:,:2] = np.mgrid[0:6,0:6].T.reshape(-1,2)    
    # Arrays to store object points and image points from all the images.
    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane.      
    cam = cv2.VideoCapture(0)
    
    while True:
        _, img = cam.read()        
        cv2.imshow('image', img)
        cv2.waitKey(500)                    
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)    
        # Find the chess board internal corners
        found_corners, corners = cv2.findChessboardCorners(gray, (6,6), cv2.CALIB_CB_FAST_CHECK)    
        # If found, add object points, image points (after refining them)
        if found_corners:
            objpoints.append(objp)  
            refined_corners = cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)
            imgpoints.append(refined_corners)   
            # Draw and display the corners
            cv2.drawChessboardCorners(img, (6,6), refined_corners, found_corners)
            cv2.imshow('Chessboard Corners Found!',img)
            k = cv2.waitKey(30) & 0xff         
            print("{} number of calibration points collected so far!".format(len(imgpoints)))
            if len(imgpoints) > num_samples or k==27:
                break            
    cam.release()
    cv2.destroyAllWindows()    
    #Creating Calibration matrices
    print("Calculating calibration matrix, this may take a while!")
    rms, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1],None,None)
      
    print("RMS:", rms)
    print("camera matrix:\n", mtx)
    print("distortion coefficients: ", dist.ravel())
 
    #Re-projection error:
    def calc_reprojection_error(objpoints, imgpoints, mtx, dist):
        tot_error = 0
        for i in xrange(len(objpoints)):
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
            error = cv2.norm(imgpoints[i],imgpoints2, cv2.NORM_L2)/len(imgpoints2)
            tot_error += error
        
        print("mean error: ", tot_error/len(objpoints))
    
    print("Reprojection mean error is: ", calc_reprojection_error(objpoints, imgpoints, mtx, dist))
    #=============================================================================
    #Saving camera calibration matrices:
        
    #reprojection_error = ret
    #camera_matrix = mtx
    #dist_coeff = dist
    #rotation_vecs = rvecs
    #translation_vecs = tvecs
    
    data = {"reprojection_error": rms, 
            "camera_matrix": mtx.tolist(),
            "dist_coeff": dist.tolist()}
    
    if perform_save:
        fname = "Camera_calibration_matrices.json"
        
        with open(fname, "w") as f:
            json.dump(data, f)        
        
    calibration_data = {"reprojection_error": data["reprojection_error"], 
                        "camera_matrix": np.array(data["camera_matrix"]),
                        "dist_coeff": np.array(data["dist_coeff"])}
                        
    return calibration_data

class create_tool_tip(object):
    '''
    Create a tool tip for a given widget
    '''
    def __init__(self, widget, ttip_text='widget description'):
        self.widget = widget
        self.ttip_text = ttip_text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
    def enter(self, event=None):
        x, y = (0,0)
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.ttip_text, padx=5,
                       background='#FFFFB2', relief='solid', borderwidth=1,
                       font=("ariel", "10", "normal"))
        label.pack()
    def close(self, event=None):
        if self.tw:
            self.tw.destroy()

class Application(tk.Frame):
    
    #============ Vars and intialization ===============
    def define_variables(self):
        self.expt_dur = tk.StringVar()
        self.stim_on_time = tk.StringVar()
        self.stim_dur = tk.StringVar()
    
        self.use_arduino = tk.IntVar()    
        self.led_freq = tk.StringVar()
        self.led_dur = tk.StringVar()
        
        self.write_vid = tk.IntVar()
        self.write_csv = tk.IntVar()
        self.fps_cap = tk.StringVar()
    
        self.expt_dur.set("300")
        self.stim_on_time.set("120")
        self.stim_dur.set("60")
        
        self.use_arduino.set("1")
        self.led_freq.set("5")
        self.led_dur.set("5")
        
        self.write_vid.set("1")
        self.write_csv.set("1")
        self.fps_cap.set("30")
        
        self.expt_running = None
    
    def dir_list_init(self, dir_list):
        if sys.platform == 'win32' or sys.platform == "darwin":
            desktop_path = os.path.abspath(os.path.expanduser("~/Desktop/"))
            
            if dir_list.size() > 0:
                dir_list.delete(0,tk.END)
            dir_list.insert(0, desktop_path)
    
    #============ work horse functions =================
    def choose_dir(self, root):
        dir_path = filedialog.askdirectory(parent=root, title='Select the directory where you wish to activity assay data to:', mustexist=True)
        return dir_path
        
    def choose_file(self, root, text):
        file_path = filedialog.askopenfilename(parent=root, title=text)
        return file_path
        
    def get_preview_img(self):
        cam = cv2.VideoCapture(0)       
        preview_img = None
        for x in range(30):
            ret, preview_img = cam.read()        
        cam.release()
        
        return preview_img
        
    def save_rois(self):     
        data = {roi_name: [list(coord) for coord in self.roi_dict[roi_name]] for roi_name in self.roi_list}                   
        fname = "FlyActivityAssay_ROIs.json"   

        if os.path.exists(fname):
            print("Previously saved ROI.json file found, overwriting it!")
            sys.stdout.flush()
            os.remove(fname)
        
        #defaults to saving to same directory as where the script is located    
        with open(fname, "w") as f:
            json.dump(data, f)
            
        print('ROI.json file was successfully saved at:\n"{}"'.format(os.path.join(os.getcwd(), fname)))
        sys.stdout.flush()
    
    def load_rois(self, root, text):
        filepath = self.choose_file(root, text)        
        
        if os.path.exists(filepath):
            filename, file_extens = os.path.splitext(filepath)                        
            if file_extens == ".json":          
                with open(filepath, 'r') as data_file:
                    data = json.load(data_file)                       
                    try:
                        #regenerate the roi names that exist in the data_file
                        self.roi_list = sorted([str(roi_key) for roi_key in data.keys()])            
                        #regenerate the roi dictionary that allows lookup of roi coordinates
                        self.roi_dict = {roi_name:tuple([np.array(element) for element in data[roi_name]]) for roi_name in self.roi_list}
                        print("ROI.json file was successfully loaded!")
                        sys.stdout.flush()
                    except:
                        print("It looks like you accidentally selected a camera calibration file! Try again!")
                        sys.stdout.flush()
            else:
                print("It looks like you didn't select a valid saved ROI file!")
                sys.stdout.flush()
        else:
            print("Loading ROI failed! Check if the file exists at: {}".format(filepath))
            sys.stdout.flush()
            
    def load_cam_calib_file(self, root, filepath=None):
        """
        Function to read in a camera calibration file which contains the 
        reprojection error, camera_matrix, and distance_coefficient produced by
        the cv2.calibrateCamera() function
        """
        if not filepath:
            filepath = self.choose_file(root, "Please choose the camera calibration file you wish to load!")

        if os.path.exists(filepath):
            filename, file_extens = os.path.splitext(filepath)                        
            if file_extens == ".json":          
                with open(filepath, 'r') as data_file:
                    data = json.load(data_file)                
                if data:
                    try:
                        self.calibration_data = {"reprojection_error": data["reprojection_error"], 
                                                 "camera_matrix": np.array(data["camera_matrix"]),
                                                 "dist_coeff": np.array(data["dist_coeff"])}                                          
                        print("Camera calibration .json file was successfully loaded!")
                        sys.stdout.flush()
                    except:
                        print("It looks like you might have accidentally selected an ROI save file! Try again!")
                        sys.stdout.flush()
            else:
                print("It looks like you didn't select a valid camera calibration file!")
                sys.stdout.flush()
        else:
            print("Loading camera calibration file failed! Check if the file exists at: {}".format(filepath))
            sys.stdout.flush()
        
    #================= Handler functions ========================
    def handle_arduino_toggle(self, led_freq_entry, led_freq_label, led_dur_entry, led_dur_label, use_arduino):
        arduino_state = use_arduino.get()
        if arduino_state == 1:
            led_freq_label.pack()
            led_freq_entry.pack()
            led_dur_label.pack()
            led_dur_entry.pack()
        else:
            led_freq_entry.pack_forget()
            led_freq_label.pack_forget()
            led_dur_entry.pack_forget()
            led_dur_label.pack_forget()
    
    def handle_calibrate_camera(self, root):
        camera_calib_msg = ( "Please move a 7x7 chessboard grid "
                             "(6x6 internal corners) in front of the camera " 
                             "taking care to tilt and rotate the grid until " 
                             "enough points for calibration have been collected. "
                             "\n\nThen, please be extremely patient as calculating " 
                             "the undistortion matrix can take a while " 
                             "(up to 10 minutes or more if you have a slow computer)"
                             "\n\nAlso, please don't interact with the main GUI while "
                             "performing the calibration, if you do, things will break :(")
                              
        messagebox.showinfo(parent = root, title="Camera calibration information!", message=camera_calib_msg)
              
        question=( "Do you want to save the resulting calibration to file? "
                   "If you don't want to calibrate the camera anymore press 'cancel'")     
        
        perform_save = messagebox.askyesnocancel(title="Camera calibration question!", message=question)
        
        if perform_save == True or perform_save == False:        
            self.calibration_data = calibrate_camera(perform_save = perform_save)
        elif perform_save == None:
            print("You cancelled performing the camera calibration")
            
    def handle_preview_camera(self, calibration_data = None):
        if calibration_data == None:
            if hasattr(self, 'calibration_data'):
                calibration_data = self.calibration_data
        cam_preview_proc = mp.Process(target=preview_camera, args=(calibration_data,))   
        cam_preview_proc.start()
        
    def handle_view_calib_details(self, root):
        if hasattr(self, 'calibration_data'):
            camera_calib_details = "The reprojection error of the current calibration file is:\n\n{}\n\nSmaller values are better!".format(self.calibration_data['reprojection_error'])
            messagebox.showinfo(parent = root, title="Camera calibration information!", message=camera_calib_details)
        else:
            print("You haven't calibrated or loaded a camera calibration file yet!")
            sys.stdout.flush()
        
    def handle_preview_camcalib(self):
        #check if there has been a camera_calibration_datafile loaded
        if hasattr(self, 'calibration_data'):   
            self.handle_preview_camera(calibration_data = self.calibration_data)
        else:
            print("You haven't calibrated or loaded a camera calibration file yet!")
            sys.stdout.flush()
    
    def handle_dir_choose(self, root, dir_list):       
        dir_path = self.choose_dir(root)
        
        if dir_list.size() > 0:
            dir_list.delete(0,tk.END)
        dir_list.insert(0, dir_path)   
    
    def handle_set_rois(self, save_roi_btn):
        #Hardcoded 4 ROIs, perhaps in the future user will be able to add
        #a customized number of them...
        roi_list = [('blue', 'roi1'), ('red', 'roi2'), 
                    ('green', 'roi3'), ('purple', 'roi4')]
                    
        preview_img = self.get_preview_img()
        
        if hasattr(self, 'calibration_data'):
            preview_img = correct_distortion(preview_img, self.calibration_data)
                    
        for roi_color, roi_name in roi_list:
            setattr(self, roi_name, roi.set_roi(roi_color, preview_img))
            getattr(self, roi_name).wait_for_roi()     
            
        self.roi_dict = {roi_name:getattr(getattr(self, roi_name), 'roi') for roi_color, roi_name in roi_list}
        
        #normalize the roi_list to what you would encounter when loading
        self.roi_list = [element[1] for element in roi_list] 
                
        save_roi_btn.pack(side=tk.LEFT, fill=tk.X,expand=1, pady=15)
        
    def handle_run(self, dir_list):
        
        if hasattr(self, "expt_proc"):
            if not app.expt_proc.is_alive():
                #clean up previous experiment pipes
                self.gui_conn.close()
                self.expt_conn.close()
                self.expt_running = False
            else:
                print("You are still running an experiment! Use the 'Stop current experiment' to quit the current one and try again!")
                sys.stdout.flush()
        
        if self.expt_running == False or self.expt_running == None:                   
            default_save_dir = dir_list.get(0)    
            #check that we have: 1) roi_list 2) roi_dict 3) cam_calibration_file
            if hasattr(self, 'roi_list') and hasattr(self, 'roi_dict'):
                if hasattr(self, 'calibration_data'):
                    
                    self.gui_conn, self.expt_conn = mp.Pipe()                    
                    expt_args = (self.expt_conn, bool(self.write_vid.get()), 
                                 bool(self.write_csv.get()), bool(self.use_arduino.get()),
                                 float(self.expt_dur.get()), float(self.led_freq.get()), 
                                 float(self.led_dur.get()), float(self.stim_on_time.get()),
                                 float(self.stim_dur.get()), float(self.fps_cap.get()), 
                                 self.roi_list, self.roi_dict, 
                                 self.calibration_data, default_save_dir)                                
                    self.expt_proc = mp.Process(target=run_expt, args=expt_args)   
                    self.expt_proc.start()
                    self.expt_running = True                                    
                else:
                    print("The activity assay gui tried to load the camera calibration automatically but could not find the file! Please load one using the load calibration function in the menu!")
                    sys.stdout.flush()
            else:
                print("You haven't set or loaded ROIs yet!!")
                sys.stdout.flush()
            
    def handle_emergency_stop(self):
        self.gui_conn.send('Shutdown!')
        time.sleep(1)
        self.expt_conn.close()
        self.gui_conn.close()
        self.expt_proc.terminate()
    
    #================= GUI widgets ========================
    def create_widgets(self):
        #------------------- Top Menu Bar ------------------------------    
        menubar = tk.Menu(self.master)
        
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Exit", command=self.master.destroy)    
        menubar.add_cascade(label="File", menu=filemenu)
        
        camcalib_menu = tk.Menu(menubar, tearoff=0)
        camcalib_menu.add_command(label="Calibrate camera", 
                                  command=partial(self.handle_calibrate_camera, self.master))
        camcalib_menu.add_command(label="Load previous calibration file", 
                                  command=partial(self.load_cam_calib_file, self.master))
        camcalib_menu.add_command(label="View current calibration details", 
                                  command=partial(self.handle_view_calib_details, self.master))
        camcalib_menu.add_command(label="Preview camera calibration", 
                                  command=self.handle_preview_camcalib)
        menubar.add_cascade(label="Camera calibration options", menu=camcalib_menu)
        
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=None)
        menubar.add_cascade(label="Help", menu=helpmenu)
        
        self.master.config(menu=menubar)
        
        #---------------------- Top Frame -----------------------------
        top_frame = tk.Frame(self.master, padx=30, borderwidth=1, 
                             relief=tk.SUNKEN)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=5)
        
        #+++++++++++++++++++++++ Expt Duration +++++++++++++++++++++++++
        expt_dur_frame = tk.Frame(top_frame)
        expt_dur_frame.pack(side=tk.LEFT, fill=tk.X, pady=15)
        
        expt_dur_label  = tk.Label(expt_dur_frame, text="Experiment duration\nin seconds:")
        expt_dur_entry = tk.Entry(expt_dur_frame, textvariable=self.expt_dur, justify=tk.CENTER)
        
        expt_dur_label.pack(side=tk.TOP)
        expt_dur_entry.pack(side=tk.TOP)
        
        #+++++++++++++++++++++++ Stim on time ++++++++++++++++++++++++++
        stim_on_frame = tk.Frame(top_frame)
        stim_on_frame.pack(side=tk.LEFT, fill=tk.X, pady=15, padx=30)
        
        stim_on_label = tk.Label(stim_on_frame, text="Time until stimulus\n onset in seconds:")
        stim_on_entry  = tk.Entry(stim_on_frame, textvariable=self.stim_on_time, justify=tk.CENTER)
        
        stim_on_label.pack(side=tk.TOP)
        stim_on_entry.pack(side=tk.TOP)
        
        #+++++++++++++++++++++++ Stim duration +++++++++++++++++++++++++
        stim_dur_frame = tk.Frame(top_frame)
        stim_dur_frame.pack(side=tk.RIGHT, fil=tk.X, pady=15)
        
        stim_dur_label = tk.Label(stim_dur_frame, 
                                  text = "Stimulus duration\n in seconds:")
        stim_dur_entry = tk.Entry(stim_dur_frame, textvariable=self.stim_dur, 
                                  justify=tk.CENTER)
        
        stim_dur_label.pack(side=tk.TOP)
        stim_dur_entry.pack(side=tk.TOP)
        
        #--------------------- Arduino settings frame ------------------           
        arduino_frame = tk.Frame(self.master, padx=30)
        arduino_frame.pack(side=tk.TOP, fill= tk.X, padx=15)
            
            #++++++++++++++++++++++++ LED freq ++++++++++++++++++++++++++++
        led_freq_frame = tk.Frame(arduino_frame)
    
        led_freq_label = tk.Label(led_freq_frame, 
                                  text="Opto stim\nfrequency in Hz:")
        led_freq_entry = tk.Entry(led_freq_frame, textvariable=self.led_freq, 
                                  justify=tk.CENTER)    
        
            #++++++++++++++++++++++++ LED duration ++++++++++++++++++++++++++++
        led_dur_frame = tk.Frame(arduino_frame)
    
        led_dur_label = tk.Label(led_dur_frame, 
                                 text="Opto stim\npulse width in ms:")
        led_dur_entry = tk.Entry(led_dur_frame, textvariable=self.led_dur, 
                                 justify=tk.CENTER)
        led_dur_tooltip_txt = "Specify the amount of time the LED is on for a given frequency.\n***BEWARE!*** Setting too high a pulse width may prevent\nflashing from achieving the desired frequency!"
        create_tool_tip(led_dur_entry, led_dur_tooltip_txt)
            
            #+++++++++++++++++++++++ back to arduino checkbox +++++++++++++++++
        arduino_checkbox = tk.Checkbutton(arduino_frame, text="Use arduino?", 
                                          variable=self.use_arduino, 
                                          command=partial(self.handle_arduino_toggle, 
                                                          led_freq_entry, 
                                                          led_freq_label, 
                                                          led_dur_entry, 
                                                          led_dur_label, 
                                                          self.use_arduino))
        arduino_checkbox.var = self.use_arduino
        arduino_checkbox.pack(side=tk.LEFT, fill = tk.X, pady=15)
        arduino_tooltip_txt = "If you want to use optogenetic light\n stim check the 'Use arduino' box."
        create_tool_tip(arduino_checkbox, arduino_tooltip_txt)
        
        #++++++++++++++++++++ packing LED dur ++++++++++++++++++++++++   
        led_dur_frame.pack(side=tk.RIGHT,fill=tk.X, pady=15)                       
        led_dur_label.pack(side=tk.TOP)
        led_dur_entry.pack(side=tk.TOP)
        
        #++++++++++++++++++++ packing LED freq +++++++++++++++++++++++   
        led_freq_frame.pack(side=tk.RIGHT,fill=tk.X, pady=15, padx=30)     
        led_freq_label.pack(side=tk.TOP)
        led_freq_entry.pack(side=tk.TOP)
        
        #------------------ other options Frame -----------------------
        #write_video, write_csv, fps_cap
        other_opt_frame = tk.Frame(self.master, padx=30, pady=15, 
                                   borderwidth=1, relief=tk.SUNKEN)
        other_opt_frame.pack(side=tk.TOP, padx=15, pady=15, fill=tk.X)
        
        write_vid_checkbox = tk.Checkbutton(other_opt_frame, 
                                            text="Write .AVI video?", 
                                            variable=self.write_vid)
        write_vid_checkbox.var = self.write_vid 
        write_vid_checkbox.pack(side=tk.LEFT)
        
        write_csv_checkbox = tk.Checkbutton(other_opt_frame, 
                                            text="Write .CSV file?", 
                                            variable=self.write_csv)
        write_csv_checkbox.var = self.write_csv
        write_csv_checkbox.pack(side=tk.LEFT, padx=50)
        
        #+++++++++++++++++++++++ fps cap frame +++++++++++++++++++++++++
        fps_cap_frame = tk.Frame(other_opt_frame)
        fps_cap_frame.pack(side=tk.RIGHT, fil=tk.X,  pady=10)
        
        fps_cap_label = tk.Label(fps_cap_frame, text = "FPS to enforce:")
        fps_cap_entry = tk.Entry(fps_cap_frame, textvariable=self.fps_cap, 
                                 justify=tk.CENTER)
        fps_cap_tooltip_txt = "Set the max frames per second\n to collect video at. Make sure your\ncamera can support the specified FPS."
        create_tool_tip(fps_cap_entry, fps_cap_tooltip_txt)
        
        fps_cap_label.pack(side=tk.TOP)
        fps_cap_entry.pack(side=tk.TOP)
            
        #------------------- Bottom Frame ------------------------------
        #Preview video, set ROIs, halt Experiment    
        bottom_frame = tk.Frame(self.master, padx=15)
        bottom_frame.pack(side=tk.TOP, fill=tk.X)
        
        preview_btn= tk.Button(bottom_frame, text="Preview video", pady=2, 
                               command=self.handle_preview_camera)
        preview_btn.pack(side=tk.LEFT, fill = tk.X, pady=15, expand=1)    
                
        stop_btn = tk.Button(bottom_frame, text="Stop current experiment (!)", 
                             pady=2, command = self.handle_emergency_stop)
        stop_btn.pack(side=tk.RIGHT, fill=tk.X, pady=15, expand=1)
        stop_tooltip_txt = "Will immediately halt the\n currently running experiment!"
        create_tool_tip(stop_btn, stop_tooltip_txt)

        #----------------------- ROI frame ------------------------------
        roi_frame = tk.Frame(self.master, padx=15, borderwidth=1, 
                             relief=tk.SUNKEN)
        roi_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=10)
        
        save_roi_btn = tk.Button(roi_frame, text="Save ROIs", pady=2, 
                                 command=self.save_rois)
        save_roi_tooltip_txt = "ROIs will be saved as: FlyActivityAssay_ROIs.json\nin the same folder as this UI script."
        create_tool_tip(save_roi_btn, save_roi_tooltip_txt)
        
        set_roi_btn = tk.Button(roi_frame, text="Set ROIs", pady=2, 
                                command=partial(self.handle_set_rois, save_roi_btn))
        set_roi_btn.pack(side=tk.LEFT, fill = tk.X,expand=1, pady=15)
        roi_tooltip_txt = "Set the regions of interest\n to quantitate activity over.\nAfter setting ROIs, the option\n to save them will appear."
        create_tool_tip(set_roi_btn, roi_tooltip_txt)
        
        load_roi_btn = tk.Button(roi_frame, text="Load ROIs", pady=2, 
                                 command=partial(self.load_rois, self.master, "Please select the ROIs.json file you wish to load "))
        load_roi_btn.pack(side=tk.RIGHT, fill=tk.X,expand=1, pady=15)
         
        #-------------------- Save Directory Frame label ---------------------
        save_dir_frame = tk.Frame(self.master, padx=15)
        save_dir_frame.pack(side=tk.TOP, fill=tk.X)
        
        save_gen_label = tk.Label(save_dir_frame, 
                                  text="Directory to save assay analysis and output to:")
        save_gen_label.pack(side=tk.LEFT)
        
        #------------------ Save directory frame -------------------------
        dir_frame = tk.Frame(self.master, padx=15)
        dir_frame.pack(side=tk.TOP, fill=tk.X)
    
        dir_list = tk.Listbox(dir_frame, width=50, height=1)
        dir_list.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)
        
        self.dir_list_init(dir_list)
    
        choose_dir = tk.Button(dir_frame, text='Choose', pady=0, 
                               command = partial(self.handle_dir_choose, self.master, dir_list))
        choose_dir.pack(side=tk.RIGHT, pady=5)
           
        #------------------- Run Frame ---------------------------------
        run_frame = tk.Frame(self.master, padx=15)
        run_frame.pack(side=tk.TOP, fill=tk.X)
        
        run_btn = tk.Button(run_frame, text="Start activity assay!", pady=2, 
                            command = partial(self.handle_run, dir_list))
        run_btn.pack( fill=tk.X, pady=5)
    
    def __init__(self, master=None):
        tk.Frame.__init__(self, master) 
        self.master=master
        self.pack()
        self.define_variables()
        self.create_widgets()
               
        default_calib_loc = os.path.join(os.getcwd(), "Camera_calibration_matrices.json")
        try:
            self.load_cam_calib_file(self.master, default_calib_loc)
        except:
            print("Automatic attempt to load camera calibration file failed. Please manually load a calibration file or perform a camera calibration from the menu")

if __name__ == '__main__': 
    root = tk.Tk()
    root.title("Fly Activity Assay - User Interface")
    app = Application(master=root)
    app.mainloop()