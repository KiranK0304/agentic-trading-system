/* ══════════════════════════════════════════════════════════
   Quantaire -1 — Live Simulation Dashboard JS
   ══════════════════════════════════════════════════════════ */

// ── DOM refs ────────────────────────────────────────────
const landingScreen  = document.getElementById('landingScreen');
const mainDashboard  = document.getElementById('mainDashboard');
const enterBtn       = document.getElementById('enterBtn');
const feed           = document.getElementById('feed');
const feedPlaceholder = document.getElementById('feedPlaceholder');
const statusDot      = document.getElementById('statusDot');
const statusText     = document.getElementById('statusText');
const timestampEl    = document.getElementById('timestamp');
const logStream      = document.getElementById('logStream');

// Countdown elements
const agentTimerEl      = document.getElementById('agentTimer');
const pnlTimerEl        = document.getElementById('pnlTimer');
const agentRingProgress = document.getElementById('agentRingProgress');
const pnlRingProgress   = document.getElementById('pnlRingProgress');

// Portfolio metric elements
const metricPosition   = document.getElementById('metricPosition');
const metricEntry      = document.getElementById('metricEntry');
const metricCurrent    = document.getElementById('metricCurrent');
const metricUnrealized = document.getElementById('metricUnrealized');
const metricRealized   = document.getElementById('metricRealized');
const metricCapital    = document.getElementById('metricCapital');
const metricTotal      = document.getElementById('metricTotal');

// Trade history elements
const tradeEmpty     = document.getElementById('tradeEmpty');
const tradeTable     = document.getElementById('tradeTable');
const tradeTableBody = document.getElementById('tradeTableBody');

// ═══════════════════════════════════════════════════════════
// 1. ANIMATED DOT GRID (Canvas) — Landing page
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
    const text = 'QUANTAIRE -1';
    let i = 0;
    function type() {
        if (i <= text.length) {
            const plain = text.substring(0, Math.min(i, 10));
            const accent = i > 10 ? `<span style="color:var(--accent)">${text.substring(10, i)}</span>` : '';
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
        // Start all live pollers
        startSimulation();
    }, 650);
});

// ═══════════════════════════════════════════════════════════
// 4. ACTIVITY LOG
// ═══════════════════════════════════════════════════════════
function addLog(message, statusClass = 'done') {
    const time = new Date().toLocaleTimeString('en-IN', { hour12: false });
    const template = `
        <div class="log-entry">
            <span class="timestamp-log">[${time}]</span>
            <span>${message}</span>
        </div>`;

    const prev = logStream.lastElementChild;
    if (prev && prev.classList.contains('active')) {
        prev.classList.remove('active');
        prev.classList.add(statusClass);
    }

    logStream.insertAdjacentHTML('beforeend', template);
    const cur = logStream.lastElementChild;
    cur.classList.add('active');
    logStream.scrollTop = logStream.scrollHeight;
}

// ═══════════════════════════════════════════════════════════
// 5. HELPER: Format Indian currency
// ═══════════════════════════════════════════════════════════
function formatINR(value) {
    const abs = Math.abs(value);
    const sign = value < 0 ? '-' : '';
    // Indian numbering: last 3 digits, then groups of 2
    const str = abs.toFixed(2);
    const [intPart, decPart] = str.split('.');
    let formatted = '';
    if (intPart.length <= 3) {
        formatted = intPart;
    } else {
        formatted = intPart.slice(-3);
        let remaining = intPart.slice(0, -3);
        while (remaining.length > 2) {
            formatted = remaining.slice(-2) + ',' + formatted;
            remaining = remaining.slice(0, -2);
        }
        if (remaining) formatted = remaining + ',' + formatted;
    }
    return `${sign}₹${formatted}.${decPart}`;
}

// ═══════════════════════════════════════════════════════════
// 6. COUNTDOWN TIMERS
// ═══════════════════════════════════════════════════════════
const RING_CIRCUMFERENCE = 2 * Math.PI * 17; // r=17 from SVG

let agentNextRun = null;
let agentIntervalMs = 30 * 60 * 1000;
let pnlNextRun = null;
let pnlIntervalMs = 5 * 60 * 1000;
let countdownIntervalId = null;

