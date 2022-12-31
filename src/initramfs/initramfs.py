import os
import shutil
import subprocess
import pathlib

from log import blog

TARGET_FILE = "acacia-initrd.img"

WORK_DIRECTORY = "initramfsbuild"

BASE_FS = [ "dev", "run", "sys", "proc", "usr", "etc" ]
USR_SUB = [ "bin", "lib", "sbin", "lib64" ]
USR_LIB_SUB = [ "firmware", "modules", "systemd" ]
ETC_SUB = [ "modprobe.d", "udev" ]

# udevd -> /usr/lib/systemd-udevd
BINFILES = ["bash", "cat", "cp", "dd", "killall", "ls", "mkdir", "mknod", "mount", "fgrep", "find", "egrep", "sed", "xargs", "grep", "umount", "sed", "sleep", "ln", "rm", "uname", "readlink", "basename", "udevadm", "kmod"]
SBINFILES = ["blkid", "switch_root"]

# required kernel modules
KERNEL_MODULES = [ "ext4", "virtio_net", "sr_mod", "usbhid", "loop", "cdrom", "net_failover", "ata_generic", "failover", "virtio_scsi", "pata_acpi", "virtio_balloon", "serio_raw", "atkbd", "libps2", "i8042", "virtio_pci", "floppy", "virtio_pci_modern_dev", "ata_piix", "serio", "hid-generic", "usbhid", "atkbd", "squashfs", "iso9660", "overlay" ]

def touch_file(file):
    with open(file, "w", encoding="utf-8") as f:
        pass

def copy_with_deps(buildroot, binfile, deps_list):
    blog.info("Copying binary {} with dependencies: {} ..".format(binfile, deps_list))

    binpath = os.path.relpath(binfile, start=buildroot)

    blog.info("Will copy {} -> {} ".format(binfile, os.path.join(WORK_DIRECTORY, binpath)))

    shutil.copy(binfile, os.path.join(WORK_DIRECTORY, binpath))

    for dep in deps_list:
        rel_path = os.path.relpath(dep, start=buildroot)

        if(os.path.exists(os.path.join(WORK_DIRECTORY, rel_path))):
            continue

        blog.info("Will copy {} -> {} ".format(dep, os.path.join(WORK_DIRECTORY, rel_path)))
        shutil.copy(dep, os.path.join(WORK_DIRECTORY, rel_path))


# find a file
def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None

# uses ldd to get all dependencies of a given dynamic binary
def get_dependencies(buildroot, binfile):
    blog.info("Calculating dependencies for {}".format(binfile))

    env = {'LD_LIBRARY_PATH': '/usr/lib:/usr/lib64'}
    bin_path = "/" + os.path.relpath(binfile, start=buildroot)
    proc = subprocess.run(['/sbin/chroot', buildroot, 'ldd', bin_path], stdout=subprocess.PIPE, env=env)

    deps = proc.stdout.decode().split("\n")

    libs = [ ]

    for d in deps:
        # skip pseudo libraries and libsystemd
        if("linux-vdso.so.1" in d or "linux-gate.so.1" in d):
            continue
        
        split = d.strip().split("=>") 
        if(len(split) == 2):
            dep_str = split[1].strip().split(" ")[0].strip()
            dependency = os.path.join(buildroot, dep_str[1:len(dep_str)])
            libs.append(dependency)
    
    blog.info("Dependencies for {} are: {}".format(binfile, libs))
    return libs    
 

