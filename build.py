"""PyInstaller build script for the Kolay İK MCP setup wizard.

Usage:
    python build.py            # build for the current platform
    python build.py --clean    # remove previous build artifacts first

Output: dist/kolay-setup (or kolay-setup.exe on Windows)
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_POINT = PROJECT_ROOT / "setup_wizard.py"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_DIR = PROJECT_ROOT

EXE_NAME = "kolay-setup"


def _hidden_imports() -> list[str]:
    """Packages PyInstaller cannot detect from static analysis."""
    return [
        # keyring backends vary by OS
        "keyring.backends",
        "keyring.backends.macOS",
        "keyring.backends.Windows",
        "keyring.backends.SecretService",
        "keyrings.alt",
        "keyrings.alt.file",
        # MCP server
        "fastmcp",
        "kolay_cli",
        "kolay_cli.mcp_server",
        "kolay_cli.security",
        "kolay_cli.services",
        "kolay_cli.services.mcp_registry",
        "kolay_cli.config",
        # UI
        "rich",
        "yaml",
        "core",
        "core.constants",
    ]


def build(clean: bool = False) -> None:
    """Run PyInstaller to produce a single-file executable."""
    if clean:
        for d in (DIST_DIR, BUILD_DIR):
            if d.exists():
                shutil.rmtree(d)
                print(f"Removed {d}")

    import os
    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        f"--name={EXE_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={SPEC_DIR}",
        # Include the src/ and core/ directories as data
        f"--add-data={PROJECT_ROOT / 'src'}{sep}src",
        f"--add-data={PROJECT_ROOT / 'core'}{sep}core",
        # Use --console for all platforms for now
        "--console",
    ]

    for imp in _hidden_imports():
        cmd.extend(["--hidden-import", imp])

    cmd.append(str(ENTRY_POINT))

    print(f"\n{'=' * 60}")
    print(f"Building {EXE_NAME} for {platform.system()} ({platform.machine()})")
    print(f"{'=' * 60}\n")
    print(f"Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"\nBuild failed (exit code {result.returncode}).")
        raise SystemExit(result.returncode)

    exe_path = DIST_DIR / EXE_NAME
    if platform.system() == "Windows":
        exe_path = exe_path.with_suffix(".exe")

    print(f"\nBuild succeeded: {exe_path}")
    print(f"Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")

    _print_signing_instructions(exe_path)


def _print_signing_instructions(exe_path: Path) -> None:
    """Print platform-specific code signing instructions."""
    system = platform.system()

    print(f"\n{'─' * 60}")
    print("Code Signing (recommended for distribution)")
    print(f"{'─' * 60}")

    if system == "Darwin":
        print("""
macOS — Apple Developer ID:

  # Sign the executable
  codesign --force --options runtime \\
    --sign "Developer ID Application: Your Name (TEAM_ID)" \\
    --timestamp \\
    """ + str(exe_path) + """

  # Submit for notarization
  xcrun notarytool submit """ + str(exe_path) + """ \\
    --apple-id "you@example.com" \\
    --team-id "TEAM_ID" \\
    --password "@keychain:AC_PASSWORD" \\
    --wait

  # Staple the notarization ticket
  xcrun stapler staple """ + str(exe_path) + """
""")

    elif system == "Windows":
        print("""
Windows — Authenticode (signtool):

  signtool sign /f certificate.pfx /p PASSWORD \\
    /tr http://timestamp.digicert.com /td sha256 \\
    /fd sha256 """ + str(exe_path) + """
""")

    else:
        print("""
Linux — GPG signature:

  gpg --detach-sign --armor """ + str(exe_path) + """

  # Users verify with:
  gpg --verify """ + str(exe_path) + """.asc
""")


if __name__ == "__main__":
    clean_flag = "--clean" in sys.argv
    build(clean=clean_flag)
