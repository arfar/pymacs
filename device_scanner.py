#!/usr/bin/env python3

import sqlite3
import org_matcher as mac_org
import multiprocessing
import subprocess
import ipaddress
import os
import datetime
import json


class MacDeviceScannerMatcher(object):
    def __init__(self, db_fname='mac.db', ip_network='192.168.1.0/24',
                 recreate=False, arp_bin='/usr/bin/arp'):
        self.db_fname = db_fname
        self.mac_org_match = mac_org.MacOrgMatch()

        if not os.path.exists(arp_bin):
            print('Couldn\'t find arp executable, scanning won\'t work')
            print('    which probably means this tool will be pretty useless')
            self.arp_bin = None
        else:
            self.arp_bin = arp_bin

        if not ip_network:
            print('No ip_network set, can\'t scan network')
            print('    which probably means this tool will be pretty useless')
        self.ip_network = ip_network

        if recreate:
            self.db_drop_tables()
        self.db_init_tables()

    def db_init_tables(self):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            CREATE TABLE IF NOT EXISTS device (
            dev_mac_addr    INTEGER  PRIMARY KEY  NOT NULL,
            dev_name        TEXT,
            dev_last_seen   TIMESTAMP
            );
            ''')

    def db_drop_tables(self):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            DROP TABLE IF EXISTS device;
            ''')

    def db_add_mac_address(self, mac_entry):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            INSERT OR REPLACE INTO device
            (dev_mac_addr, dev_last_seen, dev_name)
            VALUES (?, ?,
                (SELECT dev_name FROM device WHERE dev_mac_addr = ?)
            );
            ''', (mac_entry['mac_int'], mac_entry['date'],
                  mac_entry['mac_int'],))
            c.execute('''
            SELECT * FROM device WHERE dev_mac_addr = ?;
            ''', (mac_entry['mac_int'], ))
            dev = c.fetchone()
        return dev

    def db_add_device_name(self, mac_addr, dev_name):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            INSERT OR REPLACE INTO device
            (dev_mac_addr, dev_name, dev_last_seen)
            VALUES (?, ?,
                (SELECT dev_last_seen FROM device WHERE dev_mac_addr = ?)
            );
            ''', (mac_addr, dev_name, mac_addr, ))

    def _pinger(self, job_q, results_q):
        # Modified from:
        # http://stackoverflow.com/questions/21225464/fast-ping-sweep-in-python
        DEVNULL = open(os.devnull, 'w')
        while True:
            ip = job_q.get()
            if not ip:
                break
            result = subprocess.call(['ping', '-c1', ip],
                                     stdout=DEVNULL,
                                     stderr=DEVNULL)
            if result == 0:
                results_q.put(ip)

    def ping_scan(self, ip_addr_network_string):
        # Modified from:
        # http://stackoverflow.com/questions/21225464/fast-ping-sweep-in-python
        pool_size = 255
        jobs = multiprocessing.Queue()
        results = multiprocessing.Queue()
        pool = [
            multiprocessing.Process(target=self._pinger,
                                    args=(jobs, results))
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

    def arp_ips(self, ip_list):
        if not self.arp_bin:
            return None
        devices = []
        for ip in ip_list:
            p = subprocess.Popen(['arp', '-e', ip],
                                 stdout=subprocess.PIPE)
            output, err = p.communicate()
            result = output.decode('utf-8').split('\n')
            if 'no entry' in result[0]:
                continue
            device = {
                'ip': ip,
                'mac_hex_str': result[1].split()[2],
                'mac_int': mac_org.hex_str_to_int(result[1].split()[2]),
            }
            devices.append(device)
        return devices

    def scan_macs(self):
        ips = macscan.ping_scan(self.ip_network)
        devices = macscan.arp_ips(ips)
        return devices

    def scan_add_and_update_macs(self):
        devices = self.scan_macs()
        for device in devices:
            device['date'] = datetime.datetime.now()
            dev_in_db = macscan.db_add_mac_address(device)
            if dev_in_db[1]:
                device['name'] = dev_in_db[1]
        else:
            return devices

    def update_who_is_here(self):
        devices = self.scan_macs()
        for device in devices:
            device['date'] = datetime.datetime.now()
            macscan.db_add_mac_address(device)

    def update_name_on_mac_device(self, mac_addr, name):
        if type(mac_addr) is str:
            mac_addr = mac_org.hex_str_to_int(mac_addr)
        self.db_add_device_name(mac_addr, name)

    def match_mac_addresses_to_orgs(self, device_list):
        for device in device_list:
            device['org'] = self.mac_org_match.search_by_mac_address_int(
                device['mac_int']
            )
        return device_list


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-u', '--update', action='store_true',
        help='Scan network and update db'
    )
    parser.add_argument(
        '-s', '--show', action='store_true',
        help='Scan network, update db and return whos connected as a JSON'
    )
    parser.add_argument(
        '-z', '--ugly', action='store_true',
        help='Don\'t pretty-print the JSON output'
    )
    parser.add_argument(
        '-n', '--network', type=str, default='192.168.1.0/24',
        help='network to scan, use CIDR format, default 192.168.1.0/24'
    )
    parser.add_argument(
        '-a', '--add_name', type=str, nargs=2,
        metavar=('MAC_ADDRESS', 'NAME'),
        help='Add/update name attached to a mac address, '
             'use \'null\' to remove'
    )
    parser.add_argument(
        '-o', '--orgs', action='store_true',
        help='Add organisation data'
    )
    parser.add_argument(
        '-d', '--dump', action='store_true',
        help='Just dump out the database'
    )
    parser.add_argument(
        '-p', '--ping', action='store_true',
        help='Use the ping-scanning method'
    )
    parser.add_argument(
        '-i', '--airodump', action='store_true',
        help='Use the airodump method. NOT IMPLEMENTED YET'
    )
    args = parser.parse_args()

    def printer(args, devices):
        if args.orgs:
            devices = macscan.match_mac_addresses_to_orgs(devices)
        for device in devices:
            device['date'] = device['date'].isoformat()
        if not args.ugly:
            print(json.dumps(devices, sort_keys=True, indent=4))
        else:
            print(json.dumps(devices))

    if args.airodump:
        print('Airodump is not implemented yet, not attempting')

    macscan = MacDeviceScannerMatcher(ip_network=args.network)
    if args.update:
        macscan.update_who_is_here()
    if args.show:
        devices = macscan.scan_add_and_update_macs()
        printer(args, devices)
    if args.add_name:
        mac_addr = args.add_name[0]
        name = args.add_name[1]
        macscan.update_name_on_mac_device(mac_addr, name)
    if args.dump:
        all_seen_devices = macscan.dump_db()
        printer(args, all_seen_devices)
