import os

import pandas as pd

import config

"""
A quick script to create the development dataframe for some EDA and
random participant selection for the train/test split. Made decision to
combine AVEC's pre-identified test and train sets (all having depression
labels) to ensure maximum training size among  stratified and balanced classes
given audio segmentation challenges.
"""

df_train = pd.read_csv(
    os.path.join(
        config.BASE_DIR, "data", "labels", "train_split_Depression_AVEC2017.csv"
    )
)

df_test = pd.read_csv(
    os.path.join(config.BASE_DIR, "data", "labels", "dev_split_Depression_AVEC2017.csv")
)

df_dev = pd.concat([df_train, df_test], axis=0)
