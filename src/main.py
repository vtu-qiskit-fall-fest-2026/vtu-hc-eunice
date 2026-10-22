"""
Q-Catalyst Main Entry Point.
"""

from __future__ import annotations
from src.circuit import MOLECULE_CATALOGUE
from src.optimizer import run_vqe_simulation


def main() -> None:
    print("=" * 88)
    print(" Q-CATALYST: QUANTUM VQE SCREENING FOR DIRECT AIR CARBON CAPTURE (DAC)")
    print(" Team Eunice (VTU-QFF-HC-0145) | Track 6: Climate Change & Sustainability")
    print("=" * 88)

    header = (
        f"{'Molecule':<15} | {'Qubits':<6} | {'R (A)':<6} | "
        f"{'VQE (Ha)':<12} | {'Exact FCI (Ha)':<14} | {'Err (mHa)':<9} | {'Time (ms)':<9}"
    )
    print(header)
    print("-" * 88)

    for key in MOLECULE_CATALOGUE:
        result = run_vqe_simulation(molecule_key=key, reps=2, maxiter=110)
        print(
            f"{key:<15} | "
            f"{result['circuit_profile']['num_qubits']:<6} | "
            f"{result['bond_distance_angstrom']:<6.3f} | "
            f"{result['vqe_ground_energy_ha']:<12.6f} | "
            f"{result['exact_fci_energy_ha']:<14.6f} | "
            f"{result['energy_error_mha']:<9.4f} | "
            f"{result['execution_time_ms']:<9.1f}"
        )

    print("-" * 88)
    featured = run_vqe_simulation(molecule_key="CO2_Amine", reps=2, maxiter=120)
    print(f"\n[Featured DAC Complex: {featured['molecule_name']}]")
    print(f"  * Equilibrium Bond Distance : {featured['bond_distance_angstrom']} A")
    print(f"  * VQE Ground-State Energy   : {featured['vqe_ground_energy_ha']} Ha")
    print(f"  * Exact FCI Reference       : {featured['exact_fci_energy_ha']} Ha")
    print(f"  * Chemical Accuracy (<1.6)  : {'PASSED' if featured['chemical_accuracy_met'] else 'NEAR'} ({featured['energy_error_mha']} mHa)")
    print(f"  * Dominant Quantum States   : {dict(list(featured['state_probabilities'].items())[:4])}")
    print(f"  * DAC Thermodynamic Verdict : {featured['dac_verdict']}")
    print("\n[Transpiled Qiskit Circuit Diagram (CO2_Amine - 4 Qubits)]:")
    print(featured["circuit_profile"]["circuit_diagram"])
    print("=" * 88)


if __name__ == "__main__":
    main()
