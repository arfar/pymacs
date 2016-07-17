import re

HEX_CHARS = re.compile(r'[\Wg-zG-Z]')

def hex_str_to_int(hex_str):
    return int(HEX_CHARS.sub('', hex_str), 16)
