#!/usr/bin/env python3

import os
import sys
import requests
import json
import yaml
import csv
import hashlib
import smtplib
import ssl
import pickle
import pytz

from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from tzlocal import get_localzone


# MONITORING WEBPAGES


def url_to_filename(base_url: str):
    """
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
    """

    # Cuts fluff like 'http://' ~and 'www'~
    base_url = prune_url(base_url, cut_chars=["https://", "http://", "www."])

    # Covers both Windows and Unix
    forbidden_ascii = ["/", "\\", "\|", ":", "?", "'", '"', "?", "*", ">", "<"]

    for ascii_char in forbidden_ascii:
        base_url = base_url.replace(ascii_char, "-")

    # Replaces '.' with '_' just in case there are file extension issues
    filename_url = base_url.replace(".", "_")

    return filename_url


def load_cache(base_url, path="logs/"):
    """
    Finds CACHE html file associated with url and returns the html content as
    as a string

    Parameters:
    -------------
    base_url: str - Url of cached site
    path: str = 'logs/' - Path CACHE files are located

    Returns:
    -------------
    data_cach: str - Formatted html contents
    """

    # Convert URL to filename and read contents
    url_filename = url_to_filename(base_url)

    filename = f"{path}CACHE-{url_filename}.html"
    f = open(filename, "r")
    data_cache = f.read()

    data_cache = " ".join(data_cache.split())  # Remove all whitespaces

    return data_cache


def store_cache(base_url, data, path="logs/"):
    """
    [Over]write stored snapshot/cache of a webpage's html contents

    Parameters:
    -------------
    base_url: str - Url of site to be cached
    data: str - Html content of the site
    path: str - 'logs/' - Path where CACHE to be saved

    Returns:
    -------------
    n/a
    """

    # Convert URL to filename and write html content into that file
    url_filename = url_to_filename(base_url)
    filename = f"{path}CACHE-{url_filename}.html"
    f = open(filename, "w+")
    f.write(data)
    f.close()


def store_anchors(base_url, anchors, path="logs/"):
    """
    Append to a list of relevant anchors for a given URL

    Parameters:
    -------------
    base_url: str - Url of site to be cached
    data: str - new anchors to add
    path: str - 'logs/' - Path where ANCHORS to be saved

    Returns:
    -------------
    n/a
    """

    url_filename = url_to_filename(base_url)
    filename = f"{path}ANCHORS-{url_filename}.txt"

    if os.path.isfile(filename):
        with open(filename, "rb") as fp:
            all_anchors = pickle.load(fp)
        all_anchors.append(anchors)
    else:
        all_anchors = anchors

    with open(filename, "wb") as fp:
        pickle.dump(all_anchors, fp)


def datetime_header_format(_datetime):
    """
    Takes a datetime object and converts it to string format that
    can be interpretted by request headers

    Parameters:
    -------------
    _datetime: datetime object - given in any timezone

    Returns:
    -------------
    _datetime: str - formatted string in GMT
    """

    _datetime = _datetime.astimezone(pytz.timezone('GMT'))
    _datetime = _datetime.strftime('%a, %d %b %Y %H:%M:%S GMT')
    return _datetime
    

def localize_tz(_datetime):
    """
    Takes a datetime object and converts it to the local timezone

    Parameters:
    -------------
    _datetime: datetime object - given in any timezone

    Returns:
    -------------
    _datetime: datetime object - given in local timezone

    """

    local_tz = str(get_localzone())
    _datetime = _datetime.astimezone(pytz.timezone(local_tz))
    
    return _datetime


def url_updated(url, since_datetime):
    """
    Checks if a url has been updated since a certain datetime using the
    If-Modified-Since header

    Parameters:
    -------------
    url: str - url being monitored
    since_datetime: datetime object - check if changes have been made since this
        datetime (must be in UTC/GMT)

    Returns:
    -------------
    True or False - True if changes found, otherwise False
    """

    headers = {"If-Modified-Since": t, "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"}
    since_datetime = datetime_header_format(since_datetime)
    r = requests.header(url, headers=headers)

    status_code = r.status_code

    if status_code == 200:
        return True
    elif status_code == 204:
        return False
    else:
        print(f"Update not detected with status code {status_code}")
        return False


