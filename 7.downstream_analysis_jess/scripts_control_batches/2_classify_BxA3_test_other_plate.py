# The B4A3 and B6A3 batches contain 8 different controls, each repeated 48X. 
# There is one WT-VAR pair (ALK) (positive protein loc control)
# The objective here is to assess the influence of well position effect within plates

import pandas as pd
import polars as pl
import numpy as np
import pathlib
from tqdm import tqdm
import os

import warnings
warnings.filterwarnings("ignore")

from sklearn.metrics import f1_score
import xgboost as xgb
from itertools import combinations


def classifier(all_profiles_train, all_profiles_test, feat_col, target='Label', stratify_label=None):
    '''
    This function runs classification.
    '''
    X_train, y_train = all_profiles_train[feat_col], all_profiles_train[[target]]
    X_test, y_test = all_profiles_test[feat_col], all_profiles_test[[target]]
    
    model = xgb.XGBClassifier(objective='binary:logistic',
                        n_estimators=150,
                        tree_method='hist',
                        learning_rate = 0.05,
                        device="cuda:7",
                        random_state=42).fit(X_train, y_train, verbose=False)

    preds = model.predict(X_test)

    # Store feature importance
    feat_importances = pd.Series(
        model.feature_importances_, index=X_train.columns
    )
    
    # Evaluate with metrics
    f1score_macro = f1_score(y_test, preds, average="macro")
      
    return feat_importances, f1score_macro



def experimental_group_runner(var_profiles, ref_profiles, var_group, ref_group, data_dir, feat_col, batch_name='', 
    protein_prefix='protein', feature_type='_normalized_feature_selected'):
    '''
    This function runs the reference v.s. variants experiments. 
    '''
    ref_list = []
    var_list = []
    feat_list = []
    f1score_macro_list = []
    ref_cc_list = []
    var_cc_list = []
    
    var_profiles['Label'] = 1
    ref_profiles['Label'] = 0

    for var_key in tqdm(var_group.keys()):
        var_profs = var_profiles.loc[var_group[var_key]] 
        var_profs = pl.from_pandas(var_profs)
        
        for ref_key in ref_group.keys():
            ref_profs = ref_profiles.loc[ref_group[ref_key]]
            ref_profs = pl.from_pandas(ref_profs)
            
            # split data
            ref_train = ref_profs.filter(pl.col("Metadata_Batch") == 4)
            ref_test = ref_profs.filter(pl.col("Metadata_Batch") == 6)

            var_train = var_profs.filter(pl.col("Metadata_Batch") == 4)
            var_test = var_profs.filter(pl.col("Metadata_Batch") == 6)
            
            all_profiles_train = pl.concat([ref_train, var_train], how="vertical").to_pandas()
            all_profiles_test = pl.concat([ref_test, var_test], how="vertical").to_pandas()
            
            # make classifier
            feat_importances, f1score_macro = classifier(all_profiles_train, all_profiles_test, feat_col)
                
            feat_list.append(feat_importances)
            f1score_macro_list.append(f1score_macro)
            ref_list.append(ref_key)
            var_list.append(var_key)
            ref_cc_list.append(ref_profs.shape[0])
            var_cc_list.append(var_profs.shape[0])


    # Compile results
    df_feat_one = pd.DataFrame({"Reference_Well": ref_list, "Variant_Well": var_list})
    df_feat_two = pd.DataFrame(feat_list)
    df_feat = pd.concat([df_feat_one, df_feat_two], axis=1)

    df_feat.to_csv(f"{data_dir}/{batch_name}_{protein_prefix}_feat_importance{feature_type}.csv", index=False)
    
    result_csv = pd.DataFrame(
    {
        "Reference_Well": ref_list,
        "Variant_Well": var_list,
        "F1_Score": f1score_macro_list,
        "Reference_CC": ref_cc_list,
        "Variant_CC": var_cc_list
    }
    )
    result_csv.to_csv(f"{data_dir}/{batch_name}_{protein_prefix}_f1score{feature_type}.csv",index=False)



