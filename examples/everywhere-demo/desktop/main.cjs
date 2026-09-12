const { app, BrowserWindow, shell } = require("electron");
function createWindow() {
  const win = new BrowserWindow({
    width: 1160,
    height: 850,
    minWidth: 760,
    minHeight: 600,
    title: "Bob · OneAgent Anywhere",
    backgroundColor: "#eef2e7",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });
  const url = process.env.ONEAGENT_URL || "http://127.0.0.1:3107/desktop";
  const allowedOrigin = new URL(url).origin;
  win.webContents.setWindowOpenHandler(({ url: target }) => {
    if (new URL(target).origin === allowedOrigin)
      void shell.openExternal(target);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, target) => {
    if (new URL(target).origin !== allowedOrigin) event.preventDefault();
  });
  win.loadURL(url);
}
app.whenReady().then(createWindow);
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
