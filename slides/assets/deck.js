// Slides: shows one slide at a time, fitted to the window, with the keyboard to move between them and
// the slide's number in the address, and draws the charts written into the page as SVG, offline.
// Printing (and the app's PDF export) puts every slide on a page of its own.
(function () {
  'use strict';

  var WIDTH = 1280;
  var HEIGHT = 720;
  var PALETTE = ['#5b57ef', '#0ea5a4', '#e0a019', '#e5484d', '#8e95a2'];

  /** The colour of the nth series: the deck's own (--chart-1…5) when it set one, else the built-in. */
  function paletteColor(index) {
    var slot = index % PALETTE.length;
    if (typeof document !== 'undefined' && document && document.body && window.getComputedStyle) {
      var own = window.getComputedStyle(document.body).getPropertyValue('--chart-' + (slot + 1)).trim();
      if (own) return own;
      if (slot === 0) {
        var accent = window.getComputedStyle(document.body).getPropertyValue('--accent').trim();
        if (accent) return accent;
      }
    }
    return PALETTE[slot];
  }
  var TYPES = ['column', 'bar', 'line', 'pie', 'stacked'];

  function escape(text) {
    return String(text).replace(/[&<>"']/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
  }

  function formatted(value) {
    return Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
  }

  /** A round top for the value axis: 9.1 → 10, 260 → 300. */
  function niceMax(max) {
    if (max <= 0) return 1;
    var step = Math.pow(10, Math.floor(Math.log10(max)));
    var steps = [1, 2, 2.5, 5, 10];
    for (var i = 0; i < steps.length; i += 1) {
      if (steps[i] * step >= max) return steps[i] * step;
    }
    return 10 * step;
  }

  function failure(message) {
    return '<svg class="chart-error" viewBox="0 0 1088 120" xmlns="http://www.w3.org/2000/svg" role="img">' +
      '<text x="544" y="64" text-anchor="middle">' + escape(message) + '</text></svg>';
  }

  /** Why the chart cannot be drawn, or null. */
  function problem(spec) {
    if (!spec || TYPES.indexOf(spec.type) < 0) return 'Chart type must be one of: ' + TYPES.join(', ');
    var categories = spec.categories;
    var series = spec.series;
    if (!Array.isArray(categories) || !categories.length || !Array.isArray(series) || !series.length) return 'A chart needs categories and series';
    for (var i = 0; i < series.length; i += 1) {
      var values = series[i] && series[i].values;
      if (!Array.isArray(values) || values.length !== categories.length) return 'Each series needs one value per category';
      for (var j = 0; j < values.length; j += 1) {
        if (typeof values[j] !== 'number' || !isFinite(values[j])) return 'Chart values must be numbers';
      }
    }
    if (spec.type === 'pie' && (series.length !== 1 || series[0].values.some(function (v) { return v < 0; }))) return 'A pie chart has one series of values of 0 or more';
    return null;
  }

  function legend(names, width) {
    var items = names.map(function (name, index) {
      var x = width - (names.length - index) * 170;
      return '<rect x="' + x + '" y="4" width="14" height="14" rx="3" fill="' + paletteColor(index) + '"/>' +
        '<text class="legend-text" x="' + (x + 22) + '" y="16">' + escape(name) + '</text>';
    });
    return '<g class="legend">' + items.join('') + '</g>';
  }

  /** The chart as SVG markup, 1088 wide, from {type, categories, series: [{name, values}]}. */
  function chartSVG(spec, size) {
    var trouble = problem(spec);
    if (trouble) return failure('图表数据无法绘制 · ' + trouble);
    var width = (size && size.width) || 1088;
    var height = (size && size.height) || 440;
    var categories = spec.categories;
    var series = spec.series;
    var parts = [];
    var open = '<svg class="chart-svg" viewBox="0 0 ' + width + ' ' + height + '" xmlns="http://www.w3.org/2000/svg" role="img">';

    if (spec.type === 'pie') {
      var values = series[0].values;
      var total = values.reduce(function (a, b) { return a + b; }, 0) || 1;
      var cx = height / 2 + 40;
      var cy = height / 2;
      var r = height / 2 - 20;
      var angle = -Math.PI / 2;
      values.forEach(function (value, index) {
        var sweep = (value / total) * Math.PI * 2;
        var end = angle + sweep;
        var large = sweep > Math.PI ? 1 : 0;
        var x1 = cx + r * Math.cos(angle), y1 = cy + r * Math.sin(angle);
        var x2 = cx + r * Math.cos(end), y2 = cy + r * Math.sin(end);
        var path = sweep >= Math.PI * 2 - 1e-9
          ? 'M ' + (cx - r) + ' ' + cy + ' a ' + r + ' ' + r + ' 0 1 0 ' + 2 * r + ' 0 a ' + r + ' ' + r + ' 0 1 0 ' + -2 * r + ' 0'
          : 'M ' + cx + ' ' + cy + ' L ' + x1 + ' ' + y1 + ' A ' + r + ' ' + r + ' 0 ' + large + ' 1 ' + x2 + ' ' + y2 + ' Z';
        parts.push('<path class="slice" d="' + path + '" fill="' + paletteColor(index) + '"/>');
        var middle = angle + sweep / 2;
        if (value / total >= 0.04) {
          parts.push('<text class="slice-label" x="' + (cx + r * 0.62 * Math.cos(middle)) + '" y="' + (cy + r * 0.62 * Math.sin(middle) + 8) +
            '" text-anchor="middle">' + Math.round((value / total) * 100) + '%</text>');
        }
        angle = end;
      });
      var names = categories.map(function (name, index) {
        var y = cy - (categories.length * 44) / 2 + index * 44 + 22;
        return '<rect x="' + (cx + r + 80) + '" y="' + (y - 14) + '" width="18" height="18" rx="4" fill="' + paletteColor(index) + '"/>' +
          '<text class="legend-text" x="' + (cx + r + 110) + '" y="' + y + '">' + escape(name) + ' · ' + formatted(values[index]) + '</text>';
      });
      parts.push('<g class="legend">' + names.join('') + '</g>');
      return open + parts.join('') + '</svg>';
    }

    var several = series.length > 1;
    var top = several ? 44 : 28;
    var left = spec.type === 'bar' ? 150 : 56;
    var bottom = spec.type === 'bar' ? 16 : 44;
    var right = spec.type === 'bar' ? 64 : 8;
    var plotWidth = width - left - right;
    var plotHeight = height - top - bottom;
    var stacked = spec.type === 'stacked';
    var max = 0;
    categories.forEach(function (_, index) {
      if (stacked) {
        max = Math.max(max, series.reduce(function (sum, item) { return sum + Math.max(0, item.values[index]); }, 0));
      } else {
        series.forEach(function (item) { max = Math.max(max, item.values[index]); });
      }
    });
    var ceiling = niceMax(max);

    if (several) parts.push(legend(series.map(function (item) { return item.name; }), width));

    if (spec.type === 'bar') {
      var band = plotHeight / categories.length;
      var barHeight = Math.min(44, (band * 0.7) / series.length);
      categories.forEach(function (category, index) {
        var y0 = top + band * index + (band - barHeight * series.length) / 2;
        parts.push('<text class="axis-label" x="' + (left - 14) + '" y="' + (y0 + (barHeight * series.length) / 2 + 7) + '" text-anchor="end">' + escape(category) + '</text>');
        series.forEach(function (item, s) {
          var length = (Math.max(0, item.values[index]) / ceiling) * plotWidth;
          var y = y0 + s * barHeight;
          parts.push('<rect class="bar" x="' + left + '" y="' + y + '" width="' + length + '" height="' + (barHeight - 4) + '" rx="4" fill="' + paletteColor(s) + '"/>');
          parts.push('<text class="value-label" x="' + (left + length + 10) + '" y="' + (y + barHeight / 2 + 5) + '">' + formatted(item.values[index]) + '</text>');
        });
      });
      return open + parts.join('') + '</svg>';
    }

    for (var g = 0; g <= 4; g += 1) {
      var gy = top + plotHeight - (plotHeight * g) / 4;
      parts.push('<line class="grid" x1="' + left + '" x2="' + (left + plotWidth) + '" y1="' + gy + '" y2="' + gy + '"/>');
      parts.push('<text class="axis-value" x="' + (left - 12) + '" y="' + (gy + 5) + '" text-anchor="end">' + formatted((ceiling * g) / 4) + '</text>');
    }
    var slot = plotWidth / categories.length;
    categories.forEach(function (category, index) {
      parts.push('<text class="axis-label" x="' + (left + slot * index + slot / 2) + '" y="' + (height - 12) + '" text-anchor="middle">' + escape(category) + '</text>');
    });
    var y = function (value) { return top + plotHeight - (Math.max(0, value) / ceiling) * plotHeight; };

    if (spec.type === 'line') {
      series.forEach(function (item, s) {
        var color = paletteColor(s);
        var points = item.values.map(function (value, index) { return (left + slot * index + slot / 2) + ',' + y(value); });
        parts.push('<polyline class="line" points="' + points.join(' ') + '" fill="none" stroke="' + color + '" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>');
        item.values.forEach(function (value, index) {
          var x = left + slot * index + slot / 2;
          parts.push('<circle cx="' + x + '" cy="' + y(value) + '" r="7" fill="#fff" stroke="' + color + '" stroke-width="4"/>');
          if (!several) parts.push('<text class="value-label" x="' + x + '" y="' + (y(value) - 18) + '" text-anchor="middle">' + formatted(value) + '</text>');
        });
      });
      return open + parts.join('') + '</svg>';
    }

    var groupWidth = Math.min(slot * 0.55, stacked ? 140 : (several ? 72 : 120) * series.length);
    categories.forEach(function (_, index) {
      var x0 = left + slot * index + (slot - groupWidth) / 2;
      var base = top + plotHeight;
      series.forEach(function (item, s) {
        var value = Math.max(0, item.values[index]);
        var barHeight = (value / ceiling) * plotHeight;
        var color = paletteColor(s);
        if (stacked) {
          base -= barHeight;
          parts.push('<rect class="bar" x="' + x0 + '" y="' + base + '" width="' + groupWidth + '" height="' + barHeight + '" fill="' + color + '"/>');
        } else {
          var barWidth = groupWidth / series.length;
          var x = x0 + s * barWidth;
          parts.push('<rect class="bar" x="' + (x + 2) + '" y="' + y(value) + '" width="' + (barWidth - 4) + '" height="' + barHeight + '" rx="6" fill="' + color + '"/>');
          if (!several) parts.push('<text class="value-label" x="' + (x + barWidth / 2) + '" y="' + (y(value) - 12) + '" text-anchor="middle">' + formatted(item.values[index]) + '</text>');
        }
      });
    });
    return open + parts.join('') + '</svg>';
  }

  window.OtohaDeck = { chartSVG: chartSVG };
  if (typeof document === 'undefined' || !document) return;

  function drawCharts() {
    var figures = document.querySelectorAll('figure.chart');
    for (var i = 0; i < figures.length; i += 1) {
      var figure = figures[i];
      var source = figure.getAttribute('data-chart') || (figure.querySelector('script[type="application/json"]') || {}).textContent;
      var spec = null;
      try {
        spec = JSON.parse(source || 'null');
      } catch (error) {
        spec = null;
      }
      var holder = document.createElement('div');
      holder.className = 'chart-holder';
      // chartSVG escapes every text it writes; the page's own data never becomes markup.
      holder.innerHTML = chartSVG(spec);
      figure.insertBefore(holder, figure.firstChild);
    }
  }

  var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
  var current = 0;
  var progress = document.createElement('div');
  progress.className = 'deck-progress';

  function fit() {
    var scale = Math.min(window.innerWidth / WIDTH, window.innerHeight / HEIGHT);
    document.documentElement.style.setProperty('--deck-scale', String(scale));
  }

  function show(index) {
    if (!slides.length) return;
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach(function (slide, i) { slide.classList.toggle('active', i === current); });
    progress.style.width = ((current + 1) / slides.length) * 100 + '%';
    if (history.replaceState) history.replaceState(null, '', '#' + (current + 1));
  }

  function fromAddress() {
    var number = parseInt(String(location.hash).slice(1), 10);
    return isNaN(number) ? 0 : number - 1;
  }

  slides.forEach(function (slide, index) {
    if (index === 0 || slide.classList.contains('cover')) return;
    var part = slide.getAttribute('data-section');
    if (part && !slide.classList.contains('section') && !slide.classList.contains('closing')) {
      var label = document.createElement('div');
      label.className = 'slide-section';
      label.textContent = part;
      slide.appendChild(label);
    }
    var number = document.createElement('div');
    number.className = 'slide-number';
    number.textContent = index + 1 + ' / ' + slides.length;
    slide.appendChild(number);
  });
  drawCharts();
  document.body.appendChild(progress);
  document.documentElement.classList.add('deck-ready');
  fit();
  show(fromAddress());

  window.addEventListener('resize', fit);
  window.addEventListener('hashchange', function () { show(fromAddress()); });
  document.addEventListener('keydown', function (event) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    var next = ['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'];
    var previous = ['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'];
    if (next.indexOf(event.key) >= 0) show(current + 1);
    else if (previous.indexOf(event.key) >= 0) show(current - 1);
    else if (event.key === 'Home') show(0);
    else if (event.key === 'End') show(slides.length - 1);
    else return;
    event.preventDefault();
  });
  document.addEventListener('click', function (event) {
    if (event.target.closest && event.target.closest('a, button')) return;
    show(event.clientX > window.innerWidth / 3 ? current + 1 : current - 1);
  });
})();
