/* Gastos abiertos de Córdoba — HTML/CSS/JS plano, sin dependencias.
   Lee data/gastos.json y data/meta.json y calcula todo en el navegador. */
(function () {
  'use strict';

  // ---------- Utilidades ----------
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  var nfARS = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 });
  var nf0 = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
  var nf2 = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var nfPct = new Intl.NumberFormat('es-AR', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 });
  var MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

  var METRICS = {
    devengado: { label: 'Devengado', f: 'd' },
    pagado: { label: 'Pagado', f: 'g' },
    vigente: { label: 'Presupuesto vigente', f: 'v' },
    compromiso: { label: 'Compromiso', f: 'c' }
  };
  var TIPOS = { AC: 'Administración Central (AC)', EMAEE: 'Entes descentralizados (EMAEE)' };

  // Los montos viven como BigInt en centavos. Solo se pasan a texto al mostrarlos.
  // Pesos exactos: parte entera y centavos por separado, sin dividir como float.
  function money(v) {
    if (v == null) return 's/d';
    var neg = v < 0n, a = neg ? -v : v;
    var cents = a % 100n;
    return (neg ? '-' : '') + '$ ' + nf0.format(a / 100n) + ',' + (cents < 10n ? '0' : '') + cents.toString();
  }
  // Resumen para títulos (billones/millones): acá sí alcanza un float, es solo para mostrar.
  function compact(v) {
    if (v == null) return 'n/d';
    var p = Number(v) / 100, a = Math.abs(p);
    if (a >= 1e12) return '$ ' + nf2.format(p / 1e12) + ' billones';
    if (a >= 1e6) return '$ ' + nf0.format(p / 1e6) + ' millones';
    return money(v);
  }
  // Convierte un monto del JSON (entero en centavos) a BigInt; falla si no es entero seguro.
  function toCents(x) {
    if (x == null) return null;
    if (typeof x !== 'number' || !Number.isSafeInteger(x)) throw new Error('monto no entero en centavos: ' + x);
    return BigInt(x);
  }
  function ratio(a, b) { return b ? Number(a) / Number(b) : null; }
  function cmp(a, b) { return a > b ? 1 : (a < b ? -1 : 0); }
  function fechaLarga(iso) {
    var p = iso.split('-');
    return parseInt(p[2], 10) + ' de ' + MESES[parseInt(p[1], 10) - 1] + ' de ' + p[0];
  }
  function fechaCorta(iso) { var p = iso.split('-'); return p[2] + '/' + p[1] + '/' + p[0]; }

  // Suma en centavos enteros (BigInt); devuelve null si ninguna fila tiene dato (p. ej. compromiso en EMAEE).
  function sum(rows, f) {
    var s = 0n, any = false;
    for (var i = 0; i < rows.length; i++) {
      var x = rows[i][f];
      if (x != null) { s += x; any = true; }
    }
    return any ? s : null;
  }

  // ---------- Estado ----------
  var DATA = [], META = null, YEARS = [];
  var state = {
    tab: 'anual', tipo: 'AC', ejercicio: 2025, jur: '', unidad: '', programa: '', partida: '',
    metric: 'devengado', compare: false, dim: 'jur', n: 10,
    sortKey: 'd', sortDir: -1, page: 0, pageSize: 25
  };
  var TABS = ['anual', 'top', 'detalle', 'prov'];

  function readHash() {
    var p = new URLSearchParams(location.hash.replace(/^#/, ''));
    var g = function (k) { return p.get(k); };
    if (TABS.indexOf(g('vista')) >= 0) state.tab = g('vista');
    if (g('tipo') === 'AC' || g('tipo') === 'EMAEE') state.tipo = g('tipo');
    if (g('ejercicio') && YEARS.indexOf(+g('ejercicio')) >= 0) state.ejercicio = +g('ejercicio');
    ['jur', 'unidad', 'programa', 'partida'].forEach(function (k) { if (g(k)) state[k] = g(k); });
    if (METRICS[g('metrica')]) state.metric = g('metrica');
    if (g('comparar') === '1') state.compare = true;
    if (['jur', 'unidad', 'programa', 'partida'].indexOf(g('agrupar')) >= 0) state.dim = g('agrupar');
    if ([10, 20, 50].indexOf(+g('top')) >= 0) state.n = +g('top');
  }
  function writeHash() {
    var p = new URLSearchParams();
    p.set('vista', state.tab); p.set('tipo', state.tipo); p.set('ejercicio', state.ejercicio);
    ['jur', 'unidad', 'programa', 'partida'].forEach(function (k) { if (state[k]) p.set(k, state[k]); });
    p.set('metrica', state.metric);
    if (state.compare) p.set('comparar', '1');
    p.set('agrupar', state.dim); p.set('top', state.n);
    history.replaceState(null, '', '#' + p.toString());
  }

  // ---------- Filtros en cascada ----------
  function select(opts) {
    return DATA.filter(function (r) {
      return (opts.t == null || r.t === opts.t) &&
        (opts.y == null || r.y === opts.y) &&
        (!opts.jur || r.jc === opts.jur) &&
        (!opts.unidad || r.u === opts.unidad) &&
        (!opts.programa || r.p === opts.programa) &&
        (!opts.partida || r.pc === opts.partida);
    });
  }
  function unique(rows, keyFn, labelFn) {
    var m = new Map();
    rows.forEach(function (r) { var k = keyFn(r); if (!m.has(k)) m.set(k, labelFn(r)); });
    return Array.from(m, function (e) { return { v: e[0], l: e[1] }; })
      .sort(function (a, b) { return a.l.localeCompare(b.l, 'es', { numeric: true }); });
  }
  function fill(el, items, allLabel, current) {
    var ok = !current || items.some(function (i) { return i.v === current; });
    var html = '<option value="">' + esc(allLabel) + ' (' + items.length + ')</option>' +
      items.map(function (i) {
        return '<option value="' + esc(i.v) + '" title="' + esc(i.l) + '">' + esc(i.l) + '</option>';
      }).join('');
    el.innerHTML = html;
    el.value = ok ? current : '';
    return ok ? current : '';
  }
  function syncFilters() {
    var base = select({ t: state.tipo, y: state.ejercicio });
    state.jur = fill($('f-jur'), unique(base, function (r) { return r.jc; }, function (r) { return r.jc + ' · ' + r.jn; }), 'Todas', state.jur);
    var r2 = select({ t: state.tipo, y: state.ejercicio, jur: state.jur });
    state.unidad = fill($('f-unidad'), unique(r2, function (r) { return r.u; }, function (r) { return r.u; }), 'Todas', state.unidad);
    var r3 = select({ t: state.tipo, y: state.ejercicio, jur: state.jur, unidad: state.unidad });
    state.programa = fill($('f-programa'), unique(r3, function (r) { return r.p; }, function (r) { return r.p; }), 'Todos', state.programa);
    var r4 = select({ t: state.tipo, y: state.ejercicio, jur: state.jur, unidad: state.unidad, programa: state.programa });
    state.partida = fill($('f-partida'), unique(r4, function (r) { return r.pc; }, function (r) { return r.pc + ' · ' + r.pn; }), 'Todas', state.partida);
  }
  function filtersActive() { return !!(state.jur || state.unidad || state.programa || state.partida); }
  function currentRows() {
    return select({ t: state.tipo, y: state.ejercicio, jur: state.jur, unidad: state.unidad, programa: state.programa, partida: state.partida });
  }

  // ---------- Render ----------
  function isPartial(y, t) {
    var c = META.cortes[t + '-' + y];
    return !!c && c.slice(5) !== '12-31';
  }

  function renderStatus() {
    var c = META.cortes[state.tipo + '-' + state.ejercicio];
    var txt = c ? fechaLarga(c) + (isPartial(state.ejercicio, state.tipo) ? ' (ejercicio parcial)' : ' (cierre del ejercicio)') : 'sin dato';
    $('st-corte').textContent = txt + ' · ' + state.tipo + ' ' + state.ejercicio;
    [$('st-fuente'), $('ft-fuente')].forEach(function (a) { a.href = META.fuente; a.textContent = META.fuente.replace(/^https?:\/\//, ''); });
    $('st-atrib').textContent = META.atribucion;
    $('ft-atrib').textContent = 'Atribución: ' + META.atribucion;

    var parts = [];
    YEARS.forEach(function (y) {
      var c2 = META.cortes['AC-' + y];
      if (c2 && c2.slice(5) !== '12-31') parts.push('El ejercicio ' + y + ' es parcial: sus montos son acumulados hasta el ' + fechaCorta(c2) + ' y no son comparables con ejercicios completos.');
    });
    var av = $('aviso-parcial');
    av.hidden = !parts.length;
    av.innerHTML = parts.length ? '<strong>Ejercicios parciales.</strong> ' + esc(parts.join(' ')) : '';
  }

  function renderSelection() {
    var names = [];
    function label(sel, all) { var o = $(sel).selectedOptions[0]; return o && o.value ? o.textContent : all; }
    names.push('<b>' + esc(state.tipo) + '</b>', 'ejercicio <b>' + state.ejercicio + '</b>');
    names.push(esc(label('f-jur', 'todas las jurisdicciones')));
    if (state.unidad) names.push(esc(label('f-unidad', '')));
    if (state.programa) names.push(esc(label('f-programa', '')));
    if (state.partida) names.push(esc(label('f-partida', '')));
    $('selection').innerHTML = 'Mostrando: ' + names.join(' · ') + '. Montos en pesos corrientes, sin ajuste por inflación.';
  }

  function renderKpis(rows) {
    var order = ['vigente', 'compromiso', 'devengado', 'pagado'];
    var tot = {};
    order.forEach(function (k) { tot[k] = sum(rows, METRICS[k].f); });
    var html = order.map(function (k) {
      var v = tot[k];
      var sub = v == null ? 'No informado para este tipo' : money(v);
      return '<div class="kpi' + (k === state.metric ? ' is-active' : '') + '" data-k="' + k + '">' +
        '<div class="kpi-name">' + METRICS[k].label + '</div>' +
        '<div class="kpi-val">' + esc(compact(v)) + '</div>' +
        '<div class="kpi-sub">' + esc(sub) + '</div></div>';
    }).join('');
    var ej = tot.vigente ? ratio(tot.devengado, tot.vigente) : null;
    html += '<div class="kpi" data-k="ejecucion"><div class="kpi-name">Ejecución (devengado / vigente)</div>' +
      '<div class="kpi-val">' + (ej == null ? 'n/d' : esc(nfPct.format(ej))) + '</div>' +
      '<div class="kpi-sub">' + rows.length + ' filas</div></div>';
    $('kpis').innerHTML = html;
  }

  function metricAvailability() {
    var avail = state.tipo === 'AC';
    var radio = document.querySelector('input[name="metric"][value="compromiso"]');
    radio.disabled = !avail;
    if (!avail && state.metric === 'compromiso') state.metric = 'devengado';
    var cmp = state.compare && !filtersActive();
    $('metric-hint').textContent = (!avail && !cmp) ? 'Compromiso no está informado para EMAEE.' : '';
    document.querySelector('input[name="metric"][value="' + state.metric + '"]').checked = true;
  }

  // --- Total anual ---
  function renderAnnual() {
    var f = METRICS[state.metric].f;
    var cmpBox = $('f-compare');
    var blocked = filtersActive();
    cmpBox.disabled = blocked;
    cmpBox.checked = state.compare && !blocked;
    $('compare-hint').textContent = blocked
      ? 'La comparación AC vs EMAEE solo está disponible sin filtros de jurisdicción, unidad, programa o partida (los códigos son distintos entre AC y EMAEE).'
      : '';
    var tipos = (state.compare && !blocked) ? ['AC', 'EMAEE'] : [state.tipo];
    var f4 = { jur: state.jur, unidad: state.unidad, programa: state.programa, partida: state.partida };

    var data = YEARS.map(function (y) {
      return {
        y: y,
        vals: tipos.map(function (t) {
          var rows = select({ t: t, y: y, jur: f4.jur, unidad: f4.unidad, programa: f4.programa, partida: f4.partida });
          return { t: t, v: rows.length ? sum(rows, f) : (sum([], f)), rows: rows, partial: isPartial(y, t) };
        })
      };
    });
    var max = 0n;
    data.forEach(function (g) { g.vals.forEach(function (x) { if (x.v != null && x.v > max) max = x.v; }); });

    var chart = $('chart');
    chart.style.setProperty('--n', YEARS.length);
    chart.innerHTML = data.map(function (g) {
      return '<div class="grp">' + g.vals.map(function (x) {
        var pct = max > 0n && x.v != null ? Number(x.v) / Number(max) * 86 : 0; // float solo para el alto de la barra
        var cls = 'bar t-' + x.t + (x.partial ? ' is-partial' : '') + (g.y === state.ejercicio && x.t === state.tipo ? ' is-sel' : '');
        return '<div class="bar-wrap" title="' + esc(x.t + ' ' + g.y + ': ' + money(x.v)) + '">' +
          '<div class="bar-val">' + esc(compact(x.v)) + '</div>' +
          (x.v == null ? '' : '<div class="' + cls + '" style="height:' + pct.toFixed(2) + '%"></div>') + '</div>';
      }).join('') + '</div>';
    }).join('');

    // Etiquetas del eje (se agregan tras el gráfico)
    var old = document.getElementById('xlabels');
    if (old) old.remove();
    var xl = document.createElement('div');
    xl.className = 'xlabels'; xl.id = 'xlabels'; xl.style.setProperty('--n', YEARS.length);
    xl.innerHTML = YEARS.map(function (y) {
      var c = META.cortes[tipos[0] + '-' + y];
      return '<div>' + y + '<small>' + (c ? (isPartial(y, tipos[0]) ? 'parcial al ' : 'cierre ') + fechaCorta(c) : '') + '</small></div>';
    }).join('');
    chart.insertAdjacentElement('afterend', xl);

    var anyPartial = data.some(function (g) { return g.vals.some(function (x) { return x.partial; }); });
    $('legend').innerHTML =
      tipos.map(function (t) { return '<span><i class="' + (t === 'AC' ? 'l-ac' : 'l-em') + '"></i>' + esc(TIPOS[t]) + '</span>'; }).join('') +
      (anyPartial ? '<span><i class="l-par"></i>Ejercicio parcial (acumulado a la fecha de corte)</span>' : '') +
      '<span><i class="l-sel"></i>Ejercicio elegido en filtros</span>' +
      '<span>Métrica: <b>' + esc(METRICS[state.metric].label) + '</b></span>';

    // Texto alternativo + tabla
    var alt = data.map(function (g) {
      return g.y + ': ' + g.vals.map(function (x) { return x.t + ' ' + money(x.v); }).join(', ');
    }).join('. ');
    $('chart-alt').textContent = 'Gráfico de barras de ' + METRICS[state.metric].label + ' por ejercicio. ' + alt;

    var head = '<tr><th scope="col">Ejercicio</th>' + tipos.map(function (t) {
      return '<th scope="col" class="num">' + t + ' · ' + esc(METRICS[state.metric].label) + '</th><th scope="col" class="num">' + t + ' · % ejecución</th>';
    }).join('') + '</tr>';
    var body = data.map(function (g) {
      return '<tr><th scope="row">' + g.y + (g.vals[0].partial ? ' (parcial)' : '') + '</th>' + g.vals.map(function (x) {
        var vig = sum(x.rows, 'v'), dev = sum(x.rows, 'd');
        var ej = vig ? ratio(dev, vig) : null;
        return '<td class="num">' + esc(money(x.v)) + '</td><td class="num">' + (ej == null ? 'n/d' : esc(nfPct.format(ej))) + '</td>';
      }).join('') + '</tr>';
    }).join('');
    $('annual-table').innerHTML = '<caption>Total por ejercicio en pesos corrientes. % ejecución = devengado / presupuesto vigente.</caption><thead>' + head + '</thead><tbody>' + body + '</tbody>';
  }

  // --- Top ---
  var DIMS = {
    jur: { label: 'Jurisdicción', key: function (r) { return r.jc; }, name: function (r) { return r.jc + ' · ' + r.jn; }, sub: null },
    unidad: { label: 'Unidad', key: function (r) { return r.jc + '|' + r.u; }, name: function (r) { return r.u; }, sub: function (r) { return r.jn; } },
    programa: { label: 'Programa', key: function (r) { return r.p; }, name: function (r) { return r.p; }, sub: null },
    partida: { label: 'Partida', key: function (r) { return r.pc; }, name: function (r) { return r.pc + ' · ' + r.pn; }, sub: null }
  };
  function renderTop(rows) {
    var f = METRICS[state.metric].f, dim = DIMS[state.dim];
    var total = sum(rows, f);
    var host = $('top-body');
    if (!rows.length) { host.innerHTML = '<p class="empty">No hay filas para este filtro.</p>'; return; }
    if (total == null) { host.innerHTML = '<p class="empty">' + esc(METRICS[state.metric].label) + ' no está informado para ' + esc(state.tipo) + '. Elegí otra métrica.</p>'; return; }
    var m = new Map();
    rows.forEach(function (r) {
      var k = dim.key(r), e = m.get(k);
      if (!e) { e = { name: dim.name(r), sub: dim.sub ? dim.sub(r) : '', v: 0n, n: 0 }; m.set(k, e); }
      e.v += r[f] || 0n; e.n++;
    });
    var all = Array.from(m.values()).sort(function (a, b) { return cmp(b.v, a.v); });
    var top = all.slice(0, state.n);
    var topSum = top.reduce(function (s, e) { return s + e.v; }, 0n);
    var max = top.length ? top[0].v : 0n;
    var body = top.map(function (e, i) {
      var share = total ? Number(e.v) / Number(total) : 0; // float solo para mostrar el porcentaje
      return '<tr><td class="pos">' + (i + 1) + '</td>' +
        '<th scope="row" class="name">' + esc(e.name) + (e.sub ? '<small>' + esc(e.sub) + '</small>' : '') + '</th>' +
        '<td class="barcell"><div class="meter t-' + state.tipo + '" aria-hidden="true"><i style="width:' + (max ? (Number(e.v) / Number(max) * 100).toFixed(1) : 0) + '%"></i></div></td>' +
        '<td class="num">' + esc(money(e.v)) + '</td><td class="num">' + esc(nfPct.format(share)) + '</td></tr>';
    }).join('');
    host.innerHTML = '<div class="table-scroll"><table class="rank">' +
      '<caption>Top ' + top.length + ' de ' + all.length + ' por ' + esc(dim.label.toLowerCase()) + ' · ' + esc(METRICS[state.metric].label) + ' · ' + state.tipo + ' ' + state.ejercicio + '</caption>' +
      '<thead><tr><th scope="col" class="num">#</th><th scope="col">' + esc(dim.label) + '</th><th scope="col"><span class="sr-only">Proporción</span></th>' +
      '<th scope="col" class="num">' + esc(METRICS[state.metric].label) + '</th><th scope="col" class="num">% del total</th></tr></thead>' +
      '<tbody>' + body + '</tbody>' +
      '<tfoot><tr><th scope="row" colspan="3">Total del filtro (' + all.length + ' ' + esc(dim.label.toLowerCase()) + (all.length === 1 ? '' : 's') + ')</th><td class="num">' + esc(money(total)) + '</td><td class="num">100,0 %</td></tr></tfoot>' +
      '</table></div>' +
      '<p class="rank-sum">El top ' + top.length + ' concentra ' + esc(nfPct.format(total ? Number(topSum) / Number(total) : 0)) + ' del total filtrado. El porcentaje es sobre el total del ejercicio, tipo y filtros elegidos.</p>';
  }

  // --- Detalle ---
  var COLS = [
    { k: 'jn', label: 'Jurisdicción', get: function (r) { return r.jc + ' · ' + r.jn; } },
    { k: 'u', label: 'Unidad', get: function (r) { return r.u; } },
    { k: 'p', label: 'Programa', get: function (r) { return r.p; } },
    { k: 'pn', label: 'Partida', get: function (r) { return r.pc + ' · ' + r.pn; } },
    { k: 'v', label: 'Presupuesto vigente', num: true },
    { k: 'c', label: 'Compromiso', num: true },
    { k: 'd', label: 'Devengado', num: true },
    { k: 'g', label: 'Pagado', num: true }
  ];
  function renderDetail(rows) {
    var col = COLS.filter(function (c) { return c.k === state.sortKey; })[0] || COLS[6];
    var dir = state.sortDir;
    var sorted = rows.slice().sort(function (a, b) {
      if (col.num) {
        var x = a[col.k], y = b[col.k];
        if (x == null && y == null) return 0;
        if (x == null) return 1;
        if (y == null) return -1;
        return cmp(x, y) * dir;
      }
      return col.get(a).localeCompare(col.get(b), 'es', { numeric: true }) * dir;
    });
    var pages = Math.max(1, Math.ceil(sorted.length / state.pageSize));
    state.page = Math.min(state.page, pages - 1);
    var slice = sorted.slice(state.page * state.pageSize, (state.page + 1) * state.pageSize);

    var head = COLS.map(function (c) {
      var sel = c.k === state.sortKey;
      return '<th scope="col" class="' + (c.num ? 'num' : '') + '" aria-sort="' + (sel ? (dir > 0 ? 'ascending' : 'descending') : 'none') + '">' +
        '<button type="button" data-sort="' + c.k + '">' + esc(c.label) + '<span class="arrow" aria-hidden="true">' + (sel ? (dir > 0 ? '▲' : '▼') : '') + '</span></button></th>';
    }).join('');
    var body = slice.map(function (r) {
      return '<tr><td>' + esc(COLS[0].get(r)) + '</td><td>' + esc(r.u) + '</td><td>' + esc(r.p) + '</td><td>' + esc(COLS[3].get(r)) + '</td>' +
        ['v', 'c', 'd', 'g'].map(function (k) {
          return r[k] == null ? '<td class="num nd">s/d</td>' : '<td class="num">' + esc(money(r[k])) + '</td>';
        }).join('') + '</tr>';
    }).join('');
    var foot = '<tr><th scope="row" colspan="4">Total de ' + nf0.format(rows.length) + ' filas filtradas (todas las páginas)</th>' +
      ['v', 'c', 'd', 'g'].map(function (k) { var t = sum(rows, k); return '<td class="num">' + esc(money(t)) + '</td>'; }).join('') + '</tr>';
    $('detail-table').innerHTML = '<caption>' + esc(state.tipo) + ' · ejercicio ' + state.ejercicio + ' · ordenado por ' + esc(col.label.toLowerCase()) + (dir > 0 ? ' (menor a mayor)' : ' (mayor a menor)') + '</caption>' +
      '<thead><tr>' + head + '</tr></thead><tbody>' + (body || '<tr><td colspan="8" class="empty">No hay filas para este filtro.</td></tr>') + '</tbody><tfoot>' + foot + '</tfoot>';
    var from = sorted.length ? state.page * state.pageSize + 1 : 0;
    $('pg-info').textContent = 'Filas ' + nf0.format(from) + '–' + nf0.format(Math.min(sorted.length, (state.page + 1) * state.pageSize)) + ' de ' + nf0.format(sorted.length) + ' · página ' + (state.page + 1) + ' de ' + pages;
    $('pg-prev').disabled = state.page === 0;
    $('pg-next').disabled = state.page >= pages - 1;
  }

  function renderNotas() {
    $('notas').innerHTML = META.notas.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('');
  }

  function showTab(name, focus) {
    state.tab = name;
    TABS.forEach(function (t) {
      var on = t === name, b = $('tab-' + t);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.tabIndex = on ? 0 : -1;
      $('panel-' + t).hidden = !on;
      if (on && focus) b.focus();
    });
  }

  function renderAll() {
    metricAvailability();
    var rows = currentRows();
    renderStatus();
    renderSelection();
    renderKpis(rows);
    renderAnnual();
    renderTop(rows);
    renderDetail(rows);
    showTab(state.tab);
    writeHash();
  }

  // ---------- Eventos ----------
  function bind() {
    $('f-ejercicio').addEventListener('change', function (e) { state.ejercicio = +e.target.value; state.page = 0; syncFilters(); renderAll(); });
    document.querySelectorAll('input[name="tipo"]').forEach(function (r) {
      r.addEventListener('change', function (e) { state.tipo = e.target.value; state.page = 0; syncFilters(); renderAll(); });
    });
    [['f-jur', 'jur'], ['f-unidad', 'unidad'], ['f-programa', 'programa'], ['f-partida', 'partida']].forEach(function (p) {
      $(p[0]).addEventListener('change', function (e) { state[p[1]] = e.target.value; state.page = 0; syncFilters(); renderAll(); });
    });
    document.querySelectorAll('input[name="metric"]').forEach(function (r) {
      r.addEventListener('change', function (e) {
        state.metric = e.target.value;
        state.sortKey = METRICS[state.metric].f; state.sortDir = -1; state.page = 0;
        renderAll();
      });
    });
    $('f-compare').addEventListener('change', function (e) { state.compare = e.target.checked; renderAll(); });
    $('top-dim').addEventListener('change', function (e) { state.dim = e.target.value; renderAll(); });
    $('top-n').addEventListener('change', function (e) { state.n = +e.target.value; renderAll(); });
    $('page-size').addEventListener('change', function (e) { state.pageSize = +e.target.value; state.page = 0; renderAll(); });
    $('pg-prev').addEventListener('click', function () { state.page = Math.max(0, state.page - 1); renderDetail(currentRows()); $('detail-scroll').scrollIntoView({ block: 'nearest' }); });
    $('pg-next').addEventListener('click', function () { state.page++; renderDetail(currentRows()); $('detail-scroll').scrollIntoView({ block: 'nearest' }); });
    $('detail-table').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-sort]');
      if (!b) return;
      var k = b.getAttribute('data-sort');
      if (state.sortKey === k) state.sortDir = -state.sortDir; else { state.sortKey = k; state.sortDir = COLS.filter(function (c) { return c.k === k; })[0].num ? -1 : 1; }
      state.page = 0;
      renderDetail(currentRows());
      var nb = document.querySelector('#detail-table button[data-sort="' + k + '"]');
      if (nb) nb.focus();
    });
    $('btn-reset').addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      state.jur = state.unidad = state.programa = state.partida = ''; state.page = 0;
      syncFilters(); renderAll();
    });

    // Pestañas con teclado (flechas, inicio, fin)
    var tabs = document.querySelector('.tabs');
    tabs.addEventListener('click', function (e) {
      var b = e.target.closest('[role="tab"]'); if (b) { showTab(b.dataset.tab); writeHash(); }
    });
    tabs.addEventListener('keydown', function (e) {
      var i = TABS.indexOf(state.tab), n = TABS.length, j = null;
      if (e.key === 'ArrowRight') j = (i + 1) % n;
      else if (e.key === 'ArrowLeft') j = (i - 1 + n) % n;
      else if (e.key === 'Home') j = 0;
      else if (e.key === 'End') j = n - 1;
      if (j != null) { e.preventDefault(); showTab(TABS[j], true); writeHash(); }
    });

    // En móvil, los filtros arrancan plegados
    if (window.matchMedia('(max-width: 900px)').matches) $('filters-box').open = false;
  }

  // ---------- Arranque ----------
  function fail(msg) {
    var m = document.createElement('p');
    m.className = 'wrap notice'; m.setAttribute('role', 'alert');
    m.textContent = msg;
    document.querySelector('main').prepend(m);
  }

  Promise.all([
    fetch('data/gastos.json').then(function (r) { if (!r.ok) throw new Error('gastos.json: ' + r.status); return r.json(); }),
    fetch('data/meta.json').then(function (r) { if (!r.ok) throw new Error('meta.json: ' + r.status); return r.json(); })
  ]).then(function (res) {
    if (res[0].unidad_monto !== 'centavos') throw new Error('los montos de gastos.json no están en centavos (unidad_monto=' + res[0].unidad_monto + ')');
    var cols = res[0].columnas, idx = {};
    cols.forEach(function (c, i) { idx[c] = i; });
    DATA = res[0].filas.map(function (f) {
      return {
        t: f[idx.tipo], y: f[idx.ejercicio], corte: f[idx.fecha_corte], jc: f[idx.jur_codigo], jn: f[idx.jur_nombre],
        u: f[idx.unidad], p: f[idx.programa], pc: f[idx.partida_codigo], pn: f[idx.partida_nombre],
        v: toCents(f[idx.presupuesto_vigente]), c: toCents(f[idx.compromiso]), d: toCents(f[idx.devengado]), g: toCents(f[idx.pagado])
      };
    });
    META = res[1];
    YEARS = Array.from(new Set(DATA.map(function (r) { return r.y; }))).sort();
    state.ejercicio = YEARS[YEARS.length - 2] || YEARS[0];
    readHash();
    $('f-ejercicio').innerHTML = YEARS.map(function (y) {
      return '<option value="' + y + '">' + y + (isPartial(y, 'AC') ? ' (parcial)' : '') + '</option>';
    }).join('');
    $('f-ejercicio').value = state.ejercicio;
    document.querySelector('input[name="tipo"][value="' + state.tipo + '"]').checked = true;
    $('top-dim').value = state.dim; $('top-n').value = state.n;
    state.sortKey = METRICS[state.metric].f;
    renderNotas();
    bind();
    syncFilters();
    renderAll();
  }).catch(function (err) {
    fail('No se pudieron cargar los datos (' + err.message + '). Si abriste el archivo con doble clic, servilo con: python3 -m http.server -d web 8000');
    if (window.console) console.error(err);
  });
})();
