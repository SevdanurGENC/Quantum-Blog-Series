"""
QBlog #16 — Kuantum Kimya: VQE ile H₂ Molekülü / Quantum Chemistry: The H₂ Molecule with VQE

TR: Varyasyonel Kuantum Özdeğer Çözücü (VQE), bir molekülün en düşük enerjisini
    bulmak için ayarlanabilir bir kuantum devresini klasik optimizasyonla
    birleştirir. H₂'nin bağ uzunluğuna göre enerji eğrisini çizip "tam" çözümle
    karşılaştırıyoruz.
EN: The Variational Quantum Eigensolver (VQE) combines a tunable quantum circuit
    with classical optimisation to find a molecule's lowest energy. We trace H₂'s
    energy versus bond length and compare with the exact answer.

Çalıştır / Run:  python vqe_h2.py      (~1 dk / ~1 min)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

OUT = Path(__file__).parent / "output"
HARTREE_TO_KCAL = 627.509
BOND_LENGTHS = [0.5, 0.6, 0.7, 0.74, 0.8, 0.9, 1.0, 1.2, 1.5, 1.8, 2.1]   # Ångström


def hamiltonian(d_angstrom: float):
    coords = np.array([0.0, 0.0, 0.0, 0.0, 0.0, d_angstrom / 0.529177])      # → Bohr
    mol = qml.qchem.Molecule(["H", "H"], coords)
    H, n_qubits = qml.qchem.molecular_hamiltonian(mol)
    return H, n_qubits


def vqe(H, n_qubits, steps=60):
    hf = qml.qchem.hf_state(2, n_qubits)                 # Hartree–Fock: |1100⟩
    dev = qml.device("default.qubit", wires=n_qubits)

    @qml.qnode(dev)
    def energy(theta):
        qml.BasisState(hf, wires=range(n_qubits))
        qml.DoubleExcitation(theta, wires=[0, 1, 2, 3])  # iki elektronu birlikte uyar / excite both electrons
        return qml.expval(H)

    theta = pnp.array(0.0, requires_grad=True)
    opt = qml.GradientDescentOptimizer(0.4)
    history = [float(energy(theta))]
    for _ in range(steps):
        theta = opt.step(energy, theta)
        history.append(float(energy(theta)))
    return history[-1], float(theta), history


def exact(H) -> float:
    return float(np.linalg.eigvalsh(qml.matrix(H)).min())


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    H, nq = hamiltonian(0.74)
    print(f"H₂ @ 0.74 Å → {nq} kübit / qubits, Hamiltonyen'de {len(H)} terim / terms")
    e_vqe, th, hist = vqe(H, nq)
    e_ex = exact(H)
    print(f"Hartree–Fock : {hist[0]: .6f} Ha")
    print(f"VQE          : {e_vqe: .6f} Ha   (θ = {th:.4f})")
    print(f"Tam / Exact  : {e_ex: .6f} Ha")
    print(f"Hata / Error : {abs(e_vqe - e_ex) * HARTREE_TO_KCAL:.2e} kcal/mol "
          f"(kimyasal doğruluk / chemical accuracy < 1.6)")

    print("\n d (Å) |   HF (Ha)  |  VQE (Ha)  | Tam/Exact (Ha)")
    rows = []
    for d in BOND_LENGTHS:
        H, nq = hamiltonian(d)
        e, _, h = vqe(H, nq)
        rows.append((d, h[0], e, exact(H)))
        print(f" {d:>5.2f} | {h[0]: .5f} | {e: .5f} | {rows[-1][3]: .5f}")

    d, hf, ve, ex = map(np.array, zip(*rows))
    print(f"\nEn düşük enerji / Minimum energy at d ≈ {d[np.argmin(ve)]:.2f} Å (deneysel / experiment: 0.74 Å)")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(d, hf, "--", label="Hartree–Fock")
    ax.plot(d, ex, "-", lw=3, alpha=0.4, label="Tam / Exact")
    ax.plot(d, ve, "o", label="VQE")
    ax.set_xlabel("Bağ uzunluğu / Bond length (Å)")
    ax.set_ylabel("Enerji / Energy (Ha)")
    ax.set_title("H₂ enerji eğrisi / energy curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "16_h2_curve.png", dpi=150)
    print(f"Görsel / Figure → {OUT / '16_h2_curve.png'}")
