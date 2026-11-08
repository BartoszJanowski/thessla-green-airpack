/*
 * Thessla Green AirPack4 – flow diagram card for Home Assistant.
 *
 * Served and auto-registered by the thessla_green_airpack integration.
 *   type: custom:thessla-airpack-card
 *   device_id: <optional, defaults to the first AirPack>
 *   title: <optional>
 *
 * Entities are resolved by device + translation key, so renaming entity IDs
 * does not break the card. Anything the device does not have is hidden.
 */

const CARD_VERSION = "0.1.6";
const DOMAIN = "thessla_green_airpack";

const I18N = {
  en: {
    intake: "INTAKE", extract: "EXTRACT", supply: "SUPPLY", exhaust: "EXHAUST",
    bypass: "BYPASS", off: "Off", auto: "Auto", manual: "Manual", temporary: "Temporary",
    summer: "Summer", winter: "Winter", eco: "ECO", comfort: "COMFORT", alarms: "alarm(s)",
    efficiency: "Efficiency", no_device: "No Thessla Green AirPack4 found.",
    functions: {
      hood: "Hood", fireplace: "Fireplace", airing_bell_switch: "Airing", airing_switch: "Airing",
      airing_hygrostat: "Airing (H2O)", airing_air_quality: "Airing (air quality)", airing_manual: "Airing",
      airing_auto_schedule: "Airing", airing_manual_schedule: "Airing", open_windows: "Open windows",
      empty_house: "Empty house",
    },
  },
  pl: {
    intake: "CZERPNIA", extract: "WYWIEW", supply: "NAWIEW", exhaust: "WYRZUTNIA",
    bypass: "BYPASS", off: "Wyłączona", auto: "Automatyczny", manual: "Manualny", temporary: "Chwilowy",
    summer: "Lato", winter: "Zima", eco: "EKO", comfort: "KOMFORT", alarms: "alarm(y)",
    efficiency: "Sprawność", no_device: "Nie znaleziono centrali Thessla Green AirPack4.",
    functions: {
      hood: "Okap", fireplace: "Kominek", airing_bell_switch: "Wietrzenie", airing_switch: "Wietrzenie",
      airing_hygrostat: "Wietrzenie (H2O)", airing_air_quality: "Wietrzenie (JP)", airing_manual: "Wietrzenie",
      airing_auto_schedule: "Wietrzenie", airing_manual_schedule: "Wietrzenie", open_windows: "Otwarte okna",
      empty_house: "Pusty dom",
    },
  },
};

// role -> "domain.translation_key"
const ROLES = {
  tOutside: "sensor.outside_temperature",
  tSupply: "sensor.supply_temperature",
  tExtract: "sensor.exhaust_temperature",
  tFpx: "sensor.fpx_temperature",
  tDuct: "sensor.duct_supply_temperature",
  tGwc: "sensor.gwc_temperature",
  tAmbient: "sensor.ambient_temperature",
  flowSupply: "sensor.supply_air_flow",
  flowExhaust: "sensor.exhaust_air_flow",
  pctSupply: "sensor.supply_percentage",
  pctExhaust: "sensor.exhaust_percentage",
  filterSupply: "sensor.supply_filter_wear",
  filterExhaust: "sensor.exhaust_filter_wear",
  efficiency: "sensor.heat_recovery_efficiency",
  func: "sensor.active_function",
  bypassState: "sensor.bypass_state",
  gwcState: "sensor.gwc_state",
  comfortState: "sensor.comfort_state",
  alarms: "sensor.active_alarms",
  bypass: "binary_sensor.bypass_actuator",
  fpx: "binary_sensor.antifreeze_mode",
  alarm: "binary_sensor.alarm",
  error: "binary_sensor.error",
  fansPower: "binary_sensor.power_supply_fans",
  gwcRelay: "binary_sensor.gwc_relay",
  fan: "fan.ventilation",
  power: "switch.power",
  season: "select.season_mode",
  comfort: "select.comfort_mode_panel",
};

const COLD = [59, 130, 246]; // blue
const WARM = [245, 158, 11]; // amber

