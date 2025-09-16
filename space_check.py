import re, subprocess, sys

def user_input():
    # The script itself is always index 0 so any provided argument is always index 1
    if len(sys.argv) == 1:
        try:
            path = str(input("Enter a designated mount point here: ")).strip()
            return path
        
        # Keyboard interupt handeling
        except KeyboardInterrupt:
            quit()

    # If ONE argument is provided to the script, then that argument is used as the user provided path
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

    # Gets the name and filepath for the block device (/dev/sda1, /dev/sdc3, etc) that the block device is mounted to, aswell as the file system type
    try:
        mount = subprocess.run([f"mount -l | grep \"{user_input} type \""], shell=True, capture_output=True, text=True)
        mount_result = str(mount.stdout).strip()
        mount_search = re.search("((?:^\/)?\S+)\son\s\/\S*\stype\s(\S+)", mount_result)
        dev_name = str(mount_search.group(1))
        fs_type = str(mount_search.group(2))

    # Exits the program if any invalid mount point was entered by the user
    except Exception as e:
        print("Invalid mount point entered, please try again")
        exit()

    # Grabs and stores ALL specified fields of information that regards the designated block device
    dev_data = subprocess.run([f"sudo dumpe2fs -h {dev_name} | grep 'Block size\|Fragment size\|Inode count\|Free inodes\|Lifetime writes\|Block count\|Reserved block count\|Free blocks\|Blocks per group\|Inodes per group\|Inode size'"], shell=True, capture_output=True, text=True)
    dev_data_result = str(dev_data.stdout.strip())
    dev_data_result = dev_data_result.replace("\n", "")
    dev_data_search = re.search("\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+\s+\w\w)\D+(\d+)", dev_data_result)
    
    # This if-condition is needed because some technically valid mount points can't be opened and read, such as '/boot/efi'
    # Reading such mount points returns the error "dumpe2fs: Bad magic number in super-block while trying to open /dev/sda1"
    # This condition therefore checks if the 'dev_data_search' variable is empty or not, and exits the program if it is empty
    if dev_data_search is None:
        print("Invalid mount point entered, please try again")
        quit()

    # All previously collected data is sorted into different variables
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

    # Automatically converts the value in 'lifetime_writes_org' from MiB to GiB if original string was MiB formatted
    lifetime_writes_correct = float(lifetime_writes_org[:(len(lifetime_writes_org) - 3)])
    if lifetime_writes_org[(len(lifetime_writes_org) - 2)] == "M" and lifetime_writes_org[(len(lifetime_writes_org) - 1)] == "B":
        lifetime_writes_correct = float(lifetime_writes_correct / 1024)
    lifetime_writes_correct = float(lifetime_writes_correct)

    # Converts the raw collected data to more easily read formats (from bytes to MiB or GiB)
    inode_count_MiB = float(inode_count / 1024 / 1024)
    free_inodes_MiB = float(free_inodes / 1024 / 1024)
    inode_ratio = int((blocks_per_group / inodes_per_group) * block_size)
    inode_space = float((inode_count * inode_size) / 1024 / 1024 / 1024)
    block_count_GiB = float((block_count * block_size) / 1024 / 1024 / 1024)
    reserved_blocks_GiB = float((reserved_blocks * block_size) / 1024 / 1024 / 1024)
    
    # Whilst it looks like the 'used_blocks_GiB' calculation does not account for reserved disk space, it actually does
    # This is because the 'free_blocks' variable actually includes both user-available free space AND unused reserved disk space
    used_blocks_GiB = float(((block_count - free_blocks) * 4096) / 1024 / 1024 / 1024)
    free_blocks_GiB = float(((free_blocks - reserved_blocks) * block_size) / 1024 / 1024 / 1024)
    
    # Formula for theoretically max usable disk space = (1 - inode_size / inode_ratio - reserved blocks (in percentage form) / 100)
    max_usable_space = float(1 - inode_size / inode_ratio - round((reserved_blocks_GiB / block_count_GiB) * 100) / 100)
    total_usage_percent = float(100 - ((free_blocks / block_count) * 100))

    padding = ""
    all_values = {"Total inodes:": inode_count_MiB,
                  "Free inodes:": free_inodes_MiB,
                  "Inode size:": inode_size,
                  "Inode ratio:": inode_ratio,
                  "Inode table size:": inode_space,
                  "File system size:": block_count_GiB,
                  "Reserved space:": reserved_blocks_GiB,
                  "Used space:": used_blocks_GiB,
                  "Free space:": free_blocks_GiB,
                  "Lifetime writes:": lifetime_writes_correct
                  }

    all_prefixes = {"Total inodes:": "M",
                    "Free inodes:": "M",
                    "Inode size:": "",
                    "Inode ratio:": "",
                    "Inode table size:": "GiB",
                    "File system size:": "GiB",
                    "Reserved space:": "GiB",
                    "Used space:": "GiB",
                    "Free space:": "GiB",
                    "Lifetime writes:": "GiB"
                    }

    # Outputs an overview of the filesystem on the block device
    print("------------------------------------")
    print(f"{'Block device:':{padding}<21}", f"{dev_name:{padding}<8}")
    print(f"{'Mount point:':{padding}<21}", f"{user_input:{padding}<8}")
    print(f"{'File system:':{padding}<21}", f"{fs_type:{padding}<8}")
    print(f"{'Block size:':{padding}<21}", f"{block_size:{padding}<8}")
    print(f"{'Fragment size:':{padding}<21}", f"{fragment_size:{padding}<8}")
    print("------------------------------------")

    # Outputs all collected data that relates of the filesystem on the block device
    for entry in all_values.keys():
        print(f"{entry:{padding}<21}", f"{f'{all_values[entry]:.1f}':<9}", f"{all_prefixes[entry]:{padding}<3}")

    # Both of these percentages are relative to the total disk space of the examined file system
    print("------------------------------------")
    print(f"{'Total usable space:':{padding}<21}", f"{max_usable_space * 100:.1f}" + "%")
    print(f"{'Total space used:':{padding}<21}", f"{total_usage_percent:.1f}" + "%")
    print("------------------------------------")

path = user_input()
if path:
    dev_info(path)