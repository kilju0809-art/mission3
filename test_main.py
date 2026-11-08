import json
import tempfile
import unittest
from pathlib import Path

from main import analyze_json, classify, generate_pattern, mac_1d, mac_2d


class MacTests(unittest.TestCase):
    def test_cross_and_x_scores(self):
        cross = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
        pattern = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
        self.assertEqual(mac_2d(cross, pattern), 1)
        self.assertEqual(mac_1d(pattern, pattern), 5)

    def test_tie_classification(self):
        self.assertEqual(classify(1.0, 1.0 + 1e-10), "UNDECIDED")

    def test_json_analysis(self):
        results = analyze_json(Path(__file__).with_name("data.json"))
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item["passed"] for item in results))

    def test_pattern_generation(self):
        pattern = generate_pattern(5, "x")
        self.assertEqual(pattern[0][0], 1)
        self.assertEqual(pattern[0][2], 0)

    def test_invalid_matrix(self):
        with self.assertRaises(ValueError):
            mac_2d([[float("nan")]], [[1]])


if __name__ == "__main__":
    unittest.main()
