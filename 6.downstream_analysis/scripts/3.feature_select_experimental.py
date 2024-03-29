import pathlib

import pandas as pd
from tqdm import tqdm
# ignore mix type warnings from pandas
import warnings
warnings.filterwarnings("ignore")

from pycytominer import feature_select

def main():   
    # Data directory
    data_dir = pathlib.Path("/dgx1nas1/storage/data/sam/processed").resolve(strict=True)
    result_dir = pathlib.Path(data_dir / 'feat_selected/')
    result_dir.mkdir(exist_ok=True)

    # Input path
    batch_name = '2023_05_30_B1A1R1'
    norm_path = pathlib.Path(data_dir / batch_name + '_annotated_corrected_normalized.parquet')

    # Output path
    feat_path_1 = pathlib.Path(result_dir / batch_name + '_annotated_normalized_feat_selected_1.parquet')
    feat_path_2 = pathlib.Path(result_dir / batch_name + '_annotated_normalized_feat_selected_2.parquet')
    feat_path_3 = pathlib.Path(result_dir / batch_name + '_annotated_normalized_feat_selected_3.parquet')


    print('Step 1 starting...')
    # Perform batch level feature selection 
    feature_select(
                    profiles=norm_path,
                    features="infer",
                    image_features=False,
                    samples="all",
                    operation=["variance_threshold", "blocklist", "drop_na_columns"],
                    output_file=feat_path_1,
                    output_type='parquet',
                    compression_options="gzip",
                )
    print('Step 1 completed.')

    print('Step 2: Noise removal starting...')
    feature_select(
                    profiles=norm_path,
                    features="infer",
                    image_features=False,
                    samples="all",
                    operation="noise_removal",
                    output_file=feat_path_2,
                    output_type='parquet',
                    compression_options="gzip",
                )
    print('Step 2: Noise removal completed.')

    print('Step 3: corr_threshold starting...')
    feature_select(
                    profiles=norm_path,
                    features="infer",
                    image_features=False,
                    samples="all",
                    operation="correlation_threshold",
                    output_file=feat_path_3,
                    output_type='parquet',
                    compression_options="gzip",
                )
    print('Step 3: corr_threshold completed.')

if __name__ == "__main__":
    main()