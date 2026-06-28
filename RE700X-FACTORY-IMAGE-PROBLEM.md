# RE700X Factory-Image / TP-Link `FwUpTbl` Format — SOLVED

> **Status: SOLVED & PROVEN ON REAL HARDWARE.** The stock `nvrammanager` upload
> format is fully reverse-engineered and a packer (`re700x-factory-pack.py`)
> produces a web-UI-flashable OpenWrt factory image. It passes `nvrammanager -c`
> (acceptance) and — verified end-to-end on a real RE700X — `nvrammanager -u`
> flashes the rootfs into the inactive dual-boot slot and the device reboots
> into a fully-working OpenWrt 6.12.91. The full end-user path — uploading the
> image through the **stock TP-Link web GUI** — worked on one real RE700X. See §8.
>
> ✅ **The brick is FIXED (v1.5).** It bricked a second unit because the kernel
> cmdline was force-set (`CONFIG_CMDLINE_FORCE` + `ubi.mtd=rootfs`): the stock
> flasher wrote OpenWrt to slot `rootfs_1` and set `tp_boot_idx=1`, but the forced
> cmdline still attached slot 0 → wrong root → no boot (recoverable only via UART;
> no button/TFTP recovery). A UART diagnostic (a `CONFIG_CMDLINE_FROM_BOOTLOADER`
> build) confirmed the stock U-Boot already passes a slot-correct `ubi.mtd=rootfs_1`
> — only its `root=mtd:ubi_rootfs` was unmountable by mainline. **Fix:** drop the
> `CMDLINE_FORCE` hack from `config-6.12` and add
> `bootargs-append = " root=/dev/ubiblock0_1 coherent_pool=4M"` to the DTS
> `/chosen`; the kernel inherits the slot-correct `ubi.mtd` and the appended
> `root=` wins. Verified on hardware: OpenWrt boots cleanly from **both** slots.
> **Still pending:** the literal stock→web-GUI re-test (official firmware is
> AES-encrypted "Cloud"; the stock NAND backup was lost) — logically covered, since
> `nvrammanager` writes the slot byte-identically to what was tested (`ubiformat
> -o 0x1814 -S <field0>`) and sets the same `tp_boot_idx`. `sysupgrade` is unaffected.

---

## 1. Goal

Produce a **web-UI-flashable factory image** for the TP-Link RE700X (EU v1.0,
IPQ5018 + QCN6122) that installs OpenWrt via the **stock TP-Link web GUI**
("Upgrade Firmware") — no soldering, no UART. The OpenWrt port itself is done
and fully working; this is only about wrapping the rootfs so the stock firmware
accepts and flashes it.

## 2. How the stock web upgrade works

- Stock web "Upgrade" runs the stock flasher **`nvrammanager`** (ARM 32-bit ELF,
  `usr/bin/nvrammanager` in the stock rootfs).
  - `-u <file>` = upgrade (writes flash); `-c <file>` = check only (validate, no
    flash) — used for all local testing.
- **No RSA signature, no encryption for local upload.** (The fw-type is even
  hardcoded to "Cloud" internally, and MD5 is *not enforced* on the local path —
  see §6.) The AES "cloud" key hunt was irrelevant.
- **Outer wrapper = TP-Link safeloader:** `size` (BE u32 @0x00) = total length;
  `md5[16]` @0x04 = `MD5(salt + image[0x14:])`; **salt (RE700X)** =
  `7a2b15ed9b98596de504ab44ac2a9f4e`. Payload starts at `0x14`.

## 3. The `FwUpTbl` format (reverse-engineered)

The binary was disassembled with capstone (PIC ARMv7 — addresses built via
`movw`/`movt`, **not** literal pools, which is why earlier linear/xref attempts
found nothing). Functions decoded: `nm_readFwUpTbl`, `nm_checkUpContents`,
`nm_checkSupportList`, `nm_checkSoftVer`, `CheckUpgradeFile` (fw-type),
`nm_buildUpgradeStruct`, `nm_upgradeFwupFile`, `nm_upgradeUbiImg`,
`nm_checkBootAlter`/`nm_addBootAlter`/`nm_removeBootAlter`, `upgradeFirmware`.

### File layout

