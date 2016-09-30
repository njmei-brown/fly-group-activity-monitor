# -*- coding: utf-8 -*-
"""
Created on Wed Feb 24 16:05:07 2016

@author: Nicholas Mei

Summarized plotting script that takes an experiment condition folder (containing
individual experiments) and bins activity data for each experiment before plotting them 

"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import glob
import math

#If we are using python 2.7 or under
if sys.version_info[0] < 3:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox
    import tkSimpleDialog
      
#If we are using python 3.0 or above
elif sys.version_info[0] >= 3:
    import tkinter as tk
    import tkinter.filedialog as filedialog
    from tkinter import messagebox as tkMessageBox
    from tkinter import simpledialog as tkSimpleDialog

def chooseDir(cust_text):
    root = tk.Tk()
    try:
        root.tk.call('console','hide')
    except tk.TclError:
        pass
    
    baseFilePath = os.path.expanduser('~')
    directoryPath = filedialog.askdirectory(parent = root, title=cust_text, initialdir= baseFilePath)
    root.destroy()
    
    return directoryPath
    
def chooseFile(cust_text, default_dir=None):
    if not default_dir:
        baseFilePath = os.path.expanduser('~')
        default_dir = baseFilePath
    root = tk.Tk()
    try:
        root.tk.call('console', 'hide')
    except tk.TclError:
        pass
    filepath = filedialog.askopenfilename(parent=root, title=cust_text,
                                          defaultextension='.csv', 
                                          filetypes=[('CSV file','*.csv'),('All files','*.*')], 
                                          initialdir=default_dir)
    root.destroy()
    return filepath
        
class ResultsDict(dict):
    pass

#%%

def load_flygram_experiments(bin_size = 10, raw_data_path = None, 
                             expt_key_path = None, preview=False, 
                             norm_to_bl = False, bl_window = 30):
    
    if raw_data_path and expt_key_path:      
        #Load experiment key file
        #key file is a .csv with: "Datetime", "ROI", "Num_Flies", and "Treatment" columns
        key_df = pd.read_csv(expt_key_path)
        
        #Determine file paths for raw .csv data from the flyGrAM expts
        files_to_analyze = glob.glob('{basedir}/*/*-roi?.csv'.format(basedir = raw_data_path))
    
        treatments = list(set(key_df['Treatment'].values)) 
        try:
            sorted_treatments = sorted(treatments, key = lambda value: int(value.split(":")[0]))
        except:
            print("\nNote: Could not sort by 'Air:Ethanol' flow rate.\nTrying alternative sorting.")
            pass
        
        sorted_treatments = sorted(treatments)
        
        results_dict = ResultsDict()
        raw_results_dict = ResultsDict()
        for treatment in sorted_treatments:            
            expt_details = key_df.loc[key_df['Treatment'] == treatment]   
            
            binned_data = []
            for df_tuple in expt_details.itertuples():
                datetime = df_tuple[1]
                roi = df_tuple[2]
                num_flies = df_tuple[3]
                path = [path for path in files_to_analyze if (datetime in path) and ('roi{}'.format(roi) in path)]
            
                try:
                    data = pd.read_csv(path[0])
                except IndexError:
                    print("\n##################################################\n")
                    print("Error reading in roi .csv!\nCould not find [roi {}] with base name of:\n{}".format(roi, datetime))
                    print("\n##################################################\n")                    
                    raise
                        
                expt_dur = int(round(data['Time Elapsed (sec)'].max()))
                stim_start_time = data['Time Elapsed (sec)'][data['Stimulation'] == True].iloc[0]
                stim_end_time = data['Time Elapsed (sec)'][data['Stimulation'] == True].iloc[-1]  
                
                #normalize data based on the number of flies in each ROI (experimentor must supply this information!)
                data['Number of active flies'] = data['Number of active flies'].div(float(num_flies))
                
                if norm_to_bl:
                    baseline_window = data[data['Time Elapsed (sec)'] <= bl_window]['Number of active flies']
                    baseline_avg = baseline_window.mean()
                    
                    data['Number of active flies'] = data['Number of active flies'].div(baseline_avg)                    
                    
                #Group activity count data in bins of a specified duration (in seconds)
                binned_activity = data.groupby(pd.cut(data['Time Elapsed (sec)'], bins=range(0, expt_dur, bin_size)))['Number of active flies']
                                               
                binned_activity = binned_activity.mean()
                binned_activity.expt_dur = expt_dur
                binned_activity.stim_start_time = stim_start_time
                binned_activity.stim_end_time = stim_end_time
                                               
                binned_data.append(binned_activity)
                            
            raw_results_dict[treatment] = binned_data
            raw_results_dict.expt_dur = binned_data[0].expt_dur
            raw_results_dict.stim_start_time = binned_data[0].stim_start_time
            raw_results_dict.stim_end_time = binned_data[0].stim_end_time
            raw_results_dict.bin_size = bin_size
            
            #concatenate columns of binned data together (axis 1)
            result = pd.concat(binned_data, axis=1)       
            #take the mean and sem for 
            means = result.mean(axis=1)
            errors = result.sem(axis=1) 
            
            results_dict.expt_dur = binned_data[0].expt_dur
            results_dict.stim_start_time = binned_data[0].stim_start_time
            results_dict.stim_end_time = binned_data[0].stim_end_time
            results_dict.bin_size = bin_size
            
            results_dict[treatment] = (means, errors)
            
        if preview:
            for treatment in sorted_treatments:
                print("plotting {}".format(treatment))
                results_dict[treatment][0].plot()
            plt.show()
           
        return raw_results_dict, results_dict
        
#%%        
def plot_flygram_experiments(tk_root, bin_size, raw_data_path, key_path, save_loc, norm_to_bl = False, bl_window = 30):
    raw_results, results = load_flygram_experiments(bin_size = bin_size, 
                                         raw_data_path = raw_data_path, 
                                         expt_key_path = key_path, 
                                         preview=False, norm_to_bl=norm_to_bl, bl_window = bl_window)
    
    stim_start_time = results.stim_start_time
    stim_end_time = results.stim_end_time
    bin_size = results.bin_size
    
    try:
        sorted_treatments = sorted(results.keys(), key = lambda value: int(value.split(":")[0]))
    except:
        print("Could not sort by 'Air:Ethanol' flow rate, trying alternative sorting")
        pass
    
    sorted_treatments = sorted(results.keys())
    
    #color_palette = ["#5752D0", "#0376F7", "#36A6D6", "#5AC4F6", "#4ED55F", "#FCC803", "#F99205", "#F93B2F"]  
    color_palette = ["#5752D0", "#36A6D6", "#4ED55F", "#F99205"]  
    
    stim_label = tkSimpleDialog.askstring(parent=tk_root, title="Stimulus Label", prompt="Please enter a stimulus label for the plot")
    
    fig, ax = plt.subplots()
    fig.set_facecolor('white')
    fig.suptitle('flyGrAM Activity Summary', fontsize=16)
    
    legend_objects = []
    
    for indx, treatment in enumerate(sorted_treatments): 
        if norm_to_bl:
            means = results[treatment][0].values
            errors = results[treatment][1].values
        else:
            means = results[treatment][0].values*100
            errors = results[treatment][1].values*100
        
        #parse strings of x-axis binned intervals
        x_axis_values = list(results[list(results.keys())[0]][0].index.values)
        #convert interval strings into a numerical value of x_axis_values
        x_axis_values = [int(value.lstrip('(').split(',')[1].rstrip(']')) for value in x_axis_values]
        
        #original
        orig_x_axis_values = x_axis_values        
        
        #solution to stimulation axvspan not 'matching up' with datapoints
        x_axis_values = np.array(x_axis_values) - bin_size/2.0
        
        line, = ax.plot(x_axis_values, means, marker='o', color=color_palette[indx], mec=color_palette[indx], markersize=3.00)   
        patch = mpatches.Patch(color=color_palette[indx], alpha=0.4, linewidth=0)
        ax.fill_between(x_axis_values, means-errors, means+errors, 
                        color=color_palette[indx], alpha=0.4)                       
        legend_objects.append((line, patch))
    
    if norm_to_bl:
        ax.set_ylim([0,5])
    else:
        #print(x_axis_values)
        ax.set_ylim([0,90])

    ax.set_xlim([0,orig_x_axis_values[-1]+2*bin_size])    
    x_ticks = np.linspace(0, orig_x_axis_values[-1]+bin_size, 10, dtype=int)  

    ax.set_xticks(x_ticks)
    ax.set_xlabel('Time Elapsed (sec)', fontsize = 16)
    if norm_to_bl:
        ax.set_ylabel('Activity Normalized to Baseline', fontsize=16)
    else:
        ax.set_ylabel('Percent Activity', fontsize = 16)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False) 
    ax.tick_params(axis='both', which='both', top='off', right='off', left='off', bottom='off')
    ax.grid(False)
    
    ax.axvspan(int(math.floor(stim_start_time)), int(math.floor(stim_end_time)), facecolor='#8D8B90', alpha=0.30, edgecolor = 'none',) 
    
    label_pos = (stim_start_time+stim_end_time - 2*bin_size)/2
    
    ax.text(label_pos, 80, stim_label, fontsize=16, horizontalalignment='center', color='#8D8B90')
    
    for label in ax.yaxis.get_ticklabels()[::2]:
        label.set_visible(False)
        
    lgd = ax.legend(tuple(legend_objects), tuple(sorted_treatments), title='Treatment',
                    loc='center right', bbox_to_anchor=(1.45, 0.5), markerscale=0)
    lgd.get_title().set_fontsize('16')
    lgd.get_frame().set_linewidth(0.0)
    
    #lgd.get_title().set_ha('center')
    #renderer = fig.canvas.get_renderer()
    #shift = max([text.get_window_extent(renderer).width for text in lgd.get_texts()])
    #lgd.get_title().set_position((shift-5,0))
    
    #[140,300, 340, 600, 900, 1100]
    
    plt.tight_layout()
    fig.subplots_adjust(top=0.85)
    plt.show()

    raw_result = tkMessageBox.askyesno(parent=tk_root,message="Would you like to save the raw binned fly-GrAM data to {}?".format(save_loc))
    
    if raw_result:
        for treatment in sorted_treatments:
            df_list = raw_results[treatment]
            num_replicates = len(df_list)          
            column_df = pd.concat(df_list, axis=1)       
            rep_labels = ["Replicate {} Percent Group Activity".format(num+1) for num in range(num_replicates)]   
            column_df.columns = rep_labels          
            result_filename = treatment.replace("/", ".") + '.xls'      
            result_path = os.path.join(save_loc, result_filename)      
            column_df.to_excel(result_path)
            
    fig_result = tkMessageBox.askyesno(parent=root,message="Would you like to save a pdf results file to {}?".format(save_loc))
    
    if fig_result:
        filename = tkSimpleDialog.askstring(parent=tk_root, title="Filename", prompt="Please enter a desired name for the plotted pdf file")
        
        if filename:
            if not filename.endswith(".pdf"):
                filename = filename+".pdf"
            
            fig.savefig(os.path.join(save_loc, filename), bbox_extra_artists=(lgd,), bbox_inches='tight', format='pdf')
        else:
            print("You did not specify a filename!")
    else:
        print("Figure was not saved!")
    
if __name__ == '__main__': 
    raw_data_path = chooseDir("Please choose the directory which contains your raw fly-GrAM data")   
    key_path = chooseFile("Please choose the '.csv' key file describing experiment conditions", default_dir=raw_data_path)
    save_loc = os.path.join(os.path.expanduser('~'), "Desktop")
    
    raw_data_path = os.path.normpath(raw_data_path)
    key_path = os.path.normpath(key_path)
    save_loc = os.path.normpath(save_loc)
    
    root = tk.Tk()
    try:
        root.tk.call('console', 'hide')
    except tk.TclError:
        pass
    
    bin_size = tkSimpleDialog.askinteger(title="Analysis Bin Size", prompt="Please enter a desired bin analysis size (seconds)")
    
    if not bin_size:
        print("Bin Size for analysis was not specified! Defaulting to a bin size of 10 seconds!")
        bin_size=10
           
    plot_flygram_experiments(tk_root=root, bin_size=bin_size, 
                             raw_data_path=raw_data_path, 
                             key_path=key_path, save_loc=save_loc, 
                             norm_to_bl=False,bl_window=120)
    root.destroy()
