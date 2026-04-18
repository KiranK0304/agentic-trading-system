/* ══════════════════════════════════════════════════════════
   AgenticTrade — Premium JS (SSE Consumer + Animations)
   ══════════════════════════════════════════════════════════ */

// ── DOM refs ────────────────────────────────────────────
const landingScreen = document.getElementById('landingScreen');
const mainDashboard = document.getElementById('mainDashboard');
const enterBtn      = document.getElementById('enterBtn');
const feed          = document.getElementById('feed');
const feedPlaceholder = document.getElementById('feedPlaceholder');
const runBtn        = document.getElementById('runBtn');
const statusDot     = document.getElementById('statusDot');
const statusText    = document.getElementById('statusText');
const timestampEl   = document.getElementById('timestamp');
const ambientRing   = document.getElementById('ambientRing');
const ringProgress  = document.getElementById('ringProgress');
const ringLabel     = document.getElementById('ringLabel');

// ── Clock ───────────────────────────────────────────────
function updateClock() {
    timestampEl.textContent = new Date().toLocaleTimeString('en-IN', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ── Landing → Dashboard transition ─────────────────────
enterBtn.addEventListener('click', () => {
    landingScreen.style.opacity = '0';
    landingScreen.style.transform = 'scale(1.03)';
    landingScreen.style.transition = 'all 0.5s cubic-bezier(0.16,1,0.3,1)';
    setTimeout(() => {
        landingScreen.classList.add('hidden');
        mainDashboard.classList.remove('hidden');
        mainDashboard.style.opacity = '0';
        requestAnimationFrame(() => {
            mainDashboard.style.transition = 'opacity 0.5s ease';
            mainDashboard.style.opacity = '1';
        });
    }, 400);
});

// ── See more / less toggle ──────────────────────────────
window.toggleText = function(btn) {
    const content = btn.previousElementSibling;
    if (content.classList.contains('truncated')) {
        content.classList.remove('truncated');
        btn.textContent = 'See less';
    } else {
        content.classList.add('truncated');
        btn.textContent = 'See more';
    }
};

// ── Ring progress animation ─────────────────────────────
const TOTAL_STEPS = 7; // init, data, prepare, market, fund, tech, risk, orch_init, orch_final
let currentStep = 0;
const CIRCUMFERENCE = 2 * Math.PI * 90; // r=90

function updateRing(step, label) {
    currentStep++;
    const pct = Math.min(currentStep / TOTAL_STEPS, 1);
    const offset = CIRCUMFERENCE * (1 - pct);
    ringProgress.style.strokeDashoffset = offset;
    ringLabel.textContent = label || 'WORKING';

    if (pct >= 1) {
        ringProgress.style.stroke = 'var(--green)';
        ringLabel.textContent = 'DONE';
    }
}

function resetRing() {
    currentStep = 0;
    ringProgress.style.strokeDashoffset = CIRCUMFERENCE;
    ringProgress.style.stroke = 'var(--accent)';
    ringLabel.textContent = 'IDLE';
    ambientRing.classList.remove('active');
}

// ── Agent metadata ──────────────────────────────────────
const AGENT_META = {
    init:                { sys: true },
    data_ready:          { sys: true },
    prepare:             { sys: true },
    market_context:      { name: 'Market Observer',    class: 'fund', initials: 'MO' },
    fundamental:         { name: 'Fundamental Agent',  class: 'fund', initials: 'FA' },
    technical:           { name: 'Technical Agent',    class: 'tech', initials: 'TA' },
    risk_manager:        { name: 'Risk Manager',       class: 'risk', initials: 'RM' },
    orchestrator_initial:{ name: 'Orchestrator',       class: 'orch', initials: 'OR' },
    orchestrator_final:  { name: 'Orchestrator',       class: 'orch', initials: 'OR' },
    error:               { sys: true },
    done:                { sys: true },
};

// ── Chat HTML Builders ──────────────────────────────────

function wrap(data, inner, isDecision = false, isSell = false) {
    const m = AGENT_META[data.step] || { sys: true };
    if (m.sys) {
        return `<div class="chat-message system"><div class="chat-bubble">${inner}</div></div>`;
    }
    const bc = isDecision ? `decision-bubble${isSell ? ' sell' : ''}` : '';
    return `
        <div class="chat-message">
            <div class="chat-avatar ${m.class}">${m.initials}</div>
            <div class="chat-content">
                <span class="chat-sender">${m.name}</span>
                <div class="chat-bubble ${bc}">${inner}</div>
            </div>
        </div>`;
}

function sysMsg(d) { return wrap(d, `<em>${esc(d.message || '')}</em>`); }

function marketMsg(d) {
    return wrap(d, `
        <div class="chat-header"><strong>${esc(d.label)}</strong></div>
        <div class="text-content">
            <p>Fear &amp; Greed: <strong>${esc(d.fear_greed)}</strong> (${esc(d.fear_greed_value)}/100)</p>
            <p>Market Breadth: ${esc(d.breadth)}</p>
            <p>Headlines: ${d.headline_count}</p>
        </div>`);
}

function analysisMsg(d) {
    const sc = (d.signal||'').toLowerCase();
    const cl = d.confidence>=70?'high':d.confidence>=40?'medium':'low';
    const ft = (d.key_factors||[]).map(f=>`<span class="factor-tag">${esc(f)}</span>`).join('');
    return wrap(d, `
        <div class="chat-header">
            <span class="signal-badge ${sc}">${esc(d.signal)}</span>
            <div class="confidence-row">
                <div class="confidence-track" style="width:90px"><div class="confidence-fill ${cl}" style="width:${d.confidence}%"></div></div>
                <span class="confidence-value">${d.confidence}%</span>
            </div>
        </div>
        ${ft?`<div class="factors">${ft}</div>`:''}
        <div class="text-content truncated">${esc(d.analysis||'').replace(/\n/g,'<br/>')}</div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>`);
}

function riskMsg(d) {
    const vc = (d.verdict||'').toLowerCase();
    const ca = d.confidence_adjustment ? ` → Adjusted to ${d.confidence_adjustment}%` : '';
    return wrap(d, `
        <div class="chat-header">
            <span class="signal-badge ${vc}">${esc(d.verdict)} RISK</span>
            <strong style="font-size:0.75rem">${esc(d.risk_level)} LEVEL</strong>
        </div>
        <div class="text-content truncated">${esc(d.critique).replace(/\n/g,'<br/>')}${ca?`<br/><br/><em>Confidence${ca}</em>`:''}</div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>`);
}

function decisionMsg(d, isFinal) {
    const dc = (d.decision||'').toLowerCase();
    const sell = dc==='sell';
    const cl = d.confidence>=70?'high':d.confidence>=40?'medium':'low';
    return wrap(d, `
        <div class="chat-header">
            <span class="signal-badge ${dc}">${isFinal?'FINAL:':'INITIAL:'} ${esc(d.decision)}</span>
            <div class="confidence-row">
                <div class="confidence-track" style="width:90px"><div class="confidence-fill ${cl}" style="width:${d.confidence}%"></div></div>
                <span class="confidence-value">${d.confidence}%</span>
            </div>
        </div>
        <div class="meta-block">Entry/Exit: ₹${Number(d.entry_price).toFixed(2)}</div>
        <div class="text-content truncated" style="margin-top:0.75rem">
            <p><strong>Reasoning:</strong><br/>${esc(d.reasoning).replace(/\n/g,'<br/>')}</p>
            <br/><p><strong>Risk Notes:</strong><br/>${esc(d.risk_notes).replace(/\n/g,'<br/>')}</p>
            ${d.ft_summary&&isFinal?`<br/><p><strong>Summary:</strong><br/>${esc(d.ft_summary)}</p>`:''}
        </div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>`, true, sell);
}

// ── Message Queue (staggered rendering) ─────────────────
const MESSAGE_DELAY = 350; // ms delay between each card
let messageQueue = [];
let isProcessing = false;

function enqueueMessage(html) {
    messageQueue.push(html);
    if (!isProcessing) drainQueue();
}

function drainQueue() {
    if (messageQueue.length === 0) { isProcessing = false; return; }
    isProcessing = true;
    const html = messageQueue.shift();
    feed.insertAdjacentHTML('beforeend', html);
    const container = document.getElementById('chatContainer');
    if (container) container.scrollTop = container.scrollHeight;
    setTimeout(drainQueue, MESSAGE_DELAY);
}

// ── Main SSE Handler ────────────────────────────────────

function startAnalysis() {
    feed.innerHTML = '';
    feedPlaceholder?.remove();
    messageQueue = [];
    resetRing();
    ambientRing.classList.add('active');

    runBtn.disabled = true;
    runBtn.querySelector('.btn-text').textContent = 'Analyzing...';
    statusDot.className = 'status-dot running';
    statusText.textContent = 'Pipeline active';

    const source = new EventSource('/api/analyze');

    source.onmessage = (event) => {
        let d;
        try { d = JSON.parse(event.data); } catch { return; }

        let html = '';
        switch (d.step) {
            case 'init': case 'data_ready': case 'prepare':
                html = sysMsg(d);
                updateRing(d.step, 'DATA');
                break;
            case 'market_context':
                html = marketMsg(d);
                updateRing(d.step, 'MACRO');
                break;
            case 'fundamental':
                html = analysisMsg(d);
                updateRing(d.step, 'FUND');
                break;
            case 'technical':
                html = analysisMsg(d);
                updateRing(d.step, 'TECH');
                break;
            case 'risk_manager':
                html = riskMsg(d);
                updateRing(d.step, 'RISK');
                break;
            case 'orchestrator_initial':
                html = decisionMsg({ ...d, signal:d.decision, analysis:d.reasoning }, false);
                updateRing(d.step, 'DECIDE');
                break;
            case 'orchestrator_final':
                html = decisionMsg(d, true);
                updateRing(d.step, 'FINAL');
                break;
            case 'error':
                html = sysMsg(d);
                statusDot.className = 'status-dot error';
                statusText.textContent = 'Error';
                break;
            case 'done':
                html = sysMsg(d);
                statusDot.className = 'status-dot done';
                statusText.textContent = 'Simulation complete';
                runBtn.disabled = false;
                runBtn.querySelector('.btn-text').textContent = 'Run Analysis';
                source.close();
                break;
            default:
                html = sysMsg(d);
        }
        if (html) enqueueMessage(html);
        statusText.textContent = d.label || 'Processing...';
    };

    source.onerror = () => {
        source.close();
        statusDot.className = 'status-dot error';
        statusText.textContent = 'Connection lost';
        runBtn.disabled = false;
        runBtn.querySelector('.btn-text').textContent = 'Run Analysis';
    };
}

// Escape HTML
function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
}

runBtn.addEventListener('click', startAnalysis);
