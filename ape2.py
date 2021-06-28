  
import pyodbc
import json
import requests
from datetime import datetime, date 
from decimal import Decimal
import os
from pprint import pprint


def find_and_convert_datetime2epoch(d):
    """recursively searches through the dictionary and converts datettime 
    values to  epoch. The recursion is wrt to dictionaries only"""

    assert isinstance(d, dict),  "find_and_convert_datetime2epoch must take a dictionary as input"
    for key in d.keys():
        if isinstance(d[key], datetime):
            d[key] =   datetime(d[key]).strftime('%s')
        elif isinstance(d[key], dict):
            d[key] = find_and_convert_datetime2epoch(d[key])  # recursion 
    return d
    

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (bytes, Decimal)):
        return str(obj)
    raise TypeError ("Type %s not serializable" % type(obj))

def row2dict(cursor):
    if cursor is None:
        return None
    row = cursor.fetchone() 
    if row is None:
        return None
    col_names = list(map(lambda x: x[0] , cur.description))
    kv_list = list(zip(col_names, row))
    kv_dict = {k:v for (k,v) in kv_list }
    return kv_dict

def get_tbl_data(cursor, tbl_name):
    cursor.execute(f'select  * from {tbl_name}')
    return None


def split_data(data, chunk_size):
    reshape_data = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    print('number of chunks is {}'.format(len(reshape_data)))
    return reshape_data

    
def format_content(chunck_data, tbl_name):
    s = ''
    pre_row = {"create": {"_index": f"imos-{tbl_name.lower()}"}}
    for chunk in chunck_data:
        # chunk = find_and_convert_datetime2epoch(chunk)
        s += json.dumps(pre_row) + '\n'
        s += json.dumps(chunk, default=json_serial) + '\n'
    return s


###### PROC STARTS HERE #######
if os.name == 'nt':
    _ = os.system('cls')
else:
    _ = os.system('clear')

# for elastic
headers = {'Content-Type': 'application/json'}
url = 'http://localhost:9200/_bulk'
url_delete = 'http://localhost:9200/imos-*'

# for mssql
server = '172.16.11.58\SQL2019IMOS'
database = 'REGBA_IMOS_V14_Test2'
print(f'server: {server}\ndatabase: {database}\n')
username =  input(f'Username for {server}: ')  
password = input(f'Password for {username}: ')  

while True:
    package_sizes = input('choose cunk size for elastinc inserts (an integer): ')
    try: 
        package_sizes = int(package_sizes)
        break
    except:
        continue


con = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password, autocommit=True)
cur = con.cursor()

migrate_orders = input('Do you want to migrate orders as well(y/n)? ')
if migrate_orders == 'y':
    q_get_tbls = 'select distinct  name from sys.objects where type = \'U\''
else:
    q_get_tbls = 'select distinct  name from sys.objects where type = \'U\' and name not like \'idb%\''
cur.execute(q_get_tbls)
tbl_names = list(map(lambda x: x[0], cur.fetchall()))


requests.delete(url_delete , headers=headers)
print('the following tables will be migrated to elastic:\n')
pprint(tbl_names)

for name in tbl_names:
    print(f'processing table {name}')
    rows = []
    get_tbl_data(cur, name)
    while True:
        try:
            d = {'tbl_name': name}
            d.update(row2dict(cur))
            rows.append(d)
        except TypeError:
            break
    for chunk in split_data(rows, package_sizes): # from user input
        f_data = format_content(chunk, name)
        r = requests.post(url, data=f_data, headers=headers)
        print(r.status_code)
        if r.status_code != 200:
            print(r.content)









