// Shared client JS for Family Feud
(function () {
  const socket = io('/game');
  socket.on('connect', () => console.log('socket connected'));

  function safeCall(fn, arg) {
    try { if (typeof fn === 'function') fn(arg); } catch (err) { console.error('render error', err); }
  }

  function updateTeams(state) {
    if (!state) return;
    const t1Name = document.getElementById('team1Name');
    const t2Name = document.getElementById('team2Name');
    const t1Score = document.getElementById('team1Score');
    const t2Score = document.getElementById('team2Score');
    const t1Box = document.getElementById('team1Box');
    const t2Box = document.getElementById('team2Box');
    if (t1Name) t1Name.textContent = state.team1Name || 'Team 1';
    if (t2Name) t2Name.textContent = state.team2Name || 'Team 2';
    if (t1Score) t1Score.textContent = (state.team1Score ?? 0);
    if (t2Score) t2Score.textContent = (state.team2Score ?? 0);
    if (t1Box && t2Box) {
      if ((state.activeTeam || 1) === 1) { t1Box.classList.add('active'); t2Box.classList.remove('active'); }
      else { t2Box.classList.add('active'); t1Box.classList.remove('active'); }
    }
  }

  socket.on('state_update', state => {
    // call a page-level renderState if present
    safeCall(window.renderState, state);
    // also call optional hook
    safeCall(window.onStateUpdate, state);
    updateTeams(state);
  });

  // fetch initial state once
  fetch('/api/state').then(r => r.json()).then(state => {
    safeCall(window.renderState, state);
    safeCall(window.onStateUpdate, state);
    updateTeams(state);
  }).catch(() => {});

})();