def cache_updated(base_url, data, path="logs/"):
    """
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

    """

    # Check cache exists
    url_filename = url_to_filename(base_url)
    filename = f"{path}CACHE-{url_filename}.html"
    cache_exists = os.path.isfile(filename)

    # Yes: Compare new html data to cached html data
    if cache_exists:
        # Opens cached html page
        data_cache = load_cache(base_url, path=path)
        f = open(filename, "r")
        data_cache = f.read()

        # Loads html content as BeautifulSoup object and extracts the <body>
        soup_cache = BeautifulSoup(data_cache, "html.parser")
        body_cache = soup_cache.find("body")
        soup_data = BeautifulSoup(data, "html.parser")
        body_data = soup_data.find("body")

        # Hashes content of the new and cached body contents
        # to make comparing more efficient
        hash_cache = hash(str(body_cache))
        hash_data = hash(str(body_data))

        # If cached and new data match, no updates detected, otherwise yes
        if body_cache == body_data:
            message = f"[{now_hms()}] No update from {base_url} \n"
            write_log(message, base_url, path=path)
            return False
        else:
            message = f"[{now_hms()}] Update detected from {base_url} \n"
            write_log(message, base_url, path=path)
            return True

    # No: Create cache of html data
    else:
        message1 = f"[{now_hms()}] No cached webpage found for {base_url} \n"
        message2 = f"[{now_hms()}] Initializing page in {filename} \n"
        write_log(f"{message1}{message2}", base_url, path=path)
        store_cache(base_url, data, path=path)
        return False


def write_log(message: str, base_url, path="logs/"):
    """
    Writes to a log txt file of any message you would like to record.

    Parameters:
    -------------
    message: str - Message to be written to log
    base_url: str - Url of site to be cached
    path: str = 'logs/' - Path where LOG to be saved

    Returns:
    -------------
    n/a
    """
    print(message)
    url_filename = url_to_filename(base_url)
    filename = f"{path}LOG-{url_filename}.txt"

    if os.path.exists(filename):
        append_write = "a"
    else:
        append_write = "w"

    f = open(filename, append_write)
    f.write(message)
    f.close()


def get_anchors(html_data):
    """
    Takes BeautifulSoup object and searches <body> for anchors

    Parameters:
    -------------
    html_data: bs4 - Html content of webpage

    Returns:
    -------------
    anchors: list of bs4 - List of all anchors (including tags)
    """

    # If html_data does not have a <body>, assume the data passed if the <body>
    if html_data.find("body") == None:
        html_body = html_data
    else:
        html_body = html_data.find("body")

    anchors = list(html_body.find_all("a"))

    return anchors


def parse_anchors(anchors):
    """
    Takes list of anchors and returns the hrefs and content of each

    Parameters:
    -------------
    anchors: list of bs4 - All anchors to be parsed

    Returns:
    -------------
    hrefs: list of str - All href content found in each anchor
    contents: list of str - All content/title found in each anchor
    """
    hrefs = []
    content = []

    for anchor in anchors:
        hrefs.append(anchor.get("href"))
        content.append(anchor.text)

    return hrefs, content


def get_new_diff(new_data, old_data):
    """
    Find what is new in new_data that cannot be found in old_data

    Parameters:
    -------------
    new_data: list - e.g. list of anchors from newly pinged webpage
    old_data: list - e.g. list of anchors from cached webpage

    Returns:
    -------------
    diff: list - e.g. list of new anchors found
    """

    diff = list(set(new_data) - set(old_data))
    return diff


def load_keywords_csv(filename: str):
    """
    Loads csv delimited by linebreaks and loads them into a list

    Parameters:
    -------------
    filename: str - path and filename to the csv file of keywords

    Returns:
    -------------
    keywords: list of str - list of the keywords that were in the csv
    """

    f = open(filename, "r")
    reader = csv.reader(f, delimiter="\n")
    kws = list(reader)

    keywords = []
    for keyword in kws:
        keywords.append(keyword[0])

    return keywords


def check_for_keywords(anchors, keywords, keywords_ignore=[""]):
    """
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
    """

    # Format keywords to minimize discrepencies
    for ii, keyword in enumerate(keywords):
        keyword = keyword.lower()
        keywords[ii] = keyword

    # Parse all anchors and check if any contain keywords
    # Append to rel_anchors if a match
    hrefs, contents = parse_anchors(anchors)

    rel_anchors = []
    rel_keywords_all = []
    for anchor, href, content in zip(anchors, hrefs, contents):
        if href == None:
            continue

        href = href.lower()
        content = content.lower()

        # Check if href or content contain any of the keywords
        href_kw = any(map(href.__contains__, keywords))
        content_kw = any(map(content.__contains__, keywords))

        # Can combine with above?
        href_gen = map(href.__contains__, keywords)
        content_gen = map(content.__contains__, keywords)

        # Check if any of the "ignore keywords" exist
        href_kwi = any(map(href.__contains__, keywords_ignore))
        content_kwi = any(map(href.__contains__, keywords_ignore))

        rel_keywords = []
        if href_kw or content_kw:
            if href_kwi or content_kwi:
                print("Relevant keywords found but not added due to ignore keywords.")

            else:
                rel_anchors.append(anchor)

                for keyword in keywords:
                    if next(href_gen) or next(content_gen):
                        rel_keywords.append(keyword)

                print(f"Match because of following keywords: {rel_keywords}")

        if not rel_keywords:
            rel_keywords = [""]

        rel_keywords_all.append(rel_keywords)

    return rel_anchors, rel_keywords_all


