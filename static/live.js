// Для демонстрации без сервера переключи одну строку на true.
const FAKE = false;
const Live = (() => {
  const labels = {pending: 'Waiting for review', approved: 'Approved · In queue', generating: 'Designing the blueprint', building: 'Building in Minecraft', done: 'Built!', rejected: 'Declined by moderator', failed: 'Build failed'};
  const demo = {type: 'init', requests: [{id: 1, text: 'Clock tower', author: 'Alex', status: 'building', program: null, blocks: 0}, {id: 2, text: 'Lighthouse', author: 'Sam', status: 'done', blocks: 1794, updated_at: '2026-10-02T20:00:00Z'}], stats: {built: 1, waiting: 1, blocks: 1794}, worker_online: true};
  function progress(data) {
    const total = Math.max(0, Number(data.total) || 0), done = Math.max(0, Math.min(total, Number(data.done) || 0));
    return {done, total, percent: total ? Math.round(done / total * 100) : 0};
  }
  function connect(path, receive, status) {
    if (FAKE) { status('Demo data'); receive(demo); return; }
    if (location.protocol === 'file:') { status('Open this page from the server, or enable FAKE in live.js.'); return; }
    let socket, timer;
    function open() {
      clearTimeout(timer); timer = null;
      status('Connecting…');
      socket = new WebSocket(location.origin.replace(/^http/, 'ws') + path);
      socket.onopen = () => status('Live · Connected');
      socket.onmessage = event => { try { receive(JSON.parse(event.data)); } catch (error) { console.error('Invalid live update', error); } };
      socket.onerror = () => socket.close();
      socket.onclose = () => { status('Offline · Reconnecting…'); timer = setTimeout(open, 1500); };
    }
    // После сна заново получаем снимок: события могли быть пропущены.
    function reconnect() { if (socket && socket.readyState < 2) socket.close(); else if (!socket || socket.readyState === 3) { clearTimeout(timer); open(); } }
    document.addEventListener('visibilitychange', () => { if (!document.hidden) reconnect(); });
    window.addEventListener('online', reconnect);
    open();
  }
  async function submit(body) {
    if (FAKE) return {id: Date.now(), text: body.text, author: body.author, status: 'pending'};
    let response;
    try { response = await fetch('/api/request', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)}); }
    catch { throw new Error('Connection lost. Check your latest request before sending again.'); }
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to send your request.');
    return data;
  }
  function source(request) {
    const program = request.program || {}, names = {blueprint: 'Hand-built blueprint', osm: 'OpenStreetMap data', model: 'Designed by AI'};
    return [names[program.source], request.model || program.model].filter(Boolean).join(' · ');
  }
  return {connect, submit, labels, progress, source};
})();