```
0x0000  safeloader preamble (0x14):  size BE u32 @0x00,  md5[16] @0x04
0x0014  0x1000-byte header gap       (md5'd, NOT parsed)
0x1014  FwUpTbl table, FIXED 0x58C (1420) bytes = 12-byte header + 32 x 44 entries:
          +0x00  field0  BE u32   = ROOTFS UBI SIZE (see §4); rootfs has NO entry
          +0x04  count   BE u32   = number of meta entries (<= 32)
          +0x08  field2  BE u32   (unused -> 0)
          +0x0C  entries x 0x2C (44) bytes:
                   +0x00  name[32]   (NUL-padded)
                   +0x20  base   BE u32   (offset rel. 0x1814)
                   +0x24  size   BE u32
                   +0x28  fieldC BE u32   (content type: see §4)
0x1814  data origin: rootfs UBI FIRST (size = field0), then the meta sections
```

The table is a fixed 1420-byte struct (`nm_readFwUpTbl` `memcpy`s exactly
`0x58C` = `12 + 32*44`). Entry stride is fixed 44 — **not** count-dependent
(the old "80 vs 96" observation was an artifact of a wrong layout guess).

### Validation rules (`nm_readFwUpTbl` + `nm_checkUpContents`)

- `count <= 32`.
- Meta sections **contiguous**: `base[0] == field0`, `base[i] == field0 +
  Σ size[0..i-1]` (any gap → `wrong size at ptn`; the old "overlap" failures
  were the wrong layout too).
- `file_len >= 0x1814 + base_last + size_last` (the "0x800 footer" is just the
  `0x1014 → 0x1814` gap, not a trailer).
- Entries named **`support-list`** (data must start `SupportList:`) and
  **`soft-version`** (data must start `soft_ver:`) are mandatory **by name**.

### Content checks (device-dependent)

- `nm_checkSupportList`: reads device product-info (`/tp_data/manu_data/
  product-info`) and requires its `special_id` to match a line in the
  `support-list`. Lift the support-list verbatim from stock `fw_data/` — it
  lists all RE700X regions, so any real RE700X matches.
- `nm_checkSoftVer`: image `soft_ver` **major.minor must be >= the device's
  installed version** (anti-downgrade). Use stock `soft-version`, or
  `--bump-version` to always pass.

## 4. The write path (`nm_upgradeFwupFile`) — why `field0` = rootfs size

`-u` calls `nm_upgradeFwupFile(P=file+0x1014, L, 0x1014, "<file path>")`:

1. **Per-entry loop** over `fieldC` (entry+0x28): `2/3` → write section data to
   the flash partition named `name`; `1` → reset FW partition `name`; **anything
   else (incl. 0) → skipped.** So meta entries with `fieldC=0` are
   validation-only and never written.
2. **The rootfs is flashed separately**, always, *not* via a table entry. It
   picks the inactive dual-boot slot and runs:
   ```
   ubiformat /dev/mtd<rootfs|rootfs_1> -f "<uploaded file>" -o 0x1814 -S <field0> -F /tmp/ubiflag -y
   ```
   i.e. it writes `file[0x1814 : 0x1814+field0]`. **Therefore `field0` = rootfs
   size and the rootfs sits first at file offset `0x1814`.** (An earlier image
   with `field0=0` passed `-c` but would have run `ubiformat -S 0` → flashed an
   empty rootfs.)

### Dual-boot slot switching

- Active slot = U-Boot env `tp_boot_idx` (0/unset = `rootfs`, 1 = `rootfs_1`).
- `nm_checkBootAlter` reads `/proc/cmdline`, returns 1 iff it contains
  `mtd=rootfs_1` (i.e. currently on slot 1).
- Write goes to the **inactive** slot, then: running slot0 → write `rootfs_1` +
  `nm_addBootAlter` (`fw_setenv tp_boot_idx 1`); running slot1 → write `rootfs` +
  `nm_removeBootAlter` (`fw_setenv tp_boot_idx`). The other slot keeps stock as a
  fallback — this is what makes the flash low-risk.

## 5. The packer

`re700x-factory-pack.py` (this dir) builds the image; bundled generic stock
metadata in `re700x-fwdata/{support-list,soft-version}`.

