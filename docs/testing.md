# Acceptance test matrix

Automated tests cannot prove that today's Instagram layout still matches. Before publishing the demo, run this manual matrix with content you are authorized to access.

| Case | UI | Expected evidence |
|---|---|---|
| Public Post with comments | English | Correct URL remains open; CSV/XLSX contain genuine rows |
| Public Reel with comments | English | Comment dialog opens; Reel does not change during scroll |
| Post with replies | English | No parent comment copied under several reply usernames |
| Reel with replies | English | No `likes`, `Edited`, or `View all replies` records |
| No-comment/disabled comments | English | Clear warning or empty export; exit code 2 |
| Invalid/private/deleted URL | English | Actionable error; no traceback required from user |
| Signed-out profile | English | Login-required guidance |
| One Post or Reel | Vietnamese fallback | Supported labels work; document any missing label |

For each successful live case, manually compare at least 20 exported username/comment pairs against the browser and record: visible count, exported count, mismatches, interface rows, elapsed time, and date. Do not claim 100% recall unless measured on a finite, fully visible dataset.
