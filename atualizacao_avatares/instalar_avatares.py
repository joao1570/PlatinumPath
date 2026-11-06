from pathlib import Path
from shutil import copy2
from datetime import datetime

root = Path(__file__).resolve().parent
origem = root / 'amigos_paginados.py'
alvo = root / 'amigos_paginados.py'
# O instalador vive na pasta PlatinumPath/atualizacao_avatares
pasta = root.parent
alvo = pasta / 'amigos_paginados.py'
if not (pasta / 'app.py').exists() or not (pasta / 'amigos.py').exists():
    raise SystemExit('Extrai a pasta atualizacao_avatares dentro do PlatinumPath antes de executar.')
if not alvo.exists():
    raise SystemExit('Falta amigos_paginados.py. Instala primeiro a correção anterior dos Amigos.')
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
copy2(alvo, alvo.with_name('amigos_paginados.py.backup_' + stamp))
copy2(origem, alvo)
print('Corrigida a atualização dos avatares na cache. Os dados dos amigos permanecem guardados.')
print('Agora inicia: py -3.14 iniciar_com_psn.py')
