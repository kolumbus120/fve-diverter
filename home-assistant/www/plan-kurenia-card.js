/*
 * plan-kurenia-card — týždenný plán kúrenia Daikin (normál / útlm)
 * 2026-11-16, github.com/kolumbus120/fve-diverter: home-assistant/www/plan-kurenia-card.js
 * nasadené ako /config/www/plan-kurenia-card.js → /local/plan-kurenia-card.js
 *
 * Dáta: sensor.plan_kurenia_prehlad (packages/daikin_plan_kurenia.yaml) — rozpis
 * dní, surové profily rozvrhov, najbližšia zmena. Úprava blokov zapisuje priamo
 * do pomocníkov schedule.daikin_plan_tyzden / schedule.daikin_plan_sviatok
 * (WS schedule/update — vyžaduje admin účet). Pásik pod dňom: história
 * input_boolean.fve_daikin_slnko_aktivne (slnko/FVE) a HDO.
 *
 *   type: custom:plan-kurenia-card
 *   mode: full            # full = celý týždeň + editor, compact = dnes + odkaz,
 *                         # sviatky = zoznam sviatkov roka s prepínačom aktívny/neaktívny
 *   link: /plan-kurenia/plan   # (compact) kam vedie tlačidlo
 *
 * Režim sviatky: zoznam z calendar.slovensko (integrácia Sviatky, SK, aj kategória
 * „workday“ = štátne sviatky bez voľna). Aktívny = deň sa správa ako sviatok.
 * Stav sa číta z calendar.workday_sensor_sk_kalendar (udalosť = pracovný deň) a mení
 * cez nastavenia integrácie Workday (add_holidays / remove_holidays) — prejaví sa
 * všade, kde sa používa binary_sensor.workday_sensor_sk (plán kúrenia, TUV, obeh TUV).
 * Cez víkend prepínač nemá vplyv (víkend ostáva víkendom).
 */
const E = {
  prehlad: 'sensor.plan_kurenia_prehlad',
  aktivny: 'input_boolean.daikin_plan_kurenia_aktivny',
  normal: 'binary_sensor.daikin_plan_kurenia_normal',
  ciel: 'sensor.daikin_cielovy_posun_kurenia',
  daikin: 'number.space_heating_temperature_control',
  offNormal: 'input_number.daikin_offset_normal',
  utlm: 'input_number.daikin_utlm',
  slnko: 'input_boolean.fve_daikin_slnko_aktivne',
  hdo: 'binary_sensor.espaltherma_benefit_kwh_rate_power_supply',
  kurenie: 'switch.space_heating_climate_control',
};
const SCH = { tyzden: 'daikin_plan_tyzden', sviatok: 'daikin_plan_sviatok' };
const DNI = ['Po', 'Ut', 'St', 'Št', 'Pi', 'So', 'Ne'];
const DNI_DLHE = ['Pondelok', 'Utorok', 'Streda', 'Štvrtok', 'Piatok', 'Sobota', 'Nedeľa'];
const MENA = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

const toMin = (s) => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };
const endMin = (s) => (s >= '23:59' ? 1440 : toMin(s));
const fmt = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
const pct = (m) => `${(m / 1440) * 100}%`;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dDM = (iso) => { const [, m, d] = iso.split('-'); return `${+d}.${+m}.`; };
const localISO = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

class PlanKureniaCard extends HTMLElement {
  setConfig(config) {
    this._config = { mode: 'full', link: '/plan-kurenia/plan', ...config };
    this._edit = null;      // {kind:'tyzden'|'sviatok', den, bloky:[[od,do]...], err}
    this._hist = null;      // {slnko:[[t0,t1]], hdo:[[t0,t1]]} v ms
    this._histAt = 0;
    this._key = '';
    this._saving = false;
    this._rok = new Date().getFullYear();
    this._sv = null; this._svErr = null; this._svBusy = null; this._svLoaded = null;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
  }

  getCardSize() { return this._config && this._config.mode === 'compact' ? 4 : this._config && this._config.mode === 'sviatky' ? 8 : 12; }
  getGridOptions() { return this._config && this._config.mode !== 'full' ? { columns: 12, rows: 'auto' } : { columns: 'full', rows: 'auto' }; }

