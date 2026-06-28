# TP-Link RE700X (IPQ5018) — Image Changelog

Tracks flashable OpenWrt images for the RE700X EU v1.0 port on branch
`tplink-re700x-wip`. Versions are git-tagged (`re700x-vX.Y`). The `sha256` is of
the `squashfs-sysupgrade.bin` built from that commit. Doc-only changes
(NOTES/CHANGELOG) do not alter the firmware image, so a tagged image's sha256
stays valid across later documentation commits.

> ✅ **The dual-boot brick is FIXED as of v1.5** — OpenWrt now boots from either
> flash slot, validated on real hardware. The *literal* stock web-GUI
> reproduction is still pending (the official firmware is AES-encrypted and the
> stock NAND backup was lost), so for the very first flash from stock keep UART
> + a NAND backup handy until someone re-runs a full stock→web-GUI install.
> `sysupgrade` (OpenWrt→OpenWrt) is safe. See `README.RE700X.md`.

## v1.5 — 2026-06-28 (tag `re700x-v1.5`)

**Dual-boot brick FIXED** — OpenWrt boots from whichever flash slot the installer
writes, killing the stock-web-GUI brick.

- **Root cause** (confirmed via UART): the kernel cmdline was force-set
  (`CONFIG_CMDLINE_FORCE` + `ubi.mtd=rootfs`), so when the stock flasher wrote
  OpenWrt into the inactive dual-boot slot `rootfs_1` and set `tp_boot_idx=1`,
  the kernel still attached slot 0 (`rootfs`) → wrong/old root → no boot.
- **Diagnosis** (UART, safe slot-1-only test): a `CONFIG_CMDLINE_FROM_BOOTLOADER`
  build showed the stock U-Boot *already* passes a slot-correct `ubi.mtd=rootfs_1`
  — only with an unmountable `root=mtd:ubi_rootfs`, which is the sole cause of the
  panic/bootloop.
- **Fix** (idiomatic qualcommax, **no kernel patch**): removed the RE700X
  `CMDLINE_FORCE` hack from `target/linux/qualcommax/config-6.12`, and in the DTS
  `/chosen` added `bootargs-append = " root=/dev/ubiblock0_1 coherent_pool=4M"`
  (same mechanism the other ipq5018 boards use). The kernel now inherits U-Boot's
  slot-correct `ubi.mtd` and the appended `root=` wins over `root=mtd:ubi_rootfs`.
- **Validated on real hardware:** clean boot from **both** slots (`rootfs` *and*
  `rootfs_1`), both radios up, `coherent_pool=4M` honoured. So no matter which slot
  the web-GUI flasher targets, OpenWrt boots.
- **Still pending:** the *literal* stock→web-GUI install couldn't be re-run this
  round (official firmware is AES-encrypted "Cloud" type; the stock backup was
  lost). It's logically covered — `nvrammanager` writes the slot byte-identically
  to what was tested and sets the same `tp_boot_idx` — but a real stock-device
  web-GUI flash remains the final belt-and-suspenders check.
- sha256 (sysupgrade): see the release's `SHA256SUMS` (CI-built).

## v1.4 — 2026-05-31 (tag `re700x-v1.4`)

**Both Wi-Fi radios stable at once** — the OOM fix.

