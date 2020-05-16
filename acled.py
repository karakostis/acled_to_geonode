from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
from shapely.geometry import Point, mapping
from fiona import collection
from fiona.crs import from_epsg

# pd.__version__   #'1.0.3'

data_pth= Path("data/")
log_pth = Path("logs/")
# select time range for data
subtract_days = 5
end_date = datetime.today().strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days = subtract_days)).strftime('%Y-%m-%d')

# build url
main_url = 'https://api.acleddata.com/acled/read.csv?terms=accept&'
iso = '760'
url = "{main_url}iso={iso}&event_date={start_date}|{end_date}&event_date_where=BETWEEN".format(main_url = main_url, iso = iso, start_date = start_date, end_date = end_date)

# get csv into pandas dataset
dataset = pd.read_csv(url)

# export to shape file
if (len(dataset)>0):
    print(len(dataset))
    num_data = len(dataset)

    shpOut = data_pth/'acled.shp'
    lng = 'longitude'
    lat = 'latitude'

    schema = { 'geometry': 'Point', 'properties': { 'event_date': 'str', 'year':'int', 'event_type': 'str', 'sub_event_type': 'str', 'actor1':'str', 'actor2':'str', 'region': 'str','country': 'str', 'admin1': 'str', 'admin2': 'str', 'admin3': 'str', 'iso3': 'str' } }

    data = dataset
    with collection(shpOut, "w", crs=from_epsg(4326), driver = "ESRI Shapefile", schema = schema) as output:
        for index, row in data.iterrows():
            point = Point(row[lng], row[lat])
            output.write({
                'properties': {'event_date': row['event_date'], 'year': row['year'], 'event_type': row['event_type'], 'sub_event_type': row['sub_event_type'], 'actor1': row['actor1'], 'actor2': row['actor2'], 'region': row['region'], 'country': row['country'], 'admin1': row['admin1'], 'admin2': row['admin2'], 'admin3': row['admin3'], 'iso3': row['iso3']},
                'geometry': mapping(point)
            })


    log_msg = "{num_data} events were retrieved on {end_date} \n".format(num_data = num_data, end_date = end_date)

else:
    log_msg = "{num_data} events were retrieved on {end_date} \n".format(num_data = 0, end_date = end_date)


# logging
with open(log_pth/'log.csv','a') as fd:
    fd.write(log_msg)
