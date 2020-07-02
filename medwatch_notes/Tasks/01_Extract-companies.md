# 1. Extract companies

Compile a unique list of non-university organizations under the "Developer" column found on https://www.who.int/publications/m/item/draft-landscape-of-covid-19-candidate-vaccines

Copy of pdf also found in medwatch/datasets/novel-coronavirus-landscape-covid-19.pdf



## Put table into a csv then pandas dataframe

Used https://simplypdf.com/Excel to save as .xlsx file

Saved table of Clinical trials as medwatch/datasets/WHO-covid19-clinicaltrials.csv

Use `pandas` to read csv

```python
path_data = '../datasets/WHO-covid19-clinicaltrials.csv'
df = pd.read_csv(path_data)
df.head(17)
```



Extract all non-academia organizations from the **"Developers"** column:

```python
developers = df['Developer'].tolist()
companies = []

# Function to see if organization is a university
def is_academia(organization: str):
    keywords = ['University', 'College', 'Academy']
    tf = any(map(organization.__contains__, keywords))
    return tf

# For each row, split to individual organizations
for developer in developers:
    organizations = developer.split('/')
    	# For each organization, clean up formatting and add to companies list if not academia
    for organization in organizations:
        organization = organization.replace('\n', ' ')
        if not is_academia(organization):
            companies.append(organization)

print(companies)
```



