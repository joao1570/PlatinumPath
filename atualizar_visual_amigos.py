"""Atualiza apenas o visual da secção Amigos, preservando as restantes páginas."""
from pathlib import Path
from shutil import copy2
from datetime import datetime

base = Path(__file__).resolve().parent
if not (base / 'app.py').is_file() or not (base / 'amigos.py').is_file():
    raise SystemExit('ERRO: extrai os ficheiros na pasta principal do PlatinumPath (onde está app.py).')

origem = base / 'atualizacao_visual_amigos'
if not origem.exists():
    raise SystemExit('ERRO: falta a pasta atualizacao_visual_amigos do ZIP.')

arquivos = ['amigos.py', 'static/amigos.css', 'templates/amigos.html',
            'templates/amigo_perfil.html', 'templates/amigo_trofeus.html']
marca = datetime.now().strftime('%Y%m%d_%H%M%S')
for relativo in arquivos:
    destino = base / relativo
    fonte = origem / relativo
    if not fonte.is_file():
        raise SystemExit(f'ERRO: ficheiro em falta: {fonte}')
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        copia = destino.with_name(destino.name + f'.antes_visual_{marca}.bak')
        copy2(destino, copia)
    copy2(fonte, destino)
    print('Atualizado:', relativo)
print('Visual Amigos atualizado. Reinicia com: py -3.14 iniciar_com_psn.py')
