/* ── SSE Consumer & DOM Card Renderer ────────────────── */

const feed = document.getElementById('feed');
const feedPlaceholder = document.getElementById('feedPlaceholder');
const runBtn = document.getElementById('runBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const timestampEl = document.getElementById('timestamp');

// Update clock
function updateClock() {
    const now = new Date();
    timestampEl.textContent = now.toLocaleTimeString('en-IN', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// Icon map for each step type
const ICONS = {
    init: '⏳',
    data_ready: '📊',
    prepare: '⚙',
    market_context: '🌐',
    fundamental: '📋',
    technical: '📈',
    risk_manager: '🛡',
    orchestrator_initial: '🧠',
    orchestrator_final: '✅',
    error: '❌',
    done: '✓',
};

const ICON_CLASS = {
    prepare: 'prepare',
    market_context: 'market',
    fundamental: 'fundamental',
    technical: 'technical',
    risk_manager: 'risk',
    orchestrator_initial: 'decision',
    orchestrator_final: 'decision',
};

// ── Card Builders ───────────────────────────────────────

function buildInfoCard(data) {
    return `
        <div class="agent-card info-card">
            <div class="card-header">
                <div class="card-label">
                    <div class="card-icon ${ICON_CLASS[data.step] || 'prepare'}">${ICONS[data.step] || '•'}</div>
                    <span class="card-title">${esc(data.label)}</span>
                </div>
            </div>
            <div class="card-body">${esc(data.message || '')}</div>
        </div>`;
}

function buildMarketCard(data) {
    return `
        <div class="agent-card info-card">
            <div class="card-header">
                <div class="card-label">
                    <div class="card-icon market">🌐</div>
                    <span class="card-title">${esc(data.label)}</span>
                </div>
            </div>
            <div class="card-body">
                <p>Fear & Greed: <strong>${esc(data.fear_greed)}</strong> (${esc(data.fear_greed_value)}/100)</p>
                <p>Market Breadth: ${esc(data.breadth)}</p>
                <p>Headlines Parsed: ${data.headline_count}</p>
            </div>
        </div>`;
}

function buildAnalysisCard(data) {
    const signalClass = (data.signal || '').toLowerCase();
    const confLevel = data.confidence >= 70 ? 'high' : data.confidence >= 40 ? 'medium' : 'low';
    const factors = (data.key_factors || []).map(f => `<span class="factor-tag">${esc(f)}</span>`).join('');

    return `
        <div class="agent-card">
            <div class="card-header">
                <div class="card-label">
                    <div class="card-icon ${ICON_CLASS[data.step] || ''}">${ICONS[data.step] || '📊'}</div>
                    <span class="card-title">${esc(data.label)}</span>
                </div>
                <span class="signal-badge ${signalClass}">${esc(data.signal)}</span>
            </div>
            <div class="confidence-row">
                <span class="confidence-label">Confidence</span>
                <div class="confidence-track">
                    <div class="confidence-fill ${confLevel}" style="width: ${data.confidence}%"></div>
                </div>
                <span class="confidence-value">${data.confidence}%</span>
            </div>
            ${factors ? `<div class="factors">${factors}</div>` : ''}
            <div class="card-body">
                <p>${esc(data.analysis || '')}</p>
            </div>
        </div>`;
}

function buildRiskCard(data) {
    const verdictClass = (data.verdict || '').toLowerCase();
    const confAdj = data.confidence_adjustment ? ` → Adjusted to ${data.confidence_adjustment}%` : '';

    return `
        <div class="agent-card">
            <div class="card-header">
                <div class="card-label">
                    <div class="card-icon risk">🛡</div>
                    <span class="card-title">${esc(data.label)}</span>
                </div>
                <span class="signal-badge ${verdictClass}">${esc(data.verdict)} · ${esc(data.risk_level)}</span>
            </div>
            <div class="card-body">
                <p>${esc(data.critique)}${confAdj}</p>
            </div>
        </div>`;
}

function buildDecisionCard(data) {
    const decisionClass = (data.decision || '').toLowerCase();
    const isSell = decisionClass === 'sell';
    const confLevel = data.confidence >= 70 ? 'high' : data.confidence >= 40 ? 'medium' : 'low';

    return `
        <div class="agent-card final-decision ${isSell ? 'sell-decision' : ''}">
            <div class="card-header">
                <div class="card-label">
                    <div class="card-icon decision">${isSell ? '🔴' : '🟢'}</div>
                    <span class="card-title">${esc(data.label)}</span>
                </div>
                <span class="signal-badge ${decisionClass}">${esc(data.decision)}</span>
            </div>
            <div class="confidence-row">
                <span class="confidence-label">Confidence</span>
                <div class="confidence-track">
                    <div class="confidence-fill ${confLevel}" style="width: ${data.confidence}%"></div>
                </div>
                <span class="confidence-value">${data.confidence}%</span>
            </div>
            <div class="card-body">
                <p class="meta-line">Entry: ₹${Number(data.entry_price).toFixed(2)}</p>
                <p><strong>Reasoning:</strong> ${esc(data.reasoning)}</p>
                <p><strong>Risk Notes:</strong> ${esc(data.risk_notes)}</p>
                ${data.ft_summary ? `<p><strong>Summary:</strong> ${esc(data.ft_summary)}</p>` : ''}
            </div>
        </div>`;
}

// ── Main SSE Handler ────────────────────────────────────

function startAnalysis() {
    // Clear feed
    feed.innerHTML = '';
    feedPlaceholder?.remove();

    // UI state
    runBtn.disabled = true;
    runBtn.querySelector('.btn-text').textContent = 'Running...';
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

        let cardHTML = '';

        switch (data.step) {
            case 'init':
            case 'data_ready':
            case 'prepare':
                cardHTML = buildInfoCard(data);
                break;

            case 'market_context':
                cardHTML = buildMarketCard(data);
                break;

            case 'fundamental':
            case 'technical':
                cardHTML = buildAnalysisCard(data);
                break;

            case 'risk_manager':
                cardHTML = buildRiskCard(data);
                break;

            case 'orchestrator_initial':
                cardHTML = buildAnalysisCard({
                    ...data,
                    signal: data.decision,
                    key_factors: [],
                    analysis: data.reasoning,
                });
                break;

            case 'orchestrator_final':
                cardHTML = buildDecisionCard(data);
                break;

            case 'error':
                cardHTML = buildInfoCard(data);
                statusDot.className = 'status-dot error';
                statusText.textContent = 'Error';
                break;

            case 'done':
                statusDot.className = 'status-dot done';
                statusText.textContent = 'Analysis complete';
                runBtn.disabled = false;
                runBtn.querySelector('.btn-text').textContent = 'Run Analysis';
                source.close();
                return;

            default:
                cardHTML = buildInfoCard(data);
        }

        if (cardHTML) {
            feed.insertAdjacentHTML('beforeend', cardHTML);
            // Scroll the new card into view
            feed.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }

        // Update status
        statusText.textContent = data.label || 'Processing...';
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
function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
}

// Bind button
runBtn.addEventListener('click', startAnalysis);
