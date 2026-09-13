# Packaging notes

Source: [18810320381-del/jiuerli-visual-director](https://github.com/18810320381-del/jiuerli-visual-director)
Pinned commit: `988077a3e861da6c835621e670298fddb7d1137b`
License: [MIT](LICENSE)

The entry is named `SOURCE.md` so that only the root skill is auto-discovered. Original instructions and required text dependencies are retained; self-references to `SKILL.md` were renamed. Sample images and optional upstream automation are not included.

The three authority images are execution dependencies, not gallery samples. Their inclusion is explicitly covered by the pinned upstream README and MIT license. The source mentions two optional files (`references/photo-sketch-full-text-style.md` and `references/regression-checklist-v2.md`) that do not exist in that pinned upstream tree. The default one-call workflow does not read them. If explicitly requested, ask for those exact files; do not fabricate their contents or claim that expanded review was run.

File provenance and hashes are recorded in [source-audit.json](../../docs/source-audit.json).
