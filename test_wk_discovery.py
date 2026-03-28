import sys
import os
from odoo.tools import config
from odoo.tools.misc import find_in_path

print("--- Odoo Diagnostic ---")
# Use parse_config with a list of strings
config.parse_config(['-c', 'odoo.conf'])

print(f"Config File: {config.rcfile}")
print(f"Config bin_path: {config.get('bin_path')}")

res = find_in_path('wkhtmltopdf')
print(f"find_in_path('wkhtmltopdf') result: {res}")

if not res:
    bp = config.get('bin_path')
    if bp:
        target = os.path.join(bp, 'wkhtmltopdf.exe')
        print(f"Checking {target}...")
        print(f"Exists: {os.path.exists(target)}")
        print(f"Is file: {os.path.isfile(target)}")
        try:
            st = os.stat(target)
            print(f"Permissions: {oct(st.st_mode)}")
        except Exception as e:
            print(f"Stat error: {e}")
