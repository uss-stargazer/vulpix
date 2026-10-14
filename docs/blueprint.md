# blueprint

the blueprint is the primary source of truth that acts as a "blueprint" for your system/user. it is
a yaml file (`blueprint.yaml`) located in the [config directory](directories.md#config). it contains
the following information:

- target packages
- target configuration
- vulpix settings

the vulpix cli syncs the system with the blueprint. see `config.default/blueprint.yaml` for an
example.

## yaml schema

```yaml
required: [packages, configs]
properties:
    packages:
        type: object
        description: target packages for system, by package manager
        patternProperties:
            '.*': # package manager ID
                type: array
                items: {type: string}
                description: list of target packages
    configs:
        type: object
        description: custom, user-defined configuration for use by config-scripts
        patternProperties:
            '.*': # config manager ID
                type: any
                description: >
                    config to pass to manager; each config manager should document what this should
                    look like
    dotfiles:
        type: string
        description: path to dotfiles directory

    # vulpix settings
    settings:
        type: object
        properties:
            threads:
                type: int
                description: number of worker threads that run tasks
            alt_screen:
                type: bool
                description: whether to enter alt-screen/fullscreen when running management
            abort_uninstall_threshold:
                type: int
                description: >
                    max number of packages to be uninstalled before check trips and vulpix
                    automatically aborts

    # blueprint meta
    extends:
        type: array
        items: {type: string}
        description: >
            paths to other yaml blueprints to merge the current ontop of (arrays are concated)
```
