"""
QBlog #06 — Grover: Samanlıkta İğne / Grover: A Needle in a Quantum Haystack

TR: N elemanlı sırasız bir listede aranan öğeyi klasik olarak ~N/2 denemede,
    Grover ile ~(π/4)√N adımda buluyoruz. Her adımda "işaretle + ortalamaya
    göre yansıt" ile doğru cevabın genliği büyür.
EN: Classically ~N/2 guesses, Grover ~(π/4)√N iterations. Each step
    "marks + reflects about the mean", amplifying the right answer.

Çalıştır / Run:  python grover_search.py
"""
import math

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import MCXGate
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

N_QUBITS = 4
TARGET = "1011"          # aranan / the needle (q3 q2 q1 q0)


def phase_oracle(n: int, target: str) -> QuantumCircuit:
    """TR/EN: |target⟩'in fazını ters çevirir / flips the phase of |target⟩."""
    o = QuantumCircuit(n, name="Oracle")
    zeros = [i for i, b in enumerate(reversed(target)) if b == "0"]
    if zeros:
        o.x(zeros)
    o.h(n - 1)
    o.append(MCXGate(n - 1), list(range(n)))
    o.h(n - 1)
    if zeros:
        o.x(zeros)
    return o


def diffuser(n: int) -> QuantumCircuit:
    """TR/EN: Ortalama etrafında yansıtma / inversion about the mean."""
    d = QuantumCircuit(n, name="Diffuser")
    d.h(range(n))
    d.compose(phase_oracle(n, "0" * n), inplace=True)
    d.h(range(n))
    return d


def grover(n: int, target: str, iterations: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for _ in range(iterations):
        qc.compose(phase_oracle(n, target), inplace=True)
        qc.compose(diffuser(n), inplace=True)
    return qc


best = math.floor(math.pi / 4 * math.sqrt(2**N_QUBITS))
print(f"N = {2**N_QUBITS}, en iyi adım sayısı / optimal iterations = {best}\n")
print("Adım / Iter | P(hedef / target)")
for k in range(0, 6):
    p = Statevector(grover(N_QUBITS, TARGET, k)).probabilities_dict()[TARGET]
    print(f"{k:>11} | {p:.3f} {'█' * int(p * 40)}")

qc = grover(N_QUBITS, TARGET, best)
qc.measure_all()
sim = AerSimulator(seed_simulator=9)
counts = sim.run(transpile(qc, sim), shots=1000).result().get_counts()
top = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
print(f"\n1000 ölçümde en sık / most frequent: {top}")
