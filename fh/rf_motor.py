""" See exp() for details:

Usage
-----
* Command line:
    python ./motor.py   ## Runs many ROIs (runtime is ~10 hours)

* ipython:
    >>> from fmrilearnexp.motor import exp
    >>> # Use the known good functional ROI....
    >>> exp("respXtime_rfx_mask",
            "/data/data2/meta_accumulate/fh/roinii",
            "/data/data2/meta_accumulate/fh/fidl",
            "fm_motor_accuracy_test.txt"
            True)
"""
import os
import numpy as np
import pandas as pd

from functools import partial

# sklearn imports.
from sklearn.preprocessing import scale
from sklearn.cross_validation import KFold
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import (classification_report, accuracy_score,
        precision_score, recall_score, f1_score)

# fmrilean imports.
from fmrilearn.load import load_nii
from fmrilearn.save import (save_accuracy_table, reset_accuracy_table)
from fmrilearn.preprocess.data import (remove_invariant_features, 
        create_X_stats, smooth, shiftby)
from fmrilearn.preprocess.labels import (construct_targets, 
        construct_filter, filter_targets)
from fmrilearn.info import (print_target_info, print_X_info, print_clf_info,
        print_label_counts)
from fmrilearn.classify import simpleCV

# wheelerdata import
from wheelerdata.load.fh import (get_roi_data_paths,
        get_motor_metadata_paths)

def exp(roi, table, verbose):
    """
    An experimental function to classify a ROI from the 
    face/house data by motor response.
    
    Parameters
    ----------
    roi - the name of the roi to use
    roipath - the full path to the nifti data to classfiy
    metapath - the full path to the metadata (labels)
    table - the name of results table.
    verbose - Print debugging/status info (True).  If False this 
        function is silent.
    
    Return
    ------
    Saves a table of classification accuracies for each subject's 
        cross validation fold (n=5) as well as the overall subject 
        mean.
    
    Data
    ----
        * Face/house
        * Note: runs each subject in the face/house set in a separate
            classification experiment.

    Details
    -------
        * Classes:
            1. 'resp', i.e. motor response - 'left'/'right'

        * Preprocessing:
            1. remove_invariant_features, 
            2. smooth, 
    """
    
    roipaths = get_roi_data_paths(roi)
    metapaths = get_motor_metadata_paths()
    
    # ----
    # Loop overs Ss data, preprocess, and classify
    overall_accuracy = []
    for roipath, metapath in zip(roipaths, metapaths):
        if verbose:
            print("----")
            print("Loading data.")
            print("\t{0}".format(roipath))
            print("\t{0}".format(metapath))
    
        _, roiname = os.path.split(roipath)
                ## USe roiname in the accuracy tables

        # ----
        # Load and process labels
        meta = pd.read_csv(metapath)    
        resps = np.array(meta["resp"].tolist())
        trs = np.array(meta["TR"].tolist())
        
        # ----
        # Construct targets
        targets = construct_targets(resps=resps, trs=trs)
    
        # ----
        # Get the data, intial preprocessing
        Xsp = load_nii(roipath, sparse=True)
        Xsp = remove_invariant_features(Xsp, sparse=True)
        Xsp = Xsp[targets["trs"],:]

        if verbose:
            print("Before filtration.")
            print_target_info(targets)
            print_X_info(Xsp)

        # --
        # Filter...
        # --
        # By rt
        keepers = ["left", "right"]
        keep_lr = construct_filter(targets["resps"], keepers, True)
        targets = filter_targets(keep_lr, targets)
        Xsp = Xsp[keep_lr,:]
        
        if verbose:
            print("After filtration.")
            print_target_info(targets)
            print_X_info(Xsp)
        
        # --
        # Smooth (and desparse)
        X = smooth(Xsp.todense(), tr=1.5, ub=0.06, lb=0.001)

        # ----
        # --
        # CV setup
        nrow, ncol = X.shape
        cv = KFold(nrow, n_folds=5, indices=True)
    
        # --
        # clf setup
        clf = GradientBoostingClassifier(
                n_estimators=100, learning_rate=1.0, 
                max_depth=1, random_state=0)
    
        # --
        if verbose:
            print("Classifying...")
            print_label_counts(targets["resps"])
            print_clf_info(clf)

        truths, predictions = simpleCV(X, targets["resps"], 
                cv, clf, verbose)
    
        # ----
        # Save the results
        i = 0
        for truth, prediction in zip(truths, predictions):
            accuracy = accuracy_score(truth, prediction)
            overall_accuracy.append(accuracy)
        
            save_accuracy_table(
                table, 
                [roi, roiname, "cv_"+str(i)], 
                accuracy)
    
            if verbose:
                print("Processing the CV results...")
                print("\tFor CV {0}, accuracy was {1}".format(i, accuracy))
                print("\tFull report:")
                print(classification_report(truth, prediction, 
                        target_names=sorted(np.unique(targets["resps"]))))
                i += 1

    omean = np.array(overall_accuracy).mean()
    save_accuracy_table(table, [roi, roi, "overall"], omean)
    
    if verbose:
        print("****")
        print("Overall accuracy for {1} was {0}".format(omean, roi))
        

if __name__ == "__main__":
    # ----
    # Experimental init
    
    # --
    # Exp globals
    ACCURACY_TABLE_NAME = "fh_motor_accuracy.txt"
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
    
    # --     
    # Pre-run cleanup
    reset_accuracy_table(ACCURACY_TABLE_NAME)
       
    # --
    # A little PFA to simplify the run loop...
    named_exp = partial(exp,  
            table=ACCURACY_TABLE_NAME,
            verbose=True)
    
    # ----
    # And go!
    [named_exp(roi) for roi in ROIS]