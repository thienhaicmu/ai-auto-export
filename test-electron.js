"use strict";
const electron = require("electron");
console.log("electron type:", typeof electron);
console.log("electron.app type:", typeof electron.app);
console.log("electron keys:", Object.keys(electron || {}).slice(0, 8).join(", "));
if (electron && electron.app) {
  electron.app.whenReady().then(() => {
    console.log("APP READY - SUCCESS");
    electron.app.quit();
  });
} else {
  console.error("electron.app is undefined! electron =", electron);
  process.exit(1);
}
