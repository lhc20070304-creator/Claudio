const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const player = fs.readFileSync('static/player.js', 'utf8');
const listeners = {};
const avatar = {style: {}, dataset: {}, addEventListener: (name, fn) => listeners[name] = fn};
let minimized = 0, quit = 0;
const controls = {document: {querySelector: () => avatar}, window: {pywebview: {api: {
    minimize: () => minimized++, quit: () => quit++
}}}};
vm.createContext(controls);
vm.runInContext(player.slice(player.indexOf('// ── Avatar:'), player.indexOf('// ── Theme Toggle')), controls);
assert.equal(listeners.click, undefined); // unchanged Windows behavior
listeners.dblclick(); assert.equal(minimized, 1);
vm.runInContext(fs.readFileSync('macos/window.js', 'utf8'), controls);
listeners.click(); assert.equal(minimized, 2);
listeners.contextmenu({preventDefault() {}}); assert.equal(quit, 1);
assert.match(avatar.title, /单击/);

const source = player.slice(player.indexOf('    function fmSpeakLine('), player.indexOf('    function fmTypeLine('));
const spans = ['hello', 'world'].map(textContent => ({textContent, active: false}));
spans.forEach(s => s.classList = {add() {s.active = true;}, remove() {s.active = false;}});
let frame, src, advances = 0;
const context = {
    document: {getElementById: () => ({querySelector: () => ({querySelectorAll: () => spans})})},
    window: {highlightFmLine() {}},
    fmAudioCtx: {currentTime: 10, destination: {}, createBufferSource() {
        src = {connect() {}, start() {}}; return src;
    }},
    fmHlWord: -1, fmHlRAF: null, fmCurrentIdx: -1, fmSpeaking: false,
    fmClearWordHL() {spans.forEach(s => s.active = false); context.fmHlWord = -1;},
    fmStopWordHL() {}, updateFmStatusBar() {}, fmDebug() {}, fmAdvance() {advances++;},
    requestAnimationFrame(fn) {frame = fn; return 1;}
};
vm.createContext(context); vm.runInContext(source, context);
context.fmSpeakLine(0, 'hello world', {buf: {duration: 2}, boundaries: [
    {offset: 2000000, duration: 6000000}, {offset: 9000000, duration: 6000000}
]});
assert.deepEqual(spans.map(s => s.active), [false, false]); // leading silence
context.fmAudioCtx.currentTime = 10.3; frame();
assert.deepEqual(spans.map(s => s.active), [true, false]);
frame(); assert.deepEqual(spans.map(s => s.active), [true, false]); // paused clock
context.fmAudioCtx.currentTime = 11.1; frame(); // slow frame catches up
assert.deepEqual(spans.map(s => s.active), [false, true]);
src.onended(); assert.equal(advances, 1);
assert.deepEqual(spans.map(s => s.active), [false, false]);
console.log('PASS: Mac single click, Windows double click, right-click quit; audio-clock word highlight, silence, pause, late frame, end cleanup');
