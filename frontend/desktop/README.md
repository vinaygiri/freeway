# 🖥️ free-coding-models-desktop

This directory contains the desktop wrapper configuration, scripts, and Rust integration for `free-coding-models` using **Tauri v2**.

## 🚀 Architecture & Sidecar Setup

The desktop application wraps the core `free-coding-models` Node.js engine inside a lightweight Tauri native shell.

* **Tauri Wrapper:** Spawns a native system tray / menu bar popover, sets up OS notification triggers, and handles startup/exit events.
* **Sidecar Engine:** The modularized Node.js daemon is compiled into a standalone native executable using **Bun Compile** (as `binaries/fcm-engine`) and bundled directly inside the Tauri application. No system Node.js install is required.
* **Pragmatic Loopback Security:** The sidecar binds strictly to the loopback interface (`127.0.0.1:19280`) for local requests only, preventing local network exposure.

---

## 🛠️ Development & Building

### Prerequisites
1. [Rust and Cargo](https://rustup.rs/) installed.
2. [Bun](https://bun.sh) installed (for compiling the JS sidecar).

### 1. Building the Sidecar
Before launching Tauri, you must compile the Node.js daemon as a native sidecar:
```bash
cd desktop
# Compile the router-daemon using Bun
bun build --compile ../src/router-daemon.js --outfile binaries/fcm-engine
```

### 2. Development Mode
To run the desktop app in interactive development mode with hot-reloading:
```bash
pnpm tauri dev
```

### 3. Production Bundling
To build the final standalone production installer (`.dmg` on macOS, `.msi` on Windows, or `.AppImage` on Linux):
```bash
pnpm tauri build
```
This generates optimized standalone application bundles ready for distribution.

---

## 🔔 Lifecycle Rules

The Desktop application behaves intelligently depending on how it connects to the gateway:
* **Spawned Sidecar (`isDaemonOwner = true`):** If the app spawns its own sidecar daemon on startup, it will gracefully terminate the sidecar when the desktop app is closed.
* **Attached Front-End (`isDaemonOwner = false`):** If the app detects an already running CLI daemon on `localhost:19280`, it reuses that engine and does *not* kill it on exit, ensuring CLI processes are uninterrupted.
