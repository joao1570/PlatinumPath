"""Corrige apenas os nomes das plataformas dos jogos dos amigos.
Não altera a cache, os avatares, os troféus nem o dashboard.
"""
from pathlib import Path
from datetime import datetime
from shutil import copy2
import ast

pasta = Path(__file__).resolve().parent
alvo = pasta / 'amigos.py'
if not alvo.is_file() or not (pasta / 'app.py').is_file():
    raise SystemExit('ERRO: Coloca corrigir_plataformas_amigos.py na pasta PlatinumPath, ao lado de app.py e amigos.py.')

texto = alvo.read_text(encoding='utf-8')
helper = '''def formatar_plataformas(valor):
    """Converte enums/frozenset da PSNAWP em PS3, PS4, PS5, etc."""
    import re
    if valor is None:
        return '—'
    valores = (list(valor) if isinstance(valor, (set, frozenset, list, tuple)) else [valor])
    nomes = []
    for item in valores:
        # Os enums da biblioteca expõem normalmente .value, por exemplo 'PS5'.
        bruto = str(getattr(item, 'value', item))
        for achado in re.findall(r'PS_VITA|PSVITA|PS VITA|PSPC|PS5|PS4|PS3|PSP|PC', bruto, re.I):
            rotulo = {'PS_VITA': 'PS Vita', 'PSVITA': 'PS Vita', 'PS VITA': 'PS Vita', 'PSPC': 'PC'}.get(achado.upper(), achado.upper())
            if rotulo not in nomes:
                nomes.append(rotulo)
    ordem = {'PS3': 0, 'PS4': 1, 'PS5': 2, 'PS Vita': 3, 'PSP': 4, 'PC': 5}
    return ', '.join(sorted(nomes, key=lambda x: ordem.get(x, 99))) if nomes else '—'


'''
if 'def formatar_plataformas(' not in texto:
    marcador = 'def stats(titulo):'
    if marcador not in texto:
        raise SystemExit('ERRO: Não encontrei a função stats(titulo). Nenhum ficheiro foi alterado.')
    texto = texto.replace(marcador, helper + marcador, 1)

# Altera apenas o campo plataforma no dicionário devolvido pela função stats.
original = "'plataforma': atributo(titulo, 'title_platform', 'titlePlatform', padrao=''),"
novo = "'plataforma': formatar_plataformas(atributo(titulo, 'title_platform', 'titlePlatform', padrao=''))," 
if original in texto:
    texto = texto.replace(original, novo, 1)
elif novo in texto:
    print('A correção já estava instalada. Não é necessário alterar nada.')
    raise SystemExit(0)
else:
    raise SystemExit('ERRO: O campo plataforma tem código diferente. Nenhum ficheiro foi alterado.')

try:
    ast.parse(texto)
except SyntaxError as exc:
    raise SystemExit(f'ERRO de sintaxe na alteração ({exc}). Nenhum ficheiro foi alterado.')

backup = alvo.with_name('amigos.py.backup_plataformas_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
copy2(alvo, backup)
alvo.write_text(texto, encoding='utf-8')
print('Plataformas dos jogos dos amigos corrigidas: PS3, PS4, PS5, PS Vita, etc.')
print('Backup criado:', backup.name)
print('A cache, os avatares, os troféus e o restante visual não foram alterados.')
print('Inicia: py -3.14 iniciar_com_psn.py')
