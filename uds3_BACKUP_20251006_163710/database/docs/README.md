Database docs for the `database` package

Overview
--------
This folder contains per-module documentation for the core files in the
`database` package. Each file documents purpose, main API, tests and a short
roadmap for improvements.

Quick Links
-----------
- Project reference: `PROJECT_CODE_REFERENCE.md`
- Tests overview: `tests_overview.md`

How to extend
-------------
Add a new file `docs/<module>.md` following the style of existing files. Keep
sections: short description, analysis, main API, tests coverage and roadmap.

Generating HTML
---------------
For a simple static view, you can use `mkdocs` or `Sphinx`.

Example (mkdocs):

```powershell
pip install mkdocs
mkdocs new docs_site
# copy `database/docs` into docs_site/docs and add nav entries
mkdocs serve
```

Contributing
------------
- Keep docs up-to-date when you change the public API of a module
- Add usage examples where helpful
- Keep the docs small and focused on the developer audience
