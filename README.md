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

## Installation

Follow these steps to set up the tool on your system.

### 1. Download the standalone wizard
If you are on macOS, Windows, or Linux, you can download the `kolay-setup` binary from the [latest release](https://github.com/ezapmar/kolay-cli/releases). This version is pre-compiled and does not require you to install Python or manage dependencies manually. It is the fastest way to get started.

### 2. Run the setup tool
Open your terminal and execute the downloaded file:
```bash
./kolay-setup
```
This tool handles the initial configuration. It is necessary because it ensures your API token is stored securely in your OS Keychain rather than in plain text, and it verifies that you have acknowledged the alpha disclaimer.

### 3. Accept the alpha disclaimer
You must read and accept the safety notice. This project is a laboratory/R&D tool and is not an official product of Kolay Yazılım A.Ş. Understanding the risks is necessary because write and update operations change live HR data in your account.

### 4. Provide your API token
The wizard will prompt you for your Kolay API token. You can create one at [app.kolayik.com/settings/developer-settings](https://app.kolayik.com/settings/developer-settings). The token is necessary for the CLI to authenticate with the Kolay servers and access your data.

### 5. Install the MCP server
The tool will ask where to install the MCP server (e.g., Claude Desktop, Cursor). This step is necessary if you want to use AI assistants to interact with your HR data. The wizard automatically updates the configuration files for these clients to point to the `kolay-setup` binary.

## Example Usage

Once installed, you can list all employees in your organization with a single command:

```bash
kolay person list
```

## Features

- **People Management**: List employees, view summaries, and manage records.
- **Leave and Time**: Create and track leave records and work hours.
- **Workflow Integration**: Approvals, calendar events, and organisational units.
- **AI-Powered**: Use the built-in MCP server to talk to your HR data through AI assistants.

## Output Modes

- `--json`: Machine-readable output for scripts and agents.
- `--yes`: Skip interactive confirmations for automated tasks.
- `--debug`: Write full HTTP traces to `~/.config/kolay/debug.log` for troubleshooting.

## Notice

This is an unofficial project. Kolay Yazılım A.Ş. is not responsible for any data loss, system errors, or damages. You are responsible for the security of your API tokens and the accuracy of your operations.
