#!/usr/bin/env python3

import os
import requests
import csv

import pandas as pd
from pandas_datareader import data as pd_data
from yahooquery import Ticker
from googlesearch import search


# COLLECTING AND PREPPING DATA ON COMPANY INFO


def create_company_df(companies):
    """
    Creates a Pandas datafrane of key company attributes from a list of companies.
    Columns of the dataframe include:
        - Company             # As given in the input
        - Yahoo Listed Co.    # As listed on Yahoo! Finance
        - Symbol              # Ticker
        - Exchange
        - Market Cap          # Assumes all USD but need to fix
        - Company Size        # small, medium, large, n/a
        - Is American         # Y or N
        - Home URL
        - Press Release URL
    
    Parameters:
    -------------
    companies: list of str - list of company names
    Returns:
    -------------
    df: pandas.DataFrame - Summary of company info as described above
    """

    companies = list(set(companies))  # removes duplicates

    symbols = []
    exchanges = []
    ynames = []
    is_us = []

    for company in companies:
        sym, exch, yco, usa = check_usa_mkts(get_company_info(company))
        symbols.append(sym)
        exchanges.append(exch)
        ynames.append(yco)
        is_us.append(usa)

    marketcaps = []
    sizes = []
    urls = []
    urls_pr = []

    for sym, co in zip(symbols, companies):
        if sym == "n/a":
            print(f"Skipping {co}\n")
            marketcaps.append("n/a")
            sizes.append("n/a")
            urls.append("n/a")
            urls_pr.append("n/a")
            continue

        print(f"Checking {co} [{sym}]")
        marketcap = get_market_cap(sym)
        size = id_company_size(marketcap)
        url = get_company_url(sym)
        url_pr = get_press_release_page(url)

        marketcaps.append(marketcap)
        sizes.append(size)
        urls.append(url)
        urls_pr.append(url_pr[0])

    print("Search complete")

    df = pd.DataFrame(
        {
            "Company": companies,
            "Yahoo Listed Co.": ynames,
            "Symbol": symbols,
            "Exchange": exchanges,
            "Market Cap": marketcaps,
            "Company Size": sizes,
            "Is American": is_us,
            "Home URL": urls,
            "Press Release URL": urls_pr,
        }
    )

    return df


def add_companies_to_csv(companies, filename):
    """
    Generates a sub dataframe using create_company_df() and tacks that on to
    the csv specified.
    
    Parameters:
    -------------
    companies: list of str - list of company names
    filename: str - [path and] filename to csv to add data to
    Returns:
    -------------   
    n/a
    """

    df_add = create_company_df(companies)
    df_old = pd.read_csv(filename)
    frames = [df_old, df_add]
    df = pd.concat(frames)
    df = df.drop_duplicates()

    df.to_csv(filename, index=False)


def parse_who_companies(filename):
    """
    Automatically parses csv of World Health Organization (WHO) COVID-19
    landscape summaries and pulls list of companies
    Parameters:
    -------------
    filename: str - [path and] filename to csv of WHO data
    Returns:
    -------------    
    companies: list of str - Non-academia organizations found in csv
    """

    df = pd.read_csv(filename)
    developers = df["Developer"].tolist()
    companies = []

    # GET LIST OF COMPANIES
    # For each row, split to individual organizations
    for developer in developers:
        if is_na(developer):
            continue

        organizations = developer.split("/")

        # For each organization, clean up formatting and add to companies list if not academia
        for organization in organizations:
            organization = organization.replace("\n", " ")
            if not is_academia(organization):
                companies.append(organization)

    companies = list(set(companies))  # removes duplicates

    return companies


