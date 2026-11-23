"""Inicia a aplicação sem guardar o NPSSO em ficheiros."""
import getpass
import os
import subprocess
import sys
from pathlib import Path

def main():
    token = getpass.getpass('NPSSO da PlayStation (não é guardado): ').strip()
    if not token:
        print('NPSSO não introduzido.')
        return 1
    env = os.environ.copy()
    env['PSN_NPSSO'] = token
    return subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'app.py')],
                   cwd=Path(__file__).resolve().parent, env=env, check=False).returncode

if __name__ == '__main__':
    sys.exit(main())
