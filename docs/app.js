import {
  analyzeDraws, digitSum, distribution, normalizeDraws,
  referenceGroups, resolveAnchor, tailDigit,
} from './logic.mjs';

const $ = (id) => document.getElementById(id);
const formatNumber = new Intl.NumberFormat('zh-TW');
let draws = [];
let currentSearch = null;
let visibleDraws = 20;

function balls(numbers) {
  return '<div class="balls" aria-label="開獎號碼">'
    + numbers.map((n) => `<span class="ball">${String(n).padStart(2, '0')}</span>`).join('')
    + '</div>';
}

function showError(id, message = '') {
  const element = $(id);
  element.textContent = message;
  element.hidden = !message;
}

function drawEntry(draw) {
  return `<div class="draw-entry">
    <div class="draw-entry-top"><span>${draw.date}</span><span>第 ${draw.period} 期</span></div>
    ${balls(draw.numbers)}
  </div>`;
}

function topValues(stat) {
  if (!stat.total) return '無資料';
  const ranked = Object.entries(stat.counts).sort((a, b) => b[1] - a[1] || Number(a[0]) - Number(b[0]));
  const max = ranked[0][1];
  const winners = ranked.filter(([, count]) => count === max).map(([key]) => key).join('、');
  return `${winners}：${max} 次（${(max / stat.total * 100).toFixed(1)}%）`;
}

function renderReference() {
  showError('reference-error');
  if (!draws.length) return;
  try {
    const anchor = resolveAnchor(draws, {
      date: $('reference-date').value,
      period: $('reference-period').value.trim(),
    });
    const groups = referenceGroups(draws, anchor);
    const requested = $('reference-date').value;
    const fallback = requested !== anchor.date && !$('reference-period').value.trim()
      ? `查無 ${requested} 的開獎紀錄，改用最近可比對的 ${anchor.date}。`
      : '';
    $('reference-output').innerHTML = `
      <div class="anchor-card">
        <div>
          <p class="eyebrow">基準期</p>
          <h3>${anchor.date}</h3>
          <p>第 ${anchor.period} 期${fallback ? ` · ${fallback}` : ''}</p>
        </div>
        ${balls(anchor.numbers)}
      </div>
      <div class="reference-grid">
        ${groups.map((group) => {
          const numbers = group.matches.flatMap((draw) => draw.numbers);
          const he = distribution(numbers, digitSum, 1, 12);
          const wei = distribution(numbers, tailDigit, 0, 9);
          return `<article class="result-card reference-group">
            <span class="count-badge">${group.matches.length} 期</span>
            <h3>${group.title}</h3>
            <p class="group-description">${group.description}</p>
            ${group.matches.length ? `
              <div class="reference-summary">
                <span class="mini-stat">合數最多：${topValues(he)}</span>
                <span class="mini-stat">尾數最多：${topValues(wei)}</span>
              </div>
              ${group.matches.map(drawEntry).join('')}
            ` : '<p class="empty-state">這段期間沒有符合的開獎紀錄</p>'}
          </article>`;
        }).join('')}
      </div>`;
  } catch (error) {
    showError('reference-error', error.message);
  }
}

function renderBars(stat) {
  const max = Math.max(1, ...Object.values(stat.counts));
  return Object.entries(stat.counts).map(([key, count]) => `
    <div class="bar-row">
      <span class="bar-label">${key}</span>
      <span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:${count / max * 100}%"></span></span>
      <span class="bar-value">${count} · ${stat.total ? (count / stat.total * 100).toFixed(1) : '0.0'}%</span>
    </div>`).join('');
}

function renderHistory() {
  if (!currentSearch) return;
  const recent = currentSearch.draws.slice(-500).reverse();
  const limit = Math.min(visibleDraws, recent.length);
  $('history-list').innerHTML = recent.slice(0, limit).map(drawEntry).join('')
    || '<p class="empty-state">沒有符合條件的開獎紀錄</p>';
  const button = $('load-more');
  button.hidden = limit >= recent.length;
  $('history-note').textContent = currentSearch.drawCount > 500
    ? `最近 500 期中的 ${limit} 期；完整統計仍包含全部 ${formatNumber.format(currentSearch.drawCount)} 期`
    : `顯示 ${limit} / ${formatNumber.format(currentSearch.drawCount)} 期`;
}

function selectedChips(id) {
  return [...$(id).querySelectorAll('[aria-pressed="true"]')].map((button) => Number(button.dataset.value));
}

function optionalNumber(id) {
  const value = $(id).value.trim();
  return value ? Number(value) : null;
}

