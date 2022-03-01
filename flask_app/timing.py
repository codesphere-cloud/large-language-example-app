import timeit
import pandas as pd

print(timeit.timeit('pd.read_excel("grocery_mapping.xlsx")', setup="import pandas as pd", number=30))