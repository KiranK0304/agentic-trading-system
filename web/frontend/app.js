/* ── UI Logic & State ──────────────────────────────────── */

const landingScreen = document.getElementById('landingScreen');
const mainDashboard = document.getElementById('mainDashboard');
const enterBtn = document.getElementById('enterBtn');

const feed = document.getElementById('feed');
const feedPlaceholder = document.getElementById('feedPlaceholder');
const runBtn = document.getElementById('runBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const timestampEl = document.getElementById('timestamp');

// Enter Simulation Button
enterBtn.addEventListener('click', () => {
    landingScreen.classList.add('hidden');
    mainDashboard.classList.remove('hidden');
});

// Update clock
function updateClock() {
    const now = new Date();
    timestampEl.textContent = now.toLocaleTimeString('en-IN', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// Toggle text expansion for "See more"
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

// ── Agent Avatars & Meta Data ───────────────────────────

const AGENT_META = {
    init: { sys: true },
    data_ready: { sys: true },
    prepare: { sys: true },
    market_context: { name: 'Market Observer', class: 'fund', initials: 'MO' },
    fundamental: { name: 'Fundamental Agent', class: 'fund', initials: 'FA' },
    technical: { name: 'Technical Agent', class: 'tech', initials: 'TA' },
    risk_manager: { name: 'Risk Manager', class: 'risk', initials: 'RM' },
    orchestrator_initial: { name: 'Orchestrator', class: 'orch', initials: 'OR' },
    orchestrator_final: { name: 'Orchestrator', class: 'orch', initials: 'OR' },
    error: { sys: true },
    done: { sys: true },
};

// ── Chat Message Builders ───────────────────────────────

function buildChatWrapper(data, innerHTML, isDecision = false, isSell = false) {
    const meta = AGENT_META[data.step] || { sys: true };
    
    if (meta.sys) {
        return `
            <div class="chat-message system">
                <div class="chat-bubble">
                    ${innerHTML}
                </div>
            </div>
        `;
    }

    let bubbleClass = isDecision ? 'decision-bubble' : '';
    if (isSell) bubbleClass += ' sell';

    return `
        <div class="chat-message">
            <div class="chat-avatar ${meta.class}">${meta.initials}</div>
            <div class="chat-content">
                <span class="chat-sender">${meta.name}</span>
                <div class="chat-bubble ${bubbleClass}">
                    ${innerHTML}
                </div>
            </div>
        </div>
    `;
}

function buildSystemMessage(data) {
    return buildChatWrapper(data, `<em>${esc(data.message || '')}</em>`);
}

function buildMarketMessage(data) {
    const html = `
        <div class="chat-header">
            <strong>${esc(data.label)}</strong>
        </div>
        <div class="text-content">
            <p>Fear &amp; Greed: <strong>${esc(data.fear_greed)}</strong> (${esc(data.fear_greed_value)}/100)</p>
            <p>Market Breadth: ${esc(data.breadth)}</p>
            <p>Headlines Parsed: ${data.headline_count}</p>
        </div>
    `;
    return buildChatWrapper(data, html);
}

function buildAnalysisMessage(data) {
    const signalClass = (data.signal || '').toLowerCase();
    const confLevel = data.confidence >= 70 ? 'high' : data.confidence >= 40 ? 'medium' : 'low';
    const factors = (data.key_factors || []).map(f => `<span class="factor-tag">${esc(f)}</span>`).join('');

    const html = `
        <div class="chat-header">
            <span class="signal-badge ${signalClass}">${esc(data.signal)}</span>
            <div class="confidence-row" style="margin:0;">
                <div class="confidence-track" style="width: 100px;">
                    <div class="confidence-fill ${confLevel}" style="width: ${data.confidence}%"></div>
                </div>
                <span class="confidence-value">${data.confidence}% conf.</span>
            </div>
        </div>

        ${factors ? `<div class="factors">${factors}</div>` : ''}
        
        <div class="text-content truncated">
            ${esc(data.analysis || '').replace(/\n/g, '<br/>')}
        </div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>
    `;
    return buildChatWrapper(data, html);
}

function buildRiskMessage(data) {
    const verdictClass = (data.verdict || '').toLowerCase();
    const confAdj = data.confidence_adjustment ? ` → Adjusted to ${data.confidence_adjustment}% conf.` : '';

    const html = `
        <div class="chat-header">
            <span class="signal-badge ${verdictClass}">${esc(data.verdict)} RISK</span>
            <strong>${esc(data.risk_level)} LEVEL</strong>
        </div>
        
        <div class="text-content truncated">
            ${esc(data.critique).replace(/\n/g, '<br/>')}
            ${confAdj ? `<br/><br/><strong>Confidence adjustment:</strong> ${confAdj}` : ''}
        </div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>
    `;
    return buildChatWrapper(data, html);
}

function buildDecisionMessage(data, isFinal) {
    const decisionClass = (data.decision || '').toLowerCase();
    const isSell = decisionClass === 'sell';
    const confLevel = data.confidence >= 70 ? 'high' : data.confidence >= 40 ? 'medium' : 'low';

    const html = `
        <div class="chat-header">
            <span class="signal-badge ${decisionClass}">${isFinal ? 'FINAL:' : 'INITIAL:'} ${esc(data.decision)}</span>
            <div class="confidence-row" style="margin:0;">
                <div class="confidence-track" style="width: 100px;">
                    <div class="confidence-fill ${confLevel}" style="width: ${data.confidence}%"></div>
                </div>
                <span class="confidence-value">${data.confidence}% conf.</span>
            </div>
        </div>

        <div class="text-content truncated">
            <div style="font-family: monospace; font-size: 0.8rem; margin-bottom: 0.5rem; color: var(--accent);">
                Entry/Exit Level: ₹${Number(data.entry_price).toFixed(2)}
            </div>
            
            <p><strong>Reasoning:</strong><br/>${esc(data.reasoning).replace(/\n/g, '<br/>')}</p>
            <br/>
            <p><strong>Risk Notes:</strong><br/>${esc(data.risk_notes).replace(/\n/g, '<br/>')}</p>
            ${data.ft_summary && isFinal ? `<br/><p><strong>Exec Summary:</strong><br/>${esc(data.ft_summary)}</p>` : ''}
        </div>
        <button class="see-more-btn" onclick="toggleText(this)">See more</button>
    `;
    return buildChatWrapper(data, html, true, isSell);
}

// ── Main SSE Handler ────────────────────────────────────

function startAnalysis() {
    feed.innerHTML = '';
    feedPlaceholder?.remove();

    runBtn.disabled = true;
    runBtn.querySelector('.btn-text').textContent = 'Running simulation...';
    statusDot.className = 'status-dot running';
    statusText.textContent = 'Pipeline active';

    const source = new EventSource('/api/analyze');

    source.onmessage = (event) => {
        let data;
        try {
            data = JSON.parse(event.data);
        } catch {
            return;
        }

        let chatHTML = '';

        switch (data.step) {
            case 'init':
            case 'data_ready':
            case 'prepare':
            case 'error':
            case 'done':
                chatHTML = buildSystemMessage(data);
                if (data.step === 'error') {
                    statusDot.className = 'status-dot error';
                    statusText.textContent = 'Error';
                    runBtn.disabled = false;
                }
                if (data.step === 'done') {
                    statusDot.className = 'status-dot done';
                    statusText.textContent = 'Simulation complete';
                    runBtn.disabled = false;
                    runBtn.querySelector('.btn-text').textContent = 'Run Analysis';
                    source.close();
                }
                break;

            case 'market_context':
                chatHTML = buildMarketMessage(data);
                break;

            case 'fundamental':
            case 'technical':
                chatHTML = buildAnalysisMessage(data);
                break;

            case 'risk_manager':
                chatHTML = buildRiskMessage(data);
                break;

            case 'orchestrator_initial':
                chatHTML = buildDecisionMessage({
                    ...data,
                    signal: data.decision,
                    key_factors: [],
                    analysis: data.reasoning,
                }, false);
                break;

            case 'orchestrator_final':
                chatHTML = buildDecisionMessage(data, true);
                break;

            default:
                chatHTML = buildSystemMessage(data);
        }

        if (chatHTML) {
            feed.insertAdjacentHTML('beforeend', chatHTML);
            // Auto scroll container
            const container = document.querySelector('.chat-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }
    };

    source.onerror = () => {
        source.close();
        statusDot.className = 'status-dot error';
        statusText.textContent = 'Connection lost';
        runBtn.disabled = false;
        runBtn.querySelector('.btn-text').textContent = 'Run Analysis';
    };
}

// Escape HTML utility
function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
}

runBtn.addEventListener('click', startAnalysis);
