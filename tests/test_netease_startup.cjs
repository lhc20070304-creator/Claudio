const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const { EventEmitter } = require('node:events');
const source = fs.readFileSync('macos/netease.cjs', 'utf8');

async function run(cached) {
    let killed = false, spawned = false, options, created = false;
    const module = { exports: {} };
    const mockRequire = name => {
        if (name === 'node:fs') return {
            existsSync: () => cached,
            writeFileSync: () => { created = true; },
            readFileSync: () => cached ? 'cached-anonymous-token' : '',
        };
        if (name === 'node:child_process') return {spawn() {
            spawned = true;
            const worker = new EventEmitter();
            worker.kill = () => { killed = true; setImmediate(() => worker.emit('close')); };
            return worker; // external refresh never answers
        }};
        if (name === 'NeteaseCloudMusicApi/util/index') return { generateRandomChineseIP: () => 'test' };
        if (name === 'NeteaseCloudMusicApi/server') return { serveNcmApi: async value => { options = value; return 'ready'; } };
        return require(name);
    };
    const context = { module, require: mockRequire, process, __dirname: '/test/macos',
        global: {}, console: { error() {} }, setTimeout, clearTimeout };
    vm.runInNewContext(source, context);
    assert.equal(await module.exports.start({refreshTimeoutMs: 20}), 'ready');
    assert.equal(options.checkVersion, false);
    assert.equal(options.host, '127.0.0.1');
    assert.equal(spawned, !cached);
    assert.equal(killed, !cached);
    assert.equal(created, !cached);
}
(async () => {
    await run(true);
    await run(false);
    console.log('PASS: cached token skips network; stuck anonymous refresh is killed; API still starts without version check');
})().catch(error => { console.error(error); process.exitCode = 1; });
