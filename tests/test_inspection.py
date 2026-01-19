import pandas as pd
import os 

csv_file = 'LU015K15330000170A_Inspection_Result_20251024_131806.csv'
csv_path = os.path.join(os.path.dirname(__file__), csv_file)
df = pd.read_csv(csv_path, sep='\t', header=None)
print(df)