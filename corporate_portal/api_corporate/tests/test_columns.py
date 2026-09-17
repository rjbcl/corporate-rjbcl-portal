import pandas as pd

# Load both CSVs
df1 = pd.read_csv("/home/rjbcl/Downloads/1.csv")
df2 = pd.read_csv("/home/rjbcl/Downloads/2.csv")

# Extract register numbers
set1 = set(df1["PolicyNo"])
set2 = set(df2["PolicyNo"])

# Check equality
if set1 == set2:
    print("Both CSVs have the same register numbers.")
else:
    print("Mismatch found.")
    print("In file1 but not in file2:", set1 - set2)
    print("In file2 but not in file1:", set2 - set1)
