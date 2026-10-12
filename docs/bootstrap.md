# bootstrap

the main target of bootstrap is to install the vulpix package with pip (or any other python manager
that can expose target scripts). to do this, this is what the bootstrap scripts do:

1. **ensure `python` and `git` are installed**: python is required for obvious reasons. git is
   required because `pip install git+{REPO}` requires it and that is how vulpix is installed (TODO:
   upload pypi so this is not necessary)

- *for linux*: it's the os's job to compile and install packages like git and python, so bootstrap
  just checks for existence (TODO: check linux distro to determine package manager, and bootstrap
  packages with that; requires more bultin vulpix package managers)
- *for windows*: any of the two packages that aren't available are bootstrapped using the `manual`
  package manager. obviously, the package manager can't be run because we could be bootstrapping
  python, so we use the shell scripts located in `src/vulpix/package_managers/manual/packages`.
- in either above case, if the bootstrap script bootstraps any packages, it writes writes a log of
  them (by manager) to `$VULPIX_DATA/bootstrapped.json`.

2. **install vulpix**: simply runs `pip install git+{THIS_REPO}` (TODO: support other methods of
   installation; e.g. pipx, uv)

3. **initial vulpix run**: it is required to run `vulpix sync` to finish the bootstrap process
   because it cleans everything up, registers bootstrapped packages, sets up the config dir, and
   ensure that vulpix will be able to run outside of the temporary environment used to bootstrap it.
   for this purpose, two things happen every time vulpix is run:

- *checks `$VULPIX_CONFIG` dir*: if a blueprint does not exist in
  [`$VULPIX_CONFIG`](docs/directories.md#config), the [quickstart blueprint](#quickstart-config)
  is copied to it. if `$VULPIX_CONFIG` doesn't exist or is emtpy, the rest of the
  [quickstart config](#quickstart-config) is copied there.
- *checks `$VULPIX_DATA/bootstrapped.json`*: if this file exists (presumably created by the bootstrap
  script), the packages are manually added to the blueprint before sync is run. this way,
  bootstrapped packages can be properly registered and installed. vulpix deletes the json after,
  it's been processed.
- *ensures vulpix*: makes sure that the `vulpix` binary is accessible
    - *for linux*: makes sure vulpix is symlinked to standard bin location
    - *for windows*: adds the parent dir of vulpix.exe to PATH in environmental var registry

## quickstart config

sample contents of `$VULPIX_CONFIG` are located at `src/vulpix/resources/quickstart_config`. this
is copied if the config dir is empty (see above). it has the follow contents:

- `README.md`: info about configuring vulpix
- `blueprint.yaml`: basic quickstart blueprint with comments, etc.
- `config/`: a sample directory of config scripts for the `scripts` config manager to demonstrate
  how it should be used
