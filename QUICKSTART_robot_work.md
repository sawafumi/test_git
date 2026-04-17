# Robot×Work 干渉回避デモのクイックスタート

## 1) まず動かす
```bash
python gnn_interference_avoidance.py --seed 7 --train-samples 1200 --steps 160 --compare-baseline
```

## 2) ざっくり見方
- `explored_ratio`: 探索できたセル割合
- `inspected_rate`: 観測できたワーク割合
- `interference_events`: 干渉イベント数（小さいほど良い）

`--compare-baseline` を付けると、
- GNNリスクあり（本手法）
- risk未使用（ベースライン）
の2つが並んで出ます。

## 3) パラメータ調整
- 干渉をさらに減らしたい: `--risk-weight` を上げる（例: `4.0`）
- 探索を広げたい: `--steps` を増やす
- 学習を丁寧に: `--train-samples` を増やす
