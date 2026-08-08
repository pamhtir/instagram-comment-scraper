# Contributing

1. Create a focused branch.
2. Never add live credentials, browser data, client data, or copied Instagram HTML.
3. Add or update offline tests for behavioral changes.
4. Run `python -m pytest -q` and `python -m compileall -q main.py src tests`.
5. Explain selector assumptions and user-visible limitations in the pull request.

Live-site tests must use content and accounts the tester is authorized to access; they must not run in CI.