  set hass(hass) {
    this._hass = hass;
    if (this._config.mode === 'sviatky') {
      if (this._svLoaded !== this._rok) this._loadSviatky();
      const k = 'sv|' + Math.floor(Date.now() / 3600000);
      if (k !== this._key) { this._key = k; this._render(); }
      return;
    }
    const ids = [E.prehlad, E.aktivny, E.normal, E.ciel, E.daikin, E.offNormal, E.utlm, E.slnko, E.hdo, E.kurenie];
    const key = ids.map((i) => (hass.states[i] ? hass.states[i].last_updated : '-')).join('|') + '|' + Math.floor(Date.now() / 60000);
    if (Date.now() - this._histAt > 5 * 60000) this._loadHist();
    if (key !== this._key) { this._key = key; this._render(); }
  }

  connectedCallback() {
    this._tick = setInterval(() => { this._key = ''; if (this._hass) this.hass = this._hass; }, 60000);
  }
  disconnectedCallback() { clearInterval(this._tick); }

  // ---------------------------------------------------------------- data
  _st(id) { return this._hass && this._hass.states[id]; }
  _dni() { const s = this._st(E.prehlad); return (s && s.attributes.dni) || []; }

  async _loadHist() {
    this._histAt = Date.now();
    const dni = this._dni();
    if (!dni.length || !this._hass) return;
    const start = new Date(`${dni[0].datum}T00:00:00`);
    try {
      const r = await this._hass.callWS({
        type: 'history/history_during_period', start_time: start.toISOString(), end_time: new Date().toISOString(),
        entity_ids: [E.slnko, E.hdo], minimal_response: true, no_attributes: true,
      });
      const iv = (arr) => {
        const out = []; let on = null;
        (arr || []).forEach((x) => {
          const t = (x.lu || x.lc) * 1000; const s = x.s;
          if (s === 'on' && on === null) on = t;
          if (s !== 'on' && on !== null) { out.push([on, t]); on = null; }
        });
        if (on !== null) out.push([on, Date.now()]);
        return out;
      };
      this._hist = { slnko: iv(r[E.slnko]), hdo: iv(r[E.hdo]) };
      this._key = ''; this._render();
    } catch (e) { this._hist = null; }
  }

  // ---------------------------------------------------------------- render helpers
  _bar(bloky, opts = {}) {
    const h = opts.h || 22;
    let s = `<div class="bar ${opts.cls || ''}" style="height:${h}px">`;
    if (opts.dovolenka) s += `<div class="dov"></div>`;
    else (bloky || []).forEach(([a, b]) => {
      const x0 = toMin(a); const x1 = endMin(b);
      s += `<div class="blk" style="left:${pct(x0)};width:${pct(x1 - x0)}" title="${a}–${b === '23:59' ? '24:00' : b} normál">${opts.labels && x1 - x0 >= 120 ? `<span>${a}–${b >= '23:59' ? '24:00' : b}</span>` : ''}</div>`;
    });
    if (opts.now !== undefined) s += `<div class="now" style="left:${pct(opts.now)}"></div>`;
    return s + '</div>';
  }

  _strips(datum) {
    if (!this._hist) return '';
    const d0 = new Date(`${datum}T00:00:00`).getTime(); const d1 = d0 + 86400000;
    if (d0 > Date.now()) return '';
    const seg = (list, cls) => list.filter(([a, b]) => b > d0 && a < d1).map(([a, b]) => {
      const x0 = (Math.max(a, d0) - d0) / 60000; const x1 = (Math.min(b, d1) - d0) / 60000;
      return `<div class="${cls}" style="left:${pct(x0)};width:${pct(Math.max(x1 - x0, 3))}" title="${cls === 's' ? 'slnko (FVE)' : 'HDO'} ${fmt(Math.round(x0))}–${fmt(Math.round(x1))}"></div>`;
    }).join('');
    return `<div class="strip">${seg(this._hist.slnko, 's')}${seg(this._hist.hdo, 'h')}</div>`;
  }

