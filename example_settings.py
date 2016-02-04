# None are required, all of these given are the defaults
ARP_BIN = '/usr/sbin/arp'

MAC_DB_FNAME = 'mac.db'

IP_NETWORK = '192.168.1.0/24'  # In CIDR format

PING_BIN = '/bin/ping'

# Beacuse arp will often not find you in the arp cache, we need a helping hand
#  pickup out ourselves
import socket
import fcntl
import struct

def get_own_ip_address_hostname():
    # Often just returns '127.0.0.1', depending on how /etc/hosts is set up
    return socket.gethostbyname(socket.gethostname())

def get_own_ip_address_connect():
    # Will only work if device has internet connection
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip_addr = s.getsockname()[0]
    s.close()
    return ip_addr

def get_mac_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]

OWN_IP_ADDRESS = get_own_ip_address_connect()
OWN_MAC_ADDRESS = get_mac_address(OWN_IP_ADDRESS)
