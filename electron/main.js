/* Claudio Desktop — Electron main process */
const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const BASE = path.join(__dirname, "..");

let neteaseProc = null;
let flaskProc = null;

function startBackend() {
  neteaseProc = spawn("node", ["node_modules/NeteaseCloudMusicApi/app.js"], { cwd: BASE, stdio: "ignore" });
  flaskProc = spawn(path.join(BASE, ".venv", "Scripts", "python.exe"), ["app.py"], { cwd: BASE, stdio: "ignore" });
}

function stopBackend() {
  if (neteaseProc) { neteaseProc.kill(); neteaseProc = null; }
  if (flaskProc) { flaskProc.kill(); flaskProc = null; }
}

function waitForServer(port, retries) {
  retries = retries || 40;
  return new Promise(function (resolve) {
    var net = require("net");
    function check() {
      var s = net.connect(port, "127.0.0.1");
      s.on("connect", function () { s.destroy(); resolve(true); });
      s.on("error", function () {
        if (--retries > 0) setTimeout(check, 500);
        else resolve(false);
      });
    }
    check();
  });
}

app.whenReady().then(async function () {
  startBackend();

  var neteaseOk = await waitForServer(3000);
  if (!neteaseOk) { console.error("Netease API failed"); app.quit(); return; }
  console.log("Netease API ready");

  var flaskOk = await waitForServer(8080);
  if (!flaskOk) { console.error("Flask failed"); app.quit(); return; }
  console.log("Flask ready");

  var win = new BrowserWindow({
    width: 565, height: 1040,
    minWidth: 565, minHeight: 700,
    resizable: true,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  win.loadURL("http://127.0.0.1:8080?desktop=1");

  win.on("closed", function () { stopBackend(); app.quit(); });
});

app.on("window-all-closed", function () { stopBackend(); app.quit(); });
app.on("before-quit", function () { stopBackend(); });