  _status() {
    const pr = this._st(E.prehlad); const ciel = this._st(E.ciel); const dk = this._st(E.daikin);
    const akt = this._st(E.aktivny);
    const dovod = ciel ? ciel.attributes.dovod || '' : '';
    const teraz = dovod.startsWith('normál') ? 'normál' : dovod.startsWith('útlm') || dovod.startsWith('dovolenka') ? 'útlm' : dovod;
    let next = '—';
    if (pr && pr.state && !['unknown', 'unavailable'].includes(pr.state)) {
      const t = new Date(pr.state); const diff = Math.round((t - Date.now()) / 60000);
      const dn = DNI[(t.getDay() + 6) % 7];
      const rel = diff < 60 ? `o ${diff} min` : diff < 1440 ? `o ${Math.floor(diff / 60)} h ${diff % 60} min` : `o ${Math.round(diff / 1440)} d`;
      next = `${dn} ${t.getDate()}.${t.getMonth() + 1}. ${fmt(t.getHours() * 60 + t.getMinutes())} → <b>${esc(pr.attributes.dalsi_stav || '')}</b> <span class="mut">(${rel})</span>`;
    }
    const num = (s) => (s && !isNaN(parseFloat(s.state)) ? `${parseFloat(s.state) > 0 ? '+' : ''}${parseFloat(s.state)} °C` : '—');
    const on = akt && akt.state === 'on';
    return `
      <div class="head">
        <div class="title">Plán kúrenia</div>
        <button class="chip ${on ? 'on' : ''}" data-act="toggle">${on ? '● Plán aktívny' : '○ Plán vypnutý'}</button>
      </div>
      <div class="status">
        <div><span class="mut">Teraz</span> <b class="${teraz === 'normál' ? 'tn' : 'tu'}">${esc(teraz || '—')}</b>${dovod && dovod !== teraz ? ` <span class="mut">(${esc(dovod)})</span>` : ''}</div>
        <div><span class="mut">Cieľ</span> <b>${num(ciel)}</b> <span class="mut">· Daikin</span> <b>${num(dk)}</b></div>
        <div><span class="mut">Najbližšia zmena</span> ${on ? next : '<span class="mut">plán je vypnutý</span>'}</div>
      </div>`;
  }

  _axis() {
    let s = '<div class="axis">';
    for (let hr = 0; hr <= 24; hr += 1) {
      const major = hr % 3 === 0;
      s += `<div class="tick ${major ? 'maj' : ''} ${hr % 6 === 0 ? 'six' : ''}" style="left:${pct(hr * 60)}">${major ? `<span>${hr}</span>` : ''}</div>`;
    }
    return s + '</div>';
  }

  _render() {
    if (!this._hass || !this.shadowRoot) return;
    const pr = this._st(E.prehlad);
    const css = this._css();
    if (!pr && this._config.mode !== 'sviatky') { this.shadowRoot.innerHTML = `${css}<ha-card><div class="pad">Chýba ${E.prehlad}</div></ha-card>`; return; }
    if (this._config.mode === 'sviatky') { this._renderSviatky(css); this._bind(); return; }
    if (this._config.mode === 'compact') this._renderCompact(css);
    else this._renderFull(css);
    this._bind();
  }

  _renderCompact(css) {
    const dni = this._dni(); const today = localISO(new Date());
    const d = dni.find((x) => x.datum === today);
    const nowM = new Date().getHours() * 60 + new Date().getMinutes();
    const tag = d && d.profil !== 'týždeň' ? `<span class="tag ${d.profil === 'dovolenka' ? 'td' : ''}">${esc(d.profil)}</span>` : '';
    this.shadowRoot.innerHTML = `${css}<ha-card><div class="pad">
      ${this._status()}
      <div class="grid compact">
        <div></div>${this._axis()}
        <div class="lbl today">Dnes ${tag}</div>
        <div class="cell">${d ? this._bar(d.bloky, { dovolenka: d.profil === 'dovolenka', now: nowM, labels: true }) : ''}${d ? this._strips(d.datum) : ''}</div>
      </div>
      ${this._legend()}
      <button class="btn wide" data-act="open">Otvoriť plán kúrenia →</button>
    </div></ha-card>`;
  }

