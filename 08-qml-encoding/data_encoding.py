"""
QBlog #08 — Veriyi Kübitlere Yazmak / Writing Data into Qubits

TR: Kuantum makine öğrenmesinin ilk adımı: klasik veriyi kuantum durumuna
    kodlamak. Açı kodlama, genlik kodlama ve dolanık bir "özellik haritası"
    (ZZ feature map) karşılaştırıyoruz; iki veri noktasının kuantum
    durumları ne kadar "benzer" onu da ölçüyoruz.
EN: Step one of QML: encode classical data as a quantum state. We compare
    angle encoding, amplitude encoding and an entangling ZZ feature map, and
    measure how "similar" two data points look as quantum states.

Çalıştır / Run:  python data_encoding.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pennylane as qml
from sklearn.datasets import make_moons

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- 1) Açı / Angle
dev1 = qml.device("default.qubit", wires=1)


@qml.qnode(dev1)
def angle_encode_bloch(x):
    """TR: 2 özellik → 1 kübit: x0 enlem, x1 boylam gibi davranır.
    EN: 2 features → 1 qubit: x0 acts like latitude, x1 like longitude."""
    qml.RY(x[0], wires=0)
    qml.RZ(x[1], wires=0)
    return [qml.expval(qml.PauliX(0)), qml.expval(qml.PauliY(0)), qml.expval(qml.PauliZ(0))]


# ---------------------------------------------------------------- 2) Genlik / Amplitude
dev3 = qml.device("default.qubit", wires=3)


@qml.qnode(dev3)
def amplitude_encode(x):
    """TR: 8 sayı → yalnızca 3 kübit! (2^3 = 8 genlik)
    EN: 8 numbers → only 3 qubits! (2^3 = 8 amplitudes)"""
    qml.AmplitudeEmbedding(x, wires=range(3), normalize=True)
    return qml.state()


# ---------------------------------------------------------------- 3) ZZ özellik haritası
dev2 = qml.device("default.qubit", wires=2)


def zz_feature_map(x, reps=2):
    for _ in range(reps):
        for i in range(2):
            qml.Hadamard(wires=i)
            qml.RZ(2 * x[i], wires=i)
        qml.CNOT(wires=[0, 1])
        qml.RZ(2 * (np.pi - x[0]) * (np.pi - x[1]), wires=1)   # etkileşim / interaction
        qml.CNOT(wires=[0, 1])


@qml.qnode(dev2)
def zz_state(x):
    zz_feature_map(x)
    return qml.state()


def fidelity(a, b):
    return float(np.abs(np.vdot(a, b)) ** 2)


if __name__ == "__main__":
    x = np.array([0.8, 2.1])
    print("Açı kodlama / Angle encoding  x =", x)
    print("  Bloch (x, y, z):", np.round(angle_encode_bloch(x), 3))
    print(qml.draw(angle_encode_bloch)(x))

    data = np.array([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0])
    psi = amplitude_encode(data)
    print("\nGenlik kodlama / Amplitude encoding:", data)
    print("  genlikler / amplitudes:", np.round(np.real(psi), 3))
    print("  olasılıklar ∝ veri² / probabilities ∝ data²:", np.round(np.abs(psi) ** 2, 3))

    a, b, c = np.array([0.3, 0.4]), np.array([0.35, 0.45]), np.array([2.5, 1.2])
    print("\nZZ özellik haritası / ZZ feature map — kuantum benzerlik / quantum similarity")
    print(f"  yakın noktalar / nearby points  F(a,b) = {fidelity(zz_state(a), zz_state(b)):.3f}")
    print(f"  uzak noktalar  / distant points F(a,c) = {fidelity(zz_state(a), zz_state(c)):.3f}")
    print("  TR: Bu benzerlik #10'daki kuantum çekirdeğinin ta kendisi.")
    print("  EN: This similarity is exactly the quantum kernel of post #10.")

    # Moons veri setini Bloch küresine yerleştir / map the moons dataset onto the sphere
    X, y = make_moons(200, noise=0.08, random_state=0)
    Xs = (X - X.min(0)) / (X.max(0) - X.min(0))
    Xs = Xs * np.array([np.pi, 2 * np.pi])
    pts = np.array([angle_encode_bloch(p) for p in Xs])

    fig = plt.figure(figsize=(10, 4.5))
    ax1 = fig.add_subplot(1, 2, 1)
    ax1.scatter(X[:, 0], X[:, 1], c=y, cmap="cool", s=14)
    ax1.set_title("Klasik veri / Classical data")
    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    u, v = np.mgrid[0 : 2 * np.pi : 40j, 0 : np.pi : 20j]
    ax2.plot_wireframe(np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v), color="#999", lw=0.3)
    ax2.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=y, cmap="cool", s=14)
    ax2.set_title("Bloch küresinde / On the Bloch sphere")
    fig.tight_layout()
    fig.savefig(OUT / "08_moons_on_bloch.png", dpi=150)
    print(f"\nGörsel / Figure → {OUT / '08_moons_on_bloch.png'}")
