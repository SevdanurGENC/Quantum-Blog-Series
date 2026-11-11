"""
QBlog #14 — QAOA'nın Enerji Manzarası: Açılar ve Katmanlar / The QAOA Landscape: Angles and Layers

TR: QAOA'nın yalnızca iki açısı (γ, β) olan en basit hâli için tüm "enerji
    manzarasını" haritalıyor, sonra katman sayısını (p) artırdıkça yaklaşık
    çözümün nasıl iyileştiğini ölçüyoruz. Son olarak "açı aktarımı" hilesini
    deniyoruz: küçük bir grafta bulunan açılar büyük bir grafta da işe yarar mı?
EN: For the simplest QAOA, with just two angles (γ, β), we map the whole energy
    landscape, then measure how the approximation improves as the number of
    layers p grows. Finally we test "parameter transfer": do angles found on a
    small graph work on a bigger one?

Çalıştır / Run:  python qaoa_landscape.py      (~1 dk / ~1 min)
"""
import itertools
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

OUT = Path(__file__).parent / "output"


def make_qaoa(G: nx.Graph, p: int):
    n = G.number_of_nodes()
    cost_h, mixer_h = qml.qaoa.maxcut(G)
    dev = qml.device("default.qubit", wires=n)

    @qml.qnode(dev)
    def expected_cut(params):
        for w in range(n):
            qml.Hadamard(wires=w)
        for k in range(p):
            qml.qaoa.cost_layer(params[0][k], cost_h)
            qml.qaoa.mixer_layer(params[1][k], mixer_h)
        return qml.expval(cost_h)          # = −(beklenen kesim / expected cut)

    return expected_cut


def best_cut(G: nx.Graph) -> int:
    n = G.number_of_nodes()
    return max(sum(b[i] != b[j] for i, j in G.edges) for b in itertools.product([0, 1], repeat=n))


def optimise(G, p, init, steps=120, lr=0.05):
    f = make_qaoa(G, p)
    params = pnp.array(init, requires_grad=True)
    opt = qml.AdamOptimizer(lr)
    for _ in range(steps):
        params = opt.step(f, params)
    return -float(f(params)), np.array(params)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    G = nx.random_regular_graph(3, 8, seed=4)       # 8 düğüm, her düğüm 3 komşulu / 3-regular
    opt_cut = best_cut(G)
    print(f"3-düzenli graf / 3-regular graph: 8 düğüm/nodes, {G.number_of_edges()} kenar/edges, "
          f"en iyi kesim / best cut = {opt_cut}")

    # 1) p = 1 manzarası / landscape
    f1 = make_qaoa(G, 1)
    gammas = np.linspace(0, np.pi, 41)
    betas = np.linspace(0, np.pi / 2, 41)
    L = np.array([[-float(f1([[g], [b]])) for g in gammas] for b in betas])
    i, j = np.unravel_index(L.argmax(), L.shape)
    print(f"\np=1 ızgara taraması / grid scan: en iyi / best γ={gammas[j]:.2f}, β={betas[i]:.2f}, "
          f"kesim/cut = {L.max():.3f}  (oran / ratio r = {L.max() / opt_cut:.3f})")

    # 2) p arttıkça / as p grows — her katman bir öncekinin açılarıyla başlar (warm start)
    print("\n p | beklenen kesim / expected cut | yaklaşıklık oranı / approximation ratio")
    ratios, init = [], [[gammas[j]], [betas[i]]]
    for p in range(1, 5):
        cut, params = optimise(G, p, init)
        ratios.append(cut / opt_cut)
        print(f" {p} | {cut:>29.3f} | {cut / opt_cut:.3f}")
        # bir sonraki p için doğrusal genişlet / interpolate to p+1
        g, b = params
        init = [np.interp(np.linspace(0, 1, p + 1), np.linspace(0, 1, p), g),
                np.interp(np.linspace(0, 1, p + 1), np.linspace(0, 1, p), b)]

    # 3) Açı aktarımı / parameter transfer: 8 düğümde bulunan p=2 açılarını 12 düğümde dene
    _, p2 = optimise(G, 2, [[0.4, 0.8], [0.6, 0.3]])
    G12 = nx.random_regular_graph(3, 12, seed=11)
    cut12 = -float(make_qaoa(G12, 2)(p2))
    print(f"\nAçı aktarımı / transfer → 12 düğüm: kesim/cut = {cut12:.3f}, "
          f"oran / ratio = {cut12 / best_cut(G12):.3f}  (yeniden optimizasyon yok / no re-optimisation)")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    im = axes[0].imshow(L, origin="lower", aspect="auto", cmap="magma",
                        extent=[gammas[0], gammas[-1], betas[0], betas[-1]])
    axes[0].plot(gammas[j], betas[i], "c*", ms=14)
    axes[0].set_xlabel("γ")
    axes[0].set_ylabel("β")
    axes[0].set_title("p=1 manzarası / landscape")
    fig.colorbar(im, ax=axes[0], label="beklenen kesim / expected cut")
    axes[1].plot(range(1, 5), ratios, "o-")
    axes[1].axhline(1, ls="--", c="gray")
    axes[1].set_xlabel("p (katman / layers)")
    axes[1].set_ylabel("yaklaşıklık oranı / ratio")
    axes[1].set_title("Daha derin = daha iyi / deeper = better")
    fig.tight_layout()
    fig.savefig(OUT / "14_qaoa_landscape.png", dpi=150)
    print(f"\nGörsel / Figure → {OUT / '14_qaoa_landscape.png'}")