  _renderFull(css) {
    const pr = this._st(E.prehlad); const a = pr.attributes;
    const dni = this._dni().slice(0, 7);
    const ty = a.profil_tyzden || [[], [], [], [], [], [], []];
    const sv = a.profil_sviatok || [];
    const today = localISO(new Date());
    const nowM = new Date().getHours() * 60 + new Date().getMinutes();
    let rows = '';
    dni.forEach((d, i) => {
      const isToday = d.datum === today;
      const special = d.profil !== 'týždeň';
      const sel = this._edit && this._edit.kind === 'tyzden' && this._edit.den === i;
      rows += `
        <div class="lbl ${isToday ? 'today' : ''} ${sel ? 'sel' : ''}" data-act="edit" data-kind="tyzden" data-den="${i}">
          <span class="dn">${DNI[i]}</span> <span class="dt">${dDM(d.datum)}</span>
          ${special ? `<span class="tag ${d.profil === 'dovolenka' ? 'td' : ''}">${esc(d.profil)}</span>` : ''}
        </div>
        <div class="cell ${isToday ? 'today' : ''} ${sel ? 'sel' : ''}" data-act="edit" data-kind="tyzden" data-den="${i}">
          ${this._bar(ty[i], { now: isToday ? nowM : undefined, labels: true, cls: special ? 'dim' : '' })}
          ${special ? `<div class="eff"><span>${d.profil === 'dovolenka' ? 'platí: celý deň útlm (dovolenka)' : 'platí: profil Sviatok / prázdniny'}</span>${this._bar(d.bloky, { h: 6, dovolenka: d.profil === 'dovolenka' })}</div>` : ''}
          ${this._strips(d.datum)}
        </div>`;
    });
    const selSv = this._edit && this._edit.kind === 'sviatok';
    rows += `
      <div class="lbl sv ${selSv ? 'sel' : ''}" data-act="edit" data-kind="sviatok"><span class="dn">Sviatok</span> <span class="dt">/ prázdniny</span></div>
      <div class="cell sv ${selSv ? 'sel' : ''}" data-act="edit" data-kind="sviatok">${this._bar(sv, { labels: true })}</div>`;

    const rng = (r, name) => (r && r[0] && r[1] && r[1] >= today && r[0] <= r[1] ? `<span class="tag ${name === 'Dovolenka' ? 'td' : ''}">${name} ${dDM(r[0])}–${dDM(r[1])}</span>` : '');
    const ranges = rng(a.prazdniny, 'Prázdniny') + rng(a.dovolenka, 'Dovolenka');

    this.shadowRoot.innerHTML = `${css}<ha-card><div class="pad">
      ${this._status()}
      ${ranges ? `<div class="ranges">${ranges}</div>` : ''}
      <div class="grid">
        <div class="lbl hint">klik na deň = úprava</div>${this._axis()}
        ${rows}
      </div>
      ${this._legend()}
      ${this._editor()}
    </div></ha-card>`;
  }

  _legend() {
    return `<div class="legend">
      <span><i class="lg n"></i>normál</span><span><i class="lg u"></i>útlm</span>
      <span><i class="lg s"></i>slnko (FVE riadi)</span><span><i class="lg h"></i>HDO</span>
      <span><i class="lg d"></i>dovolenka</span></div>`;
  }

  _editor() {
    const ed = this._edit; if (!ed) return '';
    const title = ed.kind === 'sviatok' ? 'Sviatok / prázdniny (všetky dni rovnako)' : DNI_DLHE[ed.den];
    const preview = ed.bloky.filter(([x, y]) => /^\d\d:\d\d$/.test(x) && /^\d\d:\d\d$/.test(y));
    const list = ed.bloky.map(([od, d], j) => `
      <div class="brow">
        <span class="mut">normál od</span> <input type="time" step="900" value="${od}" data-j="${j}" data-f="0">
        <span class="mut">do</span> <input type="time" step="900" value="${d === '24:00' ? '00:00' : d}" data-j="${j}" data-f="1">
        <button class="ic" data-act="del" data-j="${j}" title="zmazať blok">✕</button>
      </div>`).join('');
    return `<div class="editor">
      <div class="etitle">Úprava: <b>${esc(title)}</b></div>
      ${this._bar(preview.map(([x, y]) => [x, y === '00:00' || y === '24:00' ? '23:59' : y]), { labels: true })}
      ${list || '<div class="mut">Žiadny blok — celý deň útlm.</div>'}
      <div class="mut small">Čas po 15 min. „do 00:00“ = do polnoci. Mimo blokov je útlm.</div>
      ${ed.err ? `<div class="err">${esc(ed.err)}</div>` : ''}
      <div class="ebtns">
        <button class="btn" data-act="add">+ pridať blok</button>
        <span class="sp"></span>
        <button class="btn" data-act="cancel">Zrušiť</button>
        ${ed.kind === 'tyzden' ? '<button class="btn" data-act="save" data-scope="pracovne">Uložiť na Po–Pi</button><button class="btn" data-act="save" data-scope="vsetky">Uložiť na celý týždeň</button>' : ''}
        <button class="btn pri" data-act="save" data-scope="den" ${this._saving ? 'disabled' : ''}>${this._saving ? 'Ukladám…' : 'Uložiť'}</button>
      </div></div>`;
  }

