// Mission Control — Windows desktop app.
// Opens your control panel in its own window, lives in the system tray, shows Windows
// notifications when shorts are ready, and can start with Windows.
const { app, BrowserWindow, Tray, Menu, shell, ipcMain, nativeImage, session } = require("electron");
const fs = require("fs");
const path = require("path");

app.setAppUserModelId("com.missioncontrol.app"); // proper Windows notifications + taskbar grouping

const STATE_FILE = () => path.join(app.getPath("userData"), "state.json");
const loadState = () => { try { return JSON.parse(fs.readFileSync(STATE_FILE(), "utf8")); } catch { return {}; } };
const saveState = s => { try { fs.writeFileSync(STATE_FILE(), JSON.stringify({ ...loadState(), ...s }, null, 1)); } catch {} };

// Panel address: baked in at build time (config.json), or entered on first run.
function panelUrl() {
  const s = loadState();
  if (s.url) return s.url;
  try { return JSON.parse(fs.readFileSync(path.join(__dirname, "config.json"), "utf8")).url || ""; } catch { return ""; }
}
const validUrl = u => /^https:\/\/[^\s/]+\.[^\s/]+/i.test(u || "");

let win = null, tray = null, quitting = false;
const startHidden = process.argv.includes("--hidden");

const gotLock = app.requestSingleInstanceLock();   // opening it twice just brings the window forward
if (!gotLock) app.quit();
app.on("second-instance", () => show());

function show() {
  if (!win) return createWindow();
  if (win.isMinimized()) win.restore();
  win.show(); win.focus();
}

function openPanel(hash = "") {
  const url = panelUrl();
  if (!validUrl(url)) return win.loadFile(path.join(__dirname, "setup.html"));
  win.loadURL(url.replace(/#.*$/, "") + hash).catch(() => {});
}

function createWindow() {
  const s = loadState();
  const bounds = s.bounds || { width: 1180, height: 820 };
  win = new BrowserWindow({
    ...bounds, minWidth: 380, minHeight: 560, show: false, backgroundColor: "#fbf6f0",
    title: "Mission Control", icon: path.join(__dirname, "build", "icon.png"), autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true },
  });
  if (s.maximized) win.maximize();
  win.setMenuBarVisibility(false);
  win.once("ready-to-show", () => { if (!startHidden) win.show(); });

  // Remember size/position.
  const remember = () => { if (!win.isMinimized()) saveState({ bounds: win.getNormalBounds(), maximized: win.isMaximized() }); };
  win.on("resize", remember); win.on("move", remember);

  // Closing the window keeps the app running in the tray (so notifications keep arriving).
  win.on("close", e => {
    if (quitting || loadState().quitOnClose) return;
    e.preventDefault(); win.hide();
    if (!loadState().trayHintShown) {
      tray?.displayBalloon?.({ title: "Mission Control is still running", content: "It's in the tray so you get notified when shorts are ready. Right-click the icon to quit." });
      saveState({ trayHintShown: true });
    }
  });

  // Links to other sites (YouTube, GitHub, Google sign-in for "Connect YouTube") open in your normal browser.
  const isPanel = u => { try { return new URL(u).origin === new URL(panelUrl()).origin; } catch { return false; } };
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (isPanel(url)) { win.loadURL(url); return { action: "deny" }; }
    shell.openExternal(url); return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e, url) => {
    if (url.startsWith("file:") || isPanel(url)) return;
    e.preventDefault(); shell.openExternal(url);
  });

  // No internet / panel down → friendly retry screen.
  win.webContents.on("did-fail-load", (_e, code, _desc, url, isMain) => {
    if (!isMain || code === -3) return; // -3 = aborted navigation, harmless
    win.loadFile(path.join(__dirname, "offline.html"), { query: { url: url || panelUrl() } });
  });

  // Keyboard: F5 reload, Ctrl+Shift+I developer tools, Ctrl+N new shorts.
  win.webContents.on("before-input-event", (e, input) => {
    if (input.type !== "keyDown") return;
    if (input.key === "F5") { e.preventDefault(); win.webContents.reload(); }
    if (input.control && input.shift && input.key.toLowerCase() === "i") win.webContents.toggleDevTools();
  });

  openPanel();
}

function trayIcon() {
  const img = nativeImage.createFromPath(path.join(__dirname, "build", "tray.png"));
  return img.isEmpty() ? nativeImage.createFromPath(path.join(__dirname, "build", "icon.png")).resize({ width: 16, height: 16 }) : img;
}

function buildTray() {
  tray = new Tray(trayIcon());
  tray.setToolTip("Mission Control");
  const menu = () => Menu.buildFromTemplate([
    { label: "Open Mission Control", click: () => show() },
    { label: "Shorts to approve", click: () => { show(); openPanel("#/shorts"); } },
    { label: "Channels", click: () => { show(); openPanel("#/channels"); } },
    { type: "separator" },
    { label: "Start with Windows", type: "checkbox", checked: app.getLoginItemSettings().openAtLogin,
      click: item => app.setLoginItemSettings({ openAtLogin: item.checked, args: ["--hidden"] }) },
    { label: "Keep running when closed", type: "checkbox", checked: !loadState().quitOnClose,
      click: item => saveState({ quitOnClose: !item.checked }) },
    { label: "Change panel address…", click: () => { show(); win.loadFile(path.join(__dirname, "setup.html")); } },
    { type: "separator" },
    { label: "Quit", click: () => { quitting = true; app.quit(); } },
  ]);
  tray.setContextMenu(menu());
  tray.on("right-click", () => tray.setContextMenu(menu()));
  tray.on("click", () => show());
}

// From the setup / offline screens.
ipcMain.handle("mc:set-url", (_e, url) => {
  url = String(url || "").trim();
  if (!/^https?:\/\//i.test(url)) url = "https://" + url;
  if (!validUrl(url)) return { ok: false, error: "That doesn't look like a web address" };
  saveState({ url: url.replace(/\/?(#.*)?$/, "/") });
  openPanel();
  return { ok: true };
});
ipcMain.handle("mc:get-url", () => panelUrl());
ipcMain.handle("mc:retry", (_e, url) => { if (validUrl(url)) win.loadURL(url); else openPanel(); });
ipcMain.on("mc:focus", (_e, hash) => { show(); if (hash) win.webContents.executeJavaScript(`location.hash=${JSON.stringify(hash)}`).catch(() => {}); });
ipcMain.on("mc:badge", (_e, count) => {
  tray?.setToolTip(count ? `Mission Control — ${count} to approve` : "Mission Control");
  win?.setOverlayIcon?.(null, "");
  if (count && process.platform === "win32") win?.flashFrame?.(!win.isFocused());
});

app.whenReady().then(() => {
  if (!gotLock) return;
  // Allow the panel to show Windows notifications; deny camera/mic/etc.
  session.defaultSession.setPermissionRequestHandler((_wc, perm, cb) => cb(perm === "notifications" || perm === "clipboard-sanitized-write"));
  buildTray();
  createWindow();
});
app.on("before-quit", () => { quitting = true; });
app.on("window-all-closed", () => { /* stay in tray */ });
