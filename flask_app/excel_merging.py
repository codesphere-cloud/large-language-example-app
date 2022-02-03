#from flask_app.analysis import match_and_merge
import pandas as pd
import os
#from flask_app import app
from thefuzz import process as fuzzy_process
import numpy as np


def match_and_merge(df1: pd.DataFrame, df2: pd.DataFrame, col1: str, col2: str, cutoff: int = 80):
    # adding empty row
    df2 = df2.append(pd.Series(dtype=np.float64), ignore_index=True)
    index_of_empty = len(df2) - 1

    # matching
    indexed_strings_dict = dict(enumerate(df2[col2]))
    matched_indices = set()
    ordered_indices = []
    scores = []
    for s1 in df1[col1]:
        match = fuzzy_process.extractOne(
            query=s1,
            choices=indexed_strings_dict,
            score_cutoff=cutoff
        )
        score, index = match[1:] if match is not None else (0.0, index_of_empty)
        matched_indices.add(index)
        ordered_indices.append(index)
        scores.append(score)

    # detect unmatched entries to be positioned at the end of the dataframe
    missing_indices = [i for i in range(len(df2)) if i not in matched_indices]
    ordered_indices.extend(missing_indices)
    ordered_df2 = df2.iloc[ordered_indices].reset_index()

    # merge rows of dataframes
    merged_df = pd.concat([df1, ordered_df2], axis=1)

    # adding the scores column and sorting by its values
    scores.extend([0] * len(missing_indices))
    merged_df["similarity_ratio"] = pd.Series(scores) / 100
    #merged_df.sort_values("Similarity Ratio", ascending=False)
    
    merged_df["footprint"]=merged_df["quantity"]*merged_df["typical_footprint"]
    merged_df["footprint"] = merged_df["footprint"].round(0)
    not_recognized = pd.DataFrame()
    not_recognized["product"] = merged_df.loc[merged_df['typical_footprint'].isnull()][["description"]]
    merged_df = merged_df.drop(["index"], axis=1).dropna(subset=["product", "description"])
    merged_df["quantity"]=merged_df["quantity"].astype(int)
    merged_df["footprint"]=merged_df["footprint"].astype(int)



    return merged_df, not_recognized


grocery_mapping = pd.read_excel( "grocery_mapping.xlsx", engine="openpyxl")

grocery_input = pd.read_excel( "excel_input.xlsx", engine="openpyxl")

results, not_recognized = match_and_merge(grocery_input,grocery_mapping,"description","product",75)

print(results)
print(not_recognized)

results.to_excel("output.xlsx", sheet_name='Result', index=False)