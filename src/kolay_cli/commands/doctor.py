"""
``kolay doctor`` — post-install health check.

Runs a series of checks and prints a clear pass/fail report so the user
knows whether everything is wired up correctly.
"""
from __future__ import annotations

import os
import shutil
import sys

import typer
from rich.console import Console

from ..config import CONFIG_FILE_JSON, CONFIG_FILE_YAML

app = typer.Typer(help="Check your Kolay CLI installation health.")
console = Console(highlight=False)

from ..ui.constants import PRIMARY as _PRIMARY
_OK = "[bold #57CC99]✔[/bold #57CC99]"
_FAIL = "[bold #FF6B6B]✘[/bold #FF6B6B]"
_WARN = "[bold #FFD93D]⚠[/bold #FFD93D]"


def _check_path() -> tuple[str, str]:
    """Check if the `kolay` binary is on $PATH."""
    if shutil.which("kolay"):
        return _OK, "kolay is on your PATH"
    return _FAIL, (
        "kolay is [bold]not[/bold] on your PATH — your shell can't find it\n"
        "       Run [bold]pipx ensurepath[/bold] then restart your terminal"
    )


def _check_config_file() -> tuple[str, str]:
    """Check if a config file exists."""
    if CONFIG_FILE_YAML.exists():
        return _OK, f"Config file found  [grey62]{CONFIG_FILE_YAML}[/grey62]"
    if CONFIG_FILE_JSON.exists():
        return _OK, f"Config file found  [grey62]{CONFIG_FILE_JSON}[/grey62]"
    return _WARN, (
        "No config file yet\n"
        "       Run [bold]kolay auth login[/bold] to create one"
    )


def _check_token() -> tuple[str, str]:
    """Check if an API token is configured and report its source."""
    from ..security import resolve_token_with_source, validate_token

    token, source = resolve_token_with_source()
    if not token:
        return _FAIL, (
            "No API token found\n"
            "       Run [bold]kolay auth login[/bold] or set [bold]KOLAY_API_TOKEN[/bold]"
        )

    # Source label: add a migration hint when token is in the config file
    if source == "config file":
        source = "config file  [yellow](run [bold]kolay auth login[/bold] to migrate to keychain)[/yellow]"

    # Quick local validation
    validation = validate_token(token)
    if not validation:
        return _FAIL, f"Token found but invalid  [grey62]({validation.reason})[/grey62]"

    return _OK, f"API token configured  [grey62](source: {source})[/grey62]"


def _check_api() -> tuple[str, str]:
    """Check if the API is reachable and the token is valid."""
    from ..security import resolve_token
    token = resolve_token()
    if not token:
        return _WARN, "API connectivity  [grey62](skipped — no token)[/grey62]"
    try:
        from ..api import KolayClient
        client = KolayClient(token=token)
        resp = client.get("v2/profile/me")
        data = resp.get("data", {})
        name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
        return _OK, f"API connected  [grey62]→ {name}[/grey62]"
    except Exception as exc:
        return _FAIL, f"API connection failed  [grey62]({exc})[/grey62]"


def _check_python() -> tuple[str, str]:
    """Check Python version ≥ 3.10."""
    v = sys.version_info
    label = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= (3, 10):
        return _OK, f"Python {label}"
    return _FAIL, f"Python {label}  [grey62](need ≥ 3.10)[/grey62]"


def _check_shell_completion() -> tuple[str, str]:
    """Check if shell completion is likely installed."""
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        zshrc = os.path.expanduser("~/.zshrc")
        try:
            with open(zshrc, encoding="utf-8") as f:
                if "kolay" in f.read().lower():
                    return _OK, "Shell completion installed  [grey62](zsh)[/grey62]"
        except FileNotFoundError:
            pass
        return _WARN, (
            "Shell completion not detected\n"
            "       Run [bold]kolay --install-completion zsh[/bold]"
        )
    if "bash" in shell:
        bashrc = os.path.expanduser("~/.bashrc")
        try:
            with open(bashrc, encoding="utf-8") as f:
                if "kolay" in f.read().lower():
                    return _OK, "Shell completion installed  [grey62](bash)[/grey62]"
        except FileNotFoundError:
            pass
        return _WARN, (
            "Shell completion not detected\n"
            "       Run [bold]kolay --install-completion bash[/bold]"
        )
    return _WARN, f"Unknown shell  [grey62]({shell or 'not set'})[/grey62]"


@app.callback(invoke_without_command=True)
def doctor(ctx: typer.Context) -> None:
    """Run a full health check of your Kolay CLI installation."""
    from ..ui.output import is_json_mode, json_output, strip_markup

    def _check_keyring() -> tuple[str, str]:
        import sys
        from ..security import _keyring_available, _keyring_backend_name, _is_ci

        if _is_ci():
            # In CI the env var is the right approach — keyring is not needed
            return _WARN, (
                "CI environment detected  [grey62](keyring skipped)\n"
                "       Set [bold]KOLAY_API_TOKEN[/bold] as a CI secret instead[/grey62]"
            )

        if _keyring_available():
            backend = _keyring_backend_name()
            # keyrings.alt PlaintextKeyring stores credentials unencrypted on disk —
            # useful as a fallback but meaningfully weaker than the native OS keychain.
            if "plaintext" in backend.lower():
                return _WARN, (
                    f"File-backed keyring active  [grey62]({backend} — not encrypted)\n"
                    "       Token stored in plain text in ~/.local/share/python_keyring/\n"
                    "       For encrypted storage install the Secret Service: "
                    "[bold]sudo apt install gnome-keyring[/bold][/grey62]"
                )
            return _OK, f"OS Keychain available  [grey62]({backend}) 🔐[/grey62]"

        if sys.platform == "linux":
            return _WARN, (
                "No keyring backend on Linux  [grey62](token falls back to config file)\n"
                "       For secure storage: [bold]pip install 'kolay-cli[linux]'[/bold]"
            )

        return _WARN, (
            "OS Keychain not available — token stored in config file\n"
            "       Install a keyring backend for secure storage"
        )



    checks = [
        ("PATH", _check_path),
        ("Config", _check_config_file),
        ("Keyring", _check_keyring),
        ("Token", _check_token),
        ("API", _check_api),
        ("Python", _check_python),
        ("Completion", _check_shell_completion),
    ]

    results: list[dict[str, str]] = []
    has_fail = False

    from ..ui.constants import KOLAY_LOGO
    console.print(KOLAY_LOGO)
    console.print(f"[bold {_PRIMARY}]🩺 Kolay CLI Health Check[/bold {_PRIMARY}]\n")

    for name, fn in checks:
        icon, message = fn()
        status_str = "pass" if _OK in icon else ("warn" if _WARN in icon else "fail")
        # Store plain text for JSON; keep markup for terminal rendering
        results.append({"check": name, "status": status_str, "message": strip_markup(message)})
        if _FAIL in icon:
            has_fail = True
        console.print(f"  {icon}  {message}")

    console.print()

    if is_json_mode():
        json_output({"checks": [{k: v for k, v in r.items()} for r in results], "healthy": not has_fail})
        return

    if has_fail:
        console.print(f"  [grey62]Fix the issues above and run [bold]kolay doctor[/bold] again.[/grey62]\n")
    else:
        console.print(f"  [bold #57CC99]All clear![/bold #57CC99]  Your installation is healthy.\n")
