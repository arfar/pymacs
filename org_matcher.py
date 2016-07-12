#!/usr/bin/env python3

import re
import sqlite3
import urllib.request
import os
import csv

try:
    from settings import MAC_DB_FNAME
except ImportError:
    MAC_DB_FNAME = 'mac.db'


HEX_CHARS = re.compile(r'[\Wg-zG-Z]')

def hex_str_to_int(hex_str):
    return int(HEX_CHARS.sub('', hex_str), 16)

def init_db(recreate=False):
    if recreate:
        drop_tables(MAC_DB_FNAME)
    init_tables(MAC_DB_FNAME)

"""
Database-y stuff first
"""
def drop_tables(db_fname):
    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        c.execute('''
        DROP TABLE IF EXISTS organisation;
        ''')
        c.execute('''
        DROP TABLE IF EXISTS mac_addr_org;
        ''')

def init_tables(db_fname):
    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS organisation (
        org_id      INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        org_name    TEXT NOT NULL,
        org_addr    TEXT,
        UNIQUE (org_name, org_addr)
            ON CONFLICT IGNORE
        );
        ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS mac_addr_org (
        mac_addr_start INTEGER  NOT NULL,
        mac_addr_end   INTEGER  NOT NULL,
        mac_addr_org   INTEGER  NOT NULL,
        FOREIGN KEY(mac_addr_org) REFERENCES organisation(org_id),
        UNIQUE (mac_addr_start, mac_addr_end, mac_addr_org)
            ON CONFLICT IGNORE
        );
        ''')

def dump_into_db(mac_entry_list, db_fname):
    """
    There's probably a way to even make this quicker, but its
    fast enough for the moment
    """
    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        for entry in mac_entry_list:
            if not entry:
                continue
            c.execute('''
            INSERT INTO organisation (org_name, org_addr)
            VALUES (?, ?);
            ''', (entry['org_name'], entry['org_addr'],))

    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        for entry in mac_entry_list:
            if not entry:
                continue
            c.execute('''
            INSERT INTO mac_addr_org
            (mac_addr_start, mac_addr_end, mac_addr_org)
            VALUES (?, ?,
                (SELECT org_id FROM organisation
                 WHERE org_name=? and org_addr=?));
            ''', (
                entry['mac_addr_start'],
                entry['mac_addr_end'],
                entry['org_name'],
                entry['org_addr'],)
            )

def _query_mac_address(mac_address, db_fname):
    with sqlite3.connect(db_fname) as conn:
        c = conn.cursor()
        c.execute('''
        SELECT * FROM organisation
        INNER JOIN mac_addr_org
        ON mac_addr_org.mac_addr_org = organisation.org_id
        WHERE ? >= mac_addr_org.mac_addr_start AND
              ? <= mac_addr_org.mac_addr_end;
        ''', (mac_address, mac_address, ))
        return c.fetchmany()

def add_assignment_file_to_db(assignment_class, fname):
    assignments = extract(assignment_class, fname)
    dump_into_db(assignments, MAC_DB_FNAME)

"""
Non-db functions
"""

def extract(assignment_class, fname):
    extractors = {
        'mal': extract_mal_assignments,
        'mam': extract_mam_assignments,
        'mas': extract_mas_assignments,
    }
    with open(fname, 'r') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip headers
        assignments = extractors[assignment_class](reader)
    return assignments


def extract_mal_assignments(reader):
    assignments = [
        {
            'mac_addr_start': int(row[1], 16) * (2**24),
            'mac_addr_end': int(row[1], 16) * (2**24) + int('FFFFFF', 16),
            'org_name': row[2],
            'org_addr': row[3],
        }
        for row in reader
    ]
    return assignments

def extract_mam_assignments(reader):
    assignments = [
        {
            'mac_addr_start': int(row[1], 16) * (2**20),
            'mac_addr_end': int(row[1], 16) * (2**20) + int('FFFFF', 16),
            'org_name': row[2],
            'org_addr': row[3],
        }
        for row in reader
    ]
    return assignments

def extract_mas_assignments(reader):
    assignments = [
        {
            'mac_addr_start': int(row[1], 16) * (2**16),
            'mac_addr_end': int(row[1], 16) * (2**16) + int('FFF', 16),
            'org_name': row[2],
            'org_addr': row[3],
        }
        for row in reader
    ]
    return assignments

def download_mac_file(suffix, assignment_group):
    web_addr_prefix = 'http://standards.ieee.org/develop/regauth/'
    url = ''.join([web_addr_prefix, suffix])
    filename = ''.join([assignment_group, '.csv'])
    urllib.request.urlretrieve(url, filename)

def update_db():
    assignment_url_suffixes = [
        ('oui/oui.csv', 'mal'),
        ('oui28/mam.csv','mam'),
        ('oui36/oui36.csv', 'mas')
    ]
    for suffix, assignment_group in assignment_url_suffixes:
        download_mac_file(suffix, assignment_group)
        filename = ''.join([assignment_group, '.csv'])
        add_assignment_file_to_db(
            assignment_group,
            filename,
        )

def search_by_mac_address_int(mac_address):
    """
    mac_address must be int
    returns organisation and address of mac address owner
    """
    if type(mac_address) != int:
        raise TypeError
    formatted_organisations = []
    for org in _query_mac_address(mac_address, MAC_DB_FNAME):
        organ_dict = {}
        organ_dict['org_name'] = org[1]
        organ_dict['org_addr'] = org[2]
        formatted_organisations.append(organ_dict)
    return formatted_organisations

def search_by_mac_address_str(hex_mac_address):
    return search_by_mac_address_int(hex_str_to_int(hex_mac_address))

__all__ = [
    'search_by_mac_address_int',
    'search_by_mac_address_str',
    'init_db',
    'update_db',
]

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print('Usage: {} [rewrite|upgrade|trash] [MAC]'.format(sys.argv[0]))
        sys.exit(1)

    if sys.argv[1][0] in 'rRuUtT':
        init_db(recreate=True)
        update_db()
    else:
        org_infos = search_by_mac_address_str(sys.argv[1])
        if org_infos:
            for org_info in org_infos:
                print('Organisation:')
                print('\t{}'.format(org_info['org_name']))
                print('Address:')
                print('\t{}'.format(
                    org_info['org_addr'].replace('\n', '\n\t')
                ))
        else:
            print('Failed to find an organisation matching {}'.format(sys.argv[1]))
