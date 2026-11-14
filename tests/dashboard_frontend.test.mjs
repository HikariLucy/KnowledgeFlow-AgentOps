// Synthetic fixtures only. Run with node --test tests/dashboard_frontend.test.mjs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { formatValue, traceLayout, mergePage, Pager } from '../app/ui/static/observability/core.mjs';

test('unknown values are N/D; a reported zero remains zero', () => {
  assert.equal(formatValue(null), 'N/D');
  assert.equal(formatValue(undefined), 'N/D');
  assert.equal(formatValue(NaN), 'N/D');
  assert.equal(formatValue(0), '0');
  assert.equal(formatValue(0.25, 'percent'), '25 %');
});
const span = (id, parent = null, extra = {}) => ({event:'span', event_id:id, span_id:id,
  parent_span_id:parent, started_at:'2026-11-13T00:00:00Z', duration_ms:10,
  component:'http', operation:'agent', ...extra});
test('trace hierarchy finds missing parents without fabricating operations', () => {
  const result = traceLayout([span('child','missing')], false);
  assert.equal(result.missingParents, 1);
  assert.equal(result.rows.length, 1);
  assert.equal(result.rows[0].event.span_id, 'child');
  assert.equal(result.complete, false);
});
test('out of order spans form a parent-first tree, logs are not duplicate spans', () => {
  const result = traceLayout([span('child','root'), span('root'), {event:'log', span_id:'root'}], false);
  assert.deepEqual(result.rows.map(r => [r.event.span_id, r.depth]), [['root',0], ['child',1]]);
  assert.equal(result.logCount, 1);
  assert.equal(result.missingParents, 0);
  assert.equal(result.complete, false); // absent children cannot be inferred
});
test('cycles terminate and are reported; pending pages cannot imply completeness', () => {
  const result = traceLayout([span('a','b'),span('b','a')], true);
  assert.equal(result.rows.length, 2);
  assert.equal(result.cycle, true);
  assert.equal(result.pending, true);
});
test('manual trace pages deduplicate event IDs and enforce memory cap', () => {
  assert.deepEqual(mergePage([{event_id:'a'}],[{event_id:'a'},{event_id:'b'}],2).map(e => e.event_id), ['a','b']);
  assert.equal(mergePage([{event_id:'a'}],[{event_id:'b'},{event_id:'c'}],2).length,2);
});
test('cursor history supports next/back without skipping or repeating a stable page', () => {
  const pager = new Pager();
  assert.equal(pager.after,0);
  pager.advance(50); pager.advance(100);
  assert.equal(pager.after,100);
  pager.back(); assert.equal(pager.after,50);
  pager.advance(100); assert.equal(pager.after,100);
  pager.reset(); assert.equal(pager.after,0); assert.equal(pager.page,1);
});
