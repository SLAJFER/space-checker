#!/usr/bin/env python3

import re, subprocess, sys

def user_input():
    
    if len(sys.argv) == 1:
        try:
            path = str(input("Enter a designated mount point here: ")).strip()
            return path
        except KeyboardInterrupt:
            quit()

    # If an argument is provided to the script, then that argument is used as the user provided path
    if len(sys.argv) == 2:
        path = sys.argv[1]
        return path

    if len(sys.argv) > 2:
        print("Too many arguments were provided")
        quit()

def dev_info(path_input):
    user_input = str(path_input)

    if user_input[0] != "/":
        user_input = str("/" + user_input)

    if len(user_input) > 1 and user_input[-1] == "/":
        user_input = str(user_input[:-1])

    # Gets the name and filepath for the partition (/dev/sda1, /dev/sdc3, etc), aswell as the partition's file system type
    try:
        mount = subprocess.run([f"mount -l | grep \"{user_input} type \""], shell=True, capture_output=True, text=True)
        mount_result = str(mount.stdout).strip()
        mount_search = re.search(r"((?:^\/)?\S+)\son\s\/\S*\stype\s(\S+)", mount_result)
        dev_name = str(mount_search.group(1))
        fs_type = str(mount_search.group(2))
    except Exception as e:
        print("Invalid mount point entered, please try again")
        exit()

    dev_data = subprocess.run([fr"sudo dumpe2fs -h {dev_name} | grep 'Block size\|Fragment size\|Inode count\|Free inodes\|Lifetime writes\|Block count\|Reserved block count\|Free blocks\|Blocks per group\|Inodes per group\|Inode size'"], shell=True, capture_output=True, text=True)
    dev_data_result = str(dev_data.stdout.strip())
    dev_data_result = dev_data_result.replace("\n", "")
    dev_data_search = re.search(r"\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+\s+\w\w)\D+(\d+)", dev_data_result)
    
    # This if-condition is needed because some partitions don't have any filesystem superblocks that can be opened and read
    # This includes partitions such as EFI system partition (/boot/efi) and mounted network shares
    if dev_data_search is None:
        print("Invalid mount point entered, please try again")
        quit()

    inode_count = int(dev_data_search.group(1))
    block_count = int(dev_data_search.group(2))
    reserved_blocks = int(dev_data_search.group(3))
    free_blocks = int(dev_data_search.group(4))
    free_inodes = int(dev_data_search.group(5))
    block_size = int(dev_data_search.group(6))
    fragment_size = int(dev_data_search.group(7))
    blocks_per_group = int(dev_data_search.group(8))
    inodes_per_group = int(dev_data_search.group(9))
    lifetime_writes_org = str(dev_data_search.group(10))
    inode_size = int(dev_data_search.group(11))

    # Converts the value in 'lifetime_writes_org' from MiB to GiB if original string was MiB formatted
    lifetime_writes_correct = float(lifetime_writes_org[:(len(lifetime_writes_org) - 3)])
    if lifetime_writes_org[(len(lifetime_writes_org) - 2)] == "M" and lifetime_writes_org[(len(lifetime_writes_org) - 1)] == "B":
        lifetime_writes_correct = float(lifetime_writes_correct / 1024)
    lifetime_writes_correct = float(lifetime_writes_correct)

    # Converts the raw data to more easily read formats (from bytes to KiB, MiB, or GiB)
    inode_count_MiB = float(inode_count / 1024 / 1024)
    free_inodes_MiB = float(free_inodes / 1024 / 1024)
    inode_ratio = (int((blocks_per_group / inodes_per_group) * block_size))
    inode_ratio_KiB = str(("1:{}".format(inode_ratio / 1024)).rstrip(".0"))
    inode_space = float((inode_count * inode_size) / 1024 / 1024 / 1024)
    block_count_GiB = float((block_count * block_size) / 1024 / 1024 / 1024)
    reserved_blocks_GiB = float((reserved_blocks * block_size) / 1024 / 1024 / 1024)
    used_blocks_GiB = float(((block_count - free_blocks) * 4096) / 1024 / 1024 / 1024)
    free_blocks_GiB = float(((free_blocks - reserved_blocks) * block_size) / 1024 / 1024 / 1024)
    
    # Formula for theoretically max usable disk space = (1 - inode_size / inode_ratio - reserved blocks (in percentage form) / 100)
    max_usable_space = float(1 - inode_size / inode_ratio - round((reserved_blocks_GiB / block_count_GiB) * 100) / 100)
    total_usage_percent = float(100 - ((free_blocks / block_count) * 100))

    inode_data = {
        "Total Inodes:": [inode_count_MiB, "M"],
        "Free Inodes:": [free_inodes_MiB, "M"],
        "Inode Size:": [inode_size, "Bytes"],
        "Inode Ratio:": [inode_ratio_KiB, "KiB"],
        "Inode Table Size:": [inode_space, "GiB"]
    }

    filesystem_data = {
        "Block Size:": [block_size, "Bytes"],
        "Fragment Size:": [fragment_size, "Bytes"],
        "File System Size:": [block_count_GiB, "GiB"],
        "Reserved Space:": [reserved_blocks_GiB, "GiB"],
        "Free Space:": [free_blocks_GiB, "GiB"],
        "Used Space:": [used_blocks_GiB, "GiB"],
        "Lifetime Writes:": [lifetime_writes_correct, "GiB"],
    }

    # Outputs all collected data and provides an overview of the filesystem on the provided partition
    print("------------------------------------")
    print(f"{'System Partition:':{""}<20}", f"{dev_name:{""}<8}")
    print(f"{'Mount Point:':{""}<20}", f"{user_input:{""}<8}")
    print(f"{'File System:':{""}<20}", f"{fs_type:{""}<8}")
    print("------------------------------------")
    for entry in inode_data.keys():
        if isinstance(inode_data[entry][0], float):
            print(f"{entry:{""}<20}", f"{f'{inode_data[entry][0]:.1f}':<8}", f"{inode_data[entry][1]:{""}<3}")
        else:
            print(f"{entry:{""}<20}", f"{inode_data[entry][0]:<8}", f"{inode_data[entry][1]:{""}<3}")
    print("------------------------------------")
    for entry in filesystem_data.keys():
        if isinstance(filesystem_data[entry][0], float):
            print(f"{entry:{""}<20}", f"{f'{filesystem_data[entry][0]:.1f}':<8}", f"{filesystem_data[entry][1]:{""}<3}")
        else:
            print(f"{entry:{""}<20}", f"{filesystem_data[entry][0]:<8}", f"{filesystem_data[entry][1]:{""}<3}")

    # Both percentages are relative to the total disk space of the examined file system
    print("------------------------------------")
    print(f"{'Total Usable Space:':{""}<20}", f"{max_usable_space * 100:.1f}" + "%")
    print(f"{'Total Space Used:':{""}<20}", f"{total_usage_percent:.1f}" + "%")
    print("------------------------------------")

path = user_input()
if path:
    dev_info(path)