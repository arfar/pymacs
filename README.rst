pymacs
======
Currently two separate tools (one uses the other for some features though):

#. org_matcher.py
#. device_scanner.py

org_matcher.py
--------------
Stupid simple little app which will download all the OUI MAC address
information from IEEE (comes in large text files )and put it into a database.

Then also some functions to search, given the MAC address, the organisation
which "owns" it. Obviously this won't be 100% in ensuring that the device is
what it's MAC address says it is (MAC addresses can be changed), but probably
99% of devices don't change their MAC address, so thats cool.

Usage
~~~~~
You can use this as a command line tool, or import it like a library. Also
doesn't have any external dependancies.

CLI tool is pretty straight forward, simply use ``update`` to update the
database, or give it the MAC address hex string. Almost any format of MAC will
work, it strips anything that matches the regex ``[\Wg-zG-Z]``

::

    Usage: ./org_matcher.py [update] [MAC]

Using it as a library can be seen in `device_scanner.py`_

TODO
~~~~
If there ever were a record to be removed from the .txt files downloaded from
IEEE, my script can't handle that. I had funny ideas of doing diffs of the old
saved files, but probably what a better stratergy would be is just to create a
second temporary table to save all of the new records, then just point to that
table as the up to date one. That way I could still track differences if I
really wanted to probably with some sort of ``INNER JOIN``.

device_scanner.py
-----------------
A little bit more complex than the last tool. This script is used to maintain a
list of known devices on your local network (or potentially any near-by
wireless devices if I can get ``airdump-ng`` going) and save when they were last
seen. Kind-of creepy, kind-of useful to know who was home and when.

It also hooks in with `org_matcher.py`_ to help with figuring out which MAC is
which device.

Currently it doesn't do anything other than associate a ``name`` entry with
each MAC address and save the last time it was seen.

Usage
~~~~~
I'll just dump the output of ``./device_scanner --help`` here, hopefully it's
obvious how it works.

::

    usage: device_scanner.py [-h] [-u] [-s] [-z] [-n NETWORK]
                             [-a MAC_ADDRESS NAME] [-o] [-d] [-p] [-i]

    optional arguments:
      -h, --help            show this help message and exit
      -u, --update          Scan network and update db
      -s, --show            Scan network, update db and return whos connected as a
                            JSON
      -z, --ugly            Don't pretty-print the JSON output
      -n NETWORK, --network NETWORK
                            network to scan, use CIDR format, default
                            192.168.1.0/24
      -a MAC_ADDRESS NAME, --add_name MAC_ADDRESS NAME
                            Add/update name attached to a mac address, use 'null'
                            to remove
      -o, --orgs            Add organisation data
      -d, --dump            Just dump out the database
      -p, --ping            Use the ping-scanning method
      -i, --airodump        Use the airodump method. NOT IMPLEMENTED YET

TODO
~~~~
* Shouldn't actually be too hard to implement, but it'd be interesting to save
  when devices are seen (or not) so that you could plot when someone is home
  during the day.

* Implement the airdump-ng method so that you can passively scan for devices
  and not therefore it isn't a requirement for them to be connected to the
  network.

License
=======
AGPLv3

Also I imagine IEEE wouldn't be too happy if someone just repackaged their tool
which `does the same thing already
<http://standards.ieee.org/develop/regauth/oui/public.html>`_ and tried to make
money off of it. IANAL, but I think there's probably some copyright claim or
the like of their database contents.
