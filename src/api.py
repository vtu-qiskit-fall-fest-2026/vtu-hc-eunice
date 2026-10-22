"""
Q-Catalyst Cloud Microservice & Interactive Web Dashboard.
Exposes Qiskit Variational Quantum Eigensolver (VQE) workflows via REST endpoints
and an interactive browser UI for Direct Air Carbon Capture (DAC) screening.
"""

from __future__ import annotations
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.circuit import MOLECULE_CATALOGUE
from src.optimizer import run_vqe_simulation, scan_potential_energy_surface

app = FastAPI(
    title="Q-Catalyst: Quantum Cloud VQE API",
    description="Team Eunice (VTU-QFF-HC-0145) | Track 6: Climate Change & Sustainability",
    version="1.0.0",
)


class VQERequest(BaseModel):
    molecule_key: str = Field(default="CO2_Amine", description="Target molecule key")
    bond_distance: Optional[float] = Field(default=None, description="Interatomic distance in Angstroms")
    reps: int = Field(default=2, ge=1, le=4, description="EfficientSU2 ansatz repetitions")
    maxiter: int = Field(default=100, ge=20, le=250, description="COBYLA maximum iterations")


@app.get("/api/molecules")
def list_molecules():
    return {"molecules": MOLECULE_CATALOGUE}


@app.post("/api/vqe/simulate")
def simulate_molecule(req: VQERequest):
    if req.molecule_key not in MOLECULE_CATALOGUE:
        raise HTTPException(status_code=400, detail=f"Unknown molecule: {req.molecule_key}")
    return run_vqe_simulation(
        molecule_key=req.molecule_key,
        bond_distance=req.bond_distance,
        reps=req.reps,
        maxiter=req.maxiter,
    )


