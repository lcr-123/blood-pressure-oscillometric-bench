"""Shared MSVC host build environment; never connects to hardware."""
import os
from pathlib import Path
import shutil
import subprocess

PROJECT = Path(__file__).resolve().parents[1]


def compiler_environment():
    env = os.environ.copy()
    compiler = shutil.which("cl")
    if compiler:
        return compiler, env
    vswhere = Path(env.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
    if not vswhere.is_file():
        raise FileNotFoundError("MSVC C tools required (Visual Studio Build Tools)")
    install = subprocess.check_output(
        [str(vswhere), "-latest", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
        text=True, timeout=15,
    ).strip()
    if not install:
        raise FileNotFoundError("MSVC C tools not installed")
    setup = Path(install) / "VC/Auxiliary/Build/vcvars64.bat"
    output = subprocess.check_output(
        f'cmd.exe /d /s /c ""{setup}" >nul && set"',
        text=True, errors="replace", timeout=30,
    )
    env.update(line.split("=", 1) for line in output.splitlines() if "=" in line and not line.startswith("="))
    compiler = shutil.which("cl", path=env.get("Path", env.get("PATH")))
    if not compiler:
        raise RuntimeError("MSVC environment did not expose cl.exe")
    return compiler, env


def build_replay(work):
    compiler, env = compiler_environment()
    for name in ("bp_algorithm", "bp_capture_export"):
        for folder, suffix in (("Inc", "h"), ("Src", "c")):
            shutil.copy2(PROJECT / "Core" / folder / f"{name}.{suffix}", work)
    shutil.copy2(PROJECT / "Core/Inc/bp_control.h", work)
    shutil.copy2(PROJECT / "test/host/main.h", work)
    shutil.copy2(PROJECT / "test/host/tim.h", work)
    shutil.copy2(PROJECT / "tools/host/bp_replay.c", work)
    exe = work / "bp_replay.exe"
    built = subprocess.run(
        [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
         "bp_replay.c", "bp_algorithm.c", "bp_capture_export.c", f"/Fe:{exe}"],
        cwd=work, env=env, text=True, errors="replace", capture_output=True, timeout=60,
    )
    if built.returncode:
        raise RuntimeError(built.stdout + built.stderr)
    return exe
