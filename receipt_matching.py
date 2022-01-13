import json
from thefuzz import process as fuzzy_process
import pandas as pd
import numpy as np


grocery_mapping = pd.read_excel("grocery_mapping.xlsx")

choices = grocery_mapping["Product"]

grocery_input = pd.read_excel("grocery_input.xlsx")


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
    merged_df["Similarity Ratio"] = pd.Series(scores) / 100
    return merged_df.sort_values("Similarity Ratio", ascending=False)


    

merged = match_and_merge(grocery_input,grocery_mapping,"description","Product",75).dropna(subset=["description"])

merged.to_excel("merged_output.xlsx", index=False)


    


