# Hindu Mythology — Hidden Stories (Pilot Workspace)

Phase 1: ONE Ramayana pilot, gated approvals. No automatic publishing.

Pipeline: Research → Verification → Topic → Script → Storyboard → Characters → Scenes → Animation → Voice → Music → Subtitles → Edit → QA → Export

| Folder | Purpose |
|---|---|
| `docs/` | Creative bible, gate reports |
| `research/` | Topic research + per-video fact-check files |
| `references/` | Reference channels & style images (user-supplied) |
| `config/` | Reusable style/voice/subtitle/mix/export settings |
| `characters/` `storyboard/` `scripts/` `scenes/` `audio/` `subtitles/` `renders/` `qa/` | Production stages (per-scene regeneration) |
| `pipeline/` | Code (built after Gate 1) |

Secrets: set `ELEVENLABS_API_KEY` etc. as environment secrets; see `.env.example`. Never commit keys.

Current status: see `docs/gate1_report.md`.
