"""dtree-encoding 1.9.0 only forwards to triordinal-dtree; the full tests live in Triordinal."""

import os
import sys
import unittest
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestForward(unittest.TestCase):
    def test_import_warns_and_forwards(self):
        sys.modules.pop("dtree", None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import dtree
        self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))
        import triordinal.dtree
        self.assertIs(dtree.DTree, triordinal.dtree.DTree)
        t = dtree.DTree()
        t.insert("A", "B")
        t.insert("B", "C")
        self.assertTrue(t.can_reach("A", "C"))
        self.assertEqual(dtree.__version__, "1.9.0")


if __name__ == "__main__":
    unittest.main()
