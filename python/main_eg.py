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

# For requests.get()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
}

# CSV generated from mw.create_company_df() 
LIST_COMPANIES = '../datasets/updated_company_list.csv' 
DIR_LOG = '../logs/' # Path to save logs
DIR_KEYWORDS = '../datasets/keywords_covid.csv' # List of keywords
DIR_LISTSERV = '../cfg_eg/email_examples.yaml' # List of emails to send notifications to
DIR_SENDCREDS = '../cfg_eg/sender_email_creds.yaml' # Credentials of sender's email


while True:
    start_hms = [6, 0, 0]
    end_hms = [23, 0, 0]

    time_gen = mw.gen_next_time(120, start_time=start_hms, end_time=end_hms)

    starttime, endtime = mw.gen_start_end_times(start_time=start_hms, end_time=end_hms)

    if now < starttime:
        print(f"Will start at {starttime} EST")
        pause.until(starttime)

    now = datetime.now()
    print(f"Beginning {now}")

    while now < endtime:
        # Pause until next time cycle
        time_check = next(time_gen)
        if datetime.now() < time_check:
            pause.until(time_check)

        # Prepare blank email message and list of companies hit
        email_msg = []
        email_companies = []

        df = pd.read_csv(LIST_COMPANIES)
        df = df.drop_duplicates()

        # Keywords loaded each time in case new ones added
        keywords = mw.load_keywords_csv(DIR_KEYWORDS)

        for ii in range(len(df)):
            co, yco, sym, exch, mkcap, size, am, url_home, url_pr = df.iloc[ii].T.values

            # Skip if entry is n/a for some reason
            if mw.is_na(url_pr):
                print("\n----------------------------------")
                timestamp = datetime.now()
                print(f"[{timestamp}] Skipping {co}")
                print("----------------------------------\n")
                continue

            # Otherwise, proceed
            print("\n----------------------------------")
            print(f"Checking {yco}")

            try:
                r = requests.get(url_pr, headers=HEADERS)
            except:
                message = f"CONNECTION FAILED! - Status Code: {r.status_code}\n"
                print(f"\n{message}")
                mw.write_log(message, url_pr)
                continue

            page = r.text
            page = " ".join(page.split())
            soup = BeautifulSoup(page, "html.parser")
            body = soup.find("body")

            if not body:
                message = f"Cannot find <body></body> for {url_pr}"
                mw.write_log(message, url_pr)
                continue

            # Check if page is different from cached page
            has_update = mw.cache_updated(url_pr, page)
            current_time = mw.now_hms()

            # print(has_update)
            print("\n")

            if has_update:
                # Get new anchors
                anchors = mw.get_anchors(soup)

                # Load old page/anchors
                old_page = mw.load_cache(url_pr)
                old_soup = BeautifulSoup(old_page, "html.parser")
                old_body = old_soup.find("body")
                old_anchors = mw.get_anchors(old_soup)

                # List all new anchors
                diff_anchors = mw.get_new_diff(anchors, old_anchors)

                if len(diff_anchors) > 0:
                    diff_hrefs, diff_contents = mw.parse_anchors(diff_anchors)
                    message = f"[{current_time}] New links found: \n---------------"
                    mw.write_log(message, url_pr)

                    rel_anchors, rel_keywords = mw.check_for_keywords(
                        diff_anchors, keywords
                    )
                    rel_hrefs, rel_contents = mw.parse_anchors(rel_anchors)

                    if len(rel_anchors) > 0:
                        email_companies.append(co)
                        email_msg.append(f"\n[{current_time}] {yco} - {url_pr}")
                        email_msg.append("------------------------\n")
                        all_keywords_found = set(
                            [
                                item
                                for sublist in rel_keywords
                                for item in sublist
                                if item != ""
                            ]
                        )

                        keywords_found = ", ".join(all_keywords_found)
                        message = f"Links related to {keywords_found}:"
                        mw.write_log(message, url_pr)

                        for rel_href, rel_content, anchor_keywords in zip(
                            rel_hrefs, rel_contents, rel_keywords
                        ):
                            message = f"{rel_content} :: {mw.href_to_link(rel_href, [url_pr, url_home])}"
                            email_msg.append(message)
                            mw.write_log(message, url_pr)
                            tmp_list = ", ".join(anchor_keywords)
                            message = f"Link marked because of keywords: {tmp_list}"
                            email_msg.append(message)
                            mw.write_log(message, url_pr)

                    else:
                        message = f"New links NOT related to {keywords}\n"
                        mw.write_log(message, url_pr)

                        for diff_href, diff_content in zip(diff_hrefs, diff_contents):
                            message = f"{diff_href}  ::  {diff_content}"
                            mw.write_log(message, url_pr)

                else:
                    message = f"[{current_time}] Update detected but no new anchors"
                    mw.write_log(message, url_pr)

                mw.store_cache(url_pr, page)
                print("\n\n")

        print("-----------------\nSweep Complete")

        if len(email_msg) > 0:
            receive_addresses = mw.get_listserv(DIR_LISTSERV)
            tmp_list = ", ".join(all_keywords_found)
            email_msg.insert(
                0,
                f"New links related to the following keywords have been detected! \n{tmp_list}\n",
            )

            email_companies = ", ".join(email_companies)
            email_msg.insert(
                0,
                f"Subject: Medwatch update from {email_companies} [{mw.now_hms()}]\n\n",
            )

            email_msg = "\n".join(email_msg).encode("utf-8")

            mw.send_email_notification(email_msg, receive_addresses, DIR_SENDCREDS)

        now = datetime.now()

    print("Done for the day")
