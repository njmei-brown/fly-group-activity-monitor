# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 15:13:02 2015

@author: Nicholas Mei

Functions to calibrate, save calibration, and test calibration of 
barrel distortions produced by webcam lenses.

Does *NOT* correct for perspective distortions! (that's maybe an upcoming feature...)

Adapted using examples from:
http://docs.opencv.org/3.0-beta/doc/py_tutorials/py_calib3d/py_calibration/py_calibration.html
http://www.janeriksolem.net/2014/05/how-to-calibrate-camera-with-opencv-and.html

"""

import numpy as np
import cv2
import json


def preview_camera():
    cam = cv2.VideoCapture(0)
    
    while True:
        _, img = cam.read()
        
        cv2.imshow('preview', img)
        
        k = cv2.waitKey(30) & 0xff
        if k == 27:
            break
        
        
    cam.release()
    cv2.destroyAllWindows()

def calibrate_camera():
    """
    This function does live collection of chessboard calibration points and takes
    150 such calibration samples. It calculates the appropriate transformation
    matrices then saves them into a JSON file for easy loading later.
    
    """

    # termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    
    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((6*7,3), np.float32)
    objp[:,:2] = np.mgrid[0:7,0:6].T.reshape(-1,2)
    
    # Arrays to store object points and image points from all the images.
    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane.
    
    #images = glob.glob('*.jpg')
    
    cam = cv2.VideoCapture(0)
    
    
    while True:
        _, img = cam.read()
        
        cv2.imshow('image', img)
        cv2.waitKey(500)        
            
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    
        # Find the chess board corners
        ret, corners = cv2.findChessboardCorners(gray, (7,6),None)
    
        # If found, add object points, image points (after refining them)
        if ret == True:
            objpoints.append(objp)
    
            corners2 = cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)
            imgpoints.append(corners2)
    
            # Draw and display the corners
            cv2.drawChessboardCorners(img, (7,6), corners2,ret)
            cv2.imshow('Chessboard Corners Found!',img)
            k = cv2.waitKey(30) & 0xff
            
            print len(imgpoints)
            if len(imgpoints) > 150 or k==27:
                break
            
    cam.release()
    cv2.destroyAllWindows()
    
    #Creating Calibration matrices
    print "Calculating calibration matrix, this may take a while!"
    rms, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1],None,None)
    
    
    print "RMS:", rms
    print "camera matrix:\n", mtx
    print "distortion coefficients: ", dist.ravel()
    
    
    #Re-projection error:
    def calc_reprojection_error(objpoints, imgpoints, mtx, dist):
        tot_error = 0
        for i in xrange(len(objpoints)):
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
            error = cv2.norm(imgpoints[i],imgpoints2, cv2.NORM_L2)/len(imgpoints2)
            tot_error += error
        
        print "mean error: ", tot_error/len(objpoints)
    
    print "Reprojection mean error is: ", calc_reprojection_error(objpoints, imgpoints, mtx, dist)
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
            
    fname = "Camera_ELP_calibration_matrices.json"
    
    #defaults to saving to desktop
    
    with open(fname, "w") as f:
        json.dump(data, f)

#=============================================================================
def read_cam_calibration_file(filepath):
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

#=============================================================================
#Testing calibration to make sure distortions are removed
    
def test_calibration():
    cam = cv2.VideoCapture(cv2.CAP_DSHOW + 0)
    
    data = read_cam_calibration_file("Camera_ELP_calibration_matrices.json")    
    mtx = data["camera_matrix"]
    dist = data["dist_coeff"]
    
    while True:
        ret, frame = cam.read()
        h,  w = frame.shape[:2]
        
        #apply undistortion
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx,dist,(w,h),1,(w,h))
        unwarped = cv2.undistort(frame, mtx, dist, None, newcameramtx)
        
        # crop the image
        x,y,w,h = roi
        unwarped = unwarped[y:y+h, x:x+w]
        
        #image comparisons
        cv2.imshow('original', frame)
        cv2.imshow('corrected',unwarped)
        
        key = cv2.waitKey(10)
        if key == 27:
            cv2.destroyAllWindows()
            break
