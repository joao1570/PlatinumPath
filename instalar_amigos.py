"""Instalador reversível: cria backup antes de alterar app.py e index.html."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
app = root / 'app.py'
if not app.is_file():
    raise SystemExit('ERRO: coloca todos os ficheiros deste ZIP na pasta principal PlatinumPath antes de executar.')
s = app.read_text(encoding='utf-8-sig')
if 'app.register_blueprint(amigos_bp)' not in s:
    import re
    m = re.search(r'^app\s*=\s*Flask\(__name__\).*$', s, re.MULTILINE)
    if not m:
        raise SystemExit('ERRO: não encontrei app = Flask(__name__) em app.py. Nada foi alterado.')
    shutil.copy2(app, app.with_name('app.py.antes_amigos.bak'))
    s = s[:m.end()] + '\n\nfrom amigos import amigos_bp\napp.register_blueprint(amigos_bp)\n' + s[m.end():]
    app.write_text(s, encoding='utf-8')
    print('Rotas /amigos instaladas no app.py (backup criado).')
else:
    print('Rotas /amigos já instaladas.')
index = root / 'templates' / 'index.html'
if index.is_file():
    html = index.read_text(encoding='utf-8-sig')
    if 'data-platinumpath-amigos' not in html and '</body>' in html.lower():
        shutil.copy2(index, index.with_name('index.html.antes_amigos.bak'))
        link = '''<a data-platinumpath-amigos href="/amigos" style="position:fixed;right:18px;bottom:18px;z-index:9999;background:#1765d8;color:#fff;padding:13px 19px;border-radius:28px;box-shadow:0 4px 18px #0008;font:bold 15px Arial,sans-serif;text-decoration:none">👥 Amigos</a>\n'''
        pos = html.lower().rfind('</body>')
        index.write_text(html[:pos] + link + html[pos:], encoding='utf-8')
        print('Botão Amigos acrescentado ao dashboard (backup criado).')
else:
    print('AVISO: não encontrei templates/index.html; acede a http://127.0.0.1:5000/amigos')
print('Pronto. Para iniciar: python iniciar_com_psn.py')
