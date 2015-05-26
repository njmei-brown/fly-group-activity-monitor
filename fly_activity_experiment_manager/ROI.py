# -*- coding: utf-8 -*-
"""
Created on Fri May 15 10:52:03 2015

@author: Nicholas Mei

Package so that the ROI and LINE classes are a separate import.

Allows user to draw rectangular ROIs as well as 'beam crossing' lines.
"""
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

class set_roi(object):
    """
    Class to set an roi in an image.
    Saves start of ROI on mouse button press and saves end of ROI on mouse button release
    """
    def __init__(self, roi_color, background_img):        
        self.fig, self.ax = plt.subplots()
        self.fig.set_size_inches((11, 8.5), forward=True)
        self.ax.imshow(background_img)
        self.fig.suptitle("Press the 'n' key on your keyboard when you are happy with the ROI", size=14)

        self.type = 'roi'        
        self.color = roi_color
        self.bg_img = background_img
        self.rect = Rectangle((0,0), 0, 0, edgecolor = 'black', color=self.color, alpha=0.4)
        
        self.start_pos = None
        self.end_pos = None   
        self.current_pos = None        
        self.released = True
        self.roi_finalized = False
        
        self.ax.add_patch(self.rect)
        self.ax.figure.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.ax.figure.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.ax.figure.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        self.ax.figure.canvas.mpl_connect('key_press_event', self.on_key_press)     

    def on_mouse_press(self, event):
        self.released = False
        if self.roi_finalized is False:
            self.start_pos = np.array([event.xdata, event.ydata])

    def on_mouse_release(self, event):
        self.released = True
        if self.roi_finalized is False:
            self.end_pos = np.array([event.xdata, event.ydata]) 
            self.diff = (self.end_pos - self.start_pos)
            self.rect.set_width(self.diff[0])
            self.rect.set_height(self.diff[1])
            self.rect.set_xy(self.start_pos)
            self.ax.figure.canvas.draw()
                  
    def on_mouse_motion(self, event):
        if self.roi_finalized is False:
            if self.released is False:
                self.current_pos = np.array([event.xdata, event.ydata])
                self.diff = (self.current_pos - self.start_pos)
                self.rect.set_width(self.diff[0])
                self.rect.set_height(self.diff[1])
                self.rect.set_xy(self.start_pos)
                self.ax.figure.canvas.draw()
    
    def on_key_press(self, event):
        if event.key=='n':
            self.roi = (self.start_pos.astype('int'), self.end_pos.astype('int'))
            #print "test"
            self.roi_finalized = True
            plt.close(self.fig)
          
class set_line(object):
    """
    Class to set a line to cross in an image
    Saves either an X coordinate for a vertical line or a Y coordinate for a horizontal one
    
    line will have a bit of thickness as it is essentially a very thin rectangular ROI
    """    
    def __init__(self, line_color, background_img, line_width=3, line_mode = 'vertical'):        
        self.fig, self.ax = plt.subplots()
        self.fig.set_size_inches((11, 8.5), forward=True)
        self.ax.imshow(background_img)
        self.fig.suptitle("Press the 'n' key on the keyboard when you are happy with the line", size=14)

        self.type = 'line'        
        self.line_width=line_width
        self.color = line_color
        self.ax_height, self.ax_width = background_img.shape[:2]
                
        self.line_mode = line_mode
        self.click_pos = None    
        self.start_pos = None
        self.end_pos = None
        self.roi = None
        self.roi_finalized = False        
        self.line = Rectangle((0,0), 0, 0, edgecolor = 'black', color=self.color, alpha=0.4)        
        
        self.ax.add_patch(self.line)
        self.ax.figure.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.ax.figure.canvas.mpl_connect('key_press_event', self.on_key_press)
        
    def on_mouse_press(self, event):
        if self.roi_finalized is False:
            self.click_pos = np.array([event.xdata, event.ydata])
            
            if self.line_mode is 'vertical':
                self.center_offset = event.xdata - self.line_width/2.        
                self.line.set_width(self.line_width)
                self.line.set_height(self.ax_height)
                self.line.set_xy((self.center_offset, 0))
                
                self.start_pos = np.array([self.center_offset, 0])
                self.end_pos = np.array([self.center_offset + self.line_width, self.ax_height])
                               
            if self.line_mode is 'horizontal':
                self.center_offset = event.ydata - self.line_width/2.        
                self.line.set_width(self.ax_width)
                self.line.set_height(self.line_width)
                self.line.set_xy((0, self.center_offset))
                
                self.start_pos = np.array([0, self.center_offset])   
                self.end_pos = np.array([self.ax_width, self.center_offset + self.line_width])
            
            self.ax.figure.canvas.draw()
        
    def on_key_press(self, event):
        if event.key=='n':
            self.roi = (self.start_pos.astype('int'), self.end_pos.astype('int'))
            #print "test"
            self.roi_finalized = True
            plt.close(self.fig)