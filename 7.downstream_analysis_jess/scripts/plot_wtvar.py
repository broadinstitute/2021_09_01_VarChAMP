'''
Plot middle site from all images for all WT-VAR pairs
'''

import polars as pl
import numpy as np
from sh import aws
import os
from skimage.io import imread
from matplotlib import pyplot as plt
import matplotlib as mpl
import random
import math
from tqdm import tqdm

# Define mapping between simple names and folder names
batch_dict = {"B4A3R1": "2023-12-15_B4A3R1", 
              "B6A3R2": "2023-12-21_B6A3R2", 
              "B7A1R1": "2024_01_23_Batch_7",
              "B7A2R1": "2024_01_23_Batch_7",
              "B8A1R2": "2024_02_06_Batch_8",
              "B8A2R2": "2024_02_06_Batch_8"}

letter_dict = {
    "A": "01",
    "B": "02",
    "C": "03",
    "D": "04",
    "E": "05",
    "F": "06",
    "G": "07",
    "H": "08",
    "I": "09",
    "J": "10",
    "K": "11",
    "L": "12",
    "M": "13",
    "N": "14",
    "O": "15",
    "P": "16",
}

plate_dict = {
    "B4-P1T1": "2023-12-15_B4A3R1_P1T1__2023-12-15T08_49_02-Measurement1",
    "B4-P1T2": "2023-12-15_B4A3R1_P1T2__2023-12-15T10_35_54-Measurement1",
    "B4-P1T3": "2023-12-18_B4A3R1_P1T3__2023-12-18T08_29_45-Measurement1",
    "B4-P1T4": "2023-12-18_B4A3R1_P1T4__2023-12-18T10_17_07-Measurement1",
    
    "B6-P1T1": "2023-12-21_B6A3R2_P1T1__2023-12-21T08_28_37-Measurement1",
    "B6-P1T2": "2023-12-21_B6A3R2_P1T2__2023-12-21T10_11_34-Measurement1",
    "B6-P1T3": "2023-12-21_B6A3R2_P1T3__2023-12-21T11_57_14-Measurement1",
    "B6-P1T4": "2023-12-21_B6A3R2_P1T4__2023-12-21T13_40_04-Measurement1",
    
    "B7A1R1_P1": {"T1": "2024_01_17_B7A1R1_P1T1__2024_01_17T08_35_58_Measurement_1",
                  "T2": "2024_01_17_B7A1R1_P1T2__2024_01_17T10_13_45_Measurement_1",
                  "T3": "2024_01_17_B7A1R1_P1T3__2024_01_17T11_58_08_Measurement_1",
                  "T4": "2024_01_17_B7A1R1_P1T4__2024_01_17T13_45_14_Measurement_1"},
    
    "B7A1R1_P2": {"T1": "2024_01_17_B7A1R1_P2T1__2024_01_17T15_33_09_Measurement_1",
                  "T2": "2024_01_17_B7A1R1_P2T2__2024_01_18T08_25_01_Measurement_1",
                  "T3": "2024_01_17_B7A1R1_P2T3__2024_01_18T10_47_36_Measurement_1",
                  "T4": "2024_01_17_B7A1R1_P2T4__2024_01_18T12_48_20_Measurement_1"},
        
    "B7A1R1_P3": {"T1": "2024_01_18_B7A1R1_P3T1__2024_01_18T14_27_08_Measurement_1",
                  "T2": "2024_01_19_B7A1R1_P3T2__2024_01_19T08_23_30_Measurement_1",
                  "T3": "2024_01_19_B7A1R1_P3T3__2024_01_19T10_01_45_Measurement_1",
                  "T4": "2024_01_19_B7A1R1_P3T4__2024_01_19T12_00_10_Measurement_1"},
            
    "B7A1R1_P4": {"T1": "2024_01_19_B7A1R1_P4T1__2024_01_19T13_50_55_Measurement_1",
                  "T2": "2024_01_23_B7A1R1_P4T2__2024_01_23T10_13_00_Measurement_1",
                  "T3": "2024_01_22_B7A1R1_P4T3__2024_01_22T08_37_41_Measurement_1",
                  "T4": "2024_01_22_B7A1R1_P4T4__2024_01_22T10_27_16_Measurement_1"},
    
    "B7A2R1_P1": {"T1": "2024_01_22_B7A2R1_P1T1__2024_01_22T12_13_13_Measurement_1",
                  "T2": "2024_01_22_B7A2R1_P1T2__2024_01_22T13_52_24_Measurement_1",
                  "T3": "2024_01_22_B7A2R1_P1T3__2024_01_22T15_29_31_Measurement_1",
                  "T4": "2024_01_23_B7A2R1_P1T4__2024_01_23T08_28_07_Measurement_1"},
    
    "B8A1R2_P1": {"T1": "2024_01_31_B8A1R2_P1T1__2024_01_31T10_11_57_Measurement_1",
                  "T2": "2024_01_31_B8A1R2_P1T2__2024_01_31T08_35_51_Measurement_2",
                  "T3": "2024_01_31_B8A1R2_P1T3__2024_01_31T12_09_14_Measurement_1",
                  "T4": "2024_01_31_B8A1R2_P1T4__2024_01_31T14_02_18_Measurement_2"},
    
    "B8A1R2_P2": {"T1": "2024_01_31_B8A1R2_P2T1__2024_01_31T15_41_23_Measurement_1",
                  "T2": "2024_02_01_B8A1R2_P2T2__2024_02_01T10_23_20_Measurement_2",
                  "T3": "2024_02_01_B8A1R2_P2T3__2024_02_01T12_16_30_Measurement_4",
                  "T4": "2024_02_01_B8A1R2_P2T4__2024_02_01T14_05_52_Measurement_1"},
        
    "B8A1R2_P3": {"T1": "2024_02_02_B8A1R2_P3T1__2024_02_02T08_32_30_Measurement_2",
                  "T2": "2024_02_02_B8A1R2_P3T2__2024_02_02T10_08_05_Measurement_1",
                  "T3": "2024_02_02_B8A1R2_P3T3__2024_02_02T11_58_46_Measurement_2",
                  "T4": "2024_02_02_B8A1R2_P3T4__2024_02_02T13_51_50_Measurement_1"},
            
    "B8A1R2_P4": {"T1": "2024_02_02_B8A1R2_P4T1__2024_02_02T15_32_28_Measurement_1",
                  "T2": "2024_02_05_B8A1R2_P4T2__2024_02_05T08_22_47_Measurement_2",
                  "T3": "2024_02_05_B8A1R2_P4T3__2024_02_05T10_00_30_Measurement_1",
                  "T4": "2024_02_05_B8A1R2_P4T4__2024_02_05T11_38_50_Measurement_1"},
    
    "B8A2R2_P1": {"T1": "2024_02_05_B8A2R2_P1T1__2024_02_05T13_23_28_Measurement_1",
                  "T2": "2024_02_05_B8A2R2_P1T2__2024_02_05T15_18_32_Measurement_1",
                  "T3": "2024_02_06_B8A2R2_P1T3__2024_02_06T08_23_49_Measurement_1",
                  "T4": "2024_02_06_B8A2R2_P1T4__2024_02_06T10_18_16_Measurement_1"},
    
    "B7-P1T1": "2024_01_17_B7A1R1_P1T1__2024_01_17T08_35_58_Measurement_1",
    "B7-P1T2": "2024_01_17_B7A1R1_P1T2__2024_01_17T10_13_45_Measurement_1",
    "B7-P1T3": "2024_01_17_B7A1R1_P1T3__2024_01_17T11_58_08_Measurement_1",
    "B7-P1T4": "2024_01_17_B7A1R1_P1T4__2024_01_17T13_45_14_Measurement_1",
    
    "B7-P3T1": "2024_01_18_B7A1R1_P3T1__2024_01_18T14_27_08_Measurement_1",
    "B7-P3T2": "2024_01_19_B7A1R1_P3T2__2024_01_19T08_23_30_Measurement_1",
    "B7-P3T3": "2024_01_19_B7A1R1_P3T3__2024_01_19T10_01_45_Measurement_1",
    "B7-P3T4": "2024_01_19_B7A1R1_P3T4__2024_01_19T12_00_10_Measurement_1",
    
    "B7-A2T1": "2024_01_22_B7A2R1_P1T1__2024_01_22T12_13_13_Measurement_1",
    "B7-A2T2": "2024_01_22_B7A2R1_P1T2__2024_01_22T13_52_24_Measurement_1",
    "B7-A2T3": "2024_01_22_B7A2R1_P1T3__2024_01_22T15_29_31_Measurement_1",
    "B7-A2T4": "2024_01_23_B7A2R1_P1T4__2024_01_23T08_28_07_Measurement_1",
    
    "B8-P1T1": "2024_01_31_B8A1R2_P1T1__2024_01_31T10_11_57_Measurement_1",
    "B8-P1T2": "2024_01_31_B8A1R2_P1T2__2024_01_31T08_35_51_Measurement_2",
    "B8-P1T3": "2024_01_31_B8A1R2_P1T3__2024_01_31T12_09_14_Measurement_1",
    "B8-P1T4": "2024_01_31_B8A1R2_P1T4__2024_01_31T14_02_18_Measurement_2",
    
    "B8-P3T1": "2024_02_02_B8A1R2_P3T1__2024_02_02T08_32_30_Measurement_2",
    "B8-P3T2": "2024_02_02_B8A1R2_P3T2__2024_02_02T10_08_05_Measurement_1",
    "B8-P3T3": "2024_02_02_B8A1R2_P3T3__2024_02_02T11_58_46_Measurement_2",
    "B8-P3T4": "2024_02_02_B8A1R2_P3T4__2024_02_02T13_51_50_Measurement_1",
    
    "B8-A2T1": "2024_02_05_B8A2R2_P1T1__2024_02_05T13_23_28_Measurement_1",
    "B8-A2T2": "2024_02_05_B8A2R2_P1T2__2024_02_05T15_18_32_Measurement_1",
    "B8-A2T3": "2024_02_06_B8A2R2_P1T3__2024_02_06T08_23_49_Measurement_1",
    "B8-A2T4": "2024_02_06_B8A2R2_P1T4__2024_02_06T10_18_16_Measurement_1"
}

