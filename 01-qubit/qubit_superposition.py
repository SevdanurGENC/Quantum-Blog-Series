"""
QBlog #01 — Kübit: Hem 0 Hem 1 / The Qubit: Both 0 and 1

TR: Tek bir kübiti süperpozisyona sokuyor, Bloch küresindeki yerini hesaplıyor
    ve binlerce kez ölçerek olasılıkların nasıl ortaya çıktığını görüyoruz.
EN: We put a single qubit into superposition, find its point on the Bloch
    sphere and measure it thousands of times to watch probabilities emerge.

Çalıştır / Run:  python qubit_superposition.py
"""
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Pauli, Statevector
from qiskit.visualization import plot_bloch_vector
from qiskit_aer import AerSimulator

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)


def bloch_vector(state: Statevector) -> list[float]:
    """TR: Durumun Bloch küresindeki (x, y, z) koordinatı.
    EN: (x, y, z) coordinates of the state on the Bloch sphere."""
    return [float(np.real(state.expectation_value(Pauli(p)))) for p in "XYZ"]


# 1) |0⟩ → H → |+⟩  (eşit süperpozisyon / equal superposition)
qc = QuantumCircuit(1)
qc.h(0)
state = Statevector(qc)
print("Devre / Circuit:")
print(qc.draw())
print("Durum vektörü / State vector:", np.round(state.data, 3))
print("Olasılıklar / Probabilities:",
      {k: round(float(v), 3) for k, v in state.probabilities_dict().items()})
print("Bloch vektörü / Bloch vector:", np.round(bloch_vector(state), 3))

# 2) Ölçüm: aynı deneyi 1000 kez tekrarla / Measure 1000 times
qc.measure_all()
sim = AerSimulator(seed_simulator=42)
counts = sim.run(transpile(qc, sim), shots=1000).result().get_counts()
print("\n1000 ölçüm / 1000 shots:", counts)

# 3) Ry(θ) ile olasılığı sürekli ayarla / Tune the probability with Ry(θ)
print("\n θ (derece/deg) | P(0)  | P(1)")
for deg in [0, 30, 60, 90, 120, 150, 180]:
    c = QuantumCircuit(1)
    c.ry(np.deg2rad(deg), 0)
    p = Statevector(c).probabilities()
    print(f" {deg:>13} | {p[0]:.3f} | {p[1]:.3f}")

# 4) Görseller / Figures
fig = plot_bloch_vector(bloch_vector(state), title="|+⟩ = H|0⟩")
fig.savefig(OUT / "01_bloch_plus.png", dpi=150, bbox_inches="tight")

fig, ax = plt.subplots(figsize=(5, 3.2))
keys = sorted(counts)
ax.bar(keys, [counts[k] for k in keys], color=["#3EE6F0", "#9B7BFF"])
ax.set_title("1000 ölçüm / 1000 measurements")
ax.set_ylabel("Sayı / Count")
fig.tight_layout()
fig.savefig(OUT / "01_counts.png", dpi=150)
print(f"\nGörseller kaydedildi / Figures saved → {OUT}")
