import requests
from scipy.spatial.distance import cosine
import json
import pandas as pd
import os 

model = "luminous-base"
API_KEY = os.environ.get('ALEPH_KEY')

# Create Aleph Endpoint embeddings
def create_semantic_embeddings(texts):
        
    embeddings = {}

    for txt in texts:
        response = requests.post(
            "https://api.aleph-alpha.com/semantic_embed",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "User-Agent": "Aleph-Alpha-Python-Client-1.4.2",
            },
            json={
                "model": model,
                "prompt": txt,
                "representation": "symmetric",
                "compress_to_size": 128,
            },
        )
        result = response.json()
        embeddings[txt] = result["embedding"]

    file = './semantic_embedding_dict_en.json'

    with open(file, 'w') as f: 
        json.dump(embeddings, f)

# Initial Mappings, for different languages, translate the xlsx via 
# google translate and the leading text here and analysis.py line 93
# run it once via 'pipenv run python search_embed.py' 
# after changing the mapping file
grocery_mapping = pd.read_excel("grocery_mapping_en.xlsx", engine="openpyxl")
texts = ["The grocery receipt item is: " + str(product) for product in grocery_mapping["product"]]
create_semantic_embeddings(texts)