```sh
./re700x-factory-pack.py \
  --os bin/targets/qualcommax/ipq50xx/openwrt-qualcommax-ipq50xx-tplink_re700x-squashfs-factory.ubi \
  -o /tmp/re700x-factory.bin
# optional anti-downgrade override:  --bump-version "9.9.9 Build 20991231 Rel. 99999"
```

## 6. Debunked assumptions (from the original investigation)

- Entry stride is **fixed 44**, not count-dependent.
- The "0x800 footer" is the `0x1014→0x1814` gap, not a trailer.
- Overlap/`wrong size` are a simple **contiguity** check, not a flash-size ref.
- fw-type is **hardcoded to "Cloud"** (the `fw-type:` sscanf result is
  overwritten) → no AES, and the 0x1000 header gap content is irrelevant.
- **MD5 is not even enforced** on the local `-c`/upload path (the Cloud branch
  skips the verify block) — ours is correct anyway.

## 7. Local test harness (no device needed)

`qemu-arm-static -L $ROOT $ROOT/usr/bin/nvrammanager -c /upgrade/test.bin`, with
`$ROOT` = extracted stock rootfs. To exercise the `support-list` device-match
locally, copy stock `fw_data/manu_data/product-info` to the sandbox
`$ROOT/tp_data/manu_data/product-info`. Result: `md5 verify ok!` +
`chekc firmware file success!`, exit 0.

## 8. Real-hardware validation (DONE)

Proven on a real RE700X (2026-05-31). `nvrammanager` runs natively on the
device, so the flash was tested directly: `nvrammanager -u <image>` validated,
ran `ubiformat /dev/mtd11 ... -S <field0>` into the inactive `rootfs` slot, and
rebooted; U-Boot then booted that slot into a fully-working **OpenWrt 6.12.91**
(squashfs root via `root=/dev/ubiblock0_1`, overlay, ath11k, LAN, login). So the
whole `-c` → `-u` → reboot → boot chain works.

The earlier `ubi_rootfs`-vs-`rootfs` volume-name concern was MOOT: the OpenWrt
FIT image carries its own bootargs (`root=/dev/ubiblock0_1`, ubiblock on the
standard `rootfs` volume) and does not use the stock `root=mtd:ubi_rootfs` path.

### Web-GUI path (the real end-user flow) — also verified

Restored stock to a slot from a full backup, booted it, and uploaded the image
through the **stock TP-Link web GUI** ("Firmware Upgrade"). It flashed and
rebooted into OpenWrt 6.12.91. So the end-user path (pristine stock → web GUI →
OpenWrt) works. The web upgrade runs via the `nvram_ubus` ubus daemon (luci
`controller/admin/firmware.lua` → `nvrammanager`); stock has no root shell, only
U-Boot + the web GUI — exactly what an end user has.

Use `--bump-version` so the image's `soft_ver` major.minor is ≥ the device's
installed stock version (anti-downgrade).

### `tp_boot_idx` / slot-attach gotcha (only when hand-restoring stock for a test)

Stock's `etc/init.d/wifi_fw_mount` ubiattaches the rootfs slot selected by the
U-Boot env `tp_boot_idx` — the WLAN/ADSP firmware lives as squashfs sub-volumes
*inside* the rootfs UBI. If you manually boot a slot in U-Boot without setting
`tp_boot_idx` to match, wifi_fw_mount attaches the **other** (inactive) slot,
which is exactly the upgrade target → `ubiformat` then fails ("Fail to flash ubi
image"). Fix before booting stock for the test: `setenv tp_boot_idx 1; saveenv`
(for `rootfs_1`). On a genuine device `tp_boot_idx` always matches the booted
slot, so this never happens and the web-GUI flash works out of the box.

Other artifacts of testing from a *live* OpenWrt (NOT issues on stock):
- `ubiformat` refuses a UBI-attached target mtd → `ubidetach -m <n>` first.
- `/tmp` is tmpfs; a large file can OOM/vanish → stream (`wget -O - | nandwrite`)
  or restore via U-Boot TFTP (`tftpboot` + `nand erase`/`nand write`).

## 9. Safety / repo policy

Do **not** publish device-specific MACs, serials, PINs, or ART/calib dumps. The
bundled `support-list`/`soft-version` are generic per-model stock metadata (no
per-device data). See `NOTES-re700x.md`. Port branch `tplink-re700x-wip`.
