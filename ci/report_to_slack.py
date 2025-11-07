import os, json, sys, requests, pathlib
webhook = os.environ.get("SLACK_WEBHOOK_URL")
summary = {"status":"unknown","passed":0,"failed":0,"total":0}
p = pathlib.Path("newman_report.json")
if p.exists():
  try:
    data = json.loads(p.read_text(encoding="utf-8"))
    run = data.get("run",{})
    failures = run.get("failures",[]) or []
    total = run.get("stats",{}).get("requests",{}).get("total",0)
    summary["failed"] = len(failures)
    summary["total"] = total
    summary["passed"] = max(total - len(failures), 0)
    summary["status"] = "PASS" if len(failures)==0 else "FAIL"
  except Exception as e:
    summary["status"] = f"error parsing report: {e}"
msg = f"*Nightly Doc vs API*: {summary['status']} — {summary['passed']}/{summary['total']} passed"
print(msg)
if webhook:
  requests.post(webhook, json={"text": msg}, timeout=10)