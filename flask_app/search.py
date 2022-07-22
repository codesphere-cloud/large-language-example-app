from thefuzz import process as fuzzy_process
from flask_app import embed
from flask_app.embed import find_match_new
import pandas as pd



def get_search_results(input_string: str, df2, col2: str, embeddings, cutoff_lev: int = 85, cutoff_ai: int = 85):
    
    df2 = df2.reindex(list(range(0, len(df2)+1))).reset_index(drop=True)
    index_of_empty = len(df2) - 1
    indexed_strings_dict = dict(enumerate(df2[col2]))
    match = fuzzy_process.extractOne(
    query=input_string,
    choices=indexed_strings_dict,
    score_cutoff=cutoff_lev
    )
    
    if match:
        result = [*match]
        result.extend(df2.loc[match[2], :].values.flatten().tolist())
        output = {
            "item": result[0] if pd.isna(result[7]) else result[7],
            "score" : int(result[1]),
            "footprint_per_g":  int(result[4]),
            "typical_weight" : int(result[5]),
            "footprint" : int(result[6]),
            "category" :  result[8],
                     
        }
        return output

    else:
        match = find_match_new(embeddings,input_string)
        match = (match[0][27:], match[1], match[2])

        result = match if match[1] > (cutoff_ai) else ('???',match[1],index_of_empty)
        result = [*result]
        print(result)
        result.extend(df2.loc[result[2], :].values.flatten().tolist())
        result[:7] = pd.Series(result[:7], dtype=object).fillna('0').tolist()
        print(result)
        output = {
            "item": result[0] if pd.isna(result[7]) else result[7],
            "score" : int(result[1]),
            "footprint_per_g":  int(result[4]),
            "typical_weight" : int(result[5]),
            "footprint" : int(result[6]),
            "category" :  "n/a" if pd.isna(result[8]) else result[8],
                     
        }
        return output
