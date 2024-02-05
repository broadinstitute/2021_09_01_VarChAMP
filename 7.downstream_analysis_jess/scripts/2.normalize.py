'''
Perform batch correction.
'''
import pathlib

from concurrent import futures
from typing import Optional
import pandas as pd 
from tqdm import tqdm
from statsmodels.formula.api import ols
from sklearn.base import TransformerMixin
from pycytominer.operations.transform import RobustMAD
import time
from copairs.map import aggregate
from copairs.map import run_pipeline
import numpy as np
import polars as pl
from datetime import datetime

from utils import get_features, get_metadata

def subtract_well_mean(ann_df: pd.DataFrame) -> pd.DataFrame:
    """
    Subtract the mean of each feature per each well.

    Parameters
    ----------
    ann_df : pandas.DataFrame
        Dataframe with features and metadata.

    Returns
    -------
    pandas.DataFrame
        Dataframe with features and metadata, with each feature subtracted by the mean of that feature per well.
    """
    feature_cols = ann_df.filter(regex="^(?!Metadata_)").columns.to_list()

    def subtract_well_mean_parallel_helper(feature):
        return {feature: ann_df[feature] - ann_df.groupby("Metadata_Well")[feature].mean()}
    
    with futures.ThreadPoolExecutor() as executor:
        results = executor.map(subtract_well_mean_parallel_helper, feature_cols)

    for res in results:
        ann_df.update(pd.DataFrame(res))

    return ann_df

def regress_out_cell_counts(
    well_df: pd.DataFrame,
    sc_df: pd.DataFrame,
    cc_col: str,
    min_unique: int = 100,
    cc_rename: Optional[str] = None,
    inplace: bool = True,
) -> pd.DataFrame:
    """
    Regress out cell counts from all features in a dataframe.

    Parameters
    ----------
    well_df : pandas.core.frame.DataFrame
        DataFrame of well-level profiles.
    sc_df : pandas.core.frame.DataFrame
        DataFrame of single-cell profiles.
    cc_col : str
        Name of column containing cell counts.
    min_unique : int, optional
        Minimum number of unique feature values to perform regression.
    cc_rename : str, optional
        Name to rename cell count column to.
    inplace : bool, optional
        Whether to perform operation in place.

    Returns
    -------
    df : pandas.core.frame.DataFrame
    """
    df = well_df if inplace else well_df.copy()
    df_sc = sc_df if inplace else sc_df.copy()
 
    feature_cols = list(set(get_features(df)) & set(get_features(df_sc)))
    feature_cols = [
        feature for feature in feature_cols if df[feature].nunique() > min_unique
    ]

    def regress_out_cell_counts_parallel_helper(feature):
        model = ols(f"{feature} ~ {cc_col}", data=df).fit()
        return {feature: model.resid}

    with futures.ThreadPoolExecutor() as executor:
        results = executor.map(regress_out_cell_counts_parallel_helper, feature_cols)
    
    for res in results:
        [[feature, _]] = res.items() 
        new_df = df[['Metadata_Plate', 'Metadata_Well']]
        new_df = pd.concat([new_df, pd.DataFrame(res)])
        df_merged = df_sc[['Metadata_Plate', 'Metadata_Well', feature]].merge(new_df, 
                                                                              on=['Metadata_Plate', 'Metadata_Well'], 
                                                                              suffixes=("", "_mean"))
        df_sc[feature] = df_sc[feature] - df_merged[f'{feature}_mean']

    return df_sc

def apply_norm(normalizer: TransformerMixin, df: pd.DataFrame) -> pd.DataFrame:
    feat_cols = get_features(df)
    meta_cols = get_metadata(df)
    meta = df[meta_cols]

    normalizer.fit(df[feat_cols])
    norm_feats = normalizer.transform(df[feat_cols])
    norm_feats = pd.DataFrame(norm_feats,
                              index=df.index,
                              columns=feat_cols)
    df = pd.concat([meta, norm_feats], axis=1)
    return 

