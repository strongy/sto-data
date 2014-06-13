A parsing library for STO Gateway output.

Dependencies
=======
- Python dateutil
https://pypi.python.org/pypi/python-dateutil/1.5

- Unicode CSV
https://github.com/jdunck/python-unicodecsv

Use pip to install both, making sure they are the right versions!

Input File Format
=======
The import file is extracted from Chrome's Developer Tools.  In Chrome 36, this is accessed from View -> Developer -> Developer Tools.  Go to the Network tab, then log into the Gateway.  Do this before you log in, otherwise the right network access will not be properly captured.

The file is sourced from their WebSocket-style endpoint at /socket.io/1/xhr-polling, and should begin with Proxy_Guild for general fleet information or Proxy_GroupProject for contributions data.

Once you have found the correct source data, click it, then right click from the left-side bar to "Copy Response", then paste it into a text document.  You can also save it as a HAR file, which the library will attempt to parse.

Usage
======
The default invocation:
python sto_fc.py <path_to_json_or_har> <fleet_name> <path_for_csv>

Example: python sto_fc.py /Users/foo/tmp/gateway.har COA /tmp/coa.csv"

Will take the default HAR file, use the name given, and output a CSV of Lifetime Fleet Credit contributions per account to /tmp/coa.csv.


Notes
======
There are additional functions available in the library currently not documented, such as GrandFleet (which treats multiple fleets as one for processing fleet credit data -- useful for promotions across Fed/KDF fleets), or LFC diffs (from a previous data capture, useful to determine who contributed the most since the last capture)

I'll fix this up when I get time.