def send_email_notification(message, receive_addresses, sender_creds):
    """
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
    """

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
    emails = params["emails"]

    return emails


def get_creds(filename):
    params = yaml.safe_load(open(filename))
    username = params["username"]
    password = params["password"]

    return username, password


def href_to_link(href, domains=[""]):
    """
    Takes href and checks if the link is valid. If not, it will
    cycle through a list of base_urls to see if any yield a 
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }

    href = href.strip()

    if domains[0] != "":
        domains.insert(0, "")

    for domain in domains:
        temp_url = merge_link(domain, href)
        temp_url = add_protocol(temp_url)

        if not "." in temp_url:
            continue

        try:
            r = requests.head(temp_url, headers=headers)
            if r.status_code == 200:
                return temp_url
        except:
            print(f"{temp_url} failed")

        try:
            print(switch_protocol(temp_url))
            r = requests.get(switch_protocol(temp_url), headers=headers)
            if r.status_code == 200:
                return switch_protocol(temp_url)
        except:
            print(f"{switch_protocol(temp_url)} failed")
            pass

    return href


def merge_link(url_domain, url_path):
    """
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
    """

    # Ensure domain is not empty
    if url_domain.strip() == "":
        return url_path

    # Strip / at end of domain
    if url_domain[-1] == "/":
        url_domain = url_domain[0:-1]

    # Strip / at beginning of path
    if url_path[0] == "/":
        url_path = url_path[1:]

    url_full = "/".join([url_domain, url_path])

    return url_full


def add_protocol(url, protocol="https://"):
    """
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
    """

    if url.strip()[0:4] != "http":
        url = "".join([protocol, url])

    return url


def switch_protocol(url):
    """
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
    """

    if url[0:8] == "https://":
        url = "".join(["http://", url[8:]])
    elif url[0:7] == "http://":
        url = "".join(["https://", url[7:]])
    else:
        print("http:// or https:// protocol not found")

    return url


def compose_email(message_body, organization, domain, target_url, time_requested='', keywords=[]):
    """
    Composes full email message by adding subjects and headers
    
    Parameters:
    -------------
    message_body: str - full email message sans subject and headers
    organization: str - name of organization
    domain: str - domain (home page) of the organization being followed
    target_url: str - exact url of the page that was being monitored
    time_requested: formatted datetime - time the webpage was pulled
    keywords: list of str - all keywords in the feed for the target url

    Returns:
    -------------
    email_msg: str - full email message as a string
    """

    if time_requested == '':
        time_requested = datetime.now()
        time_requested = time_requested.strftime('%a, %d %b %Y %H:%M:%S')

    email_msg = []

    email_msg.append(f'\n[{time_requested}] {organization} - {domain}')
    email_msg.append('------------------------')

    email_msg.append(message_body)    

    if keywords != []:
        email_msg.insert(0, f'New links related to the following keywords have been detected! \n{keywords}\n')
    else:
        email_msg.insert(0, f'New links related to keywords of interest found!')

    email_msg.insert(0, f'Subject: Medwatch update from {organization} [{time_requested}]\n\n')
  
    email_msg = u'\n'.join(email_msg).encode('utf-8')

    return email_msg


def anchors_to_message(anchors, keywords, target_url, home_url='', other_urls=[]):   
    """
    Composes body of the email from a list of relevant anchors

    Parameters:
    -------------
    anchors: list of bs4 objects - list of anchors to be included in the message
    keywords: list of list of str - list of lists of same length as anchors. each list
        has a list of keywords associated with each anchor.
    target_url: str - exact url of the page that was being monitored
    home_url: str - domain (home page) of the organization being followed
    other_urls: list of str - other URLs to check against for href_to_link

    Returns:
    -------------
    msg: str - email message body
    """

    msg =[]

    urls_all = []
    urls_all.append(target_url)
    
    if home_url != '':
        urls_all.append(home_url)
    else:
        home_url = target_url

    url_all.extend(other_urls)

    for anchor, kws in zip(anchors, keywords):
        href, content = parse_anchor(anchor)
        message=f'{content} :: {href_to_link(href, urls_all)}'
        msg.append(message)
        write_log(message, target_url)

        kw_list = ', '.join(kws)
        message=f'Link marked because of keywords: {kw_list}'
        msg.append(message)
        write_log(message, target_url)
        msg.append('\n----\n')    

    return msg                 
