"""
QBlog #02 — Dolanıklık: Ürkütücü Uzaktan Etki / Entanglement: Spooky Action at a Distance

TR: İki kübiti Bell durumuna sokup ölçüyoruz: sonuçlar tek tek rastgele,
    ama birlikte her zaman uyumlu. Dört Bell durumunun hepsini de kuruyoruz.
EN: We entangle two qubits into a Bell state: each result is random on its
    own, yet the pair always agrees. Then we build all four Bell states.

Çalıştır / Run:  python bell_states.py
"""
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, entropy, partial_trace
from qiskit_aer import AerSimulator

sim = AerSimulator(seed_simulator=7)


def bell(kind: str = "Φ+") -> QuantumCircuit:
    """TR/EN: Φ+, Φ-, Ψ+, Ψ- Bell durumları / Bell states."""
    qc = QuantumCircuit(2)
    if kind in ("Ψ+", "Ψ-"):
        qc.x(1)            # |01⟩ ile başla / start from |01⟩
    if kind in ("Φ-", "Ψ-"):
        qc.x(0)            # faz için / for the minus sign
    qc.h(0)                # süperpozisyon / superposition
    qc.cx(0, 1)            # dolanıklık / entanglement
    return qc


# 1) Φ+ = (|00⟩ + |11⟩)/√2
qc = bell("Φ+")
print(qc.draw())
print("Φ+ durumu / state:", Statevector(qc).draw("text"))

# 2) Ölçüm: yalnızca 00 ve 11 çıkar / Only 00 and 11 ever appear
m = qc.copy()
m.measure_all()
counts = sim.run(transpile(m, sim), shots=2000).result().get_counts()
print("\n2000 ölçüm / shots:", counts)

# 3) Tek kübit tek başına tamamen rastgele / Alone, one qubit is pure noise
rho_a = partial_trace(Statevector(qc), [1])
print("Kübit A'nın yoğunluk matrisi / Qubit A density matrix:\n", np.round(rho_a.data.real, 3))
print("Dolanıklık entropisi / Entanglement entropy (bit):", round(entropy(rho_a, base=2), 3))

# 4) Dört Bell durumu / All four Bell states
print("\nDurum | Ölçümler / Measurements")
for kind in ["Φ+", "Φ-", "Ψ+", "Ψ-"]:
    c = bell(kind)
    c.measure_all()
    res = sim.run(transpile(c, sim), shots=1000).result().get_counts()
    print(f"  {kind}  | {dict(sorted(res.items()))}")

# 5) Farklı tabanda da korelasyon / Correlated in the X basis too
x = bell("Φ+")
x.h([0, 1])                       # X tabanında ölç / measure in X basis
x.measure_all()
res = sim.run(transpile(x, sim), shots=2000).result().get_counts()
print("\nX tabanında Φ+ / Φ+ in X basis:", res)
