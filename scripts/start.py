"""Portable development launcher for the Miraclex app.

It uses a local virtual environment so the project can run on a fresh PC
without relying on globally installed Python packages.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "backend" / "requirements.txt"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
URL = f"http://localhost:{PORT}"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def in_project_venv() -> bool:
    return Path(sys.executable).resolve() == venv_python().resolve()


def run(command: list[str]) -> None:
    subprocess.check_call(command, cwd=ROOT)


def ensure_venv() -> None:
    if not venv_python().exists():
        print("Creando entorno virtual local en .venv ...", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)


def relaunch_in_venv() -> None:
    env = os.environ.copy()
    raise SystemExit(subprocess.call([str(venv_python()), str(Path(__file__).resolve())], cwd=ROOT, env=env))


def install_dependencies() -> None:
    print("Instalando/actualizando dependencias Python ...", flush=True)
    run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQUIREMENTS)])


def port_is_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((HOST, PORT)) == 0


def existing_app_responds() -> bool:
    try:
        with urllib.request.urlopen(f"{URL}/api/profiles", timeout=2) as response:
            return 200 <= response.status < 500
    except (urllib.error.URLError, TimeoutError):
        return False


def wait_for_server() -> None:
    for _ in range(30):
        if existing_app_responds():
            print(f"App lista en {URL}/app/")
            return
        time.sleep(0.5)
    print(f"Servidor iniciado. Abre {URL}/app/")


def main() -> None:
    os.chdir(ROOT)

    ensure_venv()
    if not in_project_venv():
        relaunch_in_venv()

    if port_is_open():
        if existing_app_responds():
            print(f"La app ya esta ejecutandose en {URL}/app/")
            return
        raise SystemExit(
            f"El puerto {PORT} ya esta ocupado por otro proceso. "
            "Cierra ese proceso o usa otra variable PORT."
        )

    install_dependencies()

    print(f"Iniciando Miraclex en {URL}/app/")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            HOST,
            "--port",
            str(PORT),
        ],
        cwd=ROOT,
    )

    try:
        wait_for_server()
        process.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor ...")
        process.terminate()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()
