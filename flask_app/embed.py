from math import nan
import numpy as np
from aleph_alpha_client import AlephAlphaClient
from itertools import islice
import json
import requests
import pandas as pd
from thefuzz import process as fuzzy_process
from scipy.spatial.distance import cosine
import os

API_KEY = os.environ.get('ALEPH_KEY')
model = "luminous-base"
"""
# This function takes a list of strings of any length and computes the similarity between any two strings in the list
def embedd_mappings(product_list, model="luminous-base"):

    embedding_dict = {}

    for string in product_list:

        string_embedding = client.embed(
            model=model,
            prompt=string,
            pooling=["mean"],
            layers=[-1]
        )

        embedding_dict[string] = {"embedding": string_embedding}


    # We check the embeddings in the last layer. The last layers of each model are:
    last_layers = {
        "luminous-base": "layer_40",
        "luminous-extended": "layer_46"
    }

    # This adds the mean embedding in the last layer to each entry in our dict
    for string in embedding_dict:
        embedding_dict[string]["embedding_means"] = embedding_dict[string]["embedding"]["embeddings"][last_layers[model]]["mean"]
    
    file = './embedding_dict.json'
    with open(file, 'w') as f: 
        json.dump(embedding_dict, f)

"""


def find_match_new(embeddings, product_description: str):
    embeddings_to_add = []


    response = requests.post(
        "https://api.aleph-alpha.com/embed",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "Aleph-Alpha-Python-Client-1.4.2",
        },
        json={
            "model": model,
            "prompt": product_description,
            "layers": [],
            "tokens": False,
            "pooling": ["weighted_mean"],
            "type": "symmetric",
        },
    )
    result = response.json()
    embeddings_to_add.append(result["embeddings"]["symmetric"]["weighted_mean"])    
    #print(embeddings_to_add[0])
    #print(len(embeddings_to_add))
    #print(len(embeddings))
    cosine_similarities = {}
    for item in embeddings:
        
        cosine_similarities[item] = 1 - cosine(embeddings_to_add[0], embeddings[item])

    result = (max(cosine_similarities, key=cosine_similarities.get),max(cosine_similarities.values())*100,list(cosine_similarities.keys()).index(max(cosine_similarities, key=cosine_similarities.get)))


    #print(cosine_similarities)
    #print("Best Match: " + max(cosine_similarities, key=cosine_similarities.get) + " Similarity: " + str(max(cosine_similarities.values())))
    #print(result)
    return result




def match_and_merge_ki(df1: pd.DataFrame, df2: pd.DataFrame, col1: str, embedding_dict):
    # adding empty row
    df2 = df2.reindex(list(range(0, len(df2)+1))).reset_index(drop=True)
    #df2 = pd.concat([pd.Series(dtype=np.float64).to_frame(), df2], axis=0)
    #df2 = df2.drop([0], axis=1)
    #print(df2)
    #index_of_empty = len(df2) - 1

    # matching
    #indexed_strings_dict = dict(enumerate(df2[col2]))
    
    #matched_indices = set()
    ordered_indices = []
    scores = []
    for s1 in df1[col1]:
       
        match = find_match_new(embedding_dict,s1)
        score, index = match[1:]
        #matched_indices.add(index)
        ordered_indices.append(index)
        scores.append(score)

    # detect unmatched entries to be positioned at the end of the dataframe
    #missing_indices = [i for i in range(len(df2)) if i not in matched_indices]
    #ordered_indices.extend(missing_indices)
    ordered_df2 = df2.iloc[ordered_indices].reset_index()

    # merge rows of dataframes
    merged_df = pd.concat([df1, ordered_df2], axis=1)
    #merged_df = merged_df.drop([0], axis=1)
    # adding the scores column and sorting by its values
    #scores.extend([0] * len(missing_indices))
    merged_df["similarity_ratio"] = pd.Series(scores)

    # Detect if item is measured in kg

    merged_df["footprint"]= (merged_df["quantity"]*merged_df["typical_footprint"]).round(0)
    #merged_df["footprint"] = merged_df["footprint"].round(0)
    merged_df.loc[~(merged_df["quantity"] % 1 == 0),"footprint"] = merged_df["quantity"]*10*merged_df["footprint_per_100g"]
    #not_recognized = pd.DataFrame()
    #not_recognized["product"] = merged_df.loc[merged_df['typical_footprint'].isnull()][["description"]]
    merged_df["footprint"] = merged_df["footprint"].fillna(0)
    #merged_df["product"] = merged_df["product"].fillna("???")           
    merged_df = merged_df.drop(["index"], axis=1).dropna(subset=["description"])
    
    #merged_df["quantity"]=merged_df["quantity"].astype(int)
    merged_df["footprint"]=merged_df["footprint"].astype(int)
    #merged_df["description"]=[string[:-14] for string in merged_df["description"]]
    #print(merged_df)
    
    # Replace below threshold matches
    cutoff = 0.5
    merged_df.loc[(merged_df["similarity_ratio"] < cutoff),"product"] = '???'
    merged_df.loc[(merged_df["similarity_ratio"] < cutoff),"footprint_per_100g"] = 0
    merged_df.loc[(merged_df["similarity_ratio"] < cutoff),"typical_weight"] = 0
    merged_df.loc[(merged_df["similarity_ratio"] < cutoff),"typical_footprint"] = 0
    merged_df.loc[(merged_df["similarity_ratio"] < cutoff),"footprint"] = 0    

    # Set standardized product descriptions
    merged_df.loc[(~pd.isna(merged_df["value_from"])),"product"] = merged_df["value_from"]


    return merged_df #, not_recognized




