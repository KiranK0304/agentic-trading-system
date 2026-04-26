/* ══════════════════════════════════════════════════════════
   AgenticTrade — Premium JS v3 (All 15 Enhancements)
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

// ═══════════════════════════════════════════════════════════
// 1. ANIMATED DOT GRID (Canvas)
// ═══════════════════════════════════════════════════════════
(function initGrid() {
    const c = document.getElementById('gridCanvas');
    if (!c) return;
    const ctx = c.getContext('2d');
    let w, h;
    const spacing = 40;
    let tick = 0;

    function resize() {
        w = c.width = window.innerWidth;
        h = c.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    function draw() {
        ctx.clearRect(0, 0, w, h);
        tick += 0.003;
        for (let x = spacing; x < w; x += spacing) {
            for (let y = spacing; y < h; y += spacing) {
                const dist = Math.hypot(x - w / 2, y - h / 2);
                const wave = Math.sin(dist * 0.008 - tick * 3) * 0.5 + 0.5;
                const alpha = 0.02 + wave * 0.05;
                ctx.beginPath();
                ctx.arc(x, y, 0.8, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(80,200,120,${alpha})`;
                ctx.fill();
            }
        }
        requestAnimationFrame(draw);
    }
    draw();
})();

// ═══════════════════════════════════════════════════════════
// 2. TYPEWRITER TITLE
// ═══════════════════════════════════════════════════════════
(function typewriter() {
    const el = document.getElementById('typewriter');
    if (!el) return;
    const text = 'AgenticTrade';
    let i = 0;
    function type() {
        if (i <= text.length) {
            // Color the "Trade" portion in accent green
            const plain = text.substring(0, Math.min(i, 7));
            const accent = i > 7 ? `<span style="color:var(--accent)">${text.substring(7, i)}</span>` : '';
            el.innerHTML = plain + accent;
            i++;
            setTimeout(type, 100);
        }
    }
    setTimeout(type, 400);
})();

// ── Clock ───────────────────────────────────────────────
function updateClock() {
    timestampEl.textContent = new Date().toLocaleTimeString('en-IN', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ═══════════════════════════════════════════════════════════
// 3. LANDING → DASHBOARD (Diagonal wipe)
// ═══════════════════════════════════════════════════════════
enterBtn.addEventListener('click', () => {
    landingScreen.classList.add('exit');
    setTimeout(() => {
        landingScreen.classList.add('hidden');
        mainDashboard.classList.remove('hidden');
    }, 650);
});

// ═══════════════════════════════════════════════════════════
// 4. RIPPLE EFFECT ON RUN BUTTON
// ═══════════════════════════════════════════════════════════
runBtn.addEventListener('mousedown', (e) => {
    const rect = runBtn.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    ripple.style.width = ripple.style.height = `${Math.max(rect.width, rect.height)}px`;
    runBtn.querySelector('.ripple-container').appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);
});

// ── See more / less ─────────────────────────────────────
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

// ═══════════════════════════════════════════════════════════
// 5. RING PROGRESS
// ═══════════════════════════════════════════════════════════
const TOTAL_STEPS = 7;
let currentStep = 0;
const CIRCUMFERENCE = 2 * Math.PI * 90;

function updateRing(label) {
    currentStep++;
    const pct = Math.min(currentStep / TOTAL_STEPS, 1);
    ringProgress.style.strokeDashoffset = CIRCUMFERENCE * (1 - pct);
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

// ═══════════════════════════════════════════════════════════
// 6. TIMELINE DOTS
// ═══════════════════════════════════════════════════════════
const STAGE_MAP = { data: 0, macro: 1, fund: 2, tech: 3, risk: 4, final: 5 };
const tlDots = document.querySelectorAll('.tl-dot');
const tlLines = document.querySelectorAll('.tl-line');
let lastStageIdx = -1;

function activateStage(stage) {
    const idx = STAGE_MAP[stage];
    if (idx === undefined) return;
    // Mark previous dot as done
    if (lastStageIdx >= 0 && lastStageIdx < tlDots.length) {
        tlDots[lastStageIdx].classList.remove('active');
        tlDots[lastStageIdx].classList.add('done');
    }
    // Mark connecting line as done
    if (lastStageIdx >= 0 && lastStageIdx < tlLines.length) {
        tlLines[lastStageIdx].classList.add('done');
    }
    // Set current as active
    if (idx < tlDots.length) {
        tlDots[idx].classList.add('active');
    }
    lastStageIdx = idx;
}

function completeTimeline() {
    if (lastStageIdx >= 0 && lastStageIdx < tlDots.length) {
        tlDots[lastStageIdx].classList.remove('active');
        tlDots[lastStageIdx].classList.add('done');
    }
    if (lastStageIdx >= 0 && lastStageIdx < tlLines.length) {
        tlLines[lastStageIdx].classList.add('done');
    }
}

function resetTimeline() {
    tlDots.forEach(d => { d.classList.remove('active', 'done'); });
    tlLines.forEach(l => { l.classList.remove('done'); });
    lastStageIdx = -1;
}

// ═══════════════════════════════════════════════════════════
// AGENT META & MESSAGE BUILDERS
// ═══════════════════════════════════════════════════════════
const AGENT_META = {
    init:                { sys: true },
    data_ready:          { sys: true },
    prepare:             { sys: true },
    market_context:      { name: 'Market Observer',   cls: 'fund', initials: 'MO' },
    fundamental:         { name: 'Fundamental Agent', cls: 'fund', initials: 'FA' },
    technical:           { name: 'Technical Agent',   cls: 'tech', initials: 'TA' },
    risk_manager:        { name: 'Risk Manager',      cls: 'risk', initials: 'RM' },
    orchestrator_initial:{ name: 'Orchestrator',      cls: 'orch', initials: 'OR' },
    orchestrator_final:  { name: 'Orchestrator',      cls: 'orch', initials: 'OR' },
    error:               { sys: true },
    done:                { sys: true },
};

function wrap(data, inner, isDecision = false, isSell = false, isFinal = false) {
    const m = AGENT_META[data.step] || { sys: true };
    if (m.sys) {
        return `<div class="chat-message system"><div class="chat-bubble">${inner}</div></div>`;
    }
    const bc = isDecision ? `decision-bubble${isSell ? ' sell' : ''}` : '';
    const sparkles = isFinal ? buildSparkles() : '';
    const outerClass = isFinal ? 'particle-burst' : '';
    return `
        <div class="chat-message ${outerClass}">
            ${sparkles}
            <div class="chat-avatar ${m.cls}">${m.initials}</div>
            <div class="chat-content">
                <span class="chat-sender">${m.name}</span>
                <div class="chat-bubble glow-enter ${bc}">${inner}</div>
            </div>
        </div>`;
}

function buildSparkles() {
    const chars = ['›','»','·','+','×','‹'];
    let s = '';
    for (let i = 0; i < 6; i++) {
        s += `<span class="spark" style="font-size:${10 + Math.random()*4}px; color:var(--green)">${chars[i]}</span>`;
    }
    return s;
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
    const signal = d.signal || 'NEUTRAL';
    const conf = Number.isFinite(Number(d.confidence)) ? Number(d.confidence) : 50;
    const sc = String(signal).toLowerCase();
    const cl = conf >= 70 ? 'high' : conf >= 40 ? 'medium' : 'low';
    const ft = (d.key_factors || []).map(f => `<span class="factor-tag">${esc(f)}</span>`).join('');
    return wrap(d, `
        <div class="chat-header">
            <span class="signal-badge ${sc}">${esc(signal)}</span>
            <div class="confidence-row">
                <div class="confidence-track"><div class="confidence-fill ${cl}" style="width:${conf}%"></div></div>
                <span class="confidence-value">${conf}%</span>
            </div>
        </div>
        ${ft ? `<div class="factors">${ft}</div>` : ''}
        <div class="text-content truncated">${esc(d.analysis || '').replace(/\n/g, '<br/>')}</div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>`);
}

function riskMsg(d) {
    const vc = (d.verdict || '').toLowerCase();
    const ca = d.confidence_adjustment ? ` → Adjusted to ${d.confidence_adjustment}%` : '';
    return wrap(d, `
        <div class="chat-header">
            <span class="signal-badge ${vc}">${esc(d.verdict)} RISK</span>
            <strong style="font-size:0.7rem;color:var(--txt2)">${esc(d.risk_level)} LEVEL</strong>
        </div>
        <div class="text-content truncated">${esc(d.critique).replace(/\n/g, '<br/>')}${ca ? `<br/><br/><em>Confidence${ca}</em>` : ''}</div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>`);
}

function decisionMsg(d, isFinal) {
    const dc = (d.decision || '').toLowerCase();
    const sell = dc === 'sell';
    const conf = Number.isFinite(Number(d.confidence)) ? Number(d.confidence) : 50;
    const cl = conf >= 70 ? 'high' : conf >= 40 ? 'medium' : 'low';
    return wrap(d, `
        <div class="chat-header">
            <span class="signal-badge ${dc}">${isFinal ? 'FINAL:' : 'INITIAL:'} ${esc(d.decision)}</span>
            <div class="confidence-row">
                <div class="confidence-track"><div class="confidence-fill ${cl}" style="width:${conf}%"></div></div>
                <span class="confidence-value">${conf}%</span>
            </div>
        </div>
        <div class="meta-block">Entry/Exit: ₹${Number(d.entry_price).toFixed(2)}</div>
        <div class="text-content truncated" style="margin-top:0.6rem">
            <p><strong>Reasoning:</strong><br/>${esc(d.reasoning).replace(/\n/g, '<br/>')}</p>
            <br/><p><strong>Risk Notes:</strong><br/>${esc(d.risk_notes).replace(/\n/g, '<br/>')}</p>
            ${d.ft_summary && isFinal ? `<br/><p><strong>Summary:</strong><br/>${esc(d.ft_summary)}</p>` : ''}
        </div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>`, true, sell, isFinal);
}


// ═══════════════════════════════════════════════════════════
// TYPING INDICATOR + STAGGERED MESSAGE QUEUE
// ═══════════════════════════════════════════════════════════
const MESSAGE_DELAY = 450;
let messageQueue = [];
let isProcessing = false;

function buildTypingIndicator(step) {
    const m = AGENT_META[step] || { sys: true };
    if (m.sys) return null;
    return `
        <div class="typing-indicator" id="typingBubble">
            <div class="chat-avatar ${m.cls}">${m.initials}</div>
            <div class="chat-content">
                <span class="chat-sender">${m.name}</span>
                <div class="typing-dots"><span></span><span></span><span></span></div>
            </div>
        </div>`;
}

function enqueueMessage(html, step) {
    messageQueue.push({ html, step });
    if (!isProcessing) drainQueue();
}

function drainQueue() {
    if (messageQueue.length === 0) { isProcessing = false; return; }
    isProcessing = true;
    const { html, step } = messageQueue.shift();

    // Show typing indicator first
    const typingHTML = buildTypingIndicator(step);
    if (typingHTML) {
        feed.insertAdjacentHTML('beforeend', typingHTML);
        scrollChat();
        setTimeout(() => {
            const tb = document.getElementById('typingBubble');
            if (tb) tb.remove();
            insertMessage(html);
            setTimeout(drainQueue, MESSAGE_DELAY);
        }, 500);
    } else {
        insertMessage(html);
        setTimeout(drainQueue, MESSAGE_DELAY);
    }
}

function insertMessage(html) {
    feed.insertAdjacentHTML('beforeend', html);
    scrollChat();
}

function scrollChat() {
    const container = document.getElementById('chatContainer');
    if (container) container.scrollTop = container.scrollHeight;
}


// ═══════════════════════════════════════════════════════════
// SSE HANDLER
// ═══════════════════════════════════════════════════════════
function startAnalysis() {
    feed.innerHTML = '';
    feedPlaceholder?.remove();
    messageQueue = [];
    resetRing();
    resetTimeline();
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
                updateRing('DATA');
                activateStage('data');
                break;
            case 'market_context':
                html = marketMsg(d);
                updateRing('MACRO');
                activateStage('macro');
                break;
            case 'fundamental':
                html = analysisMsg(d);
                updateRing('FUND');
                activateStage('fund');
                break;
            case 'technical':
                html = analysisMsg(d);
                updateRing('TECH');
                activateStage('tech');
                break;
            case 'risk_manager':
                html = riskMsg(d);
                updateRing('RISK');
                activateStage('risk');
                break;
            case 'orchestrator_initial':
                html = decisionMsg({ ...d, signal: d.decision, analysis: d.reasoning }, false);
                updateRing('DECIDE');
                break;
            case 'orchestrator_final':
                html = decisionMsg(d, true);
                updateRing('FINAL');
                activateStage('final');
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
                completeTimeline();
                runBtn.disabled = false;
                runBtn.querySelector('.btn-text').textContent = 'Run Analysis';
                source.close();
                break;
            default:
                html = sysMsg(d);
        }
        if (html) enqueueMessage(html, d.step);
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

// ── Escape HTML ─────────────────────────────────────────
function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
}

runBtn.addEventListener('click', startAnalysis);
