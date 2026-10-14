# vulpix

a cross-platform, blueprint-driven system management/configuration tool.

it uses `blueprint.yaml` to abstract two main things:

1. package management: abstracting over package managers (like apt, pip, pacman)
2. configuration management: abstracting over package config managers

> [!IMPORTANT]
>
> vulpix uses a plugin-like architecture for both package and config managers
> ([read this](docs/managers.md)). basically, vulpix is just a pretty cli wrapper around other
> package managers; it doesn't actually do any of the stuff. while it comes with common package
> managers (apt, pip pacman, etc.) and a default config manager, you are encouraged to build
> your own.

some extra features:

- dotfiles setup: looks for optional dotfiles repo and symlinks everything to correct locations
- multithreaded management (depending on manager support)
- internal [dotenv file](https://www.dotenv.org/) that acts as a dynamic, cross-platform config file
  for system environmental variables
    - it can be easily subscribed to in your script language's profile script
- you can have a system-wide blueprint that gets run by the root/admin user, in addition to a
  blueprint for specific users 
    - for example, the `apt` manager cannot be used by non-root blueprint

check out the [docs](docs/)!

## installing

if you already have python installed, just:

    pip install vulpix

or if not, you can run the bootstrap script, which installs python, then `pip install`s:

    curl -fsSL https://raw.githubusercontent.com/uss-stargazer/vulpix/refs/heads/main/bootstrap.sh | bash

windows has its own bootstrap script:

    iwr -Uri "https://raw.githubusercontent.com/uss-stargazer/vulpix/refs/heads/main/bootstrap.ps1" | iex

## usage

    usage: vulpix [OPTIONS] <COMMAND>

    blueprint-driven system management/configuration tool [ b(￣▽￣)d ]

    positional arguments:
      {sync,dotfiles,blueprint,dotenv,replay}
        sync                syncs system/user with the blueprint
        dotfiles            symlinks dotfiles to system locations
        blueprint           open blueprint in $VISUAL/$EDITOR
        dotenv              source vulpix dotenv in your shell
        replay              replay a log file

    options:
      -h, --help            show this help message and exit
      -V, --version         print version tag
      -v, --verbose         print debug logs
      -w, --whatif          show what would happen without doing anything
      -b, --blueprint PATH  specify blueprint.yaml path, otherwise searches default locations
      --no-fullscreen       no fullscreen/alt screen

of particular note is the sync subcommand:

    usage: vulpix sync [FILTER_OPTS]

    syncs system/user with the blueprint

    positional arguments:
      REGEX                 filter for packages of all task types

    options:
      -h, --help            show this help message and exit
      -i, --install [REGEX] if any packages are in the blueprint but are not installed, they will be
                            installed
      -u, --update [REGEX]  if any blueprint packages are already installed, they will be updated
      -a, --apply [REGEX]   basically --install ... --update ... (but you can also stack these
                            options too)
      -x, --clean [REGEX]   if any packages are installed but are not a package specified in
                            blueprint they will be uninstalled
      -r, --reinstall REGEX uninstalls then reinstalls matching packages
      -c, --config [REGEX]  runs config managers for matching packages (if any other operations are 
                            run, only configs for successful packages will be run)

    NOTE: if option passed and no [REGEX], it defaults to .*

    package managers are appended to package names before checking against regex like 
    {name}@{manager}. for example, regex of .*@pip would limit scope to packages under the 'pip'
    manager.

    if an option filter is supplied, only tasks of that type will run. if no [opts] are supplied,
    runs with --clean --apply --config.
