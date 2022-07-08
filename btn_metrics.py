import pandas as pd
import requests
import re
from bs4 import BeautifulSoup
import json


ioos_btn_df = pd.read_csv('https://github.com/MathewBiddle/ioos_by_the_numbers/raw/main/ioos_btn_metrics.csv')#columns=['category','value','date'])

today = pd.Timestamp.strftime(pd.Timestamp.today(tz='UTC'), '%Y-%m-%d')

# only update numbers if it's a new day
if today not in ioos_btn_df['date_UTC'].to_list():
    ioos_btn_df = ioos_btn_df.append({'date_UTC': today}, ignore_index=True)

fed_partners = 17

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['Federal Partners']] = [fed_partners]

regional_associations = 11

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['Regional Associations']] = [regional_associations]

comt = 5

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['COMT Projects']] = comt

hfr_installations = 165

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['HF Radar Stations']] = hfr_installations

df_glider = pd.read_csv('https://gliders.ioos.us/erddap/tabledap/allDatasets.csvp?minTime%2CmaxTime%2CdatasetID')
df_glider.dropna(
    axis=0,
    inplace=True,
    )

# drop delayed datasets
df_glider = df_glider[df_glider["datasetID"].str.contains("delayed")==False]

df_glider[['minTime (UTC)','maxTime (UTC)']] = df_glider[
                                                         ['minTime (UTC)','maxTime (UTC)']
                                                         ].apply(pd.to_datetime)

df_glider['glider_days'] = (df_glider['maxTime (UTC)'] - df_glider['minTime (UTC)']).dt.days

glider_days = df_glider['glider_days'].sum()

print('Cumulative glider days:', glider_days)

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['NGDAC Glider Days']] = glider_days

# National Platforms

## co-ops
xml = requests.get('https://opendap.co-ops.nos.noaa.gov/stations/stationsXML.jsp').text
COOPS = sum(1 for _ in re.finditer(r'\b%s\b' % re.escape("station name"), xml))

## ports
url = 'https://tidesandcurrents.noaa.gov/cdata/StationListFormat?type=Current+Data&filter=active&format=csv'
df_coops = pd.read_csv(url)
ports = df_coops[df_coops[' Project'].astype(str).str.contains('PORTS')].shape[0]

## NDBC
url = 'https://www.ndbc.noaa.gov/wstat.shtml'

html = requests.get(url).text

soup = BeautifulSoup(html, 'html.parser')

string_to_find = ['Total Base Funded Buoys:','Total Other Buoys:',
                  'Total Moored Buoys:','Total Base Funded Stations:',
                  'Total Stations:']

ndbc = dict()
for string in string_to_find:
    for tag in soup.find_all("td", string=string):
        ndbc[string] = int(tag.next_sibling.string)

NDBC = ndbc['Total Moored Buoys:'] + ndbc['Total Base Funded Stations:']

## NERRS
url = 'https://coast.noaa.gov/nerrs/about/'

html = requests.get(url).text

soup = BeautifulSoup(html, 'html.parser')

string_to_find = ['The National Estuarine Research Reserve System is a network of ']

nerrs = dict()
for string in string_to_find:
  for tag in soup.find_all("meta", attrs={'content': re.compile(string)}, limit=1):
    res = [int(i) for i in tag['content'].split() if i.isdigit()] # extract number
    #print(tag['content'])
    NERRS = int(res[0])
    #print('%s = %s' % (string, tag.next_sibling.string))

NERRS = 140

## CBIBS
base_url = 'https://mw.buoybay.noaa.gov/api/v1'
apikey = 'f159959c117f473477edbdf3245cc2a4831ac61f'
start = '2021-12-08T01:00:00z'
end = '2021-12-09T23:59:59z'
var = 'Position'

query_url = '{}/json/query?key={}&sd={}&ed={}&var={}'.format(base_url,apikey,start,end,var)

json = json.loads(requests.get(query_url).text)

CBIBS = len(json['stations'])

## OAP
url = 'https://oceanacidification.noaa.gov/WhatWeDo/Data.aspx'

html = requests.get(url).text

soup = BeautifulSoup(html, 'html.parser')

text = soup.find_all(attrs={'id':"dnn_ctr14711_ContentPane"})[0].find_all(attrs={'class':'lead'})[0].text #id="mapDiv")

res = [int(i) for i in text.split() if i.isdigit()] # extract number
OAP = int(res[0])

## CDIP
url = 'https://cdip.ucsd.edu/themes/?d2=p1:m:mobile&regions=all&units=standard&zoom=auto&pub_set=public&tz=UTC&ll_fmt=dm&numcolorbands=10&palette=cdip_classic&high=6.096'
table_list = pd.read_html(url, match='Stn')

df = table_list[0]

CDIP = df['Stn'].unique().size

## Calculating National Platforms
national_platforms = COOPS + NDBC + NERRS + CBIBS + OAP + CDIP
print("National Platforms:",national_platforms)

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['National Platforms']] = national_platforms

# Regional Platforms
url = 'http://erddap.ioos.us/erddap/tabledap/processed_asset_inventory.csvp'

df_regional_platforms = pd.read_csv(url)

regional_platforms = df_regional_platforms['station_long_name'].unique().size

print('Regional platforms:',regional_platforms)

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['Regional Platforms']] = regional_platforms

# ATN Deployments
atn_deployments = 4444

print("ATN Deployments:",atn_deployments)

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['ATN Deployments']] = atn_deployments

# MBON Projects
mbon_projects = 6

print("MBON Projects:",mbon_projects)

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['MBON Projects']] = mbon_projects

# OTT Projects
ott_projects = 8

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['OTT Projects']] = ott_projects

# NHABON Pilot Projects
nhabon_projects = 9

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['HAB Pilot Projects']] = nhabon_projects

# QARTOD Manuals
ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['QARTOD Manuals']] = 13

# IOOS Core Variables
headers = {'Accept-Encoding': 'identity'}

url = 'https://www.iooc.us/task-teams/core-ioos-variables/'

soup = BeautifulSoup(requests.get(url, headers=headers).text, 'html.parser')

text = soup.find(style="color: #808080;").get_text() # grab the sentece w/ the number

core_vars = [int(i) for i in text.split() if i.isdigit()] # extract number

print('IOOS Core Variables:',core_vars)

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['IOOS Core Variables']] = core_vars

# Metadata records
import pandas as pd

url = 'https://data.ioos.us/api/3/action/package_list'

mdf = pd.read_json(url)

metadata_records = len(mdf.result.unique())

print("Found {} records from {}.".format(metadata_records,url))

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['Metadata Records']] = metadata_records

# IOOS
ioos = 1

print("IOOS:",ioos)

ioos_btn_df.loc[ioos_btn_df['date_UTC']==today, ['IOOS']] = ioos

# Final table
ioos_btn_df['date_UTC']=pd.to_datetime(ioos_btn_df['date_UTC'])
ioos_btn_df.set_index('date_UTC')

ioos_btn_df.to_csv('ioos_btn_metrics.csv', index=False)