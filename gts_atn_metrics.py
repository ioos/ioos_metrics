import datetime as dt
import pandas as pd
from fiscalyear import *
import requests
from bs4 import BeautifulSoup

# gather FY start/end dates for previous quarter
fq = FiscalQuarter.current().prev_fiscal_quarter

start_date = fq.start.strftime("%Y-%m-%d")
end_date = fq.end.strftime("%Y-%m-%d")

start = dt.datetime.strptime(start_date, "%Y-%m-%d")
end = dt.datetime.strptime(end_date, "%Y-%m-%d")

# recursively search the https index for bufr messages
url = "https://stage-ndbc-bufr.srv.axds.co/platforms/atn/smru/profiles/"

html = requests.get(url).text
soup = BeautifulSoup(html, "html.parser")

df_out = pd.DataFrame()

for deployment in soup.find_all("a"):
    depl_url = url + deployment.text
    depl_html = requests.get(depl_url).text

    depl_soup = BeautifulSoup(depl_html, "html.parser")

    # some content is not in an html node, so we have to parse line by line
    files = depl_soup.get_text().split("\r\n")[1:-1]

    for file in files:
        content = file.split()

        if ".bufr" in content[0]:
            # save the index file information to DF.
            fname = deployment.text + content[0]
            df_file = pd.DataFrame(
                {
                    "fname": [fname],
                    "date": pd.to_datetime([content[1] + "T" + content[2]]),
                    "size": [content[3]],
                }
            )

            df_out = pd.concat([df_out, df_file])


print("{} total messages from ATN to GTS.".format(df_out.shape[0]))

# mask for FY Quarter
df_out = df_out.set_index("date").sort_index()
df_fq = df_out.sort_index()[fq.start : fq.end]

string = "For {} ({} to {}) ATN sent {} records to GTS.".format(
    fq, fq.start.strftime("%Y-%m-%d"), fq.end.strftime("%Y-%m-%d"), df_fq.shape[0]
)

print(string)

# groupby month and save data
group = df_out.groupby(pd.Grouper(freq="M"))

s = group["fname"].count()

s.index = s.index.to_period("M")

s = s.rename("total")

s.to_csv("gts/GTS_ATN_monthly_totals.csv")
