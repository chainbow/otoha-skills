/* Fits the artboard into the preview and checks the page the way a careful reviewer would.
   Findings go to the console, where page_check reports them:
     errors   - text without a data-edit name, repeated names, text outside or cut off by its box
     warnings - low contrast, text too small for the artboard, text lines on top of each other
   A page with no findings prints nothing. Add data-layer to an element whose overlap is intended. */
(function () {
  var board = document.querySelector(".artboard");
  if (!board) {
    console.error("design-check: no element with class artboard");
    return;
  }
  var root = document.documentElement;
  window.designCheck = true;
  if (getComputedStyle(board).overflow !== "hidden") {
    console.error("design-check: lib/base.css did not load; copy this skill's assets into the design folder as lib");
  }

  function fit() {
    var w = board.offsetWidth, h = board.offsetHeight;
    var scale = Math.min((window.innerWidth - 32) / w, (window.innerHeight - 32) / h, 2);
    root.style.setProperty("--fit", String(Math.max(0.05, scale)));
  }
  fit();
  window.addEventListener("resize", fit);

  var context = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  function parse(color) {
    context.clearRect(0, 0, 1, 1);
    context.fillStyle = "#000";
    context.fillStyle = color;
    context.fillRect(0, 0, 1, 1);
    var d = context.getImageData(0, 0, 1, 1).data;
    return { r: d[0], g: d[1], b: d[2], a: d[3] / 255 };
  }
  function over(top, bottom) {
    var a = top.a + bottom.a * (1 - top.a);
    if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
    return {
      r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a,
      g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a,
      b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a,
      a: a,
    };
  }
  function luminance(c) {
    function channel(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
  }
  function ratio(a, b) {
    var x = luminance(a), y = luminance(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  }

  // The solid colour behind an element, or null when a picture or gradient is behind it.
  function backdrop(element) {
    var layers = [];
    for (var node = element; node && node.nodeType === 1; node = node.parentElement) {
      var style = getComputedStyle(node);
      if (style.backgroundImage !== "none") return null;
      var color = parse(style.backgroundColor);
      if (color.a > 0) layers.push(color);
      if (color.a >= 1) break;
    }
    var result = { r: 255, g: 255, b: 255, a: 1 };
    for (var i = layers.length - 1; i >= 0; i--) result = over(layers[i], result);
    return result;
  }
  function opacityOf(element) {
    var value = 1;
    for (var node = element; node && node.nodeType === 1; node = node.parentElement) value *= parseFloat(getComputedStyle(node).opacity);
    return value;
  }

  function hasOwnText(element) {
    for (var node = element.firstChild; node; node = node.nextSibling) {
      if (node.nodeType === 3 && node.nodeValue.trim() !== "") return true;
    }
    return false;
  }
  function describe(element) {
    var text = (element.textContent || "").replace(/\s+/g, " ").trim();
    if (text.length > 28) text = text.slice(0, 28) + "…";
    var name = element.getAttribute("data-edit");
    return "<" + element.tagName.toLowerCase() + (name ? ' data-edit="' + name + '"' : "") + '> "' + text + '"';
  }
  function report(log, message, items) {
    if (!items.length) return;
    var shown = items.slice(0, 5).join("; ");
    log("design-check: " + message + " (" + items.length + "): " + shown + (items.length > 5 ? "; and " + (items.length - 5) + " more" : ""));
  }
  function contentRect(element) {
    var range = document.createRange();
    range.selectNodeContents(element);
    return range;
  }

  function check() {
    // Measure at the artboard's own size, then give the preview its fitted size back.
    var saved = root.style.getPropertyValue("--fit");
    root.style.setProperty("--fit", "1");
    var board_rect = board.getBoundingClientRect();
    var shortSide = Math.min(board.offsetWidth, board.offsetHeight);
    var smallest = Math.max(11, Math.round(shortSide * 0.015));

    var texts = [];
    var all = board.querySelectorAll("*");
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      var tag = el.tagName.toLowerCase();
      if (tag === "script" || tag === "style" || el.closest("[hidden]")) continue;
      if (hasOwnText(el)) texts.push(el);
    }

    var missing = [], names = {}, repeated = [], outside = [], cut = [], contrast = [], small = [], overlap = [], empty = [];

    texts.forEach(function (el) {
      var named = el.closest("[data-edit]");
      if (!named) missing.push(describe(el));
    });
    board.querySelectorAll("[data-edit]").forEach(function (el) {
      var name = el.getAttribute("data-edit");
      if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(name)) repeated.push(describe(el) + " has a name that is not lowercase words joined by hyphens");
      if (names[name]) repeated.push('the name "' + name + '" is used more than once'); else names[name] = true;
    });

    var lines = [];
    texts.forEach(function (el) {
      var range = contentRect(el);
      var rects = Array.prototype.slice.call(range.getClientRects()).filter(function (r) { return r.width > 0 && r.height > 0; });
      if (!rects.length) return;
      var style = getComputedStyle(el);
      if (style.visibility === "hidden" || style.display === "none") return;

      // Outside the artboard, or cut off by a box that clips.
      var bad = rects.some(function (r) {
        return r.left < board_rect.left - 1 || r.top < board_rect.top - 1 || r.right > board_rect.right + 1 || r.bottom > board_rect.bottom + 1;
      });
      if (bad) outside.push(describe(el));
      for (var node = el; node && node !== board.parentElement; node = node.parentElement) {
        var s = getComputedStyle(node);
        var clips = s.overflowX !== "visible" || s.overflowY !== "visible";
        if (clips && node !== board) {
          var box = node.getBoundingClientRect();
          if (rects.some(function (r) { return r.right > box.right + 1 || r.bottom > box.bottom + 1 || r.left < box.left - 1 || r.top < box.top - 1; })) { cut.push(describe(el)); break; }
        }
      }
      if (el.scrollHeight > el.clientHeight + 1 && s_clips(style) || el.scrollWidth > el.clientWidth + 1 && s_clips(style)) {
        if (cut.indexOf(describe(el)) < 0) cut.push(describe(el));
      }

      // Size and contrast.
      var size = parseFloat(style.fontSize);
      if (size < smallest) small.push(describe(el) + " is " + Math.round(size) + "px; at least " + smallest + "px reads on this artboard");
      var back = backdrop(el);
      if (back) {
        var fore = parse(style.color);
        fore.a *= opacityOf(el);
        var mixed = over(fore, back);
        var value = ratio(mixed, back);
        var large = size >= 24 || (size >= 18.66 && parseInt(style.fontWeight, 10) >= 700);
        var need = large ? 3 : 4.5;
        if (value < need) contrast.push(describe(el) + " is " + value.toFixed(1) + ":1, needs " + need + ":1");
      }
      if (!el.closest("[data-layer]")) rects.forEach(function (r) { lines.push({ el: el, r: r }); });
    });

    // Text lines of different elements that cover each other.
    var seen = {};
    for (var a = 0; a < lines.length; a++) {
      for (var b = a + 1; b < lines.length; b++) {
        var x = lines[a], y = lines[b];
        if (x.el === y.el || x.el.contains(y.el) || y.el.contains(x.el)) continue;
        var w = Math.min(x.r.right, y.r.right) - Math.max(x.r.left, y.r.left);
        var h = Math.min(x.r.bottom, y.r.bottom) - Math.max(x.r.top, y.r.top);
        if (w <= 2 || h <= 2) continue;
        if (w * h < 0.25 * Math.min(x.r.width * x.r.height, y.r.width * y.r.height)) continue;
        var key = describe(x.el) + " and " + describe(y.el);
        if (!seen[key]) { seen[key] = true; overlap.push(key); }
      }
    }

    // Content that stops well short of the bottom (or starts well below the top) leaves a hole.
    var topmost = Infinity, lowest = -Infinity;
    lines.forEach(function (l) { topmost = Math.min(topmost, l.r.top); lowest = Math.max(lowest, l.r.bottom); });
    board.querySelectorAll("img, svg, video, canvas").forEach(function (m) {
      var r = m.getBoundingClientRect();
      if (r.width < 8 || r.height < 8 || r.height > board_rect.height * 0.9) return;
      topmost = Math.min(topmost, r.top); lowest = Math.max(lowest, r.bottom);
    });
    if (lowest > -Infinity) {
      var below = (board_rect.bottom - lowest) / board_rect.height, above = (topmost - board_rect.top) / board_rect.height;
      if (below > 0.15) empty.push("the lowest content ends " + Math.round(below * 100) + "% above the bottom edge");
      if (above > 0.15) empty.push("the highest content starts " + Math.round(above * 100) + "% below the top edge");
    }

    root.style.setProperty("--fit", saved || "1");
    fit();

    report(console.error, "text without a data-edit name (every visible text needs one)", missing);
    report(console.error, "data-edit names must be unique lowercase slugs", repeated);
    report(console.error, "text outside the artboard", outside);
    report(console.error, "text cut off or overflowing its box", cut);
    report(console.warn, "contrast too low", contrast);
    report(console.warn, "text too small", small);
    report(console.warn, "text lines on top of each other", overlap);
    report(console.warn, "unbalanced: space left empty (spread the content or move the closing line to the bottom)", empty);
  }
  function s_clips(style) { return style.overflowX !== "visible" || style.overflowY !== "visible"; }

  var ready = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
  Promise.all([ready, new Promise(function (resolve) {
    if (document.readyState === "complete") resolve(); else window.addEventListener("load", resolve);
  })]).then(function () { setTimeout(check, 50); });
})();
