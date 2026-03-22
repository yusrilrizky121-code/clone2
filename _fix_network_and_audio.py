import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

# ── 1. network_security_config.xml — tambah googlevideo.com ─────────────────
nsc = '''<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">youtube.com</domain>
        <domain includeSubdomains="true">ytimg.com</domain>
        <domain includeSubdomains="true">googlevideo.com</domain>
        <domain includeSubdomains="true">googleapis.com</domain>
        <domain includeSubdomains="true">vercel.app</domain>
        <domain includeSubdomains="true">firebaseapp.com</domain>
        <domain includeSubdomains="true">firestore.googleapis.com</domain>
        <domain includeSubdomains="true">gstatic.com</domain>
        <domain includeSubdomains="true">google.com</domain>
    </domain-config>
</network-security-config>
'''

with open(r'auspoty-flutter\android\app\src\main\res\xml\network_security_config.xml', 'w', encoding='utf-8') as f:
    f.write(nsc)
print("network_security_config.xml updated")
