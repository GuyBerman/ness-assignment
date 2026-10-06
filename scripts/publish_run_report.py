"""Copy the last run's reports to docs/run-report/.

Traces and saved page HTML are left out, since they contain session cookies and location.

    python scripts/publish_run_report.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TARGET = ROOT / "docs" / "run-report"


def _strip_traces(results: Path) -> None:
    for result in results.glob("*-result.json"):
        data = json.loads(result.read_text(encoding="utf-8"))

        def keep(att: dict) -> bool:
            return not att.get("source", "").endswith((".zip", ".html"))

        def clean(node: dict) -> None:
            node["attachments"] = [a for a in node.get("attachments", []) if keep(a)]
            for step in node.get("steps", []):
                clean(step)

        clean(data)
        result.write_text(json.dumps(data), encoding="utf-8")
    for extension in ("zip", "html"):
        for path in results.glob(f"*-attachment.{extension}"):
            path.unlink()


def main() -> None:
    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True)

    shutil.copy2(REPORTS / "report.html", TARGET / "report.html")
    shutil.copy2(REPORTS / "junit.xml", TARGET / "junit.xml")
    shutil.copytree(REPORTS / "screenshots", TARGET / "screenshots")

    results = TARGET / "_allure-results"
    shutil.copytree(REPORTS / "allure-results", results)
    _strip_traces(results)
    subprocess.run(
        ["npx", "--yes", "allure@3", "generate", str(results), "-o", str(TARGET / "allure-report")],
        check=True,
    )
    shutil.rmtree(results)
    print(f"Published run report to {TARGET}")


if __name__ == "__main__":
    main()
