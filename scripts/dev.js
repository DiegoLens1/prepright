const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const root = path.resolve(__dirname, '..');
const backendDir = path.join(root, 'backend');
const frontendDir = path.join(root, 'frontend');

// Find python: prefer venv, fall back to system python
const isWin = process.platform === 'win32';
const venvPy = isWin
  ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
  : path.join(backendDir, '.venv', 'bin', 'python');

const python = fs.existsSync(venvPy) ? venvPy : (isWin ? 'python' : 'python3');

const backend = spawn(python, ['-m', 'uvicorn', 'prepright.main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'], {
  cwd: backendDir,
  stdio: 'inherit',
});

const viteBin = path.join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js');
const frontend = spawn('node', [viteBin], {
  cwd: frontendDir,
  stdio: 'inherit',
});

process.on('SIGINT', () => {
  backend.kill();
  frontend.kill();
  process.exit();
});
