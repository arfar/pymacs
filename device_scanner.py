#!/usr/bin/env python3.5

import org_matcher as mac_org
import device_tracker as dev_track
import my_utils as u
import multiprocessing
import subprocess
import ipaddress
import os
import datetime


def _pinger(job_q, results_q, ping_bin):
    # Modified from:
    # http://stackoverflow.com/questions/21225464/fast-ping-sweep-in-python
    DEVNULL = open(os.devnull, 'w')
    while True:
        ip = job_q.get()
        if not ip:
            break
        result = subprocess.call([ping_bin, '-c1', ip],
                                 stdout=DEVNULL,
                                 stderr=DEVNULL)
        if result == 0:
            results_q.put(ip)

def ping_scan(ip_addr_network_string, ping_bin):
    # Modified from:
    # http://stackoverflow.com/questions/21225464/fast-ping-sweep-in-python
    pool_size = 255
    jobs = multiprocessing.Queue()
    results = multiprocessing.Queue()
    pool = [
        multiprocessing.Process(target=_pinger,
                                args=(jobs, results, ping_bin))
        for i in range(pool_size)
    ]
    ip_addr_network = ipaddress.ip_network(ip_addr_network_string)
    for p in pool:
        p.start()
    for ip in ip_addr_network.hosts():
        jobs.put(str(ip))
    for p in pool:
        jobs.put(None)
    for p in pool:
        p.join()
    pingable_ips = []
    while not results.empty():
        pingable_ips.append(results.get())
    return pingable_ips

def arp_ips(ip_list, arp_bin, own_mac_address, own_ip_address=None):
    devices = []
    for ip in ip_list:
        if ip == own_ip_address:
            device = {
                'hostname': 'Yourself',
                'ip': ip,
                'mac_hex_str': own_mac_address,
                'mac_int': u.hex_str_to_int(own_mac_address),
            }
            devices.append(device)
        p = subprocess.Popen([arp_bin, '-e', ip],
                             stdout=subprocess.PIPE)
        output, err = p.communicate()
        result = output.decode('utf-8').split('\n')
        if 'no entry' in result[0]:
            continue
        device = {
            'ip': ip,
            'hostname': result[1].split()[0],
            'mac_hex_str': result[1].split()[2],
            'mac_int': u.hex_str_to_int(result[1].split()[2]),
        }
        devices.append(device)
    return devices

def scan_macs(ip_network, ping_bin, arp_bin, own_mac_address,
              own_ip_address=None):
    ips = ping_scan(ip_network, ping_bin)
    devices = arp_ips(ips, arp_bin, own_ip_address)
    return devices

def scan_add_and_update_macs(ip_network, ping_bin, arp_bin, own_mac_address,
                             own_ip_address=None):
    devices = scan_macs(ip_network, ping_bin, arp_bin, own_ip_address)
    return devices

if __name__ == '__main__':
    import argparse
    import settings
    import pprint
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--show-current', action='store_true',
        help='Scan network and print found devices in JSON format'
    )
    parser.add_argument(
        '-z', '--ugly', action='store_true',
        help='Ugly printing'
    )

    parser.add_argument(
        '-u', '--update', action='store_true',
        help=('Update database of mac addresses and save time scanned')
    )
    parser.add_argument(
        '-t', '--trash-database', action='store_true',
        help=('Drop the time series data tables')
    )
    parser.add_argument(
        '-a', '--add-name', nargs=2, metavar=('MAC_ADDR', 'NEW_NAME'),
        help=('Add name to mac address')
    )
    parser.add_argument(
        '-l', '--list', action='store_true',
        help=('List all mac addresses in database')
    )
    parser.add_argument(
        '-m', '--history-mac', action='store',
        help=('Look up history of given mac address')
    )
    parser.add_argument(
        '-n', '--history-name', action='store',
        help=('Look up history of given name')
    )

    args = parser.parse_args()

    if hasattr(settings, 'IP_NETWORK'):
        ip_network = settings.IP_NETWORK
    else:
        ip_network = '192.168.1.0/24'

    if hasattr(settings, 'ARP_BIN'):
        arp_bin = settings.ARP_BIN
    else:
        arp_bin = '/usr/bin/arp'

    if hasattr(settings, 'PING_BIN'):
        ping_bin = settings.PING_BIN
    else:
        ping_bin = '/bin/ping'

    if hasattr(settings, 'OWN_IP_ADDRESS'):
        own_ip_address = settings.OWN_IP_ADDRESS
    else:
        own_ip_address = None

    if hasattr(settings, 'OWN_MAC_ADDRESS'):
        own_mac_address = settings.OWN_MAC_ADDRESS
    else:
        own_mac_address = None

    if args.trash_database:
        dev_track.drop_tables()
        dev_track.init_tables()

    if args.update:
        devices = scan_add_and_update_macs(ip_network, ping_bin, arp_bin,
                                           own_mac_address, own_ip_address)
        timestamp = datetime.datetime.now()
        dev_track.add_timestamp(timestamp)
        for device in devices:
            dev_track.add_device(device)
            dev_track.add_device_on_timeline(device, timestamp)

    # TODO - make a better printer
    if args.history_mac:
        history = dev_track.get_device_history_mac_string(args.history_mac)
        pprint.pprint(history)

    if args.history_name:
        history = dev_track.get_device_history_mac_string(args.history_name)
        pprint.pprint(history)

    if args.add_name:
        dev_track.add_device_name_mac(*args.add_name)

    if args.list or args.add_name:
        devices = []
        for device in dev_track.all_devices():
            devices.append({
                'mac_address': u.int_mac_to_hex_mac(device[1]),
                'last_hostname': device[2],
                'name': device[3],
                'organisation': mac_org.search_by_mac_address_int(device[1]),
            })
        pprint.pprint(devices)
