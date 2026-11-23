/* Mockup kit: mutable-gui.
   Draws the 15 element kinds from theme roles (CSS custom properties --role-*), the tool
   icons, and the reference plugin's default layout, so every mockup shows the same things.
   A picture of intent: the product draws these with egui's painter. No network access. */
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const r = (n) => Math.round(n * 100) / 100;
  const pt = (cx, cy, rad, deg) => {
    const a = (deg * Math.PI) / 180;
    return [r(cx + rad * Math.cos(a)), r(cy + rad * Math.sin(a))];
  };
  const arc = (cx, cy, rad, a0, a1) => {
    if (a1 - a0 < 0.01) return "";
    const [x0, y0] = pt(cx, cy, rad, a0);
    const [x1, y1] = pt(cx, cy, rad, a1);
    return `M${x0} ${y0} A${rad} ${rad} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1}`;
  };
  const role = (name) => `var(--role-${name})`;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

  /* ---------- icons (stand-ins for Material Symbols Rounded) ---------- */
  const ICONS = {
    menu: '<circle cx="6" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="18" cy="12" r="1.8"/>',
    undo: '<path d="M9 7 4 12l5 5" fill="none"/><path d="M4 12h10a5 5 0 0 1 0 10h-3" fill="none"/>',
    redo: '<path d="m15 7 5 5-5 5" fill="none"/><path d="M20 12H10a5 5 0 0 0 0 10h3" fill="none"/>',
    alignL: '<path d="M4 3v18" fill="none"/><rect x="7" y="6" width="12" height="4" rx="1"/><rect x="7" y="14" width="7" height="4" rx="1"/>',
    alignCH: '<path d="M12 3v18" fill="none"/><rect x="5" y="6" width="14" height="4" rx="1"/><rect x="8" y="14" width="8" height="4" rx="1"/>',
    alignR: '<path d="M20 3v18" fill="none"/><rect x="5" y="6" width="12" height="4" rx="1"/><rect x="10" y="14" width="7" height="4" rx="1"/>',
    alignT: '<path d="M3 4h18" fill="none"/><rect x="6" y="7" width="4" height="12" rx="1"/><rect x="14" y="7" width="4" height="7" rx="1"/>',
    alignCV: '<path d="M3 12h18" fill="none"/><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="8" width="4" height="8" rx="1"/>',
    alignB: '<path d="M3 20h18" fill="none"/><rect x="6" y="5" width="4" height="12" rx="1"/><rect x="14" y="10" width="4" height="7" rx="1"/>',
    distH: '<path d="M3 4v16M21 4v16" fill="none"/><rect x="9" y="7" width="6" height="10" rx="1"/>',
    distV: '<path d="M4 3h16M4 21h16" fill="none"/><rect x="7" y="9" width="10" height="6" rx="1"/>',
    group: '<rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke-dasharray="3 2"/><rect x="7" y="7" width="5" height="5" rx="1"/><rect x="13" y="12" width="5" height="5" rx="1"/>',
    ungroup: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    front: '<rect x="3" y="3" width="11" height="11" rx="1" fill="none"/><rect x="9" y="9" width="12" height="12" rx="1"/>',
    back: '<rect x="9" y="9" width="12" height="12" rx="1" fill="none"/><rect x="3" y="3" width="11" height="11" rx="1"/>',
    grid: '<path d="M3 9h18M3 15h18M9 3v18M15 3v18" fill="none"/><rect x="3" y="3" width="18" height="18" rx="2" fill="none"/>',
    snap: '<path d="M6 4v8a6 6 0 0 0 12 0V4" fill="none"/><path d="M6 4h4M14 4h4" fill="none"/>',
    plus: '<path d="M12 5v14M5 12h14" fill="none"/>',
    trash: '<path d="M5 7h14M9 7V4h6v3M7 7l1 13h8l1-13" fill="none"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2" fill="none"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3" fill="none"/>',
    search: '<circle cx="10.5" cy="10.5" r="6" fill="none"/><path d="m15 15 5 5" fill="none"/>',
    warn: '<path d="M12 3 2 20h20Z" fill="none"/><path d="M12 9v5M12 17v.5" fill="none"/>',
    close: '<path d="m6 6 12 12M18 6 6 18" fill="none"/>',
    check: '<path d="m5 12 5 5 9-10" fill="none"/>',
    chevron: '<path d="m7 10 5 5 5-5" fill="none"/>',
    chevronR: '<path d="m10 7 5 5-5 5" fill="none"/>',
    link: '<path d="M10 14a4 4 0 0 0 6 0l3-3a4 4 0 0 0-6-6l-1 1M14 10a4 4 0 0 0-6 0l-3 3a4 4 0 0 0 6 6l1-1" fill="none"/>',
    unlink: '<path d="M10 14a4 4 0 0 0 6 0l3-3a4 4 0 0 0-6-6l-1 1M14 10a4 4 0 0 0-6 0l-3 3a4 4 0 0 0 6 6l1-1M3 3l18 18" fill="none"/>',
    palette: '<path d="M12 3a9 9 0 1 0 0 18c1.5 0 2-1 2-2s-1-1.5-1-2.5S14 15 15 15h2a4 4 0 0 0 4-4c0-4.5-4-8-9-8Z" fill="none"/><circle cx="7.5" cy="11" r="1.3"/><circle cx="10" cy="7" r="1.3"/><circle cx="15" cy="7.5" r="1.3"/>',
    folder: '<path d="M3 6h6l2 2h10v11H3Z" fill="none"/>',
    pages: '<rect x="4" y="3" width="12" height="15" rx="1" fill="none"/><path d="M8 21h11V7" fill="none"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16Z" fill="none"/><path d="m13 7 4 4" fill="none"/>',
    play: '<path d="M7 4v16l13-8Z"/>',
    reset: '<path d="M4 12a8 8 0 1 0 3-6.2" fill="none"/><path d="M4 4v5h5" fill="none"/>',
    upload: '<path d="M12 16V4M7 9l5-5 5 5M4 20h16" fill="none"/>',
    download: '<path d="M12 4v12M7 11l5 5 5-5M4 20h16" fill="none"/>',
    star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9Z" fill="none"/>',
    knob: '<circle cx="12" cy="12" r="8" fill="none"/><path d="M12 12 7 7" fill="none"/>',
    fader: '<path d="M12 3v18" fill="none"/><rect x="8" y="9" width="8" height="5" rx="1"/>',
    switch: '<rect x="3" y="8" width="18" height="9" rx="4.5" fill="none"/><circle cx="16.5" cy="12.5" r="3"/>',
    xy: '<rect x="3" y="3" width="18" height="18" rx="2" fill="none"/><path d="M3 14h18M10 3v18" fill="none" stroke-dasharray="2 2"/><circle cx="10" cy="14" r="2.2"/>',
    macro: '<circle cx="12" cy="12" r="8" fill="none"/><circle cx="12" cy="12" r="4" fill="none"/><path d="M12 12V5" fill="none"/>',
    selector: '<rect x="2" y="8" width="20" height="8" rx="2" fill="none"/><path d="M9 8v8M15 8v8" fill="none"/><rect x="9" y="8" width="6" height="8"/>',
    menuEl: '<rect x="3" y="7" width="18" height="10" rx="2" fill="none"/><path d="m14 11 2 2 2-2" fill="none"/>',
    tabs: '<path d="M3 18h18M4 18V8h6v10M10 18v-8h6v8" fill="none"/>',
    scope: '<rect x="3" y="4" width="18" height="16" rx="2" fill="none"/><path d="M5 12c2-6 4-6 5 0s3 6 5 0 3-6 4 0" fill="none"/>',
    spectrum: '<rect x="3" y="4" width="18" height="16" rx="2" fill="none"/><path d="M5 17c3-1 4-9 6-9s3 5 5 6 3 1 3 1" fill="none"/>',
    meter: '<rect x="6" y="3" width="4" height="18" rx="1" fill="none"/><rect x="14" y="3" width="4" height="18" rx="1" fill="none"/><rect x="6" y="10" width="4" height="11"/><rect x="14" y="13" width="4" height="8"/>',
    gr: '<rect x="9" y="3" width="6" height="18" rx="1" fill="none"/><rect x="9" y="3" width="6" height="7"/>',
    label: '<path d="M5 6h14M12 6v13" fill="none"/>',
    panel: '<rect x="3" y="5" width="18" height="14" rx="3" fill="none"/><path d="M3 9h18" fill="none"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2" fill="none"/><circle cx="9" cy="9.5" r="1.8"/><path d="m4 18 5-5 4 4 3-3 4 4" fill="none"/>',
    keyboard: '<rect x="2" y="6" width="20" height="12" rx="2" fill="none"/><path d="M6 10h1M10 10h1M14 10h1M18 10h0M7 14h10" fill="none"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2" fill="none"/><path d="M8 11V8a4 4 0 0 1 8 0v3" fill="none"/>',
    tune: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8" fill="none"/><circle cx="16" cy="7" r="2" fill="none"/><circle cx="10" cy="17" r="2" fill="none"/>',
    fit: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" fill="none"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" fill="none"/><circle cx="12" cy="12" r="3" fill="none"/>',
    eyeOff: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" fill="none"/><path d="M4 4l16 16" fill="none"/>',
    grip: '<circle cx="9" cy="6" r="1.4"/><circle cx="15" cy="6" r="1.4"/><circle cx="9" cy="12" r="1.4"/><circle cx="15" cy="12" r="1.4"/><circle cx="9" cy="18" r="1.4"/><circle cx="15" cy="18" r="1.4"/>',
    arrowBack: '<path d="m14 6-6 6 6 6" fill="none"/>',
    font: '<path d="M4 20 10 4h1l6 16M6.5 14h8" fill="none"/><path d="M18 9v11" fill="none"/>',
    dock: '<rect x="3" y="4" width="18" height="16" rx="2" fill="none"/><path d="M3 15h18" fill="none"/>',
    curve: '<rect x="3" y="3" width="18" height="18" rx="2" fill="none"/><path d="M5 19C9 19 9 5 19 5" fill="none"/>',
    puzzle: '<path d="M10 3h4v3a2 2 0 1 0 0 4v0h3v4h-3a2 2 0 1 0 0 4v3h-4v-3a2 2 0 1 0-4 0v3H3v-7h3a2 2 0 1 0 0-4H3V3h7Z" fill="none"/>',
  };
  function icon(name, size, extra) {
    const body = ICONS[name] || ICONS.menu;
    return `<svg class="ic ${extra || ""}" width="${size || 16}" height="${size || 16}" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  }

  /* ---------- elements ---------- */
  const CAPTION = 30; // label + value text under knobs
  function stateDecor(e, w, h) {
    let s = "";
    if (e.state === "focused") s += `<rect x="-3" y="-3" width="${w + 6}" height="${h + 6}" rx="6" fill="none" stroke="${role("focus")}" stroke-width="2"/>`;
    if (e.state === "unbound") s += `<rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" rx="5" fill="none" stroke="${role("disabled")}" stroke-dasharray="4 3"/>`;
    return s;
  }
  function caption(e, w, h, valueText) {
    const unbound = e.state === "unbound";
    const label = e.label || "";
    const value = unbound ? (e.missing || "gone") : valueText;
    return `<text x="${w / 2}" y="${h - 17}" text-anchor="middle" fill="${role(unbound ? "text-muted" : "text")}" font-family="${role("font-body")}" font-size="11" font-weight="500">${esc(label)}</text>` +
      (value != null ? `<text x="${w / 2}" y="${h - 3}" text-anchor="middle" fill="${role("text-muted")}" font-family="${role("font-value")}" font-size="10.5">${esc(value)}</text>` : "");
  }
  function bubble(e, x, y, text) {
    if (e.state !== "dragging") return "";
    const tw = text.length * 6.6 + 14;
    return `<g><rect x="${r(x - tw / 2)}" y="${y - 22}" width="${r(tw)}" height="18" rx="4" fill="${role("text")}"/><text x="${x}" y="${y - 9}" text-anchor="middle" fill="${role("background")}" font-family="${role("font-value")}" font-size="11">${esc(text)}</text></g>`;
  }

  function knob(e, w, h) {
    const v = e.value ?? 0.5;
    const size = Math.min(w, h - CAPTION);
    const cx = w / 2, cy = size / 2 + 1, rad = size / 2 - 5;
    const unbound = e.state === "unbound" || e.state === "disabled";
    const acc = unbound ? role("disabled") : role(e.accent || "accent-1");
    const track = e.state === "hover" ? role("text-muted") : role("border");
    const style = e.style || "arc";
    const a = 135 + 270 * v;
    const tw = Math.max(3, size / 14);
    let s = "";
    if (style === "arc") {
      s += `<path d="${arc(cx, cy, rad, 135, 405)}" stroke="${track}" stroke-width="${tw}" fill="none" stroke-linecap="round"/>`;
      if (!unbound) s += `<path d="${arc(cx, cy, rad, 135, a)}" stroke="${acc}" stroke-width="${tw}" fill="none" stroke-linecap="round"/>`;
      s += `<circle cx="${cx}" cy="${cy}" r="${rad - tw - 4}" fill="${role("surface-raised")}" stroke="${role("border")}"/>`;
      const [px, py] = pt(cx, cy, rad - tw - 6, a), [qx, qy] = pt(cx, cy, (rad - tw) * 0.35, a);
      s += `<path d="M${qx} ${qy} L${px} ${py}" stroke="${unbound ? role("disabled") : role("text")}" stroke-width="2" stroke-linecap="round"/>`;
    } else if (style === "pointer") {
      s += `<circle cx="${cx}" cy="${cy}" r="${rad}" fill="${role("surface-raised")}" stroke="${track}" stroke-width="1.5"/>`;
      for (let i = 0; i <= 10; i++) { const [x0, y0] = pt(cx, cy, rad + 2, 135 + 27 * i), [x1, y1] = pt(cx, cy, rad + 5, 135 + 27 * i); s += `<path d="M${x0} ${y0}L${x1} ${y1}" stroke="${role("text-muted")}" stroke-width="1"/>`; }
      const [px, py] = pt(cx, cy, rad - 4, a), [qx, qy] = pt(cx, cy, rad * 0.45, a);
      s += `<path d="M${qx} ${qy} L${px} ${py}" stroke="${acc}" stroke-width="3" stroke-linecap="round"/>`;
    } else {
      s += `<circle cx="${cx}" cy="${cy}" r="${rad}" fill="${role("surface-raised")}" stroke="${track}"/>`;
      if (!unbound) { const [x0, y0] = pt(cx, cy, rad, 135), [x1, y1] = pt(cx, cy, rad, a); s += `<path d="M${cx} ${cy} L${x0} ${y0} A${rad} ${rad} 0 ${a - 135 > 180 ? 1 : 0} 1 ${x1} ${y1} Z" fill="${acc}" opacity="0.85"/>`; }
      s += `<circle cx="${cx}" cy="${cy}" r="${rad * 0.42}" fill="${role("surface")}"/>`;
    }
    if (e.mod != null && !unbound) {
      const m = 135 + 270 * e.mod;
      s += `<path d="${arc(cx, cy, rad + tw / 2 + 3, Math.min(a, m), Math.max(a, m))}" stroke="${role("modulation")}" stroke-width="2.5" fill="none" stroke-linecap="round"/>`;
    }
    s += caption(e, w, h, e.text);
    s += bubble(e, cx, 0, e.text || "");
    return s + stateDecor(e, w, h);
  }

  function macro(e, w, h) {
    let s = knob(Object.assign({}, e, { style: "arc", accent: e.accent || "accent-5" }), w, h);
    const size = Math.min(w, h - CAPTION), cx = w / 2, cy = size / 2 + 1;
    const n = e.targets || 3;
    for (let i = 0; i < n; i++) { const [x, y] = pt(cx, cy, size / 2 - 1, 90 + (i - (n - 1) / 2) * 14); s += `<circle cx="${x}" cy="${y}" r="2.2" fill="${role(e.state === "unbound" ? "disabled" : "accent-5")}"/>`; }
    return s;
  }

  function fader(e, w, h) {
    const v = e.value ?? 0.5, vert = (e.orientation || "vertical") === "vertical";
    const unbound = e.state === "unbound" || e.state === "disabled";
    const acc = unbound ? role("disabled") : role(e.accent || "accent-2");
    const tk = 4, hs = 14;
    let s = "";
    if (vert) {
      const top = 4, bot = h - CAPTION - 4, x = w / 2, y = bot - (bot - top) * v;
      s += `<rect x="${x - tk / 2}" y="${top}" width="${tk}" height="${bot - top}" rx="2" fill="${role("border")}"/>`;
      if (!unbound) s += `<rect x="${x - tk / 2}" y="${y}" width="${tk}" height="${bot - y}" rx="2" fill="${acc}"/>`;
      if (e.mod != null && !unbound) { const my = bot - (bot - top) * e.mod; s += `<rect x="${x + 6}" y="${Math.min(y, my)}" width="2.5" height="${Math.abs(my - y)}" rx="1" fill="${role("modulation")}"/>`; }
      s += `<rect x="${x - 13}" y="${y - hs / 2}" width="26" height="${hs}" rx="3" fill="${role("surface-raised")}" stroke="${e.state === "hover" ? role("text-muted") : role("border")}"/><path d="M${x - 7} ${y}h14" stroke="${unbound ? role("disabled") : role("text")}" stroke-width="1.5"/>`;
      s += bubble(e, x, y - hs / 2, e.text || "");
    } else {
      const left = 6, right = w - 6, y = (h - CAPTION) / 2, x = left + (right - left) * v;
      s += `<rect x="${left}" y="${y - tk / 2}" width="${right - left}" height="${tk}" rx="2" fill="${role("border")}"/>`;
      if (!unbound) s += `<rect x="${left}" y="${y - tk / 2}" width="${x - left}" height="${tk}" rx="2" fill="${acc}"/>`;
      s += `<rect x="${x - hs / 2}" y="${y - 11}" width="${hs}" height="22" rx="3" fill="${role("surface-raised")}" stroke="${e.state === "hover" ? role("text-muted") : role("border")}"/>`;
      s += bubble(e, x, y - 11, e.text || "");
    }
    return s + caption(e, w, h, e.text) + stateDecor(e, w, h);
  }

  function toggle(e, w, h) {
    const on = !!e.on, unbound = e.state === "unbound" || e.state === "disabled";
    const tw = 34, th = 18, y = (h - th) / 2;
    const acc = unbound ? role("disabled") : role(e.accent || "accent-4");
    let s = `<rect x="2" y="${y}" width="${tw}" height="${th}" rx="9" fill="${on && !unbound ? acc : role("surface-raised")}" stroke="${on && !unbound ? acc : role("border")}"/>`;
    s += `<circle cx="${on ? 2 + tw - 9 : 11}" cy="${y + 9}" r="6.5" fill="${unbound ? role("disabled") : on ? role("background") : role("text-muted")}"/>`;
    const lab = e.state === "unbound" ? `⛓ ${e.missing || "gone"}` : e.label;
    s += `<text x="${tw + 10}" y="${h / 2 + 4}" fill="${role(unbound ? "text-muted" : "text")}" font-family="${role("font-body")}" font-size="11.5" font-weight="500">${esc(lab)}</text>`;
    return s + stateDecor(e, w, h);
  }

  function xy(e, w, h) {
    const unbound = e.state === "unbound";
    const ph = h - 18, x = 1 + (w - 2) * (e.x ?? 0.6), y = 1 + (ph - 2) * (1 - (e.y ?? 0.4));
    let s = `<rect x="0.5" y="0.5" width="${w - 1}" height="${ph - 1}" rx="${role("radius")}" fill="${role("surface-raised")}" stroke="${role("border")}"/>`;
    for (let i = 1; i < 4; i++) { s += `<path d="M${(w * i) / 4} 1V${ph - 1}M1 ${(ph * i) / 4}H${w - 1}" stroke="${role("border")}" stroke-width="0.75" opacity="0.7"/>`; }
    if (!unbound) {
      s += `<path d="M${x} 1V${ph - 1}M1 ${y}H${w - 1}" stroke="${role("accent-2")}" stroke-width="1" opacity="0.55"/>`;
      s += `<circle cx="${x}" cy="${y}" r="${e.state === "dragging" ? 9 : 7}" fill="${role("accent-2")}" stroke="${role("background")}" stroke-width="2"/>`;
    }
    s += `<text x="4" y="${h - 4}" fill="${role("text-muted")}" font-family="${role("font-body")}" font-size="10.5">${esc(e.xLabel || "X")} · ${esc(e.yLabel || "Y")}</text>`;
    s += bubble(e, x, y - 9, e.text || "");
    return s + stateDecor(e, w, h);
  }

  function selector(e, w, h) {
    const opts = e.options || ["LP", "BP", "HP"], sel = e.selected ?? 0, unbound = e.state === "unbound";
    let s = "";
    if ((e.presentation || "segments") === "segments") {
      const sw = (w - 2) / opts.length, sh = Math.min(h, 26), y = (h - sh) / 2;
      s += `<rect x="0.5" y="${y + 0.5}" width="${w - 1}" height="${sh - 1}" rx="5" fill="${role("surface-raised")}" stroke="${role("border")}"/>`;
      opts.forEach((o, i) => {
        if (i === sel && !unbound) s += `<rect x="${1 + i * sw + 2}" y="${y + 3}" width="${sw - 4}" height="${sh - 6}" rx="3.5" fill="${role(e.accent || "accent-1")}"/>`;
        s += `<text x="${1 + i * sw + sw / 2}" y="${y + sh / 2 + 4}" text-anchor="middle" fill="${i === sel && !unbound ? role("background") : role(unbound ? "disabled" : "text-muted")}" font-family="${role("font-body")}" font-size="11" font-weight="600">${esc(o)}</text>`;
      });
    } else {
      const bh = Math.min(h, 26), y = (h - bh) / 2;
      s += `<rect x="0.5" y="${y + 0.5}" width="${w - 1}" height="${bh - 1}" rx="5" fill="${role("surface-raised")}" stroke="${e.state === "hover" ? role("text-muted") : role("border")}"/>`;
      s += `<text x="9" y="${y + bh / 2 + 4}" fill="${role(unbound ? "disabled" : "text")}" font-family="${role("font-body")}" font-size="11.5">${esc(unbound ? "⛓ " + (e.missing || "gone") : opts[sel])}</text>`;
      s += `<path d="m${w - 17} ${y + bh / 2 - 2} 4 4 4-4" stroke="${role("text-muted")}" stroke-width="1.6" fill="none"/>`;
    }
    return s + stateDecor(e, w, h);
  }

  function menuEl(e, w, h) {
    const bh = Math.min(h, 26), y = (h - bh) / 2;
    let s = `<rect x="0.5" y="${y + 0.5}" width="${w - 1}" height="${bh - 1}" rx="5" fill="${role("surface-raised")}" stroke="${role("border")}"/>`;
    s += `<text x="10" y="${y + bh / 2 + 4}" fill="${role("text")}" font-family="${role("font-body")}" font-size="11.5" font-weight="500">${esc(e.label || "Presets")}</text>`;
    s += `<path d="m${w - 18} ${y + bh / 2 - 3} 5 5 5-5" stroke="${role("text-muted")}" stroke-width="1.6" fill="none"/>`;
    return s + stateDecor(e, w, h);
  }

  function tabs(e, w, h) {
    const names = e.pages || ["Main", "Filter", "Dynamics", "Mod"], cur = e.current ?? 0;
    const tw = w / names.length;
    let s = `<path d="M0 ${h - 0.5}H${w}" stroke="${role("border")}"/>`;
    names.forEach((n, i) => {
      s += `<text x="${i * tw + tw / 2}" y="${h / 2 + 3}" text-anchor="middle" fill="${i === cur ? role("text") : role("text-muted")}" font-family="${role("font-body")}" font-size="12" font-weight="${i === cur ? 600 : 500}">${esc(n)}</text>`;
      if (i === cur) s += `<rect x="${i * tw + 10}" y="${h - 3}" width="${tw - 20}" height="3" rx="1.5" fill="${role(e.accent || "accent-1")}"/>`;
    });
    return s + stateDecor(e, w, h);
  }

  function frame(w, h) {
    return `<rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" rx="${role("radius")}" fill="${role("background")}" stroke="${role("border")}"/>`;
  }
  function noSignal(e, w, h) {
    const t = `No signal: ${esc(e.tap || "out")}`;
    if (w < 80) return `<rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" rx="4" fill="none" stroke="${role("disabled")}" stroke-dasharray="4 3"/><text transform="translate(${w / 2 + 3.5} ${h / 2}) rotate(-90)" text-anchor="middle" fill="${role("text-muted")}" font-family="${role("font-body")}" font-size="10">${t}</text>`;
    return frame(w, h) + `<text x="${w / 2}" y="${h / 2 + 4}" text-anchor="middle" fill="${role("text-muted")}" font-family="${role("font-body")}" font-size="11.5">${t}</text>`;
  }
  function scope(e, w, h) {
    if (e.state === "unbound") return noSignal(e, w, h);
    let s = frame(w, h);
    for (let i = 1; i < 8; i++) s += `<path d="M${(w * i) / 8} 1V${h - 1}" stroke="${role("border")}" stroke-width="0.6" opacity="0.6"/>`;
    s += `<path d="M1 ${h / 2}H${w - 1}" stroke="${role("border")}" stroke-width="0.8"/>`;
    const trace = (amp, ph, col) => { let d = ""; for (let x = 2; x < w - 2; x += 2) { const t = x / w; const y = h / 2 - amp * (h / 2 - 10) * (Math.sin(t * Math.PI * 9 + ph) * 0.75 + Math.sin(t * Math.PI * 27 + ph) * 0.2) * (0.85 + 0.15 * Math.sin(t * 4)); d += (x === 2 ? "M" : "L") + r(x) + " " + r(y); } return `<path d="${d}" stroke="${col}" stroke-width="1.6" fill="none"/>`; };
    s += trace(0.8, 0, role(e.accent || "accent-2")) + trace(0.62, 0.5, role("accent-7"));
    s += `<text x="8" y="16" fill="${role("text-muted")}" font-family="${role("font-body")}" font-size="10.5">${esc(e.label || "Output")} · 50 ms</text>`;
    return s + stateDecor(e, w, h);
  }
  function spectrum(e, w, h) {
    if (e.state === "unbound") return noSignal(e, w, h);
    let s = frame(w, h);
    [100, 1000, 10000].forEach((f) => { const x = (Math.log10(f / 20) / Math.log10(24000 / 20)) * w; s += `<path d="M${r(x)} 1V${h - 1}" stroke="${role("border")}" stroke-width="0.8"/><text x="${r(x + 3)}" y="${h - 5}" fill="${role("text-muted")}" font-family="${role("font-value")}" font-size="9.5">${f >= 1000 ? f / 1000 + "k" : f}</text>`; });
    let d = `M1 ${h - 1}`;
    for (let x = 1; x < w; x += 2) { const t = x / w; const y = h * (0.25 + 0.55 * t * t) - 28 * Math.exp(-Math.pow((t - 0.32) * 9, 2)) + 5 * Math.sin(x * 0.7) * t; d += ` L${x} ${r(Math.min(h - 2, Math.max(6, y)))}`; }
    d += ` L${w - 1} ${h - 1} Z`;
    s += `<path d="${d}" fill="${role(e.accent || "accent-7")}" opacity="0.28"/><path d="${d.replace(/ Z$/, "").replace(/^M1 [\d.]+ /, "M1 " + (h * 0.25) + " ")}" stroke="${role(e.accent || "accent-7")}" stroke-width="1.4" fill="none"/>`;
    return s + stateDecor(e, w, h);
  }
  function level(e, w, h) {
    if (e.state === "unbound") return noSignal(e, w, h);
    const bh = h - 16, bw = (w - 10) / 2;
    let s = "";
    [[e.l ?? 0.72, e.pl ?? 0.8], [e.rr ?? 0.66, e.pr ?? 0.76]].forEach(([v, p], i) => {
      const x = 2 + i * (bw + 6);
      s += `<rect x="${x}" y="2" width="${bw}" height="${bh}" rx="2" fill="${role("surface-raised")}" stroke="${role("border")}"/>`;
      const y = 2 + bh * (1 - v);
      s += `<rect x="${x + 1}" y="${y}" width="${bw - 2}" height="${2 + bh - y - 1}" rx="1" fill="${role("positive")}"/>`;
      const warnTop = 2 + bh * (1 - 0.9);
      if (v > 0.9) s += `<rect x="${x + 1}" y="${y}" width="${bw - 2}" height="${warnTop - y}" fill="${role("warning")}"/>`;
      s += `<rect x="${x + 1}" y="${2 + bh * (1 - p)}" width="${bw - 2}" height="2" fill="${role("text")}"/>`;
    });
    s += `<text x="${w / 2}" y="${h - 2}" text-anchor="middle" fill="${role("text-muted")}" font-family="${role("font-value")}" font-size="9.5">${esc(e.text || "−6.2")}</text>`;
    return s + stateDecor(e, w, h);
  }
  function gr(e, w, h) {
    if (e.state === "unbound") return noSignal(e, w, h);
    const bh = h - 16, v = e.value ?? 0.3;
    let s = `<rect x="2" y="2" width="${w - 4}" height="${bh}" rx="2" fill="${role("surface-raised")}" stroke="${role("border")}"/>`;
    s += `<rect x="3" y="3" width="${w - 6}" height="${bh * v}" rx="1" fill="${role(e.accent || "accent-1")}"/>`;
    [6, 12, 18].forEach((db) => { const y = 2 + (bh * db) / 24; s += `<path d="M2 ${y}h4" stroke="${role("text-muted")}"/>`; });
    s += `<text x="${w / 2}" y="${h - 2}" text-anchor="middle" fill="${role("text-muted")}" font-family="${role("font-value")}" font-size="9.5">${esc(e.text || "GR")}</text>`;
    return s + stateDecor(e, w, h);
  }
  function label(e, w, h) {
    const size = e.size || 12, anchor = { left: "start", centre: "middle", right: "end" }[e.align || "left"];
    const x = { left: 0, centre: w / 2, right: w }[e.align || "left"];
    const font = role(e.typeface === "value" ? "font-value" : e.typeface === "heading" ? "font-heading" : "font-body");
    return `<text x="${x}" y="${h / 2 + size * 0.36}" text-anchor="${anchor}" fill="${role(e.role || "text")}" font-family="${font}" font-size="${size}" font-weight="${e.typeface === "heading" ? 650 : 500}" letter-spacing="${e.tracking || 0}">${esc(e.text || "Label")}</text>` + stateDecor(e, w, h);
  }
  function panel(e, w, h) {
    let s = `<rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" rx="${role("radius")}" fill="${role(e.surface || "surface")}" stroke="${role("border")}" stroke-width="${role("border-width")}"/>`;
    if (e.title) s += `<text x="12" y="20" fill="${role("text-muted")}" font-family="${role("font-heading")}" font-size="10.5" font-weight="650" letter-spacing="1">${esc(e.title.toUpperCase())}</text>`;
    return s + stateDecor(e, w, h);
  }
  function image(e, w, h) {
    const id = "g" + Math.random().toString(36).slice(2, 7);
    return `<defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${role("accent-5")}" stop-opacity="0.55"/><stop offset="1" stop-color="${role("accent-7")}" stop-opacity="0.35"/></linearGradient><pattern id="${id}p" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.6" fill="${role("text")}" opacity="0.25"/></pattern></defs><rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" rx="${role("radius")}" fill="url(#${id})"/><rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" rx="${role("radius")}" fill="url(#${id}p)"/><text x="8" y="${h - 8}" fill="${role("text")}" font-family="${role("font-body")}" font-size="10" opacity="0.8">${esc(e.file || "brushed.png")}</text>` + stateDecor(e, w, h);
  }

  /* a developer's custom kind, as the reference plugin registers it: "Transfer curve" */
  function transfer(e, w, h) {
    const unbound = e.state === "unbound";
    const d = e.value ?? 0.44, pad = 10, iw = w - 2 * pad, ih = h - 2 * pad - 14;
    let s = frame(w, h);
    if (e.grid !== false) for (let i = 1; i < 4; i++) s += `<path d="M${pad + (iw * i) / 4} ${pad}V${pad + ih}M${pad} ${pad + (ih * i) / 4}H${pad + iw}" stroke="${role("border")}" stroke-width="0.7"/>`;
    s += `<path d="M${pad} ${pad + ih}L${pad + iw} ${pad}" stroke="${role("text-muted")}" stroke-width="1" stroke-dasharray="3 3"/>`;
    if (!unbound) {
      let p = ""; const k = 1 + d * 9;
      for (let i = 0; i <= 48; i++) { const x = -1 + (2 * i) / 48, y = Math.tanh(k * x) / Math.tanh(k); p += (i ? "L" : "M") + r(pad + ((x + 1) / 2) * iw) + " " + r(pad + ih - ((y + 1) / 2) * ih); }
      s += `<path d="${p}" stroke="${role(e.accent || "accent-3")}" stroke-width="2" fill="none"/>`;
    }
    s += `<text x="${pad}" y="${h - 7}" fill="${role(unbound ? "text-muted" : "text-muted")}" font-family="${role("font-body")}" font-size="10.5">${unbound ? esc(e.missing || "gone") : "Transfer · Drive"}</text>`;
    return s + stateDecor(e, w, h);
  }
  /* an element whose custom kind is not registered here (or is newer): kept, drawn as a placeholder */
  function unknown(e, w, h) {
    const id = "u" + Math.random().toString(36).slice(2, 7);
    return `<defs><pattern id="${id}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="8" fill="${role("disabled")}" opacity="0.18"/></pattern></defs>` +
      `<rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" rx="6" fill="url(#${id})" stroke="${role("disabled")}" stroke-dasharray="5 3"/>` +
      `<text x="${w / 2}" y="${h / 2 - 3}" text-anchor="middle" fill="${role("text-muted")}" font-family="${role("font-body")}" font-size="11.5" font-weight="600">Unknown element</text>` +
      (() => { let t = `${e.kindId || "org.vendor.wavetable"} v${e.kindVersion || 3}`; const max = Math.floor((w - 12) / 5.6); if (t.length > max) t = t.slice(0, max - 1) + "…"; return `<text x="${w / 2}" y="${h / 2 + 13}" text-anchor="middle" fill="${role("text-muted")}" font-family="${role("font-value")}" font-size="9.5">${esc(t)}</text>`; })() + stateDecor(Object.assign({}, e, { state: e.state === "unbound" ? "normal" : e.state }), w, h);
  }
  const DRAW = { custom_transfer: transfer, unknown, knob, macro, fader, switch: toggle, xy_pad: xy, selector, menu: menuEl, page_tabs: tabs, oscilloscope: scope, spectrum, level_meter: level, gr_meter: gr, label, panel, image };

  function svgFor(e) {
    const w = e.w, h = e.h;
    const body = (DRAW[e.kind] || panel)(e, w, h);
    return `<svg xmlns="${NS}" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" overflow="visible" style="position:absolute;left:${e.x}px;top:${e.y}px">${body}</svg>`;
  }

  /* ---------- the reference plugin's default layout (canvas 840 x 520, page "Main") ---------- */
  const REF = {
    canvas: [840, 520],
    pages: ["Main", "Filter", "Dynamics", "Mod"],
    elements: [
      { id: "title", kind: "label", x: 24, y: 14, w: 260, h: 30, text: "REFERENCE FX", typeface: "heading", size: 15, tracking: 2 },
      { id: "tabs", kind: "page_tabs", x: 488, y: 14, w: 328, h: 30 },
      { id: "p-filter", kind: "panel", x: 24, y: 58, w: 256, h: 244, title: "Filter" },
      { id: "cutoff", kind: "knob", x: 40, y: 88, w: 72, h: 100, label: "Cutoff", value: 0.62, text: "1.24 kHz", mod: 0.74 },
      { id: "reso", kind: "knob", x: 116, y: 88, w: 72, h: 100, label: "Resonance", value: 0.35, text: "35 %" },
      { id: "envamt", kind: "knob", x: 192, y: 88, w: 72, h: 100, label: "Env Amt", value: 0.5, text: "+0 %" },
      { id: "mode", kind: "selector", x: 40, y: 206, w: 224, h: 28, options: ["LP", "BP", "HP", "Notch"], selected: 0 },
      { id: "keytrack", kind: "switch", x: 40, y: 250, w: 140, h: 28, label: "Key track", on: true },
      { id: "p-drive", kind: "panel", x: 296, y: 58, w: 184, h: 244, title: "Drive" },
      { id: "drive", kind: "knob", x: 318, y: 86, w: 140, h: 156, label: "Drive", value: 0.44, text: "8.8 dB", accent: "accent-3" },
      { id: "os", kind: "switch", x: 318, y: 256, w: 150, h: 28, label: "Oversample 2×", on: false },
      { id: "p-dyn", kind: "panel", x: 496, y: 58, w: 320, h: 244, title: "Compressor" },
      { id: "thresh", kind: "knob", x: 512, y: 88, w: 72, h: 100, label: "Threshold", value: 0.58, text: "−18.0 dB", accent: "accent-4" },
      { id: "ratio", kind: "knob", x: 588, y: 88, w: 72, h: 100, label: "Ratio", value: 0.3, text: "4.0 : 1", accent: "accent-4" },
      { id: "attack", kind: "knob", x: 512, y: 196, w: 72, h: 100, label: "Attack", value: 0.22, text: "8 ms", accent: "accent-4", style: "pointer" },
      { id: "release", kind: "knob", x: 588, y: 196, w: 72, h: 100, label: "Release", value: 0.48, text: "120 ms", accent: "accent-4", style: "pointer" },
      { id: "grm", kind: "gr_meter", x: 684, y: 88, w: 36, h: 200, value: 0.28, text: "6.7" },
      { id: "makeup", kind: "fader", x: 736, y: 88, w: 64, h: 200, label: "Makeup", value: 0.4, text: "+3.5 dB", accent: "accent-4" },
      { id: "scope", kind: "oscilloscope", x: 24, y: 318, w: 456, h: 186, label: "out" },
      { id: "macro", kind: "macro", x: 496, y: 318, w: 120, h: 170, label: "Character", value: 0.57, text: "57 %", targets: 3 },
      { id: "p-out", kind: "panel", x: 632, y: 318, w: 176, h: 170, title: "Output" },
      { id: "outfader", kind: "fader", x: 646, y: 344, w: 56, h: 138, label: "Level", value: 0.71, text: "−1.5 dB" },
      { id: "outmeter", kind: "level_meter", x: 716, y: 346, w: 30, h: 132, text: "−6.2" },
      { id: "mix", kind: "knob", x: 752, y: 352, w: 52, h: 82, label: "Mix", value: 1, text: "100 %", style: "filled" },
    ],
  };

  function canvas(opts) {
    const o = Object.assign({ layout: REF, scale: 1, theme: "", design: false, selected: [], states: {}, reserved: "bottom-right", grid: false, hide: [] }, opts || {});
    const [cw, ch] = o.layout.canvas;
    let html = `<div class="mg-canvas ${o.theme}" style="position:relative;width:${cw}px;height:${ch}px;background:var(--role-background);transform:scale(${o.scale});transform-origin:0 0;overflow:hidden">`;
    if (o.grid) html += `<div style="position:absolute;inset:0;background-image:linear-gradient(var(--tool-grid) 1px,transparent 1px),linear-gradient(90deg,var(--tool-grid) 1px,transparent 1px);background-size:8px 8px"></div>`;
    for (const base of o.layout.elements) {
      if (o.hide.includes(base.id)) continue;
      const e = Object.assign({}, base, o.states[base.id] || {});
      html += svgFor(e);
    }
    if (o.design) {
      for (const id of o.selected) {
        const e = o.layout.elements.find((x) => x.id === id);
        if (!e) continue;
        html += `<div class="mg-sel" style="position:absolute;left:${e.x - 1}px;top:${e.y - 1}px;width:${e.w + 2}px;height:${e.h + 2}px;border:1.5px solid var(--tool-accent);pointer-events:none">` +
          (o.selected.length === 1 ? ["0 0", "50% 0", "100% 0", "0 50%", "100% 50%", "0 100%", "50% 100%", "100% 100%"].map((p) => { const [a, b] = p.split(" "); return `<span style="position:absolute;left:calc(${a} - 4px);top:calc(${b} - 4px);width:7px;height:7px;background:var(--tool-handle);border:1.5px solid var(--tool-accent);border-radius:1.5px"></span>`; }).join("") : "") + `</div>`;
      }
    }
    html += `</div>`;
    return html;
  }

  const SMALL = { canvas: [400, 300], pages: ["Live"], elements: [
    { id: "t", kind: "label", x: 20, y: 12, w: 200, h: 26, text: "LIVE", typeface: "heading", size: 14, tracking: 2 },
    { id: "c", kind: "knob", x: 20, y: 52, w: 110, h: 150, label: "Cutoff", value: 0.62, text: "1.24 kHz" },
    { id: "d", kind: "knob", x: 145, y: 52, w: 110, h: 150, label: "Drive", value: 0.44, text: "8.8 dB", accent: "accent-3" },
    { id: "m", kind: "macro", x: 270, y: 52, w: 110, h: 150, label: "Character", value: 0.57, text: "57 %", targets: 3 },
    { id: "s", kind: "selector", x: 20, y: 228, w: 200, h: 28, options: ["LP", "BP", "HP", "Notch"], selected: 0 },
    { id: "b", kind: "switch", x: 232, y: 228, w: 120, h: 28, label: "Bypass", on: false } ] };
  /* the editor menu button: fixed 24 px, corner set by the developer (default bottom-right), 8 px inset */
  function menuButton(o) {
    o = Object.assign({ corner: "bottom-right", state: "faint", badge: false }, o || {});
    const [v, h] = o.corner.split("-");
    return `<div class="menu-button ${o.state}" style="${v}:8px;${h}:8px">${icon(o.state === "design" ? "edit" : "menu", 14)}${o.badge ? '<span class="badge"></span>' : ""}</div>`;
  }
  /* fill #stage (or the given id) with a canvas */
  function stage(opts, id) { const n = document.getElementById(id || "stage"); if (n) n.innerHTML = canvas(opts); }
  window.MG = { icon, svgFor, canvas, REF, SMALL, DRAW, menuButton, stage };
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-icon]").forEach((n) => { n.insertAdjacentHTML("afterbegin", icon(n.dataset.icon, +(n.dataset.size || 16))); });
    document.querySelectorAll("[data-el]").forEach((n) => { const e = JSON.parse(n.dataset.el); n.style.position = "relative"; n.style.width = e.w + "px"; n.style.height = e.h + "px"; n.innerHTML = svgFor(Object.assign({ x: 0, y: 0 }, e)); });
    if (typeof window.mgReady === "function") window.mgReady();
  });
})();
