import requests

API_URL = "http://127.0.0.1:8000/analyze_risk/"
THRESHOLD = 0.50

# Label: 1 = Scam, 0 = Legitimate
TEST_CASES = [
    {
        "name": "OTP phishing",
        "label": 1,
        "text": "Your bank account will be blocked today. Share your OTP immediately using this link."
    },
    {
        "name": "Fake investment returns",
        "label": 1,
        "text": "Invest 5000 today and receive guaranteed returns of 50000 tomorrow. Limited offer."
    },
    {
        "name": "Fake account recovery fee",
        "label": 1,
        "text": "Your crypto wallet is frozen. Pay a recovery fee to this personal account to unlock your funds."
    },
    {
        "name": "Impersonation",
        "label": 1,
        "text": "I am from bank security. Tell me your PIN and OTP immediately or your account will be permanently closed."
    },
    {
        "name": "Urgent suspicious payment",
        "label": 1,
        "text": "Your payment failed. Install this unknown app and enter your card number, CVV and OTP to receive a refund."
    },
    {
        "name": "Normal bank notification",
        "label": 0,
        "text": "Your bank statement for this month is available in the official banking app. Please sign in through the app to view it."
    },
    {
        "name": "Legitimate transaction alert",
        "label": 0,
        "text": "A purchase of 850 rupees was made using your card. If you do not recognize this transaction, contact your bank using the number on your card."
    },
    {
        "name": "Security advice",
        "label": 0,
        "text": "For your security, never share your password or OTP. Open the official bank app directly to review your account activity."
    },
    {
        "name": "Investment risk warning",
        "label": 0,
        "text": "Investments can lose value. Review the official product documents, fees and risks before investing. Returns are not guaranteed."
    },
    {
        "name": "Normal payment confirmation",
        "label": 0,
        "text": "Your payment of 1200 rupees was successful. You can view the transaction receipt in the official app."
    },
]

results = []
failed = 0

for case in TEST_CASES:
    try:
        response = requests.post(
            API_URL,
            files={
                "files": (
                    case["name"].replace(" ", "_") + ".txt",
                    case["text"],
                    "text/plain",
                )
            },
            timeout=120,
        )

        if response.status_code != 200:
            print(f'ERROR: {case["name"]}: HTTP {response.status_code}')
            print(response.text[:300])
            failed += 1
            continue

        data = response.json()
        verdict = data.get("final_verdict", {})
        probability = float(verdict.get("probability", -1))

        risk_level = verdict.get("risk_level", "Unknown")
        analysis = verdict.get("analysis", "")

        if (
            risk_level == "Unknown"
            or analysis.startswith("AI reasoning failed:")
        ):
            print(f'FAILED: {case["name"]}: AI analysis did not complete')
            failed += 1
            continue

        if probability < 0 or probability > 1:
            print(f'ERROR: Invalid probability for {case["name"]}: {probability}')
            failed += 1
            continue

        predicted = int(probability >= THRESHOLD)

        results.append({
            "name": case["name"],
            "actual": case["label"],
            "predicted": predicted,
            "probability": probability,
        })

        actual_text = "SCAM" if case["label"] else "LEGIT"
        predicted_text = "SCAM" if predicted else "LEGIT"

        print(
            f'{case["name"]}: actual={actual_text}, '
            f'predicted={predicted_text}, probability={probability:.3f}, '
            f'risk_level={risk_level}'
        )

    except Exception as exc:
        print(f'ERROR: {case["name"]}: {exc}')
        failed += 1

tp = sum(r["actual"] == 1 and r["predicted"] == 1 for r in results)
tn = sum(r["actual"] == 0 and r["predicted"] == 0 for r in results)
fp = sum(r["actual"] == 0 and r["predicted"] == 1 for r in results)
fn = sum(r["actual"] == 1 and r["predicted"] == 0 for r in results)

precision = tp / (tp + fp) if tp + fp else 0.0
recall = tp / (tp + fn) if tp + fn else 0.0
f1 = (
    2 * precision * recall / (precision + recall)
    if precision + recall else 0.0
)
accuracy = (tp + tn) / len(results) if results else 0.0

print("\n========== EVALUATION SUMMARY ==========")
print(f"Cases completed: {len(results)}/{len(TEST_CASES)}")
print(f"Cases failed:    {failed}")
print(f"Threshold:       {THRESHOLD:.2f}")
print("\nConfusion matrix counts:")
print(f"True Positives (TP):  {tp}")
print(f"True Negatives (TN):  {tn}")
print(f"False Positives (FP): {fp}")
print(f"False Negatives (FN): {fn}")

print("\nMetrics:")
print(f"Precision: {precision:.3f}")
print(f"Recall:    {recall:.3f}")
print(f"F1-score:  {f1:.3f}")
print(f"Accuracy:  {accuracy:.3f}")

print("\nNote: This is a small smoke test, not a formal model benchmark.")
print("Review failed cases and confirm the labels before drawing conclusions.")
