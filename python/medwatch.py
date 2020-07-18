#!/usr/bin/env python3

import os
import sys
import time
import math
import requests
import json
import yaml
import csv
import hashlib
import smtplib
import ssl
from datetime import datetime, timedelta

import pandas as pd
from bs4 import BeautifulSoup 
from pandas_datareader import data as pd_data
from yahooquery import Ticker
from googlesearch import search



# COLLECTING AND PREPPING DATA ON COMPANY INFO



def create_company_df(companies):
    '''
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
    '''

    companies = list(set(companies)) # removes duplicates

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
        if sym == 'n/a':
            print(f'Skipping {co}\n')
            marketcaps.append('n/a')
            sizes.append('n/a')
            urls.append('n/a')
            urls_pr.append('n/a')
            continue

        print(f'Checking {co} [{sym}]')
        marketcap = get_market_cap(sym)
        size = id_company_size(marketcap)
        url = get_company_url(sym)
        url_pr = get_press_release_page(url)
        
        marketcaps.append(marketcap)
        sizes.append(size)
        urls.append(url)
        urls_pr.append(url_pr[0])

    print('Search complete')

    df = pd.DataFrame({'Company': companies, 
                   'Yahoo Listed Co.': ynames, 
                   'Symbol': symbols, 
                   'Exchange': exchanges, 
                   'Market Cap': marketcaps, 
                   'Company Size': sizes, 
                   'Is American': is_us,
                   'Home URL': urls,
                   'Press Release URL': urls_pr})

    return df



def add_companies_to_csv(companies, filename):
    '''
    Generates a sub dataframe using create_company_df() and tacks that on to
    the csv specified.
    
    Parameters:
    -------------
    companies: list of str - list of company names
    filename: str - [path and] filename to csv to add data to

    Returns:
    -------------   
    n/a
    '''

    df_add = create_company_df(companies)
    df_old = pd.read_csv(filename)
    frames = [df_old, df_add]
    df = pd.concat(frames)
    df = df.drop_duplicates()

    df.to_csv(filename, index = False)



def parse_who_companies(filename):
    '''
    Automatically parses csv of World Health Organization (WHO) COVID-19
    landscape summaries and pulls list of companies

    Parameters:
    -------------
    filename: str - [path and] filename to csv of WHO data

    Returns:
    -------------    
    companies: list of str - Non-academia organizations found in csv
    '''

    df = pd.read_csv(filename)
    developers = df['Developer'].tolist()
    companies = []


    # GET LIST OF COMPANIES
    # For each row, split to individual organizations
    for developer in developers:
        if is_na(developer):
            continue
            
        organizations = developer.split('/')
        
        # For each organization, clean up formatting and add to companies list if not academia
        for organization in organizations:
            organization = organization.replace('\n', ' ')
            if not is_academia(organization):
                companies.append(organization)

    companies = list(set(companies)) # removes duplicates

    return companies



def get_company_info(company_name):
    '''
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
    '''

    # Fix formatting of name
    co = company_name.replace('.','').replace(' ','%20')
    
    query = f'http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={co}\
    &region=1&lang=en&callback=YAHOO.Finance.SymbolSuggest.ssCallback'

    response = requests.get(query)
    
    fdata = response.text.split('(', 1)[1]
    fdata = fdata.rsplit(')', 1)[0]
    data = json.loads(fdata)
    yahoo_json = data['ResultSet']['Result']


    return yahoo_json



def check_usa_mkts(yahoo_json):
    '''
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
    '''

    # Check that input is not empty
    if len(yahoo_json) == 0:
        return 'n/a', 'n/a', 'n/a', 'n/a'

    # List of US exchanges
    usa_mkts = ['NYSE', 'NASDAQ', 'AMEX', 
        'BSE', 'CBOE', 'CBOT', 
        'CME', 'CHX', 'ISE', 
        'MS4X', 'NSX', 'PHLX']
    
    # Load JSON into dataframe (**may operated directly as JSON)
    # and see if any of the exchanges listed in the query result match
    # the list of usa_mkts
    df = pd.DataFrame(yahoo_json)
    match = df.loc[df['exchDisp'].isin(usa_mkts)]
    
    # If no matches in US exchanges, return the first result
    if len(match) == 0:
        symbol = df['symbol'][0]
        exchange = df['exchDisp'][0]
        name = df['name'][0]
        usa = 'N'
    
    # Otherwise return first result matched to a US market
    else:
        symbol = match['symbol'][0]
        exchange = match['exchDisp'][0]
        name = match['name'][0]
        usa = 'Y'
        
    return symbol, exchange, name, usa



