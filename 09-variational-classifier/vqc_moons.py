"""
QBlog #09 — Öğrenen Bir Devre: Varyasyonel Kuantum Sınıflandırıcı
           A Circuit That Learns: The Variational Quantum Classifier

TR: Ayarlanabilir dönüş açılarına sahip bir kuantum devresini, klasik bir
    optimize edici (Adam) ile "ay" (moons) veri setini ayırmak için
    eğitiyoruz. Veriyi her katmanda yeniden yüklüyoruz (data re-uploading).
EN: We train a quantum circuit with tunable rotation angles using a classical
    optimizer (Adam) to separate the "moons" dataset, re-uploading the data
    in every layer.

Çalıştır / Run:  python vqc_moons.py      (~1 dk / ~1 min on a laptop)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp
from sklearn.datasets import make_moons
from sklearn.model_selection import train_test_split

OUT = Path(__file__).parent / "output"
N_QUBITS, N_LAYERS = 2, 4
dev = qml.device("default.qubit", wires=N_QUBITS)


def load_data(seed: int = 0):
    X, y = make_moons(240, noise=0.12, random_state=seed)
    X = (X - X.mean(0)) / X.std(0)          # ölçekle / standardise
    y = 2 * y - 1                           # {0,1} → {-1,+1}
    return train_test_split(X, y, test_size=0.25, random_state=seed)


@qml.qnode(dev)
def circuit(weights, x):
    """weights: (katman/layers, kübit/qubits, 3).  x: (batch, 2) veya (2,)"""
    for layer in weights:
        qml.AngleEmbedding(x, wires=range(N_QUBITS), rotation="Y")   # veriyi yeniden yükle / re-upload
        qml.StronglyEntanglingLayers(layer[None], wires=range(N_QUBITS))
    return qml.expval(qml.PauliZ(0))


def model(params, x):
    weights, bias = params
    return circuit(weights, x) + bias


def cost(params, X, y):
    return pnp.mean((model(params, X) - y) ** 2)


def accuracy(params, X, y) -> float:
    return float(np.mean(np.sign(model(params, X)) == y))


def train(epochs: int = 40, batch: int = 32, seed: int = 0, on_epoch=None):
    """TR/EN: Eğit; her epoch sonunda on_epoch(epoch, params) çağrılır."""
    Xtr, Xte, ytr, yte = load_data(seed)
    rng = np.random.default_rng(seed)
    weights = pnp.array(rng.normal(0, 0.6, (N_LAYERS, N_QUBITS, 3)), requires_grad=True)
    bias = pnp.array(0.0, requires_grad=True)
    params = [weights, bias]
    opt = qml.AdamOptimizer(0.08)
    for epoch in range(1, epochs + 1):
        idx = rng.permutation(len(Xtr))
        for s in range(0, len(Xtr), batch):
            b = idx[s : s + batch]
            params = opt.step(lambda w, c: cost([w, c], Xtr[b], ytr[b]), *params)
        if on_epoch:
            on_epoch(epoch, [np.array(p) for p in params])
    return params, (Xtr, Xte, ytr, yte)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    Xtr, Xte, ytr, yte = load_data()
    print(qml.draw(circuit, level="device")(np.zeros((N_LAYERS, N_QUBITS, 3)), Xtr[0]))

    def report(epoch, p):
        if epoch % 5 == 0 or epoch == 1:
            print(f"epoch {epoch:>3} | kayıp/loss {float(cost(p, Xtr, ytr)):.3f} | "
                  f"eğitim/train {accuracy(p, Xtr, ytr):.2%} | test {accuracy(p, Xte, yte):.2%}")

    params, _ = train(on_epoch=report)

    # Karar sınırı / Decision boundary
    gx, gy = np.meshgrid(np.linspace(-2.4, 2.4, 70), np.linspace(-2.4, 2.4, 70))
    grid = np.c_[gx.ravel(), gy.ravel()]
    zz = np.array(model(params, grid)).reshape(gx.shape)
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.contourf(gx, gy, zz, levels=20, cmap="coolwarm", alpha=0.75)
    ax.contour(gx, gy, zz, levels=[0], colors="k", linewidths=1.5)
    ax.scatter(*Xtr.T, c=ytr, cmap="coolwarm", edgecolors="k", s=22)
    ax.scatter(*Xte.T, c=yte, cmap="coolwarm", edgecolors="w", marker="^", s=30)
    ax.set_title(f"VQC — test doğruluğu / accuracy {accuracy(params, Xte, yte):.0%}")
    fig.tight_layout()
    fig.savefig(OUT / "09_decision_boundary.png", dpi=150)
    print(f"\nGörsel / Figure → {OUT / '09_decision_boundary.png'}")