  // ---------------------------------------------------------------- events
  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll('[data-act]').forEach((el) => el.addEventListener('click', (ev) => this._onAct(ev, el)));
    root.querySelectorAll('.editor input[type=time]').forEach((el) => el.addEventListener('input', () => {
      const j = +el.dataset.j; const f = +el.dataset.f;
      this._edit.bloky[j][f] = el.value || '';
    }));
    root.querySelectorAll('.editor input[type=time]').forEach((el) => el.addEventListener('change', () => {
      this._edit.err = null; this._key = ''; this._render();
    }));
  }

  _onAct(ev, el) {
    const act = el.dataset.act; ev.stopPropagation();
    const a = this._st(E.prehlad) ? this._st(E.prehlad).attributes : {};
    if (act === 'toggle') this._hass.callService('input_boolean', 'toggle', { entity_id: E.aktivny });
    else if (act === 'open') {
      history.pushState(null, '', this._config.link);
      window.dispatchEvent(new CustomEvent('location-changed', { detail: { replace: false } }));
    } else if (act === 'edit') {
      const kind = el.dataset.kind; const den = el.dataset.den !== undefined ? +el.dataset.den : null;
      const src = kind === 'sviatok' ? a.profil_sviatok || [] : (a.profil_tyzden || [])[den] || [];
      this._edit = { kind, den, bloky: src.map(([x, y]) => [x, y >= '23:59' ? '24:00' : y]), err: null };
    } else if (act === 'add') {
      const last = this._edit.bloky[this._edit.bloky.length - 1];
      const st = last ? Math.min(endMin(last[1] === '24:00' ? '23:59' : last[1]) + 60, 1380) : 360;
      this._edit.bloky.push([fmt(st), fmt(Math.min(st + 60, 1425))]);
    } else if (act === 'del') this._edit.bloky.splice(+el.dataset.j, 1);
    else if (act === 'cancel') this._edit = null;
    else if (act === 'save') { this._save(el.dataset.scope); return; }
    else if (act === 'sv') { if (!this._svBusy) this._toggleSviatok(el.dataset.d, el.dataset.on === '1'); return; }
    else if (act === 'rok') { this._rok += +el.dataset.k; this._sv = null; this._loadSviatky(); return; }
    this._key = ''; this._render();
  }

  _normalize(bloky) {
    const out = [];
    for (const [od, d] of bloky) {
      if (!/^\d\d:\d\d$/.test(od) || !/^\d\d:\d\d$/.test(d)) throw new Error('Vyplň čas od aj do pri každom bloku.');
      const snap = (m) => Math.round(m / 15) * 15;
      const a = snap(toMin(od)); let b = d === '00:00' || d === '24:00' ? 1440 : snap(toMin(d));
      if (b <= a) throw new Error(`Blok ${od}–${d}: koniec musí byť po začiatku (do polnoci zadaj 00:00).`);
      out.push([a, Math.min(b, 1440)]);
    }
    out.sort((x, y) => x[0] - y[0]);
    const merged = [];
    for (const blk of out) {
      const last = merged[merged.length - 1];
      if (last && blk[0] <= last[1]) last[1] = Math.max(last[1], blk[1]); else merged.push([...blk]);
    }
    return merged.map(([a, b]) => ({ from: `${fmt(a)}:00`, to: b === 1440 ? '24:00:00' : `${fmt(b)}:00` }));
  }

  async _save(scope) {
    const ed = this._edit;
    let bl;
    try { bl = this._normalize(ed.bloky); } catch (e) { ed.err = e.message; this._key = ''; this._render(); return; }
    this._saving = true; this._key = ''; this._render();
    try {
      const all = await this._hass.callWS({ type: 'schedule/list' });
      const id = SCH[ed.kind];
      const item = all.find((x) => x.id === id);
      if (!item) throw new Error(`Rozvrh ${id} sa nenašiel.`);
      const payload = { type: 'schedule/update', schedule_id: id, name: item.name };
      if (item.icon) payload.icon = item.icon;
      MENA.forEach((m) => { payload[m] = (item[m] || []).map((x) => ({ from: x.from, to: x.to })); });
      if (ed.kind === 'sviatok' || scope === 'vsetky') MENA.forEach((m) => { payload[m] = bl; });
      else if (scope === 'pracovne') MENA.slice(0, 5).forEach((m) => { payload[m] = bl; });
      else payload[MENA[ed.den]] = bl;
      await this._hass.callWS(payload);
      this._edit = null;
    } catch (e) {
      ed.err = `Uloženie zlyhalo: ${e.message || e.code || e}`;
    }
    this._saving = false; this._key = ''; this._render();
  }

  // ---------------------------------------------------------------- sviatky
  async _loadSviatky() {
    const y = this._rok; this._svLoaded = y;
    const q = (cal) => this._hass.callApi('GET', `calendars/${cal}?start=${y}-01-01T00:00:00&end=${y}-12-31T23:59:00`);
    const dd = (e) => (e.start && (e.start.date || (e.start.dateTime || '').slice(0, 10))) || '';
    try {
      const [sv, wd] = await Promise.all([q('calendar.slovensko'), q('calendar.workday_sensor_sk_kalendar')]);
      const seen = new Set();
      this._sv = sv.map((e) => ({ datum: dd(e), nazov: e.summary }))
        .filter((x) => x.datum.startsWith(String(y)) && !seen.has(x.datum) && seen.add(x.datum))
        .sort((a, b) => (a.datum < b.datum ? -1 : 1));
      this._wd = new Set(wd.map(dd));
      this._svErr = null;
    } catch (e) { this._svErr = `Načítanie sviatkov zlyhalo: ${e.message || e.body || e}`; }
    this._key = ''; this._render();
  }

  _renderSviatky(css) {
    const today = localISO(new Date());
    let rows = '';
    (this._sv || []).forEach((h) => {
      const d = new Date(`${h.datum}T12:00:00`); const wd = (d.getDay() + 6) % 7;
      const vikend = wd >= 5; const aktivny = !this._wd.has(h.datum);
      const busy = this._svBusy === h.datum;
      rows += `<div class="hrow ${h.datum < today ? 'past' : ''} ${h.datum === today ? 'htoday' : ''}">
        <span class="hd">${DNI[wd]} ${dDM(h.datum)}</span>
        <span class="hn" title="${esc(h.nazov)}">${esc(h.nazov)}</span>
        ${vikend ? '<span class="hv mut">víkend</span>'
          : `<button class="sw ${aktivny ? 'on' : ''}" data-act="sv" data-d="${h.datum}" data-on="${aktivny ? 1 : 0}" ${busy ? 'disabled' : ''}
               title="${aktivny ? 'Sviatok platí — klik = správať sa ako pracovný deň' : 'Pracovný deň — klik = správať sa ako sviatok'}">
               <i></i><span>${busy ? '…' : aktivny ? 'aktívny' : 'neaktívny'}</span></button>`}
      </div>`;
    });
    this.shadowRoot.innerHTML = `${css}<ha-card><div class="pad">
      <div class="head"><div class="title">Sviatky ${this._rok}</div>
        <span><button class="ic" data-act="rok" data-k="-1" title="predchádzajúci rok">‹</button><button class="ic" data-act="rok" data-k="1" title="ďalší rok">›</button></span></div>
      <div class="mut small" style="margin:-4px 0 8px">Aktívny = deň sa správa ako sviatok (profil Sviatok, TUV sa neblokuje).
        Neaktívny = bežný pracovný deň. Cez víkend platí vždy víkend.</div>
      ${this._svErr ? `<div class="err">${esc(this._svErr)}</div>` : ''}
      ${this._sv ? rows || '<div class="mut">Žiadne sviatky.</div>' : '<div class="mut">Načítavam…</div>'}
    </div></ha-card>`;
  }

  async _toggleSviatok(datum, bolAktivny) {
    this._svBusy = datum; this._svErr = null; this._key = ''; this._render();
    try {
      const entries = await this._hass.callWS({ type: 'config_entries/get', domain: 'workday' });
      if (!entries.length) throw new Error('integrácia Workday sa nenašla');
      const f = await this._hass.callApi('POST', 'config/config_entries/options/flow', { handler: entries[0].entry_id });
      const cur = {};
      (f.data_schema || []).forEach((s) => {
        const sv = s.description && s.description.suggested_value;
        const v = sv !== undefined ? sv : s.default;
        if (v !== undefined && v !== null) cur[s.name] = v;
      });
      const add = new Set(cur.add_holidays || []); const rem = new Set(cur.remove_holidays || []);
      if (bolAktivny) { if (add.has(datum)) add.delete(datum); else rem.add(datum); }
      else { if (rem.has(datum)) rem.delete(datum); else add.add(datum); }
      cur.add_holidays = [...add].sort(); cur.remove_holidays = [...rem].sort();
      const r = await this._hass.callApi('POST', `config/config_entries/options/flow/${f.flow_id}`, cur);
      if (r.type !== 'create_entry') throw new Error((r.errors && JSON.stringify(r.errors)) || r.type);
      await new Promise((res) => setTimeout(res, 2500));
      try { await this._hass.callWS({ type: 'fire_event', event_type: 'plan_kurenia_refresh' }); } catch (e) { /* nevadí */ }
    } catch (e) {
      this._svErr = `Zmena zlyhala: ${e.message || e.body || e.error || e}`;
    }
    this._svBusy = null; this._svLoaded = null; this._loadSviatky();
  }

  // ---------------------------------------------------------------- styles
  _css() {
    return `<style>
      :host { --pk-n: #e8833a; --pk-u: rgba(79,143,214,.22); --pk-s: #f2c200; --pk-h: #9b59d0; --pk-d: #8a8a8a; }
      .pad { padding: 16px; }
      .head { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:8px; }
      .title { font-size: 1.25em; font-weight: 500; }
      .chip { border:1px solid var(--divider-color); border-radius:16px; padding:4px 12px; background:none;
              color: var(--secondary-text-color); cursor:pointer; font: inherit; }
      .chip.on { color: var(--pk-n); border-color: var(--pk-n); }
      .status { display:flex; flex-wrap:wrap; gap:4px 24px; margin-bottom:12px; }
      .mut { color: var(--secondary-text-color); }
      .small { font-size: .85em; margin-top: 4px; }
      .tn { color: var(--pk-n); } .tu { color: #4f8fd6; }
      .ranges { margin: -4px 0 10px; display:flex; gap:6px; flex-wrap:wrap; }
      .grid { display:grid; grid-template-columns: minmax(84px, 140px) 1fr; column-gap: 10px; row-gap: 6px; align-items:center; }
      .grid.compact { grid-template-columns: minmax(60px, 100px) 1fr; }
      .lbl { cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding: 2px 4px; border-radius: 6px; }
      .lbl.hint { cursor:default; font-size:.75em; color: var(--secondary-text-color); white-space:normal; }
      .lbl .dn { font-weight: 500; } .lbl .dt { color: var(--secondary-text-color); font-size:.85em; }
      .lbl.today { color: var(--primary-color); } .lbl.today .dt { color: var(--primary-color); }
      .lbl.sel, .cell.sel { background: rgba(127,127,127,.12); }
      .lbl.sv, .cell.sv { margin-top: 8px; }
      .cell { cursor:pointer; padding: 2px 4px; border-radius: 6px; min-width: 0; }
      .grid.compact .cell, .grid.compact .lbl { cursor: default; }
      .axis { position:relative; height: 16px; margin: 0 4px; }
      .tick { position:absolute; top: 10px; width:1px; height:6px; background: var(--divider-color); }
      .tick.maj { top: 6px; height: 10px; }
      .tick span { position:absolute; top:-8px; transform: translateX(-50%); font-size: .7em; color: var(--secondary-text-color); }
      @media (max-width: 600px) { .tick.maj:not(.six) span { display:none; } }
      .bar { position:relative; background: var(--pk-u); border-radius: 4px; overflow:hidden; }
      .bar.dim { opacity: .45; }
      .blk { position:absolute; top:0; bottom:0; background: var(--pk-n); border-radius: 3px; display:flex; align-items:center; justify-content:center; overflow:hidden; }
      .blk span { font-size: .7em; color: #fff; white-space:nowrap; text-shadow: 0 0 2px rgba(0,0,0,.4); }
      .dov { position:absolute; inset:0; background: repeating-linear-gradient(45deg, var(--pk-d) 0 4px, transparent 4px 9px); opacity:.6; }
      .now { position:absolute; top:-2px; bottom:-2px; width:2px; background: var(--primary-text-color); box-shadow: 0 0 0 1px var(--card-background-color, #fff); }
      .eff { margin-top: 3px; } .eff span { font-size: .7em; color: var(--secondary-text-color); }
      .strip { position:relative; height: 5px; margin-top: 3px; }
      .strip .s, .strip .h { position:absolute; height: 2px; border-radius: 1px; }
      .strip .s { top: 0; background: var(--pk-s); } .strip .h { top: 3px; background: var(--pk-h); }
      .tag { font-size: .7em; padding: 1px 6px; border-radius: 8px; background: rgba(242,194,0,.25); margin-left: 4px; color: var(--primary-text-color); }
      .tag.td { background: rgba(138,138,138,.3); }
      .legend { display:flex; flex-wrap:wrap; gap: 4px 16px; margin-top: 12px; font-size: .8em; color: var(--secondary-text-color); }
      .lg { display:inline-block; width: 14px; height: 8px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
      .lg.n { background: var(--pk-n); } .lg.u { background: var(--pk-u); border:1px solid rgba(79,143,214,.5); }
      .lg.s { background: var(--pk-s); height: 3px; } .lg.h { background: var(--pk-h); height: 3px; }
      .lg.d { background: repeating-linear-gradient(45deg, var(--pk-d) 0 3px, transparent 3px 6px); }
      .editor { margin-top: 16px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px; display:flex; flex-direction:column; gap: 8px; }
      .etitle { font-size: 1.05em; }
      .brow { display:flex; align-items:center; gap: 8px; flex-wrap: wrap; }
      .brow input { font: inherit; padding: 4px 6px; border-radius: 6px; border: 1px solid var(--divider-color);
                    background: var(--card-background-color); color: var(--primary-text-color); color-scheme: light dark; }
      .ebtns { display:flex; gap: 8px; flex-wrap: wrap; align-items:center; }
      .ebtns .sp { flex: 1; }
      .btn { font: inherit; border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color);
             border-radius: 6px; padding: 6px 12px; cursor:pointer; }
      .btn.pri { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
      .btn.wide { width: 100%; margin-top: 12px; }
      .btn:disabled { opacity: .6; cursor: default; }
      .ic { font: inherit; border: none; background: none; color: var(--secondary-text-color); cursor:pointer; padding: 4px 8px; }
      .err { color: var(--error-color, #db4437); }
      .hrow { display:grid; grid-template-columns: 62px 1fr auto; gap: 8px; align-items:center; padding: 5px 2px; border-bottom: 1px solid var(--divider-color); }
      .hrow:last-child { border-bottom: none; }
      .hrow.past { opacity: .5; } .hrow.htoday .hd { color: var(--primary-color); font-weight: 500; }
      .hd { white-space:nowrap; font-size: .9em; } .hn { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .hv { font-size: .8em; padding-right: 6px; }
      .sw { display:flex; align-items:center; gap:6px; font: inherit; font-size: .8em; border:none; background:none; cursor:pointer;
            color: var(--secondary-text-color); padding: 2px 0; min-width: 92px; justify-content: flex-end; }
      .sw i { position:relative; width: 30px; height: 16px; border-radius: 8px; background: var(--divider-color); transition: background .2s; flex: none; }
      .sw i::after { content:''; position:absolute; top:2px; left:2px; width:12px; height:12px; border-radius:50%; background:#fff; transition: left .2s; }
      .sw.on { color: var(--pk-n); } .sw.on i { background: var(--pk-n); } .sw.on i::after { left: 16px; }
      .sw:disabled { opacity: .6; cursor: default; }
    </style>`;
  }
}

if (!customElements.get('plan-kurenia-card')) customElements.define('plan-kurenia-card', PlanKureniaCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: 'plan-kurenia-card', name: 'Plán kúrenia', description: 'Týždenný plán kúrenia Daikin (normál/útlm)' });
