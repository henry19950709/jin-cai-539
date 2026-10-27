export function digitSum(number) {
  return Math.floor(number / 10) + (number % 10);
}

export function tailDigit(number) {
  return number % 10;
}

export function normalizeDraws(payload) {
  const rows = Array.isArray(payload) ? payload : payload?.draws;
  if (!Array.isArray(rows)) throw new Error('開獎資料格式不正確');

  const draws = rows.map((row) => {
    const period = Number(row.period);
    const numbers = row.numbers?.map(Number);
    if (!Number.isInteger(period) || !/^\d{4}-\d{2}-\d{2}$/.test(row.date)
      || !Array.isArray(numbers) || numbers.length !== 5
      || new Set(numbers).size !== 5
      || numbers.some((n) => !Number.isInteger(n) || n < 1 || n > 39)) {
      throw new Error('開獎資料有無效的期別或號碼');
    }
    return { period, date: row.date, numbers };
  });
  draws.sort((a, b) => a.date.localeCompare(b.date) || a.period - b.period);
  return draws;
}

export function distribution(numbers, mapper, first, last) {
  const counts = Object.fromEntries(
    Array.from({ length: last - first + 1 }, (_, i) => [first + i, 0]),
  );
  for (const number of numbers) counts[mapper(number)] += 1;
  return { counts, total: numbers.length };
}

export function analyzeDraws(draws, filter = {}) {
  const heValues = new Set(filter.heValues || []);
  const weiValues = new Set(filter.weiValues || []);
  const matchedDraws = draws.filter((draw) => {
    if (filter.year && Number(draw.date.slice(0, 4)) !== filter.year) return false;
    if (filter.month && Number(draw.date.slice(5, 7)) !== filter.month) return false;
    if (filter.periodFrom != null && draw.period < filter.periodFrom) return false;
    if (filter.periodTo != null && draw.period > filter.periodTo) return false;
    if (heValues.size && !draw.numbers.some((n) => heValues.has(digitSum(n)))) return false;
    if (weiValues.size && !draw.numbers.some((n) => weiValues.has(tailDigit(n)))) return false;
    return true;
  });
  const numbers = matchedDraws.flatMap((draw) => draw.numbers.filter((number) =>
    !filter.matchNumbersOnly
      || ((!heValues.size || heValues.has(digitSum(number)))
        && (!weiValues.size || weiValues.has(tailDigit(number)))),
  ));
  return {
    draws: matchedDraws,
    drawCount: matchedDraws.length,
    numberCount: numbers.length,
    he: distribution(numbers, digitSum, 1, 12),
    wei: distribution(numbers, tailDigit, 0, 9),
  };
}

export function weekdaySlot(dateText) {
  const [, year, month, day] = dateText.match(/^(\d{4})-(\d{2})-(\d{2})$/) || [];
  if (!day) throw new Error('日期格式不正確');
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day), 12));
  return { weekday: date.getUTCDay(), nth: Math.ceil(Number(day) / 7) };
}

export function resolveAnchor(draws, { date, period } = {}) {
  if (!draws.length) return null;
  if (period != null && period !== '') {
    const found = draws.find((draw) => draw.period === Number(period));
    if (!found) throw new Error(`找不到期別 ${period}`);
    return found;
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date || '')) throw new Error('請選擇有效日期');
  const exact = draws.find((draw) => draw.date === date);
  if (exact) return exact;
  const year = Number(date.slice(0, 4));
  const previousYearDate = `${year - 1}${date.slice(4)}`;
  const previousYear = draws.find((draw) => draw.date === previousYearDate);
  if (previousYear) return previousYear;
  return [...draws].reverse().find((draw) => draw.date <= date) || draws.at(-1);
}

function shiftMonth(year, month, offset) {
  const date = new Date(Date.UTC(year, month - 1 - offset, 1, 12));
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() + 1 };
}

export function referenceGroups(draws, anchor) {
  const year = Number(anchor.date.slice(0, 4));
  const month = Number(anchor.date.slice(5, 7));
  const day = Number(anchor.date.slice(8, 10));
  const slot = weekdaySlot(anchor.date);
  const previousYears = new Set(Array.from({ length: 5 }, (_, i) => year - i - 1));
  const previousMonths = new Set(Array.from({ length: 12 }, (_, i) => {
    const shifted = shiftMonth(year, month, i + 1);
    return `${shifted.year}-${String(shifted.month).padStart(2, '0')}`;
  }));
  const inPreviousYear = (draw) => previousYears.has(Number(draw.date.slice(0, 4)));
  const sameSlot = (draw) => {
    const candidate = weekdaySlot(draw.date);
    return candidate.weekday === slot.weekday && candidate.nth === slot.nth;
  };
  const groups = [
    { key: 'period', title: '前五年・同期數', description: `每年的第 ${anchor.period % 1000} 期`, matches: draws.filter((draw) =>
      inPreviousYear(draw) && draw.period % 1000 === anchor.period % 1000) },
    { key: 'date', title: '前五年・同日期', description: `${month} 月 ${day} 日`, matches: draws.filter((draw) =>
      inPreviousYear(draw) && Number(draw.date.slice(5, 7)) === month && Number(draw.date.slice(8, 10)) === day) },
    { key: 'weekday', title: '前五年・同週次', description: `同月第 ${slot.nth} 個星期${'日一二三四五六'[slot.weekday]}`, matches: draws.filter((draw) =>
      inPreviousYear(draw) && Number(draw.date.slice(5, 7)) === month && sameSlot(draw)) },
    { key: 'month-date', title: '前十二月・同日期', description: `每月 ${day} 日`, matches: draws.filter((draw) =>
      previousMonths.has(draw.date.slice(0, 7)) && Number(draw.date.slice(8, 10)) === day) },
    { key: 'month-weekday', title: '前十二月・同週次', description: `每月第 ${slot.nth} 個星期${'日一二三四五六'[slot.weekday]}`, matches: draws.filter((draw) =>
      previousMonths.has(draw.date.slice(0, 7)) && sameSlot(draw)) },
  ];
  return groups.map((group) => ({ ...group, matches: group.matches.reverse() }));
}
