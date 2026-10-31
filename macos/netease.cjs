// macOS startup must not wait indefinitely for anonymous login or npm checks.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawn } = require('node:child_process');

async function start({ refreshTimeoutMs = 5000 } = {}) {
    const tokenPath = path.join(os.tmpdir(), 'anonymous_token');
    if (!fs.existsSync(tokenPath)) fs.writeFileSync(tokenPath, '', { mode: 0o600 });
    if (!fs.readFileSync(tokenPath, 'utf8').trim()) {
        // Run upstream refresh in a disposable worker. On timeout, logged-in
        // requests and QR login remain available through the local API.
        await new Promise(resolve => {
            const worker = spawn(process.execPath,
                ['-e', "require('NeteaseCloudMusicApi/generateConfig')().catch(() => process.exit(1))"],
                { cwd: path.resolve(__dirname, '..'), stdio: 'ignore' });
            const timer = setTimeout(() => {
                console.error('[netease] Anonymous refresh timed out; continuing with local API.');
                worker.kill('SIGKILL');
            }, refreshTimeoutMs);
            worker.once('error', () => { clearTimeout(timer); resolve(); });
            worker.once('close', () => { clearTimeout(timer); resolve(); });
        });
    }
    global.cnIp = require('NeteaseCloudMusicApi/util/index').generateRandomChineseIP();
    return require('NeteaseCloudMusicApi/server').serveNcmApi({
        host: '127.0.0.1', checkVersion: false,
    });
}

module.exports = { start };
if (require.main === module) {
    start().catch(error => {
        console.error('[netease] Local API startup failed:', error.message);
        process.exitCode = 1;
    });
}
