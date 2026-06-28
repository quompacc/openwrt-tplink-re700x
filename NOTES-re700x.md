# TP-Link RE700X EU v1.0 WIP Notes

Status: experimental OpenWrt bring-up only. Do not flash. Current scope is DTS,
build integration, initramfs/FIT generation, and RAM boot via U-Boot/TFTP.

Do not publish device-specific MAC addresses, serial numbers, PINs, or ART
dumps. The ART dump and stock backup files are local recovery inputs only.

## Current Status

- Branch: `tplink-re700x-wip`
- Boot method: U-Boot/TFTP RAM boot only
- Current validated local test image: `/srv/tftp/re700x-ramboot-baseline.itb`
  (`5749ed6b920be18737c406c758907c1c65613fdd8b6509090b1c200154750591`)
- Kernel starts and reaches userspace on initramfs.
- SPI-NAND is detected and SMEM/MIBIB partitions are exposed correctly.
- `factory_data` mounts read-only as UBIFS and provides `default-mac`.
- Ethernet on the external port works through `lan` at 1000 Mbps full duplex.
- `br-lan` and `lan` use the 6-byte `default-mac` from `factory_data`.
- Default network config treats the single external port as DHCP client LAN.
- IPQ5018 Wi-Fi is enabled. Calibration is extracted from `0:art`;
  device-specific board-2 files are included from the stock RE700X EU v1.0
  rootfs boarddata. QCN6122 5G now works too (see "5G / QCN6122 WORKS" below).
- No factory or sysupgrade image support is considered ready.

## Hardware

- Device: TP-Link RE700X
- Hardware: EU v1.0
- SoC: Qualcomm IPQ5018 / IPQ0509
- RAM: 256 MiB
- Flash: 128 MiB SPI-NAND, GigaDevice F50D1G41LB
- Stock FIT default configuration: `config@mp03.3-c2`
- Stock FIT kernel: `kernel@1`
- Stock FIT FDT: `fdt@mp03.3-c2`
- Stock FIT load address used from U-Boot: `0x44000000`
- Generated OpenWrt FIT kernel load/entry: `0x41000000` (qualcommax default)

## UART and U-Boot

- UART settings: 115200 8N1
- UART SoC pins from stock DTB: GPIO20/GPIO21
- U-Boot: 2016.01
- Break string: `tpl`
- Prompt: `IPQ5018#`
- TFTP works through U-Boot `eth1`
- U-Boot reports `eth1`/MAC1 PHY ID `0x001cc916`, matching Realtek RTL8211F.
- Use `setenv` only for RAM-boot tests. Do not `saveenv` as part of bring-up.

## GPIOs

Buttons:

- Reset: GPIO19, active low, confirmed by GPIO level diff and hotplug event
- WPS: GPIO20, active low, confirmed by GPIO level diff and hotplug event

The stock DTB describes buttons with `gpio-keys-polled` and
`poll-interval = <100>`, but its listed GPIOs did not match runtime behavior on
this unit. The current OpenWrt DTS uses `gpio-keys-polled` with the runtime
confirmed GPIO19/GPIO20 mapping.

Stock DTB caveat: the `gpio-keys-polled` node itself has no `pinctrl-0`
reference in the decompiled DTB. A separate `button_pins` node exists, but it
contains only a child named `wps_button` on GPIO38 and appears unreferenced by
the keys node. GPIO31 appears as the WPS `gpios` entry only. This is a real
stock-DTB inconsistency and should be treated as evidence, not resolved by
guessing random GPIOs.

LEDs (all five confirmed empirically by GPIO output sweep, all active-high):

- Power:    GPIO31 (global 543)
- WPS red:  GPIO32 (global 544)
- WPS blue: GPIO22 (global 534)
- 2G WLAN:  GPIO33 (global 545)
- 5G WLAN:  GPIO34 (global 546)

The stock DTB LED GPIOs (Power 38, WPS red 18, blue 22, 2G 39, 5G 13) were all
wrong except blue 22 -- just like the stock button GPIOs. The real LEDs are the
consecutive group 31-34 plus blue 22. The current DTS enables all five, with
led_pins = gpio22,31,32,33,34. The stock DTB also wrongly claimed gpio33 as the
RTL8211F PHY reset; gpio33 is the 2.4G LED, so the rtl8211f node has no
reset-gpios and Ethernet is stable without a Linux-side reset.

Caveat for future probing: the serial console is on gpio28/29 (NOT gpio31/32).
Driving gpio28 (global 540) or gpio29 (global 541) as output freezes the live
connection; gpio4-9 are NAND. These are excluded from the led-sweep tool.

## Flash Layout from SMEM/MIBIB

Partitions are expected from Qualcomm SMEM/MIBIB. Do not hard-code fixed DTS
partitions for this WIP port.

```text
0:SBL1           0x00000000 0x00080000
0:MIBIB          0x00080000 0x00080000
0:BOOTCONFIG     0x00100000 0x00040000
0:BOOTCONFIG1    0x00140000 0x00040000
0:QSEE           0x00180000 0x00100000
0:DEVCFG         0x00280000 0x00040000
0:CDT            0x002c0000 0x00040000
0:APPSBLENV      0x00300000 0x00080000
0:APPSBL         0x00380000 0x00140000
0:ART            0x004c0000 0x00100000
0:TRAINING       0x005c0000 0x00080000
rootfs           0x00640000 0x02a00000
rootfs_1         0x03040000 0x02a00000
0:ETHPHYFW       0x05a40000 0x00080000
factory_data     0x05ac0000 0x00900000
runtime_data     0x063c0000 0x01100000
```

