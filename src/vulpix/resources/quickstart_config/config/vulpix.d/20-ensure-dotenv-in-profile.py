"""
this script is an example that checks whether you have the line `vulpix dotenv ...` in
your shell profile (see `vulpix dotenv --help` if you're confused).
"""

import logging
import re
from pathlib import Path

from vulpix.core import VulpixError, dirs, system

# define common script profiles for each supported shell
profiles_by_shell: dict[str, list[Path]] = {
    "sh": [
        Path.home() / ".profile",
        Path.home() / ".bashrc",
        Path.home() / ".bash_profile",
        Path.home() / ".zshrc",
        Path.home() / ".zprofile",
    ],
    "pwsh": [dirs.config("powershell") / "Microsoft.PowerShell_profile.ps1"],
}
if system.OS == "window":
    windows_profiles = [
        Path.home() / "Documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1",
        Path.home() / "Documents/PowerShell/Microsoft.PowerShell_profile.ps1",
    ]
    profiles_by_shell["pwsh"].extend(windows_profiles)


def check_profile(profile: Path, sh: str) -> bool:
    """checks a shell profile for the `vulpix dotenv {shell}` command."""

    if profile.exists():
        pattern = re.compile(f"vulpix\\s+dotenv\\s+{sh}")
        with open(profile, "r") as file:
            for line in file:
                if pattern.search(line):
                    return True
    return False


def main(logger: logging.Logger):
    found_profiles = False

    for shell, profiles in profiles_by_shell.items():
        if not any(p.exists() for p in profiles):
            continue

        found_profiles = True
        logger.debug(f"checking profiles: {profiles}")
        if not any(check_profile(p, shell) for p in profiles):
            logger.error(f"at least one {shell} profile exists but none source dotenv")
            logger.info("delete this script if you don't care")
            raise VulpixError("you should source the dotenv! (see `vulpix dotenv -h`)")

    if found_profiles:
        logger.info("dotenv sourced in profile(s)!")
    else:
        logger.info("no script profiles found")
