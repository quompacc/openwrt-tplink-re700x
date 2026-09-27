# Rebase von openwrt/openwrt#23982 auf aktuelles `main`

Die beiden Commits des Upstream-PRs (Stand `f47be3b`, 18.07.2026), rebased auf
`openwrt/main` @ `ab58ca8f` (26.09.2026):

- `0001-mac80211-ath11k-pick-DP-ring-sizes-at-runtime-based-.patch`
- `0002-qualcommax-add-support-for-TP-Link-RE700X.patch`

## Was sich geändert hat

- **Gerätesupport (0002):** ließ sich konfliktfrei anwenden, inhaltlich unverändert
  (Auto-Merge in `ipq-wifi/Makefile`, `ipq50xx.mk`, `platform.sh`).
- **ath11k-Patch 953 (0001):** `main` hat `mac80211` von 6.18.26 auf
  **backports 7.2** angehoben. Der Patch ging noch durch, aber Hunk 4 nur mit
  *fuzz 2* (upstream hat `hw_params.max_tx_ring` in
  `hw_params.hal_params->num_tx_rings` umbenannt). Der Patch wurde gegen
  backports 7.2 (mit allen vorherigen `mac80211`-Patches angewendet) neu
  erzeugt: jetzt ohne Fuzz/Offset, Code-Änderung selbst identisch.

## Geprüft / nicht geprüft

- ✅ Beide Commits wenden sauber auf `main` an.
- ✅ Patch 953 wendet exakt auf backports 7.2 an; keine weiteren hart codierten
  Ringgrößen übrig.
- ✅ DTS-Struktur passt zu AX830/MX2000 auf `main` (`&gmac1` + `&uniphy0`);
  das Umbenennen der qca8k-Switch-Nodes (`9e3c8633`) betrifft den RE700X nicht.
- ❌ **Kein Build und kein Test auf Hardware.** Insbesondere der Ethernet-Link mit
  der DWMAC/UNIPHY-DTS ist weiterhin ungetestet – das steht im PR noch als
  offener Punkt.

## In den PR übernehmen

In deinem lokalen `openwrt`-Clone (Branch des PRs, z. B. `re700x`):

```sh
git fetch https://github.com/openwrt/openwrt main
git checkout -B re700x FETCH_HEAD
git am /pfad/zu/upstream-pr-23982/*.patch
# bauen + auf dem Gerät testen, dann:
git push --force-with-lease <dein-fork> re700x
```
