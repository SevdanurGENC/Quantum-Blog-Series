"""
QBlog #03 — Kuantum Işınlanma / Quantum Teleportation

TR: Alice'in bilinmeyen kübit durumunu, yalnızca 2 klasik bit ve paylaşılan
    bir Bell çifti kullanarak Bob'a aktarıyoruz. Önce koşullu (dinamik)
    devre, sonra ertelenmiş ölçüm sürümü ile sonucu doğruluyoruz.
EN: We move Alice's unknown qubit state to Bob using just 2 classical bits
    and a shared Bell pair — first with a dynamic circuit, then verify with
    the deferred-measurement version.

Çalıştır / Run:  python teleportation.py
"""
import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import Statevector, partial_trace, state_fidelity
from qiskit_aer import AerSimulator

rng = np.random.default_rng(3)
theta, phi = rng.uniform(0, np.pi), rng.uniform(0, 2 * np.pi)
print(f"Gizli durum / Secret state: θ={theta:.3f}, φ={phi:.3f}")

target = QuantumCircuit(1)
target.u(theta, phi, 0, 0)
psi = Statevector(target)


def prepare(qc: QuantumCircuit, q) -> None:
    qc.u(theta, phi, 0, q[0])   # Alice'in durumu / Alice's state
    qc.h(q[1])                  # Bell çifti / Bell pair (Alice q1, Bob q2)
    qc.cx(q[1], q[2])
    qc.cx(q[0], q[1])           # Bell ölçümü hazırlığı / Bell measurement
    qc.h(q[0])


# ---- 1) Dinamik devre: ölç → klasik bitle düzelt / measure → classically correct
q = QuantumRegister(3, "q")
crz, crx = ClassicalRegister(1, "z"), ClassicalRegister(1, "x")
qc = QuantumCircuit(q, crz, crx)
prepare(qc, q)
qc.barrier()
qc.measure(q[0], crz)
qc.measure(q[1], crx)
with qc.if_test((crx, 1)):
    qc.x(q[2])
with qc.if_test((crz, 1)):
    qc.z(q[2])
print(qc.draw(fold=110))

# Bob'un kübitini Z ekseninde ölçüp beklenen olasılıkla karşılaştır
# Measure Bob's qubit and compare with the expected probability
check = qc.copy()
cb = ClassicalRegister(1, "bob")
check.add_register(cb)
check.measure(q[2], cb)
sim = AerSimulator(seed_simulator=11)
counts = sim.run(transpile(check, sim), shots=4000).result().get_counts()
p1_bob = sum(v for k, v in counts.items() if k[0] == "1") / 4000
print(f"\nBob P(1) ölçülen / measured: {p1_bob:.3f}   beklenen / expected: {psi.probabilities()[1]:.3f}")

# ---- 2) Ertelenmiş ölçüm: tam durumu doğrula / deferred measurement: verify fully
d = QuantumCircuit(3)
prepare(d, d.qubits)
d.cx(1, 2)    # klasik X yerine CNOT / CNOT instead of classical X
d.cz(0, 2)    # klasik Z yerine CZ  / CZ instead of classical Z
bob = partial_trace(Statevector(d), [0, 1])
print("Sadakat / Fidelity(Alice → Bob):", round(state_fidelity(bob, psi), 6))
