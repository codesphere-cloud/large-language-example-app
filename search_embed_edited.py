import requests
from scipy.spatial.distance import cosine
import json
import pandas as pd

model = "luminous-base"
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxNDg4LCJyb2xlIjoiQ2xpZW50IiwiY3JlYXRlZCI6MTY1NzI3MjcwMDAzNzI2NTkxOH0.YRCDlf9DyWT64q4SjqDvXM18sdEw2leyZ4eK97nF87g" # find your token here: https://app.aleph-alpha.com/profile 


def create_embeddings(texts):
        
    embeddings = {}

    for txt in texts:
        response = requests.post(
            "https://api.aleph-alpha.com/embed",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "User-Agent": "Aleph-Alpha-Python-Client-1.4.2",
            },
            json={
                "model": model,
                "prompt": txt,
                "layers": [],
                "tokens": False,
                "pooling": ["weighted_mean"],
                "type": "symmetric",
            },
        )
        result = response.json()
        embeddings[txt] = result["embeddings"]["symmetric"]["weighted_mean"]

    file = './search_embedding_dict.json'

    with open(file, 'w') as f: 
        json.dump(embeddings, f)


# Initial Mappings
#grocery_mapping = pd.read_excel("grocery_mapping.xlsx", engine="openpyxl")
#texts = ["Auf dem Kassenzettel steht: " + str(product) for product in grocery_mapping["product"]]
#create_embeddings(texts)



def find_match(embeddings, product_description):
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

    #print(len(embeddings_to_add))
    #print(len(embeddings))
    cosine_similarities = {}
    for item in embeddings:
        
        cosine_similarities[item] = 1 - cosine(embeddings_to_add[0], embeddings[item])

    result = (max(cosine_similarities, key=cosine_similarities.get),max(cosine_similarities.values()),list(cosine_similarities.keys()).index(max(cosine_similarities, key=cosine_similarities.get)))
    #print(cosine_similarities)
    #print("Best Match: " + max(cosine_similarities, key=cosine_similarities.get) + " Similarity: " + str(max(cosine_similarities.values())))
    print(result)
    return result

test_string = "Auf dem Kassenzettel steht: hack gemischt"
with open('./search_embedding_dict.json', 'r') as f:
    embeddings = json.load(f)

#find_match(embeddings, test_string)




def match_and_merge_ki(df1: pd.DataFrame, df2: pd.DataFrame, col1: str, col2: str, embedding_dict, cutoff: int = 80):
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
       
        match = find_match(embedding_dict,s1)
        score, index = match[1:]
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
    



    return merged_df #, not_recognized


texts = [
   "Auf dem Kassenzettel steht: Extra Prof. 2x 14 S",
   "Auf dem Kassenzettel steht: Mozzarella",
   "Auf dem Kassenzettel steht: Cheddar",
   "Auf dem Kassenzettel steht: Mehl",
   "Auf dem Kassenzettel steht: Kerrygold Extra",
   "Auf dem Kassenzettel steht: Frischkaese",   
   "Auf dem Kassenzettel steht: T-Shirt"
]

list1 = ["Schokoriegel", "Mehl", "Schweineschnitzel", "G+G Mozzarella", "Parmig. Reggiano", "Frischkaese", "Mozzarella"]
list2 = [string + " im Supermarkt" for string in list1]
list2 = ["Auf dem Kassenzettel steht: " + string for string in list1]
quantity = [1,1,1,1,1,1,1]
total = [1,1,1,1,1,1,1]
grocery_mapping = pd.read_excel("grocery_mapping.xlsx", engine="openpyxl")
ocr_result = pd.DataFrame(texts, columns=["description"]) 
ocr_result['quantity']=quantity
ocr_result['total']=total
results = match_and_merge_ki(ocr_result,grocery_mapping,"description","product",embeddings,75)
print(results)


"""




texts = [
   "Auf dem Kassenzettel steht: Extra Prof. 2x 14 S",
   "Auf dem Kassenzettel steht: Mozzarella",
   "Auf dem Kassenzettel steht: Cheddar",
   "Auf dem Kassenzettel steht: Mehl",
   "Auf dem Kassenzettel steht: Kerrygold Extra",
   "Auf dem Kassenzettel steht: T-Shirt"
]

# Calculate cosine similarities
# Cosine similarities are in [-1, 1]. Higher means more similar
cosine_sim_0_1 = 1 - cosine(embeddings[0], embeddings[1])
cosine_sim_0_2 = 1 - cosine(embeddings[0], embeddings[2])
cosine_sim_0_3 = 1 - cosine(embeddings[0], embeddings[3])
cosine_sim_0_4 = 1 - cosine(embeddings[0], embeddings[4])
cosine_sim_0_5 = 1 - cosine(embeddings[0], embeddings[5])

print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[1], cosine_sim_0_1))
print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[2], cosine_sim_0_2))
print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[3], cosine_sim_0_3))
print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[4], cosine_sim_0_4))
print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[5], cosine_sim_0_5))
"""

