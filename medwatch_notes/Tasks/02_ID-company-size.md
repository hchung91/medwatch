# 2. Identify company size

From the `companies` list derived from the previous section, use Yahoo! Finance (?) API to determine the company's market value

Note: 

- If not a publicly traded company, should return n/a
- If not a US-based company, should have some kind of flag

Starting point (ended up not using):
https://towardsdatascience.com/valuing-a-company-with-python-1ddab3e33502



## Get company ticker symbol from company name

As a first attempt, I tried pulling data from the Wikipedia infobox section using `wptools`. Quickly found this was not very robust so shifted over to a Yahoo! Finance API but the Wikipedia attempt can be found in [medwatch/notebooks/07-01-20_Parse_CSV_for_companies.ipynb](medwatch/notebooks/07-01-20_Parse_CSV_for_companies.ipynb) 



### Setting up Yahoo! Queries 

```python
import requests
import json
```



The query base is

```
query = f'http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={COMPANY_NAME}&region=1&lang=en&callback=YAHOO.Finance.SymbolSuggest.ssCallback'

```

As an added precaution, I did some extra formatting to `COMPANY_NAME` before calling the query but this may be an unnecessary step

```python
COMPANY_NAME = COMPANY_NAME.replace('.', '').replace(' ', '%20')
```



### Make the query and format it

To pull data, run the command:

```python
r = requests.get(query)
print(r) # Return code of 200 means it was successful
```

For some reason, this does not produce a clean JSON file but instead wraps it around the API interface called and paranthesis. I formatted it manually as a quick fix.

```python
data = r.text.split('(', 1)[1]
data = data.rsplit(')', 1)[0]
```

**NOTE:** The second parameter of `1` in both `split()` calls is very important in case there are parentheses within the actual JSON. This was the source of a big bug.

From here, we can dump it into a JSON file and isolate just the search results

```python
data = json.loads(data)
data = data['ResultSet']['Result']
```



Ultimately, I wrapped all this together into a function

```python
def get_and_parse_query(query):
  r = requests.get(query)
  data = r.text.split('(', 1)[1]
  data = data.rsplit(')', 1)[0]
  data = json.loads(data)
  data = data['ResultSet']['Result']
  
  return data
```

These basic functions can be looped over a list of companies and the results marked. If the `get` request yields no results, `len(data)` will equal `0`. I set all outputs to such queries as `'n/a'`.

A query may also yield multiple suggestions. For these instances, I prioritized results that were in a US stock exchange. More information about that can be found in the [following section](#Prioritize US Markets/Exchanges). Otherwise, it would default to the first results. 



### Prioritize US Markets/Exchanges

List of US securities markets were found [here](https://www.investopedia.com/ask/answers/08/security-market-usa.asp). A reference list was defined as

```python
usa_mkts = ['NYSE', 'NASDAQ', 'AMEX', 
               'BSE', 'CBOE', 'CBOT', 
               'CME', 'CHX', 'ISE', 
               'MS4X', 'NSX', 'PHLX']
```

Given the JSON data, we can then check if any of the `'exchDisp'` fields match any of the entries in `usa_mkts` 

```python
match = df.loc[df['exchDisp'].isin(usa_mkts)]

if len(match) == 0:
  # None of the listed results are American
else:
  # Found a match from the US
```

To pull different fields of a set of results, put the JSON in a data frame and search under `symbol`, `exchDisp`, and `name` to get the stock ticker symbol, the name of the exchange, and how Yahoo! Finance formats the company name respectively. See snippet below for an example.

```python
# To get the symbol, exchange, and name of the first JSON entry [data], do the following

df = pd.DataFrame(data)
symbol = df['symbol'][0]
exchange = df['exchDisp'][0]
name = df['name'][0]
```





## Live Market Data using pandas_datareader

Module can be found at
https://pypi.org/project/pandas-datareader/



### Get Market Cap of a list of companies

Stackoverflow link:
https://stackoverflow.com/questions/54815864/downloading-a-companies-market-cap-from-yahoo

```python
from pandas_datareader import data
tickers = ['AAPL','AMZN','TSLA','GOOG']
data.get_quote_yahoo(tickers)['marketCap']

AAPL    964416176128
AMZN    928656588800
GOOG    869718360064
TSLA     45642039296
Name: marketCap, dtype: int64
```

**NOTE:** Output is in dollars

Apply same principle but set `tickers` to list of symbols obtained from the [prior section](#Make the query and format it).



### Classify a company by size

Companies were initially somewhat arbitrarily defined as being small, medium, large, or v-large depending on whether they made over $0, $10B, $25B, or $50B dollars. Method to classify that is currently naively coded as follows.

```python
def id_company_size(market_cap):
  sizes = ['small', 'medium', 'large', 'v-large']
  thresh = [0, 10e9, 25e9, 50e9]

  if market_cap > thresh[3]:
      size = sizes[3]
  elif market_cap > thresh[2]:
      size = sizes[2]
  elif market_cap > thresh[1]:
      size = sizes[1]
  else:
      size = sizes[0]

  return size
```