function tempColor(t) {
  if (t === null || Number.isNaN(t)) return "var(--secondary-text-color)";
  const k = Math.max(0, Math.min(1, (t - 0) / 22));
  const c = COLD.map((v, i) => Math.round(v + (WARM[i] - v) * k));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

const SVG = `
<svg viewBox="0 0 900 470" role="img" preserveAspectRatio="xMidYMid meet">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="context-stroke"></path>
    </marker>
  </defs>

  <!-- labels -->
  <text class="lbl" x="20" y="62" id="lblIntake"></text>
  <text class="lbl" x="880" y="62" text-anchor="end" id="lblExtract"></text>
  <text class="lbl" x="20" y="455" id="lblExhaust"></text>
  <text class="lbl" x="880" y="455" text-anchor="end" id="lblSupply"></text>

  <!-- bypass path (drawn first, under everything) -->
  <path id="pBypass" class="duct bypass" d="M 345 120 V 440 H 610 V 400"></path>

  <!-- air paths -->
  <path id="pIntake" class="duct" d="M 20 120 H 345 L 382 221" marker-end="url(#arrow)"></path>
  <path id="pExtract" class="duct" d="M 880 120 H 555 L 518 221" marker-end="url(#arrow)"></path>
  <path id="pSupplyOut" class="duct" d="M 518 299 L 570 400 H 880" marker-end="url(#arrow)"></path>
  <path id="pExhaustOut" class="duct" d="M 382 299 L 330 400 H 20" marker-end="url(#arrow)"></path>

  <!-- heat exchanger -->
  <g id="hx" class="clickable">
    <polygon id="hxPoly" points="360,260 405,182 495,182 540,260 495,338 405,338"></polygon>
    <text id="hxLabel" class="big" x="450" y="256" text-anchor="middle"></text>
    <text id="hxSub" class="small" x="450" y="282" text-anchor="middle"></text>
  </g>

  <!-- temperatures -->
  <text id="tOutside" class="temp clickable" x="20" y="95"></text>
  <text id="tExtract" class="temp clickable" x="880" y="95" text-anchor="end"></text>
  <text id="tSupply" class="temp clickable" x="880" y="430" text-anchor="end"></text>
  <!-- register 0x16 (TO): Air++ shows it on the exhaust side, before WYRZUTNIA -->
  <text id="tAmbient" class="temp clickable" x="175" y="388" text-anchor="middle"></text>

  <!-- GWC -->
  <g id="gGwc" class="comp clickable">
    <rect x="58" y="104" width="50" height="32" rx="6"></rect>
    <text x="83" y="125" text-anchor="middle" class="tag">GWC</text>
    <text id="tGwc" x="83" y="160" text-anchor="middle" class="small"></text>
  </g>

  <!-- supply filter -->
  <g id="gFilterSupply" class="clickable">
    <path class="filter" d="M 150 96 l 12 8 l -12 8 l 12 8 l -12 8 l 12 8 l -12 8"></path>
    <text id="filterSupply" x="156" y="170" text-anchor="middle" class="small"></text>
  </g>

  <!-- FPX -->
  <g id="gFpx" class="comp clickable">
    <rect x="196" y="106" width="44" height="28" rx="6"></rect>
    <text x="218" y="125" text-anchor="middle" class="tag">FPX</text>
    <text id="tFpx" x="218" y="160" text-anchor="middle" class="small"></text>
  </g>

  <!-- supply fan -->
  <g id="gFanSupply" class="clickable">
    <circle class="fanring" cx="290" cy="120" r="27"></circle>
    <g class="blades" id="bladesSupply">
      <path d="M290 120 Q 282 100 290 96 Q 298 100 290 120 Z"></path>
      <path d="M290 120 Q 282 100 290 96 Q 298 100 290 120 Z" transform="rotate(120 290 120)"></path>
      <path d="M290 120 Q 282 100 290 96 Q 298 100 290 120 Z" transform="rotate(240 290 120)"></path>
    </g>
    <text id="pctSupply" x="290" y="172" text-anchor="middle" class="mid"></text>
    <text id="flowSupply" x="290" y="192" text-anchor="middle" class="small"></text>
  </g>

  <!-- exhaust fan -->
  <g id="gFanExhaust" class="clickable">
    <circle class="fanring" cx="640" cy="120" r="27"></circle>
    <g class="blades" id="bladesExhaust">
      <path d="M640 120 Q 632 100 640 96 Q 648 100 640 120 Z"></path>
      <path d="M640 120 Q 632 100 640 96 Q 648 100 640 120 Z" transform="rotate(120 640 120)"></path>
      <path d="M640 120 Q 632 100 640 96 Q 648 100 640 120 Z" transform="rotate(240 640 120)"></path>
    </g>
    <text id="pctExhaust" x="640" y="172" text-anchor="middle" class="mid"></text>
    <text id="flowExhaust" x="640" y="192" text-anchor="middle" class="small"></text>
  </g>

  <!-- exhaust filter -->
  <g id="gFilterExhaust" class="clickable">
    <path class="filter" d="M 750 96 l 12 8 l -12 8 l 12 8 l -12 8 l 12 8 l -12 8"></path>
    <text id="filterExhaust" x="756" y="170" text-anchor="middle" class="small"></text>
  </g>

  <!-- duct heater / cooler -->
  <g id="gDuct" class="comp clickable">
    <rect x="700" y="384" width="56" height="32" rx="6"></rect>
    <text id="ductTag" x="728" y="405" text-anchor="middle" class="tag"></text>
    <text id="tDuct" x="728" y="375" text-anchor="middle" class="small"></text>
  </g>
</svg>`;

const STYLE = `
  :host { display: block; }
  ha-card { padding: 12px 12px 4px; overflow: hidden; }
  .header { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; margin: 0 4px 4px; }
  .title { font-size: 1.15em; font-weight: 500; margin-right: auto; color: var(--primary-text-color); }
  .chip { font-size: 0.8em; padding: 3px 10px; border-radius: 12px; cursor: pointer;
          background: var(--secondary-background-color, rgba(127,127,127,.15)); color: var(--primary-text-color);
          white-space: nowrap; }
  .chip.alarm { background: var(--error-color, #db4437); color: #fff; }
  .chip.accent { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .chip[hidden] { display: none; }
  svg { width: 100%; height: auto; display: block; }
  text { fill: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, inherit); }
  .lbl { font-size: 18px; letter-spacing: .06em; fill: var(--secondary-text-color); }
  .temp { font-size: 22px; }
  .mid { font-size: 21px; }
  .small { font-size: 17px; fill: var(--secondary-text-color); }
  .big { font-size: 26px; font-weight: 500; }
  .tag { font-size: 13px; font-weight: 600; }
  .duct { fill: none; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; transition: opacity .6s, stroke .6s; }
  .duct.flow { stroke-dasharray: 10 8; animation: tg-flow linear infinite; }
  .duct.dim { opacity: .18; }
  .bypass { opacity: .18; stroke: var(--secondary-text-color); }
  #hxPoly { fill: rgba(20,184,166,.07); stroke: #14b8a6; stroke-width: 5; transition: opacity .6s; }
  #hx.dim #hxPoly { opacity: .25; }
  .fanring { fill: none; stroke: var(--secondary-text-color); stroke-width: 3; }
  .blades path { fill: var(--secondary-text-color); }
  .blades { transform-box: fill-box; transform-origin: center; }
  .blades.spin { animation: tg-spin linear infinite; }
  .filter { fill: none; stroke: var(--secondary-text-color); stroke-width: 2.5; stroke-linejoin: round; }
  .comp rect { fill: none; stroke: var(--secondary-text-color); stroke-width: 2; opacity: .5; transition: all .4s; }
  .comp .tag { fill: var(--secondary-text-color); opacity: .6; }
  .comp.on rect { stroke: var(--warning-color, #f59e0b); fill: rgba(245,158,11,.15); opacity: 1; }
  .comp.on .tag { fill: var(--warning-color, #f59e0b); opacity: 1; }
  .comp.cool.on rect { stroke: #3b82f6; fill: rgba(59,130,246,.15); }
  .comp.cool.on .tag { fill: #3b82f6; }
  .warn { fill: var(--warning-color, #f59e0b) !important; }
  .crit { fill: var(--error-color, #db4437) !important; }
  .clickable { cursor: pointer; }
  [hidden] { display: none; }
  .empty { padding: 16px; color: var(--secondary-text-color); }
  @keyframes tg-flow { to { stroke-dashoffset: -36; } }
  @keyframes tg-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    .duct.flow, .blades.spin { animation: none; }
  }
`;

class ThesslaAirPackCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("thessla-airpack-card-editor");
  }

  static getStubConfig(hass) {
    const device = findDevices(hass)[0];
    return device ? { device_id: device } : {};
  }

  setConfig(config) {
    this._config = { ...config };
    this._map = null;
    this._lastKey = null;
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    return 5;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: 5, min_rows: 4 };
  }

  _t() {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").slice(0, 2);
    return I18N[lang] || I18N.en;
  }

  _build() {
    if (this._built) return;
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="header">
          <span class="title" id="title"></span>
          <span class="chip alarm" id="chipAlarm" hidden></span>
          <span class="chip" id="chipMode" hidden></span>
          <span class="chip accent" id="chipFunc" hidden></span>
          <span class="chip" id="chipSeason" hidden></span>
          <span class="chip" id="chipComfort" hidden></span>
        </div>
        <div id="body">${SVG}</div>
        <div class="empty" id="empty" hidden></div>
      </ha-card>`;
    this._el = (id) => this.shadowRoot.getElementById(id);
    this.shadowRoot.addEventListener("click", (ev) => {
      const target = ev.composedPath().find((n) => n.dataset && n.dataset.entity);
      if (target) {
        this.dispatchEvent(new CustomEvent("hass-more-info", {
          detail: { entityId: target.dataset.entity }, bubbles: true, composed: true,
        }));
      }
    });
    this._built = true;
  }

  _resolve() {
    const hass = this._hass;
    const deviceId = this._config.device_id || findDevices(hass)[0];
    const map = {};
    if (deviceId) {
      for (const entry of Object.values(hass.entities || {})) {
        if (entry.device_id !== deviceId || entry.platform !== DOMAIN || !entry.translation_key) continue;
        map[`${entry.entity_id.split(".")[0]}.${entry.translation_key}`] = entry.entity_id;
      }
    }
    this._deviceId = deviceId;
    this._map = {};
    for (const [role, key] of Object.entries(ROLES)) this._map[role] = map[key];
  }

  _update() {
    if (!this._config || !this._hass) return;
    this._build();
    if (!this._map || this._entitiesRef !== this._hass.entities) {
      this._resolve();
      this._entitiesRef = this._hass.entities;
    }
    // Re-render only when one of our entities changed.
    const ids = Object.values(this._map).filter(Boolean);
    const key = ids.map((id) => this._hass.states[id]?.last_updated).join("|") + this._hass.locale?.language;
    if (key === this._lastKey) return;
    this._lastKey = key;
    this._render();
  }

  _st(role) {
    const id = this._map[role];
    return id ? this._hass.states[id] : undefined;
  }

  _num(role) {
    const s = this._st(role);
    if (!s) return null;
    const n = parseFloat(s.state);
    return Number.isNaN(n) ? null : n;
  }

  _on(role) {
    const s = this._st(role);
    return s ? s.state === "on" : null;
  }

  _show(id, visible) {
    this._el(id).toggleAttribute("hidden", !visible);
  }

  _text(id, value, role) {
    const el = this._el(id);
    el.textContent = value;
    if (role && this._map[role]) el.dataset.entity = this._map[role];
  }

  _render() {
    const t = this._t();
    const $ = this._el;
    const hasDevice = Boolean(this._deviceId) && Object.values(this._map).some(Boolean);
    this._show("body", hasDevice);
    this._show("empty", !hasDevice);
    $("empty").textContent = t.no_device;
    if (!hasDevice) return;

    const fmtT = (role) => {
      const v = this._num(role);
      return v === null ? "—" : `${v.toFixed(1)} °C`;
    };
    const fmtPct = (v) => (v === null ? "—" : `${Math.round(v)} %`);

    // Header
    const deviceName = this._hass.devices?.[this._deviceId]?.name_by_user || this._hass.devices?.[this._deviceId]?.name;
    $("title").textContent = this._config.title ?? deviceName ?? "AirPack";

    const powerOn = this._on("power") !== false;
    const fansOn = this._on("fansPower") !== false;
    const running = powerOn && fansOn;
    const fan = this._st("fan");
    const preset = fan?.attributes?.preset_mode;
    this._show("chipMode", Boolean(fan));
    this._text("chipMode", running ? (t[preset] || preset || "—") : t.off, "fan");
    if (!running) $("chipMode").dataset.entity = this._map.power || this._map.fan;

    const func = this._st("func")?.state;
    const funcActive = func && !["none", "unknown", "unavailable"].includes(func);
    this._show("chipFunc", Boolean(funcActive));
    if (funcActive) this._text("chipFunc", t.functions[func] || func, "func");

    const season = this._st("season")?.state;
    this._show("chipSeason", season === "summer" || season === "winter");
    if (season) this._text("chipSeason", season === "summer" ? `☀ ${t.summer}` : `❄ ${t.winter}`, "season");

    const comfort = this._st("comfort")?.state;
    this._show("chipComfort", comfort === "eco" || comfort === "comfort");
    if (comfort) this._text("chipComfort", t[comfort] || comfort, "comfort");

    const eff = this._num("efficiency");

    const alarmCount = this._num("alarms") || 0;
    const anyAlarm = this._on("alarm") || this._on("error") || alarmCount > 0;
    this._show("chipAlarm", Boolean(anyAlarm));
    if (anyAlarm) {
      this._text("chipAlarm", `⚠ ${alarmCount || ""} ${t.alarms}`.replace("  ", " "), this._map.alarms ? "alarms" : "error");
    }

    // Labels
    $("lblIntake").textContent = t.intake;
    $("lblExtract").textContent = t.extract;
    $("lblSupply").textContent = t.supply;
    $("lblExhaust").textContent = t.exhaust;

    // Temperatures
    this._text("tOutside", fmtT("tOutside"), "tOutside");
    this._text("tExtract", fmtT("tExtract"), "tExtract");
    this._text("tSupply", fmtT("tSupply"), "tSupply");
    this._show("tAmbient", Boolean(this._map.tAmbient));
    this._text("tAmbient", fmtT("tAmbient"), "tAmbient");

    // Fans
    const fanPct = fan?.attributes?.percentage ?? null;
    const pctS = this._num("pctSupply") ?? fanPct;
    const pctE = this._num("pctExhaust") ?? pctS;
    this._text("pctSupply", running ? fmtPct(pctS) : t.off, "pctSupply");
    this._text("pctExhaust", running ? fmtPct(pctE) : t.off, "pctExhaust");
    $("gFanSupply").dataset.entity = this._map.fan || this._map.pctSupply || "";
    $("gFanExhaust").dataset.entity = this._map.fan || this._map.pctExhaust || "";
    const flowS = this._num("flowSupply");
    const flowE = this._num("flowExhaust");
    this._show("flowSupply", Boolean(this._map.flowSupply));
    this._show("flowExhaust", Boolean(this._map.flowExhaust));
    this._text("flowSupply", flowS === null ? "—" : `${Math.round(flowS)} m³/h`, "flowSupply");
    this._text("flowExhaust", flowE === null ? "—" : `${Math.round(flowE)} m³/h`, "flowExhaust");
    this._spin("bladesSupply", running ? pctS : 0);
    this._spin("bladesExhaust", running ? pctE : 0);

    // Filters
    for (const [role, id, group] of [["filterSupply", "filterSupply", "gFilterSupply"], ["filterExhaust", "filterExhaust", "gFilterExhaust"]]) {
      const v = this._num(role);
      this._show(group, Boolean(this._map[role]));
      this._text(id, fmtPct(v), role);
      $(group).dataset.entity = this._map[role] || "";
      $(id).classList.toggle("warn", v !== null && v >= 80 && v < 100);
      $(id).classList.toggle("crit", v !== null && v >= 100);
    }

    // FPX
    const hasFpx = Boolean(this._map.fpx || this._map.tFpx);
    this._show("gFpx", hasFpx);
    $("gFpx").classList.toggle("on", Boolean(this._on("fpx")));
    $("gFpx").dataset.entity = this._map.fpx || this._map.tFpx || "";
    this._text("tFpx", this._map.tFpx ? fmtT("tFpx") : "");

    // GWC (only when the hardware was detected -> its entities are enabled)
    const hasGwc = Boolean(this._map.tGwc || this._map.gwcState);
    this._show("gGwc", hasGwc);
    const gwcState = this._st("gwcState")?.state;
    $("gGwc").classList.toggle("on", Boolean(this._on("gwcRelay")) || (gwcState && !["inactive", "unknown", "unavailable"].includes(gwcState)));
    $("gGwc").dataset.entity = this._map.tGwc || this._map.gwcState || "";
    this._text("tGwc", this._map.tGwc ? fmtT("tGwc") : "");

    // Duct heater / cooler (COMFORT)
    const hasDuct = Boolean(this._map.tDuct);
    this._show("gDuct", hasDuct);
    const comfortState = this._st("comfortState")?.state;
    $("gDuct").classList.toggle("on", comfortState === "heating" || comfortState === "cooling");
    $("gDuct").classList.toggle("cool", comfortState === "cooling");
    $("ductTag").textContent = comfortState === "cooling" ? "❄" : "♨";
    $("gDuct").dataset.entity = this._map.comfortState || this._map.tDuct || "";
    this._text("tDuct", fmtT("tDuct"), "tDuct");

    // Bypass + air paths
    const bypassState = this._st("bypassState")?.state;
    const bypassOpen = this._on("bypass") ?? (bypassState ? !["inactive", "unknown", "unavailable"].includes(bypassState) : false);
    const cOut = tempColor(this._num("tOutside"));
    const cExt = tempColor(this._num("tExtract"));
    const cSup = tempColor(this._num("tSupply"));
    const cExh = tempColor(mix(this._num("tOutside"), this._num("tExtract")));

    this._duct("pIntake", cOut, running ? pctS : 0, bypassOpen);
    this._duct("pExtract", cExt, running ? pctE : 0, false);
    this._duct("pSupplyOut", cSup, running ? pctS : 0, false);
    this._duct("pExhaustOut", cExh, running ? pctE : 0, false);
    const bp = $("pBypass");
    bp.style.stroke = bypassOpen ? cOut : "";
    bp.style.opacity = bypassOpen ? "1" : "";
    this._animate(bp, bypassOpen && running ? pctS : 0);
    bp.dataset.entity = this._map.bypass || this._map.bypassState || "";
    if (bypassOpen) {
      // Supply air skips the exchanger: show the first part of the intake normally.
      $("pIntake").classList.remove("dim");
      $("pIntake").setAttribute("d", "M 20 120 H 345");
      $("pIntake").removeAttribute("marker-end");
    } else {
      $("pIntake").setAttribute("d", "M 20 120 H 345 L 382 221");
      $("pIntake").setAttribute("marker-end", "url(#arrow)");
    }

    $("hx").classList.toggle("dim", bypassOpen);
    $("hx").dataset.entity = this._map.efficiency || this._map.bypassState || "";
    $("hxLabel").textContent = bypassOpen ? t.bypass : eff !== null ? `${Math.round(eff)} %` : "";
    $("hxSub").textContent = !bypassOpen && eff !== null ? t.efficiency : "";
  }

  _duct(id, color, pct, dim) {
    const el = this._el(id);
    el.style.stroke = color;
    el.classList.toggle("dim", dim);
    this._animate(el, dim ? 0 : pct);
  }

  _animate(el, pct) {
    const moving = pct && pct > 0;
    el.classList.toggle("flow", Boolean(moving));
    if (moving) el.style.animationDuration = `${(36 / (8 + pct * 0.9)).toFixed(2)}s`;
  }

  _spin(id, pct) {
    const el = this._el(id);
    const moving = pct && pct > 0;
    el.classList.toggle("spin", Boolean(moving));
    if (moving) el.style.animationDuration = `${(60 / (10 + pct * 1.6)).toFixed(2)}s`;
  }
}

function mix(a, b) {
  if (a === null || b === null) return a ?? b;
  return (a + b) / 2;
}

function findDevices(hass) {
  const devices = new Set();
  for (const entry of Object.values(hass?.entities || {})) {
    if (entry.platform === DOMAIN && entry.device_id) devices.add(entry.device_id);
  }
  return [...devices];
}

class ThesslaAirPackCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => ({ device_id: "AirPack", title: "Title" }[s.name] || s.name);
      this._form.addEventListener("value-changed", (ev) => {
        this._config = { ...this._config, ...ev.detail.value };
        Object.keys(this._config).forEach((k) => this._config[k] === "" && delete this._config[k]);
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      { name: "device_id", selector: { device: { integration: DOMAIN } } },
      { name: "title", selector: { text: {} } },
    ];
  }
}

/*
 * Sidebar panel ("AirPack4", /airpack4): the same diagram full-page, one per
 * AirPack. Registered by the integration; the device page's
 * "Open configuration page" button links here.
 */
class ThesslaAirPackPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  set panel(panel) {
    this._panel = panel;
  }

  set route(route) {
    this._route = route;
  }

  _render() {
    if (!this._hass) return;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; min-height: 100vh; background: var(--primary-background-color); }
          .toolbar { display: flex; align-items: center; gap: 4px; height: var(--header-height, 56px);
                     padding: 0 12px; box-sizing: border-box; color: var(--app-header-text-color, var(--primary-text-color));
                     background: var(--app-header-background-color, var(--primary-background-color));
                     border-bottom: var(--app-header-border-bottom, none); }
          .title { font-size: 20px; font-weight: 400; margin-left: 4px; }
          .content { max-width: 1100px; margin: 0 auto; padding: 16px; display: grid; gap: 16px; }
          .empty { padding: 32px 16px; color: var(--secondary-text-color); text-align: center; }
        </style>
        <div class="toolbar"><ha-menu-button></ha-menu-button><div class="title">AirPack4</div></div>
        <div class="content" id="content"></div>`;
      this._menu = this.shadowRoot.querySelector("ha-menu-button");
      this._content = this.shadowRoot.getElementById("content");
      this._cards = new Map();
    }
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;

    const devices = findDevices(this._hass);
    for (const [id, card] of this._cards) {
      if (!devices.includes(id)) {
        card.remove();
        this._cards.delete(id);
      }
    }
    for (const id of devices) {
      let card = this._cards.get(id);
      if (!card) {
        card = document.createElement("thessla-airpack-card");
        card.setConfig({ device_id: id });
        this._cards.set(id, card);
        this._content.appendChild(card);
      }
      card.hass = this._hass;
    }
    if (!devices.length) {
      const lang = (this._hass.locale?.language || this._hass.language || "en").slice(0, 2);
      this._content.innerHTML = `<div class="empty">${(I18N[lang] || I18N.en).no_device}</div>`;
    } else {
      this._content.querySelector(".empty")?.remove();
    }
  }
}

if (!customElements.get("thessla-airpack-panel")) {
  customElements.define("thessla-airpack-panel", ThesslaAirPackPanel);
}

if (!customElements.get("thessla-airpack-card")) {
  customElements.define("thessla-airpack-card", ThesslaAirPackCard);
  customElements.define("thessla-airpack-card-editor", ThesslaAirPackCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "thessla-airpack-card",
    name: "Thessla Green AirPack4",
    description: "Live air-flow diagram of the AirPack recuperator.",
    preview: true,
    documentationURL: "https://github.com/BartoszJanowski/thessla-green-airpack",
  });
  console.info(`%c THESSLA-AIRPACK-CARD %c ${CARD_VERSION} `, "background:#14b8a6;color:#fff", "");
}
