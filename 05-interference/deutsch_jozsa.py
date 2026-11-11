"""
QBlog #05 — Girişim: Kuantum Hızının Sırrı / Interference: The Secret of Quantum Speedups

TR: Deutsch–Jozsa algoritması, bir fonksiyonun "sabit" mi "dengeli" mi
    olduğunu TEK sorguda bulur. Klasik olarak en kötü durumda 2^(n-1)+1
    sorgu gerekir. Kilit nokta: yanlış cevaplar birbirini yok eder.
EN: Deutsch–Jozsa decides whether a function is constant or balanced with a
    SINGLE query (classically up to 2^(n-1)+1). The trick: wrong answers
    cancel each other out through interference.

Çalıştır / Run:  python deutsch_jozsa.py
"""
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

N = 4  # giriş kübiti / input qubits


def constant_oracle(n: int, value: int) -> QuantumCircuit:
    o = QuantumCircuit(n + 1, name=f"sabit/const={value}")
    if value:
        o.x(n)
    return o


def balanced_oracle(n: int, mask: int) -> QuantumCircuit:
    """f(x) = (x · mask) mod 2  → her zaman dengeli / always balanced (mask≠0)."""
    o = QuantumCircuit(n + 1, name=f"dengeli/balanced m={mask:0{n}b}")
    for i in range(n):
        if (mask >> i) & 1:
            o.cx(i, n)
    return o


def deutsch_jozsa(oracle: QuantumCircuit, n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n + 1, n)
    qc.x(n)
    qc.h(range(n + 1))          # tüm girişleri aynı anda / all inputs at once
    qc.compose(oracle, inplace=True)
    qc.h(range(n))              # girişim / interference
    qc.measure(range(n), range(n))
    return qc


sim = AerSimulator(seed_simulator=5)
oracles = [constant_oracle(N, 0), constant_oracle(N, 1)] + [
    balanced_oracle(N, m) for m in (0b1010, 0b0111, 0b1111)
]

print(deutsch_jozsa(oracles[2], N).draw(fold=100))
print("\nKâhin / Oracle                 | Sonuç / Result | Karar / Verdict")
for o in oracles:
    counts = sim.run(transpile(deutsch_jozsa(o, N), sim), shots=1024).result().get_counts()
    top = max(counts, key=counts.get)
    verdict = "SABİT / CONSTANT" if top == "0" * N else "DENGELİ / BALANCED"
    print(f"{o.name:<30} | {top:^14} | {verdict}")

print("\nTR: Dengeli kâhinlerde ölçüm sonucu gizli maskenin ta kendisi (Bernstein–Vazirani'nin tohumu).")
print("EN: For balanced oracles the result IS the hidden mask (the seed of Bernstein–Vazirani).")
