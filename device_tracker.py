import settings
import sqlite3

def init_tables():
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS device (
        dev_id          INTEGER  PRIMARY KEY  NOT NULL,
        dev_mac_addr    INTEGER,
        dev_name        TEXT,
        UNIQUE (dev_mac_addr) ON CONFLICT IGNORE
        );
        ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS timeline (
        time_id          INTEGER  PRIMARY KEY  NOT NULL,
        time_datetime    DATE     NOT NULL,
        time_present     BOOL,
        time_device_id   INTEGER  NOT NULL,
        FOREIGN KEY (time_device_id) REFERENCES device(dev_id)
        );
        ''')

def drop_tables():
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        DROP TABLE IF EXISTS device;
        ''')
        c.execute('''
        DROP TABLE IF EXISTS timeline;
        ''')

def add_device(device):
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        INSERT INTO device (dev_mac_addr) VALUES (?);
        ''', (device['mac_int'],))

def add_device_name(mac_addr, dev_name):
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        UPDATE device
        SET dev_name = ? WHERE dev_mac_addr = ?
        ''', (dev_name, mac_addr))

def all_devices():
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        SELECT * FROM device
        ''')
        return c.fetchall()
