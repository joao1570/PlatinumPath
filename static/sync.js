(() => {
  const form = document.querySelector('#sync-form');
  if (!form) return;
  const status = document.querySelector('#sync-status'), details = document.querySelector('#sync-details'), log = document.querySelector('#sync-log');
  const buttons = [...form.querySelectorAll('button')];
  const offline = buttons.every(b => b.disabled);
  let timer;
  function render(data) {
    if (data.estado === 'inativo') return;
    const busy = data.estado === 'a_sincronizar';
    buttons.forEach(b => b.disabled = offline || busy);
    status.textContent = busy ? 'A sincronizar…' : data.estado === 'concluido' ? 'Concluído. Atualiza o dashboard.' : 'Sincronização incompleta. Consulta o registo.';
    details.hidden = false;
    log.textContent = (data.linhas || []).join('\n');
    if (busy) {clearTimeout(timer); timer = setTimeout(poll, 1500);}
  }
  async function poll() {
    try { const r = await fetch('/sincronizar/estado', {cache:'no-store'}); if (!r.ok) throw Error(); render(await r.json()); }
    catch {status.textContent = 'Não foi possível consultar o estado. A tentar novamente…'; timer = setTimeout(poll, 3000);}
  }
  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (e.submitter?.value === '0' && !confirm('Verificar todos os jogos pode demorar e atingir limites da PSN. Continuar?')) return;
    buttons.forEach(b => b.disabled = true);
    const body = new FormData(form); body.set('limite', e.submitter?.value || '30');
    try {
      const r = await fetch('/sincronizar', {method:'POST', body}); const data = await r.json();
      if (!r.ok) {status.textContent = data.erro || 'Não foi possível iniciar.'; if (r.status === 409) poll(); else buttons.forEach(b => b.disabled = offline); return;}
      render(data);
    } catch { status.textContent = 'Não foi possível confirmar o início. A verificar o estado…'; poll(); }
  });
  poll();
})();
