# config managers

config managers are given the "config" object defined in your blueprint and a list of packages to
configure, and they decide how to configure the packages.

## vulpix defaults

### `scripts`

a config manager that allows the user to create custom scripts for each package that do their
configuration. it places the burden of actual configuration on you (the user), cause you have to
create the scripts.

### script discovery

scripts are stored in `$VULPIX_CONFIG/scripts` (see [vulpix dirs](docs/directories.md#config)) the
script dir should be formatted like:

```
$VULPIX_CONFIG/scripts/
├─ ...general root scripts that run on every config
├─ $PACKAGE.d/
│  └─ ...scripts that run on every config of this package
└─ ...other *.d dirs for package configs
```

for example:

```
$VULPIX_CONFIG/scripts/
├─ 00-some-system-script.py
├─ 10-windows-only-script.ps1
├─ 10-unix-only-script.sh
├─ 10-will-still-run-if-exec.exe
├─ 50-upstream-script.py
├─ python.d/
│  ├─ 10-generic-config.py
│  ├─ 20-setup-base-packages.py
│  ├─ 20-setup-base-packages.py
│  └─ ...more scripts
├─ ...other general scripts
└─ ...other *.d dirs for package configs
```

all files in the root dir or a `*.d` dir that are executable or end with `.sh`, `.ps1`, or `.py`
will attempt to be run. scripts in `{PACKAGE}.d` dir will only run if the `{PACKAGE}` is passed to
this manager. `.sh` scripts will only run if linux and `.ps1` scripts will only run if windows.

as the above example shows, this manager also supports numbered script names like
`00-do-something.py`, which enables asynchronous script execution. the assumption is that all
scripts at the same numbered level can be run in parallel.

> [!TIP]
>
> these "custom config scripts" can be stored in your dotfiles repo.

#### order example

```
$VULPIX_CONFIG/config/
├─ global.d/
│  ├─ 00-system.py
│  ├─ 10-env.py
│  ├─ 10-windows-env.ps1
│  └─ 50-tidy-user.py
├─ bash.d/
│  ├─ 00-system-env-vars.sh
│  ├─ 30-fancy-prompt.sh
│  └─ other-stuff.sh
└─ mpd.d/
   ├─ 10-systemctl-service-enabled.py
   ├─ 30-config-file.py
   └─ 50-tidy-music-dir.py
```

for example, in the above sample `$VULPIX_CONFIG/config`, the scripts will be run in parallel in the
following rounds (assuming all the packages are in the cli scope):

1. `global.d/00-system.py`, `bash.d/00-system-env-vars.sh` (if linux)
2. `global.d/10-env.py`, `global.d/10-windows-env.ps1` (if windows),
   `mpd.d/10-systemctl-service-enabled.py`
3. `bash.d/30-fancy-prompt.sh` (if linux), `mpd.d/30-config-file.py`
4. `global.d/50-tidy-user.py`, `50-tidy-music-dir.py`
5. `bash.d/other-stuff.sh` (if linux)

### python scripts

the standard script type is a standalone python script. the script root will always be run, and if
the script exports a `main` function, it will also automatically be run. the main function can also
accept any of the following params:

```python
def main(
    config: Any, logger: logging.Logger, queue: vulpix.core.tasks.ThreadedTaskQueue
):
    pass
```

the `config` param is whatever config is in your blueprint.

python scripts can access any utils of the `vulpix` package (`vulpix.utils`, `vulpix.core.dotenv`,
`vulpix.core.system`, `vulpix.core.dirs`, etc.).

## create your own

see [custom managers docs](docs/managers.md#custom-managers).

your Python module must export a `package_manager_class` variable that contains a subclass of
[`ConfigManager`](../src/vulpix/config_managers/__init__.py).
