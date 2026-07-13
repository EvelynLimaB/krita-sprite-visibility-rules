# Contributing

1. Keep the rule engine and storage schema independent of Krita/PyQt where possible.
2. Add regression tests for every behavior change.
3. Run `python scripts/build_release.py` and `python -m unittest discover -s tests -v`.
4. Do not depend on internal Layers-docker widgets; use the public libkis API.
5. Schema changes require migration code and a schema-version bump.
