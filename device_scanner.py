#!/usr/bin/env python3
"""
Just does scanning, no database stuff
"""

import org_matcher as mac_org
import multiprocessing
import subprocess
import ipaddress
import os
import datetime
import json


class MacDeviceScannerMatcher(object):
    def __init__(self, arp_bin, ping_bin, ip_network='192.168.1.0/24',
                 recreate=False, own_ip_address=None, own_mac_address='self'):
        self.mac_org_match = mac_org.MacOrgMatch()
        self.own_ip_address = own_ip_address
        self.own_mac_address = own_mac_address

        if not os.path.exists(arp_bin):
            print('Couldn\'t find arp executable, scanning won\'t work')
            print(' which probably means this tool will be pretty useless')
            self.arp_bin = None
        else:
            self.arp_bin = arp_bin

        if not os.path.exists(ping_bin):
            print('Couldn\'t find ping executable, scanning won\'t work at all')
            print(' which probably means this tool will be pretty useless')
            self.ping_bin = None
        else:
            self.ping_bin = ping_bin

        self.ip_network = ip_network

    def _pinger(self, job_q, results_q):
        # Modified from:
        # http://stackoverflow.com/questions/21225464/fast-ping-sweep-in-python
        DEVNULL = open(os.devnull, 'w')
        while True:
            ip = job_q.get()
            if not ip:
                break
            result = subprocess.call([self.ping_bin, '-c1', ip],
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
            if ip == self.own_ip_address:
                device = {
                    'ip': ip,
                    'mac_hex_str': self.own_mac_address,
                    'mac_int': mac_org.hex_str_to_int(self.own_mac_address),
                }
                devices.append(device)
            p = subprocess.Popen([self.arp_bin, '-e', ip],
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
        return devices

def match_mac_addresses_to_orgs(self, device_list):
    for device in device_list:
        device['org'] = mac_org.search_by_mac_address_int(
            device['mac_int']
        )
    return device_list


if __name__ == '__main__':
    import argparse
    import settings
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s', '--show', action='store_true',
        help='Scan network and print found devices in JSON format'
    )
    parser.add_argument(
        '-z', '--ugly', action='store_true',
        help='Don\'t pretty-print the JSON output'
    )
    parser.add_argument(
        '-n', '--network', type=str,
        help='network to scan, use CIDR format, default 192.168.1.0/24'
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

    if args.airodump:
        print('Airodump is not implemented yet, not attempting')

    if args.network:
        ip_network = args.network
    elif hasattr(settings, 'IP_NETWORK'):
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

    macscan = MacDeviceScannerMatcher(arp_bin, ping_bin, ip_network,
                                      own_ip_address=own_ip_address,
                                      own_mac_address=own_mac_address)
    def printer(args, devices):
        if args.orgs:
            devices = macscan.match_mac_addresses_to_orgs(devices)
        for device in devices:
            # to make it all pretty for JSON stuff
            device['date'] = device['date'].isoformat()
        if not args.ugly:
            print(json.dumps(devices, sort_keys=True, indent=4))
        else:
            print(json.dumps(devices))

    if args.show:
        devices = macscan.scan_add_and_update_macs()
        printer(args, devices)