def control_group_runner(controls, control_group, data_dir, feat_col, batch_name='', 
    protein_prefix='protein', feature_type='_normalized_feature_selected'):
    '''
    This function runs the null control experiments. 
    '''
    w1_list = []
    w2_list = []
    feat_list = []
    f1score_macro_list = []
    w1_cc_list = []
    w2_cc_list = []
    
    # get all possible pairs of wells
    well_pairs = combinations(list(control_group.keys()), 2)
    
    for (idx_one, idx_two) in tqdm(well_pairs):
        well_one = controls.loc[control_group[idx_one]].reset_index(drop=True)
        well_one["Label"] = 1
        well_two = controls.loc[control_group[idx_two]].reset_index(drop=True)
        well_two["Label"] = 0
        
        well_one = pl.from_pandas(well_one)
        well_two = pl.from_pandas(well_two)
        
        # split data 
        w1_train = well_one.filter(pl.col("Metadata_Batch") == 4)
        w1_test = well_one.filter(pl.col("Metadata_Batch") == 6)
        
        w2_train = well_two.filter(pl.col("Metadata_Batch") == 4)
        w2_test = well_two.filter(pl.col("Metadata_Batch") == 6)
        
        all_profiles_train = pl.concat([w1_train, w2_train], how="vertical").to_pandas()
        all_profiles_test = pl.concat([w1_test, w2_test], how="vertical").to_pandas()
        
        # make classifier
        feat_importances, f1score_macro = classifier(all_profiles_train, all_profiles_test, feat_col)
            
        feat_list.append(feat_importances)
        f1score_macro_list.append(f1score_macro)
        w1_list.append(idx_one)
        w2_list.append(idx_two)
        w1_cc_list.append(well_one.shape[0])
        w2_cc_list.append(well_two.shape[0])
    
    
    # Compile results
    df_feat_one = pd.DataFrame({"Well_One": w1_list, "Well_Two": w2_list})
    df_feat_two = pd.DataFrame(feat_list)
    df_feat = pd.concat([df_feat_one, df_feat_two], axis=1)

    df_feat.to_csv(f"{data_dir}/{batch_name}_{protein_prefix}_control_feat_importance{feature_type}.csv",index=False)

    result_csv = pd.DataFrame({
        "Well_One": w1_list,
        "Well_Two": w2_list,
        "F1_Score": f1score_macro_list,
        "Well_One_CC": w1_cc_list,
        "Well_Two_CC": w2_cc_list
        })
    result_csv.to_csv(f"{data_dir}/{batch_name}_{protein_prefix}_control_f1score{feature_type}.csv",index=False)
    
    
def null_group_runner(controls, control_group, data_dir, feat_col, batch_name='', 
    protein_prefix='protein', feature_type='_normalized_feature_selected'):
    '''
    This function runs the null control experiments. 
    '''
    w1_list = []
    w2_list = []
    feat_list = []
    f1score_macro_list = []
    w1_cc_list = []
    w2_cc_list = []
    
    # get all possible pairs of wells
    well_pairs = combinations(list(control_group.keys()), 2)
    
    for (idx_one, idx_two) in tqdm(well_pairs):
        well_one = controls.loc[control_group[idx_one]].reset_index(drop=True)
        well_one["Label"] = 1
        well_two = controls.loc[control_group[idx_two]].reset_index(drop=True)
        well_two["Label"] = 0
        
        well_one = pl.from_pandas(well_one)
        well_two = pl.from_pandas(well_two)
        
        # split data 
        w1_train = well_one.filter(pl.col("Metadata_Batch") == 4)
        w1_test = well_one.filter(pl.col("Metadata_Batch") == 6)
        
        w2_train = well_two.filter(pl.col("Metadata_Batch") == 4)
        w2_test = well_two.filter(pl.col("Metadata_Batch") == 6)
        
        # shuffle the training labels
        all_profiles_train = pl.concat([w1_train, w2_train], how="vertical")
        all_profiles_train = all_profiles_train.with_columns(pl.col("Label").shuffle(seed=123).alias("Label")).to_pandas()
        all_profiles_test = pl.concat([w1_test, w2_test], how="vertical").to_pandas()
        
        # make classifier
        feat_importances, f1score_macro = classifier(all_profiles_train, all_profiles_test, feat_col)
            
        feat_list.append(feat_importances)
        f1score_macro_list.append(f1score_macro)
        w1_list.append(idx_one)
        w2_list.append(idx_two)
        w1_cc_list.append(well_one.shape[0])
        w2_cc_list.append(well_two.shape[0])
    
    
    # Compile results
    df_feat_one = pd.DataFrame({"Well_One": w1_list, "Well_Two": w2_list})
    df_feat_two = pd.DataFrame(feat_list)
    df_feat = pd.concat([df_feat_one, df_feat_two], axis=1)

    df_feat.to_csv(f"{data_dir}/{batch_name}_{protein_prefix}_control_feat_importance{feature_type}.csv",index=False)

    result_csv = pd.DataFrame({
        "Well_One": w1_list,
        "Well_Two": w2_list,
        "F1_Score": f1score_macro_list,
        "Well_One_CC": w1_cc_list,
        "Well_Two_CC": w2_cc_list
        })
    result_csv.to_csv(f"{data_dir}/{batch_name}_{protein_prefix}_control_f1score{feature_type}.csv",index=False)
    
    
