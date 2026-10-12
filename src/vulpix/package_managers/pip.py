"""
package manager for the pip package manager.

NOTE: it's recommended to use the `pipx`, `uv`, etc. package managers (TODO) instead of pip. the pip
manager is not very efficient since pip is yet to support parallel downloads/installs. not only
that, but `pip install ...` has to be reexecuted for each package since there's no option to ignore
missing/failed packages (causing the whole operation to be aborted, which is not ideal in the
context of vulpix because just one offending package in the blueprint would screw it all up).
"""

import sys

from vulpix.core import VulpixError, logging, tasks
from vulpix.package_managers import (
    InvalidPackage,
    ManagerTask,
    PackageDiff,
    PackageManager,
)
from vulpix.utils import LoggedCommand, in_virtual_env


def pip_cmd(*args: str) -> LoggedCommand:
    return LoggedCommand(sys.executable, "-m", "pip", *args)


def get_packages(logger: logging.Logger) -> list[str]:
    cmd = pip_cmd("list", "--format=freeze")
    cmd.run(logger, log_stdout=False)
    stdout = [l.strip() for l in cmd.stdout or [] if l.strip()]
    packages = [p.split("=", 1)[0] for p in stdout]
    logger.debug(f"all pip packages: {packages}")
    return packages


def get_top_level_packages(logger: logging.Logger) -> list[str]:
    cmd = pip_cmd("list", "--not-required", "--format=freeze")
    cmd.run(logger, log_stdout=False)
    stdout = [l.strip() for l in cmd.stdout or [] if l.strip()]
    packages = [p.split("=", 1)[0] for p in stdout]
    logger.debug(f"top pip packages: {packages}")
    return packages


@tasks.task_function
def install_package(package: str, logger: logging.Logger):
    pip_cmd("install", package).run(logger)


@tasks.task_function
def update_package(package: str, logger: logging.Logger):
    pip_cmd("install", "--upgrade", "--upgrade-strategy=eager", package).run(logger)


@tasks.task_function
def reinstall_package(package: str, logger: logging.Logger):
    pip_cmd("install", "--force-reinstall", package).run(logger)


@tasks.task_function
def uninstall_package(package: str, logger: logging.Logger):
    pip_cmd("uninstall", "--yes", package).run(logger)


task_by_verb = {
    "install": install_package,
    "update": update_package,
    "reinstall": reinstall_package,
    "uninstall": uninstall_package,
}


class PipManager(PackageManager):
    main_logger: logging.Logger

    def __init__(self):
        self.main_logger = logging.getLogger("main")

        # since this is meant to work as a system package manager, no venvs
        if in_virtual_env():
            raise VulpixError("cannot use 'pip' manager in virtual env")

        # make sure pip is installed
        pip_cmd("--version").run(self.main_logger, log_stdout=False)

    def check_packages(self, packages: list[str]) -> None:
        # super simple check; this way it accepts package names, version modifers, git repos, etc.
        for package in packages:
            if " " in package:
                raise InvalidPackage(package, manager="pip")

    def get_package_diff(self, blueprint_packages: list[str]) -> PackageDiff:
        diff = PackageDiff()

        top_level_installed = get_top_level_packages(self.main_logger)
        diff.to_uninstall = [
            p for p in top_level_installed if p not in blueprint_packages
        ]

        all_installed = get_packages(self.main_logger)
        for p in blueprint_packages:
            if p in all_installed:
                diff.to_update.append(p)
            else:
                diff.to_install.append(p)

        # don't pip uninstall pip!
        diff.to_uninstall = [p for p in diff.to_uninstall if p != "pip"]

        return diff

    @tasks.task_function
    def apply_changes(self, diff: PackageDiff, queue: tasks.ThreadedTaskQueue) -> None:
        tasks = [ManagerTask.uninstall(p, "pip") for p in diff.to_uninstall]
        tasks.extend([ManagerTask.reinstall(p, "pip") for p in diff.to_reinstall])
        tasks.extend([ManagerTask.install(p, "pip") for p in diff.to_install])
        tasks.extend([ManagerTask.update(p, "pip") for p in diff.to_update])

        # tasks have to be run synchronously (pip, i'm disappointed in you...)
        for task in tasks:
            task.run(queue, task_by_verb[task.verb], args=(task.package,))
            queue.wait_for_tasks([task.name])  # wait before continuing


package_manager_class = PipManager
