# Performance and completeness

## Safe speed controls

- `--max-comments N` stops as soon as the business target is met.
- `--no-replies` avoids expensive expansion when replies are out of scope.
- `STABLE_ROUNDS` controls the no-growth stop condition; reduce only after live testing.
- `PAUSE_MIN_SECONDS` and `PAUSE_MAX_SECONDS` trade speed for stability.
- Extraction and scrolling stay inside the comment surface and cache IDs.
- One browser-side DOM snapshot replaces repeated Selenium calls for every row.
- The panel jumps to its current bottom and uses visible-tail/scroll geometry instead of profile-link counts, which remain constant under Instagram virtualization.
- No-progress waits default to four seconds rather than twelve; successful DOM changes return sooner.

`clicked=0` is not automatically an error: many Instagram layouts lazy-load by
scrolling and expose no text button. Judge completeness by growth in `unique`,
manual browser comparison, and the acceptance matrix—not by `clicked` alone.

Do not begin with parallel tabs, multiple sessions, or aggressive zero-delay settings. They raise memory use, profile-lock risk, throttling, verification, instability, and cross-target data risk.

## Why totals vary

Instagram dynamically ranks and loads comments. Visibility can vary by account, region, UI experiment, moderation, deletion, hidden comments, replies, network state, and access limits. The honest promise is “collects publicly visible comments loaded in the authorized browser session,” not “every comment from any URL.”

Official, authorized APIs are preferable for stable high-volume client work when access and use case permit.
