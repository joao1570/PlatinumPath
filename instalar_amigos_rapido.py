"""Instala otimização do carregamento de Amigos; não altera páginas nem DB."""
from pathlib import Path
from shutil import copy2
from datetime import datetime
base = Path(__file__).resolve().parent
origem = base / 'amigos_rapido' / 'amigos.py'
destino = base / 'amigos.py'
if not (base / 'app.py').exists() or not destino.exists() or not origem.exists():
    raise SystemExit('Extrai o ZIP na pasta do PlatinumPath (junto ao app.py e amigos.py).')
marca = datetime.now().strftime('%Y%m%d_%H%M%S')
backup = destino.with_name(destino.name + '.antes_rapido_' + marca + '.bak')
copy2(destino, backup)
copy2(origem, destino)
print('Amigos otimizado. Backup:', backup.name)
print('Inicia com: py -3.14 iniciar_com_psn.py')
