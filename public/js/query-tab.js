/**
 * Query Tab
 * Intelligence Dashboard style query interface
 */

function initQueryTab() {
  const panel = document.getElementById('query-tab-panel');
  
  panel.innerHTML = `
    <div class="query-container">
      <!-- Query Input -->
      <div class="query-input-section">
        <textarea 
          id="queryInput" 
          placeholder="Ask a question about this brain's knowledge..."
          class="query-textarea"
        ></textarea>

        <!-- Options Grid -->
        <div class="query-options">
          <div class="option-group">
            <label>Model:</label>
            <select id="queryModel" class="query-select">
              <option value="gpt-5.1" selected>GPT-5.1 (Default - Fast with 24h Caching)</option>
              <option value="gpt-5">GPT-5 (Maximum Reasoning Depth)</option>
              <option value="gpt-5-mini">GPT-5 Mini (Ultra Fast & Economical)</option>
            </select>
          </div>

          <div class="option-group">
            <label>Reasoning Mode:</label>
            <select id="queryMode" class="query-select">
              <option value="fast">Fast (Quick Extraction)</option>
              <option value="normal" selected>Normal (Balanced Depth)</option>
              <option value="deep">Deep (Maximum Analysis)</option>
              <option value="grounded">Grounded (Evidence-Focused)</option>
              <option value="raw">🔓 Raw (No Formatting)</option>
              <option value="report">Report (Academic Style)</option>
              <option value="innovation">💡 Innovation (Creative Synthesis)</option>
              <option value="consulting">📊 Consulting (Strategic)</option>
              <option value="executive">📊 Executive Summary</option>
            </select>
            <div id="modeHint" class="option-hint">
              Balanced depth mode - comprehensive answers with source citations
            </div>
          </div>
        </div>

        <!-- Enhancement Checkboxes -->
        <div class="query-enhancements">
          <label><input type="checkbox" id="evidenceMetrics"> Evidence Metrics</label>
          <label><input type="checkbox" id="enableSynthesis" checked> Synthesis</label>
          <label><input type="checkbox" id="coordinatorInsights" checked> Coordinator Insights</label>
          <label title="Build on the results of your previous query"><input type="checkbox" id="followUpMode"> Follow-up Mode</label>
        </div>

        <!-- Context Options -->
        <div class="query-context-options">
          <label><input type="checkbox" id="includeOutputs" checked> 📁 Include Output Files</label>
          <label><input type="checkbox" id="includeThoughts" checked> 💭 Include Thought Stream</label>
        </div>

        <!-- Action Buttons -->
        <div class="query-actions">
          <button id="executeQueryBtn" class="btn-primary" onclick="executeQuery()">🔍 Execute Query</button>
          <button onclick="clearQuery()" class="btn-secondary">Clear</button>
          
          <div class="export-controls">
            <label>Export:</label>
            <select id="exportFormat" class="query-select-sm">
              <option value="none">None</option>
              <option value="markdown">Markdown</option>
              <option value="json">JSON</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Suggestions -->
      <div id="querySuggestions" class="query-suggestions-container">
        <div class="suggestions-header">💡 Suggestions:</div>
        <div id="suggestionsList" class="suggestions-list">
          <!-- Populated by loadSuggestions() -->
        </div>
      </div>

      <!-- Loading State -->
      <div id="queryLoading" class="query-loading" style="display: none;">
        <div class="loading-spinner"></div>
        <div>Searching knowledge graph and synthesizing answer...</div>
        <div class="loading-hint">This may take 10-30 seconds</div>
      </div>

      <!-- Results -->
      <div id="queryResults" style="display: none;"></div>

      <!-- History -->
      <div id="queryHistory" style="display: none;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3>Query History</h3>
          <button onclick="clearQuery()" class="btn-secondary" style="padding: 4px 12px; font-size: 11px;">Clear All</button>
        </div>
        <div id="historyList"></div>
      </div>
    </div>
  `;

  loadQueryHistory();
  loadSuggestions();
}

