# kolay-cli

An unofficial command-line interface and MCP server for the Kolay İK HR platform.

```
     ##################
    ###            ###
   ####   ####     %%%           %%%
  ####   ####      %%%           %%%
 ####   ####       %%%           %%%
####   ####        %%%   %%%%  %%%%%%%%%  %%%  %%%%%%%%%%%  %%%     %%%% 
####   ###         %%%  %%%%  %%%%%   %%%%   %%%  %%%%%   %%%%%  %%%%    %%%
####  #####        %%%%%%%    %%%       %%%  %%%  %%%       %%%   %%%%  %%%%
 #### ########     %%%%%%%    %%%       %%%  %%%  %%%       %%%    %%%%%%%% 
  ####  #### ####  %%% %%%%   %%%%     %%%%  %%%  %%%%     %%%%     %%%%%% 
   ####   #### ####  %%%   %%%%  %%%%%%%%%%%   %%%   %%%%%%%%%%%%      %%%% 
     ### ####  ####  %%%     %%%    %%%%%      %%%      %%%%  %%%      %%%% 
      #####   ###                                           %%%%% 
       ##################                                  %%%%% 
```

## Notice

This is an unofficial lab project. It is not an official product of Kolay Yazılım A.Ş. They are not responsible for data loss or system errors. You are responsible for your API tokens. Write and update operations change live HR data. Use with care.

## Install

### 1. Install the package

```bash
pipx install kolay-cli
```

`pipx` installs the tool in an isolated environment and puts the `kolay` command on your PATH. If you don't have `pipx`, install it first with `pip install pipx`.

### 2. Authenticate

```bash
kolay auth login
```

You will be prompted for your Kolay API token. You can create one at [app.kolayik.com/settings/developer-settings](https://app.kolayik.com/settings/developer-settings). The token is stored securely in your OS Keychain.

### 3. Connect your AI assistant (optional)

```bash
kolay mcp install
```

This writes the MCP server configuration into the config files for Claude Desktop, Cursor, or other supported AI clients. After this step, your AI assistant can query and update your HR data directly.

### 4. Verify the installation

```bash
kolay doctor
```

This checks that your token is valid, the API is reachable, and all dependencies are in place.

## Example

```bash
kolay person list
kolay leave create --type annual --start 2026-03-01 --end 2026-03-03
```

## Commands

Commands follow the `kolay <resource> <action>` pattern.

| Resource    | Actions                                      |
|-------------|----------------------------------------------|
| auth        | login, logout, status                        |
| config      | show, set                                    |
| person      | list, view, summary, create, update, terminate |
| leave       | list, create                                 |
| timelog     | list, create, delete                         |
| training    | list, create, delete                         |
| calendar    | list, create, update, delete                 |
| transaction | list                                         |
| expense     | list                                         |
| approval    | list                                         |
| unit        | tree                                         |
| mcp         | install, serve                               |
| doctor      | (health check)                               |

## Flags

| Flag      | Effect                                              |
|-----------|-----------------------------------------------------|
| `--json`  | Print machine-readable JSON. Use in scripts/agents. |
| `--yes`   | Skip all confirmation prompts.                      |
| `--debug` | Write HTTP traces to `~/.config/kolay/debug.log`.   |

## Exit Codes

| Code | Meaning    |
|------|------------|
| 0    | Success    |
| 1    | Error      |
| 2    | Bad input  |
| 3    | Not found  |
| 4    | Auth error |
| 5    | Conflict   |

## Links

- [API Docs](https://apidocs.kolayik.com)
- [GitHub](https://github.com/ezapmar/kolay-cli)
- [PyPI](https://pypi.org/project/kolay-cli)
