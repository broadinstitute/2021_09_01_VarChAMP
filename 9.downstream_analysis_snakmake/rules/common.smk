import preprocess
import os

batch = config["Metadata_Batch"]
plates = os.listdir(f"inputs/single_cell_profiles/{batch}/")

rule parquet_convert:
    input: 
        "inputs/single_cell_profiles/{batch}/{plate}/{plate}.sqlite"
    output:
        "outputs/single_cell_profiles/{batch}/{plate}_raw.parquet"
    run:
        preprocess.convert_parquet(*input, *output)

rule annotate:
    input:
        "outputs/single_cell_profiles/{batch}/{plate}_raw.parquet"
    output:
        "outputs/single_cell_profiles/{batch}/{plate}_annotated.parquet"
    run:
        platemap = preprocess.get_platemap(f'inputs/metadata/platemaps/{wildcards.batch}/barcode_platemap.csv', f'{wildcards.plate}')
        platemap_path = f"inputs/metadata/platemaps/{wildcards.batch}/platemap/{platemap}.txt"
        preprocess.annotate_with_platemap(*input, platemap_path, *output)

rule aggregate:
    input:
        expand(
            "outputs/single_cell_profiles/{batch}/{plate}_annotated.parquet",
            batch=batch, 
            plate=plates)
    output:
        "outputs/batch_profiles/{batch}/raw.parquet"
    run:
        preprocess.aggregate(*input, *output)