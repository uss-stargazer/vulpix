# dotenv file

vulpix maintains an internal [dotenv file](https://www.dotenv.org/) located at
`$VULPIX_CONFIG/.env.json`. it's json because it's cross-platform and can be sourced by powershell 
or any posix compliant shell using `vulpix dotenv {shell}`.

it's meant to be souced in your shell profile:

- powershell: `vulpix dotenv pwsh | Invoke-Expression`
- sh, bash, zsh, and so on: `eval "$(vulpix dotenv sh)"`

the following things can access and edit the file:

- package managers
- config managers (this includes your own custom scripts for the `scripts` manager)
- you (you can set your own env vars; beware that managers could totally overwrite them if they want
  to)
