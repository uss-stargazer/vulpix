import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from vulpix import config_managers, package_managers, utils
from vulpix.cli import bootstrap, ensurevulpix, logging
from vulpix.cli.task_section import TaskSection, emotes, term
from vulpix.core import VulpixError, blueprint, dirs, dotenv, dotfiles
from vulpix.core.manager_tasks import (
    ManagerTask,
    TaskStatusDict,
    completed_package_tasks,
)
from vulpix.core.managers import Package

failure_s, success_s = term.red("failure"), term.green("success")


type RegexSearch = Callable[[str], bool]
type PackageDiffFilter = Callable[
    [str, package_managers.PackageDiff], package_managers.PackageDiff
]
type ConfigPackageFilter = Callable[[list[Package]], list[Package]]


def filter_package_names(
    names: list[str],
    manager: str,
    rg: list[re.Pattern[str]],
    negate: bool = False,
) -> list[str]:
    if not negate:
        return [n for n in names if Package(n, manager).check_match(*rg)]
    return [n for n in names if not Package(n, manager).check_match(*rg)]


def filter_packages(
    packages: list[Package], rg: list[re.Pattern[str]]
) -> list[Package]:
    return [p for p in packages if p.check_match(*rg)]


def build_package_filter(
    general: re.Pattern[str],
    install: re.Pattern[str] | None,
    update: re.Pattern[str] | None,
    apply: re.Pattern[str] | None,
    clean: re.Pattern[str] | None,
    reinstall: re.Pattern[str] | None,
) -> PackageDiffFilter:
    def _diff_filter(
        manager: str, diff: package_managers.PackageDiff
    ) -> package_managers.PackageDiff:
        # reinstall takes precedent (this is also different since we are telling it to reinstall
        # instead of install/update, rather than just filtering)
        if reinstall is not None:
            reinstall_pkgs = filter_package_names(
                [*diff.to_install, *diff.to_update], manager, rg=[reinstall]
            )
            diff.to_install = filter_package_names(
                diff.to_install, manager, rg=[reinstall], negate=True
            )
            diff.to_update = filter_package_names(
                diff.to_update, manager, rg=[reinstall], negate=True
            )
            diff.to_reinstall.extend(reinstall_pkgs)

        # then clean and apply filters
        def _filter(packages: list[str], *patterns: re.Pattern[str] | None):
            if all(p is None for p in patterns):
                packages[:] = []
            else:
                rg = [p for p in patterns if p is not None]
                packages[:] = filter_package_names(packages, manager, [*rg, general])

        _filter(diff.to_uninstall, clean)
        _filter(diff.to_install, install, apply)
        _filter(diff.to_update, update, apply)

        return diff

    return _diff_filter


def build_config_filter(
    general: re.Pattern[str],
    config: re.Pattern[str],
    package_management_tasks: TaskStatusDict | None,
) -> ConfigPackageFilter:
    def _filter(packages: list[Package]) -> list[Package]:
        if package_management_tasks:
            package_tasks = {
                Package(t.package, t.manager): status
                for t, status in package_management_tasks.items()
                if t.package
            }
            packages = [p for p in packages if package_tasks.get(p)]

        return filter_packages(packages, rg=[config, general])

    return _filter


def flatten_packages_by_manager(
    pbm: dict[str, list[str]],
) -> list[Package]:
    flattened: list[Package] = []
    for manager, packages in pbm.items():
        flattened.extend([Package(p, manager) for p in packages])
    return flattened


def task_summary(tasks: TaskStatusDict) -> str:
    failed = [
        f"  - {task.name} ({failure_s})"
        for task, success in tasks.items()
        if not success
    ]
    succeeded = [
        f"  - {task.name} ({success_s})" for task, success in tasks.items() if success
    ]
    failed.sort()
    succeeded.sort()
    return "\n".join([*failed, *succeeded]) + "\n"


def print_section_summary(tasks: TaskStatusDict, logger: logging.Logger):
    if len(tasks) > 0:
        tasks_failed = any(not status for status in tasks.values())
        if tasks_failed:
            logger.warning(
                "some manager tasks failed (`vulpix replay <task>` to check logs)"
            )

        em = emotes["failure"] if tasks_failed else emotes["success"]
        print(f"[{em}] summary:\n" + task_summary(tasks))


