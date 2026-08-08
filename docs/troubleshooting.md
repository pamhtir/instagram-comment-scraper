# Troubleshooting

## The comment surface temporarily disappears

Instagram can replace the Post/Reel dialog while comments are loading. Version 1.0.1 retries the surface automatically. If recovery still fails after the configured attempts, comments already collected are exported instead of discarded. Increase `SURFACE_RECOVERY_ATTEMPTS` only if your connection is unusually slow.

| Message or symptom | Meaning | Action |
|---|---|---|
| Chrome could not start | Dedicated profile is locked or Chrome/driver failed | Close Chrome windows using that profile; retry |
| Login is required | Profile has no valid session | Run visibly and sign in manually |
| Verification required | Instagram challenged the session | Complete it manually; do not automate bypasses |
| Content unavailable | URL is private, deleted, invalid, or inaccessible | Verify authorization and visibility in the same profile |
| Comment surface not found | Layout changed or comments are unavailable | Retry visibly; preserve a redacted screenshot for debugging |
| No visible comments | Nothing loaded or selectors no longer match | Use `--log-level DEBUG`; complete the manual test matrix |
| XLSX permission error | Workbook is open or folder is protected | Close Excel or choose another `--output` path |
| Very slow run | Replies, throttling, or long waits | Try `--no-replies --max-comments N`; do not parallelize immediately |

Paste a plain URL. Markdown syntax is repaired, but plain URLs are clearer. Never upload `.env`, profile folders, cookies, or unredacted debug HTML when requesting support.
