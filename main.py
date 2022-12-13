from ast import Or
import os
import pandas
import requests
import urllib.parse
import warnings

# influx
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, WriteOptions, WriteType
from influxdb_client.domain.write_precision import WritePrecision

from datetime import date, datetime, timedelta
from calendar import monthrange

"""
    get env vars
"""
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

FROM_YYYY = os.getenv('FROM_YYYY')
FROM_MM = os.getenv('FROM_MM')

TO_YYYY = os.getenv('TO_YYYY')
TO_MM = os.getenv('TO_MM')

BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET")
ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
HOST = os.getenv("DOCKER_INFLUXDB_INIT_HOST")
PORT = os.getenv("DOCKER_INFLUXDB_INIT_PORT")
URL = os.getenv("DOCKER_INFLUXDB_URL", "http://localhost:8086")

RUN_YESTERDAY = os.getenv("RUN_YESTERDAY", False)

WRITE_TO_FILE = os.getenv("WRITE_TO_FILE", False)


"""
    utility functions
"""
def build_dirs(usage_date):
    yyyy, mm, dd = usage_date.split('-')

    if not os.path.exists(f'data/{yyyy}'):
        # create year dir
        os.mkdir(f'data/{yyyy}')

    if not os.path.exists(f'data/{yyyy}/{mm}'):
        # create month dir
        os.mkdir(f'data/{yyyy}/{mm}')

def get_days(yyyy, mm):
    return monthrange(yyyy, mm)


"""
    main function for getting data from epb
"""
def get_data(option, usage_date=None):

    usage_key = ''
    filename = None

    if usage_date:
        yyyy, mm, dd = usage_date.split('-')
        usage_key = f'&usage_date={usage_date}'
        filename = f'data/{yyyy}/{mm}/{usage_date}.csv'
        build_dirs(usage_date)

    # start session
    s = requests.session()

    if not ACCESS_TOKEN:
        url = "https://api.epb.com/web/api/v1/login/"
        payload = "{\n    \"grant_type\": \"PASSWORD\",\n    \"password\": \"" + PASSWORD + "\",\n    \"username\": \"" + USERNAME + "\"\n}"
        headers = {'Content-Type': 'application/json'}
        r = s.post(url, headers=headers, data=payload)

        if r.status_code != 200:
            print(f'Failed to login: {r.status_code}')

        access_token = r.json()['tokens']['access']['token']
    else:
        access_token = ACCESS_TOKEN

    safe_access_key = urllib.parse.quote_plus(access_token)

    url = f"https://api.epb.com/web/api/v1/usage/power/permanent/{option}/download"
    payload = f'account_id=2193175001&token={safe_access_key}&gis_id=10799&zone_id=America%2FNew_York{usage_key}'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = s.post(url, headers=headers, data=payload)

    if r.status_code != 200:
        print(f'Failed to get data: {r.status_code}')

    export_data(r.content, filename)


"""
    helper functions for getting specific types of data
"""
def get_hourly(usage_date=None):
    option = "compare/hourly"
    if usage_date == None:
        option = "day/hourly"
        usage_date = datetime.today().strftime('%Y-%m-%d')

    get_data(option, usage_date)


def get_daily():
    get_data("compare/daily")


def get_monthly():
    get_data("compare/monthly")


"""
    data to export data to file or stdout
"""
def export_data(input, filename):
    warnings.simplefilter("ignore")

    try:
        # read an excel file and convert
        # into a dataframe object
        df = pandas.DataFrame(pandas.read_excel(input, sheet_name=1, engine="openpyxl"))
        # show the dataframe
    except Exception as e:
        print(e)
        return

    if filename and WRITE_TO_FILE:
        # write out to file
        df.to_csv(f'{filename}', index=False, header=True)
    else:
        print(df)

    if filename:
        with InfluxDBClient(url=URL, token=TOKEN, org=ORG) as client:
            write_options = WriteOptions(write_type=WriteType.batching)
            write_api = client.write_api(write_options=write_options)

            for idx, record in enumerate(df.to_dict('records')):
                kwh = float(record['Primary Cycle Estimated Power Use'].replace("kWh",''))
                dictionary = {
                    "measurement": "usage",
                    "fields": {"kWh": kwh},
                    "time": record['Primary Cycle Date']
                }
                write_api.write(BUCKET, ORG, dictionary, write_precision=WritePrecision.S)

                cost = float(record['Primary Cycle Estimated Cost'].replace("$",""))
                dictionary = {
                    "measurement": "usage",
                    "fields": {"cost": cost},
                    "time": record['Primary Cycle Date']
                }
                write_api.write(BUCKET, ORG, dictionary, write_precision=WritePrecision.S)

                temp = float(record['Primary Cycle Average Air Temperature'][:-2]) if type(record['Primary Cycle Average Air Temperature']) is str else None
                dictionary = {
                    "measurement": "usage",
                    "fields": {"temp": temp},
                    "time": record['Primary Cycle Date']
                }
                write_api.write(BUCKET, ORG, dictionary, write_precision=WritePrecision.S)

            write_api.close()

def load_months_of_data(from_yyyy, from_mm, to_yyyy, to_mm, to_dd=None):
    dates = []
    for yyyy in range(from_yyyy, to_yyyy+1):
        for mm in range(from_mm, to_mm+1):
            num_days = get_days(yyyy, mm)[1]
            for dd in range(1, num_days+1):
                dates.append(f'{yyyy}-{mm:02d}-{dd:02d}')

    for d in dates:
        get_hourly(usage_date=d)


def load_yesterday():
    yesterday = date.today() - timedelta(days = 1)
    get_hourly(usage_date=yesterday.strftime('%Y-%m-%d'))


if __name__ == "__main__":
    if FROM_YYYY and FROM_MM and TO_YYYY and TO_MM and not RUN_YESTERDAY:
        load_months_of_data(
            from_yyyy=int(FROM_YYYY),
            from_mm=int(FROM_MM),
            to_yyyy=int(TO_YYYY),
            to_mm=int(TO_MM)
        )
    else:
        print("loading yesterdays data")
        load_yesterday()

