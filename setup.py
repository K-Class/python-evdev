import os
import sys
import textwrap
from pathlib import Path
from setuptools import setup, Extension, Command
from setuptools.command import build_ext as _build_ext
from subprocess import run, CalledProcessError


curdir = Path(__file__).resolve().parent
ecodes_path = curdir / "evdev/ecodes.c"


def create_ecodes(headers=None):
    if not headers:
        include_paths = set()
        cpath = os.environ.get("CPATH", "").strip()
        c_inc_path = os.environ.get("C_INCLUDE_PATH", "").strip()

        if cpath:
            include_paths.update(cpath.split(":"))
        if c_inc_path:
            include_paths.update(c_inc_path.split(":"))

        include_paths.add("/usr/include")
        files = ["linux/input.h", "linux/input-event-codes.h", "linux/uinput.h"]
        headers = [os.path.join(path, file) for path in include_paths for file in files]

    # Filtrele ve mevcut başlık dosyalarını bul
    headers = [header for header in headers if os.path.isfile(header)]
    if not headers:
        msg = """\
        The 'linux/input.h' and 'linux/input-event-codes.h' include files
        are missing. You will have to install the kernel header files in
        order to continue:

            dnf install kernel-headers-$(uname -r)
            apt-get install linux-headers-$(uname -r)
            emerge sys-kernel/linux-headers
            pacman -S kernel-headers

        If they are installed in a non-standard location, use the '--evdev-headers' option.
        """
        sys.stderr.write(textwrap.dedent(msg))
        sys.exit(1)

    # Komutu çalıştır ve hata yönetimi ekle
    try:
        print(f"Writing {ecodes_path} using headers: {' '.join(headers)}")
        with ecodes_path.open("w") as fh:
            cmd = [sys.executable, "evdev/genecodes.py", *headers]
            run(cmd, check=True, stdout=fh)
    except CalledProcessError as e:
        sys.stderr.write(f"Error during code generation: {e}\n")
        sys.exit(1)


class build_ecodes(Command):
    description = "Generate ecodes.c"
    user_options = [("evdev-headers=", None, "Paths to input subsystem headers")]

    def initialize_options(self):
        self.evdev_headers = None

    def finalize_options(self):
        if self.evdev_headers:
            self.evdev_headers = self.evdev_headers.split(":")

    def run(self):
        create_ecodes(self.evdev_headers)


class build_ext(_build_ext.build_ext):
    def has_ecodes(self):
        if ecodes_path.exists():
            print("ecodes.c already exists ... skipping build_ecodes")
        return not ecodes_path.exists()

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)
        _build_ext.build_ext.run(self)

    sub_commands = [("build_ecodes", has_ecodes)] + _build_ext.build_ext.sub_commands


cflags = ["-std=c++23", "-Wno-error=declaration-after-statement"]
setup(
    ext_modules=[
        Extension("evdev._input", sources=["evdev/input.c"], extra_compile_args=cflags),
        Extension("evdev._uinput", sources=["evdev/uinput.c"], extra_compile_args=cflags),
        Extension("evdev._ecodes", sources=["evdev/ecodes.c"], extra_compile_args=cflags),
    ],
    cmdclass={
        "build_ext": build_ext,
        "build_ecodes": build_ecodes,
    },
)
