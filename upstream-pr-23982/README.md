# Rebase von openwrt/openwrt#23982 auf aktuelles `main`

Die Commits des Upstream-PRs (Stand `f47be3b`, 18.07.2026), rebased auf
`openwrt/main` @ `ab58ca8f` (26.09.2026):

- `0001-mac80211-ath11k-pick-DP-ring-sizes-at-runtime-based-.patch`
- `0002-qualcommax-fix-qpic-snand-use-after-free-on-deferred.patch` (neu)
- `0003-qualcommax-add-support-for-TP-Link-RE700X.patch`

## Was sich geändert hat

- **Gerätesupport (0003):** ließ sich konfliktfrei anwenden, inhaltlich unverändert
  (Auto-Merge in `ipq-wifi/Makefile`, `ipq50xx.mk`, `platform.sh`).
- **ath11k-Patch 953 (0001):** `main` hat `mac80211` von 6.18.26 auf
  **backports 7.2** angehoben. Der Patch ging noch durch, aber Hunk 4 nur mit
  *fuzz 2* (upstream hat `hw_params.max_tx_ring` in
  `hw_params.hal_params->num_tx_rings` umbenannt). Der Patch wurde gegen
  backports 7.2 (mit allen vorherigen `mac80211`-Patches angewendet) neu
  erzeugt: jetzt ohne Fuzz/Offset, Code-Änderung selbst identisch.

