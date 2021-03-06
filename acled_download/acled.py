from pathlib import Path
from datetime import datetime, timedelta
import time
import json

import pandas as pd
from shapely.geometry import Point, mapping
from fiona import collection
from fiona.crs import from_epsg

# pd.__version__   #'1.0.3'

data_pth= Path("data/")
log_pth = Path("logs/")

# load script parameters
with open('params.json') as params_file:
    params = json.load(params_file)

end_date = datetime.today().strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days = params['subtract_days'])).strftime('%Y-%m-%d')

print("end_date", end_date)
print("start_date", start_date)
# build url
query_limit = params['query_limit'] # default 500
main_url = "https://api.acleddata.com/acled/read.csv?terms=accept&limit={query_limit}&".format(query_limit = query_limit)
iso = '760' # Syria
url = "{main_url}iso={iso}&event_date={start_date}|{end_date}&event_date_where=BETWEEN".format(main_url = main_url, iso = iso, start_date = start_date, end_date = end_date)
#print(url)
# get csv into pandas dataset
dataset = pd.read_csv(url)

# export to shape file
if (len(dataset)>0):
    data_exist = True
    num_data = len(dataset)
    print(num_data)

    shpOut = data_pth/'acled.shp'
    lng = 'longitude'
    lat = 'latitude'

    schema = { 'geometry': 'Point', 'properties': { 'event_date': 'str', 'year':'int', 'event_type': 'str', 'sub_event_type': 'str', 'actor1':'str', 'actor2':'str', 'region': 'str','country': 'str', 'admin1': 'str', 'admin2': 'str', 'admin3': 'str', 'iso3': 'str' } }

    with collection(shpOut, "w", crs=from_epsg(4326), driver = "ESRI Shapefile", schema = schema) as output:
        for index, row in dataset.iterrows():
            point = Point(row[lng], row[lat])
            output.write({
                'properties': {'event_date': row['event_date'], 'year': row['year'], 'event_type': row['event_type'], 'sub_event_type': row['sub_event_type'], 'actor1': row['actor1'], 'actor2': row['actor2'], 'region': row['region'], 'country': row['country'], 'admin1': row['admin1'], 'admin2': row['admin2'], 'admin3': row['admin3'], 'iso3': row['iso3']},
                'geometry': mapping(point)
            })


    log_msg = "{num_data} events were retrieved on {end_date} \n".format(num_data = num_data, end_date = end_date)

    #create zipfile
    time.sleep(5)
    from zipfile import ZipFile
    with ZipFile(data_pth/'acled.zip', 'w') as zipObj:
        zipObj.write(data_pth/'acled.shp')
        zipObj.write(data_pth/'acled.dbf')
        zipObj.write(data_pth/'acled.shx')
        zipObj.write(data_pth/'acled.prj')
        zipObj.write(data_pth/'acled.cpg')

else:
    log_msg = "{num_data} events were retrieved on {end_date} \n".format(num_data = 0, end_date = end_date)
    data_exist = False

# create config file
config_params = {
    "name": params['layer_name'], # we can keep this name
    "path": params['path_to_zip'],
    "data_exist": data_exist
}

config = {
	"config": {
		"host": params['host'],
		"username": params['geonode_username'],
		"password": params['geonode_password']
	},
	"files": [{
        "data_exist": data_exist,
		"name": config_params['name'],
		"path": config_params['path']
	}]
}


with open('config.json','w') as fp:
    json.dump(config, fp, indent=4)

# logging
with open(log_pth/'log.csv','a') as fd:
    fd.write(log_msg)

# send email notification
import smtplib
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login("wfp.gis.syr@gmail.com", "g1smaps2020")
msg = log_msg
sender = 'wfp.gis.syr@gmail.com'
recipients = ['dkarakostis@gmail.com']
s.sendmail(sender, recipients, str(msg))
s.quit()
