```markdown
# Sailfish OS on Sony Xperia 10 V (XQ-DC72 / Zambezi)

> **Note:** This repository is a community debugging log. Parts of it were drafted by **DeepSeek (AI Assistant)** from live debugging sessions. AI-generated content is not authoritative — every claim below is backed by a command output you can re-run. Where something is unverified, it says so.

## 📱 Project status: not bootable on XQ-DC72 as distributed

**The Sailfish community port release `SFOS_X10V_Release_0.0.1.tar.bz2` cannot boot this device as shipped.**

The release tarball contains exactly five entries:

```
./hybris-boot.img     (boot_a)
./dtbo.img            (dtbo_a)
./md5.lst             (checksums)
./sailfish.img001     (userdata)
```

There is **no `vendor_boot.img`**, no `vbmeta.img`, and no install script or README in the release.

This matters because the device is a **GKI device**. `hybris-boot.img` reports boot header **version 3** (Generic Kernel Image). On GKI devices, `boot_a` and `vendor_boot_a` are a **required pair**: the vendor ramdisk, the device-tree fstab, and the DTB all live in `vendor_boot_a`. Flashing only `boot_a` leaves the device's existing `vendor_boot_a` in place, and the Sailfish initramfs then runs against a vendor ramdisk and device tree it was never built for.

The observed result is the failure documented in this repository: the kernel boots, the device hangs at the Sony logo, and `pstore` is empty because the kernel never reached console init.

This is a **port-side gap**, not a device fault and not a user error. The phone's hardware is confirmed working: LineageOS 22.2 boots and runs on it.

## 🧱 The stack

- **Device:** Sony Xperia 10 V, model **XQ-DC72** (dual physical SIM). Confirmed from `ro.product.model` on a working LineageOS boot; corroborated by the `holi-qrdsku1-snd-card` audio card name. Not the XQ-DC54 / PDX-235 assumed in earlier drafts.
- **SoC:** Qualcomm Snapdragon 695 (`holi`).
- **Base (working):** LineageOS 22.2 (Android 15), kernel `5.4.300-qgki-gde696eaff864`.
- **Stock firmware on hand:** `68.1.A.2.270` and `68.2.A.3.123`.
- **Port target:** Sailfish OS 5.1 community port, `SFOS_X10V_Release_0.0.1`.
- **Blobs:** `SW_binaries_for_Xperia_Android_13_5.4_v4b_zambezi.img` (installation status unverified, see below).

## 🧩 Why it hangs: the short version

Three independent mismatches, all confirmed from command output:

1. **Missing `vendor_boot.img` in the release.** Confirmed by `tar -tjf SFOS_X10V_Release_0.0.1.tar.bz2` → 5 entries, no vendor_boot.
2. **Build-ID gap.** `hybris-boot.img` reports `os patch level 2025-10`. The device's current `vendor_boot_a` reports `buildid=ZAMBEZI-1.1.0-REL-240918-0236` (2024-09-18). Thirteen months apart.
3. **Product variant gap.** `vendor_boot_a` reports `buildproduct=pdx235` (XQ-DC54). The device reports `XQ-DC72`.

Any one of these would be enough to break the boot pair. All three are present.

See `TROUBLESHOOTING.md §1` for the full evidence and the reproduction steps.

## ⚠️ Known issues (accurate status)

- **Boot hang at Sony logo — confirmed, port-side.** Missing `vendor_boot.img` in the release. Not fixable by flashing the provided files, disabling vbmeta, or patching the fstab. See above.
- **Touchscreen — works.** FocalTech `fts_ts` initialises and reports events on LineageOS. The Sailfish display failure has not been independently observed because the boot never reaches userspace; do not attribute it to touchscreen hardware.
- **Camera — untested on Sailfish.** On the LineageOS baseline, the full Qualcomm camera stack initialises (`camera.qcom.so`, `com.qti.chi.override.so`, and `libofflinelog.so` are all present in `/vendor/lib64/`). Earlier drafts of this repo claimed `libofflinelog.so` was missing; that was wrong. If the Sailfish camera crashes when the port eventually boots, suspect packaging on the Sailfish side, not a missing blob.
- **Battery / charging — cosmetic.** On the LineageOS baseline, `smblib_set_icl_current: set ICL to 500000uA` re-asserts roughly every five seconds while charging. State of charge tracks correctly (98 → 100 over 2.5 h). This is an ICL re-negotiation loop, not a gauge fault, and not a boot blocker.
- **SELinux — permissive.** `hybris-boot.img` cmdline is `androidboot.selinux=permissive audit=0`. The port was never brought to enforcing. This is not the boot cause (SELinux is off), but it is a maturity signal.
- **Blob installation — unverified.** It has not been independently confirmed that the v4b blobs are currently installed on this unit, or that they survived later flashes. See `TROUBLESHOOTING.md §1a`.

## 🛠️ Working baseline: hardware diagnostics

Captured from a working LineageOS 22.2 boot on the XQ-DC72. Useful as a reference for anyone debugging a Sailfish bring-up on `holi`.

- **Partition map:** dynamic `super -> sda74`. Separate `vendor_boot_a/b` (`sda70`/`sda71`), `dtbo_a/b` (`sda58`/`sda59`), `vbmeta_a/b` (`sda52`/`sda53`), **and `vbmeta_system_a/b` (`sda54`/`sda55`)**. Note there are two AVB images on the active slot, not one.
- **HALs and kernel modules:** full `vendor/lib64/hw/` listing including `camera.qcom.so`, `com.qti.chi.override.so`, `vulkan.adreno.so`; kernel modules `focaltech_fts`, `aw882xx_dlkm`, `camera`, `wlan`.
- **Input devices:** FocalTech `fts_ts`, Egis `egis_fp`, `qpnp_pon`, `holi-qrdsku1-snd-card` headset/button jacks.
- **Kernel:** `5.4.300-qgki-gde696eaff864`, GKI.
- **fstab:** read from the device tree (`/proc/device-tree/firmware/android/`), root is `/first_stage_ramdisk`, `super` mounted via logical partitions (`dm-*`). There is no static `/dev/block/by-name/system`.

## 📚 Documentation

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — evidence, reproduction steps, log capture procedure, the confirmed root cause, and what does *not* work.
- **[gather_info.py](gather_info.py)** — collects HALs, inputs, modules, and kernel log from a working LineageOS install. Has a `--scrub` flag that redacts MAC and IP addresses. Use it before publishing any logs.
- **[INSTALLING.md](INSTALLING.md)** — *does not exist.* The port ships no install script and no install documentation. The four files in the tarball are not sufficient to produce a booting device on GKI hardware. Do not follow older guides that tell you to flash `boot_a` and `userdata` alone.

## 🔗 Credits

- **LineageOS** — working Android base for this device, and the practical flashing reference.
- **Sony** — AOSP device configurations and proprietary binaries.
- **The Sailfish OS community** — `droid-hal`, `hybris-boot`, and the tooling.
- **sharks-dev** — author of the Zambezi Sailfish port.
- **DeepSeek (AI)** — drafting and structuring this documentation. See disclaimer at the top.

## 🤝 Contributing

If you are the port maintainer: a `vendor_boot.img` built against the same kernel tree and DT as `hybris-boot.img` would make this port viable on `holi` GKI devices. Failing that, a rebuild of `hybris-boot.img` as a pre-GKI, self-contained boot image (if the target bootloader permits) would sidestep the pairing requirement.

If you are another user: corrections to inaccurate AI-generated claims are especially welcome. Please include the command output that backs the correction.

*Last updated: October 2026.*
```
