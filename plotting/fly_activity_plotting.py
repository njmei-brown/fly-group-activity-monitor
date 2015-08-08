# -*- coding: utf-8 -*-
"""
Created on Wed Jun 17 16:41:50 2015

@author: Nicholas Mei

Summarized plotting script that takes an experiment condition folder (containing
individual experiments) and bins activity data for each experiment before plotting them 

"""
import sys
import os
import matplotlib.pyplot as plt
import pandas as pd
import glob
import math

#If we are using python 2.7 or under
if sys.version_info[0] < 3:
    import Tkinter as tk
    import tkFileDialog
    
    def chooseDir(cust_text):
        root = tk.Tk()
        try:
            root.tk.call('console','hide')
        except tk.TclError:
            pass
        
        baseFilePath = "C:/Users/Nicholas/Desktop/FlyBar Analysis"
        directoryPath = tkFileDialog.askdirectory(parent = root, title=cust_text, initialdir= baseFilePath)
        root.destroy()
        
        return directoryPath
        
#If we are using python 3.0 or above
elif sys.version_info[0] > 3:
    import tkinter as tk
    from tkinter.filedialog import askdirectory
    
    def chooseDir(cust_text):
        root = tk.Tk()
        try:
            root.tk.call('console','hide')
        except tk.TclError:
            pass
        
        baseFilePath = "C:/Users/Nicholas/Desktop/FlyBar Analysis"
        directoryPath = askdirectory(parent = root, title=cust_text, initialdir= baseFilePath)
        root.destroy()
        
        return directoryPath

#datafile
#datafile = u'C:/Users/Nicholas/Desktop/fly-activity-assay/Analysis/5 Hz 10 Pulse width/2015-06-08 18.38/2015-06-08 18.38-roi1.csv'

      
def plot_summarized_activity(bin_size=5, scaling_matrix = None):
    """
    plotting function that allows user to select an experiment condition folder
    (containing individual experiment results folders). Function bins activity data
    for each experiment before averaging binned activity over replicates.    
    
    This function assumes that you've normalized for the number of flies
    in each roi csv file so that unequal numbers of flies in each ROI do not skew results
    """

    rois_to_analyze = ['roi1', 'roi3', 'roi2', 'roi4']
    #select a folder that contains all the experiments that you want to analyze together
    base_directory = chooseDir("Please select the experiment condition you would like to have analyzed")    
    
    if os.path.exists(base_directory):
    
        fig, axarr = plt.subplots(2,2, sharey=True)    
        fig.suptitle('{}'.format(os.path.basename(base_directory)), fontsize=20, fontweight='bold')
        
        for indx, roi in enumerate(rois_to_analyze):
            files_to_analyze = glob.glob('{basedir}/*/*-{roi_name}.csv'.format(basedir = base_directory, roi_name = roi))
            #print files_to_analyze
            #print len(files_to_analyze)
            
            binned_data = []
            for indx2, datafile in enumerate(files_to_analyze):      
                
                scaling_factor = scaling_matrix[4*indx + indx2]                
                
                data = pd.read_csv(datafile)
                
                expt_dur = int(round(data['Time Elapsed (sec)'].max()))
                stim_start_time = data['Time Elapsed (sec)'][data['Stimulation'] == True].iloc[0]
                stim_end_time = data['Time Elapsed (sec)'][data['Stimulation'] == True].iloc[-1]   
                
                #scale data accordingly
                data['Number of active flies'] = data['Number of active flies']/float(scaling_factor)
    
                #Group activity count data in bins of a specified duration (in seconds)
                binned_activity = data.groupby(pd.cut(data['Time Elapsed (sec)'], bins=range(0, expt_dur, bin_size)))['Number of active flies']
                
                binned_data.append(binned_activity.mean())
            
            #concatenate columns together (axis 1)
            result = pd.concat(binned_data, axis=1)       
            means = result.mean(axis=1)
            errors = result.sem(axis=1) 
            
            #Plotting stuff
            currax = axarr.flat[indx]              
            currax.set_title('Binned activity for roi {}'.format(roi.lstrip('roi')), fontsize=14)
            means.plot(ax=currax, yerr = errors, marker='o')
            currax.set_xlabel('Time elapsed in {} second bins'.format(bin_size))
            currax.set_ylabel('Normalized mean number of active flies')
            currax.spines['right'].set_visible(False)
            currax.spines['top'].set_visible(False) 
            currax.tick_params(top="off",right="off")
            currax.grid(False)
            #get the appropriate group indx by dividing the stim_start_time by bin size
            #Also need to account for the fact that binning starts at 0 so subtract 1 from the resulting indx
            currax.axvspan(int(math.floor(stim_start_time/bin_size))-1, int(math.floor(stim_end_time/bin_size))-1, facecolor='r', alpha=0.25, edgecolor = 'none') 