class Cli(argparse.Namespace):
    type Command = Literal["sync", "dotfiles", "blueprint", "dotenv", "replay"]

    logger: logging.Logger

    # generic options
    help: bool = False
    version: bool = False
    verbose: bool = False
    blueprint: str | None = None
    edit_blueprint: bool = False
    whatif: bool = False
    command: Command | None = None

    # sync command
    general: re.Pattern[str]
    install: re.Pattern[str] | None = None
    update: re.Pattern[str] | None = None
    apply: re.Pattern[str] | None = None
    clean: re.Pattern[str] | None = None
    reinstall: re.Pattern[str] | None = None
    config: re.Pattern[str] | None = None

    # dotfiles command
    path: str | None = None

    # replay command
    log: re.Pattern[str] | None = None
    list: bool = False

    # dotenv command
    shell: Literal["sh", "pwsh"] | None

    @property
    def sync_options(self):
        return [
            self.install,
            self.update,
            self.apply,
            self.clean,
            self.reinstall,
            self.config,
        ]

    def init_console_logging(self):
        """this is the minimium required logger after settings have been populated"""
        self.logger = logging.getLogger("main")
        logging.attach_console_logging(self.logger, verbose=self.verbose)

        # TaskSection settings
        TaskSection.verbose_loggers = self.verbose
        if self.no_fullscreen:
            TaskSection.alt_screen = False

    def init_file_logging(self):
        """
        this initializes a main portion of the cli by clearing log files and attaching main log
        file. this is seperate from __init__() because some subcommands require logs... those
        subcommands just have fileless main logging.
        """
        logging.clear_logs()
        logging.attach_log_file(self.logger)

    # cli utils -----------------------------------------------------------------------------------

    def get_blueprint_path(self) -> Path:
        default_blueprint_path = (
            dirs.VULPIX_CONFIG.resolve(strict=False) / "blueprint.yaml"
        )
        blueprint_path = default_blueprint_path
        if self.blueprint is not None:
            blueprint_path = Path(self.blueprint)
        self.whatif_log(f"blueprint: {blueprint_path}")

        # if --blueprint not passed as arg, then run bootstrap checks
        if blueprint_path.resolve(strict=False) == default_blueprint_path:
            self.logger.debug("running bootstrap checks")

            # if the config dir isn't right, prompt to use quickstart config
            bootstrap.run_quickstart_config_check(self.logger)

            # if vulpix bootstrapped script was just run, add packages to blueprint
            bootstrap.run_bootstrapped_packages_check(blueprint_path, self.logger)

            # ensure vulpix will be available in the future
            ensurevulpix.ensure_vulpix(self.logger)

        if not blueprint_path.exists():
            raise VulpixError(f"expected blueprint file at '{blueprint_path}'")
        return blueprint_path

    _cached_bp: blueprint.ExpandedBlueprint | None = None

    def get_expanded_blueprint(self) -> blueprint.ExpandedBlueprint:
        if self._cached_bp:
            return self._cached_bp

        path = self.get_blueprint_path()
        bp = blueprint.datafile(path, self.logger).loadf()
        expanded_bp = blueprint.ExpandedBlueprint.expand(bp, path, self.logger)

        self.logger.debug(str(expanded_bp))
        self._cached_bp = expanded_bp
        return expanded_bp

    def whatif_log(self, log: str):
        if self.whatif:
            self.logger.info(log)
        else:
            self.logger.debug(log)

    def package_manage_section(self, diff_filter: PackageDiffFilter) -> TaskStatusDict:
        bp = self.get_expanded_blueprint()
        if len(bp.packages) == 0:
            self.logger.warning(
                "no package managers in blueprint, skipping package management"
            )
            return {}

        manager_diffs: dict[str, package_managers.PackageDiff] = {}
        for manager_id, packages in bp.packages.items():
            manager = package_managers.get_manager(manager_id)
            diff = manager.get_package_diff(packages)
            diff.remove_dups()
            self.logger.debug(f"(og) {manager_id}: {diff}")

            diff = diff_filter(manager_id, diff)
            self.whatif_log(f"{manager_id}: {diff}")
            if diff.is_empty():
                self.logger.warning(
                    f"no regex matches, skipping '{manager_id}' manager"
                )
                continue

            manager_diffs[manager_id] = diff

            # trip and abort if too much uninstalls
            abort_threshold = bp.settings.abort_uninstall_threshold or 0
            n_uninstall = len(diff.to_uninstall)
            if n_uninstall >= abort_threshold:
                self.logger.error(
                    f"'{manager_id}' manager wants to uninstall {n_uninstall} packages"
                )
                raise VulpixError(
                    f"abort_uninstall_threshold ({abort_threshold}) tripped"
                )

        if self.whatif:
            return {}

        with TaskSection(
            "package management",
            bp,
            logger=self.logger,
            emote=emotes["section"],
        ) as section:
            for manager_id, diff in manager_diffs.items():
                manager = package_managers.get_manager(manager_id)
                task = ManagerTask("package_manager", manager_id)
                task.run(section, manager.apply_changes, args=(diff,))

        return completed_package_tasks(section.completed_tasks)

    def package_config_section(
        self, package_filter: ConfigPackageFilter
    ) -> TaskStatusDict:
        bp = self.get_expanded_blueprint()
        if len(bp.configs) == 0:
            self.logger.warning(
                "no config managers in blueprint, skipping config management"
            )
            return {}

        # we give packages to the config managers as a hint of what to config
        packages = list(set(flatten_packages_by_manager(bp.packages)))
        self.logger.debug(f"(og) config packages: {packages}")
        packages = package_filter(packages)
        self.whatif_log(f"config packages: {packages}")
        self.whatif_log(f"config managers: {list(bp.configs.keys())}")
        if len(packages) == 0:
            self.logger.warning(
                "no packages are visible to config (hidden by filtering or failure); running config anyways"
            )

        if self.whatif:
            return {}

        with TaskSection(
            "config management",
            bp,
            logger=self.logger,
            emote=emotes["section"],
        ) as section:
            for manager_id, config in bp.configs.items():
                manager = config_managers.get_manager(manager_id)
                task = ManagerTask("config_manager", manager_id)
                task.run(section, manager.apply_config, args=(config, packages))

        return completed_package_tasks(section.completed_tasks)

    # command methods ------------------------------------------------------------------------------

    def sync_command(self):
        self.init_file_logging()

        # check core files first
        dotenv.datafile.loadf()
        self.get_expanded_blueprint()

        if all(o is None for o in self.sync_options):
            # no opts = --clean --apply --config
            self.clean = re.compile(".*")
            self.apply = re.compile(".*")
            self.config = re.compile(".*")
            self.logger.debug(f"expanded --clean --apply --config")
        package_manage_options = self.sync_options[:-1]

        # package management
        tasks: TaskStatusDict | None = None
        if any(o is not None for o in package_manage_options):
            package_filter = build_package_filter(self.general, *package_manage_options)
            tasks = self.package_manage_section(package_filter)
            print_section_summary(tasks, self.logger)

        # config management
        if self.config is not None:
            config_filter = build_config_filter(self.general, self.config, tasks)
            config_tasks = self.package_config_section(config_filter)
            print_section_summary(config_tasks, self.logger)
            tasks = utils.merge_dicts(tasks or {}, config_tasks)

        # write tasks statuses for replay cmd
        status = logging.TaskStatusLog({t.name: s for t, s in (tasks or {}).items()})
        logging.task_status_datafile.dumpf(status)

    def dotfiles_command(self):
        self.init_file_logging()

        dotfiles_path = self.path
        if not dotfiles_path:
            bp = self.get_expanded_blueprint()
            if bp.dotfiles:
                dotfiles_path = bp.dotfiles
        if not dotfiles_path:
            raise VulpixError("could not locate dotfiles; specify in blueprint or arg")
        dotfiles_path = Path(dotfiles_path)
        font_dir = dotfiles_path / "fonts"  # optional

        # get dotfiles
        self.logger.info(f"finding dotfiles at '{dotfiles_path}'")
        links = dotfiles.iter_dotfiles(
            dotfiles_path, ignore_paths=[font_dir], logger=self.logger
        )
        if len(links) == 0:
            self.logger.warning("no dotfiles found")

        # check existing link targets
        if not self.whatif:
            existing_targets = []
            for item, link in links:
                if link.exists():
                    try:
                        utils.rm_link(link)
                    except OSError, ValueError:
                        self.logger.debug("link already exists", exc_info=True)
                        existing_targets.append(link)
            if len(existing_targets) > 0:
                print()  # style
                self.logger.warning(
                    "the following items will be overwritting and replaced by links:"
                )
                print("\n".join(["  - " + str(t) for t in existing_targets]) + "\n")
                if not utils.verify("are you sure you want to continue?"):
                    raise VulpixError("dotfiles aborted")

                for target in existing_targets:
                    utils.rm_fr(target)
                print()  # style

        # link dotfiles
        _max_item_len = max(len(utils.pretty_path(l[0])) for l in links)
        for item, link in links:
            self.logger.info(utils.pretty_link_log(item, link, _max_item_len))
            if not self.whatif:
                utils.link(item, link, self.logger)

        # install fonts
        if font_dir.exists() and font_dir.is_dir():
            d = utils.pretty_path(font_dir)
            if self.whatif:
                self.logger.info(f"would install fonts from {d}")
            else:
                self.logger.info(f"installing fonts from {d}")
                dotfiles.install_fonts(font_dir, self.logger)

    def blueprint_command(self):
        self.init_file_logging()
        utils.open_in_editor(self.get_blueprint_path(), self.logger)

    def dotenv_command(self):
        self.init_file_logging()

        if self.shell is None:
            dotenv.datafile.loadf()  # check validity
            utils.open_in_editor(dotenv.path, self.logger)
            return

        self.logger.debug(f"converting '{dotenv.path}'")
        with dotenv.datafile as env:
            match self.shell:
                case "sh":
                    source = env.as_sh()
                case "pwsh":
                    source = env.as_pwsh()
                case _:
                    raise ValueError("invalid shell option")
        print(source)

    def replay_command(self):
        log_names = logging.get_log_file_names()
        if self.list:
            for name in log_names:
                print(name)
            return

        if len(log_names) == 0:
            self.logger.warning("no log files")
            return

        if self.log:
            log_names = [l for l in log_names if self.log.search(l)]
            if len(log_names) == 0:
                raise VulpixError("no log files matching regex")

        if len(log_names) == 1:
            log_name = log_names[0]
        else:
            task_status = logging.task_status_datafile.loadf().tasks

            def choice_line(log_name: str) -> str:
                task_name = Path(log_name).stem
                if task_name in task_status:
                    success = task_status[task_name]
                    return f"{log_name} ({success_s if success else failure_s})"
                return log_name

            choices = [choice_line(l) for l in log_names]
            log_name = utils.prompt_choice("select log", log_names, choices)

        if not self.verbose:
            self.logger.warning("use --verbose to see debug logs")
        self.logger.info(f"replaying '{log_name}' log:\n")
        logging.console_log_to(sys.stdout, self.logger)  # temp log to stdout
        logging.replay_log_file(log_name, self.logger)
        logging.console_log_to(sys.stderr, self.logger)

    # main ----------------------------------------------------------------------------------------

    def main(self) -> int:
        self.init_console_logging()
        self.logger.debug(str(self))

        # intercept all errors so the terminal doesn't get cluttered (unless verbose)
        try:
            match self.command:
                case "sync":
                    command = self.sync_command
                case "dotfiles":
                    command = self.dotfiles_command
                case "blueprint":
                    command = self.blueprint_command
                case "dotenv":
                    command = self.dotenv_command
                case "replay":
                    command = self.replay_command
                case _:
                    raise VulpixError("invalid command")

            command()
        except VulpixError as e:
            self.logger.critical(e.message)
            return e.exit_status
        except Exception:
            self.logger.debug("exception raised", exc_info=True)
            self.logger.warning(f"see error details at '{dirs.VULPIX_LOG}'")
            self.logger.critical("an unexpected, uncaught error occured")
            return 1

        return 0