## RAM Boot Test Only

Use U-Boot/TFTP only. Do not write flash.

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 openwrt-qualcommax-ipq50xx-tplink_re700x-initramfs-uImage.itb
bootm 0x44000000
```

Current validated baseline test copy:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-ipq5018-baseline.itb
bootm 0x44000000
```

Historical RAM test copies kept for traceability:

Factory data / MAC mount test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-factorydata.itb
bootm 0x44000000
```

Initial Wi-Fi test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-wifi-test1.itb
bootm 0x44000000
```

Board-2 Wi-Fi test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-board2-test1.itb
bootm 0x44000000
```

Isolated IPQ5018 Wi-Fi test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-ipq5018-only-mm1.itb
bootm 0x44000000
```

Dual-radio memory-mode-1 test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-both-mm1.itb
bootm 0x44000000
```

Stock-memory dual-radio test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-stockmem-mm1.itb
bootm 0x44000000
```

QCN6122-only memory-mode-1 test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-qcn-only-mm1.itb
bootm 0x44000000
```

QCN6122-only memory-mode-2 test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-qcn-only-mm2.itb
bootm 0x44000000
```

QCN6122 PD3/default-mapping test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-qcn-pd3-default.itb
bootm 0x44000000
```

Button polling diagnostic test:

```text
setenv serverip 192.168.1.248
setenv ipaddr 192.168.1.50
tftpboot 0x44000000 re700x-keys-polled.itb
bootm 0x44000000
```

Post-boot network sanity checks:

```sh
mount | grep factory_data
ls -l /tmp/factory_data
ip addr show dev br-lan
ip link show dev lan
ping -c 3 192.168.1.1
```

MAC check without printing the real address:

```sh
factory_hex=$(hexdump -v -e '6/1 "%02x"' /tmp/factory_data/default-mac)
lan_hex=$(cat /sys/class/net/lan/address | tr -d ':')
br_hex=$(cat /sys/class/net/br-lan/address | tr -d ':')

