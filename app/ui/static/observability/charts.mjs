import {formatValue} from './core.mjs';
export const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};
const ns = 'http://www.w3.org/2000/svg';
function svgEl(tag, attributes = {}, text) {
  const node = document.createElementNS(ns, tag);
  for (const [k,v] of Object.entries(attributes)) node.setAttribute(k, String(v));
  if (text !== undefined) node.textContent = text;
  return node;
}
function truncateLabel(text, maxLen = 22) {
  const s = String(text ?? '');
  return s.length > maxLen ? `${s.slice(0, maxLen - 1)}…` : s;
}
/** Accessible bars: keyboard/hover inspection plus an exact-values table. */
export function chart(container, items, {unit = '', temporal = false, color = 'blue', integerAxis = false, onSelect} = {}) {
  container.replaceChildren();
  const available = items.filter(i => typeof i.value === 'number' && Number.isFinite(i.value));
  if (!available.length) {
    container.append(el('div', 'N/D · Sin muestras para esta selección', 'empty-chart'));
    return;
  }
  const width = 640, height = temporal ? 196 : Math.max(152, items.length * 36 + 24);
  const svg = svgEl('svg', {viewBox: `0 0 ${width} ${height}`, role:'group', 'aria-label':`Gráfico en ${unit || 'unidades'}`});
  const tooltip = el('p', 'Enfoca o pasa sobre una barra para inspeccionar sus muestras.', 'chart-tooltip');
  tooltip.setAttribute('aria-live', 'polite');
  const rawMax = Math.max(1, ...available.map(i => i.value));
  const maximum = integerAxis ? Math.ceil(rawMax) : rawMax;
  const ticks = integerAxis && maximum <= 4
    ? Array.from({length: maximum + 1}, (_, i) => i)
    : Array.from({length: 5}, (_, g) => maximum * g / 4);
  const info = i => `${i.label}: ${formatValue(i.value)} ${unit} · ${i.detail || ''}`;
  if (temporal) {
    for (const tickVal of ticks) {
      const ratio = maximum > 0 ? tickVal / maximum : 0;
      const y = height - 30 - ratio * (height - 50);
      svg.append(svgEl('line', {x1:44,y1:y,x2:630,y2:y,class:'grid-line'}));
      svg.append(svgEl('text', {x:38,y:y+4,'text-anchor':'end',class:'axis-label'}, formatValue(tickVal)));
    }
  }
  items.forEach((item, index) => {
    const present = typeof item.value === 'number' && Number.isFinite(item.value);
    let x, y, w, h;
    if (temporal) {
      const plotW = 582;
      w = Math.max(4, plotW / items.length - 5);
      x = 46 + index * plotW / items.length;
      h = present ? Math.max(item.value > 0 ? 3 : 2, item.value / maximum * (height - 50)) : 0;
      y = height - 30 - h;
      if (index % 6 === 0 || index === items.length - 1) {
        const anchor = index === items.length - 1 ? 'end' : 'start';
        const lx = index === items.length - 1 ? x + w : x;
        svg.append(svgEl('text', {x:lx,y:height-8,'text-anchor':anchor,class:'axis-label'}, item.shortLabel || item.label));
      }
    } else {
      x = 165; y = index * 36 + 8; w = present ? Math.max(item.value > 0 ? 4 : 2, item.value / maximum * 360) : 0; h = 16;
      svg.append(svgEl('rect', {x, y, width:360, height:h, rx:2, class:'bar-track'}));
      const lbl = svgEl('text', {x:0,y:y+12,class:'bar-label'}, truncateLabel(item.label, 21));
      lbl.append(svgEl('title', {}, String(item.label)));
      svg.append(lbl);
      svg.append(svgEl('text', {x:536,y:y+12,class:'bar-value'}, `${formatValue(item.value)} ${unit}`));
    }
    if (!present) return;
    const rect = svgEl('rect', {x,y,width:w,height:h,rx:2,class:`data-bar ${color}`,tabindex:0,role:onSelect?'button':'img','aria-label':info(item)});
    rect.append(svgEl('title', {}, info(item)));
    rect.addEventListener('mouseenter', () => { tooltip.textContent = info(item); });
    rect.addEventListener('focus', () => { tooltip.textContent = info(item); });
    if (onSelect) {
      rect.addEventListener('click', () => onSelect(item));
      rect.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') {e.preventDefault();onSelect(item);} });
    }
    svg.append(rect);
  });
  container.append(svg, tooltip);
  const details = el('details'); details.append(el('summary', 'Ver valores y cobertura'));
  const table = el('table'), head = el('thead'), tr = el('tr'), body = el('tbody');
  for (const title of ['Serie', `Valor ${unit}`, 'Muestras / cobertura']) tr.append(el('th',title));
  head.append(tr); table.append(head,body);
  for (const item of items) {const row = el('tr');row.append(el('td',item.label),el('td',formatValue(item.value)),el('td',item.detail || 'N/D'));body.append(row);}
  const scroll = el('div',undefined,'table-scroll chart-table-scroll');scroll.append(table);details.append(scroll);container.append(details);
}
export function timeline(start, duration, total) {
  const svg = svgEl('svg', {viewBox:'0 0 600 22',role:'img','aria-label':`Inicio relativo ${formatValue(start)} ms, duración ${formatValue(duration)} ms`,class:'timeline'});
  svg.append(svgEl('line',{x1:0,y1:11,x2:600,y2:11,class:'grid-line'}));
  svg.append(svgEl('rect',{x:Math.max(0,start/total*600),y:4,width:Math.max(2,duration/total*600),height:14,rx:2,class:'data-bar'}));
  return svg;
}
