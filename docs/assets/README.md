# Capture the real synthetic UI

Screenshot pending: no browser was available in the implementation environment.
No image has been fabricated. Intended committed path: `docs/assets/synthetic-demo.png`.

1. Install dependencies as in the root README, then run `python demo_presentation.py`.
2. Run `python -m streamlit run app.py --browser.gatherUsageStats false`.
3. Open the local URL printed by Streamlit (normally http://localhost:8501).
4. Select **Synthetic Demo**, never **Latest saved live run**. Wait for map assets.
5. Capture the real browser view at a width where the SYNTHETIC DEMO label,
   invented-scenario explanation, map, status text and limitations remain readable.
   Keep map attribution visible; use browser zoom/full-page capture if needed.
6. Inspect the image: no credentials, personal browser details, live traffic or
   misleading real-incident claim. Save it as `docs/assets/synthetic-demo.png`.
7. Replace the pending note/comment in README with its supplied Markdown image link.

Review the actual rendered screenshot before committing. Do not create a mock
screenshot, edit labels out, or add runtime live bundles alongside it.
