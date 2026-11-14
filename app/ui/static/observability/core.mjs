/** Pure presentation helpers; never estimate operational metrics. */
export function formatValue(value, kind = 'number') {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'N/D';
  const n = kind === 'percent' ? value * 100 : value;
  return new Intl.NumberFormat('es-CL', {maximumFractionDigits: 2}).format(n) + (kind === 'percent' ? ' %' : '');
}
export class Pager {
  constructor() { this.reset(); }
  reset() { this.history = [0]; }
  get after() { return this.history.at(-1); }
  get page() { return this.history.length; }
  advance(cursor) { if (cursor !== null && cursor > this.after) this.history.push(cursor); }
  back() { if (this.history.length > 1) this.history.pop(); }
}
export function mergePage(previous, incoming, cap = 1000) {
  const seen = new Set(previous.map(e => e.event_id));
  return [...previous, ...incoming.filter(e => !seen.has(e.event_id) && seen.add(e.event_id))].slice(0, cap);
}
export function traceLayout(events, pending) {
  const spans = new Map(events.filter(e => e.event === 'span').map(e => [e.span_id, e]));
  const children = new Map();
  let missingParents = 0;
  const roots = [];
  for (const event of spans.values()) {
    if (!event.parent_span_id || !spans.has(event.parent_span_id)) {
      roots.push(event);
      if (event.parent_span_id) missingParents++;
    } else {
      if (!children.has(event.parent_span_id)) children.set(event.parent_span_id, []);
      children.get(event.parent_span_id).push(event);
    }
  }
  const ordered = list => list.sort((a,b) => Date.parse(a.started_at) - Date.parse(b.started_at) || (a.sequence ?? 0) - (b.sequence ?? 0));
  const visited = new Set(), rows = [];
  let cycle = false;
  function visit(event, depth, path) {
    if (path.has(event.span_id)) { cycle = true; return; }
    if (visited.has(event.span_id)) return;
    visited.add(event.span_id); rows.push({event, depth});
    const next = new Set(path); next.add(event.span_id);
    for (const child of ordered(children.get(event.span_id) || [])) visit(child, depth + 1, next);
  }
  for (const event of ordered(roots)) visit(event, 0, new Set());
  for (const event of spans.values()) if (!visited.has(event.span_id)) { cycle = true; visit(event, 0, new Set()); }
  return {rows, missingParents, pending, cycle, complete: false,
    logCount: events.filter(e => e.event === 'log').length,
    hasHttpRoot: [...spans.values()].some(e => e.component === 'http' && !e.parent_span_id)};
}
