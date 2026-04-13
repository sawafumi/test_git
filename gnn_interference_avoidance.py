"""ロボット探索時の干渉回避デモ（ロボット × ワーク）。

- シーン: 2Dグリッド上でロボットがワーク（対象物）を探索
- 課題: ワーク周辺の安全距離を守りながら探索効率を高める
- 手法: ロボット + ワークをグラフ化し、簡易GNNで候補移動の干渉リスクを予測

依存ライブラリ: 標準ライブラリのみ
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass


ACTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),  (0, 0),  (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


@dataclass
class Work:
    x: int
    y: int
    radius: float


@dataclass
class Scene:
    size: int
    works: list[Work]
    robot_start: tuple[int, int]


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    bt = list(zip(*b))
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def transpose(m: list[list[float]]) -> list[list[float]]:
    return [list(col) for col in zip(*m)]


def relu(m: list[list[float]]) -> list[list[float]]:
    return [[v if v > 0 else 0.0 for v in row] for row in m]


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def add_bias(m: list[list[float]], b: list[float]) -> list[list[float]]:
    return [[v + b[j] for j, v in enumerate(row)] for row in m]


def normalize_adjacency(adj: list[list[float]]) -> list[list[float]]:
    n = len(adj)
    a = [[adj[i][j] + (1.0 if i == j else 0.0) for j in range(n)] for i in range(n)]
    deg = [sum(r) for r in a]
    out = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            out[i][j] = a[i][j] / math.sqrt(max(deg[i] * deg[j], 1e-9))
    return out


def dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def in_bounds(x: int, y: int, size: int) -> bool:
    return 0 <= x < size and 0 <= y < size


def is_interfering(x: int, y: int, scene: Scene, clearance: float) -> bool:
    if not in_bounds(x, y, scene.size):
        return True
    for w in scene.works:
        if dist(x, y, w.x, w.y) <= (w.radius + clearance):
            return True
    return False


def graph_from_scene(scene: Scene, robot_xy: tuple[int, int], inspected: list[int]) -> tuple[list[list[float]], list[list[float]]]:
    # node0=robot, node1..=work
    rx, ry = robot_xy
    n = 1 + len(scene.works)

    feats: list[list[float]] = []
    feats.append([1.0, 0.0, rx / scene.size, ry / scene.size, 1.0])  # robot node
    for i, w in enumerate(scene.works):
        feats.append([0.0, 1.0, w.x / scene.size, w.y / scene.size, 1.0 if inspected[i] else 0.0])

    adj = [[0.0 for _ in range(n)] for _ in range(n)]
    coords = [(rx, ry)] + [(w.x, w.y) for w in scene.works]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = dist(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            adj[i][j] = 1.0 / (1.0 + d)

    return feats, normalize_adjacency(adj)


class RiskGNN:
    """候補移動後のロボット干渉リスク（二値）を予測する簡易GNN。"""

    def __init__(self, in_dim: int, hidden_dim: int, seed: int = 0):
        rng = random.Random(seed)
        self.w1 = [[rng.gauss(0, 0.15) for _ in range(hidden_dim)] for _ in range(in_dim)]
        self.b1 = [0.0 for _ in range(hidden_dim)]
        self.w2 = [[rng.gauss(0, 0.15) for _ in range(hidden_dim)] for _ in range(hidden_dim)]
        self.b2 = [0.0 for _ in range(hidden_dim)]
        self.w_out = [rng.gauss(0, 0.2) for _ in range(hidden_dim)]
        self.b_out = 0.0

    def forward(self, x: list[list[float]], a: list[list[float]]) -> tuple[float, tuple]:
        h1 = relu(add_bias(matmul(matmul(a, x), self.w1), self.b1))
        h2 = relu(add_bias(matmul(matmul(a, h1), self.w2), self.b2))
        robot_emb = h2[0]  # node0
        logit = sum(robot_emb[i] * self.w_out[i] for i in range(len(self.w_out))) + self.b_out
        p = sigmoid(logit)
        return p, (x, a, h1, h2, robot_emb, p)

    def train_step(self, x: list[list[float]], a: list[list[float]], y: float, lr: float) -> float:
        # 出力層のみ更新（安定重視の軽量学習）
        p, cache = self.forward(x, a)
        _, _, _, _, robot_emb, _ = cache
        grad = (p - y)

        for i in range(len(self.w_out)):
            self.w_out[i] -= lr * grad * robot_emb[i]
        self.b_out -= lr * grad

        return -(y * math.log(max(p, 1e-8)) + (1 - y) * math.log(max(1 - p, 1e-8)))

    def predict_risk(self, x: list[list[float]], a: list[list[float]]) -> float:
        p, _ = self.forward(x, a)
        return p


def observe_gain(pos: tuple[int, int], visited: set[tuple[int, int]], size: int, sensor_range: int = 1) -> int:
    px, py = pos
    gain = 0
    for dx in range(-sensor_range, sensor_range + 1):
        for dy in range(-sensor_range, sensor_range + 1):
            nx, ny = px + dx, py + dy
            if in_bounds(nx, ny, size) and (nx, ny) not in visited:
                gain += 1
    return gain


def train_risk_model(model: RiskGNN, scene: Scene, samples: int, clearance: float, seed: int, lr: float):
    rng = random.Random(seed)
    inspected = [0] * len(scene.works)
    losses = []
    for _ in range(samples):
        x = rng.randrange(scene.size)
        y = rng.randrange(scene.size)
        feats, adj = graph_from_scene(scene, (x, y), inspected)
        label = 1.0 if is_interfering(x, y, scene, clearance) else 0.0
        losses.append(model.train_step(feats, adj, label, lr=lr))
    return sum(losses) / max(len(losses), 1)


def run_exploration(scene: Scene, model: RiskGNN, steps: int, clearance: float, risk_weight: float):
    robot = scene.robot_start
    visited: set[tuple[int, int]] = {robot}
    inspected = [0] * len(scene.works)
    interference_count = 0

    for _ in range(steps):
        # ワークを観測できたら inspected 更新
        for i, w in enumerate(scene.works):
            if dist(robot[0], robot[1], w.x, w.y) <= (w.radius + 1.5):
                inspected[i] = 1

        candidates = []
        for ax, ay in ACTIONS:
            nx, ny = robot[0] + ax, robot[1] + ay
            feats, adj = graph_from_scene(scene, (nx, ny), inspected)
            risk = model.predict_risk(feats, adj)
            gain = observe_gain((nx, ny), visited, scene.size)
            revisit_penalty = 1.2 if (nx, ny) in visited else 0.0
            stay_penalty = 0.8 if (nx, ny) == robot else 0.0
            score = gain - risk_weight * risk - revisit_penalty - stay_penalty
            candidates.append((score, risk, (nx, ny)))

        candidates.sort(key=lambda t: t[0], reverse=True)

        # 上位候補から、まず干渉しない手を優先採用
        nxt = robot
        risk = 1.0
        for score, cand_risk, cand in candidates:
            if in_bounds(cand[0], cand[1], scene.size) and not is_interfering(cand[0], cand[1], scene, clearance):
                nxt = cand
                risk = cand_risk
                break
        else:
            _, risk, nxt = candidates[0]
        if not in_bounds(nxt[0], nxt[1], scene.size):
            nxt = robot
        if is_interfering(nxt[0], nxt[1], scene, clearance):
            interference_count += 1
        robot = nxt
        visited.add(robot)

    explored = len(visited) / (scene.size * scene.size)
    inspected_rate = sum(inspected) / max(len(inspected), 1)
    return explored, inspected_rate, interference_count


def build_scene(size: int, n_works: int, seed: int) -> Scene:
    rng = random.Random(seed)
    works = []
    for _ in range(n_works):
        works.append(Work(x=rng.randrange(2, size - 2), y=rng.randrange(2, size - 2), radius=rng.uniform(0.8, 1.6)))
    robot_start = (1, 1)
    return Scene(size=size, works=works, robot_start=robot_start)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--size", type=int, default=24)
    p.add_argument("--works", type=int, default=8)
    p.add_argument("--steps", type=int, default=180)
    p.add_argument("--clearance", type=float, default=1.2)
    p.add_argument("--train-samples", type=int, default=1500)
    p.add_argument("--hidden", type=int, default=24)
    p.add_argument("--risk-weight", type=float, default=3.0)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    scene = build_scene(size=args.size, n_works=args.works, seed=args.seed)
    model = RiskGNN(in_dim=5, hidden_dim=args.hidden, seed=args.seed)

    loss = train_risk_model(
        model,
        scene,
        samples=args.train_samples,
        clearance=args.clearance,
        seed=args.seed,
        lr=0.06,
    )

    explored, inspected_rate, interference = run_exploration(
        scene,
        model,
        steps=args.steps,
        clearance=args.clearance,
        risk_weight=args.risk_weight,
    )

    print("--- Robot x Work 干渉回避探索 ---")
    print(f"train_loss={loss:.4f}")
    print(f"explored_ratio={explored:.3f}")
    print(f"inspected_rate={inspected_rate:.3f}")
    print(f"interference_events={interference}")


if __name__ == "__main__":
    main()
