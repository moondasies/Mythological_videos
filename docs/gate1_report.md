# Gate 1 — Research, Creative Direction and Production Feasibility

Date: 2026-11-05 · Status: **PARTIAL. Waiting on your inputs (see §5)**

## 1. Timing: the Ramayana film
- *Ramayana: Part 1* (dir. Nitesh Tiwari; Ranbir Kapoor as Rama, Sai Pallavi as Sita, Yash as Ravana; prod. Namit Malhotra) was **reported for a worldwide release on 5 November 2026, which is today**. Part 2 is planned for Diwali 2027.
- Trade reports show heavy advance bookings (more than ₹63 cr globally as of 1 Nov).
- Reports conflict (5 Nov, 6 Nov, 8 Nov). I could not reach a primary producer or studio announcement, so treat the date as reported, not verified.
- **Implication:** Audience interest is peaking now and should stay high through the Diwali run and up to Part 2. The pilot should not chase the film's specific scenes or likenesses. Our designs must be original and must not resemble the film's actors or costumes.
- Sources: [Telangana Today (Nov 5 date)](https://telanganatoday.com/ramayana-part-1-release-date-confirmed-for-november-5-2026), [Sacnilk advance bookings](https://www.sacnilk.com/news/ramayana-worldwide-advance-booking-crosses-2-million-for-opening-day-ahead-of-november-5-release), [The Week](https://www.theweek.in/news/entertainment/2026/11/01/ramayana-part-1-advance-bookings-collection-update.amp.html), [Onmanorama (2024 two-part announcement)](https://onmanorama.com/entertainment/entertainment-news/2024/11/06/ranbir-kapoor-sai-pallavi-ramayana-release-poster-out.html), [Outlook (Nov 6 report)](https://www.outlookindia.com/art-entertainment/ramayana-release-date-out-ranbir-kapoor-starrer-to-hit-theatres-2-days-ahead-of-diwali)

## 2. Topic research
I researched 12 candidates. Full records and scoring are in [`research/ramayana_topic_research.md`](../research/ramayana_topic_research.md).

| Rank | Topic | Score | Source |
|---|---|---:|---|
| 1 | **Trijata's dream** (recommended) | 4.65 | Valmiki, Sundara Kanda, Sarga 27 |
| 2 | Sampati, the brother who burnt his wings | 4.55 | Kishkindha Kanda, Sargas 56–63 |
| 3 | Ahalya: invisible, not stone, in Valmiki | 4.50 | Bala Kanda, Sargas 48–49 |

**Why Trijata:**
- It is one contained scene at night in Ashoka Vatika, so it fits in 60 seconds without cutting corners on accuracy.
- The cast is small, which keeps character consistency manageable for a first pilot.
- The dream imagery (white versus red, Lanka sinking) is visually striking.
- The source is clean, with a known later-tradition caveat (Trijata as Vibhishana's daughter) that we label honestly.

## 3. Reference-channel analysis — BLOCKED
I have not received the channel links yet. The container's network policy also **denies youtube.com** (proxy returns 403), so I cannot open the channels from here.

Even with access, I can't honestly "watch" a video by reading its title or transcript. For a real analysis, please provide, for each channel, one of the following:
- 3–5 downloaded video files (MP4) in `references/channels/<channel>/`, or
- network access to youtube.com and the links. In that case I can pull metadata and transcripts, but **not** watch the visuals, and I will state that limitation in the analysis.

## 4. Production feasibility (inspected in this container)
| Capability | Status | Notes |
|---|---|---|
| Project repo | Empty | Folder structure, configs and docs scaffolded in this commit |
| ffmpeg | ✅ Available | Compositing, parallax, mixing, subtitles and export are all possible locally |
| Python 3 + Pillow/NumPy | ✅ | For the layer and parallax engine and QA frame checks |
| Node 22, Playwright/Chromium | ✅ | Can be used for subtitle and typography rendering |
| Devanagari font | ❌ Not installed | Can install Noto Sans Devanagari from npm or PyPI (both allowed) |
| **ElevenLabs API** | ❌ **Network-blocked** | `api.elevenlabs.io` is denied by the environment network policy |
| **Image generation** | ❌ **None available** | There is no image model in the container and no provider key. A provider is required (see below) |
| **Image-to-video / motion** | ❌ None | Optional. Subtle motion can be built locally (see below) |
| youtube.com / scripture sites | ❌ Network-blocked | Research went through web search only |

### Recommended visual pipeline (subject to testing)
1. **Character sheets:** Generate front, ¾ and side views plus expressions with an image model that supports **reference-image conditioning**. Then lock the approved sheets.
2. **Scenes as layers:** Each shot gets its own background plate, character layer(s) and FX layer (mist, leaves, fireflies, diya flicker).
3. **Motion, local and controllable:** 2.5D parallax, blink and breathe loops made from 2–3 eye-state frames, wind on cloth through mesh warps, and particle FX. All of it is built in Python and ffmpeg. This avoids "zoom on a still" and avoids the identity drift of generative video.
4. **Optional generative video:** For 1–3 hero shots only, after a consistency test.

**Decision needed:** Which image provider can you give access to? Options include OpenAI image models, Google Imagen/Gemini, Ideogram, Leonardo, Midjourney (no official API), or Replicate/fal (Flux + LoRA, which gives the best consistency control). The choice affects cost and how consistent the characters are. I will test before committing to one.

### Voice
- ElevenLabs is the right first test. Its multilingual models support Hindi, and it offers pronunciation dictionaries (alias rules), so it fits our requirements on paper. **Not yet tested.**
- **Secure key setup:** Do not paste the key into chat. Add `ELEVENLABS_API_KEY` as a secret or environment variable in the cloud environment settings, and add `api.elevenlabs.io` to Allowed domains. `.env` is git-ignored, and the code reads only from the environment.
- **Fallback if quality fails:** Azure Neural TTS (hi-IN voices with SSML phonemes) or Google Cloud TTS (hi-IN). I would report the failure before switching, not after.

### Expected cost (estimate, to be confirmed with your plans)
- **ElevenLabs:** A 60 s narration is about 900–1,100 characters. With 10–20 takes and auditions, that comes to roughly 20–30k characters, which fits within the Starter or Creator tiers.
- **Images:** About 60–150 generations for character sheets, scenes and retakes. Depending on the provider, that is roughly US$3–$20.
- **Generative video (optional):** About US$1–$10 for a few hero shots.
- **Music:** Use a royalty-free library you already license, or I can compose a simple drone/bansuri-style bed procedurally. A procedural bed is clean to license but lower in quality.

**No paid API has been called yet. Cost so far: $0.**

## 5. What I need from you
1. **Four reference-channel links.** For a true visual analysis, also 3–5 video files per channel.
2. **2–3 illustration style images.** Upload them to `references/style_images/` or attach them in chat.
3. **Image-generation provider choice and access** (key as an environment secret, plus its domain allowlisted).
4. **Approval of the topic direction:** Trijata (recommended), Sampati or Ahalya.
5. Later (Gate 2): the ElevenLabs key configured as a secret, with `api.elevenlabs.io` allowlisted.

Once items 1–2 arrive, I'll complete the reference analysis and the style direction and present the full Gate 1 package.