function renderStatistics() {
  showError('statistics-error');
  if (!draws.length) return;
  const periodFrom = optionalNumber('period-from');
  const periodTo = optionalNumber('period-to');
  if (periodFrom != null && periodTo != null && periodFrom > periodTo) {
    showError('statistics-error', '起始期別不能大於結束期別');
    return;
  }
  currentSearch = analyzeDraws(draws, {
    year: optionalNumber('filter-year'),
    month: optionalNumber('filter-month'),
    periodFrom,
    periodTo,
    heValues: selectedChips('he-options'),
    weiValues: selectedChips('wei-options'),
    matchNumbersOnly: $('numbers-only').checked,
  });
  visibleDraws = 20;
  $('statistics-output').innerHTML = `
    <div class="stats-summary">
      <div class="metric"><span>符合期數</span><strong>${formatNumber.format(currentSearch.drawCount)}</strong></div>
      <div class="metric"><span>統計號碼</span><strong>${formatNumber.format(currentSearch.numberCount)}</strong></div>
    </div>
    <div class="distribution-grid">
      <section class="result-card distribution-card" aria-label="合數分布">
        <h3>合數分布</h3>${renderBars(currentSearch.he)}
      </section>
      <section class="result-card distribution-card" aria-label="尾數分布">
        <h3>尾數分布</h3>${renderBars(currentSearch.wei)}
      </section>
    </div>
    <section class="result-card history-card">
      <h3>開獎明細</h3>
      <p id="history-note"></p>
      <div id="history-list"></div>
      <button id="load-more" class="secondary-button load-more" type="button" hidden>顯示更多</button>
    </section>`;
  $('load-more').addEventListener('click', () => { visibleDraws += 20; renderHistory(); });
  renderHistory();
}

function createChips(id, values) {
  const container = $(id);
  for (const value of values) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'filter-chip';
    button.dataset.value = String(value);
    button.setAttribute('aria-pressed', 'false');
    button.textContent = String(value);
    button.addEventListener('click', () => {
      button.setAttribute('aria-pressed', button.getAttribute('aria-pressed') === 'true' ? 'false' : 'true');
    });
    container.append(button);
  }
}

function populateFilters() {
  const years = [...new Set(draws.map((draw) => draw.date.slice(0, 4)))].reverse();
  $('filter-year').innerHTML = '<option value="">全部年份</option>'
    + years.map((year) => `<option value="${year}">${year} 年</option>`).join('');
  $('filter-month').innerHTML = '<option value="">全部月份</option>'
    + Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}">${i + 1} 月</option>`).join('');
}

async function loadData(force = false) {
  const button = $('reload-data');
  button.disabled = true;
  $('data-status').textContent = '正在載入歷史開獎資料…';
  try {
    const response = await fetch('./data/cache.json', { cache: force ? 'reload' : 'default' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const loaded = normalizeDraws(payload);
    if (!loaded.length) throw new Error('開獎資料為空');
    draws = loaded;
    const latest = draws.at(-1);
    const daysOld = Math.floor((Date.now() - new Date(`${latest.date}T12:00:00+08:00`).getTime()) / 86400000);
    $('data-status').textContent = `${formatNumber.format(draws.length)} 期 · 資料截至 ${latest.date}`;
    $('data-note').textContent = daysOld > 7
      ? '開獎資料已超過七天未更新，近期結果請以官方公告為準。'
      : '資料僅供歷史統計參考';
    $('reference-date').value = latest.date;
    populateFilters();
    renderReference();
    renderStatistics();
  } catch (error) {
    $('data-status').textContent = draws.length ? '無法取得更新，繼續使用現有資料' : '無法載入開獎資料';
    $('data-note').textContent = `請檢查網路或資料檔：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function switchTab(name) {
  for (const button of document.querySelectorAll('.tab')) {
    const active = button.dataset.tab === name;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-selected', String(active));
    $('panel-' + button.dataset.tab).hidden = !active;
  }
}

createChips('he-options', Array.from({ length: 12 }, (_, i) => i + 1));
createChips('wei-options', Array.from({ length: 10 }, (_, i) => i));
for (const button of document.querySelectorAll('.tab')) {
  button.addEventListener('click', () => switchTab(button.dataset.tab));
}
$('reference-form').addEventListener('submit', (event) => { event.preventDefault(); renderReference(); });
$('statistics-form').addEventListener('submit', (event) => { event.preventDefault(); renderStatistics(); });
$('reset-filters').addEventListener('click', () => {
  $('statistics-form').reset();
  for (const chip of document.querySelectorAll('.filter-chip')) chip.setAttribute('aria-pressed', 'false');
  renderStatistics();
});
$('reload-data').addEventListener('click', () => loadData(true));

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
}
loadData();
