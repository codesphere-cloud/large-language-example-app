import pandas as pd
import pandas_dedupe



mapping = pd.read_excel("deduped_mapping.xlsx")
training = pd.read_excel("excel_input.xlsx")



if __name__ == '__main__':
    #mapping_deduped = pandas_dedupe.dedupe_dataframe(mapping,["product","category"])
    #training_deduped = pandas_dedupe.dedupe_dataframe(training,["product"])
    #print(training_deduped)
    #print(mapping_deduped)
    #mapping_deduped.to_excel("deduped_mapping.xlsx")
    #df_final = pandas_dedupe.link_dataframes(mapping_deduped,training_deduped,["product"])
    #print(df_final)
    #df_final.to_excel("clustering.xlsx")
    df_final = pandas_dedupe.link_dataframes(mapping,training,["product"])
    df_final = df_final.dropna(subset=["confidence"])
    print(df_final)
    df_final.to_excel("clustering.xlsx")
