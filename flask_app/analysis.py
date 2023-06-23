import requests
import pandas as pd
import os
import re
import json
from flask_app import app
from thefuzz import process as fuzzy_process
from scipy.spatial.distance import cosine
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

API_KEY = os.environ.get('ALEPH_KEY')
model = "luminous-base"


endpoint = os.environ.get('AZURE_FORM_ENDPOINT')
key = os.environ.get('AZURE_FORM_KEY')

def azure_form_recognition(image_input):
    document = image_input

    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    poller = document_analysis_client.begin_analyze_document("prebuilt-receipt", document)
    receipts = poller.result()
    for idx, receipt in enumerate(receipts.documents):
        if receipt.fields.get("MerchantName"):
            store = receipt.fields.get("MerchantName").value
        else:
            store="Unknown store"
        if receipt.fields.get("Items"):
            d = []
            for idx, item in enumerate(receipt.fields.get("Items").value):
                item_name = item.value.get("Description")
                if item_name:
                    d.append( {
                        "description": item_name.value,
                        "quantity" : [float(re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", item.value.get("Quantity").content)[0].replace(",",".")) if item.value.get("Quantity") and item.value.get("Quantity").value !=None else 1][0],
                        "total" : [item.value.get("TotalPrice").value if item.value.get("TotalPrice") else 1][0]
                        }
                    ) 
            grocery_input =  pd.DataFrame(d)

    return  grocery_input, store   


def find_match_semantic(embeddings, product_description: str):
    embeddings_to_add = []

    response = requests.post(
        "https://api.aleph-alpha.com/semantic_embed",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "Aleph-Alpha-Python-Client-1.4.2",
        },
        json={
            "model": model,
            "prompt": product_description,
            "representation": "symmetric",
            "compress_to_size": 128,
        },
    )
    result = response.json()
    embeddings_to_add.append(result["embedding"])    
    cosine_similarities = {}
    for item in embeddings:
        
        cosine_similarities[item] = 1 - cosine(embeddings_to_add[0], embeddings[item])

    result = (max(cosine_similarities, key=cosine_similarities.get),max(cosine_similarities.values())*100,list(cosine_similarities.keys()).index(max(cosine_similarities, key=cosine_similarities.get)))

    return result


def match_and_merge_combined(df1: pd.DataFrame, df2: pd.DataFrame, col1: str, col2: str, embedding_dict, cutoff: int = 80, cutoff_ai: int = 80, language: str = 'de'):
    # adding empty row
    df2 = df2.reindex(list(range(0, len(df2)+1))).reset_index(drop=True)
    index_of_empty = len(df2) - 1

    # Context - provides the context for our large language models
    if language == 'de': phrase='Auf dem Kassenzettel steht: ' 
    else: phrase='The grocery item is: '

    # First attempt a fuzzy string based match = faster & cheaper than semantic match
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
        # If match below cutoff fetch semantic match
        score, index = match[1:] if match is not None else find_match_semantic(embedding_dict,phrase+s1)[1:]
        if score < cutoff_ai:
            index = index_of_empty 
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
   
    # Detect if item is measured in kg and correct values
    merged_df["footprint"]= (merged_df["quantity"]*merged_df["typical_footprint"]).round(0)
    merged_df.loc[~(merged_df["quantity"] % 1 == 0),"footprint"] = merged_df["quantity"]*10*merged_df["footprint_per_100g"]
    merged_df.loc[~(merged_df["quantity"] % 1 == 0),"typical_weight"] = merged_df["quantity"]*1000
    merged_df.loc[~(merged_df["quantity"] % 1 == 0),"quantity"] = 1
    merged_df["footprint"] = merged_df["footprint"].fillna(0)
    merged_df["product"] = merged_df["product"].fillna("???")           
    merged_df = merged_df.drop(["index"], axis=1).dropna(subset=["description"])

    # Type conversion to integers
    merged_df["footprint"]=merged_df["footprint"].astype(int)
    
    # Set standardized product descriptions
    merged_df.loc[(~pd.isna(merged_df["value_from"])),"product"] = merged_df["value_from"]    

    return merged_df 

# Call this function from the main route for the english analysis
def analyze_receipt_en(image):
    # Load mapping table for fuzzy string mapping
    grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping_en.xlsx"), engine="openpyxl")
    ocr_result, store = azure_form_recognition(image)

    # Load semantic embedding dict for semantic mapping        
    with open('./semantic_embedding_dict_en.json', 'r') as f:
        embeddings = json.load(f)
    # You can change the cutoff params here for higher / lower accuracy 
    results = match_and_merge_combined(ocr_result,grocery_mapping,"description","product",embeddings,88,55,"en")
    results = results.fillna(0)

    return results

def analyze_receipt(image):
    # Load mapping table for fuzzy string mapping
    grocery_mapping = pd.read_excel(os.path.join(os.path.dirname(app.instance_path), "grocery_mapping.xlsx"), engine="openpyxl")
    ocr_result, store = azure_form_recognition(image)

    # Load semantic embedding dict for semantic mapping        
    with open('./semantic_embedding_dict.json', 'r') as f:
        embeddings = json.load(f)
    # You can change the cutoff params here for higher / lower accuracy 
    results = match_and_merge_combined(ocr_result,grocery_mapping,"description","product",embeddings,88,55,"de")
    results = results.fillna(0)

    return results