"""
QBlog #04 — Kuantum Zarı / Rolling a Quantum Die

TR: Klasik bilgisayarlar "sahte" rastgele sayı üretir; kübit ölçümü ise
    doğası gereği rastgeledir. 3 kübitle 0–7 arası sayı üretip, reddetme
    örneklemesiyle adil bir 6 yüzlü zar yapıyoruz.
EN: Classical computers produce pseudo-random numbers; measuring a qubit is
    random by nature. We draw 0–7 from 3 qubits and use rejection sampling
    to build a fair six-sided die.

Not / Note: Simülatör içeride sözde rastgele üretici kullanır. Gerçek
kuantum rastgelelik için aynı devreyi gerçek donanımda (ör. IBM Quantum)
çalıştırın. / The simulator itself uses a PRNG — run on real hardware for
genuine quantum randomness.

Çalıştır / Run:  python quantum_dice.py
"""
from collections import Counter

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

N_QUBITS = 3
qc = QuantumCircuit(N_QUBITS)
qc.h(range(N_QUBITS))      # her kübit %50 / each qubit 50-50
qc.measure_all()
print(qc.draw())

sim = AerSimulator()
compiled = transpile(qc, sim)


def quantum_numbers(n: int) -> list[int]:
    """TR/EN: n adet 0–7 sayı / n numbers in 0–7 (one shot each)."""
    mem = sim.run(compiled, shots=n, memory=True).result().get_memory()
    return [int(bits, 2) for bits in mem]


def roll_dice(n_rolls: int) -> list[int]:
    """TR: 6 ve 7'yi atıp yeniden çek (reddetme örneklemesi).
    EN: Discard 6 and 7 and redraw (rejection sampling)."""
    rolls: list[int] = []
    while len(rolls) < n_rolls:
        rolls += [x + 1 for x in quantum_numbers(2 * n_rolls) if x < 6]
    return rolls[:n_rolls]


print("Beş zar / Five rolls:", roll_dice(5))

N = 6000
hist = Counter(roll_dice(N))
expected = N / 6
chi2 = sum((hist[f] - expected) ** 2 / expected for f in range(1, 7))
print(f"\n{N} atış / rolls:")
for face in range(1, 7):
    print(f"  {face}: {'█' * (hist[face] // 40)} {hist[face]}")
print(f"χ² = {chi2:.2f}  (5 serbestlik derecesi, %95 sınırı ≈ 11.07 / 5 dof, 95% limit ≈ 11.07)")
