import {formatValue as fmt, traceLayout, mergePage, Pager} from './core.mjs';
import {chart, el, timeline} from './charts.mjs';

const $ = id => document.getElementById(id);
const state = {applied:null, generation:0, controller:null, pageController:null, traceController:null,
  pager:new Pager(), next:null, pageData:null, summary:null, operations:{}, trace:[], traceNext:null, traceId:null, traceVersion:0};
const labels = {successful:'Completadas',failed:'Fallidas',cancelled:'Canceladas',abstained:'Abstenciones',needs_clarification:'Aclaraciones',unknown:'Sin resultado'};
const modes = {offline:'OFFLINE · Ejecuciones locales',mock:'MOCK · DATOS SINTÉTICOS / DOBLES',live:'LIVE · Uso reportado por proveedores',unknown:'UNKNOWN · Procedencia no clasificada',offline_mock:'OFFLINE_MOCK · Partición heredada; no equivale a offline ni mock'};
const dateLabel = date => new Date(date).toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short'});
const utcLabel = date => date ? new Date(date).toISOString().replace('T',' ').replace('Z',' UTC') : 'N/D';
const localInput = date => new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,19);
function notify(text, kind='') { $('notice').textContent=text; $('notice').className=`notice ${kind}`; }
function errorMessage(error) {
  const known = {401:'Autenticación requerida. Recarga la página e ingresa las credenciales locales.',403:'Acceso rechazado: se requiere conexión local y del mismo origen.',404:'Dashboard deshabilitado.',413:'La selección supera 50.000 eventos. Reduce el período.',422:'Revisa los filtros: período válido de hasta 7 días y operación compatible con el componente.',503:'Almacén no disponible. Revisa la configuración local y reinicia el servidor.'};
  return known[error.status] || 'No se pudo completar la consulta. Revisa el servidor y vuelve a aplicar los filtros.';
}
async function api(path, params, signal) {
  const response = await fetch(`/dashboard/api/${path}${params?'?'+params:''}`,{signal,credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}});
  if (!response.ok) {const error=new Error('Request failed');error.status=response.status;throw error;}
  return response.json();
}
function setPeriod() {
  if ($('period').value === 'custom') return;
  const end = new Date(); end.setMilliseconds(0);
  $('until').value=localInput(end);
  $('since').value=localInput(new Date(end.getTime()-Number($('period').value)*3600000));
}
function selections() {
  const start=new Date($('since').value), end=new Date($('until').value);
  if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || start>=end || end-start>7*86400000) throw new Error('period');
  const params = new URLSearchParams({execution_mode:$('mode').value,since:start.toISOString(),until:end.toISOString()});
  for (const key of ['component','operation','status']) if ($(key).value) params.set(key,$(key).value);
  return params;
}
function operationOptions() {
  const values = $('component').value ? state.operations[$('component').value] || [] : [...new Set(Object.values(state.operations).flat())].sort();
  $('operation').replaceChildren(el('option','Todas')); $('operation').firstChild.value='';
  for (const value of values) {const option=el('option',value);option.value=value;$('operation').append(option);}
}
function kpis(metrics) {
  const request=metrics?.requests, latency=metrics?.request_latency_ms, tokens=metrics?.tokens?.total_tokens;
  const total=request?.total;
  const coverage=`N=${fmt(total)} spans HTTP retenidos`;
  const tokenCoverage=`${fmt(tokens?.observed_spans)}/${fmt(tokens?.total_spans)} spans proveedor con total reportado`;
  const specs=[
    ['Total de solicitudes',total,'solicitudes',coverage],
    ['Solicitudes exitosas',request?.successful,'solicitudes',`${coverage} · status ok`],
    ['Tasa de errores',request?.error_rate,'',`${fmt(request?.failed)} errores / ${fmt(total)} solicitudes`,'percent'],
    ['Latencia promedio',latency?.mean,'ms',`N=${fmt(latency?.count)} spans HTTP`],
    ['Latencia p50',latency?.p50,'ms',`N=${fmt(latency?.count)} · percentil interpolado`],
    ['Latencia p95',latency?.p95,'ms',`N=${fmt(latency?.count)} · percentil interpolado`],
    ['Tokens observados',tokens?.observed_sum,'tokens',tokenCoverage]
  ];
  $('kpis').replaceChildren();
  for (const [label,value,unit,detail,kind] of specs) {
    const isMissing = typeof value !== 'number' || !Number.isFinite(value);
    const card=el('article',undefined,isMissing?'kpi kpi-na':'kpi'), display=el('div',fmt(value,kind),'kpi-value');
    if (unit) display.append(el('small',unit));
    card.append(el('div',label,'kpi-label'),display,el('p',detail),el('small',$('period-note').textContent,'kpi-period'));
    $('kpis').append(card);
  }
}
function performance(metrics, series=[]) {
  const temporal = series.map(b=>({label:`${dateLabel(b.since)} → ${dateLabel(b.until)}`,shortLabel:new Date(b.since).toLocaleTimeString('es-CL',{hour:'2-digit',minute:'2-digit'}),value:b.mean_ms,detail:`N=${b.requests} spans HTTP`}));
  chart($('latency-chart'),temporal,{unit:'ms',temporal:true});
  chart($('error-chart'),series.map((b,i)=>({...temporal[i],value:b.requests?b.errors:null,detail:`${b.errors} errores / ${b.requests} solicitudes`})),{unit:'errores',temporal:true,color:'amber',integerAxis:true});
  chart($('component-chart'),Object.entries(metrics?.components || {}).map(([label,m])=>({label,value:m.mean,detail:`N=${m.count} · p50 ${fmt(m.p50)} ms · p95 ${fmt(m.p95)} ms`})),{unit:'ms'});
  chart($('outcome-chart'),metrics?.executions?.total ? Object.entries(labels).map(([key,label])=>({label,value:metrics.executions[key],detail:`N=${metrics.executions.total} ejecuciones de agente`})) : [],{unit:'ejecuciones',color:'green'});
  toolsChart(metrics);
  chart($('token-chart'),Object.entries(metrics?.tokens || {}).map(([key,t])=>({label:{input_tokens:'Input',output_tokens:'Output',total_tokens:'Total reportado'}[key],value:t.observed_sum,detail:`${t.observed_spans}/${t.total_spans} spans proveedor con datos · suma observada`})),{unit:'tokens',color:'green'});
}
function toolsChart(metrics) {
  const measure=$('tool-measure').value;
  chart($('tool-chart'),Object.entries(metrics?.tools || {}).map(([label,m])=>({label,value:m[measure],detail:`N=${m.count} · media ${fmt(m.mean)} ms · p95 ${fmt(m.p95)} ms`})),{unit:measure==='count'?'llamadas':'ms'});
}
function clearTable(text='Cargando eventos…') {
  const row=el('tr'), cell=el('td',text);cell.colSpan=7;row.append(cell);$('event-body').replaceChildren(row);
  $('previous').disabled=true;$('next').disabled=true;$('event-count').textContent='N/D eventos';
}
function renderEvents(page) {
  state.pageData=page;
  $('event-body').replaceChildren();
  if (!page.items.length) clearTable('Sin eventos para estos filtros. No se infiere ausencia de actividad fuera del almacén.');
  for (const event of page.items) {
    const row=el('tr'), trace=el('td');
    if (event.trace_id) {
      const link=el('button',`${event.trace_id.slice(0,12)}…`,'trace-link');link.title=event.trace_id;link.setAttribute('aria-label',`Explorar traza ${event.trace_id}`);
      link.addEventListener('click',()=>{ $('trace-input').value=event.trace_id;loadTrace(event.trace_id);$('traces').scrollIntoView({block:'start'}); });trace.append(link);
    } else trace.textContent='Sin traza';
    const date=el('td',utcLabel(event.ended_at || event.timestamp)), operation=el('td',event.component || 'log');
    operation.append(el('span',event.operation || event.code || 'N/D','event-operation'));
    const rawState = event.status || event.level || 'N/D';
    const status=el('td');status.append(el('span',rawState,`state ${rawState.toLowerCase()}`));
    row.append(trace,date,el('td',event.execution_mode),operation,status,el('td',`${fmt(event.duration_ms)}${event.duration_ms==null?'':' ms'}`),el('td',event.error_code || '—'));
    $('event-body').append(row);
  }
  state.next=page.next_after;
  $('previous').disabled=state.pager.page===1;$('next').disabled=state.next===null;
  $('page-label').textContent=`Página ${state.pager.page} · hasta 50 eventos · orden de ingestión`;
  $('event-count').textContent=`${page.items.length} eventos en esta página`;
}
function eventsParams() {const p=new URLSearchParams(state.applied);p.set('limit','50');p.set('after',String(state.pager.after));return p;}
async function changePage(forward) {
  const before=[...state.pager.history];
  if (forward) state.pager.advance(state.next); else state.pager.back();
  state.pageController?.abort();state.pageController=new AbortController();
  const version=state.generation;clearTable();
  try {const page=await api('events',eventsParams(),state.pageController.signal);if(version===state.generation)renderEvents(page);}
  catch(error){if(error.name==='AbortError'||version!==state.generation)return;state.pager.history=before;if(state.pageData)renderEvents(state.pageData);else clearTable(errorMessage(error));notify(errorMessage(error)+' Se conserva la última página disponible; puedes reintentar.','error');}
}
function resetTrace() {
  state.traceController?.abort();state.traceVersion++;state.trace=[];state.traceNext=null;state.traceId=null;
  $('trace-more').disabled=true;$('trace-more').hidden=true;$('trace-tree').replaceChildren();$('trace-tools').replaceChildren();
  $('trace-notice').textContent='Selecciona una traza para inspeccionar sus spans.';$('trace-notice').className='notice';
}
function renderTrace() {
  const info=traceLayout(state.trace,state.traceNext!==null);
  const capped=state.trace.length>=1000 && info.pending;
  const notes=[`Modo ${state.applied.get('execution_mode')} · ${state.trace.length} eventos cargados (${info.logCount} logs).`,
    'Cobertura parcial o no verificable: retención, pérdidas o páginas pendientes pueden omitir operaciones. No se reconstruyen eventos eliminados.'];
  if(info.missingParents)notes.push(`${info.missingParents} spans con padre ausente entre los eventos cargados.`);
  if(!info.hasHttpRoot)notes.push('No hay raíz HTTP entre los spans cargados.');
  if(info.pending)notes.push(capped?'Límite visual de 1.000 eventos alcanzado; quedan páginas sin mostrar.':'Quedan páginas por consultar.');
  if(info.cycle)notes.push('Se detectó una relación cíclica; la jerarquía no es confiable.');
  if(!state.trace.length)notes.push('No hay eventos retenidos para esta traza en el modo aplicado.');
  const hasWarnings = Boolean(info.missingParents || !info.hasHttpRoot || info.pending || info.cycle || !state.trace.length);
  $('trace-notice').textContent=notes.join(' ');$('trace-notice').className=hasWarnings?'notice warning':'notice';
  $('trace-tree').replaceChildren();
  const starts=info.rows.map(r=>Date.parse(r.event.started_at));
  const start=starts.length?Math.min(...starts):0;
  const total=Math.max(1,...info.rows.map(r=>Date.parse(r.event.started_at)-start+r.event.duration_ms));
  for(const {event,depth} of info.rows){
    const row=el('div',undefined,'trace-row'), head=el('div',undefined,'trace-row-header');
    const name=el('span',undefined,'trace-name');name.append(el('span',`${'· '.repeat(Math.min(depth,12))}${depth?'↳ ':''}`,'branch'),document.createTextNode(`${event.component} / ${event.operation}`));
    head.append(name,el('span',event.status,`state ${event.status}`),el('code',`${fmt(event.duration_ms)} ms`));
    row.append(head,timeline(Date.parse(event.started_at)-start,event.duration_ms,total));
    const details=el('details');details.append(el('summary','IDs, tiempos y error técnico'),el('pre',`Span: ${event.span_id}\nPadre: ${event.parent_span_id || 'raíz'}\nInicio UTC: ${utcLabel(event.started_at)}\nError: ${event.error_code || '—'}\nResultado: ${event.outcome || 'N/D'}\nProfundidad observada: ${depth}`));row.append(details);$('trace-tree').append(row);
  }
  if(info.rows.length)$('trace-tree').append(el('p','Posición temporal por started_at UTC; ancho por duración monotónica. Un ajuste del reloj puede alterar la alineación, no la duración medida.'));
  const logs=state.trace.filter(e=>e.event==='log');
  if(logs.length){const details=el('details');details.append(el('summary',`${logs.length} logs correlacionados`));for(const log of logs)details.append(el('p',`${utcLabel(log.timestamp)} · ${log.code} · ${log.error_code || 'sin error'} · span ${log.span_id || 'N/D'}`));$('trace-tree').append(details);}
  $('trace-tools').replaceChildren();
  const tools=info.rows.map(r=>r.event).filter(e=>e.component==='tool').sort((a,b)=>Date.parse(a.started_at)-Date.parse(b.started_at)||a.sequence-b.sequence);
  for(const event of tools)$('trace-tools').append(el('li',`${event.operation} · ${fmt(event.duration_ms)} ms · ${event.status}`));
  if(!tools.length)$('trace-tools').append(el('li','Sin herramientas entre los spans cargados'));
  $('trace-more').hidden=!info.pending;$('trace-more').disabled=!info.pending||capped;
}
async function loadTrace(id, more=false) {
  if(!state.applied || !/^[a-f0-9]{32}$/.test(id))return;
  state.traceController?.abort();state.traceController=new AbortController();const version=++state.traceVersion;
  if(!more){state.trace=[];state.traceNext=null;state.traceId=id;$('trace-tree').replaceChildren();$('trace-tools').replaceChildren();}
  $('trace-notice').textContent='Cargando eventos de la traza…';$('trace-notice').className='notice';$('trace-more').disabled=true;
  const params=new URLSearchParams({execution_mode:state.applied.get('execution_mode'),trace_id:id,limit:'100',after:String(more?state.traceNext:0)});
  try{const page=await api('events',params,state.traceController.signal);if(version!==state.traceVersion)return;state.trace=mergePage(state.trace,page.items);state.traceNext=page.next_after;renderTrace();}
  catch(error){if(error.name==='AbortError'||version!==state.traceVersion)return;$('trace-notice').textContent=errorMessage(error);$('trace-notice').className='notice error';$('trace-more').hidden=!more;$('trace-more').disabled=!more;}
}
function renderQuality(quality) {
  const bench = Array.isArray(quality?.benchmarks) && quality.benchmarks.length ? quality.benchmarks[0] : null;
  $('precision').textContent = fmt(quality?.precision, 'percent');
  $('consistency').textContent = fmt(quality?.consistency, 'percent');
  if (!bench || quality?.status === 'not_evaluated') {
    $('quality-state').textContent = 'Sin evaluación validada';
    $('precision-detail').textContent = 'Sin muestras evaluadas';
    $('consistency-detail').textContent = 'Sin repeticiones evaluadas';
    $('quality-meta').hidden = true;
    $('quality-scenarios').hidden = true;
    $('quality-scenario-body').replaceChildren();
    return;
  }
  const conMetric = bench.metrics?.consistency;
  const modeNote = bench.not_live_gemini_evidence ? `modo ${bench.execution_mode} (sin Gemini live)` : `modo ${bench.execution_mode}`;
  $('quality-state').textContent = bench.synthetic ? `Evaluación ${bench.execution_mode} · incluye fixtures sintéticos` : `Evaluación validada · ${bench.execution_mode}`;
  $('precision-detail').textContent = `N=${fmt(bench.sample_size)} evaluables · ${fmt(bench.correct_cases)} ok / ${fmt(bench.incorrect_cases)} fail`;
  $('consistency-detail').textContent = conMetric?.sample_size ? `N=${fmt(conMetric.sample_size)} repeticiones válidas` : 'Sin repeticiones evaluadas';
  $('quality-meta').textContent = `${bench.benchmark_version || 'benchmark'} · ${dateLabel(bench.generated_at)} · commit ${bench.git_sha || 'N/D'} · ${modeNote} · ${fmt(bench.pending_validation_cases)} pendientes de validación`;
  $('quality-meta').hidden = false;
  const rows = Object.entries(bench.by_scenario || {});
  $('quality-scenario-body').replaceChildren();
  for (const [scenario, counts] of rows) {
    const tr = el('tr');
    tr.append(el('td', scenario), el('td', fmt(counts.evaluable)), el('td', fmt(counts.correct)), el('td', fmt(counts.incorrect)), el('td', fmt(counts.pending_validation)));
    $('quality-scenario-body').append(tr);
  }
  $('quality-scenarios').hidden = !rows.length;
}
async function refresh(event) {
  event?.preventDefault();
  setPeriod();
  let params;
  try{params=selections();}catch{notify('Selecciona fechas válidas: desde debe preceder a hasta, con un máximo de 7 días.','error');return;}
  state.controller?.abort();state.pageController?.abort();state.controller=new AbortController();
  const signal=state.controller.signal, version=++state.generation;
  state.applied=params;state.pager.reset();state.pageData=null;state.summary=null;resetTrace();
  $('mode-note').textContent=modes[params.get('execution_mode')];$('mode-note').className=params.get('execution_mode')==='mock'?'synthetic':'';
  $('period-note').textContent=`${dateLabel(params.get('since'))} → ${dateLabel(params.get('until'))}`;
  kpis(null);performance(null);clearTable();notify('Consultando eventos retenidos…');
  $('capture-state').textContent='Captura: N/D';$('last-update').textContent='Actualizando…';$('quality-state').textContent='Consultando evaluación…';
  const results=await Promise.allSettled([api('summary',params,signal),api('events',eventsParams(),signal),api('quality',new URLSearchParams({execution_mode:params.get('execution_mode')}),signal)]);
  if(version!==state.generation)return;
  const failures=[];
  if(results[0].status==='fulfilled'){
    const data=results[0].value;state.summary=data;kpis(data.metrics);performance(data.metrics,data.series);
    $('capture-state').textContent=`Captura ${data.collection.enabled?'activada':'desactivada'} · este proceso`;
    $('last-update').textContent=`Consulta: ${dateLabel(data.generated_at)} · caché ≤ ${data.cached_for_seconds} s`;
    $('coverage-note').textContent=`${data.metrics.matched_events} eventos retenidos coincidentes · ${data.collection.dropped_events} fallos de captura en este proceso · historia incompleta. Los filtros se aplican a spans, no expanden trazas.`;
    if(data.metrics.matched_events===0)notify('Sin eventos retenidos para esta selección. Cambia el período o el modo; la captura desactivada no crea datos retrospectivos.');
    else notify('Lectura actualizada. Los indicadores cubren solo los eventos retenidos que coinciden con los filtros.');
  }else{failures.push(errorMessage(results[0].reason));$('last-update').textContent='Actualización no disponible';$('coverage-note').textContent='Cobertura N/D: no se pudo obtener el resumen.';}
  if(results[1].status==='fulfilled')renderEvents(results[1].value);else{clearTable(errorMessage(results[1].reason));failures.push(errorMessage(results[1].reason));}
  if(results[2].status==='fulfilled'){
    // Only this evaluated contract may populate quality. No inference from operational spans.
    renderQuality(results[2].value);
  }else{renderQuality(null);$('quality-state').textContent='Evaluación no disponible';failures.push(errorMessage(results[2].reason));}
  if(failures.length)notify([...new Set(failures)].join(' '),'error');
}
$('filters').addEventListener('submit',refresh);
$('period').addEventListener('change',setPeriod);
for(const id of ['since','until'])$(id).addEventListener('input',()=>{$('period').value='custom';});
$('component').addEventListener('change',operationOptions);
$('tool-measure').addEventListener('change',()=>toolsChart(state.summary?.metrics));
$('previous').addEventListener('click',()=>changePage(false));$('next').addEventListener('click',()=>changePage(true));
$('trace-form').addEventListener('submit',event=>{event.preventDefault();loadTrace($('trace-input').value.trim());});
$('trace-more').addEventListener('click',()=>loadTrace(state.traceId,true));
for(const link of document.querySelectorAll('.section-nav a'))link.addEventListener('click',()=>{for(const l of document.querySelectorAll('.section-nav a'))l.removeAttribute('aria-current');link.setAttribute('aria-current','location');});
setPeriod();kpis(null);performance(null);
try{
  const options=await api('options');state.operations=options.operations;
  for(const name of Object.keys(options.operations)){const option=el('option',name);option.value=name;$('component').append(option);}
  operationOptions();await refresh();
}catch(error){notify(errorMessage(error),'error');}
