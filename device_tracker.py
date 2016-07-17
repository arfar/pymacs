import settings
import sqlite3
import my_utils as u

def init_tables():
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS device (
        device_id          INTEGER  PRIMARY KEY  NOT NULL,
        device_mac_addr    INTEGER,
        device_name        TEXT,
        UNIQUE (device_mac_addr) ON CONFLICT IGNORE
        );
        ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS time_line (
        time_line_id             INTEGER  PRIMARY KEY  NOT NULL,
        time_line_device_id      INTEGER  NOT NULL,
        time_line_time_stamp_id  INTEGER  NOT NULL,
        FOREIGN KEY (time_line_device_id) REFERENCES device(device_id)
        FOREIGN KEY (time_line_time_stamp_id) REFERENCES time_stamp(time_stamp_id)
        );
        ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS time_stamp (
        time_stamp_id        INTEGER    PRIMARY KEY  NOT NULL,
        time_stamp_datetime  TIMESTAMP  NOT NULL,
        UNIQUE (time_stamp_datetime) ON CONFLICT IGNORE
        );
        ''')


def drop_tables():
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        DROP TABLE IF EXISTS device;
        ''')
        c.execute('''
        DROP TABLE IF EXISTS time_line;
        ''')
        c.execute('''
        DROP TABLE IF EXISTS time_stamp;
        ''')

def add_device(device):
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        INSERT INTO device (device_mac_addr) VALUES (?);
        ''', (device['mac_int'],))

def add_device_name(mac_addr, dev_name):
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        UPDATE device
        SET device_name = ? WHERE device_mac_addr = ?
        ''', (dev_name, mac_addr))

def all_devices():
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        SELECT * FROM device
        ''')
        return c.fetchall()

def add_timestamp(time):
    with sqlite3.connect(settings.MAC_DB_FNAME, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        c = conn.cursor()
        c.execute('''
        INSERT INTO time_stamp (time_stamp_datetime) VALUES (?);
        ''', (time,))

def add_device_on_timeline(device, timestamp):
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        INSERT INTO time_line
            (time_line_device_id,
             time_line_time_stamp_id)
        VALUES (
            (SELECT device_id FROM device WHERE device_mac_addr=?),
            (SELECT time_stamp_id FROM time_stamp WHERE time_stamp_datetime=?)
        );
        ''', (device['mac_int'], timestamp,))
        return c.lastrowid

def get_device_history_mac_string(device_mac_str, datetime_range=()):
    mac_int = u.hex_str_to_int(device_mac_str)
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        SELECT device_id FROM device WHERE device_mac_addr=?
        ''', (mac_int,))
        device_id = c.fetchone()
    try:
        device_id = device_id[0]
    except TypeError:
        # Device mac not found probably
        return []
    return _get_device_history_id(device_id, datetime_range)

def get_device_history_name(device_name, datetime_range=()):
    with sqlite3.connect(settings.MAC_DB_FNAME) as conn:
        c = conn.cursor()
        c.execute('''
        SELECT device_id FROM device WHERE device_name=?
        ''', (device_name,))
        device_id = c.fetchone()
    return _get_device_history_id(device_id, datetime_date)

def _get_device_history_id(device_id, datetime_range=()):
    # TODO - Put more of this logic into the DB call - I'm sure it can
    #        all/mostly be done within SQL, which means it'll probably be 100x
    with sqlite3.connect(settings.MAC_DB_FNAME, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        c = conn.cursor()
        if datetime_range:
            # TODO - Actually implement a date range - currently just going
            #        to return all dates even if a datetime range is set
            return []
        else:
            c.execute('''
            SELECT * FROM time_stamp
            ''')
            time_stamps = c.fetchall()
        c.execute('''
        SELECT * FROM time_line WHERE time_line_device_id=?
        ''', (device_id,))
        device_timeline_db = c.fetchall()

    # THIS IS TERRIBLY IN EFFICIENT CODE - I JUST WANT TO GET SOMETHING WORKING
    # FOR THE MOMENT
    device_timeline = []
    for time_stamp in time_stamps:
        for device_db in device_timeline_db:
            if time_stamp[0] == device_db[2]:
                device_timeline.append((time_stamp[1], True))
                break
        else:
            device_timeline.append((time_stamp[1], False))
    return device_timeline