- **ath11k DP-ring shrink** (`patches/ath11k/952-ath11k-reduce-dp-ring-sizes-for-256MB.patch`,
  values from openwrt/openwrt#21495 / `CONFIG_ATH11K_SMALLBUFFERS`): ath11k
  pre-allocated ~94 MB of oversized RX/TX ring skbs (per radio) → OOM with both
  radios on 256 MB. Shrunk the rings (TX-comp 32768→2048, RXDMA-buf 4096→1024,
  monitor rings 1024/4096/2048→512/128/128).
- **5 GHz (QCN6122) re-enabled** — both radios now run with **~48 MB free** on the
  256 MB device, confirmed stable on hardware.
- sha256 (sysupgrade): see the release's `SHA256SUMS` (CI-built).

## v1.3 — 2026-05-31 (tag `re700x-v1.3`)

Slimmer, nicer web UI + German. **Theme is `luci-theme-material`** (the Argon
feed wouldn't build against this OpenWrt). Built/flashed via `sysupgrade`.

- Dropped `luci-ssl` + `luci-app-firewall` + `luci-app-package-manager` (and the
  old custom theme) → `luci-light` + `luci-app-statistics` (Network / Wireless /
  System / Status / Statistics only). Much less cluttered.
- **`luci-theme-argon`** + `luci-app-argon-config` — modern, configurable look
  (background, blur, accent colour, dark mode), set in the UI.
- Web UI defaults to **German** (`CONFIG_LUCI_LANG_de=y` + a board-gated
  `uci-defaults` that sets `luci.main.lang=de`).
- `usteer` + `luci-app-usteer` kept (wired-backhaul client steering / roaming).
- DTS: tidied the QCN6122 comment block (no functional change).
- sha256 (sysupgrade): see the release's `SHA256SUMS` (CI-built).

## v1.2 — 2026-05-31 (tag `re700x-v1.2`)

Same firmware as v1.0/v1.1 — this release adds automation + docs:

- **CI auto-build**: pushing a `re700x-v*` tag now builds the image and publishes
  the release with all assets automatically via GitHub Actions
  (`.github/workflows/re700x-release.yml`), using the built-in `GITHUB_TOKEN`.
- README: "Install from stock via web GUI" section (web-flash is the primary
  install path now; UART/TFTP demoted to recovery).
- sha256 (sysupgrade): see the release's `SHA256SUMS` (CI-built).

## v1.1 — 2026-05-31 (tag `re700x-v1.1`)

Adds a **web-UI-flashable factory image** — install OpenWrt on a stock RE700X
straight from the TP-Link "Firmware Upgrade" web page (no UART, no soldering).
Firmware is the v1.0 port; this release is the install-path tooling.

- sha256 (sysupgrade): `41d5366da07ef2f1a9a6019b247ef936e8bd68ae488b52687d5ebb35f9e1ad0c`
- New tool `re700x-factory-pack.py` (+ bundled `re700x-fwdata/`) wraps the rootfs
  UBI into the stock `nvrammanager` upload format (TP-Link safeloader + the
  reverse-engineered `FwUpTbl` partition table). Build it with:
  ```
  ./re700x-factory-pack.py \
     --os bin/targets/qualcommax/ipq50xx/openwrt-qualcommax-ipq50xx-tplink_re700x-squashfs-factory.ubi \
     --bump-version "9.9.9 Build 20991231 Rel. 99999" -o re700x-factory.bin
  ```
- Format fully reverse-engineered from the stock `nvrammanager`; see
  `RE700X-FACTORY-IMAGE-PROBLEM.md`.
- Proven end-to-end on real hardware: `nvrammanager -c`/`-u` **and** the stock
  web GUI flash the rootfs into the inactive dual-boot slot and reboot into
  OpenWrt 6.12.91.

## v1.0 — 2026-05-31 (commit 20fd56b47a)

First fully working image: all hardware up.

- sha256 (sysupgrade): `a3873d326429e6bd094efeb99d1cfc80f56df3a03a8b8c7396a31a0082ab5edf`
- **5G Wi-Fi 6 (QCN6122) now works** — the last open item:
  - `q6v5_wcss` boot-args set to the stock values: UPD2 on PCIE1 + reset
    GPIO 27 (0x1b). This is what lets the QCN6122 userpd finish init instead
    of stalling in the DOG watchdog / `err_smem_ver` and crashing the Q6.
  - Added `board-tplink_re700x.qcn6122` (ath11k `board-2.bin` built from stock
    `bdwlan.b60`, board_id 0x60, variant `TP-Link-RE700X`) → fixes the ath11k
    board-data load failure (-12).
- Both radios run as APs simultaneously and stay stable.
- Carries forward everything from v0.9.

## v0.9 — 2026-05-30 (commits 7f70639f7e, f15057cc87)

First flashable image that boots OpenWrt from NAND.

- sha256 (sysupgrade, 2.4G image): `09981a4a…`
- Boots persistently from NAND (no more U-Boot/TFTP RAM-boot dance).
- Ethernet (WAN/LAN), 5 LEDs, 2 buttons.
- **2.4G Wi-Fi 6 (IPQ5018)** works.
- 5G/QCN6122 not yet working (userpd stalled in init).
- Key flash fixes: `DEVICE_DTS_CONFIG=config@mp02.1`, platform.sh
  `CI_UBIPART=rootfs`, `CONFIG_CMDLINE_FORCE` + `coherent_pool`.
