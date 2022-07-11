import requests
from scipy.spatial.distance import cosine


model = "luminous-base"
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoyMTYsInJvbGUiOiJDbGllbnQiLCJjcmVhdGVkIjoxNjQ5OTQwNDI3NDIzNTQ4MjA5fQ.sYvTpwtybMPXtODaR1K04bzkF9dAy3Yn-UYQWSHWdt4" # find your token here: https://app.aleph-alpha.com/profile 

texts = [
   "Auf dem Kassenzettel steht: G+G Mozarella",
   "Auf dem Kassenzettel steht: Mozzarella",
   "Auf dem Kassenzettel steht: Cheddar",
   "Auf dem Kassenzettel steht: Mehl",
   "Auf dem Kassenzettel steht: Sahne",
   "Auf dem Kassenzettel steht: Aqua Nordic Ingwer-Zirtonengras"
]

text3 = [
    "Auf dem Kassenzettel steht: Gouda",
    "Auf dem Kassenzettel steht: Mortadella",
    "Auf dem Kassenzettel steht: Pizza Tomate Mozzarella"
]

text2 = [
       "Auf dem Kassenzettel steht: G+G Mozarella",
]

embeddings = []

embeddings2 = []

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
    embeddings.append(result["embeddings"]["symmetric"]["weighted_mean"])

for txt in text2:
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
    embeddings2.append(result["embeddings"]["symmetric"]["weighted_mean"])

# Calculate cosine similarities
# Cosine similarities are in [-1, 1]. Higher means more similar
cosine_sim_0_1 = 1 - cosine(embeddings2[0], embeddings[1])
cosine_sim_0_2 = 1 - cosine(embeddings2[0], embeddings[2])
cosine_sim_0_3 = 1 - cosine(embeddings2[0], embeddings[3])
cosine_sim_0_4 = 1 - cosine(embeddings2[0], embeddings[4])
cosine_sim_0_5 = 1 - cosine(embeddings2[0], embeddings[5])
#cosine_sim_0_6 = 1 - cosine(embeddings[0], embeddings[6])
#cosine_sim_0_7 = 1 - cosine(embeddings[0], embeddings[7])
#cosine_sim_0_8 = 1 - cosine(embeddings[0], embeddings[8])


print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[1], cosine_sim_0_1))
print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[2], cosine_sim_0_2))
print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[3], cosine_sim_0_3))
print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[4], cosine_sim_0_4))
print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[5], cosine_sim_0_5))
#print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[6], cosine_sim_0_6))
#print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[7], cosine_sim_0_7))
#print("Cosine similarity between \"%s\" and \"%s\" is: %.3f" % (texts[0], texts[8], cosine_sim_0_8))