- **Fehlende Gerätefunktionen ergänzt (0003).** Der PR-Stand vom 18.07. hätte
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
- ✅ **Hardware-Test 28.09.2026 (Lauf #7, Initramfs per TFTP):** beide Fixes
  bestätigt. NAND beim Boot erkannt (16 qcomsmem-Partitionen, kein `bind`
  nötig), `factory_data` gemountet, RTL8211F erkannt, **Link 1 Gbps/Full**
  mit der DWMAC/UNIPHY-DTS, 2,4-GHz-Kalibrierung ok.
  - 5 GHz: `qmi failed to load CAL data file:cal-ahb-b00a040.wifi.bin` (-12).
    Ursache: RE700X-Eintrag für QCN6122 war beim Einfügen im QCN9074-Abschnitt
    von `11-ath11k-caldata` gelandet → verschoben (Lauf #8).
- ✅ **Hardware-Test 29.09.2026 (Lauf #8, vom Flash, Update per LuCI mit
  Einstellungen):** komplett bestanden. Boot vom Flash, Link 1 Gbps/Full,
  **beide Radios** (2,4 GHz `phy0-ap0` Kanal 1; 5 GHz `phy1-ap0` Kanal 36/80 MHz),
  keine Kalibrierfehler, MACs = Label +1/+2, ~47 MB RAM verfügbar mit beiden
  Radios und `coherent_pool=2M`.
- ⚠️ Weiterhin nicht Ende-zu-Ende getestet: Erstinstallation aus der
  Stock-Firmware per Web-GUI (`factory-webflash.bin`), kein Gerät mit Stock-FW.
- ❗ **29.09.2026: Speicherfehler im alten ath11k-Patch 953 gefunden.**
  `ATH11K_TX_COMPL_NEXT()` wrappte weiter bei 32768, der `tx_status`-Puffer hatte
  aber nur 2048 Einträge → Out-of-bounds bei WLAN-TX-Verkehr. Betraf Image #8
  und den alten WLAN-Branch, **nicht** den PR (dort ist der Patch entfernt) und
  **nicht** die Release-Firmware (952 ändert die Makros direkt). Ersetzt durch
  neuen 953 (ath12k-artige Speicherprofile, siehe `upstream-kernel/`), Branch
  `re700x-wifi-followup` aktualisiert; dort außerdem die WLAN-LEDs ergänzt.
- ❌ Lauf #9 und #10 (29.09.2026): abgebrochen, bevor etwas vom RE700X gebaut
  wurde. Ursache war das Test-Skript: Die Umgebungsvariable `PATCH_DIR`
  überschreibt in OpenWrt den Patch-Ordner jedes Pakets, dadurch wurden keine
  Patches angewendet. Umbenannt in `SERIES_DIR`.
- ✅ **Lauf #11 (29.09.2026): Build erfolgreich**, WLAN-Folgestand
  (`wifi-followup/`: neuer Patch 953, WLAN an, WLAN-LEDs + LED-Migration),
  beide `board-2.bin` im Image nachgewiesen. Hardware-Test steht aus.
- ✅ **Hardware-Test 29.09.2026 (Lauf #11, vom Flash, Update mit Einstellungen,
  EG-Gerät):** Boot sauber, beide Radios, keine WLAN-Fehler/`-108`. Unter
  Last (YouTube, danach >6 Clients, Router-WLAN aus) keine neuen Meldungen;
  Firmware: `WLAN.HK.2.7.0.1-01744-QCAHKSWPL_SILICONZ-1`.
- ❌ **Speicherleck (29.09.2026, Lauf #11):** `MemAvailable` fällt stetig
  (40 MB nach Boot → 25 MB nach 21 min → 10 MB nach 1 h, 3–6 Clients).
  Alte Release-Firmware (OG, Kernel 6.12, NSS-Ethernet, backports 6.18.26):
  ~44 MB nach 93 Tagen. Nicht Userspace (`AnonPages` 6 MB), Slab nur +4 MB;
  ~30 MB mehr in keiner `meminfo`-Zeile → vermutlich nicht freigegebene
  Netzwerkpakete. Kandidaten: Kernel 6.18, ath11k (backports 7.2),
  DWMAC/UNIPHY-Ethernet. Eingrenzung per minütlichem Log (Speicher vs.
  Paketzähler je Schnittstelle) läuft. **Bis dahin nichts weiter einreichen.**
- ⚠️ **Korrektur 30.09.2026:** Das "Speicherleck" oben ist so **nicht belegt**.
  Die "RAM low - reboot"-Abbrüche kamen vom eigenen Log-Skript (Schwelle
  15 MB), nicht von Speichermangel. Längerer Lauf mit Lauf #12 (mac80211
  6.18.39) unter WLAN-Last: `MemAvailable` fällt auf ~16 MB, der Kernel gibt
  danach wieder frei (23–29 MB) bei weiterlaufendem Verkehr. Offen ist nur
  der höhere Grundverbrauch gegenüber der Release-Firmware (EG 16–30 MB vs.
  OG 44–52 MB frei); Langzeittest ohne Skript-Neustart auf OOM-Meldungen läuft.
- Lauf #12 (Test-Build, nur zur Eingrenzung): wie #11, aber mac80211 auf
  6.18.39 zurückgesetzt (`bisect-mac80211-6.18.39/`). Gleiches Verhalten wie #11
  → das Verhalten hängt nicht an backports 7.2.
- ✅ **Vergleich unter gleicher Last (30.09.2026, EG, Router-WLAN aus, 4–6 Clients,
  Log-Skript mit 4-MB-Schwelle):**
  - Lauf #12 (mac80211 6.18.39): `MemAvailable` schwankt 12–34 MB, erholt sich
    jeweils in 1–3 min, kein Abwärtstrend, keine OOM-Meldung.
  - Lauf #11 (mac80211 7.2, Ziel-Stand): 14–37 MB bei mehr 5-GHz-Verkehr
    (bis ~30.000 TX-Pakete/min), kein Abwärtstrend, keine OOM-Meldung.
  - → Beide Treiber gleichwertig, **Lauf #11 besteht den Hardware-Test**.
    Release-Firmware (OG) liegt unter ähnlicher Last (6 Clients) ebenfalls bei
    ~30 MB frei; die früheren 44–52 MB waren bei weniger Last. Kein relevanter
    Unterschied.

## Review-Runde 30.09.2026 (George)

- "remove the crypto and cryptobam nodes please. The upstream driver was broken
  and has been removed." → `&crypto`/`&cryptobam` aus der DTS entfernt.
- "there's an upstream patch for this one" (torvalds/linux `f94c9b68bb5f`,
  "spi: spi-qpic-snand: publish the ECC context to snandc->qspi", in v7.3) →
  eigener Patch 0402 ersetzt durch Backport
  `0093-v7.3-spi-spi-qpic-snand-publish-the-ECC-context-to-snandc-qspi.patch`.
  Der Cleanup-Hunk ist an 6.18 angepasst (dort gibt es noch kein
  `oob_buf`-Handling in `qcom_spi_ecc_cleanup_ctx_pipelined()`), im Patch
  vermerkt. Geprüft: wendet sauber auf 6.18.52 an, danach 0401 ohne Versatz.
- Beide Commits neu auf `openwrt/main` @ `c759267c` (30.09.2026) gesetzt,
  konfliktfrei. Test-Build Lauf #13 erfolgreich (Kernel mit 0093 + DTS ohne Crypto-Nodes kompiliert, Image erzeugt).
- ✅ 01.10.2026: Fork-Branch `re700x-upstream` per force-with-lease auf
  `6f604eb1` aktualisiert (vorher `65b655d9`); PR #23982 zeigt die zwei neuen
  Commits (`819935d8` Backport, `6f604eb1` Gerät).
- ⚠️→✅ 01.10.2026: openwrt-ai/FormalityCheck: Committer von `6f604eb1` war
  `Claude <noreply@anthropic.com>` (Umgebungs-Standard beim Neuaufsetzen).
  Committer korrigiert (Inhalt identisch, gleicher Tree), PR-Head jetzt
  `ac4be590`. `user.name`/`user.email` im OpenWrt-Klon fest auf Eduard gesetzt.
- ❌→✅ 02.10.2026: OpenWrt-CI "Build Kernel / Check Kernel patches" rot auf
  `ac4be590`: Backport 0093 lag im `git format-patch`-Format vor (Diffstat,
  `diff --git`, Signatur, volle Funktionsnamen), nicht im per
  `make target/linux/refresh` erzeugten quilt-Format. Auf das Refresh-Format
  umgestellt (Inhalt identisch, 0401 unverändert gültig), PR-Head jetzt `47bc9143`.
