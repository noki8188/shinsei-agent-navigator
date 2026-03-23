from __future__ import annotations

import unittest

from app.evals import evaluate_backend
from app.runtime import WorkflowSettings


class RepresentativeScenarioEvalTest(unittest.TestCase):
    def test_representative_scenarios_pass_rule_based_eval(self) -> None:
        results = evaluate_backend(WorkflowSettings(workflow_backend="rule_based"))
        failed = [result for result in results if not result.success]
        self.assertFalse(
            failed,
            msg="\n".join(
                f"{result.name}: {', '.join(result.issues)}" for result in failed
            ),
        )


if __name__ == "__main__":
    unittest.main()
