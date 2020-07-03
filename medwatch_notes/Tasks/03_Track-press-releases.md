# 3. Track press releases

## Compile list of all the companies' webpages

Starting points:
https://medium.com/the-red-fish/automate-finding-a-company-url-with-a-company-name-on-google-sheets-for-free-in-3-easy-steps-7ea77280bcdc

https://towardsdatascience.com/current-google-search-packages-using-python-3-7-a-simple-tutorial-3606e459e0d4



## From homepage, find press releases page

Used package which utilizes Google's API



## Monitor press release pages for updates

- Get a snapshot of each press release page using BeautifulSoup and store it
- Continue grabbing snapshots and comparing it to what is stored
- If new snapshot is the same as the saved snapshot, delete and wait until next ping (may need to learn things like ignoring time, ip addresses, etc)
- If new snapshot is different from save snapshot, find what is different and check for links/descriptions