channel_dict = {
    "DAPI": "1",
    "GFP": "2",
    "AGP": "3",
    "Mito": "4",
    "Brightfield1": "5",
    "Brightfield2": "6",
    "Brightfield": "7",
}


def plotMultiImages(df, sel_channel, max_intensity, n_rows, display=True, plotpath=""):
    
    # Determine the layout of the subplots
    n_cols = math.ceil(df.shape[0]/n_rows)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 6 * n_rows))
    axes = axes.ravel()
    counter = 0
    
    imgs = df.to_dicts()
    for img in imgs:
        # parameters from df: sel_batch, sel_plate, site, well, rep
        sel_batch = img['Batch']
        sel_plate = img['Plate']
        site = img['Site']
        well = img['Well']
        rep = img['Replicate']
        allele = img['Allele']
        
        # construct image name and aws path
        letter = well[0]
        col = well[1:3]
        batch = batch_dict[sel_batch]
        row = letter_dict[letter]
        plate = plate_dict[sel_plate]
        
        if type(plate) == dict:
            plate = plate[rep]

        channel = channel_dict[sel_channel]
        
        plot_label = f"{sel_channel}: {sel_plate}, {rep}, {site}, {well}, {allele}"
        
        if sel_channel == "GFP":
            cmap = mpl.colors.LinearSegmentedColormap.from_list("green_cmap", ["#000","#65fe08"])
        elif sel_channel == "DAPI":
            cmap = mpl.colors.LinearSegmentedColormap.from_list("green_cmap", ["#000","#0000FF"])
        elif sel_channel == "Mito":
            cmap = mpl.colors.LinearSegmentedColormap.from_list("green_cmap", ["#000","#FF0000"]) 
        elif sel_channel == "AGP":
            cmap = mpl.colors.LinearSegmentedColormap.from_list("green_cmap", ["#000","#FFFF00"]) 
        else:
            cmap = "gray"

        img_nm = f"r{row}c{col}f{site}p01-ch{channel}sk1fk1fl1.tiff"

        aws_path = f"s3://cellpainting-gallery/cpg0020-varchamp/broad/images/{batch}/images/{plate}/Images/{img_nm}"
        dgx_path = (
            f"/dgx1nas1/storage/data/jess/varchamp/images/{sel_batch}{rep}/{sel_plate}"
        )

        # construct folder path in DGX
        os.makedirs(dgx_path, exist_ok=True)

        # download image if it doesn't already exist
        if not os.path.isfile(f"{dgx_path}/{img_nm}"):
            aws("s3", "cp", aws_path, f"{dgx_path}/{img_nm}")

        # read tiff into numpy array
        img = imread(f"{dgx_path}/{img_nm}", as_gray=True)
        
        # Plotting the image
        ax = axes[counter]
        if isinstance(max_intensity, int):
            im = ax.imshow(img, vmin=0, vmax=max_intensity, cmap=cmap)
        else:
            int_perc = np.percentile(img, max_intensity*100)
            im = ax.imshow(img, vmin=0, vmax=int_perc, cmap=cmap)
            
        ax.axis("off")
        ax.text(20, 30, plot_label, color='white', bbox=dict(facecolor='black', alpha=0.5, linewidth=2))
        
        int_95 = str(int(round(np.percentile(img, 95))))
        ax.text(0.95, 0.05, int_95, color='white', fontsize=20,
        verticalalignment='bottom', horizontalalignment='right', transform=ax.transAxes)
        
        # increase axis index
        counter = counter + 1

    # display plot
    plt.tight_layout()
    
    if display:
        plt.show()
    else:
        plt.savefig(plotpath, dpi=300, bbox_inches='tight')
        plt.close(fig)


