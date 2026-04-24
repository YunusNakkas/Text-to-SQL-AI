// ─── State ───
let history = JSON.parse(localStorage.getItem('tsql_history') || '[]');
let rawSQL = '';

// ─── Char counter ───
const nlInput = document.getElementById('nlInput');
nlInput.addEventListener('input', () => {
  document.getElementById('charCount').textContent = nlInput.value.length + '/500';
});

// ─── Generate ───
async function generateSQL() {
  const question = nlInput.value.trim();

  if (!question) {
    showError('Lütfen bir soru yazın.');
    return;
  }
  clearError();

  const btn = document.getElementById('generateBtn');
  btn.classList.add('loading');

  try {
    const response = await fetch('http://127.0.0.1:5001/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    const data = await response.json();

    if (!response.ok) {
      showError(data.error || 'Bir hata oluştu.');
      return;
    }

    rawSQL = data.sql;
    displayOutput(data.sql, '', data.columns, data.results);
    addHistory(question, data.sql, data.columns, data.results);
  } catch (err) {
    showError('Bağlantı hatası: ' + err.message);
  } finally {
    btn.classList.remove('loading');
  }
}

function displayOutput(sql, explain, columns, results) {
  const out = document.getElementById('outputCard');
  document.getElementById('sqlOutput').innerHTML = highlightSQL(sql);
  const es = document.getElementById('explainSection');
  if (explain) {
    document.getElementById('explainText').textContent = explain;
    es.style.display = '';
  } else {
    es.style.display = 'none';
  }

  // Display results table
  const rt = document.getElementById('resultsSection');
  if (columns && results) {
    let tableHtml = '<table class="results-table"><thead><tr>';
    columns.forEach(col => tableHtml += `<th>${col}</th>`);
    tableHtml += '</tr></thead><tbody>';
    results.forEach(row => {
      tableHtml += '<tr>';
      row.forEach(cell => tableHtml += `<td>${cell}</td>`);
      tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table>';
    document.getElementById('resultsContent').innerHTML = tableHtml;
    rt.style.display = '';
  } else {
    rt.style.display = 'none';
  }

  out.classList.add('show');
  out.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ─── Syntax highlight ───
function highlightSQL(sql) {
  const keywords = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|ON|AS|AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE|IS|NULL|ORDER BY|GROUP BY|HAVING|LIMIT|OFFSET|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|ALTER|DROP|INDEX|DISTINCT|UNION|ALL|CASE|WHEN|THEN|ELSE|END|WITH|OVER|PARTITION|BY|TOP|ROWNUM|ASC|DESC|PRIMARY|KEY|FOREIGN|REFERENCES|CONSTRAINT|DEFAULT|AUTO_INCREMENT|SERIAL|VARCHAR|INT|INTEGER|BIGINT|DECIMAL|FLOAT|DOUBLE|DATE|DATETIME|TIMESTAMP|BOOLEAN|TEXT|CHAR)\b/gi;
  const functions = /\b(COUNT|SUM|AVG|MIN|MAX|COALESCE|NULLIF|IFNULL|NVL|NOW|CURDATE|DATE_FORMAT|YEAR|MONTH|DAY|DATEDIFF|CONCAT|SUBSTRING|LENGTH|LOWER|UPPER|TRIM|ROUND|FLOOR|CEIL|ABS|MOD|CAST|CONVERT|ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD)\b/gi;
  const strings = /'([^']*)'/g;
  const nums = /\b(\d+)\b/g;
  const comments = /--.*/g;

  return sql
    .replace(comments, m => `<span class="cm">${m}</span>`)
    .replace(strings, (m, s) => `<span class="str">'${s}'</span>`)
    .replace(keywords, m => `<span class="kw">${m}</span>`)
    .replace(functions, m => `<span class="fn">${m}</span>`)
    .replace(nums, m => `<span class="num">${m}</span>`);
}

// ─── Copy ───
function copySql() {
  navigator.clipboard.writeText(rawSQL).then(() => {
    const btn = document.getElementById('copyBtn');
    btn.classList.add('copied');
    btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Kopyalandı`;
    setTimeout(() => {
      btn.classList.remove('copied');
      btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2v1"/></svg> Kopyala`;
    }, 2000);
  });
}

// ─── History ───
function addHistory(nl, sql, columns, results) {
  history.unshift({ nl, sql, columns, results, ts: Date.now() });
  if (history.length > 10) history = history.slice(0, 10);
  localStorage.setItem('tsql_history', JSON.stringify(history));
  renderHistory();
}

function renderHistory() {
  const card = document.getElementById('historyCard');
  const list = document.getElementById('historyList');
  if (!history.length) { card.style.display = 'none'; return; }
  card.style.display = '';
  list.innerHTML = history.map((h, i) => `
    <div class="history-item" onclick="loadHistory(${i})">
      <span class="history-nl">${escHtml(h.nl)}</span>
    </div>`).join('');
}

function loadHistory(i) {
  const h = history[i];
  nlInput.value = h.nl;
  document.getElementById('charCount').textContent = h.nl.length + '/500';
  rawSQL = h.sql;
  displayOutput(h.sql, '', h.columns, h.results);
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── Error ───
function showError(msg) {
  const e = document.getElementById('errorMsg');
  e.textContent = '⚠ ' + msg;
  e.classList.add('show');
}
function clearError() {
  document.getElementById('errorMsg').classList.remove('show');
}

// ─── Enter key ───
nlInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.ctrlKey) generateSQL();
});

// ─── Init ───
renderHistory();