async function fetchSchedule() {
    try {
        const res = await fetch('/api/schedule');
        const data = await res.json();

        if (data.agent_run && data.agent_run.next_run) {
            agentNextRun = new Date(data.agent_run.next_run).getTime();
            agentIntervalMs = data.agent_run.interval_minutes * 60 * 1000;
        }
        if (data.price_update && data.price_update.next_run) {
            pnlNextRun = new Date(data.price_update.next_run).getTime();
            pnlIntervalMs = data.price_update.interval_minutes * 60 * 1000;
        }
    } catch (e) {
        console.warn('Failed to fetch schedule:', e);
    }
}

function updateCountdowns() {
    const now = Date.now();

    // Agent countdown
    if (agentNextRun) {
        const remaining = Math.max(0, agentNextRun - now);
        const totalMin = Math.floor(remaining / 60000);
        const totalSec = Math.floor((remaining % 60000) / 1000);
        agentTimerEl.textContent = `${String(totalMin).padStart(2, '0')}:${String(totalSec).padStart(2, '0')}`;

        // Progress ring (how much time has elapsed of the interval)
        const elapsed = agentIntervalMs - remaining;
        const progress = Math.min(1, elapsed / agentIntervalMs);
        const offset = RING_CIRCUMFERENCE * (1 - progress);
        agentRingProgress.style.strokeDashoffset = offset;

        // When countdown hits 0, refresh schedule
        if (remaining <= 0) {
            agentTimerEl.textContent = 'RUNNING...';
            agentTimerEl.classList.add('running-flash');
            agentNextRun = null;
            addLog('AGENT PIPELINE EXECUTING...');
            // Re-fetch schedule after a delay
            setTimeout(async () => {
                await fetchSchedule();
                await fetchPortfolio();
                agentTimerEl.classList.remove('running-flash');
                addLog('AGENT RUN COMPLETED');
            }, 90000); // Wait 90s for agent to finish
        }
    } else {
        agentTimerEl.textContent = '--:--';
    }

    // P&L countdown
    if (pnlNextRun) {
        const remaining = Math.max(0, pnlNextRun - now);
        const totalMin = Math.floor(remaining / 60000);
        const totalSec = Math.floor((remaining % 60000) / 1000);
        pnlTimerEl.textContent = `${String(totalMin).padStart(2, '0')}:${String(totalSec).padStart(2, '0')}`;

        const elapsed = pnlIntervalMs - remaining;
        const progress = Math.min(1, elapsed / pnlIntervalMs);
        const offset = RING_CIRCUMFERENCE * (1 - progress);
        pnlRingProgress.style.strokeDashoffset = offset;

        if (remaining <= 0) {
            pnlTimerEl.textContent = 'UPDATING...';
            pnlTimerEl.classList.add('running-flash');
            pnlNextRun = null;
            addLog('PRICE UPDATE RUNNING...');
            setTimeout(async () => {
                await fetchSchedule();
                await fetchPortfolio();
                pnlTimerEl.classList.remove('running-flash');
                addLog('P&L UPDATED');
            }, 15000); // Wait 15s for price fetch
        }
    } else {
        pnlTimerEl.textContent = '--:--';
    }
}

// ═══════════════════════════════════════════════════════════
// 7. PORTFOLIO POLLER
// ═══════════════════════════════════════════════════════════
let lastTradeCount = 0;

async function fetchPortfolio() {
    try {
        const res = await fetch('/api/portfolio');
        const data = await res.json();
        updatePortfolioUI(data);
    } catch (e) {
        console.warn('Failed to fetch portfolio:', e);
    }
}

