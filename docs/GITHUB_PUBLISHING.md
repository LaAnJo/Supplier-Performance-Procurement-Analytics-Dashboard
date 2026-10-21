# Publish this as its own GitHub repository

**Suggested GitHub repository:** `Supplier-Performance-Procurement-Analytics`

1. Extract the downloaded ZIP outside Downloads, e.g. into `Documents/GitHub-Projects/Supplier_Performance_Procurement_Analytics`.
2. Open the extracted folder in VS Code. Read `LICENSE_NOTE.md` and exclude any original or derived dataset you are not authorized to redistribute.
3. Run `python -m src.pipeline` and `python -m pytest -q` after installing requirements. Confirm your outputs.
4. Sign in to GitHub and create an **empty repository** with the suggested name (do not initialize with a README or `.gitignore`).
5. In VS Code terminal, from your extracted project folder:

```powershell
git config user.name "LaAnJo"
git config user.email "62889201+LaAnJo@users.noreply.github.com"
git init -b main
git status
git add .
git diff --cached --stat
git commit -m "feat: build supplier procurement analytics demo"
git remote add origin https://github.com/LaAnJo/Supplier-Performance-Procurement-Analytics.git
git push -u origin main
```

**For an existing repository:** always `git clone` the repository first, copy these files inside, then `git add`, `git commit` and `git push`; do not force-push or overwrite its history.

**To keep working professionally:** use branches for features, commit logical units, push and open PRs. For changes made directly on the GitHub site, run `git pull --ff-only origin main` locally before editing.

**Do not claim a real Power BI `.pbix` is in this repository.** The guide and DAX exist; the `.pbix` must be built separately with Power BI Desktop.
