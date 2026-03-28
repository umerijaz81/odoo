import sys
import os
from odoo.tools import config
from odoo.addons.base.models.ir_actions_report import _wkhtml

print("--- Odoo Diagnostic Full State ---")
config.parse_config(['-c', 'odoo.conf'])

wkinfo = _wkhtml()
print(f"State: {wkinfo.state}")
print(f"Version: {wkinfo.version}")
print(f"Bin: {wkinfo.bin}")
print(f"Patched QT: {wkinfo.is_patched_qt}")
print(f"Workers: {config['workers']}")

if wkinfo.state != 'ok':
    print("REASON FOR FAILURE:")
    if wkinfo.state == 'install':
        print("- Binary not found in path.")
    elif wkinfo.state == 'upgrade':
        print("- Version too old (< 0.12.0).")
    elif wkinfo.state == 'workers':
        print("- Multiprocessing required (workers=1 is not allowed).")
    elif wkinfo.state == 'broken':
        print("- Binary is broken or not responding to --version.")
