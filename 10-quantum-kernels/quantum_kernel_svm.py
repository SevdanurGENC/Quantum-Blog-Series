"""
QBlog #10 — Kuantum Çekirdekleri: Verinin Gizli Boyutları
           Quantum Kernels: The Hidden Dimensions of Data

TR: Her veri noktasını bir kuantum durumuna gönderiyor, iki durum arasındaki
    örtüşmeyi (fidelity) bir "benzerlik" olarak kullanıyor ve bunu klasik bir
    Destek Vektör Makinesine (SVM) veriyoruz: Kuantum SVM (QSVM).
EN: We map every data point to a quantum state, use the overlap between two
    states as a similarity, and feed that kernel to a classical SVM: a QSVM.

Çalıştır / Run:  python quantum_kernel_svm.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pennylane as qml
from sklearn.datasets import make_circles
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

OUT = Path(__file__).parent / "output"
N_QUBITS = 3
dev = qml.device("default.qubit", wires=N_QUBITS)


def feature_map(x):
    """TR: 2 özellik + 3. "gizli" özellik x0·x1 → dolanık özellik haritası.
    EN: 2 features + a hidden 3rd feature x0·x1 → entangling feature map."""
    f = [x[0], x[1], x[0] * x[1]]
    for _ in range(2):
        for i in range(N_QUBITS):
            qml.Hadamard(wires=i)
            qml.RZ(f[i], wires=i)
        for i in range(N_QUBITS):
            j = (i + 1) % N_QUBITS
            qml.CNOT(wires=[i, j])
            qml.RZ(f[i] * f[j], wires=j)
            qml.CNOT(wires=[i, j])


@qml.qnode(dev)
def overlap_circuit(x1, x2):
    """TR: Donanımda yapılan yol: U(x1) sonra U(x2)† ve |000⟩ olasılığı.
    EN: The hardware way: U(x1) then U(x2)† and the probability of |000⟩."""
    feature_map(x1)
    qml.adjoint(feature_map)(x2)
    return qml.probs(wires=range(N_QUBITS))


@qml.qnode(dev)
def embed(x):
    feature_map(x)
    return qml.state()


def kernel_matrix(A, B):
    """TR: Simülatörde hızlı yol: durumları bir kez hesapla, |⟨a|b⟩|².
    EN: Fast simulator path: compute states once, then |⟨a|b⟩|²."""
    SA = np.array([embed(a) for a in A])
    SB = np.array([embed(b) for b in B])
    return np.abs(SA.conj() @ SB.T) ** 2


def load_data(seed: int = 1):
    X, y = make_circles(160, noise=0.08, factor=0.45, random_state=seed)
    X = X * 2.2                                   # açı aralığına ölçekle / scale to angles
    return train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    Xtr, Xte, ytr, yte = load_data()

    k_hw = overlap_circuit(Xtr[0], Xtr[1])[0]
    k_sv = kernel_matrix(Xtr[:1], Xtr[1:2])[0, 0]
    print(f"k(x0, x1) devre/circuit = {k_hw:.4f} | durum/statevector = {k_sv:.4f}")

    K_train = kernel_matrix(Xtr, Xtr)
    K_test = kernel_matrix(Xte, Xtr)
    qsvm = SVC(kernel="precomputed", C=4.0).fit(K_train, ytr)
    print(f"QSVM test doğruluğu / accuracy:          {qsvm.score(K_test, yte):.2%}")

    lin = SVC(kernel="linear").fit(Xtr, ytr)
    print(f"Doğrusal SVM / Linear SVM (karşılaştırma): {lin.score(Xte, yte):.2%}")
    print("TR: Halkalar düz bir çizgiyle ayrılamaz; kuantum çekirdeği ayırır.")
    print("EN: Rings can't be split by a straight line; the quantum kernel can.")

    order = np.argsort(ytr)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    axes[0].imshow(K_train[np.ix_(order, order)], cmap="magma")
    axes[0].set_title("Kuantum çekirdek matrisi / Quantum kernel matrix")
    gx, gy = np.meshgrid(np.linspace(-3, 3, 60), np.linspace(-3, 3, 60))
    grid = np.c_[gx.ravel(), gy.ravel()]
    zz = qsvm.decision_function(kernel_matrix(grid, Xtr)).reshape(gx.shape)
    axes[1].contourf(gx, gy, zz, levels=20, cmap="coolwarm", alpha=0.75)
    axes[1].contour(gx, gy, zz, levels=[0], colors="k")
    axes[1].scatter(*Xtr.T, c=ytr, cmap="coolwarm", edgecolors="k", s=20)
    axes[1].set_title("QSVM karar sınırı / decision boundary")
    fig.tight_layout()
    fig.savefig(OUT / "10_qsvm.png", dpi=150)
    print(f"\nGörsel / Figure → {OUT / '10_qsvm.png'}")
