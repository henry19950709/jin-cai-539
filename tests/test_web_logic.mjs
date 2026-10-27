import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  analyzeDraws, digitSum, normalizeDraws, referenceGroups,
  resolveAnchor, weekdaySlot,
} from '../docs/logic.mjs';

const sample = normalizeDraws({
  draws: [
    { period: 115000194, date: '2026-08-11', numbers: [1, 2, 3, 4, 5] },
    { period: 114000194, date: '2025-08-11', numbers: [10, 11, 12, 13, 14] },
    { period: 113000194, date: '2024-08-11', numbers: [19, 20, 21, 28, 39] },
    { period: 115000195, date: '2026-08-12', numbers: [30, 31, 32, 33, 34] },
  ],
});

test('合數與只統計符合號碼的篩選與 Python 語意一致', () => {
  assert.equal(digitSum(19), 10);
  assert.equal(digitSum(28), 10);
  const periodFilter = analyzeDraws(sample, { year: 2024, heValues: [10], weiValues: [9] });
  assert.equal(periodFilter.drawCount, 1);
  assert.equal(periodFilter.numberCount, 5);
  const numberFilter = analyzeDraws(sample, {
    year: 2024, heValues: [10], weiValues: [9], matchNumbersOnly: true,
  });
  assert.equal(numberFilter.drawCount, 1);
  assert.equal(numberFilter.numberCount, 1);
  assert.equal(numberFilter.he.counts[10], 1);
  assert.equal(numberFilter.wei.counts[9], 1);
});

test('跨年同期數參照不包含基準年', () => {
  const anchor = resolveAnchor(sample, { period: 115000194 });
  const groups = referenceGroups(sample, anchor);
  assert.deepEqual(groups[0].matches.map((draw) => draw.period), [114000194, 113000194]);
  assert.equal(weekdaySlot('2026-08-11').nth, 2);
});

test('無開獎日期優先找前一年同日，再找最近一期', () => {
  assert.equal(resolveAnchor(sample, { date: '2027-08-11' }).date, '2026-08-11');
  assert.equal(resolveAnchor(sample, { date: '2026-08-13' }).date, '2026-08-12');
  assert.throws(() => resolveAnchor(sample, { period: 999 }), /找不到期別/);
});

test('真實資料可正確計算所有期別與 2024 年的統計', async () => {
  const payload = JSON.parse(await readFile(new URL('../data/daily539_cache.json', import.meta.url), 'utf8'));
  const draws = normalizeDraws(payload);
  assert.ok(draws.length >= 5955);
  const all = analyzeDraws(draws);
  assert.equal(all.numberCount, draws.length * 5);
  assert.equal(analyzeDraws(draws, { year: 2024 }).drawCount, 314);
});
