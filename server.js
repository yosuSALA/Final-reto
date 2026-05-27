/* ═══════════════════════════════════════════════════════
   SERVER — Express static file server
   Serves the SPA frontend and proxies /api calls to the
   FastAPI backend running on port 8000.
   ═══════════════════════════════════════════════════════ */

import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app  = express();
const PORT = process.env.PORT || 3000;
const API_TARGET = process.env.API_URL || 'http://localhost:8000';

// ── API Proxy ────────────────────────────────────────────
// Forward /api/* requests to the FastAPI backend so the
// browser never needs to hit port 8000 directly.
app.use('/api', createProxyMiddleware({
    target: API_TARGET,
    changeOrigin: true,
    pathRewrite: { '^/api': '/api' },
}));

// ── Static Assets ────────────────────────────────────────
app.use(express.static(path.join(__dirname, 'public')));

// ── SPA Fallback ─────────────────────────────────────────
// Return index.html for any non-asset route so hash-routing
// works correctly when the user refreshes the page.
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`✅  Auditor Agéntico running at http://localhost:${PORT}`);
    console.log(`    API proxy → ${API_TARGET}/api`);
});