def main():
    
    os.environ["CUDA_VISIBLE_DEVICES"]="6,7"
    
    result_dir = pathlib.Path(f'/dgx1nas1/storage/data/jess/varchamp/sc_data/classification_results/Rep_Ctrls_scen2')
    result_dir.mkdir(exist_ok=True)
    
    data_path = "/dgx1nas1/storage/data/jess/varchamp/sc_data/processed_profiles/Rep_Ctrls/annotated_normalized_featselected.parquet"
    
    # Concatenate files from both batches
    sc_profiles = pl.scan_parquet(data_path)
    sc_profiles = sc_profiles.filter(pl.col("Metadata_SYMBOL") == "ALK")
    
        
    # Get all metadata variable names  
    feat_col = [i for i in sc_profiles.columns if "Metadata_" not in i]
    
    # Include only GFP features for protein channel 
    feat_cols_protein = [
        i
        for i in feat_col
        if ("GFP" in i)
        and ("DNA" not in i)
        and ("AGP" not in i)
        and ("Mito" not in i)
    ]
    
    # Select non-protein channel features, where GFP does not exist in feat_cols
    feat_cols_non_protein = [i for i in feat_col if "GFP" not in i]

    # Define labels for classification
    variants = sc_profiles.filter(pl.col("Metadata_allele") == 'ALK_R1275Q').collect().to_pandas()
    var_well_group = variants.groupby("Metadata_Well").groups

    references = sc_profiles.filter(pl.col("Metadata_allele") == 'ALK_').collect().to_pandas()
    ref_well_group = references.groupby("Metadata_Well").groups
    
    # Run classification
    # control_group_runner(
    #     references, 
    #     ref_well_group, 
    #     result_dir, 
    #     feat_cols_protein, 
    #     batch_name='Rep_Ctrls_scen2',
    #     protein_prefix='protein_REF')
    # print("Finish building null for REF well with protein features")
    
    # control_group_runner(
    #     variants, 
    #     var_well_group, 
    #     result_dir, 
    #     feat_cols_protein, 
    #     batch_name='Rep_Ctrls_scen2',
    #     protein_prefix='protein_VAR')
    # print("Finish building null for VAR well with protein features")

    # experimental_group_runner(
    #     var_profiles = variants, 
    #     ref_profiles = references,
    #     var_group = var_well_group, 
    #     ref_group = ref_well_group,
    #     data_dir = result_dir, 
    #     feat_col = feat_cols_protein, 
    #     batch_name = 'Rep_Ctrls_scen2',
    #     protein_prefix = 'protein')
    # print("Finish WT-VAR classification with protein features")
    
    # control_group_runner(
    #     references, 
    #     ref_well_group, 
    #     result_dir, 
    #     feat_cols_non_protein, 
    #     batch_name='Rep_Ctrls_scen2',
    #     protein_prefix='non_protein_REF')
    # print("Finish building null for REF well with non-protein features")
    
    # control_group_runner(
    #     variants, 
    #     var_well_group, 
    #     result_dir, 
    #     feat_cols_non_protein, 
    #     batch_name='Rep_Ctrls_scen2',
    #     protein_prefix='non_protein_VAR')
    # print("Finish building null for VAR well with non-protein features")
    
    # experimental_group_runner(
    #     var_profiles = variants, 
    #     ref_profiles = references,
    #     var_group = var_well_group, 
    #     ref_group = ref_well_group,
    #     data_dir = result_dir, 
    #     feat_col = feat_cols_non_protein, 
    #     batch_name = 'Rep_Ctrls_scen2',
    #     protein_prefix = 'non_protein')
    # print("Finish WT-VAR classification with non-protein features")
    
    print("Start computing null")
    null_group_runner(
        references, 
        ref_well_group, 
        result_dir, 
        feat_cols_protein, 
        batch_name='Rep_Ctrls_scen2',
        protein_prefix='protein_NULL')
    print("Finish building NULL with protein features")
    
    null_group_runner(
        references, 
        ref_well_group, 
        result_dir, 
        feat_cols_non_protein, 
        batch_name='Rep_Ctrls_scen2',
        protein_prefix='non_protein_NULL')
    print("Finish building NULL with non-protein features")
    
    
if __name__ == '__main__':
    main()