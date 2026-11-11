"""
QBlog #13 — QAOA: Kuantum Optimizasyon ile MaxCut / QAOA: Solving MaxCut with Quantum Optimisation

TR: Bir sosyal ağı, aralarındaki bağlantıların en çoğu "kesilecek" şekilde iki
    gruba ayırmak (MaxCut) NP-zor bir problemdir. QAOA, kuantum devresinin
    açılarını klasik bir optimize ediciyle ayarlayarak iyi çözümleri bulur.
EN: Splitting a network into two groups so that as many edges as possible are
    cut (MaxCut) is NP-hard. QAOA tunes a quantum circuit's angles with a
    classical optimiser to find good solutions.

Çalıştır / Run:  python qaoa_maxcut.py
"""
import itertools
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

OUT = Path(__file__).parent / "output"
EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (0, 3), (1, 4), (2, 5)]
N, P = 6, 3                       # düğüm / nodes, QAOA katmanı / layers
G = nx.Graph(EDGES)

cost_h, mixer_h = qml.qaoa.maxcut(G)
dev = qml.device("default.qubit", wires=N)


def qaoa_layer(gamma, alpha):
    qml.qaoa.cost_layer(gamma, cost_h)    # problem: kesilen kenarları ödüllendir / reward cut edges
    qml.qaoa.mixer_layer(alpha, mixer_h)  # karıştırıcı: keşfet / explore


def circuit(params):
    for w in range(N):
        qml.Hadamard(wires=w)
    qml.layer(qaoa_layer, P, params[0], params[1])


@qml.qnode(dev)
def energy(params):
    circuit(params)
    return qml.expval(cost_h)


@qml.qnode(qml.device("default.qubit", wires=N, seed=3), shots=1000)
def sample(params):
    circuit(params)
    return qml.sample(wires=range(N))


def cut_size(bits) -> int:
    return sum(bits[i] != bits[j] for i, j in EDGES)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    best = max(cut_size(b) for b in itertools.product([0, 1], repeat=N))
    print(f"Graf: {N} düğüm, {len(EDGES)} kenar | kaba kuvvet en iyi kesim / brute-force best cut = {best}")

    params = pnp.array([[0.5] * P, [0.5] * P], requires_grad=True)
    opt = qml.AdamOptimizer(0.05)
    for step in range(1, 151):
        params = opt.step(energy, params)
        if step in (1, 25, 50, 100, 150):
            print(f"adım/step {step:>3} | beklenen kesim / expected cut = {-float(energy(params)):.3f}")

    bits = [tuple(int(b) for b in s) for s in np.array(sample(params))]
    counts = Counter(bits)
    top = counts.most_common(4)
    print("\nEn sık ölçülen bölmeler / Most frequent partitions:")
    for b, c in top:
        print(f"  {''.join(map(str, b))}  kesim/cut = {cut_size(b)}  ({c / 10:.1f}%)")
    hit = sum(c for b, c in counts.items() if cut_size(b) == best) / 1000
    print(f"\nOptimal çözümü bulma olasılığı / probability of an optimal cut: {hit:.1%}")
    print(f"Rastgele tahminle / random guess: "
          f"{sum(cut_size(b) == best for b in itertools.product([0, 1], repeat=N)) / 2 ** N:.1%}")

    b = top[0][0]
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    pos = nx.circular_layout(G)
    nx.draw_networkx_nodes(G, pos, node_color=["#3EE6F0" if v else "#FF5FA2" for v in b], ax=ax)
    nx.draw_networkx_labels(G, pos, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=[e for e in EDGES if b[e[0]] != b[e[1]]], style="dashed", ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=[e for e in EDGES if b[e[0]] == b[e[1]]], width=2.5, ax=ax)
    ax.set_title(f"QAOA kesimi / cut = {cut_size(b)} (kesik çizgiler kesildi / dashed = cut)")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "13_maxcut.png", dpi=150)
    print(f"\nGörsel / Figure → {OUT / '13_maxcut.png'}")
