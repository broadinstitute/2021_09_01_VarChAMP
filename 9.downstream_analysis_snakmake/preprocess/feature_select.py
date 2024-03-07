"""Feature selection using pycytominer"""
import logging

import pandas as pd
from pycytominer.operations import correlation_threshold, variance_threshold

from .correct import find_feat_cols

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def select_features(dframe_path, feat_selected_path):
    """Run feature selection"""
    dframe = pd.read_parquet(dframe_path)
    features = find_feat_cols(dframe.columns)
    low_variance = variance_threshold(dframe, features)
    features = [f for f in features if f not in low_variance]
    logger.info("%d features removed by variance_threshold" % (len(low_variance)))
    high_corr = correlation_threshold(dframe, features)
    features = [f for f in features if f not in high_corr]
    logger.info("%d features removed by correlation_threshold" % (len(high_corr)))

    dframe.drop(columns=low_variance + high_corr, inplace=True)

    dframe.reset_index(drop=True).to_parquet(feat_selected_path)