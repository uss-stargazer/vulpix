"""
operations on vulpix's dotenv file (located at $CONFIG/.env.json).

the dotenv file is the bridge between vulpix and the system environment. it is (ideally) sourced in
the user shell profile (using the vulpix cli). therefore, the dotenv represents the subset of system
env vars that are used/exported by vulpix or any vulpix managers (package or config).

a good example is is the "manual" package manager, which appends software bin paths to dotenv's PATH
var so the user can access software binaries.

NOTE: it's a json file since it should be platform agnostic. the vulpix cli parses the json into
whatever shell script language that wants to source it.
"""

from dataclasses import dataclass, field
from json import JSONDecodeError

from dacite import DaciteError

from vulpix.core import VulpixError, dirs, logging, system
from vulpix.utils import DataclassFile

_default_pwsh_list_sep = ";" if system.OS == "windows" else ":"


@dataclass
class Dotenv:
    # when sourced, sets the overrides the env vars
    env: dict[str, str | list[str]] = field(default_factory=dict)

    # when sourced, appends to existing env vars
    append_env: dict[str, str | list[str]] = field(default_factory=dict)

    PATH: list[str] = field(default_factory=list)

    def prepend_path(self, path: str):
        if path not in self.PATH:
            self.PATH.insert(0, path)

    # script language conversion ------------------------------------------------------------------

    def as_sh(self, list_sep: str = ":") -> str:
        # env
        lines = [
            f'export {name}="{list_sep.join(val)}"'
            if isinstance(val, list)
            else f'export {name}="{val}"'
            for name, val in self.env.items()
        ]

        # append_env
        lines.extend([
            f'export {name}="${name}{list_sep}{list_sep.join(val)}"'
            if isinstance(val, list)
            else f'export {name}="{val}"'
            for name, val in self.append_env.items()
        ])

        # PATH
        if self.PATH:
            self.PATH = list(dict.fromkeys(self.PATH))
            sh_path_arr = " ".join([f'"{p}"' for p in self.PATH])
            lines.extend([
                f"printf {sh_path_arr} | while IFS= read -r p; do",
                '  case ":$PATH:" in',
                '  *":$p:"*) ;;',
                '  *) PATH="$p${PATH:+:$PATH}" ;;',
                '  esac',
                'done',
                'export PATH',
            ])

        return "\n".join(lines)

    def as_pwsh(self, list_sep: str = _default_pwsh_list_sep) -> str:
        # env
        lines = [
            f'$env:{name} = "{list_sep.join(val)}"'
            if isinstance(val, list)
            else f'$env:{name} = "{val}"'
            for name, val in self.env.items()
        ]

        # append_env
        lines.extend([
            f'$env:{name} += "{list_sep}{list_sep.join(val)}"'
            if isinstance(val, list)
            else f'$env:{name} += "{val}"'
            for name, val in self.append_env.items()
        ])

        # PATH
        if self.PATH:
            self.PATH = list(dict.fromkeys(self.PATH))
            ps_arr = ", ".join([f"'{p}'" for p in self.PATH])
            lines.extend([
                '$_paths = $env:PATH -split ";"',
                "$_paths = @(@(@(" + ps_arr + ') | where { $_ -notin $_paths }) + $_paths)',
                '$env:PATH = $_paths -join ";"',
                'Remove-Variable -Name "_paths"'
            ])

        return "\n".join(lines)


path = dirs.VULPIX_CONFIG / ".env.json"


def handle_error(exc_type: type[Exception], exc_value: Exception) -> bool:
    if issubclass(exc_type, (JSONDecodeError, DaciteError)):
        logging.getLogger("main").error(str(exc_value))
        raise VulpixError(f"invalid dotenv file at '{path}'")

    return False


datafile = DataclassFile(path, dclass=Dotenv, on_error=handle_error)