def get_company_url(ticker_symbol: str):
    '''
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
    '''

    response = Ticker(ticker_symbol, asynchronous=True)
    data = response.asset_profile
    url = data[ticker_symbol]['website']

    return url



def is_academia(organization: str):
    '''
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
    '''

    # Current list of keywords associated with academia
    keywords = ['university', 'college', 'academy']

    # Check if any of the keywords can be found in the given organization
    # Case set to lower to minimize issues with formatting
    # https://stackoverflow.com/questions/8122079/python-how-to-check-a-string-for-substrings-from-a-list
    tf = any(map(organization.lower().__contains__, keywords))

    # Return true or false
    return tf



def get_market_cap(symbol):
    '''
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
    '''
    try:
        cap = pd_data.get_quote_yahoo(symbol)['marketCap']
        cap = cap[symbol]

    except:
        print(f'Market cap for {symbol} not found.')
        cap = 'n/a'

    return cap



def id_company_size(market_cap):
    '''
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
    '''

    if market_cap == 'n/a':
        print('Market cap not defined.')
        return 'n/a'

    sizes = ['small', 'medium', 'large']
    thresh = [0, 2e9, 10e9]
    
    if market_cap > thresh[2]:
        size = sizes[2]
    elif market_cap > thresh[1]:
        size = sizes[1]
    else:
        size = sizes[0]
        
    return size



def search_google(query, num_results = 1):
    '''
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
    '''

    results = []
    num_ppg = min([num_results, 10])
    for i in search(query,           # The query you want to run
                tld = 'com',         # The top level domain
                lang = 'en',         # The language
                num = num_ppg,       # Number of results per page
                start = 0,           # First result to retrieve
                stop = num_results,  # Last result to retrieve
                pause = 3.0,         # Lapse between HTTP requests
               ):
        
        results.append(i)
    
    if len(results) == 0:
        results = ['n/a']
        
    return results



def prune_url(full_url: str):
    '''
    Method to clean up domain (e.g. removes www. or http://)
    Found having full URL can yield odd Google searches

    e.g. prune_url('https://www.google.com/')
         returns 'google.com'

    Parameters:
    -------------
    full_url: str - String of URL to be pruned

    Returns:
    -------------
    pruned_url: str - String of pruned URL
    '''
    cut_chars = ['https://', 'http://', 'www.']
    
    for cut in cut_chars:
        full_url = full_url.replace(cut, '')
    
    if full_url[-1] == '/':
        pruned_url = full_url[0:-1]
    else:
        pruned_url = full_url
    
    return pruned_url



def get_press_release_page(company_url:str):
    '''
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
    '''
    print(f'Searching for press release page on {company_url}')
    domain = prune_url(company_url) # Cleans up domain as full URL gave odd results
    # query = f'site:{domain} press releases' # Formats query
    query = f'site:{domain} investor news' # Formats query
    pr_url = search_google(query) # Searches Google and returns first result
    print(f'Found: {pr_url}')
    print('-------------------------------------\n')
    return pr_url



#########



# MONITORING WEBPAGES



def url_to_filename(base_url:str):
    '''
    Takes URL and replaces all unallowed Unix and Windows filename characters
    so that some semblance of the URL can be used as part of a filename

    e.g. url_to_filename('https://www.google.com/news/')
         returns 'google_com-news'

    Parameters:
    -------------
    base_url: str - String of URL to be converted into a filename format

    Returns:
    -------------
    filename_url: str - String of a filename based on a given URL
    '''
    
    # Cuts fluff like 'http://' and 'www'
    base_url = prune_url(base_url)
    
    # Covers both Windows and Unix
    forbidden_ascii = ['/', '\\', '\|', ':', '?',
                      '\'', '\"', '?', '*', '>', '<']
    
    for ascii_char in forbidden_ascii:
        base_url = base_url.replace(ascii_char, '-')
    
    # Replaces '.' with '_' just in case there are file extension issues
    filename_url = base_url.replace('.', '_')
    
    return filename_url



