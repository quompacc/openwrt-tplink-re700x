# ath11k-Patch für den Linux-Kernel

`0001-wifi-ath11k-use-smaller-DP-rings-on-low-memory-syste.patch` bringt die
Speicherreduktion für 256-MB-Geräte in den offiziellen Linux-Kernel. Darum hat
George im PR gebeten ("Can you send it pls?"). Erst wenn der Patch dort
angenommen ist, darf WLAN für den RE700X in OpenWrt eingeschaltet werden.

## Was der Patch macht

- Er übernimmt das Muster, das **ath12k im Kernel schon verwendet**
  (`ath12k_core_get_memory_mode()`): Beim Start wird der RAM gemessen. Unter
  256 MiB nutzbarem RAM wird ein Profil mit kleineren Datenpfad-Ringen gewählt,
  darüber bleibt alles wie bisher.
- Kleinere Ringe: TX-Completion 32768 → 2048, RXDMA-Buffer 4096 → 1024,
  Monitor-Status 1024 → 512, Monitor-Buffer 4096 → 128, Monitor-Dest 2048 → 128
  (dieselben Werte wie die bisherige RE700X-Firmware).
- **Korrigiert den Fehler der alten OpenWrt-Version (Patch 953 vom Juni):**
  `ATH11K_TX_COMPL_NEXT()` lief weiter bis 32768, obwohl der `tx_status`-Puffer
  nur 2048 Einträge hatte → Lesen/Schreiben außerhalb des Puffers bei
  WLAN-Verkehr. Jetzt läuft der Index genau bis zur gewählten Ringgröße.

## Geprüft / nicht geprüft

- ✅ Basis: Linux 7.3-rc5 (torvalds/linux, 27.09.2026).
- ✅ Kompiliert (x86_64, ath11k + ath11k_pci + ath11k_ahb, `W=1`) **ohne Warnungen**.
- ✅ `scripts/checkpatch.pl --strict`: 0 Fehler, 0 Warnungen, 0 Hinweise.
- ✅ Lässt sich als OpenWrt-Patch 953 exakt auf backports 7.2 anwenden
  (Branch `re700x-wifi-followup`, `upstream-pr-23982/wifi-followup/`).
- ✅ **Auf Hardware getestet (29./30.09.2026, RE700X, OpenWrt-Lauf #11):** beide
  Radios unter Last (4–6 Clients, bis ~30.000 TX-Pakete/min auf 5 GHz),
  14–37 MB frei, keine OOM-Meldung, keine WLAN-Fehler. `Tested-on:` für
  IPQ5018 und QCN6122 ist eingetragen, die Commit-Message nennt jetzt die
  gemessenen Werte statt der früheren 47 MiB.
- ✅ **Gegen `ath-next` geprüft (30.09.2026):** `git am` auf `ath-next` @
  `21b4248bfa0f` (Merge tag 'ath-next-20260927') sauber, `checkpatch --strict`
  0 Fehler / 0 Warnungen.

## Ablauf bis zum Versand (später, gemeinsam)

1. ~~**Hardware-Test:**~~ erledigt (siehe oben).
   Ursprüngliche Anleitung: Testimage aus dem Branch `re700x-wifi-followup` bauen
   (WLAN an, neuer Patch 953), auf dem RE700X flashen, beide Radios mit Verkehr
   laufen lassen (z. B. ein paar GB über WLAN kopieren), `free -m` und `dmesg`
   prüfen. Danach unter die `Signed-off-by`-Zeile setzen:
   ```
   Tested-on: IPQ5018 hw1.0 AHB WLAN.HK.2.7.0.1-01744-QCAHKSWPL_SILICONZ-1
   ```
   (Firmware-Version aus dem `dmesg` des Geräts: `fw_build_id …`)

2. ~~**Auf `ath-next` umsetzen:**~~ erledigt (siehe oben).
   ```sh
   git clone https://git.kernel.org/pub/scm/linux/kernel/git/ath/ath.git -b ath-next
   cd ath
   git am /pfad/zu/0001-wifi-ath11k-use-smaller-DP-rings-on-low-memory-syste.patch
   ./scripts/checkpatch.pl --strict -g HEAD
   ```

3. **Empfänger** (laut `scripts/get_maintainer.pl`):
   - To: Jeff Johnson `<jjohnson@kernel.org>` (ath11k-Maintainer)
   - Cc: `ath11k@lists.infradead.org`, `linux-wireless@vger.kernel.org`,
     `linux-kernel@vger.kernel.org`
   - Optional Cc: George Moussalem (hat darum gebeten)

4. **Versenden** – Kernel-Patches gehen **per E-Mail**, nicht über GitHub.
   Normale Mailprogramme zerstören die Formatierung, daher `git send-email`:
   ```sh
   git config --global sendemail.smtpServer <dein SMTP-Server>
   git config --global sendemail.smtpUser <dein Login>
   git format-patch -1 --subject-prefix="PATCH ath-next"
   git send-email --to=jjohnson@kernel.org \
     --cc=ath11k@lists.infradead.org --cc=linux-wireless@vger.kernel.org \
     --cc=linux-kernel@vger.kernel.org \
     0001-*.patch
   ```
   Tipp: vorher mit `--to=<deine eigene Adresse>` an dich selbst schicken.

5. **Danach:** Antworten kommen per E-Mail an `eduard.hart@etik.com`. Auf
   Rückfragen antworten wir als "Reply-All" im Klartext (kein HTML). Wird eine
   geänderte Version nötig, geht sie als `[PATCH v2 ath-next]` raus.

Wenn der Patch im Kernel angenommen ist: OpenWrt-Folge-PR aus
`re700x-wifi-followup` (WLAN an, LEDs, Patch 953 → dann als Backport).
