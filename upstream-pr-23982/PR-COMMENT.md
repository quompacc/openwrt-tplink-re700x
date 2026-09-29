Rebased onto current main and **tested on hardware** (booting from flash, sysupgrade with kept settings):

- Ethernet with the new DWMAC/UNIPHY stack: `Link is Up - 1Gbps/Full` (gmac1 → SGMII/uniphy0 → RTL8211F)
- Both radios up (IPQ5018 2.4 GHz + QCN6122 5 GHz, 80 MHz), ~47 MB RAM available with both radios
- MACs from the `factory_data` UBI volume (label / +1 / +2)

Changes since the last push:

1. **New patch: `spi: spi-qpic-snand: publish the ECC context on creation`.** With Linux ≥ 6.15 the RE700X did not boot from flash: `spi-nand spi0.0: probe with driver spi-nand failed with error -512`, so no MTD partitions and no rootfs. Cause: a use-after-free of the ECC context on deferred probe (spinand now reads the factory OTP of the ESMT F50D1G41LB during registration, then the qcom smem partition parser defers, and the retry reads the freed context). An equivalent fix has been posted to linux-spi; this patch can be dropped once that is backported.
2. **DTS: `&mdio0` enabled again.** Without it the RTL8211F on MDIO1 timed out (`-110`). Its probe sets TCSR `ETH_LDO_RDY` for the CMN PLL, as on the other ipq5018 boards.
3. **Board scripts added:** caldata extraction from `0:art` (IPQ5018 @ 0x1000, QCN6122 @ 0x26800; without it ath11k fails with `qmi failed to load CAL data file`), `02_network` LAN entry, and MACs from `factory_data` via preinit, following the EAP650. The LAN MAC previously came from an `ethaddr` in `0:appsblenv`, which does not exist on this device, so the DTS nvmem cell is removed.
4. The ath11k DP ring patch is refreshed for backports 7.2 (no functional change).

Board data for the QCN6122/IPQ5018 is still pending in openwrt/firmware_qca-wireless#141.

@georgemoussalem: did the ath11k DP ring size change make it upstream, or should I send it myself?

Not tested end-to-end: the first install from stock firmware via the TP-Link web UI (no unit on stock firmware left). The flashing path is covered by the dual-slot boot test described in the commit message; UART is recommended for a first install.