def load_cache(base_url, path='logs/'):
    '''
    Finds CACHE html file associated with url and returns the html content as
    as a string

    Parameters:
    -------------
    base_url: str - Url of cached site
    path: str = 'logs/' - Path CACHE files are located

    Returns:
    -------------
    data_cach: str - Formatted html contents
    '''

    # Convert URL to filename and read contents
    url_filename = url_to_filename(base_url)
    
    filename = f'{path}CACHE-{url_filename}.html'
    f=open(filename, 'r')
    data_cache = f.read()
    
    data_cache = " ".join(data_cache.split()) # Remove all whitespaces
    
    return data_cache



def store_cache(base_url, data, path='logs/'):
    '''
    [Over]write stored snapshot/cache of a webpage's html contents

    Parameters:
    -------------
    base_url: str - Url of site to be cached
    data: str - Html content of the site
    path: str = 'logs/' - Path where CACHE to be saved

    Returns:
    -------------
    n/a
    '''

    # Convert URL to filename and write html content into that file
    url_filename = url_to_filename(base_url)
    filename = f'{path}CACHE-{url_filename}.html'
    f = open(filename, 'w+')
    f.write(data)
    f.close()
                      


def cache_updated(base_url, data, path='logs/'):
    '''
    Checks if new html data is different from old cached html data. If changes
    found, return True, otherwise return False. If cache not found, it creates 
    a cache of the html page and returns False.

    Parameters:
    -------------
    base_url: str - Url of site to be cached
    data: str - Html content of the site
    path: str = 'logs/' - Path where CACHE to be saved

    Returns:
    -------------
    True or False - True if changes found, otherwise False (including if no 
        cache found)

    '''
    
    # Check cache exists
    url_filename = url_to_filename(base_url)
    filename = f'{path}CACHE-{url_filename}.html'
    cache_exists = os.path.isfile(filename)
    
    # Yes: Compare new html data to cached html data
    if cache_exists:
        #Opens cached html page
        data_cache = load_cache(base_url, path=path)
        f=open(filename, 'r')
        data_cache = f.read()
        
        # Loads html content as BeautifulSoup object and extracts the <body>
        soup_cache = BeautifulSoup(data_cache, 'html.parser')
        body_cache = soup_cache.find('body')
        soup_data = BeautifulSoup(data, 'html.parser')
        body_data = soup_data.find('body')
        
        # Hashes content of the new and cached body contents 
        # to make comparing more efficient
        hash_cache = hash(str(body_cache))
        hash_data = hash(str(body_data))
        
        # If cached and new data match, no updates detected, otherwise yes
        if body_cache == body_data:
            message = f'[{now_hms()}] No update from {base_url} \n'
            write_log(message, base_url, path=path)
            return False
        else:
            message = f'[{now_hms()}] Update detected from {base_url} \n'
            write_log(message, base_url, path=path)
            return True
    
    # No: Create cache of html data    
    else:
        message1 = f'[{now_hms()}] No cached webpage found for {base_url} \n'
        message2 = f'[{now_hms()}] Initializing page in {filename} \n'
        write_log(f'{message1}{message2}', base_url, path=path)
        store_cache(base_url, data, path=path)
        return False
        
        
        
def write_log(message:str, base_url, path='logs/'):
    '''
    Writes to a log txt file of any message you would like to record.

    Parameters:
    -------------
    message: str - Message to be written to log
    base_url: str - Url of site to be cached
    path: str = 'logs/' - Path where LOG to be saved

    Returns:
    -------------
    n/a
    '''
    print(message)
    url_filename = url_to_filename(base_url)
    filename = f'{path}LOG-{url_filename}.txt'

    if os.path.exists(filename):
        append_write = 'a' 
    else:
        append_write = 'w'

    f = open(filename, append_write)
    f.write(message)
    f.close()



def get_anchors(html_data):
    '''
    Takes BeautifulSoup object and searches <body> for anchors

    Parameters:
    -------------
    html_data: bs4 - Html content of webpage

    Returns:
    -------------
    anchors: list of bs4 - List of all anchors (including tags)
    '''
    
    # If html_data does not have a <body>, assume the data passed if the <body>
    if html_data.find('body') == None:
        html_body = html_data
    else:
        html_body = html_data.find('body')   
        
    anchors = list(html_body.find_all('a'))

    return anchors



