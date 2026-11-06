"""Inicia a aplicação sem guardar o NPSSO em ficheiros."""
import getpass
import os
import subprocess
import sys

def main():
    token = getpass.getpass('NPSSO da PlayStation (não é guardado): ').strip()
    if not token:
        print('NPSSO não introduzido.')
        return
    env = os.environ.copy()
    env['PSN_NPSSO'] = token
    subprocess.run([sys.executable, 'app.py'], env=env, check=False)

if __name__ == '__main__':
    main()
