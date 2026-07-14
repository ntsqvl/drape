# DRAPE demo video — shooting script (3:00, judges stop at 3:00)

**Setup before recording**
- Record the browser window at 1440×900+, 60fps if possible (QuickTime: File → New Screen Recording, or OBS). No music (rules: no copyrighted material). Voiceover can be recorded separately over the cut.
- Backend live (`YOUCAM_MOCK=0`), your real selfie ready. Your session's renders are already disk-cached, so the "live" session replays instantly — either record the cached run and say so, or delete `.cache/youcam` for authentic waits and cut them in editing.
- Have one product photo from a real store saved for the garment check.
- Keep the unit chip visible — it quietly proves the budget story.

---

**0:00–0:18 — Hook** *(screen: upload page, slow scroll)*

> "A personal color analysis costs about two hundred dollars and a studio appointment. A colorist holds fabric drapes to your face and watches your skin react. DRAPE runs that session from one selfie — with the drapes rendered on your own body."

On-screen text (add in edit): **Built on YouCam AI Facial Color Tones Analyzer · AI Skin Analysis · AI Clothes VTO**

**0:18–0:40 — Upload + photo QC** *(screen: drop selfie, preview in the oval mirror, precheck line appears)*

> "Drop a selfie. Before a single API unit is spent, DRAPE checks the photo — resolution, exposure, color cast — because a warm lamp can skew an undertone reading."

Click **Begin draping**.

**0:40–1:25 — The draping session** *(screen: session screen; the trace streams while renders appear in the mirror)*

> "This is an agent running a real draping appointment. Round one: a warm gold drape against a cool orchid — both rendered on me by YouCam's generative try-on, both measured in Lab color space from the actual pixels. Warm wins, so round two tests depth. Round three picks between neighboring seasons. Eight renders instead of sixteen — the agent only renders what the previous round makes relevant. If a photo fails the face check, it retries with a tighter crop for free — failed tasks are refunded."

*(Let 2–3 trace lines be readable; speed up waits in edit.)*

**1:25–1:50 — The verdict + reveal** *(screen: season name lands, then the side-by-side)*

> "The verdict: my season, with an honest confidence level — it tells you which round was the close call. And the reveal every draping studio sells: me in my best color, next to me in my worst."

**1:50–2:10 — Interactive draping room** *(screen: click 2–3 swatches in the fan; mirror re-drapes)*

> "The palette isn't a chart — it's a fitting room. Click any swatch and it's rendered on you. Two API units the first time, free from cache after."

**2:10–2:40 — Shop + check-a-garment** *(screen: shop rack with match badges, then upload the store product photo, badge appears, click "See it on you")*

> "Every garment on the rack is scored against my palette, with a reason. And the part I actually want as a shopper: drop a product photo from any store, and DRAPE scores it before you buy — then shows it on you. That's the moment before a purchase where returns are born."

**2:40–3:00 — Close** *(screen: click "Save your card", show the PNG; end card slide)*

> "Your verdict becomes a card you can share. Three YouCam API features, one agentic loop, forty-five units per session. DRAPE — which colors were made for you."

End slide (add in edit): **DRAPE — github.com/ntsqvl/drape · Built with YouCam API (Skin AI + Apparel VTO track)**

---

**Editing checklist**
- Total ≤ 3:00 (judges are not required to watch past three minutes).
- Footage shows the project running in the browser (requirement).
- The YouCam APIs are named on screen and in narration (requirement).
- No third-party trademarks beyond YouCam/Perfect Corp., no music.
- Upload public to YouTube; paste the link in the Devpost form.
