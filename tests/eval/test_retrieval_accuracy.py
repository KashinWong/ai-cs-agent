"""SC-002 门禁（T043b）：中/英评测集正确率 >= 90%。

无服务/无 WEBHOOK_TOKEN 时自动 skip，不阻塞单元测试；带服务环境（CI/本地 compose）
下作为「未验证不上线」的硬门禁。
"""
import os

import httpx
import pytest

BASE = os.environ.get("AI_CS_BASE", "http://localhost:8000")
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "")


def _reachable() -> bool:
    if not WEBHOOK_TOKEN:
        return False
    try:
        return httpx.get(f"{BASE}/api/v1/health", timeout=2).status_code in (200, 503)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _reachable(), reason="backend/WEBHOOK_TOKEN not available for eval"
)


def test_bilingual_accuracy_threshold():
    from tests.eval.run_eval import main

    report = main()
    for ds, rate in report.items():
        assert rate >= 0.90, f"{ds} accuracy {rate:.0%} < 90% (SC-002)"