def main():
    # Filepaths
    pm_dir = "/dgx1nas1/storage/data/jess/varchamp/platemaps"
    metrics_dir = "/dgx1nas1/storage/data/jess/varchamp/sc_data/classification_results/B7B8_1percent"
    
    # Read in summary metrics
    metrics_wtvar = pl.read_csv(f"{metrics_dir}/metrics_summary.csv")
    local_wtvar = metrics_wtvar.filter(pl.col("Classifier_type") == "localization")
    local_wtvar = local_wtvar.sort(pl.col("Macro_F1_mean"), descending=True)

    # Format all platemaps
    pms = ["B7A1R1_P1.txt", "B7A1R1_P2.txt", "B7A1R1_P3.txt", "B7A1R1_P4.txt", "B7A2R1_P1.txt", "B8A1R2_P1.txt", "B8A1R2_P2.txt", "B8A1R2_P3.txt", "B8A1R2_P4.txt", "B8A2R2_P1.txt"]
    pm_dfs = []
    for pm in pms:
        try:
            temp = pl.read_csv(f"{pm_dir}/{pm}", separator="\t").select(['plate_map_name', 'well_position', 'control_type', 'gene_allele'])
            pm_dfs.append(temp)
        except Exception as e:
            print("Error reading {pm}: {e}")
    pm_df = pl.concat(pm_dfs).rename({"well_position": "Well", "plate_map_name": "Plate", "gene_allele": "Allele"}).with_columns(
        pl.lit("05").alias("Site"),
        pl.col("Plate").str.slice(0,6).alias("Batch")
    )
    rep_df = pl.DataFrame({
        "Batch": ["B7A1R1", "B7A1R1", "B7A1R1", "B7A1R1", 
                "B7A2R1", "B7A2R1", "B7A2R1", "B7A2R1", 
                "B8A1R2", "B8A1R2", "B8A1R2", "B8A1R2",
                "B8A2R2", "B8A2R2", "B8A2R2", "B8A2R2"],
        "Replicate": ["T1", "T2", "T3", "T4",
                    "T1", "T2", "T3", "T4",
                    "T1", "T2", "T3", "T4",
                    "T1", "T2", "T3", "T4"]
    })
    pm_df = pm_df.join(rep_df, on="Batch")
    
    
    
    # Plot images for each WT-VAR pair
    var_alleles = local_wtvar.select("allele_0").to_series().to_list()
    plot_dir = "/dgx1nas1/storage/data/jess/varchamp/images/B7B8_1percent_wtvar"

    for var_allele in tqdm(var_alleles):
        gfp_nm = f"{var_allele}_GFP.png"
        mito_nm = f"{var_allele}_Mito.png"
        
        wt_allele = var_allele.split("_")[0]
        plot_img = pm_df.filter(((pl.col("Allele") == var_allele) | (pl.col("Allele") == wt_allele))).unique().sort(["Allele", "Batch", "Replicate"])

        nrow = int(round(plot_img.shape[0]/4))
        
        plotMultiImages(plot_img, "GFP", 0.99, nrow, display=False, plotpath=f"{plot_dir}/{gfp_nm}")
        plotMultiImages(plot_img, "Mito", 0.99, nrow, display=False, plotpath=f"{plot_dir}/{mito_nm}")
        
        
if __name__ == '__main__':
    main()
