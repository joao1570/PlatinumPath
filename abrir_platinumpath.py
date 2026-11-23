"""Inicia o servidor local e abre a interface no navegador quando estiver pronta."""
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

URL = "http://127.0.0.1:5000/"
BASE = Path(__file__).resolve().parent


def servidor_ativo() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 5000), timeout=0.3):
            return True
    except OSError:
        return False


def executar(modo: str) -> int:
    if servidor_ativo():
        print("O servidor local ja esta a usar a porta 5000.")
        print("Fecha a janela anterior do PlatinumPath antes de iniciares outra.")
        print("Podes abrir a aplicacao atual em", URL)
        return 1

    script = "iniciar_com_psn.py" if modo == "psn" else "app.py"
    print("A iniciar PlatinumPath ({}).".format("PSN" if modo == "psn" else "offline"), flush=True)
    if modo == "psn":
        print("Quando for pedido, cola o NPSSO no terminal. O texto nao aparece por seguranca.", flush=True)
    print("Para parar a aplicacao, fecha esta janela ou usa Ctrl+C.", flush=True)

    processo = subprocess.Popen([sys.executable, str(BASE / script)], cwd=BASE)
    aberto = False
    limite = time.monotonic() + 90
    while time.monotonic() < limite:
        if processo.poll() is not None:
            print("O servidor terminou antes de iniciar a interface.")
            return processo.returncode or 1
        try:
            with urllib.request.urlopen(URL, timeout=0.5):
                pass
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.5)
            continue
        aberto = bool(webbrowser.open(URL))
        if not aberto:
            print("Abre manualmente no navegador:", URL)
        else:
            print("A interface esta aberta em", URL)
        break
    if not aberto and time.monotonic() >= limite:
        print("Ainda nao abriu o navegador. Visita manualmente:", URL)
    try:
        return processo.wait()
    except KeyboardInterrupt:
        processo.terminate()
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processo.kill()
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Iniciar o PlatinumPath no navegador")
    modos = parser.add_mutually_exclusive_group(required=True)
    modos.add_argument("--psn", action="store_true", help="pedir NPSSO e ativar a PSN")
    modos.add_argument("--offline", action="store_true", help="iniciar sem NPSSO")
    args = parser.parse_args()
    return executar("psn" if args.psn else "offline")


if __name__ == "__main__":
    sys.exit(main())
