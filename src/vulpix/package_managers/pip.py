"""
package manager for the pip package manager.

NOTE: it's recommended to use the `pipx`, `uv`, etc. package managers (TODO) instead of pip. the pip
manager is not very efficient since pip is yet to support parallel downloads/installs. not only
that, but `pip install ...` has to be reexecuted for each package since there's no option to ignore
missing/failed packages (causing the whole operation to be aborted, which is not ideal in the
context of vulpix because just one offending package in the blueprint would screw it all up).
"""

import sys
from pathlib import Path

from vulpix.core import VulpixError, dirs, logging, system, tasks
from vulpix.package_managers import (
    ManagerTask,
    PackageDiff,
    PackageManager,
)
from vulpix.utils import LoggedCommand


class Venv:
    venv: Path
    logger: logging.Logger

    def _script(self, s: str) -> Path:
        if system.OS == "windows":
            subdir = "Scripts"
            s += ".exe"
        else:
            subdir = "bin"
        return self.venv / subdir / s

    def __init__(self, path: Path, logger: logging.Logger):
        self.venv = path
        self.logger = logger

    def exists(self) -> bool:
        required_paths = [self.venv, self._script("python"), self._script("pip")]
        return all(p.exists() for p in required_paths)

    def create(self):
        if self.exists():
            self.logger.debug("venv already exists")
            return

        try:
            self.logger.info(f"creating internal venv at '{self.venv}'")
            cmd = LoggedCommand(sys.executable, "-m", "venv", str(self.venv))
            cmd.run(self.logger)
        except VulpixError:
            raise VulpixError(f"could not create virtual env at {self.venv}")

        if not self.exists():
            raise VulpixError(
                f"virtual env created at {self.venv}, but no python/pip binaries"
            )

    def pip(self, *args: str) -> LoggedCommand:
        return LoggedCommand(str(self._script("pip")), *args)

    def get_packages(self) -> list[str]:
        if not self.exists():
            return []

        cmd = self.pip("list", "--format=freeze").run(self.logger, log_stdout=False)
        stdout = [l.strip() for l in cmd.stdout or [] if l.strip()]
        packages = [p.split("=", 1)[0] for p in stdout]
        self.logger.debug(f"all pip packages: {packages}")
        return packages

    def get_top_level_packages(self) -> list[str]:
        if not self.exists():
            return []

        cmd = self.pip("list", "--not-required", "--format=freeze").run(
            self.logger, log_stdout=False
        )
        stdout = [l.strip() for l in cmd.stdout or [] if l.strip()]
        packages = [p.split("=", 1)[0] for p in stdout]
        self.logger.debug(f"top pip packages: {packages}")
        return packages


@tasks.task_function
def install_package(package: str, venv: Venv, logger: logging.Logger):
    venv.pip("install", package).run(logger)


@tasks.task_function
def update_package(package: str, venv: Venv, logger: logging.Logger):
    venv.pip("install", "--upgrade", "--upgrade-strategy=eager", package).run(logger)


@tasks.task_function
def reinstall_package(package: str, venv: Venv, logger: logging.Logger):
    venv.pip("install", "--force-reinstall", package).run(logger)


@tasks.task_function
def uninstall_package(package: str, venv: Venv, logger: logging.Logger):
    venv.pip("uninstall", "--yes", package).run(logger)


task_by_verb = {
    "install": install_package,
    "update": update_package,
    "reinstall": reinstall_package,
    "uninstall": uninstall_package,
}


class PipManager(PackageManager):
    venv_path = dirs.VULPIX_DATA / "pip/.venv"
    venv: Venv

    def __init__(self):
        main_logger = logging.getLogger("main")
        self.venv = Venv(self.venv_path, main_logger)

        # make sure pip is installed
        try:
            LoggedCommand(sys.executable, "-m", "pip", "--version").run(
                main_logger, log_stdout=False
            )
        except VulpixError:
            raise VulpixError("pip module is required for 'pip' package manager")

    def check_packages(self, packages: list[str]) -> None:
        # defer package checking to the pip binary when running
        pass

    def get_package_diff(self, blueprint_packages: list[str]) -> PackageDiff:
        diff = PackageDiff()

        top_level_installed = self.venv.get_top_level_packages()
        diff.to_uninstall = [
            p for p in top_level_installed if p not in blueprint_packages
        ]

        all_installed = self.venv.get_packages()
        for p in blueprint_packages:
            if p in all_installed:
                diff.to_update.append(p)
            else:
                diff.to_install.append(p)

        # don't pip uninstall pip!
        diff.to_uninstall = [p for p in diff.to_uninstall if p != "pip"]

        return diff

    @tasks.task_function
    def apply_changes(
        self, diff: PackageDiff, logger: logging.Logger, queue: tasks.ThreadedTaskQueue
    ) -> None:
        self.venv.logger = logger
        self.venv.create()

        tasks = [ManagerTask.uninstall(p, "pip") for p in diff.to_uninstall]
        tasks.extend([ManagerTask.reinstall(p, "pip") for p in diff.to_reinstall])
        tasks.extend([ManagerTask.install(p, "pip") for p in diff.to_install])
        tasks.extend([ManagerTask.update(p, "pip") for p in diff.to_update])

        # tasks have to be run synchronously (pip, i'm disappointed in you...)
        for task in tasks:
            task.run(queue, task_by_verb[task.verb], args=(task.package, self.venv))
            queue.wait_for_tasks([task.name])  # wait before continuing


package_manager_class = PipManager
