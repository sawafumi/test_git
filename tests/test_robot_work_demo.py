import unittest

import gnn_interference_avoidance as demo


class RobotWorkDemoTest(unittest.TestCase):
    def test_risk_mode_reduces_interference_vs_baseline(self):
        scene = demo.build_scene(size=24, n_works=8, seed=7)
        model = demo.RiskGNN(in_dim=5, hidden_dim=24, seed=7)
        demo.train_risk_model(model, scene, samples=1200, clearance=1.2, seed=7, lr=0.06)

        _, _, interference_risk = demo.run_exploration(
            scene, model, steps=160, clearance=1.2, risk_weight=3.0, use_risk=True
        )
        _, _, interference_base = demo.run_exploration(
            scene, model, steps=160, clearance=1.2, risk_weight=3.0, use_risk=False
        )

        self.assertLessEqual(interference_risk, interference_base)


if __name__ == "__main__":
    unittest.main()
