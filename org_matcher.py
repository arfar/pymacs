#!/usr/bin/env python3

import re
import sqlite3
import urllib.request
import os


HEX_CHARS = re.compile(r'[\Wg-zG-Z]')


def hex_str_to_int(hex_str):
    return int(HEX_CHARS.sub('', hex_str), 16)


class MacOrgMatch(object):
    def __init__(self, db_fname='mac.db', recreate=False):
        self.db_fname = db_fname
        self.RE_OUI_MAL = (
            re.compile(r'^[0-9a-fA-f]{2}-[0-9a-fA-f]{2}-[0-9a-fA-f]{2}')
        )
        self.RE_COMPANY_ID = re.compile(r'[0-9a-fA-F]{6}')
        self.RE_OUI_MAS = re.compile(r'[0-9a-fA-F]{6}-[0-9a-fA-F]{6}')

        if recreate:
            self.drop_all_tables()
        self.init_db_tables()

    """
    Database-y stuff first
    """
    def drop_all_tables(self):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            DROP TABLE IF EXISTS organisation;
            ''')
            c.execute('''
            DROP TABLE IF EXISTS mac_addr_org;
            ''')

    def init_db_tables(self):
        with sqlite3.connect(self.db_fname) as conn:
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

    def dump_into_db(self, mac_entry_list):
        """
        There's probably a way to even make this quicker, but its
        fast enough for the moment
        """
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            for entry in mac_entry_list:
                if not entry:
                    continue
                c.execute('''
                INSERT INTO organisation (org_name, org_addr)
                VALUES (?, ?);
                ''', (entry['org_name'], entry['org_addr'],))

        with sqlite3.connect(self.db_fname) as conn:
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

    def _query_mac_address(self, mac_address):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            SELECT * FROM organisation
            INNER JOIN mac_addr_org
            ON mac_addr_org.mac_addr_org = organisation.org_id
            WHERE ? >= mac_addr_org.mac_addr_start AND
                  ? <= mac_addr_org.mac_addr_end;
            ''', (mac_address, mac_address, ))
            return c.fetchmany()

    def add_list_file_to_db(self, mac_list, fname):
        mac_entries_list = [
            self._extract_entry(entry, list_name=mac_list)
            for entry in self._find_next_assignment(fname)
        ]
        self.dump_into_db(mac_entries_list)

    """
    Extraction type functions below here
    """
    def _find_next_assignment(self, fname):
        f = open(fname, 'r', encoding='utf8')
        # Skip past everything before address
        for line in f:
            if 'Address' in line:
                break
            else:
                continue
        tmp_lines = []
        for messy_line in f:
            # want to leave tabs intact
            line = messy_line.strip('\n').strip(' ')
            if line == '' and len(tmp_lines) > 0:
                yield tmp_lines
                tmp_lines = []
            if line == '':
                continue
            tmp_lines.append(line)

    def _extract_entry(self, text, list_name='mal'):
        """
        If it's an MA-L Address block, it'll have the format:
# noqa
import blah
  OUI/MA-L			Organization
  company_id			Organization
                                Address
        or if it's an MA-M Address block:
  OUI     			Organization
  OUI-28/MA-M Range    		Organization
  				Address
        or if it's an MA-S Address block:
  OUI     			Organization
  OUI-36/MA-S Range    		Organization
                                Address
# noqa
        One parser for both MA-M and MA-S should work
        """
        converted_entry = {}
        if list_name == 'mal':
            addr = self.RE_COMPANY_ID.match(text[1]).group(0)
            converted_entry['mac_addr_start'] = int(addr, 16) * (2**24)
            converted_entry['mac_addr_end'] = (
                converted_entry['mac_addr_start'] + 0xFFFFFF
            )
        else:
            oui_addr = int(
                self.RE_OUI_MAL.match(text[0]).group(0).replace('-', ''), 16
            )
            bottom_addr_range = self.RE_OUI_MAS.match(text[1]).group(0)
            start_bottom_addr, end_bottom_addr = bottom_addr_range.split('-')
            converted_entry['mac_addr_start'] = (
                (oui_addr * (2**24)) + int(start_bottom_addr, 16)
            )
            converted_entry['mac_addr_end'] = (
                (oui_addr * (2**24)) + int(end_bottom_addr, 16)
            )
        converted_entry['org_name'] = text[0].split('\t\t')[1]
        converted_entry['org_addr'] = '\n'.join(
            [line.strip() for line in text[2:] if line.strip() != '']
        )
        if 'IEEE REGISTRATION AUTHORITY' in converted_entry['org_name']:
            # This is used as a place holder for other entries, like MA-S
            return None
        return converted_entry

    def _download_mac_file(self, web_addr_suffix, fname):
        web_addr_prefix = 'http://standards.ieee.org/develop/regauth/'
        url = ''.join([web_addr_prefix, web_addr_suffix])
        urllib.request.urlretrieve(url, fname)

    """
    Externally type facing functions here
    """
    def update_db(self, files=None):
        mal_web_addr = 'oui/oui.txt'
        mam_web_addr = 'oui28/mam.txt'
        mas_web_addr = 'oui36/oui36.txt'
        if files:
            mac_list_files_suffix = files
        else:
            mac_list_files_suffix = {}
            mac_list_files_suffix['mal'] = 'mal.txt'
            mac_list_files_suffix['mam'] = 'mam.txt'
            mac_list_files_suffix['mas'] = 'mas.txt'

            self._download_mac_file(mal_web_addr, mac_list_files_suffix['mal'])
            self._download_mac_file(mam_web_addr, mac_list_files_suffix['mam'])
            self._download_mac_file(mas_web_addr, mac_list_files_suffix['mas'])

        # TODO
        #  When there's an update/change, figure out some way to remove ones
        #  that no longer exist

        for mac_file in mac_list_files_suffix:
            self.add_list_file_to_db(
                mac_file,
                mac_list_files_suffix[mac_file]
            )

        for mac_file in mac_list_files_suffix:
            os.renames(mac_list_files_suffix[mac_file],
                       ''.join(['old_', mac_list_files_suffix[mac_file]]))

    def search_by_mac_address_int(self, mac_address):
        """
        mac_address must be int
        returns organisation and address of mac address owner
        """
        if type(mac_address) != int:
            raise TypeError
        formatted_organisations = []
        for org in self._query_mac_address(mac_address):
            organ_dict = {}
            organ_dict['org_name'] = org[1]
            organ_dict['org_addr'] = org[2]
            formatted_organisations.append(organ_dict)
        return formatted_organisations

    def search_by_mac_address_str(self, hex_mac_address):
        return self.search_by_mac_address_int(hex_str_to_int(hex_mac_address))


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: {} [update] [MAC]'.format(sys.argv[0]))
        sys.exit(1)

    m = MacOrgMatch()
    if sys.argv[1][0] == 'u':
        m.update_db()
    else:
        org_infos = m.search_by_mac_address_str(sys.argv[1])
        if org_infos:
            for org_info in org_infos:
                print('Organisation:')
                print('\t{}'.format(org_info['org_name']))
                print('Address:')
                print('\t{}'.format(
                    org_info['org_addr'].replace('\n', '\n\t')
                ))
