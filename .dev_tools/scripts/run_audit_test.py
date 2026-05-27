import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.database import SessionLocal
from backend.agent import AuditAgent

db = SessionLocal()
agent = AuditAgent(db)

for i in range(1, 6):
    result = agent.audit_invoice(i)
    print(f"Invoice {i}: risk_score={result['risk_score']}, status={result['status']}, findings={result['findings_count']}")
    for f in result.get("findings", []):
        print(f"  -> {f['severity']}: {f['title']}")

db.close()
