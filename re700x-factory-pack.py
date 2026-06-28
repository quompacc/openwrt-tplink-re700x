#!/usr/bin/env python3
"""
RE700X TP-Link web-UI-flashable factory-image packer.

Wraps an OpenWrt rootfs UBI into an image accepted by the stock `nvrammanager`
(TP-Link "Upgrade Firmware" web page), so OpenWrt can be installed from stock
with no soldering/UART. Format fully reverse-engineered from the stock ARM
`nvrammanager` (see RE700X-FACTORY-IMAGE-PROBLEM.md). Verified end-to-end with
`qemu-arm-static` running the real binary: `nvrammanager -c` returns success.

File layout:
  0x0000  safeloader preamble (0x14):  size BE u32 @0x00,  md5[16] @0x04
  0x0014  0x1000-byte header gap       (md5'd, not parsed; fw-type is ignored)
  0x1014  FwUpTbl table, FIXED 0x58C (1420) bytes = 12-byte header + 32x44 entries:
            +0x00  field0  BE u32  = ROOTFS SIZE (ubiformat -S); rootfs occupies
                                     the data region first and has NO table entry
            +0x04  count   BE u32  = number of meta entries (<= 32)
            +0x08  field2  BE u32  (unused -> 0)
            +0x0C  entries x 0x2C:  name[32] + base(BE u32) + size(BE u32) + fieldC(BE u32)
  0x1814  data origin: rootfs UBI (size field0) first, then the meta sections

  md5 = MD5( SALT + image[0x14:] );  size@0 = total file length

The stock writer (`nm_upgradeFwupFile`) flashes the rootfs to the inactive
dual-boot slot via:
  ubiformat /dev/mtd<rootfs|rootfs_1> -f "<file>" -o 0x1814 -S <field0> -F /tmp/ubiflag -y
then flips U-Boot env `tp_boot_idx` (fw_setenv) to boot the new slot. Table
entries are only acted on if fieldC in {1: reset FW ptn, 2/3: write ptn by name};
fieldC=0 keeps the mandatory `support-list`/`soft-version` entries validation-only.
"""
import struct, hashlib, os, argparse

SALT      = bytes.fromhex('7a2b15ed9b98596de504ab44ac2a9f4e')   # RE700X md5 salt
TABLE_OFF = 0x1014
DATA_OFF  = 0x1814          # = TABLE_OFF + 0x800  (base[] origin / rootfs start)
ENTRY_SZ  = 0x2C
MAX_ENT   = 32
TABLE_SZ  = 12 + MAX_ENT * ENTRY_SZ     # 0x58C (fixed memcpy size in nm_readFwUpTbl)
HERE      = os.path.dirname(os.path.abspath(__file__))

def make_entry(name, base, size, fieldC):
    nm = name.encode()
    if len(nm) >= 32:
        raise ValueError(f"name too long (>=32): {name!r}")
    return nm + b'\x00' * (32 - len(nm)) + struct.pack('>III', base, size, fieldC)

def build_image(os_data, meta_sections):
    """os_data: rootfs UBI (implicit OS, field0=its size, no table entry).
       meta_sections: list of dict(name=, data=, fieldC=) after the OS, in table order."""
    if len(meta_sections) > MAX_ENT:
        raise ValueError("too many sections")
    field0 = len(os_data)                              # rootfs size (ubiformat -S)
    blob = bytearray(os_data)
    bases, cur = [], field0
    for s in meta_sections:
        bases.append(cur); blob += s['data']; cur += len(s['data'])

    tbl = struct.pack('>III', field0, len(meta_sections), 0)
    for i, s in enumerate(meta_sections):
        tbl += make_entry(s['name'], bases[i], len(s['data']), s.get('fieldC', 0))
    tbl += b'\x00' * (TABLE_SZ - len(tbl))
    assert len(tbl) == TABLE_SZ

    file_len = DATA_OFF + len(blob)
    img = bytearray(b'\xff' * file_len)
    img[TABLE_OFF:TABLE_OFF + TABLE_SZ] = tbl
    img[DATA_OFF:DATA_OFF + len(blob)] = blob
    struct.pack_into('>I', img, 0, len(img))
    img[4:0x14] = hashlib.md5(SALT + bytes(img[0x14:])).digest()
    return bytes(img), field0, bases

def main():
    ap = argparse.ArgumentParser(description="Pack an OpenWrt rootfs UBI into a "
                                 "stock-web-flashable RE700X factory image.")
    ap.add_argument('--os', required=True,
                    help='OpenWrt rootfs UBI (…-tplink_re700x-squashfs-factory.ubi)')
    ap.add_argument('--support-list', default=os.path.join(HERE, 're700x-fwdata', 'support-list'))
    ap.add_argument('--soft-version', default=os.path.join(HERE, 're700x-fwdata', 'soft-version'))
    ap.add_argument('--bump-version', default=None,
                    help='override soft_ver line to always pass anti-downgrade, '
                         'e.g. "9.9.9 Build 20991231 Rel. 99999"')
    ap.add_argument('-o', '--out', required=True, help='output factory image path')
    args = ap.parse_args()

    os_data = open(args.os, 'rb').read()
    sl = open(args.support_list, 'rb').read()
    sv = open(args.soft_version, 'rb').read()
    if args.bump_version:
        sv = b'soft_ver:' + args.bump_version.encode() + sv[sv.index(b'\n'):]
    assert sl.startswith(b'SupportList:'), "support-list must start with 'SupportList:'"
    assert sv.startswith(b'soft_ver:'),    "soft-version must start with 'soft_ver:'"

    meta = [
        {'name': 'support-list', 'data': sl, 'fieldC': 0},
        {'name': 'soft-version', 'data': sv, 'fieldC': 0},
    ]
    img, field0, bases = build_image(os_data, meta)
    open(args.out, 'wb').write(img)

    print(f"wrote {args.out}  ({len(img)} bytes)")
    print(f"  table @ {TABLE_OFF:#x}   data @ {DATA_OFF:#x}")
    print(f"  rootfs (implicit, ubiformat -S field0): size={field0:#x} @ file {DATA_OFF:#x}")
    for i, s in enumerate(meta):
        print(f"  entry[{i}] {s['name']:14} base={bases[i]:#010x} size={len(s['data']):#x} "
              f"(file @ {DATA_OFF+bases[i]:#x})")
    print(f"  md5={img[4:0x14].hex()}")

if __name__ == '__main__':
    main()