@app.get("/api/vqe/pes/{molecule_key}")
def get_pes_curve(molecule_key: str, num_points: int = 8, reps: int = 2):
    if molecule_key not in MOLECULE_CATALOGUE:
        raise HTTPException(status_code=400, detail=f"Unknown molecule: {molecule_key}")
    return {
        "molecule_key": molecule_key,
        "surface": scan_potential_energy_surface(molecule_key, num_points=num_points, reps=reps),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Q-Catalyst | Quantum VQE Carbon Capture Cloud</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
  <header class="border-b border-emerald-500/30 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
    <div class="max-w-7xl mx-auto px-6 py-4 flex flex-wrap justify-between items-center gap-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="px-2.5 py-1 text-xs font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 rounded-full">Track 6: Climate & Sustainability</span>
          <span class="px-2.5 py-1 text-xs font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 rounded-full">Team Eunice ? VTU-QFF-HC-0145</span>
        </div>
        <h1 class="text-2xl font-extrabold mt-1 bg-gradient-to-r from-emerald-400 via-teal-200 to-indigo-400 bg-clip-text text-transparent">
          Q-Catalyst: Cloud VQE Screening for Direct Air Carbon Capture (DAC)
        </h1>
      </div>
      <button onclick="runSimulation()" id="runBtn" class="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg shadow-lg shadow-emerald-500/20 transition">
        ? Execute Quantum VQE Circuit
      </button>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-6 space-y-6">
    <!-- Controls -->
    <section class="grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-900/90 border border-slate-800 p-5 rounded-xl">
      <div>
        <label class="block text-xs uppercase text-slate-400 font-semibold mb-1">Target DAC Candidate Complex</label>
        <select id="moleculeSelect" onchange="updateDefaultDistance()" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-emerald-300 font-medium">
          <option value="CO2_Amine">CO2-Amine (MOF Functionalized Site - 4Q)</option>
          <option value="Mg_MOF74_CO2">Mg-MOF-74--CO2 (Open Metal Site - 4Q)</option>
          <option value="LiH">LiH (Alkali Hydride Sorbent - 4Q)</option>
          <option value="H2">H2 (Calibration Benchmark - 2Q)</option>
        </select>
      </div>
      <div>
        <label class="block text-xs uppercase text-slate-400 font-semibold mb-1">Interatomic Distance (?): <span id="distVal" class="text-emerald-400 font-mono">1.48</span></label>
        <input type="range" id="distanceInput" min="0.50" max="2.80" step="0.05" value="1.48" oninput="document.getElementById('distVal').innerText=this.value" class="w-full accent-emerald-400 mt-2" />
      </div>
      <div>
        <label class="block text-xs uppercase text-slate-400 font-semibold mb-1">EfficientSU2 Ansatz Reps</label>
        <select id="repsInput" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm">
          <option value="1">1 Layer (Shallow NISQ)</option>
          <option value="2" selected>2 Layers (Balanced Hardware-Efficient)</option>
          <option value="3">3 Layers (Deep Expressibility)</option>
        </select>
      </div>
      <div>
        <label class="block text-xs uppercase text-slate-400 font-semibold mb-1">COBYLA Max Iterations</label>
        <input type="number" id="maxiterInput" value="110" min="30" max="220" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono" />
      </div>
    </section>

    <!-- KPI Cards -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <div class="text-xs text-slate-400 uppercase">VQE Ground-State Energy</div>
        <div id="kpiVqe" class="text-2xl font-mono font-bold text-emerald-400 mt-1">-- Ha</div>
        <div id="kpiExact" class="text-xs text-slate-400 mt-1">Exact FCI: -- Ha</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <div class="text-xs text-slate-400 uppercase">Quantum Error vs. Exact FCI</div>
        <div id="kpiError" class="text-2xl font-mono font-bold text-teal-300 mt-1">-- mHa</div>
        <div id="kpiAcc" class="text-xs text-slate-400 mt-1">Threshold: 1.6 mHa (Chemical Accuracy)</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <div class="text-xs text-slate-400 uppercase">CO2 Binding Enthalpy (?H)</div>
        <div id="kpiEnthalpy" class="text-2xl font-mono font-bold text-indigo-400 mt-1">-- kJ/mol</div>
        <div id="kpiRole" class="text-xs text-slate-400 mt-1 truncate">--</div>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <div class="text-xs text-slate-400 uppercase">Transpiled Qiskit Circuit</div>
        <div id="kpiCircuit" class="text-2xl font-mono font-bold text-amber-300 mt-1">-- Qubits / Depth --</div>
        <div id="kpiTime" class="text-xs text-slate-400 mt-1">Execution Latency: -- ms</div>
      </div>
    </section>

    <!-- Verdict Banner -->
    <div id="verdictBanner" class="bg-emerald-950/40 border border-emerald-500/40 rounded-xl p-4 text-sm font-medium text-emerald-200">
      Select a molecule and click <b>Execute Quantum VQE Circuit</b> to screen carbon-capture binding thermodynamics.
    </div>

    <!-- Charts -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-slate-900 border border-slate-800 p-5 rounded-xl">
        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">VQE Energy Convergence Trajectory (COBYLA)</h2>
        <canvas id="convergenceChart" height="140"></canvas>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-5 rounded-xl">
        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-300 mb-3">AerSimulator Quantum Basis State Probabilities</h2>
        <canvas id="probChart" height="140"></canvas>
      </div>
    </section>

    <!-- Qiskit Circuit Diagram -->
    <section class="bg-slate-900 border border-slate-800 p-5 rounded-xl">
      <div class="flex justify-between items-center mb-3">
        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-300">Transpiled Qiskit EfficientSU2 Variational Circuit</h2>
        <span id="gateStats" class="text-xs font-mono text-emerald-400"></span>
      </div>
      <pre id="circuitBox" class="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs font-mono text-emerald-300 overflow-x-auto leading-relaxed">Loading quantum circuit...</pre>
    </section>
  </main>

  <script>
    const defaultDistances = { CO2_Amine: 1.48, Mg_MOF74_CO2: 2.05, LiH: 1.60, H2: 0.74 };
    let convChart = null;
    let probChart = null;

    function updateDefaultDistance() {
      const mol = document.getElementById('moleculeSelect').value;
      const d = defaultDistances[mol] || 1.48;
      document.getElementById('distanceInput').value = d;
      document.getElementById('distVal').innerText = d;
    }

    async function runSimulation() {
      const btn = document.getElementById('runBtn');
      btn.disabled = true;
      btn.innerText = '? Running Qiskit VQE...';

      const payload = {
        molecule_key: document.getElementById('moleculeSelect').value,
        bond_distance: parseFloat(document.getElementById('distanceInput').value),
        reps: parseInt(document.getElementById('repsInput').value),
        maxiter: parseInt(document.getElementById('maxiterInput').value),
      };

      try {
        const res = await fetch('/api/vqe/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();

        document.getElementById('kpiVqe').innerText = data.vqe_ground_energy_ha.toFixed(6) + ' Ha';
        document.getElementById('kpiExact').innerText = 'Exact FCI: ' + data.exact_fci_energy_ha.toFixed(6) + ' Ha';
        document.getElementById('kpiError').innerText = data.energy_error_mha.toFixed(3) + ' mHa';
        document.getElementById('kpiEnthalpy').innerText = data.binding_enthalpy_kj_mol.toFixed(2) + ' kJ/mol';
        document.getElementById('kpiRole').innerText = data.dac_role;
        document.getElementById('kpiCircuit').innerText = data.circuit_profile.num_qubits + 'Q / Depth ' + data.circuit_profile.circuit_depth;
        document.getElementById('kpiTime').innerText = 'Latency: ' + data.execution_time_ms.toFixed(1) + ' ms (' + data.iterations + ' iters)';
        document.getElementById('verdictBanner').innerHTML = '<b>DAC Thermodynamic Verdict (' + data.formula + '):</b> ' + data.dac_verdict;
        document.getElementById('circuitBox').innerText = data.circuit_profile.circuit_diagram;
        document.getElementById('gateStats').innerText = 'Parameters: ' + data.circuit_profile.num_parameters + ' | CX Gates: ' + data.circuit_profile.cx_gates + ' | Total Gates: ' + data.circuit_profile.total_gates;

        // Update Convergence Chart
        const labels = data.convergence_history.map(p => p.iteration);
        const energies = data.convergence_history.map(p => p.energy_ha);
        const exacts = data.convergence_history.map(p => p.exact_ha);

        if (convChart) convChart.destroy();
        convChart = new Chart(document.getElementById('convergenceChart'), {
          type: 'line',
          data: {
            labels,
            datasets: [
              { label: 'Qiskit VQE Energy (Ha)', data: energies, borderColor: '#34d399', borderWidth: 2, pointRadius: 0, tension: 0.2 },
              { label: 'Exact FCI Reference (Ha)', data: exacts, borderColor: '#818cf8', borderDash: [6, 4], borderWidth: 2, pointRadius: 0 }
            ]
          },
          options: { plugins: { legend: { labels: { color: '#cbd5e1' } } }, scales: { x: { ticks: { color: '#94a3b8' } }, y: { ticks: { color: '#94a3b8' } } } }
        });

        // Update State Probability Chart
        const stateKeys = Object.keys(data.state_probabilities).slice(0, 8);
        const stateVals = stateKeys.map(k => data.state_probabilities[k]);

        if (probChart) probChart.destroy();
        probChart = new Chart(document.getElementById('probChart'), {
          type: 'bar',
          data: {
            labels: stateKeys.map(k => '|' + k + '?'),
            datasets: [{ label: 'Measurement Probability', data: stateVals, backgroundColor: '#38bdf8' }]
          },
          options: { plugins: { legend: { labels: { color: '#cbd5e1' } } }, scales: { x: { ticks: { color: '#94a3b8' } }, y: { beginAtZero: true, max: 1.0, ticks: { color: '#94a3b8' } } } }
        });
      } finally {
        btn.disabled = false;
        btn.innerText = '? Execute Quantum VQE Circuit';
      }
    }

    window.onload = runSimulation;
  </script>
</body>
</html>"""
