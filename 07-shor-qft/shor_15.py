"""
QBlog #07 — Shor ve QFT: Şifreler Tehlikede mi? / Shor & the QFT: Is Encryption in Danger?

TR: RSA'nın güvenliği büyük sayıları çarpanlarına ayırmanın zorluğuna dayanır.
    Shor algoritması bu işi "periyot bulma" problemine çevirir ve periyodu
    Kuantum Fourier Dönüşümü (QFT) ile bulur. Burada 15 = 3 × 5'i buluyoruz.
EN: RSA relies on factoring being hard. Shor turns factoring into period
    finding and solves it with the Quantum Fourier Transform. We factor 15.

Çalıştır / Run:  python shor_15.py
"""
import math
from fractions import Fraction

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit_aer import AerSimulator

N, A = 15, 7          # çarpanlarına ayrılacak sayı ve taban / number and base
N_COUNT = 8           # sayaç kübitleri / counting qubits
N_WORK = 4            # 15 < 2^4


def qft_dagger(n: int) -> QuantumCircuit:
    """TR/EN: Ters QFT, elle kuruldu / inverse QFT, built by hand."""
    qc = QuantumCircuit(n, name="QFT†")
    for i in range(n // 2):
        qc.swap(i, n - i - 1)
    for j in range(n):
        for m in range(j):
            qc.cp(-math.pi / 2 ** (j - m), m, j)
        qc.h(j)
    return qc


def mod_mult_gate(a: int, power: int) -> UnitaryGate:
    """|y⟩ → |a^power · y mod N⟩ (y < N), diğerleri sabit / others unchanged."""
    factor = pow(a, power, N)
    dim = 2**N_WORK
    U = np.zeros((dim, dim))
    for y in range(dim):
        U[(factor * y) % N if y < N else y, y] = 1
    return UnitaryGate(U, label=f"{a}^{power} mod {N}")


qc = QuantumCircuit(N_COUNT + N_WORK, N_COUNT)
qc.h(range(N_COUNT))
qc.x(N_COUNT)                                  # çalışma yazmacı = |1⟩
for k in range(N_COUNT):
    gate = mod_mult_gate(A, 2**k).control(1)
    qc.append(gate, [k] + list(range(N_COUNT, N_COUNT + N_WORK)))
qc.compose(qft_dagger(N_COUNT), range(N_COUNT), inplace=True)
qc.measure(range(N_COUNT), range(N_COUNT))

sim = AerSimulator(seed_simulator=15)
counts = sim.run(transpile(qc, sim), shots=2048).result().get_counts()

print("Ölçüm | Faz / Phase | Tahmini periyot r / Guessed period r")
factors = set()
for bits, c in sorted(counts.items(), key=lambda kv: -kv[1]):
    phase = int(bits, 2) / 2**N_COUNT
    r = Fraction(phase).limit_denominator(N).denominator
    print(f"{bits} | {phase:>6.3f}      | r = {r}   ({c} kez / times)")
    if phase and r % 2 == 0 and pow(A, r, N) == 1:
        for g in (math.gcd(A ** (r // 2) - 1, N), math.gcd(A ** (r // 2) + 1, N)):
            if 1 < g < N:
                factors.add(g)

print(f"\nPeriyot / Period of {A}^x mod {N}: r = 4  (7, 4, 13, 1, 7, …)")
print(f"Bulunan çarpanlar / Factors found: {sorted(factors)}  → {N} = "
      + " × ".join(map(str, sorted(factors))))
