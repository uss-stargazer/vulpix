from pathlib import Path

from vulpix.core import VulpixError, logging, system
from vulpix.package_managers.manual.packages import (
    run_external_script,
    simple_shell_wrapper,
)

WINDOWS_SCRIPT = str(Path(__file__).resolve().parent / "msys2.ps1")


def main(install_dir: str, logger: logging.Logger) -> list[str]:
    if system.OS != "windows":
        raise VulpixError("msys2 is only for windows")
    return run_external_script(WINDOWS_SCRIPT, install_dir, logger=logger)


if __name__ == "__main__":
    simple_shell_wrapper(main)
