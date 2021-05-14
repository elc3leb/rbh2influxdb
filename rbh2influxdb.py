#!/anaconda/envs/dev_env/bin/python3
from influxdb import InfluxDBClient
import argparse
import socket
import sys
import time
import re
from datetime import datetime , timedelta, date

parser = argparse.ArgumentParser(description='Write / Read to / from influxdb SGBD')
parser.add_argument('-H', '--host', type=str, help='Influxdb Server Address', required=False, default='influxdb_host')
parser.add_argument('-P', '--port', type=int, help='Influxdb Server Port', required=False, default='<port>')
parser.add_argument('-u', '--user', type=str, help='Influxdb User', required=False, default='robinhood')
parser.add_argument('-p', '--password', type=str, help='Influxdb User Password', required=False, default='<passwor>')
parser.add_argument('-d', '--dbname', type=str, help='Influxdb Database Name', required=False, default='robinhood')
parser.add_argument('-l', '--log', type=str, help='Path to the log file', nargs='+', required=True)
args = parser.parse_args()

client = InfluxDBClient(args.host, args.port, args.user, args.password, args.dbname)

current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

# SI unit prefixes
SI_K, SI_M, SI_G, SI_T, SI_P = 10 ** 3, 10 ** 6, 10 ** 9, 10 ** 12, 10 ** 15

hours, minutes, secondes, duration = 0, 0, 0, 0

def get_unit(n):
    if re.findall(r'.*\d+\.\d+ MB.*', n):
        unit = 'MB'
    if re.findall(r'.*\d+\.\d+ GB.*', n):
        unit = 'GB'
    if re.findall(r'.*\d+\.\d+ TB.*', n):
        unit = 'TB'
    if re.findall(r'.*\d+\.\d+ PB.*', n):
        unit = 'PB'
    return unit


def convert_to_bytes(n,unit):
    if 'PB' in unit:
        return '%.1f' % (float(n) * SI_P)
    if 'TB' in unit:
        return '%.1f' % (float(n) * SI_T)


def define_filecontent(content):
    for line in content:
        if 'FS_Scan | Starting' in line:
            return "scan"
            break
        if 'cleanup | Starting' in line:
            return "cleanup"
            break
    return 0

def get_filecontent(arg_path):
    path = arg_path
    with open(path) as file:
        lines = file.read().splitlines()
    return lines

json_template = []
for path in args.log:
    is_valid_log = True
    if 'scratch' in path.split('/')[-1]:
        fs_value= 'scratch'
    if 'scratchrd' in path.split('/')[-1]:
        fs_value= 'scratchrd'
    if 'data_local' in path.split('/')[-1]:
        fs_value= 'data_local'
    scan_end_date=""
    content = get_filecontent(path)
    if 'scan' in define_filecontent(content):
        for line in content:
            if 'FS_Scan | Starting' in line:
                scan_start_date = line[0:19]
                if scan_start_date:
                    scan_start_date = scan_start_date.replace('/','-')
                    scan_start_date = scan_start_date.replace(' ','T')
                    scan_start_date = "{}Z".format(scan_start_date)
                    print(scan_start_date)
            if 'FS_Scan | Full scan' in line:
                entries_value = re.findall(r'(\d+) entries', line)[-1]
                if entries_value:
                    entries_value = int(entries_value)
                    print(entries_value)
            if 'FS_Scan | Full scan' in line:
                duration_value = re.findall(r'Duration = (\d+)', line)[-1]
                if duration_value:
                    duration_value = int(duration_value)
                    print(duration_value)
            if 'Main | All tasks done' in line:
                scan_end_date = line[0:19]
                if scan_end_date:
                    scan_end_date = scan_end_date.replace('/','-')
                    scan_end_date = scan_end_date.replace(' ','T')
                    scan_end_date = "{}Z".format(scan_end_date)
                    print(scan_end_date)


        measurement='RobinhoodScan'
        json_template = [
                {
                    "measurement": "{}".format(measurement),
                    "tags" : {
                        "fs": "{}".format(fs_value),
                        "type": "scan",
                    },
                    "time": scan_end_date,
                    "fields": {
                       "start_date": scan_start_date,
                       "entries": entries_value,
                       "duration": duration_value,
                       "end_date": scan_end_date,
                    }
                }
            ]


        if is_valid_log and json_template:
            print("Insert Scan information on Influxdb for {}".format(path.split('/')[-1]))
            client.write_points(json_template,database='robinhood', time_precision='ms', batch_size=10000, protocol='json')

    if 'cleanup' in define_filecontent(content):
        for line in content:
            if 'cleanup | Starting' in line:
                clean_start_date = line[0:19]
                if clean_start_date:
                    clean_start_date = clean_start_date.replace('/','-')
                    clean_start_date = clean_start_date.replace(' ','T')
                    print('clean_start_date={}'.format(clean_start_date))
            if 'successful actions' in line:
                actions = re.findall(r'(\d+) successful actions', line)[-1]
                if actions:
                    actions = int(actions)
                    print('actions={}'.format(actions))
            if 'cleanup | Policy run summary' in line:
                unit = get_unit(line)
                cleared_volumes = re.findall(r'volume: (\d+\.\d+)', line)[-1]
                cleared_volumes = convert_to_bytes(cleared_volumes,unit)
                if cleared_volumes:
                    cleared_volumes = float(cleared_volumes)
                    print('cleared_volumes={}'.format(cleared_volumes))
            if 'cleanup | Policy run summary' in line:
                if re.findall(r'time=(\d+h)', line):
                    hours = re.findall(r'(\d+)h', line)[-1]
                if re.findall(r'time=.*(\d+min)', line):
                    minutes = re.findall(r'(\d+)min', line)[-1]
                if re.findall(r'time=.*(\d+s)', line):
                    secondes = re.findall(r'(\d+)s', line)[-1]
                duration = 3600 * int(hours)
                duration += 60 * int(minutes)
                duration += int(secondes)
                print('duration={}'.format(duration))
            if 'Main | All tasks done' in line:
                clean_end_date = line[0:19]
                if clean_end_date:
                    clean_end_date = clean_start_date.replace('/','-')
                    clean_end_date = clean_start_date.replace(' ','T')
                    print('clean_end_date={}\n'.format(clean_end_date))


        measurement='RobinhoodClean'
        json_template = [
                {
                    "measurement": "{}".format(measurement),
                    "tags" : {
                        "fs": "{}".format(fs_value),
                        "type": "clean",
                    },
                    "time": clean_end_date,
                    "fields": {
                      "start_date": clean_start_date,
                                                 "actions": actions,
                                                 "volumes": cleared_volumes,
                                                 "duration": duration,
                                                 "end_date": clean_end_date,
                    }
                }
            ]


        if re.findall(r'\d+-\d+-\d+T\d+:\d+:\d+', clean_end_date):
            print("Insert Clean information on Influxdb for {}".format(path.split('/')[-1]))
            client.write_points(json_template,database='robinhood', time_precision='ms', batch_size=10000, protocol='json')


    if define_filecontent(content) == 0:
        print('Unknown log file format')
