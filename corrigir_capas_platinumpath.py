"""PlatinumPath: remove o emoji de comando atras das capas dos jogos.

Altera apenas templates/index.html. Preserva imagens, funcionalidades e dados.
Cria um backup na mesma pasta do template antes de alterar.
"""
from pathlib import Path
from datetime import datetime
import re
import shutil

root = Path(__file__).resolve().parent
p = root / 'templates' / 'index.html'
if not (root / 'app.py').is_file() or not p.is_file():
    raise SystemExit('ERRO: poe este ficheiro junto do app.py, na pasta PlatinumPath.')
html = p.read_text(encoding='utf-8')

# O placeholder 🎮 aparece sempre, mesmo quando a capa carrega.
# Remove-se o emoji e acrescenta-se um fallback apenas quando necessario.
pat = re.compile(
    r'(?P<open><div class="cover">)\s*🎮\s*'
    r'(?P<if>\{% if jogo\["imagem_url"\] %\})'
    r'(?P<body>.*?)'
    r'(?P<end>\{% endif %\}\s*</div>)',
    re.S,
)

def replace(m):
    inner = m.group('body')
    old = 'onerror="this.style.display=\'none\'"'
    new = 'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'block\'"'
    if old not in inner:
        raise ValueError('O evento onerror da capa mudou; nao alterei nada.')
    inner = inner.replace(old, new, 1)
    fallback = '<span class="cover-fallback" style="display:none;font-size:12px;color:#9caecc">Sem capa</span>'
    return (
        m.group('open') + '\n                    ' + m.group('if')
        + inner.rstrip() + '\n                        ' + fallback
        + '\n                    {% else %}\n'
        + '                        <span class="cover-fallback" style="font-size:12px;color:#9caecc">Sem capa</span>\n'
        + '                    {% endif %}\n                </div>'
    )

updated, count = pat.subn(replace, html)
if count == 0:
    if 'class="cover-fallback"' in html:
        print('Correcao ja aplicada. Nada a fazer.')
        raise SystemExit(0)
    raise SystemExit('ERRO: nao encontrei a estrutura esperada das capas; nao alterei nada.')
if count != 1:
    raise SystemExit(f'ERRO: encontrei {count} blocos de capas; nao alterei nada.')

backup = root.parent / f"{root.name}_backup_correcao_capas_{datetime.now():%Y%m%d_%H%M%S}" / "templates" / "index.html"
backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(p, backup)
p.write_text(updated, encoding='utf-8')
print('SUCESSO! Emoji de comando removido de tras das imagens dos jogos.')
print('O texto Sem capa aparece apenas quando nao ha imagem ou esta falha.')
print('Backup:', backup)
print('Reinicia a app e carrega Ctrl+F5 no navegador.')
