# Installing Sailfish OS on Sony Xperia 10 V (XQ-DC72)

> **⚠️ Reconstructed, not validated.**
> This guide was **rebuilt from debugging notes** after the original `INSTALLING.md` was lost. It has **not been confirmed to produce a booting Sailfish system** on this unit. Steps marked **UNVERIFIED** are inferred from the partition map and working LineageOS baseline, not from a successful run. Treat it as a starting point and record what actually happens.
>
> **Device:** XQ-DC72 (`holi` / Snapdragon 695), confirmed from `ro.product.model` on a working LineageOS boot. If you are on a different `holi` SKU, re-verify every step.

## 0. Read this first

The project is **experimental**. As of the last update, the device **hangs at the Sony logo** during the Sailfish `hybris-boot` handoff, and the root cause is **not yet determined**. See `TROUBLESHOOTING.md` §1 for the four working hypotheses and §2 for how to capture the pstore log that will tell you which one applies.

**Do not assume the v4b blobs are installed.** Their status on this unit is unconfirmed. Verify before any Sailfish boot attempt (step 2a).

## 1. What you need

- Sony Xperia 10 V, **XQ-DC72** (dual physical SIM).
- Stock Android 14 base — firmware **`68.1.A.2.270`**, **XQ-DC72 variant** (not PDX-235).
- LineageOS 22.2 (Android 15) for `zambezi`, flashed and **booting** (touchscreen works = good baseline).
- Sony v4b blobs: `SW_binaries_for_Xperia_Android_13_5.4_v4b_zambezi.img`.
- Sailfish OS 5.1 community port for Zambezi: `hybris-boot.img`, `dtbo.img`, `sailfish.img001`.
- `fastboot` **v33 or v34**. Newer versions have been reported to fail on Sony's implementation.
- Unlocked bootloader. Sony blocks `fastboot boot`, so every image must be **flashed**, not booted from RAM.

## 2. Establish a working baseline

1. Flash stock `68.1.A.2.270` (XQ-DC72), boot Android once.
2. Flash LineageOS 22.2 per its own instructions, boot it.
3. Confirm touchscreen, Wi-Fi, and that `ro.product.model` reports `XQ-DC72`:
   ```bash
   adb shell getprop ro.product.model
