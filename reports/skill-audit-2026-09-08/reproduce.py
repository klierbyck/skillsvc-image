"""运行修复后的安全回归；历史缺陷复现保存在 reproduce_before_fix.py。"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_security_regressions.py"
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
