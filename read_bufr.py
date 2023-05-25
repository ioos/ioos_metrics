fname = 'bufr_messages/profile_1048783524.bufr'

import pdbufr
#fname = 'https://stage-ndbc-bufr.srv.axds.co/platforms/atn/smru/profiles/ct169-594-21/profile_1023825600.bufr'
#df_bufr = pdbufr.read_bufr(fname, flat=True, columns="data")

df_bufr = pdbufr.read_bufr(fname,
                           columns=("latitude","longitude","data_datetime","salinity"),
                           )

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
#import urllib.request

# recursively search the https index for bufr messages
url = 'https://stage-ndbc-bufr.srv.axds.co/platforms/atn/smru/profiles/'

html = requests.get(url).text
soup = BeautifulSoup(html, 'html.parser')

df_out = pd.DataFrame()

for deployment in soup.find_all('a'):

  depl_url = url+deployment.text
  depl_html = requests.get(depl_url).text

  depl_soup = BeautifulSoup(depl_html, 'html.parser')

  # some content is not in an html node, so we have to parse line by line
  files = depl_soup.get_text().split('\r\n')[1:-1]

  for file in files:

    content = file.split()

    if '.bufr' in content[0]:
      # save the index file information to DF.
      fname = deployment.text+content[0]
      download_url = url+fname

      fname_out = os.path.join('bufr_messages',fname.replace("/","\\"))
      print(os.path.normpath(fname_out))
      directory = os.path.join("bufr_messages",deployment.text)

      # if not os.path.exists(directory):
      #   os.mkdir(directory)
      # r = requests.get(download_url)
      # with open(fname_out, 'wb') as f:
      #   f.write(r.content)