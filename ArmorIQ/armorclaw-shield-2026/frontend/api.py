from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from logs.audit_logger import get_recent_logs, get_log_stats
from enforcement.policy_loader import get_all_policies
import uvicorn

app = FastAPI(title="ArmorClaw Shield Dashboard")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/api/logs")
def api_logs(limit: int = 50):
    return get_recent_logs(min(limit, 100))

@app.get("/api/stats")
def api_stats():
    return get_log_stats()

@app.get("/api/policies")
def api_policies():
    return get_all_policies()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!DOCTYPE html>
<html><head><title>ArmorClaw Shield</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui; background: #0f0f0f; color: #e5e5e5; padding: 24px; }
  h1 { font-size: 20px; font-weight: 500; margin-bottom: 20px; color: #fff; }
  .stats { display: flex; gap: 16px; margin-bottom: 24px; }
  .stat { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 16px 24px; flex: 1; }
  .stat-val { font-size: 28px; font-weight: 600; }
  .stat-label { font-size: 12px; color: #888; margin-top: 4px; }
  .green { color: #4ade80; } .red { color: #f87171; } .blue { color: #60a5fa; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 10px 12px; background: #1a1a1a; color: #888; font-weight: 400; border-bottom: 1px solid #2a2a2a; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e1e1e; }
  tr:hover td { background: #1a1a1a; }
  .allow { color: #4ade80; font-weight: 500; }
  .block { color: #f87171; font-weight: 500; }
  .ts { color: #555; font-size: 11px; }
</style></head><body>
<h1>ArmorClaw Shield — Enforcement Dashboard</h1>
<div class="stats" id="stats"></div>
<table><thead><tr>
  <th>Time</th><th>Verdict</th><th>Intent</th><th>Policy</th><th>Reason</th>
</tr></thead><tbody id="logs"></tbody></table>
<script>
async function load() {
  const [stats, logs] = await Promise.all([
    fetch('/api/stats').then(r => r.json()),
    fetch('/api/logs?limit=50').then(r => r.json())
  ]);
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="stat-val blue">${stats.total}</div><div class="stat-label">Total decisions</div></div>
    <div class="stat"><div class="stat-val green">${stats.allowed}</div><div class="stat-label">Allowed</div></div>
    <div class="stat"><div class="stat-val red">${stats.blocked}</div><div class="stat-label">Blocked</div></div>
    <div class="stat"><div class="stat-val">${stats.block_rate}%</div><div class="stat-label">Block rate</div></div>`;
  document.getElementById('logs').innerHTML = logs.map(r => `
    <tr>
      <td class="ts">${r.timestamp?.slice(11,19) || ''}</td>
      <td class="${r.verdict?.toLowerCase()}">${r.verdict}</td>
      <td>${r.intent_type || ''}</td>
      <td class="ts">${r.policy_id || '—'} ${r.policy_name ? '· ' + r.policy_name : ''}</td>
      <td class="ts">${(r.reason || '').slice(0, 80)}</td>
    </tr>`).join('');
}
load();
setInterval(load, 3000);
</script></body></html>"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)