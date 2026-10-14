# dotfiles repos

vulpix works well with 'dotfiles' repos. you can use your preferred tool
([there's a lot of them](https://dotfiles.github.io/utilities/)) and it should work nicely.

dotfiles repos are cool because you can store your `blueprint.yaml` and config scripts there along
with all the package-specific configuration files that, along with the config scripts, make up your
entire system config. apply dotfiles, then run vulpix config, and your good to go.

## managing with vulpix

vulpix also implements its own dotfiles manager if you want to use it. i made this mainly because i
wanted cross-platform dotfiles symlinking. you can specify the directory to look for dotfiles for in
your `blueprint.yaml` or pass it directly to the cli. `vulpix dotfiles <path>` creates symlinks to
all the standard locations (uses blueprint if no `<path>`).

TODO: allow passing github url to dotfiles subcommand.

it expects the following directory structure and symlinks as follows:

```
dotfiles/
├─ .config/
│  ├─ $tool/ -> ~/.config/$tool, ~\AppData\Local\$tool
│  │  └─ ...tool config
│  └─ ...
├─ fonts/ -> wherever your os stores fonts (copies fonts, no symlink)
├─ ...$homedir/ -> ~/$homedir
└─ ...$homefile -> ~/$homefile
```

you can also have a `.vuplixignore` to specify anything that shouldn't be symlinked (although it
doesn't handle all the fancyness that .gitignore handles, like globs).
