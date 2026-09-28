# Rebase von openwrt/openwrt#23982 auf aktuelles `main`

Die beiden Commits des Upstream-PRs (Stand `f47be3b`, 18.07.2026), rebased auf
`openwrt/main` @ `ab58ca8f` (26.09.2026):

- `0001-mac80211-ath11k-pick-DP-ring-sizes-at-runtime-based-.patch`
- `0002-qualcommax-fix-qpic-snand-use-after-free-on-deferred.patch` (neu)
- `0003-qualcommax-add-support-for-TP-Link-RE700X.patch`

## Was sich geändert hat

- **Gerätesupport (0002):** ließ sich konfliktfrei anwenden, inhaltlich unverändert
  (Auto-Merge in `ipq-wifi/Makefile`, `ipq50xx.mk`, `platform.sh`).
- **ath11k-Patch 953 (0001):** `main` hat `mac80211` von 6.18.26 auf
  **backports 7.2** angehoben. Der Patch ging noch durch, aber Hunk 4 nur mit
  *fuzz 2* (upstream hat `hw_params.max_tx_ring` in
  `hw_params.hal_params->num_tx_rings` umbenannt). Der Patch wurde gegen
  backports 7.2 (mit allen vorherigen `mac80211`-Patches angewendet) neu
  erzeugt: jetzt ohne Fuzz/Offset, Code-Änderung selbst identisch.

- **Fehlende Gerätefunktionen ergänzt (0002).** Der PR-Stand vom 18.07. hätte
  auf dem Gerät nicht vollständig funktioniert. Verglichen mit der laufenden
  Firmware aus diesem Repo fehlten:
  1. **WLAN-Kalibrierdaten:** kein `11-ath11k-caldata`-Eintrag. ath11k braucht
     `cal-ahb-*.bin` aus `0:art` (IPQ5018 @ 0x1000, QCN6122 @ 0x26800), sonst
     "qmi failed to load CAL data file" → **kein WLAN**. `board-2.bin` allein
     reicht nicht.
  2. **Netzwerk-Grundkonfiguration:** kein `02_network`-Eintrag → bei
     Neuinstallation **kein LAN-Interface**.
  3. **LAN-MAC:** die DTS las `ethaddr` aus `0:appsblenv`. Dort steht aber keine
     MAC (nur `baudrate` + `has_default_mac`, siehe NOTES) → zufällige MAC.
     Jetzt wie beim TP-Link EAP650 in `main`: `factory_data` wird in preinit
     gemountet, `default-mac` = LAN, +1 = 2,4 GHz, +2 = 5 GHz (gleiche Werte
     wie die laufende Firmware).
  Die Commit-Message (Abschnitt MAC-Adressen) ist entsprechend korrigiert.

## Test-Build

`.github/workflows/re700x-pr-test.yml` baut genau diesen Stand (openwrt/main @
`ab58ca8f` + diese Patches, Board-Dateien lokal eingespielt, gleiche
LuCI-Pakete wie die re700x-Releases). Ergebnis: Artifact
`re700x-pr23982-test-image` im Actions-Tab.

## Geprüft / nicht geprüft

- ✅ Beide Commits wenden sauber auf `main` an.
- ✅ Patch 953 wendet exakt auf backports 7.2 an; keine weiteren hart codierten
  Ringgrößen übrig.
- ✅ DTS-Struktur passt zu AX830/MX2000 auf `main` (`&gmac1` + `&uniphy0`);
  das Umbenennen der qca8k-Switch-Nodes (`9e3c8633`) betrifft den RE700X nicht.
- ✅ **Build erfolgreich** (Actions-Lauf #5, 27.09.2026): Image kompiliert,
  beide RE700X-`board-2.bin` (IPQ5018 + QCN6122) per Hash im Rootfs der
  `sysupgrade.bin` nachgewiesen. Artifact `re700x-pr23982-test-image`.
  (Lauf #4 und älter: ohne board-2.bin – nicht verwenden.)
- ❌ **Hardware-Test 28.09.2026 (Lauf #5): bootet NICHT vom Flash.** UART-Log:
  `spi-nand spi0.0: probe with driver spi-nand failed with error -512` →
  keine MTD-Partitionen → wartet ewig auf `/dev/ubiblock0_1`. Außerdem
  `RTL8211F … probe … failed with error -110` (MDIO-Timeout) → kein Ethernet.
  Folgefehler: kein `factory_data`, keine WLAN-Kalibrierdaten.
  - **NAND, Ursache gefunden:** Use-after-free in `spi-qpic-snand` bei
    zurückgestelltem Probe (Kernel ≥ 6.15 liest den Factory-OTP des ESMT
    F50D1G41LB beim Registrieren). Manueller `bind` nach dem Boot funktioniert
    (16 Partitionen). Fix: neuer Patch `0402-…` (Commit 0002). Upstream
    existiert ein gleichwertiger Fix auf linux-spi.
  - **PHY, Hypothese:** `&mdio0` war in der DTS deaktiviert; dessen Probe setzt
    TCSR `ETH_LDO_RDY` für die CMN-PLL. Alle anderen IPQ5018-Boards und die
    laufende Firmware haben es aktiv → wieder aktiviert, **noch unbestätigt**.
  - Nächster Test: Initramfs per TFTP (ohne Flash-Schreibzugriff).
