"""makes sure that the vulpix executable is available outside of the current shell session."""

import os
import shutil
from pathlib import Path

from vulpix.core import VulpixError, logging, system
from vulpix.utils import link, in_virtual_env


def get_vulpix_bin() -> Path:
    vulpix_path = shutil.which("vulpix")
    if not vulpix_path:
        raise VulpixError(
            "cannot find the 'vulpix' binary... how are you running this?"
        )

    return Path(vulpix_path)


def ensure_vulpix_windows(vulpix_path: Path, logger: logging.Logger):
    """adds the parent dir of vulpix.exe to PATH in environmental var registry"""

    import winreg

    vulpix_bin_dir = vulpix_path.parent

    if system.IS_ROOT:
        reg_key = winreg.HKEY_LOCAL_MACHINE
        reg_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    else:
        reg_key = winreg.HKEY_CURRENT_USER
        reg_path = r"Environment"
    logger.debug(f"editing PATH env var in registry: {reg_key} {reg_path}")

    with winreg.OpenKey(
        reg_key, reg_path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE
    ) as key:
        try:
            path_var, data_type = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            path_var = ""
            data_type = winreg.REG_EXPAND_SZ
        logger.debug(f"existing PATH: {path_var}")

        paths = [os.path.normpath(p).lower() for p in path_var.split(";") if p]
        if os.path.normpath(vulpix_bin_dir).lower() in paths:
            return

        sep = ";" if path_var and not path_var.startswith(";") else ""
        path_var = os.path.normpath(vulpix_bin_dir) + sep + path_var
        logger.debug(f"edited PATH: {path_var}")
        winreg.SetValueEx(key, "Path", 0, data_type, path_var)


def ensure_vulpix_linux(vulpix_path: Path, logger: logging.Logger):
    """makes sure vulpix is symlinked to standard bin location"""

    bin_dir = Path("/usr/local/bin") if system.IS_ROOT else Path.home() / ".local/bin"
    if not bin_dir.exists():
        raise VulpixError(f"expected posix bin dir to exist: {bin_dir}")

    if vulpix_path.parent.samefile(bin_dir):
        return

    vulpix_bin = bin_dir / "vulpix"
    logger.debug(f"linking {vulpix_path} to {vulpix_bin}")
    link(vulpix_path, vulpix_bin, logger)
    vulpix_bin.chmod(0o755)


def ensure_vulpix(logger: logging.Logger):
    if in_virtual_env():
        logger.warn("cannot ensure vulpix will be avilable because you're in a venv")
        return

    vulpix_path = get_vulpix_bin()
    logger.debug(f"got vulpix at: {vulpix_path}")

    f = ensure_vulpix_windows if system.OS == "windows" else ensure_vulpix_linux
    f(vulpix_path, logger)