async function loadSuggestions() {
  const container = document.getElementById('querySuggestions');
  const list = document.getElementById('suggestionsList');
  if (!container || !list) return;

  // Standard high-value prompts
  const standardPrompts = [
    { label: "🔬 Novel Concepts", text: "What are the most novel concepts discovered in this research?" },
    { label: "⚡ Actionable Tests", text: "What actionable tests or experiments were proposed?" },
    { label: "💰 Market Opportunity", text: "Identify the biggest market opportunities from these insights." },
    { label: "🚀 Commercialization", text: "Propose a strategy for commercialization based on these findings." },
    { label: "🎯 Strategic Direction", text: "What is the recommended strategic direction moving forward?" },
    { label: "🔗 Synthesis Results", text: "Summarize the key synthesis results across all research cycles." },
    { label: "🛡️ Defensible Ideas", text: "What are the most defensible ideas or proprietary insights?" },
    { label: "💵 Quick Wins", text: "Identify any quick wins or immediate next steps." },
    { label: "📋 Summary", text: "Provide a high-level executive summary of this entire brain." }
  ];

  // POPULATE STANDARD PROMPTS IMMEDIATELY
  let html = standardPrompts.map(p => `
    <div class="suggestion-chip" onclick="applySuggestion('${escapeHtml(p.text)}')">
      ${escapeHtml(p.label)}
    </div>
  `).join('');
  
  list.innerHTML = html;
  container.style.display = 'block';

  // FETCH DYNAMIC INSIGHTS IN THE BACKGROUND
  try {
    const response = await fetch('/api/query/suggestions');
    const data = await response.json();

    if (data.success && data.suggestions && data.suggestions.length > 0) {
      // Append dynamic suggestions to existing HTML
      const dynamicHtml = data.suggestions.map(s => `
        <div class="suggestion-chip" onclick="applySuggestion('${escapeHtml(s.text || s)}')">
          ${escapeHtml(s.text || s)}
        </div>
      `).join('');
      
      list.innerHTML += dynamicHtml;
    }
  } catch (e) {
    console.error('Failed to load dynamic suggestions:', e);
  }
}

function applySuggestion(text) {
  const input = document.getElementById('queryInput');
  if (input) {
    input.value = text;
    input.focus();
    // No longer auto-executing - let user review
  }
}

// Query state
let lastQueryResult = null;
let queryHistory = [];

function getHistoryKey() {
  const brainPath = window.currentBrainInfo?.brainPath || 'global';
  return `cosmo.queryHistory.${brainPath}`;
}

function saveQueryHistory() {
  localStorage.setItem(getHistoryKey(), JSON.stringify(queryHistory.slice(0, 50)));
}

function loadQueryHistory() {
  const saved = localStorage.getItem(getHistoryKey());
  if (saved) {
    try {
      queryHistory = JSON.parse(saved);
      updateQueryHistory();
    } catch (e) {
      console.error('Failed to load query history:', e);
      queryHistory = [];
    }
  } else {
    queryHistory = [];
    const historyDiv = document.getElementById('queryHistory');
    if (historyDiv) historyDiv.style.display = 'none';
  }
}