[ "$lan_hex" = "$factory_hex" ] && echo "lan equals default-mac" || echo "lan differs from default-mac"
[ "$br_hex" = "$factory_hex" ] && echo "br-lan equals default-mac" || echo "br-lan differs from default-mac"
```

## Bring-Up Log

- Initial DTS/build integration created `tplink,re700x` for
  `qualcommax/ipq50xx` and produced a bootable initramfs FIT using
  `config@mp03.3-c2`.
- First RAM boot reached userspace. The early U-Boot warnings about missing
  `/soc/qpic-nand@79b0000` and PCI did not block Linux boot.
- SMEM partition parsing works. `/proc/mtd` exposes all 16 expected
  partitions from MIBIB/SMEM.
- Initial Ethernet assumptions were corrected: the external port is not
  QCA8081. U-Boot PHY ID `0x001cc916` and runtime tests match Realtek
  RTL8211F on MDIO1 address 6.
- `re700x-rtl8211f.itb` validated external `lan` link at 1000 Mbps full duplex
  and successful ping to the TFTP host with a static IP.
- `re700x-lan-dhcp2.itb` validated default DHCP client config on `br-lan` with
  `lan` as its single bridge port.
- `re700x-macfix.itb` confirmed that MAC setup still failed while
  `factory_data` was not mounted.
- `re700x-factorydata.itb` validated read-only mount of
  `ubi14:ubi_factory_data` at `/tmp/factory_data`; `default-mac` exists as a
  6-byte file; `lan` and `br-lan` both match `default-mac`; DHCP lease and
  ping to the upstream router work.
- `re700x-wifi-test1.itb` enables the internal IPQ5018 radio and the external
  QCN6122 userpd2 radio for RAM-only testing. Caldata extraction uses `0:art`
  offset `0x1000` for IPQ5018 and `0x26800` for QCN6122, with MAC addresses
  derived from `/tmp/factory_data/default-mac`. No device-specific board-2/BDF
  package exists yet, so ath11k may still stop at firmware/board data lookup.
- Stock `rootfs` was copied read-only from `/dev/mtd11ro` and extracted
  offline. The UBI image contains the stock FIT in volume 0 and the SquashFS
  rootfs in volume 2.
- Stock TP-Link boarddata selection chooses `boarddata_hw1.0/EU` for the EU
  hardware. The RAM-only OpenWrt test now packages these stock boarddata files
  as ath11k board-2 containers:
  `boarddata_hw1.0/EU/bdwlan.b24` for IPQ5018 and
  `boarddata_hw1.0/EU/bdwlan.b60` for QCN6122.
- `re700x-board2-test1.itb` includes `ipq-wifi-tplink_re700x`, installing
  `board-2.bin` for both `ath11k/IPQ5018/hw1.0` and
  `ath11k/QCN6122/hw1.0`. The FIT hash is
  `b4d2df528a8a96e4dfc77212fc454f1c80f09bc54590ced6e3be6c7c910e3e5c`.
- `re700x-board2-test1.itb` validates that both board-2 files are present and
  the previous boarddata lookup error is gone. IPQ5018 caldata is generated,
  but QCN6122 caldata is not generated before ath11k times out. The current
  blocking error is `failed to wait wlan mode request (mode 0): -110` on
  `c000000.wifi`.
- `re700x-ipq5018-only-mm1.itb` is an isolation test: QCN6122 is disabled and
  the internal IPQ5018 radio uses firmware memory mode 1. The FIT hash is
  `ac9857a717df5a6ad6dbd6564aa6b3712393a3359ec9ad59513b442baa7b26d6`.
- `re700x-ipq5018-only-mm1.itb` validates that the internal IPQ5018 radio
  starts with firmware memory mode 1. `wifi status` reports `radio0` as up;
  no WLAN interface is configured yet, so `iw dev` remains empty.
- `re700x-both-mm1.itb` enables both IPQ5018 and QCN6122 with firmware memory
  mode 1. The FIT hash is
  `917492c4bb0e18d302bd4bc8e4590c0df63437a85db37f5d3d224757ee4050b8`.
- `re700x-both-mm1.itb` still times out on `c000000.wifi` when QCN6122 is
  enabled, even though IPQ5018 alone works with memory mode 1.
- Stock DTB uses `qcom,userpd-subsys-name = "q6v5_wcss_userpd1"` for the
  internal IPQ5018 radio and places QCN6122 BDF/M3 regions at `0x4d200000` and
  `0x4de00000`. `re700x-stockmem-mm1.itb` tests those stock-derived addresses
  while keeping both radios on firmware memory mode 1. The FIT hash is
  `4f36a34892656492038b561cb393859b75516cd9f2a19bf4ed489b339781bac4`.
- `re700x-stockmem-mm1.itb` still times out on `c000000.wifi`, so the
  stock-derived QCN BDF/M3 addresses alone do not solve the dual-radio start
  issue.
- `re700x-qcn-only-mm1.itb` disables the internal IPQ5018 radio and keeps
  QCN6122 on PD2 with memory mode 1 and stock-derived memory hints. The FIT
  hash is `60d34394c6e22fa799211f788d780076cc5302676898c100ce6b00c88584b8c2`.
- Runtime test with `re700x-qcn-only-mm1.itb`: QCN6122 probes on PD2 and Q6
  starts, but QCN6122 caldata is not generated and Q6 later reports a fatal
  `err_smem_ver.2.1` crash from process `wlan1`. The remoteproc recovery then
  times out. `iw dev` remains empty and `wifi status` is empty.
- `re700x-qcn-only-mm2.itb` keeps the same QCN6122-only setup but changes only
  QCN6122 firmware memory mode from 1 to 2, matching the stock DTB's wireless
  memory-mode hint more closely. The FIT hash is
  `4357319d2dae990d192f5cbeb51057a7c0f932353f59182d30d0aa2f52c7969d`.
- Runtime test with `re700x-qcn-only-mm2.itb`: QCN6122 still crashes Q6 in the
  same way as memory mode 1. PD2 starts and reports `FW memory mode: 2`, then
  Q6 reports fatal `err_smem_ver.2.1` from process `wlan1`; remoteproc recovery
  times out. QCN6122 caldata is still not generated.
- `re700x-qcn-pd3-default.itb` is a diagnostic deviation from stock: IPQ5018
  and QCN PD2 are disabled, QCN is tested through `wifi2`/PD3 with the default
  OpenWrt PCIe0/PD3 mapping, `q6_region` is extended like existing triple-radio
  IPQ5018 devices, and the `b00b040` QCN6122 caldata hotplug case is added for
  `tplink,re700x`. The FIT hash is
  `ac6df20f57cfefebcc6250b5b4ea557f6992492d5922e3c80df69f6ecd167b9c`.
- Runtime test with `re700x-qcn-pd3-default.itb`: PD3 also fails with the same
  Q6 watchdog pattern. The log shows `b00b040.wifi`, userpd 3, and
  `FW memory mode: 1`; then Q6 reports fatal `err_smem_ver.2.1` from process
  `wlan2`/`TIMER_CLIENT_3`, followed by remoteproc recovery timeout. This rules
  out a simple PD2-vs-PD3 mapping mistake as the primary QCN6122 blocker.
- Current baseline after the QCN isolation tests is IPQ5018-only Wi-Fi: the
  internal IPQ5018 radio is enabled with firmware memory mode 1, while QCN6122
  remains disabled. This preserves the known-good RAM-boot and Ethernet state
  and avoids repeated Q6 crashes during normal bring-up tests.
- `re700x-ipq5018-baseline.itb` is the restored IPQ5018-only RAM-boot baseline
  after QCN isolation testing. The FIT hash is
  `1f8d9d3d9e6f7396518eb69ccdc5c40f2eb649b4b51d0cab88ef68ddbcf53d70`.
- Runtime test with `re700x-ipq5018-baseline.itb`: Ethernet/DHCP works on
  `br-lan`, the TFTP host is reachable, IPQ5018 `board-2.bin` and
  `cal-ahb-c000000.wifi.bin` are present, ath11k starts `c000000.wifi` on
  userpd 1 with firmware memory mode 1, and `wifi status` reports `radio0`
  up. No Q6 fatal error is observed in this baseline.
- Extended runtime validation with `re700x-ipq5018-baseline.itb`: `/proc/mtd`
  exposes the expected 16 SMEM partitions, `/proc/device-tree/model` reports
  `TP-Link RE700X`, compatible strings are `tplink,re700x` and `qcom,ipq5018`,
  `factory_data` mounts read-only as UBIFS, and the factory default MAC is
  applied to both `br-lan` and `lan`. LEDs enumerate as `blue:wps`,
  `green:power`, `green:wlan2g`, `green:wlan5g`, and `red:wps`. `netifd`
  obtains a DHCP lease on `lan` through `br-lan`; the only observed Wi-Fi
  userspace warning is `command failed: Not supported (-95)` during antenna
  configuration, after which `radio0` remains up.
- LED GPIO runtime tests are incomplete. A temporary diagnostic image,
  `re700x-leddiag-freegpio.itb`, disabled the `gpio-leds` node only to free
  the lines for RAM-only probing. GPIO22/global 534 was confirmed as a visible
  blue LED, second from the top, active-high (`1` on, `0` off), likely WPS
  blue. GPIO29/global 541 must not be tested further: driving it as GPIO caused
  the live shell/network connection to drop. GPIO46 could be switched as normal
  GPIO but did not affect visible LEDs. Other tested free GPIO candidates did
  not visibly control Power, 2.4G, 5G, or red WPS.
- Runtime LED class tests in the normal baseline confirmed that `blue:wps`
  drives GPIO22 and the visible blue LED correctly. `green:power`/GPIO38,
  `green:wlan2g`/GPIO39, `green:wlan5g`/GPIO13, and `red:wps`/GPIO18 all
  switch electrically between low and high but caused no visible front-panel
  LED change. These four nodes are therefore disabled until the real front LED
  wiring is identified.
- RAM-boot test with `re700x-ledsafe.itb` confirms that disabling the
  unvalidated LED child nodes is effective: `/sys/class/leds` only exposes the
  confirmed `blue:wps` LED.
- Stock rootfs/static analysis: `/usr/bin/gpiod` opens `/dev/gpio` for GPIO
  ioctl access, but WPS/reset handling ultimately consumes `/var/run/btn_wps`,
  `/var/run/btn_reset`, `/tmp/button_wps_check`, and
  `/tmp/button_reset_check`. The stock kernel module
  `gpio-button-hotplug.ko` supports both `gpio-keys` and `gpio-keys-polled`.
  This points back to the DT/kernel button path rather than a separate
  userspace-only button pin map.
- Stock rootfs button path:
  `/etc/init.d/gpio` creates `/dev/gpio` and starts `/usr/bin/gpiod`;
  `/etc/hotplug.d/button/50-btn-wps` writes `/var/run/btn_wps` when the kernel
  emits WPS events; `/etc/hotplug.d/button/51-btn-reset` writes
  `/var/run/btn_reset`. In production mode WPS is handled on `released`; in
  non-production mode it is handled on `pressed`.
- Factory/test code uses `/tmp/button_wps_check`, `/tmp/button_reset_check`,
  and related files as status flags. `tddp` and
  `luci/controller/admin/button_check.lua` only inspect these files; they do
  not reveal another hardware GPIO map.
- `gpiod` also depends on runtime state files such as
  `/tmp/device_runtime.info`, `/tmp/wifi_mod_exist`, `/tmp/calcmode`, and
  `/tmp/wifi.conf`. These affect TP-Link LED/WPS state-machine behavior, but
  not the basic kernel button GPIO declaration.
- `re700x-keys-polled.itb` changes only the OpenWrt `keys` node from
  `gpio-keys` to stock-style `gpio-keys-polled` with `poll-interval = <100>`.
  The FIT hash is
  `101fa11e2c654c7ea086ec7a264bddccc4e383f71b8a9c8ecc3de2015fe600fd`.
- Runtime test with `re700x-keys-polled.itb`: the live device tree confirms
  `/proc/device-tree/keys/compatible` is `gpio-keys-polled`, but pressing WPS
  still produces no `/tmp/button-test.log` entry and `logread` only shows the
  `gpio_button_hotplug` module load. This rules out interrupt-only key
  handling as the immediate cause of the missing WPS event.
- `re700x-stock-keys-nopinctrl.itb` keeps stock-style `gpio-keys-polled` but
  removes the explicit OpenWrt `keys` pinctrl reference. This matches the stock
  keys node more closely; the separate stock `button_pins/wps_button` remains
  suspicious because it names GPIO38 while the actual WPS key node names GPIO31.
  The FIT hash is
  `6aefa5f77157821b0b58304cf74c3fd2193c6b46c038b908c3f4c0ab4ac0fd7c`.
- `re700x-wps-gpio38.itb` is a single-purpose WPS diagnostic: it keeps
  stock-style `gpio-keys-polled`, moves only the WPS key from GPIO31 to GPIO38,
  and applies `button_pins` to GPIO25/GPIO38 with pull-up. This tests whether
  the stock DTB's otherwise-unreferenced `button_pins/wps_button` was the real
  WPS input. The FIT hash is
  `9d840a9ca40c17be4050781e3f5ac6465da7619f7bf6dcf66297fc54480f5a7c`.
- Runtime test with `re700x-wps-gpio38.itb`: pressing WPS still produces no
  `/tmp/button-test.log` entry and `logread` only reports the
  `gpio_button_hotplug` module load. GPIO38 is therefore not confirmed through
  stock-style polling.
- `re700x-wps-gpio38-irq.itb` keeps WPS on GPIO38 but changes the keys node
  from `gpio-keys-polled` to `gpio-keys`, matching the WN-DAX3000GR style for
  GPIO38/WPS. This isolates polling vs interrupt-style key handling. The FIT
  hash is
  `e86b1eab67381b99f1ab42ed53810e9eaf4d3f1416ccfa6fbe6e1eed4c927b84`.
- Runtime test with `re700x-wps-gpio38-irq.itb`: pressing WPS still produces
  no `/tmp/button-test.log` entry and `logread` only reports the
  `gpio_button_hotplug` module load. GPIO38 is therefore not confirmed as WPS
  through either `gpio-keys-polled` or `gpio-keys`.
- Direct runtime level check with `re700x-wps-gpio38-irq.itb`: while pressing
  WPS, GPIO38 stays `in high func0 8mA pull up`. GPIO38 is therefore also
  electrically not observed as the WPS button line in this setup. GPIO31 is not
  useful in this particular image because it is no longer claimed by the key
  node and shows as `out high`.
- Direct runtime level check of stock reset candidate GPIO25: no visible level
  change was observed while pressing reset. This makes the stock button GPIO
  mapping suspect on this hardware/boot path, or indicates that the buttons are
  read through a path not visible as ordinary TLMM GPIO input state.

## Current DTS Bring-Up Assumptions

- SPI-NAND is described through QPIC with `qcom,smem-part`.
- Factory/sysupgrade images are intentionally not defined.
- Wi-Fi is enabled only in RAM-test images for calibration/BDF validation.
- Ethernet is based on the stock DTB's two NSS-DP/MDIO links, not the
  WN-DAX3000GR QCA8337 switch topology.
- External Ethernet on `lan` uses the Realtek RTL8211F at MDIO1 address 6.
- RAM-boot test with `re700x-rtl8211f.itb` links at 1000 Mbps full duplex and
  can ping the TFTP host with a static address on `lan`.
- Board default network config uses `lan` as a DHCP client, matching the
  single-port repeater/AP use case.
- RAM-boot test with `re700x-lan-dhcp2.itb` creates `br-lan`, brings `lan` up
  through netifd, and obtains an IPv4 DHCP lease from the upstream router.
- `factory_data` is mounted read-only during preinit for TP-Link RE700X so
  board scripts can read `/tmp/factory_data/default-mac`.
- RAM-boot test with `re700x-factorydata.itb` mounts `factory_data` as
  `ubi14:ubi_factory_data`, reads the 6-byte `default-mac`, assigns it to
  both `lan` and `br-lan`, and obtains a DHCP lease from the upstream router.
- Runtime validation: `/proc/mtd` exposes all 16 SMEM partitions, device-tree
  compatible is `tplink,re700x`, and the only visually confirmed LED is the
  blue WPS-like LED on GPIO22. The current DTS exposes only this LED.
- Buttons are currently polled GPIO keys: reset on GPIO19 active-low and WPS on
  GPIO20 active-low. Both are confirmed by before/after GPIO level diffs and
  runtime hotplug events.
- Stock's keys node does not reference pinctrl, and its separate unreferenced
  `button_pins` child names GPIO38 as `wps_button`.
- Runtime testing did not confirm WPS events on GPIO31 or GPIO38 with the
  normal OpenWrt key paths. GPIO20 active-low is confirmed as WPS.
- Do not continue guessing single GPIO numbers for WPS. First run a full GPIO
  before/after diff while holding each physical button, then map only lines that
  actually change.
- Full GPIO before/after diff while holding WPS found GPIO20 changing from
  `in high func0 8mA pull down` to `in low func0 8mA pull down`. This is the
  first direct electrical match for the WPS button; test image
  `re700x-wps-gpio20.itb` maps WPS to GPIO20 active-low.
  The FIT hash is
  `d284162dbe8f07f54bb21479d5878b66407d3cc9d83046c7f30472de4670490f`.
- Runtime test with `re700x-wps-gpio20.itb`: pressing WPS creates
  `/tmp/button-test.log` with `ACTION=pressed BUTTON=wps SEEN=0`.
- Full GPIO before/after diff while holding reset found GPIO19 changing from
  `in high func3 8mA pull down` to `in low func3 8mA pull down`. GPIO36 also
  changed, but it is MDIO/MDC and treated as Ethernet-side noise. Test image
  `re700x-buttons-gpio19-20.itb` maps reset to GPIO19 active-low and keeps WPS
  on confirmed GPIO20 active-low.
  The FIT hash is
  `5749ed6b920be18737c406c758907c1c65613fdd8b6509090b1c200154750591`.
- Runtime test with `re700x-buttons-gpio19-20.itb`: briefly pressing reset
  creates `/tmp/button-test.log` with `ACTION=pressed BUTTON=reset SEEN=0`.
  Reset is confirmed as GPIO19 active-low.
- Stock rootfs additionally loads `button-hotplug.ko` and runs `/usr/bin/gpiod`
  against `/dev/gpio`. `gpiod` contains explicit button-check paths for reset,
  WPS, LED switch, and power, and writes `/tmp/button_wps_check` /
  `/tmp/button_reset_check`; this may be separate from the normal DT
  `gpio-keys` hotplug path.
- Stock DTB indicates two active radios: internal IPQ5018 on userpd1 and
  QCN6122 on userpd2; a third radio is disabled. The current OpenWrt DTS
  mirrors this as `&wifi` and `&wifi1` only.
- `ipq-wifi-tplink_re700x` uses board name
  `bus=ahb,qmi-chip-id=0,qmi-board-id=255,variant=TP-Link-RE700X` for both
  generated board-2 containers.

## Open Items

- QCN6122 remains blocked: PD2 mode 1, PD2 mode 2, and PD3 mode 1 all crash Q6
  before QCN caldata is requested.
- QCN6122 deep-dive (2026-05-30, still blocked). Crash is err_smem_ver.2.1 /
  "USER-PD DOG detects stalled initialization" (process wlan1), ~40s after the
  userpd spawns and before any QMI/caldata exchange -> board-2 and caldata are
  not the trigger. Ruled out (all identical ~52s DOG on PD2): custom board-2
  present vs removed; bdf/m3 0x4d200000/0x4de00000 vs canonical 0x4d100000/
  0x4df00000; boot-args PCIE0/GPIO15 vs PCIE1/GPIO18 (identical -> reset GPIO is
  not the lever, and both stock PCIe controllers are disabled so QCN6122 is
  AHB-integrated). Replicating gl-b3000 (wifi1 on UPD3, no boot-args) was worse:
  IPQ5018 then fails QMI (-110) with no phy at all; on UPD2 the 2.4G radio still
  works. Only tplink_re700x shipped a custom ipq-wifi board file (now removed);
  upstream provides no board-2, devices use caldata (QCN at 0:art 0x26800). Next
  real step: capture the QCN6122 init/reset/clock sequence under stock firmware,
  or wait for upstream 5GHz support. Do not keep guessing DTS values.
- Continue from the validated RAM-boot baseline image
  `re700x-ramboot-baseline.itb`.
- Continue LED work cautiously: keep GPIO22 as confirmed, do not test GPIO29
  again, and keep the other stock LED GPIOs disabled until the real front panel
  wiring is identified.
- Decide later whether this target needs factory/sysupgrade image generation.
- Keep all tests RAM-boot-only until recovery and install paths are fully
  understood.

## Flash / Install Path Analysis (2026-05-30, read-only from full backup)

A full stock NAND backup was pulled via the RAM-booted OpenWrt (nc stream of
/dev/mtd0ro..15ro) to /home/eduard/tftp/re700x-stock-backup/ (full-nand.bin +
per-partition mtdNN-*.bin + SHA256SUMS). Verified: 122421248 bytes total,
factory_data has a valid UBI# header, 0:art has real caldata at 0x1000
(IPQ5018) and 0x26800 (QCN6122). This is the recovery safety net.

Stock boot flow (U-Boot 2016.01, bootcmd is compiled-in; appsblenv only holds
baudrate + has_default_mac):
- Active A/B slot is chosen from `0:bootconfig` (mtd2) / `0:bootconfig1` (mtd3).
  Format: magic a0a1a2a3, version 1, 8 entries, footer b0b1b2b3. Entries:
  0:QSEE, 0:DEVCFG, 0:CDT, 0:APPSBL, 0:HLOS, rootfs, 0:WIFIFW, 0:BTFW, each with
  a primaryboot flag. All flags 0 => boot the PRIMARY slot (rootfs, not
  rootfs_1).
- U-Boot attaches UBI on the active rootfs partition, reads the static UBI
  volume "kernel" (a FIT) to 0x44000000, and bootm's it using the FIT's DEFAULT
  config. The same U-Boot also boots our ARM64 FIT (every RAM test:
  "Jumping to AARCH64 kernel"), so the format is compatible.
- Stock rootfs UBI has volumes "kernel" (FIT, many fdt@mpXX configs, default
  config@mp02.1) and "ubi_rootfs" (squashfs). Linux cmdline used
  root=mtd:ubi_rootfs.

OpenWrt image recipe (model after cmcc_mr3000d-ci, the IPQ5018+QCN6122 sibling):
- $(call Device/FitImageLzma) + $(call Device/UbiFit) produces a UBI whose
  kernel volume is named "kernel" (scripts/ubinize-image.sh line 78) -> exactly
  what the stock U-Boot loads. rootfs volume is "rootfs"(+"rootfs_data"); U-Boot
  ignores it, OpenWrt's own kernel uses it. Only the "kernel" volume name must
  match, and it does.
- Needed device knobs: DEVICE_DTS_CONFIG = config@mp03.3-c2 (RE700X FIT default,
  already boots), SOC ipq5018, BLOCKSIZE 128k, PAGESIZE 2048, NAND_SIZE 128m,
  IMAGE_SIZE <= rootfs size 0x2a00000 (43008k). The current RE700X device entry
  only builds an initramfs; add Device/UbiFit + sizes to get sysupgrade.

Install path (no TP-Link factory image needed): keep RAM-booting the OpenWrt
initramfs as today, then run sysupgrade with the UbiFit sysupgrade.bin -> it
ubiformats the rootfs partition and writes the kernel+rootfs UBI to the PRIMARY
slot; leave bootconfig at 0. Reboot -> U-Boot boots the primary rootfs ->
"kernel" FIT -> OpenWrt. Recovery on failure: rewrite stock partitions from the
backup (esp. 0:art + factory_data) via the RAM OpenWrt / U-Boot TFTP.

Open items before flashing: (1) add the UbiFit/sysupgrade device recipe and
build it; (2) decide IMAGE_SIZE vs the 42 MiB rootfs slot; (3) dry-run the
recovery (restore stock rootfs from backup) once before the first real flash.

## Recovery write path VALIDATED (2026-05-30, on-device dry test)

Validated that a backed-up partition image can be written back to NAND
bit-identically, using the alternate (non-booted) slot rootfs_1 (mtd12) with
its own content (state-preserving, primary rootfs untouched):
1. dd if=/dev/mtd12ro -> sha256 == backup (94d904...) [read path + backup faithful]
2. mtd write /tmp/rootfs_1.bin rootfs_1  [no errors]
3. dd if=/dev/mtd12ro | sha256 == 94d904... [round-trip bit-identical]
Conclusion: `mtd write <backup-image> <partition-name>` faithfully restores a
NAND partition. Recovery is proven; flashing is acceptably de-risked. Host->device
file delivery over nc is unreliable in this sandbox (listener killed), but that is
secondary - in real recovery the backup can be delivered via U-Boot TFTP or nc, and
the critical NAND write step is confirmed working from a RAM-booted OpenWrt.

## FLASHED + booting OpenWrt from NAND (2026-05-30)

The port now installs and boots from flash. Three fixes were needed beyond the
RAM-boot baseline:

1. DEVICE_DTS_CONFIG = config@mp02.1 (not config@mp03.3-c2). The stock TP-Link
   U-Boot reads the "kernel" UBI volume FIT and selects the config *by name*
   "config@mp02.1"; a different name -> "Config not available" -> U-Boot falls
   back to the stock rootfs slot.
2. platform.sh tplink,re700x case: CI_UBIPART=rootfs (the device's UBI part is
   "rootfs", not the default "firmware") + remove_oem_ubi_volume ubi_rootfs.
3. CONFIG_CMDLINE_FORCE: the stock U-Boot force-overrides the FIT bootargs with
   "ubi.mtd=rootfs root=mtd:ubi_rootfs", which mainline cannot satisfy (our UBI
   rootfs volume is "rootfs", mounted as /dev/ubiblock0_1 via preinit, not via
   a kernel root=mtd:). Forcing the cmdline makes the kernel ignore U-Boot's and
   mount /dev/ubiblock0_1. NOTE: CONFIG_CMDLINE_FORCE is target-global (ok for a
   single-device build, not upstream-clean).

Working from flash: NAND boot, ethernet, 5 LEDs, buttons.

## 2.4G Wi-Fi WORKS (IPQ5018) - the QCN "block" was partly coherent_pool

The forced cmdline initially dropped the DTS chosen "coherent_pool=2M", which
caused ath11k remoteproc firmware load to fail with "DMA pool exhausted for
pd-1" (qcom_mdt_load dma_alloc, ~264 KiB seg) -> -12, no phy. Adding
coherent_pool=4M to the forced cmdline fixed it: the IPQ5018 2.4G radio comes
fully up (phy0, 802.11ax HE20, WPA-PSK AP verified, 2.4G LED netdev trigger
works). The earlier "ath11k blocked" conclusion was wrong for 2.4G - it was the
DMA pool, not a fundamental block.

## 5G / QCN6122 still BLOCKED - re-test with coherent_pool=8M (2026-05-30)

Re-enabled &wifi1 with coherent_pool=8M to see if the 5G block was also just the
pool. Result: pd-2 now boots (DMA exhaustion gone), but the QCN userpd still
stalls in init -> "err_smem_ver.2.1 ... USER-PD DOG detects stalled
initialization" ~40s in. Worse, this crash takes down the cd00000 Q6 root PD,
which makes the (previously working) 2.4G radio fail QMI with -110, and
"Coldboot Calibration timed out". So the QCN6122 block is NOT the DMA pool; it
needs the stock init/reset sequence. Left &wifi1 status=disabled; 2.4G stays up.

## 5G / QCN6122 WORKS (2026-05-31) - solved by reading the stock firmware

Stopped guessing and extracted the stock config to recover the two
board-specific values that cannot be guessed. Both came from the stock NAND
backup in `/home/eduard/tftp/re700x-stock-backup/`.

### Extracting the stock DTB
The stock `mtd11-rootfs.bin` is a UBI image with two volumes: `kernel` (static)
and `ubi_rootfs`. The `kernel` volume is itself a FIT image; its `config@mp02.1`
(the config the stock U-Boot selects for this board) points to `fdt@mp02.1`.

    ubireader_extract_images -o out mtd11-rootfs.bin     # -> vol-kernel(.itb), vol-ubi_rootfs
    dumpimage -T flat_dt -p 22 -o stock.dtb out/.../vol-kernel.ubifs   # image 22 = fdt@mp02.1
    dtc -I dtb -O dts -o stock-mp02.1.dts stock.dtb

`ubi_rootfs` is squashfs (magic `hsqs`), not ubifs - `unsquashfs` it to get the
stock `/lib/firmware/boarddata`. Extracted DTS saved as
`re700x-stock-backup/stock-mp02.1.dts`.

### Fix 1: q6v5_wcss boot-args (the real blocker)
The QCN6122 on IPQ5018 is NOT a PCIe card with its own reset/regulator/clock
node - it boots as a protection domain (userpd2) on the shared Q6/WCSS. The
firmware does the radio reset itself, using the GPIO named in the PIL boot-args.

boot-args v1 format (per external radio, decoded from
`patches-6.12/0815-...v1-bootargs.patch`):

    <PCIE-index, length, userPD-id, reset-gpio, reserved, reserved>

Firmware defaults: UPD2 = PCIE1/gpio0x12(18), UPD3 = PCIE0/gpio0x0f(15).
Stock RE700X passes `<0x1 4 3 15 0 0  0x2 4 2 0x1b 0 0>` - i.e. for UPD2 (our
QCN6122) it overrides the reset GPIO to **0x1b = 27** on PCIE1. Earlier attempts
only tried gpio15/PCIE0 and gpio18/PCIE1; gpio27 was never tried and was the
entire blocker. With the stock boot-args, pd-2 boots through, QMI completes, no
more `err_smem_ver`/DOG watchdog, and the Q6 root PD + 2.4G radio stay up.

### Fix 2: QCN6122 board-2.bin (ath11k board file)
Once the PD booted, ath11k failed with `failed to load board data file: -12`
because there was no `ath11k/QCN6122/hw1.0/board-2.bin`. Built
`package/firmware/ipq-wifi/src/board-tplink_re700x.qcn6122` with ath11k-bdencoder
from the stock `boarddata/boarddata_hw1.0/EU/bdwlan.b60` (board_id 0x60), using
the same single variant key as the working 2.4G file:
`bus=ahb,qmi-chip-id=0,qmi-board-id=255,variant=TP-Link-RE700X`. (The existing
`.ipq5018` file is byte-identical to stock `bdwlan.b24`, board_id 0x24 - same
convention.) The ipq-wifi Makefile already maps `.qcn6122` ->
`ath11k/QCN6122/hw1.0/board-2.bin`.

### Bringing up the APs
`wifi config` generates both radios but leaves each `wifi-iface` at
`disabled '1'`. Set the IFACES (not just the devices) to `disabled '0'`, set
`country`, `wifi up`. Both APs come up: phy0 2.4G ch1 HE20, phy1 5G ch36 HE80,
simultaneous and stable. The `command failed: Not supported (-95)` antenna-mask
lines in logread are harmless (ath11k doesn't support set-antenna).

Result: the RE700X port is feature-complete - NAND boot, ethernet, LEDs,
buttons, 2.4G and 5G Wi-Fi 6 all working.

## Dual-boot brick FIXED (2026-06-28)

The web-GUI factory flash bricked a second unit. Cause (confirmed v1.5): the
kernel cmdline was force-set in `target/linux/qualcommax/config-6.12`
(`CONFIG_CMDLINE_FORCE=y` + `ubi.mtd=rootfs`). The stock flasher writes OpenWrt
into the inactive dual-boot slot `rootfs_1` (mtd12) and sets U-Boot
`tp_boot_idx=1`; U-Boot then loads the slot-1 kernel, but the forced cmdline
still made the kernel attach slot 0 (`rootfs`/mtd11) -> wrong/old root -> no
boot. No button/TFTP recovery on this bootloader; only UART.

### Diagnosis (safe, slot-1-only, slot-0 kept as fallback)
Built a diagnostic with `CONFIG_CMDLINE_FROM_BOOTLOADER=y` (so the kernel uses
U-Boot's cmdline, revealing it), wrote it to slot 1 only
(`ubiformat /dev/mtd12 -f diag.ubi -y`), set `tp_boot_idx=1` at the U-Boot
prompt, booted. The kernel printed:

    Kernel command line: ubi.mtd=rootfs_1 root=mtd:ubi_rootfs rootfstype=squashfs rootwait

i.e. the stock U-Boot ALREADY passes a slot-correct `ubi.mtd=rootfs_1`. The
kernel even attached mtd12 and created `ubiblock0_1`; the ONLY failure was
`root=mtd:ubi_rootfs` (mainline can't mount a UBI volume by that syntax) ->
panic/bootloop. Recovered with `setenv tp_boot_idx 0; saveenv`.

### The fix (idiomatic qualcommax, no kernel patch)
The target already carries `patches-6.12/0911-arm64-cmdline-replacement.patch`,
which adds `bootargs-append` / `bootargs-find/replace` to `/chosen` in
`early_init_dt_scan_chosen` (other ipq5018 boards - ax830, mx2000, ... - use
`bootargs-append`). arm64's Kconfig has NO `CMDLINE_EXTEND` (only FORCE /
FROM_BOOTLOADER), so the FORCE->EXTEND idea silently falls back to FORCE - dead
end. Instead:
1. Removed the `CONFIG_CMDLINE`/`CMDLINE_FORCE` lines from `config-6.12` (revert
   to generic empty cmdline; this hack was added in 7f70639f7e).
2. DTS `/chosen`: `bootargs-append = " root=/dev/ubiblock0_1 coherent_pool=4M"`.

The kernel inherits U-Boot's slot-correct `ubi.mtd` and the appended `root=`
wins over `root=mtd:ubi_rootfs` (Linux uses the last `root=`); `coherent_pool=4M`
keeps the ath11k 2.4 GHz DMA happy.

### Validated on hardware
Wrote the fixed image to BOTH slots and booted each:
- Slot 1 (`tp_boot_idx=1`): `ubi.mtd=rootfs_1 ... root=/dev/ubiblock0_1 coherent_pool=4M`,
  `ubi0: attached mtd12 (name "rootfs_1")`, clean squashfs root mount, both radios.
- Slot 0 (`tp_boot_idx=0`): `ubi.mtd=rootfs ... root=/dev/ubiblock0_1 coherent_pool=4M`,
  `ubi0: attached mtd11 (name "rootfs")`, clean mount, both radios.
So OpenWrt boots from whichever slot the flasher targets -> brick dead.

### Still pending
The *literal* stock->web-GUI install was not re-run: the official firmware
(`re700xv1_eu-...ver1-3-15...`) is AES-encrypted "Cloud" type (header
`fw-type:Cloud`, high-entropy payload, no UBI#/squashfs), and the original stock
NAND backup was lost. So we couldn't restore stock to drive `nvrammanager`. It's
logically covered - `nvrammanager` does `ubiformat /dev/mtd<inactive> -o 0x1814
-S <field0>` of the same payload (byte-identical to the tested `factory.ubi`) and
sets the same `tp_boot_idx` - but a full stock-device web-GUI flash remains the
final belt-and-suspenders check.

### Latent follow-up
`platform.sh` sysupgrade always sets `CI_UBIPART=rootfs` (slot 0), ignoring the
booted slot - if you run from slot 1 and sysupgrade, it writes the wrong slot.