def parse_anchors(anchors):
    '''
    Takes list of anchors and returns the hrefs and content of each

    Parameters:
    -------------
    anchors: list of bs4 - All anchors to be parsed

    Returns:
    -------------
    hrefs: list of str - All href content found in each anchor
    contents: list of str - All content/title found in each anchor
    '''
    hrefs = []
    content = []
    
    for anchor in anchors:
        hrefs.append(anchor.get('href'))
        content.append(anchor.text)
    
    return hrefs, content



def get_new_diff(new_data, old_data):
    '''
    Find what is new in new_data that cannot be found in old_data

    Parameters:
    -------------
    new_data: list - e.g. list of anchors from newly pinged webpage
    old_data: list - e.g. list of anchors from cached webpage

    Returns:
    -------------
    diff: list - e.g. list of new anchors found
    '''

    diff = list(set(new_data) - set(old_data))
    return diff



def load_keywords_csv(filename:str):
    '''
    Loads csv delimited by linebreaks and loads them into a list

    Parameters:
    -------------
    filename: str - path and filename to the csv file of keywords

    Returns:
    -------------
    keywords: list of str - list of the keywords that were in the csv
    '''

    f = open(filename, 'r')
    reader = csv.reader(f, delimiter='\n')
    kws = list(reader)
    
    keywords = []
    for keyword in kws:
        keywords.append(keyword[0])

    return keywords


def check_for_keywords(anchors, keywords, keywords_ignore = ['']):
    '''
    Takes a list of anchors and returns a subset of anchors in which a keyword
    was found.
    
    Parameters:
    -------------
    anchors: list - Anchor tags of interest
    keywords: list - Keywords to search in anchor tags
    keywords_ignore: list - Keywords to mark anchor is not relevant if present

    Returns:
    -------------
    rel_anchors: list - Subset of anchors which consist of relevant anchors
        in which a keyword was found
    '''

    # Format keywords to minimize discrepencies
    for ii, keyword in enumerate(keywords):
        keyword = keyword.lower()
        keywords[ii] = keyword

    # Parse all anchors and check if any contain keywords
    # Append to rel_anchors if a match
    hrefs, contents = parse_anchors(anchors)

    rel_anchors = []
    for anchor, href, content in zip(anchors, hrefs, contents):
        if href == None:
            continue
            
        href = href.lower()
        content = content.lower()

        # Check if href or content contain any of the keywords
        href_kw = any(map(href.__contains__, keywords))
        content_kw = any(map(content.__contains__, keywords))

        # Check if any of the "ignore keywords" exist
        href_kwi = any(map(href.__contains__, keywords_ignore))
        content_kwi = any(map(href.__contains__, keywords_ignore))

        if (href_kw or content_kw): 
            if (href_kwi or content_kwi):
                print('Relevant keywords found but not added due to ignore keywords.')
            else:
                rel_anchors.append(anchor)

    return rel_anchors



def send_email_notification(message, receive_addresses, sender_creds):
    '''
    Send an email to a list of recipients and log 
    For now, the send address must be a gmail account
    
    Parameters:
    -------------
    message - String or possibly html content
    receive_addresses: list of str - email addresses of recipients
    send_creds: str - filename of sender credentials

    Returns:
    -------------
    n/a
    '''

    sender_address, password = get_creds(sender_creds)
    port = 465
    smtp_server = "smtp.gmail.com"
    
    # Create a secure SSL context
    context = ssl.create_default_context()
    
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(sender_address, password)
        for receive_address in receive_addresses:
            server.sendmail(sender_address, receive_address, message)



def get_listserv(filename):
    params = yaml.safe_load(open(filename))
    emails = params['emails']

    return emails


    
def get_creds(filename):
    params = yaml.safe_load(open(filename))
    username = params['username']
    password = params['password']

    return username, password



def href_to_link(href, domains=['']):
    '''
    Takes href and checks if the link is valid. If not, it will
    cycle through a list of base_urls to see if any yield a 
    '''

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

    href = href.strip()

    if domains[0] != '':
        domains.insert(0, '')

    for domain in domains:
        temp_url = merge_link(domain, href)
        temp_url = add_protocol(temp_url)

        if not '.' in temp_url:
            continue

        try:
            r = requests.head(temp_url, headers = headers)
            if r.status_code == 200:
                return temp_url
        except:
            print(f'{temp_url} failed')
            

        try:
            print(switch_protocol(temp_url))
            r = requests.get(switch_protocol(temp_url), headers = headers)
            if r.status_code == 200:
                return switch_protocol(temp_url)
        except:
            print(f'{switch_protocol(temp_url)} failed')
            pass

    return href