def match_and_merge_combined(df1: pd.DataFrame, df2: pd.DataFrame, col1: str, col2: str, embedding_dict, cutoff: int = 80):
    # adding empty row
    df2 = df2.reindex(list(range(0, len(df2)+1))).reset_index(drop=True)
    #df2 = pd.concat([pd.Series(dtype=np.float64).to_frame(), df2], axis=0)
    #df2 = df2.drop([0], axis=1)
    #print(df2)
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
        score, index = match[1:] if match is not None else find_match_new(embedding_dict,"Auf dem Kassenzettel steht: "+s1)[1:]
        matched_indices.add(index)
        ordered_indices.append(index)
        scores.append(score)

    # detect unmatched entries to be positioned at the end of the dataframe
    missing_indices = [i for i in range(len(df2)) if i not in matched_indices]
    ordered_indices.extend(missing_indices)
    ordered_df2 = df2.iloc[ordered_indices].reset_index()

    # merge rows of dataframes
    merged_df = pd.concat([df1, ordered_df2], axis=1)
    #merged_df = merged_df.drop([0], axis=1)
    # adding the scores column and sorting by its values
    scores.extend([0] * len(missing_indices))
    merged_df["similarity_ratio"] = pd.Series(scores) / 100
   
    # Detect if item is measured in kg

    merged_df["footprint"]= (merged_df["quantity"]*merged_df["typical_footprint"]).round(0)
    #merged_df["footprint"] = merged_df["footprint"].round(0)
    merged_df.loc[~(merged_df["quantity"] % 1 == 0),"footprint"] = merged_df["quantity"]*10*merged_df["footprint_per_100g"]
    #not_recognized = pd.DataFrame()
    #not_recognized["product"] = merged_df.loc[merged_df['typical_footprint'].isnull()][["description"]]
    merged_df["footprint"] = merged_df["footprint"].fillna(0)
    merged_df["product"] = merged_df["product"].fillna("???")           
    merged_df = merged_df.drop(["index"], axis=1).dropna(subset=["description"])
    
    #merged_df["quantity"]=merged_df["quantity"].astype(int)
    merged_df["footprint"]=merged_df["footprint"].astype(int)
    #print(merged_df)
    
    # Set standardized product descriptions
    merged_df.loc[(~pd.isna(merged_df["value_from"])),"product"] = merged_df["value_from"]    



    return merged_df #, not_recognized


"""
grocery_mapping = pd.read_excel("grocery_mapping.xlsx", engine="openpyxl")
list1 = ["Schokoriegel", "Mehl", "Schweineschnitzel", "G+G Mozzarella", "Parmig. Reggiano", "Frischkaese", "Mozzarella"]
list2 = [string + " im Supermarkt" for string in list1]
quantity = [1,1,1,1,1,1,1]
total = [1,1,1,1,1,1,1]


#input_words = [str(product) + " im Supermarkt" for product in grocery_mapping["product"]]

#embedd_mappings(input_words)
with open('./embedding_dict.json', 'r') as f:
    embedding_dict = json.load(f)

ocr_result = pd.DataFrame(list2, columns=["description"]) 
ocr_result['quantity']=quantity
ocr_result['total']=total
results = match_and_merge_ki(ocr_result,grocery_mapping,"description","product",embedding_dict,83)
print(results)
#matches = find_match(embedding_dict, "Frischkaese im Supermarkt")
#print(matches)
#print(embedding_dict)
#print(json.dumps(embedding_dict, indent=4, sort_keys=False))
"""