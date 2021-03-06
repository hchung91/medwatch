#!/usr/bin/env python3

import os
import sys
import time
import requests
import yaml

from datetime import datetime

import medwatch as mw 
from bs4 import BeautifulSoup 
import pandas as pd
import pause


# CSV generated from mw.create_company_df() 
company_file = '../datasets/updated_company_list.csv' 

log_dir = '../logs/' # Path to save logs
keywords_dir = '../datasets/keywords_covid.csv' # List of keywords

listserv_dir = '../cfg_eg/email_examples.yaml' # List of emails to send notifications to
sendercreds_dir = '../cfg_eg/sender_email_creds.yaml' # Credentials of sender's email

while True:
    time_gen = mw.gen_next_time(120, start_time=[6,0,0], end_time=[23,0,0])

    organizations = ['FDA']
    gov_urls = ['https://www.fda.gov/news-events/fda-newsroom/press-announcements']
    keywords_ignore = ['Daily Roundup']
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}


    now = datetime.now()

    year = now.year
    month = now.month
    day = now.day

    if now < datetime(year,month,day,6,00):
        print('Will start at 6am EST')
        pause.until(datetime(year,month,day,6,00))

    print(f'[{now}] Beginning government organization check')
    while now < datetime(year,month,day,23,00):
        time_check = next(time_gen)
        if datetime.now() < time_check:
            pause.until(time_check)

        email_msg = []
        email_organizations = []

        keywords = mw.load_keywords_csv(keywords_dir)

        for org, url, kw_ignore in zip(organizations, gov_urls, keywords_ignore):       
            print('\n----------------------------------')
            print(f'[{mw.now_hms()}] Checking {org}')

            try:
                r = requests.get(url, headers=headers)
            except:
                message = f'CONNECTION FAILED! - Status Code: {r.status_code}\n'
                print(f'\n{message}')
                mw.write_log(message, url)
                continue

            page = r.text
            page = " ".join(page.split())
            soup = BeautifulSoup(page, 'html.parser')
            body = soup.find('body')

            if not body:
                message = f'Cannot find <body></body> for {url}'
                mw.write_log(message, url)
                continue

            anchors = mw.get_anchors(soup)

            has_update = mw.cache_updated(url, page)
            current_time = mw.now_hms()

            print(has_update)
            print('\n')

            if has_update:
                old_page = mw.load_cache(url)
                old_soup = BeautifulSoup(old_page, 'html.parser')
                old_body = old_soup.find('body')
                old_anchors = mw.get_anchors(old_soup)
                diff_anchors = mw.get_new_diff(anchors, old_anchors)
                diff_hrefs, diff_contents = mw.parse_anchors(diff_anchors)
                
                if len(diff_anchors) > 0:
                    message = f'[{current_time}] New links found: \n---------------\n'
                    mw.write_log(message, url)

                    rel_anchors = mw.check_for_keywords(diff_anchors, keywords, keywords_ignore = kw_ignore)
                    rel_hrefs, rel_contents = mw.parse_anchors(rel_anchors)

                    if len(rel_anchors) > 0:
                        email_organizations.append(org)
                        email_msg.append(f'\n[{current_time}] {org} - {url}')
                        email_msg.append('------------------------')
                        message=f'Links related to {keywords}:\n'
                        mw.write_log(message, url)
                        
                        for rel_href, rel_content in zip(rel_hrefs, rel_contents):
                            message=f'{rel_content} :: {rel_href}'
                            email_msg.append(message)
                            mw.write_log(message, url)

                    else:
                        message=f'[{current_time}] New links not related to {keywords}\n'
                        mw.write_log(message,url)

                        for diff_href, diff_content in zip(diff_hrefs, diff_contents):
                            message = f'{diff_href}  ::  {diff_content}'
                            mw.write_log(message, url)
                        
                else:
                    message = f'[{current_time}] Update detected but no new anchors'
                    mw.write_log(message, url)
                    
                    
                mw.store_cache(url, page)
                print('\n\n')
        
       
        print('-----------------\nSweep Complete')

        if len(email_msg) > 0:
            receive_addresses = mw.get_listserv(listserv_dir)

            email_msg.insert(0, f'New links related to the following keywords have been detected! \n{keywords}\n')
            
            email_organizations = ', '.join(email_organizations)
            email_msg.insert(0, f'Subject: Medwatch update from {email_organizations} [{mw.now_hms()}]\n\n')

            email_msg = u'\n'.join(email_msg).encode('utf-8')

            mw.send_email_notification(email_msg, receive_addresses, sendercreds_dir)


        now = datetime.now()

    print('Done for the day')
