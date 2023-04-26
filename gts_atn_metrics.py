import datetime as dt
import pandas as pd
from fiscalyear import *
import requests
from bs4 import BeautifulSoup
import re

# gather FY start/end dates for previous quarter
fq = FiscalQuarter.current().prev_fiscal_quarter

start_date = fq.start.strftime('%Y-%m-%d')
end_date = fq.end.strftime('%Y-%m-%d')

start = dt.datetime.strptime(start_date,'%Y-%m-%d')
end = dt.datetime.strptime(end_date,'%Y-%m-%d')

# build an array for days between dates
date_array = (start + dt.timedelta(days=x) for x in range(0, (end - start).days))

# get a unique list of year-months for url build
months=[]
for date_object in date_array:
    months.append(date_object.strftime("%Y-%m"))
months = sorted(set(months))

df = pd.DataFrame(columns=['fname'])

url = 'https://stage-ndbc-bufr.srv.axds.co/platforms/atn/smru/profiles/'

html = requests.get(url).text
soup = BeautifulSoup(html, 'html.parser')

i = 0
for deployment in soup.find_all('a'):
  depl_url = url+deployment.text
  #print(depl_url)
  depl_html = requests.get(depl_url).text
  depl_soup = BeautifulSoup(depl_html, 'html.parser')

  for tag in depl_soup.find_all('a'):
    if '.bufr' in tag.text:
      print(tag.text)
      df1 = pd.DataFrame({'fname':[tag.text]})
      df = pd.concat([df,df1])
      i+=1

print('{} total messages from ATN to GTS.'.format(i))
#print(soup.prettify())
#
#
# url = 'https://stage-ndbc-bufr.srv.axds.co/platforms/atn/smru/profiles/ct169-594-21/'
# html = requests.get(url).text
# soup = BeautifulSoup(html, 'html.parser')
#
# i = 0
# for tag in soup.find_all('a'):
#   if '.bufr' in tag.text:
#     print(tag.text)
#     i+=1
#
# print(i)