"""
QBlog #12 — Çorak Platolar: Kuantum ML'in Gizli Düşmanı / Barren Plateaus: The Hidden Enemy of Quantum ML

TR: Rastgele başlatılmış kuantum devrelerinde, kübit sayısı arttıkça gradyanın
    varyansı ÜSTEL olarak küçülür: optimize edici "dümdüz bir çölde" kaybolur.
    Bunu ölçüyor ve "küresel" ile "yerel" maliyet fonksiyonlarını karşılaştırıyoruz.
EN: In randomly initialised circuits the variance of the gradient shrinks
    EXPONENTIALLY with the number of qubits: the optimiser gets lost in a flat
    desert. We measure it and compare global vs local cost functions.

Çalıştır / Run:  python barren_plateaus.py      (~1 dk / ~1 min)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pennylane as qml

OUT = Path(__file__).parent / "output"
SAMPLES = 120
QUBITS = [2, 3, 4, 5, 6, 7, 8, 9, 10]


def make_cost(n: int, local: bool):
    dev = qml.device("default.qubit", wires=n)
    obs = qml.PauliZ(0) @ qml.PauliZ(1) if local else qml.prod(*[qml.PauliZ(i) for i in range(n)])

    @qml.qnode(dev)
    def cost(params, gates):
        for i in range(n):
            qml.RY(np.pi / 4, wires=i)
        for layer, glayer in zip(params, gates):            # derinlik ~ n / depth ~ n
            for i in range(n):
                getattr(qml, glayer[i])(layer[i], wires=i)  # rastgele RX/RY/RZ
            for i in range(n - 1):
                qml.CZ(wires=[i, i + 1])
        return qml.expval(obs)

    return cost


def grad_first_param(cost, params, gates):
    """TR: Parametre kaydırma kuralı — gerçek donanımdaki gibi, yalnızca 2 devre.
    EN: Parameter-shift rule — just 2 circuits, exactly as on real hardware."""
    p, m = params.copy(), params.copy()
    p[0, 0] += np.pi / 2
    m[0, 0] -= np.pi / 2
    return 0.5 * (cost(p, gates) - cost(m, gates))


def variance(n: int, local: bool, rng) -> float:
    cost = make_cost(n, local)
    depth = max(n, 4)
    g = []
    for _ in range(SAMPLES):
        params = rng.uniform(0, 2 * np.pi, (depth, n))
        gates = rng.choice(["RX", "RY", "RZ"], (depth, n))
        g.append(grad_first_param(cost, params, gates))
    return float(np.var(g))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(7)
    res = {"global": [], "local": []}
    print(" kübit/qubits | Var[∂C] küresel/global | Var[∂C] yerel/local")
    for n in QUBITS:
        vg, vl = variance(n, False, rng), variance(n, True, rng)
        res["global"].append(vg)
        res["local"].append(vl)
        print(f" {n:>11} | {vg:>22.2e} | {vl:>19.2e}")

    slope = np.polyfit(QUBITS, np.log2(res["global"]), 1)[0]
    print(f"\nKüresel maliyette her yeni kübit varyansı ~{2 ** -slope:.1f} kat küçültüyor.")
    print(f"Global cost: each extra qubit shrinks the variance by ~{2 ** -slope:.1f}x.")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(QUBITS, res["global"], "o-", label="küresel / global  (Z⊗Z⊗…⊗Z)")
    ax.semilogy(QUBITS, res["local"], "s-", label="yerel / local  (Z₀Z₁)")
    ax.set_xlabel("kübit sayısı / number of qubits")
    ax.set_ylabel("Var[∂C/∂θ]")
    ax.set_title("Çorak plato / Barren plateau")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "12_barren_plateau.png", dpi=150)
    print(f"\nGörsel / Figure → {OUT / '12_barren_plateau.png'}")