def create_initramfs(buildroot, kname, kver, bindir):
    kmod_dir = os.path.join(buildroot, "usr/lib/modules/{}".format(kver))

    if(not os.path.exists(kmod_dir)):
        blog.error("No kernel modules directory found for given kernel version.")
        return -1

    blog.info("Creating temporary initramfs build directory..")
    
    # probaly CTRL+C, clean up..
    if(os.path.exists(WORK_DIRECTORY)):
        blog.warn("Removing old work directory..")
        shutil.rmtree(WORK_DIRECTORY)

    os.mkdir(WORK_DIRECTORY)
    
    # base directory structure
    for path in BASE_FS:
        target = os.path.join(WORK_DIRECTORY, path)
        blog.info("Creating {}".format(target))
        os.mkdir(target)
    
    usr_path = os.path.join(WORK_DIRECTORY, "usr")
    for path in USR_SUB:
        target = os.path.join(usr_path, path)
        blog.info("Creating {}".format(target))
        os.mkdir(target)
    
    lib_path = os.path.join(usr_path, "lib")
    for path in USR_LIB_SUB:
        target = os.path.join(lib_path, path)
        blog.info("Creating {}".format(target))
        os.mkdir(target)
   
    etc_path = os.path.join(WORK_DIRECTORY, "etc")
    for path in ETC_SUB:
        target = os.path.join(etc_path, path)
        blog.info("Creating {}".format(target))
        os.mkdir(target)

    # symlinks
    blog.info("Creating symlinks..")
    os.symlink("usr/bin", os.path.join(WORK_DIRECTORY, "bin"))
    os.symlink("usr/lib", os.path.join(WORK_DIRECTORY, "lib"))
    os.symlink("usr/sbin", os.path.join(WORK_DIRECTORY, "sbin"))
    os.symlink("usr/lib64", os.path.join(WORK_DIRECTORY, "lib64"))

    #symlink bash -> sh
    os.symlink("/usr/bin/bash", os.path.join(WORK_DIRECTORY, "usr/bin/sh"))

    # mk null and console
    blog.info("Creating device nodes..")
    os.system("mknod -m 640 {} c 5 1".format(os.path.join(WORK_DIRECTORY, "dev/console")))
    os.system("mknod -m 664 {} c 5 1".format(os.path.join(WORK_DIRECTORY, "dev/null")))
    
    blog.info("Copying udev configuration..")
    try:
        # copy udev.conf from buildroot
        shutil.copy(os.path.join(buildroot, "etc/udev/udev.conf"), os.path.join(WORK_DIRECTORY, "etc/udev/udev.conf"))
        # rules.d
        shutil.copytree(os.path.join(buildroot, "etc/udev/rules.d"), os.path.join(WORK_DIRECTORY, "etc/udev/rules.d"))
    except FileNotFoundError as ex:
        blog.error("Could not find required udev configuration files: {}".format(ex))
        return -1

    # copy firmware, if it exists..
    if(os.path.exists(os.path.join(buildroot, "usr/lib/firmware"))):
        blog.info("Copying linux-firmware..")
        shutil.copytree(os.path.join(buildroot, "usr/lib/firmware"), os.path.join(WORK_DIRECTORY, "usr/lib/firmware"))
    
    if(not os.path.exists(os.path.join(bindir, "init"))):
       blog.error("No init binary available.")
       return -1
    
    blog.info("Copying init binary..")
    shutil.copy(os.path.join(bindir, "init"), os.path.join(WORK_DIRECTORY, "init"))
    
    blog.info("Writing /loadmodules..")

    with open(os.path.join(WORK_DIRECTORY, "loadmodules"), "w+") as lm:
        f_entry = True
        lm.write("KMODULES=(")

        for mod in KERNEL_MODULES:
            if(f_entry):
                f_entry = False
                lm.write(mod)
            else:
                lm.write(" " + mod)

        lm.write(")\n")

    blog.info("Copying /usr/bin binaries..")
    for b in BINFILES:
        b_path = os.path.join(buildroot, os.path.join("usr/bin", b))
        copy_with_deps(buildroot, b_path, get_dependencies(buildroot, b_path))

    blog.info("Copying /usr/sbin binaries..")
    for b in SBINFILES:
        b_path = os.path.join(buildroot, os.path.join("usr/sbin", b))
        copy_with_deps(buildroot, b_path, get_dependencies(buildroot, b_path))

    blog.info("Copying systemd-udevd..")
    sd_udevd = "usr/lib/systemd/systemd-udevd"

    sd_udevd_path = os.path.join(buildroot, sd_udevd)
    sd_udevd_deps = get_dependencies(buildroot, sd_udevd_path)
    
    shutil.copy(os.path.join(buildroot, sd_udevd), os.path.join(WORK_DIRECTORY, sd_udevd))

    for dep in sd_udevd_deps:
        src = dep

        rel_path = os.path.relpath(src, start="buildroot")
        dst = os.path.join(WORK_DIRECTORY, rel_path)

        if(os.path.exists(dst)):
            continue

        blog.info("Copying library {} -> {}..".format(src, dst))
        shutil.copy(src, dst)

    blog.info("Symlinking /usr/bin/kmod. lsmod, insmod, modprobe")
    os.symlink("/usr/bin/kmod", os.path.join(WORK_DIRECTORY, "usr/bin/lsmod"))
    os.symlink("/usr/bin/kmod", os.path.join(WORK_DIRECTORY, "usr/bin/insmod"))
    os.symlink("/usr/bin/kmod", os.path.join(WORK_DIRECTORY, "usr/bin/modprobe"))
   
    blog.info("Copying udev and systemd configs")
    shutil.copytree(os.path.join(buildroot, "usr/lib/udev"), os.path.join(WORK_DIRECTORY, "usr/lib/udev"))
    #shutil.copytree(os.path.join(buildroot, "usr/lib/systemd"), os.path.join(WORK_DIRECTORY, "usr/lib/systemd"))
    
    blog.info("Copying kernel modules...")
    shutil.copytree(kmod_dir, os.path.join(WORK_DIRECTORY, "usr/lib/modules/{}".format(kver)), symlinks=False, ignore_dangling_symlinks=True)

    blog.info("Compressing initrd..")
    os.system("(cd {}; find . | cpio -o -H newc --quiet | gzip -9) > {}".format(WORK_DIRECTORY, TARGET_FILE))

    blog.info("Created initramfs.")
    return 0

