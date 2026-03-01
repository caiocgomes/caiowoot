## 1. Backend

- [x] 1.1 Add history stats to GET /review response: count validated (not rejected, not promoted), rejected, and promoted annotations
- [x] 1.2 Rename stats labels: "total_confirmed" → "total_accepted" in the response

## 2. Frontend - Stats

- [x] 2.1 Update review stats rendering: rename "confirmadas" → "aceitas", add history stats row (validadas, rejeitadas, promovidas)

## 3. Frontend - Rules Section

- [x] 3.1 Add rules list section in sidebar below pending annotations (fetch GET /rules, render each rule with toggle switch and text)
- [x] 3.2 Add toggle on/off for rules (call PATCH /rules/{id}/toggle, update UI)
- [x] 3.3 Add inline edit for rule text (click to edit, save calls PUT /rules/{id})

## 4. Frontend - Rules Detail

- [x] 4.1 Add rule detail view in main area when clicking a rule (show full text, source annotation if available, edit/toggle/delete actions)
