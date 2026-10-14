# vulpix quickstart

this is the default config to help get you started using vulpix. at some point, take a look at the
[docs](https://github.com/uss-stargazer/vulpix/tree/main/docs)!

your current config looks something like this:

```
$VULPIX_CONFIG/
├─ blueprint.yaml # the main blueprint that vulpix syncs your system with
└─ config/        # scripts for `scripts` config manager (optional)
```

**`blueprint.yaml`** is probably the most important file as it contains the target packages and
configuration for your system/user.

the **`config/`** subdirectory is specifically for the [`scripts`
manager](https://github.com/uss-stargazer/vulpix/tree/main/docs/config_managers#scripts). this is just one
config manager you can use, so it's not required. it corresponds to and has access to the
`configs.scripts` object in your `blueprint.yaml`. take a look at the example scripts in it to learn
how it works.

after first running, vulpix should create a
[**`.env.json`**]((https://github.com/uss-stargazer/vulpix/tree/main/docs/config_managers#scripts)) file,
which is basically an internal [dotenv file](https://www.dotenv.org/) (in json format) that acts as
a dynamic, cross-platform  config for environmental variables.
