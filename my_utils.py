import re

HEX_CHARS = re.compile(r'[\Wg-zG-Z]')

def hex_str_to_int(hex_str):
    return int(HEX_CHARS.sub('', hex_str), 16)

def int_mac_to_hex_mac(int_mac, separator=':'):
    padded_str = '{0:012x}'.format(int_mac)
    split_string = ':'.join([
        '{}{}'.format(padded_str[pos], padded_str[pos+1])
        for pos in range(0, len(padded_str), 2)
    ])
    return split_string
