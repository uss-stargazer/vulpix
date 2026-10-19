# package managers

package managers are given the list of packages in your blueprint, and they decide what to install,
uninstall, reinstall, or update (the user can filter these actions using the cli).

## vulpix defaults

### `manual`

custom package manager that is manually implemented by vulpix (hence "manual" from vulpix's
perspective, and from your perspective too if you peek at the code or contribute).

see [here](../src/vulpix/package_managers/manual/__init__.py) for implementation details and
[here](../src/vulpix/package_managers/manual/packages/) for a list of supported packages.

### `expect`

expect isn't really a package manager. all it does is check if the package is already installed, and
if it is, it succeeds and continues to config (or whatever else). this is useful for many reasons,
but i can think of two right now:

- if a package comes preinstalled on your os (like bash on linux), you can expect its existence in
  your portable blueprint
- if you want a tool available at the user level blueprint, but it needs to be installed system-wide
  (for example, most apt use cases), you can just "expect" in your user blueprint and defer
  installation to your system-wide/root blueprint, however it decides to manage it.

by default, the manager checks if it exists and if not, fails the installation task. there are some
presets for checking the existence of common packages, else it just checks if the name of the
package is a valid command. you can bypass these checks (see the tip below).

> [!TIP]
>
> the expect manager supports the special package name syntax `package_name!` (the whole id would be
> like `bash!@expect`). in this case, literally no checks are preformed (it's just comment at this
> point).

### `pip`

package manager that drives [pip](https://pip.pypa.io/), which is the default python package
manager.

> [!IMPORTANT]
> things to note:
> 
> - no virtual environments are created; everything is in the global pip environment
>   - this becomes messy since two packages could depend on two different version of the same
>     dependency (in this case, one of the target packages would fail)
>   - if the global python env is externally managed (e.g. on debian), this manager cannot be used
> - pip is pretty slow
>   - pip itself is yet to support parallel downloads/installs
>   - each operations must be executed individually and synchronously
>   - an seperate `pip` process has to be spawned for each task since for batched operations, the
>     entire operation aborts if just one package fails
    
> [!TIP]
> it's recommended to use the `pipx`, `uv`, etc. package managers instead of pip for the above
> reasons.

### `pipx`

package manager that drives [pipx](https://pipx.pypa.io/), which is NOT the default python package
manager (pip), but a wrapper over it that creates a self-contained virtual environment for each
global package. this makes it a much better alternative to `pip` at the global level for cli tools
and binaries.

advantages over the `pip` package manager:

- it also solves global packages on "externally managed" global environments (common on
  linux distros, e.g. debian), which is not allowed for `pip`
- operations can be run in parallel, so it's much faster
- since each package has it's own virtual env, no dependency resolution errors

## create your own

see [custom managers docs](./managers.md#custom-managers).

your Python module must export a `config_manager_class` variable that contains a subclass of
[`PackageManager`](../src/vulpix/package_managers/__init__.py).
