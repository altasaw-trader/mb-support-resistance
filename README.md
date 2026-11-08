# MB Support & Resistance — 28 Forex pairs

A mobile-friendly GitHub Pages dashboard showing the six nearest confirmed swing resistance levels above the latest available close and six nearest confirmed swing support levels below it, for M30/H1/H4/D1.

## Data & limitations
- Yahoo Finance unofficial FX data, **not** FundedNext quotes.
- M30: last ~59 calendar days; H1: ~700 days; H4: derived from H1 (UTC 4-hour buckets); D1: ~3 years. Yahoo may restrict data further.
- Confirmed pivots require three bars to the left and three bars to the right. Near-duplicate levels are clustered. There may be fewer than six valid levels; unavailable levels display `—`.
- Values are refreshed by scheduled GitHub Actions, not live tick-by-tick.
- The script keeps the last valid data marked `stale` if a fetch fails.

## Deployment
1. Create a GitHub repository (e.g. `mb-support-resistance`).
2. Upload `index.html`, `update.py`, `requirements.txt`, `README.md`, and the hidden `.github/workflows/update.yml` folder (preserve its path).
3. In repository Settings → Pages, select Deploy from a branch → main → /(root).
4. In Actions → Update MB Support Resistance → Run workflow, run once to create `data.json`.
5. If commit fails due to permissions: Settings → Actions → General → Workflow permissions → Read and write permissions.
6. Open `https://YOUR_USERNAME.github.io/mb-support-resistance/` after deployment.

To **replace** an existing `mb-average` site instead, back it up first and replace the same files in that repo; the existing `update.yml` should be replaced/removed to prevent competing jobs. Use the same existing GitHub Pages URL.
