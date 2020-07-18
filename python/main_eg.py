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

    now = datetime.now()

    year = now.year
    month = now.month
    day = now.day

    starttime = datetime(year, month, day, 6, 0)

    if now.hour >= 23:
        starttime = starttime + timedelta(days = 1)

    if now < starttime:
        print(f'Will start at {starttime} EST')
        pause.until(starttime)

    now = datetime.now()
    print(f'Beginning {now}')
    while now < datetime(year,month,day,23,00):
        time_check = next(time_gen)
        if datetime.now() < time_check:
            pause.until(time_check)
        
        email_msg = []
        email_companies = []

        df = pd.read_csv(company_file)
        df = df.drop_duplicates()
        
        # cos = df['Company'].tolist()
        # ycos = df['Yahoo Listed Co.'].tolist()
        # syms = df['Symbols'].tolist()
        # pr_urls = df['Press Release URL'].tolist()

        keywords = mw.load_keywords_csv(keywords_dir)

        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

        for ii in range(len(df)): 
            co, yco, sym, exch, mkcap, size, am, url_home, url_pr = \
            df.iloc[ii].T.values

            
            if not mw.is_na(url_pr):
                print('\n----------------------------------')
                print(f'Checking {yco}')
                
                try:
                    r = requests.get(url_pr, headers=headers)
                except:
                    message = f'CONNECTION FAILED! - Status Code: {r.status_code}\n'
                    print(f'\n{message}')
                    mw.write_log(message, url_pr)
                    continue
                    
                page = r.text
                page = " ".join(page.split())
                soup = BeautifulSoup(page, 'html.parser')
                body = soup.find('body')
                
                if not body:
                    message = f'Cannot find <body></body> for {url_pr}'
                    mw.write_log(message, url_pr)
                    continue
                    
                anchors = mw.get_anchors(soup)
                
                has_update = mw.cache_updated(url_pr, page)
                current_time = mw.now_hms()
                
                # print(has_update)
                print('\n')
             
                if has_update:
                    old_page = mw.load_cache(url_pr)
                    old_soup = BeautifulSoup(old_page, 'html.parser')
                    old_body = old_soup.find('body')
                    old_anchors = mw.get_anchors(old_soup)
                    diff_anchors = mw.get_new_diff(anchors, old_anchors)
                    
                    if len(diff_anchors) > 0:
                        diff_hrefs, diff_contents = mw.parse_anchors(diff_anchors)
                        message = f'[{current_time}] New links found: \n---------------'
                        mw.write_log(message, url_pr)

                        rel_anchors, rel_keywords = mw.check_for_keywords(diff_anchors, keywords)
                        rel_hrefs, rel_contents = mw.parse_anchors(rel_anchors)

                        if len(rel_anchors) > 0:
                            email_companies.append(co)
                            email_msg.append(f'\n[{current_time}] {yco} - {url_pr}')
                            email_msg.append('------------------------')
                            all_keywords_found = set([item for sublist in rel_keywords for item in sublist if item != ''])
                            message=f'Links related to {', '.join(all_keywords_found)}:'
                            mw.write_log(message, url_pr)
                            
                            for rel_href, rel_content, anchor_keywords in zip(rel_hrefs, rel_contents, rel_keywords):
                                message=f'{rel_content} :: {mw.href_to_link(rel_href, [url_pr, url_home])}'
                                email_msg.append(message)
                                mw.write_log(message, url_pr)
                                message=f'Link marked because of keywords: {', '.join(anchor_keywords)}'
                                email_msg.append(message)
                                mw.write_log(message, url_pr)

                        else:
                            message=f'New links NOT related to {keywords}\n'
                            mw.write_log(message,url_pr)

                            for diff_href, diff_content in zip(diff_hrefs, diff_contents):
                                message = f'{diff_href}  ::  {diff_content}'
                                mw.write_log(message, url_pr)
                            
                    else:
                        message = f'[{current_time}] Update detected but no new anchors'
                        mw.write_log(message, url_pr)
                        
                    
                    mw.store_cache(url_pr, page)
                    print('\n\n')
            
            else:
                print('\n----------------------------------')
                print(f'Skipping {co}')
                print('\n----------------------------------\n\n')

        print('-----------------\nSweep Complete')

        if len(email_msg) > 0:
            receive_addresses = mw.get_listserv(listserv_dir)
            email_msg.insert(0, f'New links related to the following keywords have been detected! \n{', '.join(all_keywords_found)}\n')
            
            email_companies = ', '.join(email_companies)
            email_msg.insert(0, f'Subject: Medwatch update from {email_companies} [{mw.now_hms()}]\n\n')

            email_msg = u'\n'.join(email_msg).encode('utf-8')

            mw.send_email_notification(email_msg, receive_addresses, sendercreds_dir)


        now = datetime.now()

    print('Done for the day')