def get_company_info(company_name):
    """
    Queries Yahoo! Finance Symbol Suggest API with a company name
    and returns all results of possibly matched publicly listed companies 
    and related info including a company's symbol, exchange, website, and 
    the company's name as listed on Yahoo! for comparison.
    e.g. get_company_info('google')
         returns 
         [{"symbol":"GOOG","name":"Alphabet Inc.","exch":"NMS",
         "type":"S","exchDisp":"NASDAQ","typeDisp":"Equity"},
         {"symbol":"GOOGL","name":"Alphabet Inc.","exch":"NMS",
         "type":"S","exchDisp":"NASDAQ","typeDisp":"Equity"},
         {"symbol":"^VXGOG","name":"CBOE EQUITY VIXON GOOGLE","exch":"WCB",
         "type":"I","exchDisp":"Chicago Board Options Exchange","typeDisp":"Index"},
         {"symbol":"^NY2LGOOG","name":"ICE Leveraged 2x GOOG Index","exch":"NYS",
         "type":"I","exchDisp":"NYSE","typeDisp":"Index"},
         {"symbol":"GOOGL.MI","name":"ALPHABET CLASSE A","exch":"MIL",
         "type":"S","exchDisp":"Milan","typeDisp":"Equity"},
         {"symbol":"GOOGL.BA","name":"Alphabet Inc.","exch":"BUE",
         "type":"S","exchDisp":"Buenos Aires","typeDisp":"Equity"},
         {"symbol":"GOOGL.MX","name":"Alphabet Inc.","exch":"MEX",
         "type":"S","exchDisp":"Mexico","typeDisp":"Equity"},
         {"symbol":"GOOG.MI","name":"Alphabet Inc.","exch":"MIL",
         "type":"S","exchDisp":"Milan","typeDisp":"Equity"},
         {"symbol":"GOOG.MX","name":"Alphabet Inc.","exch":"MEX",
         "type":"S","exchDisp":"Mexico","typeDisp":"Equity"}]}}
    Parameters:
    -------------
    company_name: str - name of organization
    Returns:
    -------------
    yahoo_json: json - JSON of all relevant company matches and financial infromation
    """

    # Fix formatting of name
    co = company_name.replace(".", "").replace(" ", "%20")

    query = f"http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={co}\
    &region=1&lang=en&callback=YAHOO.Finance.SymbolSuggest.ssCallback"

    response = requests.get(query)

    fdata = response.text.split("(", 1)[1]
    fdata = fdata.rsplit(")", 1)[0]
    data = json.loads(fdata)
    yahoo_json = data["ResultSet"]["Result"]

    return yahoo_json


def check_usa_mkts(yahoo_json):
    """
    Takes result of Yahoo! Finance company search query and prioritizes returning
    results from US exchanges.  
    e.g. sym, exch, yname, am = check_usa_mkts(get_company_info('google'))
         returns
         sym = 'GOOG'
         exch = 'NASDAQ'
         yname = 'Alphabet'
         am = 'Y'
    Parameters:
    -------------
    yahoo_json: json - JSON from Yahoo! Finance Symbol Suggest API. JSON can
        be obtained using the medwatch get_company_info() method
    Returns:
    -------------
    symbol: str - Company's ticker symbol
    exchange: str - Exchange company is listed under
    name: str - Official company name listed on Yahoo!
    usa: str - 'Y' for is on US exchange, 'N' otherwise (**may change to T/F)
    """

    # Check that input is not empty
    if len(yahoo_json) == 0:
        return "n/a", "n/a", "n/a", "n/a"

    # List of US exchanges
    usa_mkts = [
        "NYSE",
        "NASDAQ",
        "AMEX",
        "BSE",
        "CBOE",
        "CBOT",
        "CME",
        "CHX",
        "ISE",
        "MS4X",
        "NSX",
        "PHLX",
    ]

    # Load JSON into dataframe (**may operated directly as JSON)
    # and see if any of the exchanges listed in the query result match
    # the list of usa_mkts
    df = pd.DataFrame(yahoo_json)
    match = df.loc[df["exchDisp"].isin(usa_mkts)]

    # If no matches in US exchanges, return the first result
    if len(match) == 0:
        symbol = df["symbol"][0]
        exchange = df["exchDisp"][0]
        name = df["name"][0]
        usa = "N"

    # Otherwise return first result matched to a US market
    else:
        symbol = match["symbol"][0]
        exchange = match["exchDisp"][0]
        name = match["name"][0]
        usa = "Y"

    return symbol, exchange, name, usa


def get_company_url(ticker_symbol: str):
    """
    Get company's official website/homepage as listed on Yahoo! Finance from
    its ticker symbol.
    e.g. get_company_url('GOOG')
         returns https://www.google.com/
    Parameters:
    -------------
    ticker_symbol: str - Company's ticker symbol
    Returns:
    -------------
    url: str - String of company's homepage url
    """

    response = Ticker(ticker_symbol, asynchronous=True)
    data = response.asset_profile
    url = data[ticker_symbol]["website"]

    return url