def prep_for_map(df_path: str, map_cols: [str]):

    # define filters
    q = pl.scan_parquet(df_path).filter(
        (pl.col("Metadata_node_type") != "TC") &  # remove transfection controls
        (pl.sum_horizontal(pl.col(map_cols).is_null()) == 0)  # remove any row with missing values for selected meta columns
        )
    
    # different data frames for metadata and profiling data
    meta_cols = q.select(map_cols)
    meta_cols = meta_cols.collect().to_pandas()

    feat_col = [i for i in q.columns if "Metadata_" not in i] 
    q = q.select(feat_col)
    feat_cols = q.collect().to_pandas()

    map_input = {'meta': meta_cols, 'feats': feat_cols}

    return map_input


def main():
    epsilon_mad = 0.0
    batch_name = 'B1A1R1'

    # Data directories
    data_dir = pathlib.Path("/dgx1nas1/storage/data/jess/varchamp/sc_data/processed_profiles").resolve(strict=True)
    result_dir = data_dir

    # Input file paths
    anno_file = pathlib.Path(data_dir / f"{batch_name}_annotated.parquet")
    df_well_path = f'/dgx1nas1/storage/data/jess/varchamp/well_data/{batch_name}_well_level.parquet'

    # Output file paths
    well_file = pathlib.Path(result_dir / f"{batch_name}_annotated_corrected_wellmean.parquet")
    cc_file = pathlib.Path(result_dir / f"{batch_name}_annotated_corrected_cc.parquet")
    norm_file = pathlib.Path(result_dir / f"{batch_name}_annotated_corrected_normalized.parquet")

    # Set paramters for mAP
    pos_sameby = ['Metadata_allele']
    pos_diffby = ['Metadata_Plate', 'Metadata_Well']
    neg_sameby = ['Metadata_Plate']
    neg_diffby = ['Metadata_allele']
    null_size = 10000

    map_cols = list(set(pos_sameby + pos_diffby + neg_sameby + neg_diffby))

    start = time.perf_counter()
    map_input = prep_for_map(anno_file, map_cols)
    end = time.perf_counter()
    print(f'Polars runtime: {end-start}.')

    # compute map
    start = time.perf_counter()
    map_result = run_pipeline(map_input['meta'], map_input['feats'], pos_sameby, pos_diffby, neg_sameby, neg_diffby, null_size)
    end = time.perf_counter()
    print(f'map runtime: {end-start}.')

    # Combine scores from samples with the same Metadata_Sample_Unique
    map_result_agg = aggregate(map_result, 'Metadata_Sample_Unique', threshold = 0.05) # Need to change second parameter to match my exp design
    map_result_agg[['above_p_threshold', 'above_q_threshold']].value_counts()

    # Well position correction
    start = time.perf_counter()
    df_well_corrected = subtract_well_mean(pd.read_parquet(anno_file))
    end = time.perf_counter()
    print(f'Well position correction runtime: {end-start}.')
    # df_well_corrected.to_parquet(path=well_file, compression="gzip", index=False)
    
    # Cell count regression
    start = time.perf_counter()
    df_well_level = pd.read_parquet(df_well_path)
    plate_list = df_well_level['Metadata_Plate'].unique().tolist()
    df_cc_corrected = regress_out_cell_counts(df_well_level, df_well_corrected,'Metadata_Object_Count')
    end = time.perf_counter()
    print(f'Cell count regression runtime: {end-start}.')
    # df_cc_corrected.to_parquet(path=cc_file, compression="gzip", index=False)
    print(f"\n Position and cell count corrected profiles saved in: {cc_file}")


    def robust_mad_parallel_helper(plate):
        df_plate = df_cc_corrected[df_cc_corrected['Metadata_Plate']==plate].copy()
        normalizer = RobustMAD(epsilon_mad)
        df_plate = apply_norm(normalizer, df_plate)
        return df_plate
    
    start = time.perf_counter()
    with futures.ThreadPoolExecutor() as executor:
        results = executor.map(robust_mad_parallel_helper, plate_list)
    end = time.perf_counter()
    print(f'RobustMAD runtime: {end-start} secs.')

    result_list = [res for res in results]
    df_norm = pd.concat(result_list, ignore_index=True)
    # df_norm.to_parquet(path=norm_file, compression="gzip", index=False)

if __name__ == '__main__':
    main()