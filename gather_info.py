#!/usr/bin/env python3
import subprocess
import os
import datetime
import argparse
import re

def run_adb(command):
    """Runs an ADB shell command and returns the output."""
    try:
        result = subprocess.run(
            ["adb", "shell", command],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"ERROR running '{command}':\n{e.stderr}"

def scrub_data(content):
    """Redacts MAC addresses, IPv4 addresses, and IPv6 addresses."""
    # Redact MAC addresses (XX:XX:XX:XX:XX:XX)
    content = re.sub(
        r'([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})',
        'XX:XX:XX:XX:XX:XX',
        content
    )
    # Redact IPv4 addresses (X.X.X.X)
    content = re.sub(
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'X.X.X.X',
        content
    )
    # Redact IPv6 addresses (X::X)
    content = re.sub(
        r'\b(?:[a-fA-F0-9]{1,4}:){2,7}[a-fA-F0-9]{1,4}\b',
        'X::X',
        content
    )
    return content

def save_to_file(run_dir, filename, content, do_scrub):
    """Saves the content to a file in the specified directory."""
    if do_scrub:
        content = scrub_data(content)
    
    filepath = os.path.join(run_dir, filename)
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  [+] Saved: {filepath}")

def main():
    parser = argparse.ArgumentParser(
        description="Android Device Diagnostic Agent. Gathers hardware logs for libhybris/Sailfish porting.",
        epilog="WARNING: Without --scrub, MAC addresses and IP addresses will be saved in plain text. Do not publish raw logs to public repositories."
    )
    parser.add_argument(
        "--scrub", 
        action="store_true", 
        help="Redact MAC and IP addresses from the output files before saving."
    )
    args = parser.parse_args()

    print("==================================================")
    print("   Android Device Diagnostic Agent (LineageOS)")
    print("==================================================")

    if args.scrub:
        print("[+] Scrub mode ENABLED. Sensitive data will be redacted.")
    else:
        print("==================================================")
        print("   ⚠️  WARNING: SCRUB MODE DISABLED ⚠️")
        print("==================================================")
        print("  You have NOT enabled --scrub.")
        print("  MAC addresses, IPv4, and IPv6 addresses will be")
        print("  saved in the output files in PLAIN TEXT.")
        print("")
        print("  DO NOT upload these raw files to a public GitHub")
        print("  repository or share them online without redacting")
        print("  the network_interfaces.txt file first.")
        print("==================================================")
        input("  Press [Enter] to continue, or [Ctrl+C] to abort...")

    # 1. Check if ADB sees the device
    print("[*] Checking ADB connection...")
    try:
        devices = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
        if "device" not in devices:
            print("[-] Error: No device found. Make sure USB debugging is enabled and authorized.")
            return
        print("[+] Device found!")
    except FileNotFoundError:
        print("[-] Error: 'adb' command not found. Is platform-tools installed?")
        return

    # 2. Create the output directory
    base_output_dir = "device_diagnostics"
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(base_output_dir, f"run_{timestamp}")
    os.makedirs(run_dir)
    
    print(f"\n[*] Saving data to: {run_dir}\n")

    # 3. Define the commands we want to run
    commands = {
        "build_props.txt": "getprop | grep -E 'ro.build.version.release|ro.product.model|ro.board.platform|ro.product.cpu.abi'",
        "cpu_info.txt": "cat /proc/cpuinfo",
        "dmesg.txt": "dmesg",
        "kernel_version.txt": "uname -a",
        "lsmod.txt": "lsmod",
        "partitions.txt": "ls -la /dev/block/bootdevice/by-name/",
        "hal_hw_dir.txt": "ls -la /vendor/lib64/hw/",
        "hal_lib64.txt": "ls -la /vendor/lib64/",
        "graphics_props.txt": "getprop | grep -iE 'gralloc|hwcomposer|egl|gpu|opengl'",
        "input_devices.txt": "getevent -pl",
        "vendor_firmware.txt": "ls -la /vendor/firmware/",
        "network_interfaces.txt": "ip addr show",
        "wifi_props.txt": "getprop | grep -i wifi"
    }

    # 4. Run the commands and save the output
    print("[*] Gathering data from the device...")
    for filename, cmd in commands.items():
        print(f"  [>] Running: {cmd}")
        output = run_adb(cmd)
        save_to_file(run_dir, filename, output, args.scrub)

    # 5. Print a summary of the HAL directory
    print("\n==================================================")
    print("   QUICK SUMMARY: Vendor Hardware HALs")
    print("==================================================")
    hal_output = run_adb("ls -la /vendor/lib64/hw/")
    
    keywords = ["gralloc", "hwcomposer", "gps", "wifi", "bluetooth", "sensors"]
    for line in hal_output.splitlines():
        if any(k in line.lower() for k in keywords):
            print(f"  {line}")

    print("\n==================================================")
    print("   DONE!")
    print(f"   All files have been saved in: {run_dir}")
    if args.scrub:
        print("   [+] MAC and IP addresses have been redacted.")
    else:
        print("   [!] Reminder: Raw MAC/IP addresses are present.")
        print("       Redact network_interfaces.txt before sharing.")
    print("==================================================")

if __name__ == "__main__":
    main()
