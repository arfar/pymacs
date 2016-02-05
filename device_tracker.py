import 

        if recreate:
            self.db_drop_tables()
        self.db_init_tables()

    def db_init_tables(self):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            CREATE TABLE IF NOT EXISTS macs_device (
            dev_mac_addr    INTEGER  PRIMARY KEY  NOT NULL,
            dev_name        TEXT,
            dev_last_seen   TIMESTAMP
            );
            ''')

    def db_drop_tables(self):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            DROP TABLE IF EXISTS macs_device;
            ''')

    def db_add_mac_address(self, mac_entry):
        with sqlite3.connect(self.db_fname) as conn:
            c = conn.cursor()
            c.execute('''
            INSERT OR REPLACE INTO macs_device
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
            INSERT OR REPLACE INTO macs_device
            (dev_mac_addr, dev_name, dev_last_seen)
            VALUES (?, ?,
                (SELECT dev_last_seen FROM device WHERE dev_mac_addr = ?)
            );
            ''', (mac_addr, dev_name, mac_addr, ))
