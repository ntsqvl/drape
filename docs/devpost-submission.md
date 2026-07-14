# Devpost submission text

**Project name:** DRAPE — a personal color draping studio
**Track:** Skin AI + Apparel VTO (combined)
**Repo:** https://github.com/ntsqvl/drape · **Video:** (YouTube link)

---

## Inspiration

Personal color analysis — the "12-season" draping session — is a booming ritual: people pay $150–300, book studios weeks out, and travel for appointments where a colorist holds fabric drapes to their face and watches their skin react. The method is real, but the access isn't. Meanwhile, the same question drives one of retail's biggest costs: color-mismatch returns from purchases made on a guess.

We realized YouCam's APIs contain both halves of a draping session: the **eyes** (AI Facial Color Tones Analyzer + AI Skin Analysis read the client's coloring) and the **drapes** (AI Clothes VTO renders any fabric color on the client's own body — better than fabric held near a chin).

## What it does

One selfie in, and an agent runs a three-round draping session:

1. **Reads you.** Facial Color Tones Analyzer returns your skin/hair/eye/eyebrow/lip colors; Skin Analysis (SD) reads today's redness and radiance, so saturated reds get demoted on a flare-up day.
2. **Drapes you.** Round one renders a warm-gold and a cool-orchid drape on your body (Clothes VTO) and scores the **measured pixels** of each render in CIELAB. Rounds two and three narrow depth, then sub-season — about 8 renders instead of a naive 16, chosen adaptively.
3. **The verdict.** Your season with an honest confidence level (it tells you which round was the close call), a best-vs-worst reveal on your own body, and an **interactive palette**: click any swatch and it's rendered on you.
4. **Retail.** A demo rack re-sorted by match score with plain-language reasons — and a garment checker: drop a product photo from *any* store, get a match verdict before you buy, then see it on you. Plus a shareable verdict card.

## How we built it

FastAPI + React. Three YouCam features chained with a closed feedback loop — VTO output is *measured* (shading-corrected extraction: hue/chroma from the dominant cluster, lightness from the 75th percentile of garment pixels) and drives which drape gets rendered next. The decision logic is a deterministic tree shared between the live agent and a renderless classifier, which let us calibrate against a **golden set of 36 season archetypes: 100% temperature, 100% family, 92% exact sub-season**, enforced as regression tests (42-test suite, whole pipeline runs offline against a pixel-honest mock engine).

## Challenges we ran into

- The tone analyzer returns hex colors but **no undertone field** — we derive temperature from Lab b*/chroma, with lip color as secondary evidence.
- Face-size checks are strict and stochastic near the boundary. Since failed tasks are billed-then-refunded (net zero), we use **the API itself as the face detector**: try full frame, retry with tighter center crops for free. Cloth try-on keeps the original frame (it needs your shoulders).
- The tone analyzer misread black hair as pale blonde on a cropped photo — eyebrows track natural hair depth, so a large hair/eyebrow disagreement swaps in the eyebrow reading.
- Depth probe drapes must be lightness-matched: the pair's midpoint *is* the light/deep boundary. Our golden set caught a mis-centered pair silently misclassifying mid-light warm people.

## Accomplishments we're proud of

Two independent live sessions on the same person — different framing paths, one containing the hair misread — converged on the same verdict. The whole session costs ~45 units, with a reserve floor, per-IP caps, and content-hash caching so replays are free.

## What's next

Drift telemetry already accumulates with every live render (requested vs. measured ΔE) — the calibration dataset for tightening the harmony engine. Then: YouCam Camera Kit guided capture to eliminate framing failures at the source, and palette-filtered catalog integrations for retailers.

---

### Built with
Python · FastAPI · React · Vite · Pillow · YouCam AI Facial Color Tones Analyzer · YouCam AI Skin Analysis (SD) · YouCam AI Clothes VTO (cloth-v3)

### Notes for judges
- The deployed demo defaults to **demo personas** (offline mock engine, zero units, can't fail) — the "live" chip in the masthead shows real unit balance when you upload your own selfie.
- DRAPE is a heuristic implementation of the 12-season draping method — a formalization of a subjective craft — not a clinically validated assessment, and the UI says so.
