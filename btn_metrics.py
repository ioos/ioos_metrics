import config
import pandas as pd
from suds.client import Client

wsdlURL = "https://cdmo.baruch.sc.edu/webservices2/requests.cfc?wsdl"

user = config.CDMO_NAME

pwd = config.CDMO_KEY

soapClient = Client(wsdlURL,
                    timeout=90,
                    retxml=True,
                    username=user,
                    password=pwd,
                    prettyxml=True)

wq_station_name = "niwolwq"

response = soapClient.service.exportAllParamsDateRangeXMLNew(wq_station_name, "2023-03-23", "2023-03-23")

print(pd.read_xml(response,xpath=".//returnData"))