function updatePortfolioUI(data) {
    // Position badge
    metricPosition.textContent = data.position;
    metricPosition.className = 'metric-value position-badge ' +
        (data.position === 'LONG' ? 'long' : data.position === 'SHORT' ? 'short' : 'neutral');

    // Prices
    metricEntry.textContent = data.entry_price > 0 ? `₹${Number(data.entry_price).toFixed(2)}` : '—';
    metricCurrent.textContent = data.current_price > 0 ? `₹${Number(data.current_price).toFixed(2)}` : '—';

    // P&L with color
    const unrealized = data.unrealized_pnl || 0;
    metricUnrealized.textContent = formatINR(unrealized);
    metricUnrealized.className = 'metric-value pnl ' + (unrealized > 0 ? 'positive' : unrealized < 0 ? 'negative' : '');

    const realized = data.realized_pnl || 0;
    metricRealized.textContent = formatINR(realized);
    metricRealized.className = 'metric-value pnl ' + (realized > 0 ? 'positive' : realized < 0 ? 'negative' : '');

    // Capital & Total
    metricCapital.textContent = formatINR(data.capital);
    metricTotal.textContent = formatINR(data.total_value);

    // Trade history
    const trades = data.trade_history || [];
    if (trades.length > 0) {
        tradeEmpty.classList.add('hidden');
        tradeTable.classList.remove('hidden');

        // Only update if new trades appeared
        if (trades.length !== lastTradeCount) {
            lastTradeCount = trades.length;
            tradeTableBody.innerHTML = '';

            // Show most recent first
            for (let i = trades.length - 1; i >= 0; i--) {
                const t = trades[i];
                const pnl = t.pnl || 0;
                const pnlClass = pnl > 0 ? 'positive' : pnl < 0 ? 'negative' : '';
                const dirClass = t.direction === 'LONG' ? 'long' : 'short';

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><span class="dir-badge ${dirClass}">${t.direction}</span></td>
                    <td>₹${Number(t.entry_price).toFixed(0)}</td>
                    <td>₹${Number(t.exit_price).toFixed(0)}</td>
                    <td class="pnl ${pnlClass}">${formatINR(pnl)}</td>
                `;
                tradeTableBody.appendChild(row);
            }

            // Remove placeholder if first trade
            if (feedPlaceholder && trades.length > 0) {
                feedPlaceholder.remove();
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════
// 7b. AGENT FEED — Render all agent cards from /api/last-run
// ═══════════════════════════════════════════════════════════
let lastRunTimestamp = null;

async function fetchLastRun() {
    try {
        const res = await fetch('/api/last-run');
        const data = await res.json();
        if (data && data.timestamp && data.timestamp !== lastRunTimestamp) {
            lastRunTimestamp = data.timestamp;
            renderAgentFeed(data);
        }
    } catch (e) {
        console.warn('Failed to fetch last run:', e);
    }
}

function renderAgentFeed(data) {
    if (feedPlaceholder) feedPlaceholder.remove();
    feed.innerHTML = '';

    // Fundamental Analysis
    if (data.fundamental) {
        const d = data.fundamental;
        const sc = (d.signal || 'NEUTRAL').toLowerCase();
        const conf = d.confidence || 50;
        const cl = conf >= 70 ? 'high' : conf >= 40 ? 'medium' : 'low';
        const ft = (d.key_factors || []).map(f => `<span class="factor-tag">${esc(f)}</span>`).join('');
        feed.innerHTML += `
            <div class="chat-message">
                <div class="chat-avatar fund">FA</div>
                <div class="chat-content">
                    <span class="chat-sender">Fundamental Agent</span>
                    <div class="chat-bubble glow-enter">
                        <div class="chat-header">
                            <span class="signal-badge ${sc}">${esc(d.signal)}</span>
                            <div class="confidence-row">
                                <div class="confidence-track"><div class="confidence-fill ${cl}" style="width:${conf}%"></div></div>
                                <span class="confidence-value">${conf}%</span>
                            </div>
                        </div>
                        ${ft ? `<div class="factors">${ft}</div>` : ''}
                        <div class="text-content truncated">${esc(d.analysis || '').replace(/\n/g, '<br/>')}</div>
                        <button class="see-more-btn" onclick="toggleText(this)">See more</button>
                    </div>
                </div>
            </div>`;
    }

    // Technical Analysis
    if (data.technical) {
        const d = data.technical;
        const sc = (d.signal || 'NEUTRAL').toLowerCase();
        const conf = d.confidence || 50;
        const cl = conf >= 70 ? 'high' : conf >= 40 ? 'medium' : 'low';
        const ft = (d.key_factors || []).map(f => `<span class="factor-tag">${esc(f)}</span>`).join('');
        feed.innerHTML += `
            <div class="chat-message">
                <div class="chat-avatar tech">TA</div>
                <div class="chat-content">
                    <span class="chat-sender">Technical Agent</span>
                    <div class="chat-bubble glow-enter">
                        <div class="chat-header">
                            <span class="signal-badge ${sc}">${esc(d.signal)}</span>
                            <div class="confidence-row">
                                <div class="confidence-track"><div class="confidence-fill ${cl}" style="width:${conf}%"></div></div>
                                <span class="confidence-value">${conf}%</span>
                            </div>
                        </div>
                        ${ft ? `<div class="factors">${ft}</div>` : ''}
                        <div class="text-content truncated">${esc(d.analysis || '').replace(/\n/g, '<br/>')}</div>
                        <button class="see-more-btn" onclick="toggleText(this)">See more</button>
                    </div>
                </div>
            </div>`;
    }

    // Risk Manager
    if (data.risk_review) {
        const d = data.risk_review;
        const vc = (d.verdict || '').toLowerCase();
        const ca = d.confidence_adjustment ? ` → Adjusted to ${d.confidence_adjustment}%` : '';
        feed.innerHTML += `
            <div class="chat-message">
                <div class="chat-avatar risk">RM</div>
                <div class="chat-content">
                    <span class="chat-sender">Risk Manager</span>
                    <div class="chat-bubble glow-enter">
                        <div class="chat-header">
                            <span class="signal-badge ${vc}">${esc(d.verdict)} RISK</span>
                            <strong style="font-size:0.7rem;color:var(--txt2)">${esc(d.risk_level)} LEVEL</strong>
                        </div>
                        <div class="text-content truncated">${esc(d.critique).replace(/\n/g, '<br/>')}${ca ? `<br/><br/><em>Confidence${ca}</em>` : ''}</div>
                        <button class="see-more-btn" onclick="toggleText(this)">See more</button>
                    </div>
                </div>
            </div>`;
    }

    // Final Decision (Orchestrator)
    if (data.decision) {
        const d = data.decision;
        const dc = (d.decision || '').toLowerCase();
        const sell = dc === 'sell';
        const conf = d.confidence || 50;
        const cl = conf >= 70 ? 'high' : conf >= 40 ? 'medium' : 'low';
        feed.innerHTML += `
            <div class="chat-message particle-burst">
                <div class="chat-avatar orch">OR</div>
                <div class="chat-content">
                    <span class="chat-sender">Orchestrator</span>
                    <div class="chat-bubble glow-enter decision-bubble ${sell ? 'sell' : ''}">
                        <div class="chat-header">
                            <span class="signal-badge ${dc}">FINAL: ${esc(d.decision)}</span>
                            <div class="confidence-row">
                                <div class="confidence-track"><div class="confidence-fill ${cl}" style="width:${conf}%"></div></div>
                                <span class="confidence-value">${conf}%</span>
                            </div>
                        </div>
                        <div class="meta-block">Entry/Exit: ₹${Number(d.entry_price).toFixed(2)}</div>
                        <div class="text-content truncated" style="margin-top:0.6rem">
                            <p><strong>Reasoning:</strong><br/>${esc(d.reasoning).replace(/\n/g, '<br/>')}</p>
                            <br/><p><strong>Risk Notes:</strong><br/>${esc(d.risk_notes).replace(/\n/g, '<br/>')}</p>
                            ${d.ft_summary ? `<br/><p><strong>Summary:</strong><br/>${esc(d.ft_summary)}</p>` : ''}
                        </div>
                        <button class="see-more-btn" onclick="toggleText(this)">See more</button>
                    </div>
                </div>
            </div>`;
    }

    // Scroll to top of feed
    const container = document.getElementById('chatContainer');
    if (container) container.scrollTop = 0;
}

// See more / less toggle
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
// 8. SIMULATION START (all pollers)
// ═══════════════════════════════════════════════════════════
let portfolioIntervalId = null;
let scheduleRefreshId = null;
let lastRunPollId = null;

async function startSimulation() {
    addLog('SIMULATION DASHBOARD INITIALIZED');

    // Initial fetch
    await fetchSchedule();
    await fetchPortfolio();
    await fetchLastRun();
    addLog('PORTFOLIO STATE LOADED');

    // Start countdown timer (updates every second)
    countdownIntervalId = setInterval(updateCountdowns, 1000);

    // Poll portfolio every 10 seconds
    portfolioIntervalId = setInterval(fetchPortfolio, 10000);

    // Poll last run results every 30 seconds
    lastRunPollId = setInterval(fetchLastRun, 30000);

    // Refresh schedule every 60 seconds (to stay in sync)
    scheduleRefreshId = setInterval(fetchSchedule, 60000);

    addLog('ALL POLLERS ACTIVE');
}

// ═══════════════════════════════════════════════════════════
// 9. ESCAPE HTML UTILITY
// ═══════════════════════════════════════════════════════════
function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
}
