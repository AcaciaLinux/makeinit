import os
import argparse

from log import blog
from initramfs import initramfs

def main():
    # init blog
    blog.initialize()
    
    # setup argparser
    argparser = argparse.ArgumentParser(description="The AcaciaLinux initramfs utility.")
    argparser.add_argument("-k", "--kernel", help="Kernel version to use for the initramfs", required=True)
    args = argparser.parse_args()

    kernel_version = args.kernel
    
    if(not os.path.exists(os.path.join("/usr/lib/modules/", kernel_version))):
        blog.error("No kernel module directory found for version {}".format(kernel_version))
        return -1

    blog.info("Making initramfs for {}..".format(kernel_version))
    
    initramfs.TARGET_FILE = "/boot/acacia-initramfs-{}.img".format(kernel_version)
    initramfs.create_initramfs("/", "vmlinuz-linux-lts", kernel_version, "bin")

if(__name__ == "__main__"):
    main()
