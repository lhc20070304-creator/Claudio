/* ═══ DotGrid — spec: dotSize=2 gap=11 base=#2d2836 active=#34D399 ═══ */
(function () {
  var canvas = document.getElementById('dotGridCanvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');

  var DOT = 2, GAP = 11, CELL = DOT + GAP;
  var PROXIMITY = 100, PUSH = 10, SHOCK_RADIUS = 100, SHOCK_STRENGTH = 2;
  var RETURN_MS = 500;

  function hex(s) {
    var m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(s);
    return m ? [parseInt(m[1],16), parseInt(m[2],16), parseInt(m[3],16)] : [0,0,0];
  }
  var base = hex('#2d2836'), active = hex('#34D399');

  var dots = [], mx = -9999, my = -9999;
  var w = 0, h = 0;

  function build() {
    var wrap = canvas.parentElement;
    var rw = wrap.clientWidth, rh = wrap.clientHeight;
    var dpr = window.devicePixelRatio || 1;
    canvas.width = rw * dpr;
    canvas.height = rh * dpr;
    canvas.style.width = rw + 'px';
    canvas.style.height = rh + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    w = rw; h = rh;

    var cols = Math.floor((w + GAP) / CELL);
    var rows = Math.floor((h + GAP) / CELL);
    var gw = CELL * cols - GAP, gh = CELL * rows - GAP;
    var sx = (w - gw) / 2 + DOT / 2;
    var sy = (h - gh) / 2 + DOT / 2;

    dots = [];
    for (var y = 0; y < rows; y++)
      for (var x = 0; x < cols; x++)
        dots.push({ cx: sx + x * CELL, cy: sy + y * CELL, ox: 0, oy: 0 });
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    var psq = PROXIMITY * PROXIMITY;
    for (var i = 0; i < dots.length; i++) {
      var d = dots[i];
      var dx = d.cx - mx, dy = d.cy - my, dsq = dx * dx + dy * dy;
      var px = d.ox, py = d.oy;
      var rd = DOT / 2;
      var r = base[0], g = base[1], b = base[2];
      if (dsq <= psq) {
        var dist = Math.sqrt(dsq);
        var raw = 1 - dist / PROXIMITY;
        var t = raw * raw * (3 - 2 * raw); // smoothstep dome
        r = Math.round(base[0] + (active[0] - base[0]) * t);
        g = Math.round(base[1] + (active[1] - base[1]) * t);
        b = Math.round(base[2] + (active[2] - base[2]) * t);
        px += (dx / (dist || 1)) * PUSH * t;
        py += (dy / (dist || 1)) * PUSH * t;
      }
      ctx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
      ctx.beginPath();
      ctx.arc(d.cx + px, d.cy + py, rd, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function loop() { draw(); requestAnimationFrame(loop); }

  function shock(cx, cy) {
    for (var i = 0; i < dots.length; i++) {
      var d = dots[i];
      var dist = Math.hypot(d.cx - cx, d.cy - cy);
      if (dist < SHOCK_RADIUS) {
        var f = Math.max(0, 1 - dist / SHOCK_RADIUS);
        var tx = (d.cx - cx) * SHOCK_STRENGTH * f;
        var ty = (d.cy - cy) * SHOCK_STRENGTH * f;
        var st = performance.now();
        d.ox = tx; d.oy = ty;
        (function spring(dot, sx, sy, start) {
          return function tick(now) {
            var p = Math.min((now - start) / RETURN_MS, 1);
            var e = 1 - Math.pow(1 - p, 3);
            dot.ox = sx * (1 - e); dot.oy = sy * (1 - e);
            if (p < 1) requestAnimationFrame(tick);
            else { dot.ox = 0; dot.oy = 0; }
          };
        })(d, tx, ty, st)(st);
      }
    }
  }

  function onMove(e) {
    var r = canvas.getBoundingClientRect();
    mx = e.clientX - r.left; my = e.clientY - r.top;
  }
  function onLeave() { mx = -9999; my = -9999; }
  function onClick(e) {
    var r = canvas.getBoundingClientRect();
    shock(e.clientX - r.left, e.clientY - r.top);
  }

  build();
  loop();
  window.addEventListener('resize', build);
  canvas.parentElement.addEventListener('mousemove', onMove, { passive: true });
  canvas.parentElement.addEventListener('mouseleave', onLeave);
  canvas.parentElement.addEventListener('click', onClick);
})();
