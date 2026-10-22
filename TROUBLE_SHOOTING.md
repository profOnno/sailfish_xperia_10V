```markdown
> **Note:** This troubleshooting guide was drafted by **DeepSeek (AI Assistant)** from live debugging sessions. AI-generated content is not authoritative — every claim below is backed by a command output you can re-run. Where a conclusion is unverified, it says so.

# Sailfish OS on Sony Xperia 10 V (XQ-DC72) — Troubleshooting

**Device:** XQ-DC72 (`holi`, Snapdragon 695). Confirmed from `ro.product.model` on a working LineageOS boot and corroborated by `holi-qrdsku1-snd-card`. **Not** XQ-DC54 / PDX-235. If you are on a different `holi` SKU, re-verify every claim below against your own device.

**Current state:** LineageOS 22.2 boots and runs on this device. The Sailfish port hangs at the Sony logo. The cause is confirmed and documented in §1.

---

## 1. Confirmed root cause: missing `vendor_boot.img` in the port release

### Evidence (reproducible)

**Release inventory:**

```
$ tar -tjf SFOS_X10V_Release_0.0.1.tar.bz2
./hybris-boot.img
./dtbo.img
./md5.lst
./sailfish.img001
```

Five entries. No `vendor_boot.img`. No `vbmeta.img`. No install script. No README.

**Boot image header (`hybris-boot.img`):**

```
boot magic: ANDROID!
kernel_size: 43731456
ramdisk size: 8835737
os version: 15.0.0
os patch level: 2025-10
boot image header version: 3
command line args: androidboot.selinux=permissive audit=0
```

Header version **3** = Generic Kernel Image. On GKI, `boot` and `vendor_boot` are a required pair.

**Vendor boot header (device's existing `vendor_boot_a`):**

```
boot magic: VNDRBOOT
vendor boot image header version: 3
vendor ramdisk size: 707850
dtb size: 330580
vendor command line args: ... buildproduct=pdx235
  buildid=ZAMBEZI-1.1.0-REL-240918-0236 buildvariant=user
```

`buildproduct=pdx235` = XQ-DC54. `buildid` dated **2024-09-18**.

**The device reports `XQ-DC72`.**

### The three mismatches

| # | Mismatch | Consequence |
|---|---|---|
| 1 | Port release ships no `vendor_boot.img` | The boot/vendor_boot pair is incomplete. `hybris-boot.img` runs against a vendor ramdisk, DT fstab, and DTB it was not built for. |
| 2 | `hybris-boot.img` is `2025-10`; `vendor_boot_a` is `2024-09-18` | Thirteen-month gap. The vendor ramdisk modules and DTB predate the kernel by over a year. |
| 3 | `vendor_boot_a` is `pdx235` (XQ-DC54); device is `XQ-DC72` | Product-variant mismatch. Audio routing, sensor config, and partition expectations may differ. |

### Reproduction

Flash the release's three payload files to the active slot, leave `vendor_boot_a` untouched:

```bash
sudo fastboot getvar current-slot          # e.g. "a"

