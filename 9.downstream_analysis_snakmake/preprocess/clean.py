import sys
sys.path.append('..')
from utils import find_feat_cols, find_feat_cols_polars, find_meta_cols_polars

import pandas as pd 
import polars as pl
import logging

# logging.basicConfig(format='%(levelname)s:%(asctime)s:%(name)s:%(message)s', level=logging.WARN)
logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARN)


def clip_features(dframe, threshold):
    '''Clip feature values to a given magnitude'''
    feat_cols = find_feat_cols(dframe)
    counts = (dframe.loc[:, feat_cols].abs() > threshold).sum()[lambda x:x > 0]
    if len(counts) > 0:
        logger.info(f'Clipping {counts.sum()} values in {len(counts)} columns')
        dframe.loc[:, feat_cols].clip(-threshold, threshold, inplace=True)
    return dframe

def drop_outlier_feats(dframe: pd.DataFrame, threshold: float):
    '''Remove columns with 1 percentile of absolute values larger than threshold'''
    feat_cols = find_feat_cols(dframe)
    large_feat = dframe[feat_cols].abs().quantile(0.99) > threshold
    large_feat = set(large_feat[large_feat].index)
    keep_cols = [c for c in dframe.columns if c not in large_feat]
    num_ignored = dframe.shape[1] - len(keep_cols)
    logger.info(f'{num_ignored} ignored columns due to large values')
    dframe = dframe[keep_cols]
    return dframe, num_ignored


def outlier_removal(input_path: str, output_path: str):
    '''Remove outliers'''
    dframe = pd.read_parquet(input_path)
    dframe, _ = drop_outlier_feats(dframe, threshold=1e2)
    dframe = clip_features(dframe, threshold=1e2)
    dframe.to_parquet(output_path)

def clip_features_polar(lframe: pl.LazyFrame, threshold) -> pl.LazyFrame:
    '''Clip feature values to a given magnitude'''
    feat_cols = find_feat_cols_polars(lframe)
    clipped_frame = (
        lframe.with_columns(
            [
                pl.when(pl.col(col).abs() > threshold)
                .then(pl.lit(threshold) * pl.col(col).sign())
                .otherwise(pl.col(col))
                .alias(col)
                for col in feat_cols
            ]
        )
    )
    return clipped_frame

def drop_outlier_feats_polar(lframe: pl.LazyFrame, threshold: float) -> pl.LazyFrame:
    """
    Remove columns from a Polars LazyFrame where the 
    99th percentile of absolute values is larger than a threshold.
    """
    feat_cols = find_feat_cols_polars(lframe)
    meta_cols = find_meta_cols_polars(lframe)

    # Filter columns based on the condition
    def filter_columns(col_name: str):
        if (
            lframe.select(pl.col(col_name).abs().quantile(0.99, interpolation="higher"))
            .filter(pl.col(col_name) <= threshold)
        ).collect().shape[0] > 0:
            return True
        else: 
            return False

    feat_cols_filtered = [col for col in feat_cols if filter_columns(col)] 
    lframe_filtered = lframe.select(
        [meta_cols + feat_cols_filtered]
    )

    return lframe_filtered

def outlier_removal_polars(input_path: str, output_path: str):
    '''Remove outliers'''
    lframe = pl.scan_parquet(input_path)
    lframe = drop_outlier_feats_polar(lframe, threshold=1e2)
    lframe = clip_features_polar(lframe, threshold=1e2)
    lframe.collect().to_pandas()
    lframe.to_parquet(output_path, compression='gzip', index=False)