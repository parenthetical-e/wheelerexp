"""Calculate event-related average trials for each response

usage: python ./rt_timecourse.py"""

import sys, os

import pandas as pd
import numpy as np

from fmrilearn.analysis import eva, fir
from fmrilearn.preprocess.labels import (construct_targets, 
        construct_filter, filter_targets, create_y, merge_labels)
from fmrilearn.preprocess.data import remove_invariant_features
from fmrilearn.load import load_nii
from fmrilearn.info import print_target_info, print_X_info

from wheelerdata.load.fh import get_RT_metadata_paths, get_roi_data_paths


# ----
# Globals
TR = 1.5
WINDOW = 20  ## In TR, leftover from fir usage.... leaving for now.
MINWINDOW = 11  ## In TR

def timecourses(roi, table):
    print("----")
    roipaths = get_roi_data_paths(roi)
    metapaths = get_RT_metadata_paths()

    # ----
    # Loop overs Ss data, preprocess, and classify
    Xeva, yeva, roinames, timecourse_index = None, None, None, None  ## Init
    i = 0
    for roipath, metapath in zip(roipaths, metapaths):
                    
        _, roiname = os.path.split(roipath)
        roiname, _ = os.path.splitext(roiname)

        # ----
        # Get data, only keep labeled data, that which we have a TR for
        print("Loading {0}".format(roipath))
        X = remove_invariant_features(load_nii(
                roipath, sparse=True)).todense()

        # ----
        # Load labels and construct targets
        print("Loading {0}".format(metapath))
        meta = pd.read_csv(metapath)    
        reaction_times = np.array(meta["rt"].tolist())
        trial_index = np.array(meta["trialcount"].tolist())
        trs = np.array(meta["TR"].tolist())

        print("Constructing targets")
        targets = construct_targets(
                reaction_times=reaction_times, 
                trial_index=trial_index,
                trs=trs)

        # ----
        # Filter for valid resp only
        print("Filtering")
        X = X[targets["trs"],:] ## Need to align X with targets before
                                ## anything else.

        # By rt
        keepers = ["rt1", "rt2", "rt3", "rt4"]
        keep_rts = construct_filter(targets["reaction_times"], keepers, True)
        targets = filter_targets(keep_rts, targets)
        X = X[keep_rts,:]
        
        # --
        # Combine reaction_times into fast and slow
        fsmap = {
            "rt1": "slow", "rt2": "slow", 
            "rt3": "fast", "rt4" : "fast"
        }
        targets["fast_slow"] = merge_labels(targets["reaction_times"], fsmap)
        
        print("After filtration.")
        print_target_info(targets)
        print_X_info(X)
        
        # ----
        # Calc trial estimates
        print("Calculating timecourses")
        y =  create_y(targets["fast_slow"])
        Xeva_i, yeva_i, timecourse_index_i = eva(X, targets["fast_slow"], targets["trial_index"], MINWINDOW)
        roinames_i = np.repeat(roiname, yeva_i.shape[0])
        
        # Check col numbers, skip with warning if off
        if (i > 0) and (Xeva.shape[1] != Xeva_i.shape[1]):
            print("WARNING: {0} had the wrong number of cols.".format(roiname))
            print("***SKIPPING***")
            continue
        
        print("Joining timecourses")
        if i == 0:
            Xeva = Xeva_i.copy()
            yeva = yeva_i.copy()
            roinames = roinames_i.copy()
            timecourse_index = timecourse_index_i.copy()
        else:
            Xeva = np.vstack([Xeva, Xeva_i])
            yeva = np.concatenate([yeva, yeva_i])
            roinames = np.concatenate([roinames, roinames_i])
            timecourse_index = np.concatenate([timecourse_index,
                    timecourse_index_i])
        
        i += 1
    
    print("Saving")
    # Use pandas to save a data table....
    df_eva = pd.DataFrame(Xeva)
    df_eva['reaction_times'] = yeva    ## Renaming for clarity
    df_eva['roinames'] = roinames
    df_eva['timecourse_index'] = timecourse_index
    df_eva["vox_mean"] = Xeva.mean(1)  ## Average of all voxels
    df_eva.to_csv(table, sep=',', index=False)


if __name__ == "__main__":

    ROIS = ["respXtime_rfx_mask",
           "left_ventrical",
           "right_ventrical",
           "left_putamen",
           "right_putamen",
           "left_caudate",
           "right_caudate",
           "sma",
           "precentral",
           "postcentral",
           "parietal_superior",
           "loc_superior",
           "loc_iferior",
           "mfg",
           "sfg",
           "insula",
           "ifg_triangularis",
           "ifg_opercularis",
           "stempotal_anterior",
           "stempotal_posterior",
           "acc",
           "pcc",
           "precuneous",
           "ofc",
           "left_hippocampus",
           "right_hippocampus",
           "parahippo_anterior",
           "parahippo_posterior"]

    # print("TEST RUN")
    # ROIS = ["respXtime_rfx_mask",]

    for roi in ROIS:
        timecourses(roi, "fh_rt_eva_timecourse_{0}.csv".format(roi))
