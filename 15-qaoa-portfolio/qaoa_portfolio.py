"""
QBlog #15 — QAOA ile Portföy Optimizasyonu / Portfolio Optimisation with QAOA

TR: 6 hisse senedinden tam 3 tanesini seçerek getiri/risk dengesini en iyi
    yapan portföyü arıyoruz. Problem bir QUBO'ya (ikili karesel optimizasyon),
    oradan da bir Ising Hamiltonyeni'ne çevriliyor ve QAOA ile çözülüyor.
    "Tam 3 hisse" kısıtı için iki yol deniyoruz: ceza terimi ve kısıtı koruyan
    XY karıştırıcısı.
    Not: Veriler hayalîdir; bu bir algoritma örneğidir, yatırım tavsiyesi değildir.
EN: Pick exactly 3 of 6 stocks to get the best return/risk trade-off. The problem
    becomes a QUBO, then an Ising Hamiltonian, solved with QAOA. We enforce
    "exactly 3" two ways: a penalty term and a constraint-preserving XY mixer.
    Note: the data is made up — this is an algorithm demo, not investment advice.

Çalıştır / Run:  python qaoa_portfolio.py      (~1 dk / ~1 min)
"""
import itertools
from pathlib import Path

import matplotlib
import networkx as nx

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

OUT = Path(__file__).parent / "output"
NAMES = ["A", "B", "C", "D", "E", "F"]
MU = np.array([0.12, 0.10, 0.07, 0.15, 0.09, 0.11])            # beklenen getiri / expected return
VOL = np.array([0.20, 0.15, 0.08, 0.30, 0.12, 0.18])           # oynaklık / volatility
CORR = np.array([
    [1.0, 0.6, 0.2, 0.5, 0.1, 0.4],
    [0.6, 1.0, 0.3, 0.4, 0.2, 0.5],
    [0.2, 0.3, 1.0, 0.1, 0.3, 0.2],
    [0.5, 0.4, 0.1, 1.0, 0.0, 0.6],
    [0.1, 0.2, 0.3, 0.0, 1.0, 0.1],
    [0.4, 0.5, 0.2, 0.6, 0.1, 1.0],
])
SIGMA = np.outer(VOL, VOL) * CORR                              # kovaryans / covariance
Q_RISK, K = 2.0, 3                                             # risk iştahı / aversion, kaç hisse / how many
N = len(MU)


def objective(x) -> float:
    """TR/EN: en aza indir / minimise  q·xᵀΣx − μᵀx."""
    x = np.asarray(x, float)
    return Q_RISK * x @ SIGMA @ x - MU @ x


def qubo_hamiltonian(penalty: float):
    """x_i = (1 − Z_i)/2 dönüşümüyle QUBO → Ising. / QUBO → Ising via x_i = (1 − Z_i)/2."""
    Qm = Q_RISK * SIGMA.copy()
    lin = -MU.copy()
    if penalty:                                                 # + A (Σx − K)²
        Qm += penalty * np.ones((N, N))
        lin += penalty * (-2 * K) * np.ones(N)
    coeffs, ops = [], []
    for i in range(N):
        # x_i² = x_i  →  köşegeni doğrusala kat / fold the diagonal into the linear part
        h = -(lin[i] + Qm[i, i]) / 2 - sum(Qm[i, j] + Qm[j, i] for j in range(N) if j != i) / 4
        coeffs.append(h)
        ops.append(qml.PauliZ(i))
        for j in range(i + 1, N):
            coeffs.append((Qm[i, j] + Qm[j, i]) / 4)
            ops.append(qml.PauliZ(i) @ qml.PauliZ(j))
    return qml.Hamiltonian(coeffs, ops)


def dicke_like_start():
    """TR/EN: K tane 1 içeren eşit süperpozisyon / equal superposition of all states with K ones."""
    states = [b for b in itertools.product([0, 1], repeat=N) if sum(b) == K]
    vec = np.zeros(2 ** N)
    for b in states:
        vec[int("".join(map(str, b)), 2)] = 1
    return vec / np.linalg.norm(vec)


def run(mode: str, p=3, steps=150):
    dev = qml.device("default.qubit", wires=N)
    H = qubo_hamiltonian(penalty=0.0 if mode == "xy" else 1.0)
    start = dicke_like_start()

    def circuit(params):
        if mode == "xy":
            qml.StatePrep(start, wires=range(N))               # zaten "tam 3" / already "exactly 3"
            mixer = qml.qaoa.xy_mixer(nx.complete_graph(N))       # 1 sayısını korur / preserves the number of 1s
        else:
            for w in range(N):
                qml.Hadamard(wires=w)
            mixer = qml.qaoa.x_mixer(range(N))
        for k in range(p):
            qml.qaoa.cost_layer(params[0][k], H)
            qml.qaoa.mixer_layer(params[1][k], mixer)

    @qml.qnode(dev)
    def energy(params):
        circuit(params)
        return qml.expval(H)

    @qml.qnode(dev)
    def probs(params):
        circuit(params)
        return qml.probs(wires=range(N))

    params = pnp.array([[0.3] * p, [0.4] * p], requires_grad=True)
    opt = qml.AdamOptimizer(0.05)
    for _ in range(steps):
        params = opt.step(energy, params)
    return np.array(probs(params))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    feasible = [b for b in itertools.product([0, 1], repeat=N) if sum(b) == K]
    ranked = sorted(feasible, key=objective)
    best = ranked[0]
    pick = lambda b: "".join(n for n, x in zip(NAMES, b) if x)
    print(f"{len(feasible)} geçerli portföy / valid portfolios. Kaba kuvvet en iyisi / brute-force best: "
          f"{pick(best)}  (amaç/objective = {objective(best):.4f})")
    print("İlk 3 / Top 3:", ", ".join(f"{pick(b)} ({objective(b):.4f})" for b in ranked[:3]))

    for mode, label in (("penalty", "Ceza terimi / Penalty + X mixer"), ("xy", "XY karıştırıcı / XY mixer")):
        pr = run(mode)
        top = np.argsort(pr)[::-1][:3]
        valid = sum(pr[int("".join(map(str, b)), 2)] for b in feasible)
        p_best = pr[int("".join(map(str, best)), 2)]
        print(f"\n{label}")
        print(f"  geçerli (tam {K}) olasılığı / P(valid): {valid:.1%}")
        print(f"  en iyi portföy olasılığı / P(best):    {p_best:.1%}   (rastgele geçerli / random valid: {1 / len(feasible):.1%})")
        for idx in top:
            b = tuple(int(c) for c in format(idx, f"0{N}b"))
            print(f"   {''.join(map(str, b))}  {pick(b) or '-':<6} {pr[idx]:.1%}")

    pr = run("xy")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    labels = [pick(b) for b in ranked]
    ax.bar(labels, [pr[int("".join(map(str, b)), 2)] for b in ranked],
           color=["#FF8A3D" if b == best else "#8892b0" for b in ranked])
    ax.set_ylabel("QAOA olasılığı / probability")
    ax.set_title("Portföyler en iyiden en kötüye / Portfolios, best → worst")
    plt.setp(ax.get_xticklabels(), rotation=60)
    fig.tight_layout()
    fig.savefig(OUT / "15_portfolio.png", dpi=150)
    print(f"\nGörsel / Figure → {OUT / '15_portfolio.png'}")
