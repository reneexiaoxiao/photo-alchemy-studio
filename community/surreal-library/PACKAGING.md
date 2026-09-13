# Packaging notes

Source: [hbmartin/skills](https://github.com/hbmartin/skills)
Pinned commit: `bbf3e8c6215c5c8743bcf1848cb1cde1b51f8254`
License: [Apache-2.0](LICENSE)

The entry is named `SOURCE.md` so that only the root skill is auto-discovered. Original instructions and required text dependencies are retained; self-references to `SKILL.md` were renamed. Sample images and optional upstream automation are not included.

The root workflow uses built-in ImageGen. The source retains documentation of its original imagemine, Claude, Gemini and optional Apple Photos integration for attribution and context; the original engine and its install, configuration, scheduling and write commands must not execute in this package.

File provenance and hashes are recorded in [source-audit.json](../../docs/source-audit.json).
