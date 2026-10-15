// The only bridge between the web panel and Windows. Exposes a few safe actions, nothing else.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("missionDesktop", {
  isDesktop: true,
  focus: hash => ipcRenderer.send("mc:focus", hash),       // bring window to front (e.g. clicking a notification)
  setBadge: count => ipcRenderer.send("mc:badge", count),   // "N to approve" in the tray tooltip
  setUrl: url => ipcRenderer.invoke("mc:set-url", url),
  getUrl: () => ipcRenderer.invoke("mc:get-url"),
  retry: url => ipcRenderer.invoke("mc:retry", url),
});
