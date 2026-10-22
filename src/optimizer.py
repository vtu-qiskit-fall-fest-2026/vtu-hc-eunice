"""
Q-Catalyst Variational Quantum Eigensolver (VQE) & Carbon Capture Analytics.
"""

from __future__ import annotations
import time
from typing import Dict, Any, List
import numpy as np
from scipy.optimize import minimize

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator

from src.circuit import (
    MOLECULE_CATALOGUE,
    build_molecular_hamiltonian,
    build_ansatz,
    profile_transpiled_circuit,
)

HARTREE_TO_KJ_MOL = 2625.499639


def compute_exact_ground_state(hamiltonian: SparsePauliOp, nuclear_repulsion: float) -> float:
    mat = hamiltonian.to_matrix()
    eigenvalues = np.linalg.eigvalsh(mat)
    electronic_ground = float(np.real(eigenvalues[0]))
    return electronic_ground + nuclear_repulsion


def sample_optimal_state_probabilities(
    bound_circuit: QuantumCircuit, shots: int = 2048
) -> Dict[str, float]:
    meas_qc = bound_circuit.copy()
    meas_qc.measure_all()
    simulator = AerSimulator()
    job = simulator.run(meas_qc, shots=shots, seed_simulator=42)
    counts = job.result().get_counts()
    total = sum(counts.values())
    sorted_probs = {
        k: round(v / total, 4)
        for k, v in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    }
    return sorted_probs


def run_vqe_simulation(
    molecule_key: str = "CO2_Amine",
    bond_distance: float | None = None,
    reps: int = 2,
    maxiter: int = 110,
    seed: int = 42,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    hamiltonian, nuclear_repulsion, meta = build_molecular_hamiltonian(molecule_key, bond_distance)
    actual_distance = float(bond_distance) if bond_distance is not None else meta["eq_distance"]

    ansatz = build_ansatz(
        num_qubits=meta["num_qubits"],
        reps=reps,
        entanglement="linear",
        hf_state=meta["hf_state"],
    )

    exact_energy = compute_exact_ground_state(hamiltonian, nuclear_repulsion)

    convergence_history: List[Dict[str, float]] = []
    rng = np.random.default_rng(seed)
    initial_params = rng.normal(0.0, 0.22, size=ansatz.num_parameters)

    def cost_function(params: np.ndarray) -> float:
        bound_qc = ansatz.assign_parameters(params)
        sv = Statevector.from_instruction(bound_qc)
        electronic_energy = float(np.real(sv.expectation_value(hamiltonian)))
        total_energy = electronic_energy + nuclear_repulsion
        convergence_history.append(
            {
                "iteration": len(convergence_history) + 1,
                "energy_ha": round(total_energy, 6),
                "exact_ha": round(exact_energy, 6),
                "error_mha": round(abs(total_energy - exact_energy) * 1000.0, 4),
            }
        )
        return total_energy

    opt_result = minimize(
        cost_function,
        initial_params,
        method="COBYLA",
        options={"maxiter": maxiter, "rhobeg": 0.25, "tol": 1e-6},
    )

    optimal_params = opt_result.x
    vqe_energy = float(opt_result.fun)
    error_mha = abs(vqe_energy - exact_energy) * 1000.0
    chemical_accuracy_met = bool(error_mha <= 1.6)

    # Binding energy relative to dissociated asymptote
    binding_energy_ha = vqe_energy - meta["asymptote_ha"]
    binding_enthalpy_kj_mol = binding_energy_ha * HARTREE_TO_KJ_MOL

    optimal_qc = ansatz.assign_parameters(optimal_params)
    state_probs = sample_optimal_state_probabilities(optimal_qc, shots=2048)
    circuit_profile = profile_transpiled_circuit(ansatz)

    abs_kj = abs(binding_enthalpy_kj_mol)
    if 35.0 <= abs_kj <= 95.0:
        dac_verdict = "OPTIMAL DAC SORBENT (Low Regeneration Thermal Penalty < 100 C)"
    elif abs_kj > 95.0:
        dac_verdict = "STRONG CHEMISORPTION (High Capture Rate; High Regeneration Energy)"
    else:
        dac_verdict = "WEAK PHYSISORPTION (Fast Desorption; Best for High-Pressure Flue Gas)"

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "molecule_key": molecule_key,
        "molecule_name": meta["name"],
        "formula": meta["formula"],
        "dac_role": meta["dac_role"],
        "bond_distance_angstrom": round(actual_distance, 3),
        "vqe_ground_energy_ha": round(vqe_energy, 6),
        "exact_fci_energy_ha": round(exact_energy, 6),
        "energy_error_mha": round(error_mha, 4),
        "chemical_accuracy_met": chemical_accuracy_met,
        "binding_enthalpy_kj_mol": round(binding_enthalpy_kj_mol, 2),
        "dac_verdict": dac_verdict,
        "iterations": len(convergence_history),
        "execution_time_ms": round(elapsed_ms, 2),
        "state_probabilities": state_probs,
        "circuit_profile": circuit_profile,
        "convergence_history": convergence_history,
    }


def scan_potential_energy_surface(
    molecule_key: str = "CO2_Amine", num_points: int = 9, reps: int = 2
) -> List[Dict[str, float]]:
    meta = MOLECULE_CATALOGUE[molecule_key]
    distances = np.linspace(meta["min_distance"], meta["max_distance"], num_points)
    surface_points: List[Dict[str, float]] = []

    for d in distances:
        res = run_vqe_simulation(
            molecule_key=molecule_key,
            bond_distance=float(d),
            reps=reps,
            maxiter=75,
        )
        surface_points.append(
            {
                "distance_angstrom": round(float(d), 3),
                "vqe_energy_ha": res["vqe_ground_energy_ha"],
                "exact_energy_ha": res["exact_fci_energy_ha"],
                "error_mha": res["energy_error_mha"],
            }
        )
    return surface_points