def merge_link(url_domain, url_path):
    '''
    Combines a url base and extension, taking into consideration
    the number of slashes

    e.g. merge_link('reddit.com/', '/r/nba') 
         merge_link('reddit.com', 'r/nba')
         merge_link('reddit.com/', 'r/nba')
         merge_link('reddit.com', 'r/nba')
         all return 'reddit.com/r/nba'
    
    Parameters:
    -------------
    url_domain: str - [Sub]domain name
    url_path: str - Portion after domain

    Returns:
    -------------
    url_full: str - Combined URL
    '''

    # Ensure domain is not empty
    if url_domain.strip() == '':
        return url_path

    # Strip / at end of domain
    if url_domain[-1] == '/':
        url_domain = url_domain[0:-1]

    # Strip / at beginning of path
    if url_path[0] == '/':
        url_path = url_path[1:]

    url_full = '/'.join([url_domain, url_path])

    return url_full



def add_protocol(url, protocol='https://'):
    '''
    Checks if http:// or https:// protocol is defined
    if not, adds https:// by default

    e.g. add_protocol('reddit.com')
         returns 'https://reddit.com'

    Parameters:
    -------------
    url: str - Given URL
    protocol: str - Defaults to https://, can specify http://

    Returns:
    -------------
    url: str - URL with protocol
    '''

    if url.strip()[0:4] != 'http':
        url = ''.join([protocol, url])

    return url



def switch_protocol(url):
    '''
    Switches https:// to http:// and vice versa

    e.g. switch_protocol('http://www.reddit.com')
         returns 'https://www.reddit.com'
         switch_protocol('http://www.reddit.com')
         returns 'https://www.reddit.com'
    
    Parameters:
    -------------
    url: str - Given URL

    Returns:
    -------------
    url: str - URL with new protocol
    '''

    if url[0:8] == 'https://':
        url = ''.join(['http://',url[8:]])
    elif url[0:7] == 'http://':
        url = ''.join(['https://',url[7:]])
    else:
        print('http:// or https:// protocol not found')
    
    return url



##########



# SYSTEM FUNCTIONS



def now_hms():
    '''
    Get current time in HH:MM:SS format
    **Plan to add timezones with pytz package

    e.g. now_hms()
         returns '11:00:00'

    Parameters:
    -------------
    n/a

    Returns:
    -------------
    current_time: str - Current time in HH:MM:SS
    '''

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    return current_time



def is_na(subject):
    '''
    Checks if input is NaN which may be in multiple formats including a string
    ('n/a', or 'NaN'), float, or boolean.

    e.g. is_na('n/a')        returns True
         is_na(nan)          returns True
         is_na(False)        returns True
         is_na(1234)         returns False
         is_na('google.com') returns False

    Parameters:
    -------------
    subject: - Not type specific

    Returns:
    -------------
    True/False
    '''

    if isinstance(subject, str):
        na_versions = ['n/a', 'nan']
        if subject.lower() in na_versions:
            return True
        else: 
            return False
    elif isinstance(subject, float):
        if math.isnan(subject):
            return True
    elif isinstance(subject, bool):
        return not subject
    else:
        return False


def gen_next_time(intervals, start_time=[6,0,0], end_time=[23,0,0]):
    '''
    Function that generates the next datetime based off a specified
    interval

    Parameters:
    -------------
    interval: float - number of seconds between start of next datetime
    start_time: tuple of length 3 - (H, M, S)
    end_time: tuple of length 3 - (H, M, S)

    Yields:
    -------------
    next_datetime: datetime - 
    '''
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day

    start_time = datetime(year, month, day, 
        start_time[0], start_time[1], start_time[2], 0)

    end_time = datetime(year, month, day, 
        end_time[0], end_time[1], end_time[2], 0)

    next_datetime = start_time

    if end_time < now:
        end_time += timedelta(days=1)


    while next_datetime < end_time:

        if next_datetime < now:
            while next_datetime < now:
                next_datetime += timedelta(seconds=intervals)
        else:
            next_datetime += timedelta(seconds=intervals)

        yield next_datetime








