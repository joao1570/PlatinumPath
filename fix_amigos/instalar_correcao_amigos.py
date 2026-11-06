"""Aplica correção de lentidão e avatares à secção Amigos existente."""
from pathlib import Path
from shutil import copy2
from datetime import datetime
pasta = Path(__file__).resolve().parent.parent
alvo = pasta / 'amigos.py'
origem = pasta / 'fix_amigos' / 'amigos_paginados.py'
template = pasta / 'templates' / 'amigos.html'
if not alvo.exists() or not origem.exists() or not template.exists() or not (pasta / 'app.py').exists():
    raise SystemExit('Extrai todo o ZIP na pasta PlatinumPath, junto ao app.py.')
s = alvo.read_text(encoding='utf-8')
a = s.find('@amigos_bp.route(\'/amigos\')')
b = s.find('@amigos_bp.route(\'/amigos/pesquisar\')', a)
if a < 0 or b < 0:
    raise SystemExit('Estrutura do amigos.py diferente do esperado; não foi alterada.')
novo = '''@amigos_bp.route('/amigos')
def lista_amigos():
    from amigos_paginados import obter_pagina
    from flask import request
    try:
        pagina = max(1, int(request.args.get('pagina', 1)))
    except (ValueError, TypeError):
        pagina = 1
    atualizar = request.args.get('atualizar') == '1'
    with conexao() as c:
        guardados = [dict(x) for x in c.execute('SELECT * FROM amigos_guardados ORDER BY online_id').fetchall()]
    oficiais, erro, total, pagina_real = [], None, 0, pagina
    try:
        oficiais, pagina_real, total, erro = obter_pagina(cliente(), pagina, atualizar)
    except Exception as exc:
        erro = f'PSN indisponível: {type(exc).__name__}. Tenta abrir novamente.'
    vistos = {x['id'].lower() for x in oficiais}
    # Os jogadores guardados aparecem na primeira página.
    if pagina_real == 1:
        for g in guardados:
            if g['online_id'].lower() not in vistos:
                oficiais.append({'id': g['online_id'], 'avatar': g['avatar_url'], 'plus': False})
    return render_template('amigos.html', amigos=oficiais,
        guardados={x['online_id'].lower() for x in guardados}, erro=erro,
        pagina_amigos=pagina_real, total_psn=total, por_pagina=12)


'''
s = s[:a] + novo + s[b:]
# Corrige também avatares de perfis individuais / jogadores pesquisados.
a = s.find('def avatar(dados):')
b = s.find('\ndef infos_usuario(', a)
if a >= 0 and b >= 0:
    s = s[:a] + '''def avatar(dados):
    from amigos_paginados import _avatar
    return _avatar(dados)

''' + s[b:]
h = template.read_text(encoding='utf-8')
if 'pagina_amigos' not in h:
    h += '''\n{% if total_psn > por_pagina %}
<div style="display:flex;gap:12px;justify-content:center;align-items:center;padding:22px;flex-wrap:wrap">
{% if pagina_amigos > 1 %}<a class="btn" href="{{ url_for('amigos.lista_amigos',pagina=pagina_amigos-1) }}">‹ Anteriores</a>{% endif %}
<span style="opacity:.75">Página {{ pagina_amigos }} de {{ (total_psn + por_pagina - 1) // por_pagina }}</span>
{% if pagina_amigos * por_pagina < total_psn %}<a class="btn primary" href="{{ url_for('amigos.lista_amigos',pagina=pagina_amigos+1) }}">Mais amigos ›</a>{% endif %}
</div>
{% endif %}
'''
# Move o bloco para dentro do main, antes do fim de body, mantendo estilo existente.
block = h[h.find('{% if total_psn > por_pagina %}'):]
h = h[:h.find('{% if total_psn > por_pagina %}')]
h = h.replace('</main>', block + '\n</main>')
# Se ficheiro teve alteração manual, backup sempre.
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
copy2(alvo, alvo.with_name('amigos.py.backup_' + stamp))
copy2(template, template.with_name('amigos.html.backup_' + stamp))
copy2(origem, pasta / 'amigos_paginados.py')
alvo.write_text(s, encoding='utf-8')
template.write_text(h, encoding='utf-8')
print('Correção instalada. Lista PSN paginada (12 amigos por página) e avatares repostos.')
print('Inicia: py -3.14 iniciar_com_psn.py')
