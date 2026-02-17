let chart;

/* ===== LOAD STATS ===== */
async function loadStats() {
  const res = await fetch("/api/stats");
  const data = await res.json();

  document.getElementById("totalFindings").innerText = data.total_findings;
  document.getElementById("criticalIssues").innerText = data.critical_issues;
  document.getElementById("observations").innerText = data.observations;
  document.getElementById("riskScore").innerText = data.risk_score;
  document.getElementById("confidence").innerText = data.confidence + "%";

  drawChart(data.history || [10,20,30,40,50]);
}

/* ===== DRAW CHART ===== */
function drawChart(values) {
  const ctx = document.getElementById("riskChart");

  if (chart) chart.destroy();

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: ["Jan","Feb","Mar","Apr","May"],
      datasets: [{
        label: "Risk Trend",
        data: values,
        tension: 0.3
      }]
    }
  });
}

/* ===== UPLOAD FINDINGS ===== */
async function uploadFindings() {
  const files = document.getElementById("fileInput").files;

  const formData = new FormData();
  for (let f of files) formData.append("files", f);

  const res = await fetch("/api/upload-findings", {
    method: "POST",
    body: formData
  });

  await res.json();
  loadStats();
}

/* ===== CHAT ===== */
async function sendChat() {
  const text = document.getElementById("chatText").value;

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message: text})
  });

  const data = await res.json();

  const box = document.getElementById("chatMessages");
  box.innerHTML += `<p><b>You:</b> ${text}</p>`;
  box.innerHTML += `<p><b>AI:</b> ${data.response}</p>`;

  document.getElementById("chatText").value = "";
}

window.onload = loadStats;