def is_academia(organization: str):
    """
    Checks if organization is associated with academia. 
    Since academic institutions are not publicly traded, this
    helps serve as an indicator to ignore.
    Checks for keywords associated with academia.
    e.g. is_academia('Arizona State University')
         returns True
         is academia('Google')
         returns False
    Parameters:
    -------------
    organization: str - Full name of organization (currently cannot handle abbreviations) 
    Returns:
    -------------
    tf: bool - Boolean True if academia, False otherwise
    """

    # Current list of keywords associated with academia
    keywords = ["university", "college", "academy"]

    # Check if any of the keywords can be found in the given organization
    # Case set to lower to minimize issues with formatting
    # https://stackoverflow.com/questions/8122079/python-how-to-check-a-string-for-substrings-from-a-list
    tf = any(map(organization.lower().__contains__, keywords))

    # Return true or false
    return tf


def get_market_cap(symbol):
    """
    Finds company's market cap based off the company's ticker symbol.
    Value returned will be USD for US companies. 
    **Need to address different currencies and possibly include currency conversion
    e.g. get_market_cap('GOOG')
         returns 1034277860323
    Parameters:
    -------------
    symbol: str - Company's ticker symbol
    Returns:
    -------------
    cap: int - Market cap of company in currency of country company is located in
    """
    try:
        cap = pd_data.get_quote_yahoo(symbol)["marketCap"]
        cap = cap[symbol]

    except:
        print(f"Market cap for {symbol} not found.")
        cap = "n/a"

    return cap


def id_company_size(market_cap):
    """
    Classifies pharmaceutical/biotech size as small, medium, or large 
    based on market cap (USD).
    e.g. id_company_size(3e9)
         returns 'medium'
    
    Parameters:
    -------------
    market_cap - Float or int of a company's market cap
    Returns:
    -------------
    size: str - Classification of company as small, medium, or large
    """

    if market_cap == "n/a":
        print("Market cap not defined.")
        return "n/a"

    sizes = ["small", "medium", "large"]
    thresh = [0, 2e9, 10e9]

    if market_cap > thresh[2]:
        size = sizes[2]
    elif market_cap > thresh[1]:
        size = sizes[1]
    else:
        size = sizes[0]

    return size


def search_google(query, num_results=1):
    """
    Takes search phrase, queries Google, and returns list of domains of results.
    Defaulted to return 1 result but can be modified.
    e.g. search_google('apple')
         returns ['https://www.apple.com/']
    
    Parameters:
    -------------
    query: str - String of what to search on Google
    num_results: int = 1 - Maximum number of results returned
    Returns:
    -------------
    results: list - List of strings with domains of search results
    """

    results = []
    num_ppg = min([num_results, 10])
    for i in search(
        query,  # The query you want to run
        tld="com",  # The top level domain
        lang="en",  # The language
        num=num_ppg,  # Number of results per page
        start=0,  # First result to retrieve
        stop=num_results,  # Last result to retrieve
        pause=3.0,  # Lapse between HTTP requests
    ):

        results.append(i)

    if len(results) == 0:
        results = ["n/a"]

    return results


def prune_url(full_url: str, cut_chars=[]):
    """
    Method to clean up domain (e.g. removes www. or http://)
    Found having full URL can yield odd Google searches
    e.g. prune_url('https://www.google.com/', cut_chars=['https://', 'www.'])
         returns 'google.com'
    Parameters:
    -------------
    full_url: str - String of URL to be pruned
    Returns:
    -------------
    pruned_url: str - String of pruned URL
    """

    # cut_chars = ["https://", "http://", "www."]

    for cut in cut_chars:
        full_url = full_url.replace(cut, "")

    if full_url[-1] == "/":
        pruned_url = full_url[0:-1]
    else:
        pruned_url = full_url

    return pruned_url


def get_press_release_page(company_url: str):
    """
    Finds 'press releases' landing page based off company's official website 
    by searching Google.
    Company's official URL can be found using medwatch's get_company_url().
    e.g. get_press_release_page('https://www.astrazeneca.com/')
         returns 'https://www.astrazeneca.com/media-centre/press-releases.html'
    Parameters:
    -------------
    company_url: str - String of company's official homepage
    Returns:
    -------------
    pr_url: str - String of company's press releases landing page
    """
    print(f"Searching for press release page on {company_url}")
    domain = prune_url(
        company_url, cut_chars=["https://", "http://", "www."]
    )  # Cleans up domain as full URL gave odd results
    # query = f'site:{domain} press releases' # Formats query
    query = f"site:{domain} investor news"  # Formats query
    pr_url = search_google(query)  # Searches Google and returns first result
    print(f"Found: {pr_url}")
    print("-------------------------------------\n")
    return pr_url