async function executeQuery() {
  const input = document.getElementById('queryInput');
  const query = input.value.trim();
  if (!query) return;

  const model = document.getElementById('queryModel').value;
  const mode = document.getElementById('queryMode').value;
  const evidenceMetrics = document.getElementById('evidenceMetrics').checked;
  const synthesis = document.getElementById('enableSynthesis').checked;
  const coordinatorInsights = document.getElementById('coordinatorInsights').checked;
  const includeOutputs = document.getElementById('includeOutputs').checked;
  const includeThoughts = document.getElementById('includeThoughts').checked;
  const exportFormat = document.getElementById('exportFormat').value;
  const followUpMode = document.getElementById('followUpMode').checked;

  const btn = document.getElementById('executeQueryBtn');
  const resultsDiv = document.getElementById('queryResults');
  const loadingDiv = document.getElementById('queryLoading');

  // Show loading
  resultsDiv.style.display = 'none';
  loadingDiv.style.display = 'block';
  btn.disabled = true;

  try {
    const response = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        model,
        mode,
        includeEvidenceMetrics: evidenceMetrics,
        enableSynthesis: synthesis,
        includeCoordinatorInsights: coordinatorInsights,
        includeOutputs,
        includeThoughts,
        exportFormat: exportFormat !== 'none' ? exportFormat : null,
        priorContext: (followUpMode && lastQueryResult) ? {
          query: lastQueryResult.query,
          answer: lastQueryResult.answer
        } : null
      })
    });

    const result = await response.json();
    
    if (result.error) {
      throw new Error(result.error);
    }

    // Save for follow-ups
    lastQueryResult = { query, answer: result.answer };
    queryHistory.unshift({ query, ...result });

    // Display result
    displayQueryResult(result);
    updateQueryHistory();
    saveQueryHistory();

  } catch (error) {
    resultsDiv.innerHTML = `<div class="error-message">❌ Error: ${error.message}</div>`;
    resultsDiv.style.display = 'block';
  }

  loadingDiv.style.display = 'none';
  btn.disabled = false;
}

function displayQueryResult(result) {
  const resultsDiv = document.getElementById('queryResults');
  
  const sourceCount = result.metadata?.sources?.memoryNodes || 0;
  const thoughtCount = result.metadata?.sources?.thoughts || 0;
  
  const html = `
    <div class="answer-card">
      <div class="answer-header">📝 ${escapeHtml(result.query || 'Query')}</div>
      <div class="answer-content">${marked.parse(result.answer)}</div>
      
      <div class="answer-metadata">
        <span>📊 ${sourceCount} memory nodes, ${thoughtCount} thoughts</span>
        <span>⚡ ${result.metadata.model}</span>
        <span>🎯 ${result.metadata.mode}</span>
        <span>🕐 ${new Date(result.metadata.timestamp).toLocaleTimeString()}</span>
      </div>
      
      ${result.metadata?.evidenceQuality ? `
        <div class="evidence-panel">
          <div class="panel-title">📊 Evidence Quality</div>
          <div>Quality: ${result.metadata.evidenceQuality.quality}</div>
          <div>Confidence: ${((result.metadata.evidenceQuality.confidence || 0) * 100).toFixed(0)}%</div>
        </div>
      ` : ''}
      
      ${result.metadata?.synthesis ? `
        <div class="synthesis-panel">
          <div class="panel-title">🔬 Synthesis</div>
          <div>${result.metadata.synthesis.summary || 'Included in response'}</div>
        </div>
      ` : ''}
    </div>
  `;
  
  resultsDiv.innerHTML = html;
  resultsDiv.style.display = 'block';
  resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

function updateQueryHistory() {
  const historyDiv = document.getElementById('queryHistory');
  const listDiv = document.getElementById('historyList');
  
  if (queryHistory.length === 0) {
    if (historyDiv) historyDiv.style.display = 'none';
    return;
  }
  
  listDiv.innerHTML = queryHistory.map((item, i) => `
    <div class="history-item" onclick="loadHistoryItem(${i})">
      <div class="history-query">${escapeHtml(item.query || '')}</div>
      <div class="history-meta">${item.metadata?.mode || 'normal'} · ${new Date(item.metadata?.timestamp || Date.now()).toLocaleString()}</div>
    </div>
  `).join('');
  
  historyDiv.style.display = 'block';
}

function loadHistoryItem(index) {
  const item = queryHistory[index];
  document.getElementById('queryInput').value = item.query || '';
  displayQueryResult(item);
  // Update lastQueryResult so follow-up mode works from this point
  lastQueryResult = { query: item.query, answer: item.answer };
}

function clearQuery() {
  document.getElementById('queryInput').value = '';
  document.getElementById('queryResults').style.display = 'none';
  lastQueryResult = null;
  
  if (confirm('Clear query history for this brain?')) {
    queryHistory = [];
    saveQueryHistory();
    updateQueryHistory();
    const historyDiv = document.getElementById('queryHistory');
    if (historyDiv) historyDiv.style.display = 'none';
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

