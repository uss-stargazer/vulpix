"""package manager for the pipx package manager."""

from subprocess import CalledProcessError

from vulpix.core import VulpixError, logging, tasks
from vulpix.package_managers import (
    ManagerTask,
    PackageDiff,
    PackageManager,
)
from vulpix.utils import LoggedCommand


def pipx_cmd(*args: str) -> LoggedCommand:
    return LoggedCommand("pipx", *args)


def get_packages(logger: logging.Logger) -> list[str]:
    cmd = pipx_cmd("list", "--short").run(logger, log_stdout=False)
    stdout = [l.strip() for l in cmd.stdout or [] if l.strip()]
    packages = [p.split(" ", 1)[0] for p in stdout]
    logger.debug(f"pipx packages: {packages}")
    return packages


@tasks.task_function
def install_package(package: str, logger: logging.Logger):
    pipx_cmd("install", package).run(logger)


@tasks.task_function
def update_package(package: str, logger: logging.Logger):
    pipx_cmd("upgrade", package).run(logger)


@tasks.task_function
def reinstall_package(package: str, logger: logging.Logger):
    pipx_cmd("reinstall", package).run(logger)


@tasks.task_function
def uninstall_package(package: str, logger: logging.Logger):
    pipx_cmd("uninstall", package).run(logger)


task_by_verb = {
    "install": install_package,
    "update": update_package,
    "reinstall": reinstall_package,
    "uninstall": uninstall_package,
}


class PipxManager(PackageManager):
    main_logger: logging.Logger

    def __init__(self):
        self.main_logger = logging.getLogger("main")

        # make sure pip is installed
        try:
            pipx_cmd("--version").run(self.main_logger, log_stdout=False)
        except CalledProcessError:
            raise VulpixError("pipx command is required for 'pipx' package manager")

    def check_packages(self, packages: list[str]) -> None:
        # defer package checking to actual pipx task
        pass

    def get_package_diff(self, blueprint_packages: list[str]) -> PackageDiff:
        diff = PackageDiff()
        installed = get_packages(self.main_logger)

        for p in blueprint_packages:
            if p in installed:
                diff.to_update.append(p)
            else:
                diff.to_install.append(p)
        diff.to_uninstall = [p for p in installed if p not in blueprint_packages]

        return diff

    @tasks.task_function
    def apply_changes(self, diff: PackageDiff, queue: tasks.ThreadedTaskQueue) -> None:
        tasks = [ManagerTask.uninstall(p, "pipx") for p in diff.to_uninstall]
        tasks.extend([ManagerTask.reinstall(p, "pipx") for p in diff.to_reinstall])
        tasks.extend([ManagerTask.install(p, "pipx") for p in diff.to_install])
        tasks.extend([ManagerTask.update(p, "pipx") for p in diff.to_update])

        for task in tasks:
            task.run(queue, task_by_verb[task.verb], args=(task.package,))


package_manager_class = PipxManager
