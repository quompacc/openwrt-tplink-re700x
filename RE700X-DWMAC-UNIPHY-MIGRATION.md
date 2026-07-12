# RE700X → DWMAC/UNIPHY: DTS-Migration für PR openwrt/openwrt#23982

Umsetzung der Maintainer-Anfrage von `georgemoussalem` (12. Jul 2026):

> „can you please rebase on top of main which now includes the new DWMAC/UNIPHY
> ethernet stack and convert your device tree? See the MX2000 as an example."

Das aktuelle `openwrt/main` hat den qualcommax-Ethernet-Stack von der alten
NSS-`dp`/`ess`-Architektur (`&switch`, `&dp1`, `&dp2`, `MAC_MODE_*`) auf den
mainline-Stack mit **DWMAC** (`&gmac0`/`&gmac1`) + **UNIPHY** (`&uniphy0`)
umgestellt. Die RE700X-DTS muss entsprechend umgeschrieben werden.

Die fertig konvertierte Datei liegt daneben: **`ipq5018-re700x.dts`**.

## Was sich an der DTS ändert

Hardware-Fakt (aus `NOTES-re700x.md`, Zeilen 47 / 254–256 / 444): der RE700X hat
**genau einen** Gigabit-Port, verdrahtet als

```
IPQ5018 MAC1 --- SGMII (uniphy0) ---> Realtek RTL8211F @ MDIO1 addr 6
```

Der SoC-interne GE-PHY (MAC0/`gmac0`) ist an keinen externen Port geführt. Damit
ist der RE700X ein Direkt-PHY-Fall wie die **Yuncore AX830** (nur SGMII/RTL8211F
statt 2500base-x/QCA8081), nicht wie die MX2000 (die hängt an einem QCA8337-Switch).

Alt (ess/dp-Stack) → Neu (DWMAC/UNIPHY):

- `&switch { switch_mac_mode = <MAC_MODE_SGMII_CHANNEL0>; qcom,port_phyinfo {…} }`
  → **entfällt komplett**.
- `&dp1` (WAN, interner ge_phy@7/mdio0) → **entfällt** (Port existiert nicht).
- `&dp2` (LAN, RTL8211F) → wird zu **`&gmac1`** mit `phy-handle = <&rtl8211f_6>`,
  `phy-mode = "sgmii"`, `label = "lan"`, MAC aus `macaddr_appsblenv_ethaddr` off. 0.
- neu: **`&uniphy0`** mit `assigned-clock-rates = <UNIPHY_REFCLK_25MHZ>` (SGMII/1G;
  vgl. MX2000 = 25 MHz, AX830 = 50 MHz für 2500base-x).
- `&mdio1` bleibt, enthält jetzt den `rtl8211f_6`-PHY-Node direkt (kein Switch).
- `&mdio0` / `&ge_phy` (interner PHY) → **entfallen** (MAC0 ungenutzt).
- Aliase `ethernet0/ethernet1/label-mac-device` → entfernt (moderne Konvention,
  wie AX830/MX2000); die Port-MAC kommt aus `nvmem-cells` an `&gmac1`.

Die WLAN-Nodes (`&q6v5_wcss`, `&wifi`, `&wifi1`), NAND, LEDs, Buttons und die
Dual-Boot-`chosen`-bootargs bleiben inhaltlich unverändert.

## Bereits eingearbeitete Review-Fixes

Damit die konvertierte DTS gleich dem letzten Review-Stand entspricht:

- `coherent_pool` 4M → **2M** (wie alle anderen ipq5018-Boards).
- LEDs nutzen `LED_FUNCTION_WLAN_2GHZ` / `LED_FUNCTION_WLAN_5GHZ` statt Roh-Strings.
- `qcom,userpd-subsys-name` aus `&wifi` entfernt (mainline-Default; `&wifi1` behält es).
- veralteter Kommentar „patch 952 / README" → „patch 953".

## Rebase + Apply (Fork `quompacc/openwrt`, Branch `re700x-upstream`)

```sh
# im Klon deines Forks
git remote add upstream https://github.com/openwrt/openwrt.git   # falls noch nicht vorhanden
git fetch upstream
git checkout re700x-upstream
git rebase upstream/main
```

Der Rebase selbst läuft i. d. R. **konfliktfrei**, weil deine DTS eine neue Datei
ist. Aber danach referenziert sie entfernte Nodes (`&dp1`, `&switch`, `MAC_MODE_*`)
und der Build bricht. Deshalb die DTS austauschen:

```sh
# WICHTIG: die Zieldatei heisst ipq5018-tplink-re700x.dts (mit Vendor-Prefix) —
# das ist der Name, auf den DEVICE_DTS in image/ipq50xx.mk zeigt. Die konvertierte
# Arbeitsdatei (ipq5018-re700x.dts) muss die bestehende Target-DTS ERSETZEN, sonst
# baut OpenWrt weiter die alte ess/dp-Variante und die neue liegt unreferenziert daneben.
cp /pfad/zu/ipq5018-re700x.dts \
   target/linux/qualcommax/dts/ipq5018-tplink-re700x.dts

git add target/linux/qualcommax/dts/ipq5018-tplink-re700x.dts
git commit --amend --no-edit    # in den "add support"-Commit falten
```

Am Device-Commit (`qualcommax: add support for TP-Link RE700X`) noch die
Ethernet-Zeile der Commit-Message anpassen, z. B.:

> Ethernet: 1x Gigabit via IPQ5018 MAC1 (DWMAC) — SGMII/uniphy0 — Realtek
> RTL8211F @ MDIO1 addr 6 (single LAN port).

Der DP-Ring-Runtime-Patch (Commit 1) bleibt vorerst wie besprochen als Interim;
sobald `georgemoussalem`s ath11k-Variante in mainline ath11k landet, kann der
lokale Patch raus.

`DEVICE_DTS_CONFIG`, Paketliste und das factory-webflash-Image in
`image/ipq50xx.mk` bleiben unverändert.

## Build-Check

```sh
./scripts/feeds update -a && ./scripts/feeds install -a
make defconfig
# Target: qualcommax / ipq50xx, Device: TP-Link RE700X aktivieren
make target/linux/prepare V=s          # DTS/DTB kompiliert -> schneller Syntaxtest
make -j"$(nproc)"                       # voller Build
```

Wenn `make target/linux/prepare` die DTB fehlerfrei baut, ist die Node-Auflösung
(`&gmac1`, `&uniphy0`, `&mdio1`, `UNIPHY_REFCLK_25MHZ`) gegen das neue
`ipq5018-ess.dtsi` sauber.

## Hardware-Gegentest (auf dem Gerät)

- `ip link` zeigt genau ein `lan`-Interface, Link **1000/full** am RJ45.
- `lan`-MAC == `ethaddr` aus `0:appsblenv` (Offset 0).
- Beide Radios oben (`iw dev`), ~48 MB frei (`free`).
- Clean boot aus beiden Dual-Boot-Slots.

Erst danach den PR von *Draft* auf *ready* stellen — und weiterhin abhängig von
`openwrt/firmware_qca-wireless#141` (board-2.bin), das zuerst mergen muss.