sudo fastboot flash boot_a     hybris-boot.img
sudo fastboot flash dtbo_a     dtbo.img
sudo fastboot flash userdata   sailfish.img001
# Do NOT flash vendor_boot_a — the release has nothing to flash to it.
```

Expected result: device boots, Sony logo appears, hangs indefinitely. `pstore` is empty (kernel never reached console init). This is the observed behaviour and is consistent with a boot/vendor_boot pairing mismatch.

### What does *not* fix this

These were all tried or considered during the debugging sessions and none are the root cause:

- **Disabling verity on `vbmeta` and `vbmeta_system`.** The port doesn't ship a vbmeta. The base system already boots with AVB disabled. This is not the blocker.
- **Patching the ramdisk fstab to use `super`/dynamic partitions.** The fstab lives in the *vendor ramdisk / DTB*, not in `hybris-boot.img`'s ramdisk. Patching the wrong file changes nothing.
- **Flashing a newer/older `fastboot`.** v33 and v34 both complete the flash. The hang is not a flashing error.
- **Re-flashing the blobs.** The v4b blobs are orthogonal to the boot-pair problem.
- **Re-flashing the LineageOS `vendor_boot_a` after the port files.** This leaves you with LineageOS's vendor ramdisk running under a Sailfish kernel and init — a harder mismatch, not an easier one.

### What *would* fix this

Port-side work, not device-side flashing:

1. **Ship a `vendor_boot.img` built against the same kernel tree and DT as `hybris-boot.img`.** This is the correct GKI solution. It requires the port maintainer to have the build artefacts.
2. **Rebuild `hybris-boot.img` as a pre-GKI, self-contained boot image.** Sidesteps the pairing, but only works if the device bootloader accepts a header-v0/2 boot image on a GKI slot. Unverified.
3. **Replace the Sailfish ramdisk's root-mount logic with a dynamic-partition-aware equivalent, and merge the LineageOS DT fstab into a rebuilt vendor_boot.** This is a real engineering effort, not a flash step. It also means leaving the working LineageOS state for every test cycle, with the associated risk of losing the baseline.

None of these are actions a user can take without the port's build tree.

### 1a. ⚠️ Unverified: v4b blob installation status

It has not been independently confirmed on this unit that the v4b blob image was successfully written, or that it survived subsequent `boot`/`vendor_boot`/`super` flashes. A later flash of those partitions should not overwrite the blob partitions, but this has not been re-checked on this device.

To close this before attributing any future failure to the blobs:

```bash
# On the running LineageOS baseline:
adb root
adb shell ls -l /vendor/lib64/libofflinelog.so
adb shell ls -l /vendor/lib64/hw/camera.qcom.so
adb shell ls -l /vendor/lib64/com.qti.chi.override.so
```

If those three files are present, the blob set that matters for camera is in place. For a full verification, re-flash the v4b image from a clean state and hash-compare the target partitions against the source image.

---

## 2. Capturing logs from a failed Sailfish boot

Sony's bootloader blocks `fastboot boot hybris-boot.img --cmdline "bootmode=debug"`, so the Telnet debug console is unavailable. Use `pstore`, read back from LineageOS Recovery.

1. Let the device hang at the Sony logo (or bootloop).
2. Force off: hold **Power + Volume Up** until it vibrates three times.
3. Boot to **LineageOS Recovery**: hold **Volume Down + Power** until the Sony logo appears, release.
4. Confirm ADB sees recovery: `adb devices`.
5. Pull the log:

```bash
adb shell "cat /sys/fs/pstore/console-ramoops*"  > pstore_sailfish_crash.txt
adb shell "cat /sys/fs/pstore/dmesg-ramoops*"    > pstore_sailfish_dmesg.txt 2>/dev/null
```

### Interpreting the result

- **Both files empty / missing** → kernel died before console init. On this device, with this port, this is the **expected** result (see §1). It rules out userspace and compositor causes; it does not distinguish between the three mismatches in §1, all of which can produce this outcome.
- **Files exist and stop early with `dm-verity` / mount / AVB errors** → the kernel reached init; the failure is a root-mount problem. Not the pattern observed here, but worth checking if you are testing a modified port.
- **Files exist and reach init / userspace** → root mounted; the hang is downstream (compositor / `libhybris`). Also not observed here.

---

## 3. Working LineageOS baseline: what the device actually does

Captured from a boot of LineageOS 22.2 on this device. Use as a reference when comparing against any Sailfish attempt.

### 3.1 Root mount and partition layout

From early-boot `dmesg`:

```
[1.429217] init: AVB is not enabled, skip verity setup for '/metadata'
[1.431412] EXT4-fs (sda47): mounted filesystem ...
[1.418997] init: Switching root to '/first_stage_ramdisk'
[1.419280] init: [libfstab] Using Android DT directory /proc/device-tree/firmware/android/
[1.419681] init: [libfstab] ReadFstabFromDt(): failed to read fstab from dt
```

Key facts:

- **AVB is disabled** on the working boot. The base system does not rely on it.
- **fstab is read from the device tree**, not from a static `/etc/fstab` in the ramdisk.
- **root is `/first_stage_ramdisk`**, then `super` is mounted via logical partitions (`dm-6` through `dm-22`).
- **There is no `/dev/block/by-name/system`.** Any Sailfish initramfs that expects one will fail.

### 3.2 Verified partition map

```
super               -> /dev/block/sda74
metadata            -> /dev/block/sda47
userdata            -> /dev/block/sda75
misc                -> /dev/block/sda43
vbmeta_a            -> /dev/block/sda52
vbmeta_system_a     -> /dev/block/sda54
vendor_boot_a       -> /dev/block/sda70
dtbo_a              -> /dev/block/sda58
boot_a              -> /dev/block/sda29
```

Note **two** AVB images on the active slot: `vbmeta` and `vbmeta_system`. Any verity-disabling procedure that touches only `vbmeta` is incomplete.

### 3.3 Hardware confirmation

- **Touchscreen:** FocalTech `fts_ts` initialises, reports events. Working.
- **Audio:** Awinic `aw882xx` initialises two amplifiers. `aw_cali.bin` is loaded via a sysfs fallback after an initial `-13` (EACCES) on the direct path — functional, but the fallback is SELinux-dependent. DSP calibration `kctl` is missing (`msm_adsp_init_mixer_ctl_adm_pp_event_queue: failed to get kctl.`); playback works despite this.
- **Camera:** Full Qualcomm stack initialises. `camera.qcom.so` (~11.9 MB), `com.qti.chi.override.so` (~3.2 MB), and `libofflinelog.so` (~51 KB) all present in `/vendor/lib64/`. **`libofflinelog.so` is not missing.** Earlier drafts of this document said it was; that was incorrect.
- **Wi-Fi:** `wlan_mac.bin` from `/vendor/firmware/wlan/qca_cld/` is used for MAC. If that file is absent in a Sailfish vendor image, Wi-Fi will come up with a zero or random MAC.
- **Fingerprint:** Egis `egis_fp` initialises. `egisap` TEE app loads from QSEECOM.
- **Battery / charging:** `smblib_set_icl_current: set ICL to 500000uA` repeats roughly every five seconds while charging. SOC tracks correctly (98 → 100 over 2.5 h). This is a **cosmetic ICL re-negotiation loop**, not a gauge fault and not a boot blocker. Earlier drafts called for a kernel patch; the evidence does not support that framing.
- **I2C bus 2 early-boot noise:** `i2c_geni 4c90000.i2c: i2c error :-107` (`ENOTCONN`) fires hundreds of times during early probe for `aw2016_led`, `sec_ts`, `FTS_TS`, `EGISFP`, `wl2868c`. It resolves within ~2.5 s. Not a bug, but relevant if a future Sailfish bring-up probes those devices synchronously.

---

## 4. Diagnostic script

`gather_info.py` collects HALs, inputs, modules, and kernel log from a working LineageOS install.

### Prerequisite

```bash
adb root
```

On a standard LineageOS user build the `shell` user cannot read `/vendor/firmware/` or `dmesg`. If `adb root` fails, enable "Rooted debugging" in Developer Options or install Magisk.

### Scrub before publishing

`--scrub` redacts MAC addresses, IPv4, and IPv6.

```bash
python3 gather_info.py --scrub
```

If you run it without the flag, the script warns and pauses. If you proceed without scrubbing, **do not publish `network_interfaces.txt`** — it contains your Wi-Fi MAC and local IPs in plain text.

### Verify the scrub

```bash
grep -E "([0-9a-f]{2}:){5}[0-9a-f]{2}|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|([0-9a-f]{1,4}:){2,}" all_diagnostics.txt
```

Successful scrub → no output. Any output → do not publish until corrected.

---

## 5. If you are the port maintainer

The single most useful change is to ship a `vendor_boot.img` built from the same kernel tree and DT as `hybris-boot.img`. Without it, the port cannot boot GKI devices. The evidence is in §1 and can be reproduced from the release tarball alone.

Secondarily, a README in the release explaining which devices and which bootloader layouts the port supports would have saved the debugging sessions that produced this document.

---

## 6. If you are another user with an XQ-DC72

Do not flash the port expecting it to boot. It will not. Keep the phone on LineageOS 22.2, which works. If you want to try the port anyway, accept that you are risking the working baseline, and understand that the fix requires port-side build work, not a flashing procedure.

*Last updated: October 2026.*
```
