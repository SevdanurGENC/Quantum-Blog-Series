"""
QBlog #11 — Kuantum Bilgisayar El Yazısı Okuyabilir mi? / Can a Quantum Computer Read Handwriting?

TR: 8x8 piksellik el yazısı rakamları (64 özellik) PCA ile 4 sayıya sıkıştırıyor,
    4 kübitlik bir varyasyonel devreyle "3" ile "8"i ayırt ediyoruz.
    Hibrit model: sıkıştırma klasik, sınıflandırma kuantum.
EN: We compress 8x8 handwritten digits (64 features) to 4 numbers with PCA and
    train a 4-qubit variational circuit to tell "3" from "8".
    A hybrid model: classical compression, quantum classification.

Çalıştır / Run:  python quantum_digits.py      (~1 dk / ~1 min)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

OUT = Path(__file__).parent / "output"
DIGITS = (3, 8)
N_QUBITS, N_LAYERS = 4, 3
dev = qml.device("default.qubit", wires=N_QUBITS)


def load_data(seed: int = 0):
    d = load_digits()
    mask = np.isin(d.target, DIGITS)
    X, y = d.data[mask], np.where(d.target[mask] == DIGITS[0], 1, -1)
    Xtr, Xte, ytr, yte, Itr, Ite = train_test_split(
        X, y, d.images[mask], test_size=0.25, random_state=seed, stratify=y)
    pca = PCA(N_QUBITS, random_state=seed).fit(Xtr)            # 64 → 4
    sc = MinMaxScaler((0, np.pi)).fit(pca.transform(Xtr))      # açılara / to angles
    f = lambda A: sc.transform(pca.transform(A))
    return f(Xtr), f(Xte), ytr, yte, Ite, pca


@qml.qnode(dev)
def circuit(weights, x):
    for layer in weights:
        qml.AngleEmbedding(x, wires=range(N_QUBITS), rotation="Y")   # veriyi yükle / load data
        qml.StronglyEntanglingLayers(layer[None], wires=range(N_QUBITS))
    return qml.expval(qml.PauliZ(0))


def model(params, X):
    return circuit(params[0], X) + params[1]


def cost(params, X, y):
    return pnp.mean((model(params, X) - y) ** 2)


def accuracy(params, X, y):
    return float(np.mean(np.sign(model(params, X)) == y))


def train(epochs=25, batch=24, seed=0, on_epoch=None):
    Xtr, Xte, ytr, yte, _, _ = load_data(seed)
    rng = np.random.default_rng(seed)
    params = [pnp.array(rng.normal(0, 0.4, (N_LAYERS, N_QUBITS, 3)), requires_grad=True),
              pnp.array(0.0, requires_grad=True)]
    opt = qml.AdamOptimizer(0.06)
    for ep in range(1, epochs + 1):
        idx = rng.permutation(len(Xtr))
        for s in range(0, len(Xtr), batch):
            b = idx[s : s + batch]
            params = opt.step(lambda w, c: cost([w, c], Xtr[b], ytr[b]), *params)
        if on_epoch:
            on_epoch(ep, [np.array(p) for p in params])
    return params


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    Xtr, Xte, ytr, yte, Ite, pca = load_data()
    print(f"Eğitim / train: {len(Xtr)}  test: {len(Xte)}  |  "
          f"PCA 4 bileşen varyansın %{pca.explained_variance_ratio_.sum() * 100:.0f}'sini tutuyor "
          f"/ keeps {pca.explained_variance_ratio_.sum():.0%} of the variance")

    def report(ep, p):
        if ep in (1, 5, 10, 15, 20, 25):
            print(f"epoch {ep:>2} | kayıp/loss {float(cost(p, Xtr, ytr)):.3f} | "
                  f"eğitim/train {accuracy(p, Xtr, ytr):.1%} | test {accuracy(p, Xte, yte):.1%}")

    params = train(on_epoch=report)

    pred = np.sign(np.array(model(params, Xte)))
    fig, axes = plt.subplots(3, 8, figsize=(10, 4.2))
    for ax, img, p, t in zip(axes.ravel(), Ite, pred, yte):
        ax.imshow(img, cmap="gray_r")
        lab = DIGITS[0] if p > 0 else DIGITS[1]
        ax.set_title(f"→ {lab}", color="green" if p == t else "red", fontsize=11)
        ax.axis("off")
    fig.suptitle(f"4 kübit, {params[0].size + 1} parametre / 4 qubits, {params[0].size + 1} parameters")
    fig.tight_layout()
    fig.savefig(OUT / "11_predictions.png", dpi=150)
    print(f"\nGörsel / Figure → {OUT / '11_predictions.png'}")
