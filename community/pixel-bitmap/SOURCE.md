---
name: pixel-style-poster-skill
description: Generate Pixel Style Poster prompts and matching raster images. Use when the user gives a theme, phrase, object, mood, photo, or content idea and wants a 3:4 editorial bitmap poster with a large fine dot-matrix subject, optional title-led or quiet microtype typography, close subject-text composition, optional colored-wash reverse halftone backgrounds, restrained color transitions, and low-resolution print texture. This is not retro game pixel art.
---

# Pixel Style Poster Skill

Turn the user's content into both:

1. a final image-generation prompt, and
2. a generated raster image made from that prompt.

## Mode Policy

Use **Standard Mode** for all generation. Use the Fine Bitmap Prompt Compiler in this `SOURCE.md` to convert the user's content into a compact, imageable, high-fidelity prompt.

The output canvas must be **vertical 3:4** unless the user explicitly asks for another ratio.

## Style Calibration

The style should be calibrated toward fine bitmap print posters, not chunky pixel art.

Prefer:

- one or two main dot-matrix elements as the visual subject
- a large enough subject, or a subject-text pairing, to carry the page; white or near-white background is acceptable when the subject has strong presence
- animal, flower, food, person, or animation-inspired motif translated into a fine bitmap print pattern
- small, tight pixels or halftone dots that create soft tonal transitions through density changes
- monochrome or near-monochrome ink with subtle density variation
- warm off-white, pale gray, or faintly tinted paper space with subtle fibers, not sterile dead white
- either quiet microtype or one prominent theme title near the subject, depending on the user's text intent
- integrated typography that supports the subject and usually occupies roughly 5%-18% of the composition; title-led requests may reach 15%-25%
- non-repeating visible text; each readable phrase, label, or date should appear once unless the user explicitly asks for repeated text-as-image
- 30% chance of diary-like pixel layout with small captions, date marks, thin pixel curves, or quiet page structure
- 10% chance of text forming the subject, silhouette, or decorative structure
- for person-focused outputs, close-up face or head-and-shoulders crops are usually stronger than full-body figures; prefer stylish, handsome/beautiful, Japanese editorial feeling, precise facial silhouette, and refined gaze

Avoid by default:

- oversized blocky pixels
- flat solid color with no tonal transition
- loud mixed colors or neon contrast
- cartoon sticker feeling
- game interface, game asset, or 8-bit icon logic
- chaotic layout
- text becoming more important than the visual subject
- text becoming too tiny or incidental
- repeated readable text in ordinary poster layouts
- forced large title when the user only supplied a subject and did not ask for title-led layout
- title and subject floating far apart without a designed relationship
- childlike craft-poster feeling
- generic full-body girl illustration when a person-focused prompt asks for style or mood

## Standard Mode Prompt Compiler

Default generation should compile only the parts that become visible pixels in the final image prompt.

### Visual Rules Used by the Prompt Compiler

Use these rule groups as prompt material:

- **Style identity:** fine bitmap editorial poster, 3:4 vertical canvas, white/warm paper or soft colored-wash paper space, large dot-matrix subject, optional prominent title or quiet microtype, low-resolution print language.
- **Core visual rules:** use concrete renderable rules for canvas, composition, subject scale, bitmap construction, title policy, small surrounding typography, color, texture, and flat scanned-paper mood.
- **Stable common traits:** vertical 3:4 poster, flat paper surface, fine visible pixels or dot matrix, controlled monochrome or two-color ink, soft tonal transition through pixel density, graphic design layout, non-repeating readable text, and restrained surrounding captions.
- **Replaceable variables:** subject, phrase, mood, layout, pixel density, ink color, typography mode, crop scale, texture process.
- **Negative constraints:** use as hard avoid material, especially anti-game-pixel-art, anti-chunky-pixel, anti-cartoon, anti-childlike-craft, anti-uncomposed-blank-background, anti-chaotic-layout, and anti-cinematic-realism constraints.
- **Prompt shape:** use the field order below, not the sample wording.

Do not use these as default prompt material:

- source path, sample count, README notes, or analysis notes
- long style explanation that does not become pixels
- exact captions, dates, logos, or names copied from reference images
- sample-specific subjects unless the user requests them
- vague aesthetic labels without visible construction rules

### First-Principles Prompt Fields

Every Standard Mode prompt must answer these rendering questions in this order:

1. **Canvas:** What is the output frame and base surface?
   - vertical 3:4 editorial poster; white, warm off-white, pale gray, faint ivory, pale blue-gray, barely tinted paper, or a soft colored-wash paper background; flat scanned-paper view; no mockup. A whiter background is acceptable when the main subject is large and the typography is restrained.

2. **Attention Geometry:** Where does the eye go and how much is empty?
   - use deliberate negative space, but the subject plus any text must feel large enough to carry the full poster. The main bitmap subject may occupy 40%-80% of the canvas depending on the user's theme. Prefer one main element, or two coordinated elements at most. If a title is used, place it close to the subject, either above, touching an edge, wrapped around a corner, or balanced across the same visual zone. Small text should sit around the subject, not scattered randomly.

3. **Imageable Subject:** What visual form comes from the user's prompt?
   - convert the user's theme into one clear animal, flower, food, person, animation-inspired motif, plant, insect, face, symbol, everyday item, abstract silhouette, or text-shaped figure. If the user gives an abstract feeling, choose one imageable metaphor. For people, prefer a close-up face, head-and-shoulders portrait, cropped gaze, or stylish profile before choosing a full-body figure, but keep facial features visibly translated into dot-matrix and pixel-density marks.

4. **Bitmap Construction:** What makes the subject belong to this style?
   - build the subject from fine visible square pixels, dot-matrix halftone, ASCII-like repeated text, stepped aliased edges, low-resolution scan lines, missing pixel gaps, broken grid marks, or density-shifted dot fields. Details should be suggested through pixel density, dot spacing, and absence. The image should have gradual tonal transition made from denser and looser marks, not a solid flat fill.

5. **Typography System:** How does text behave visually?
   - do not force a large title when the user only provides a subject. If the user gives title text, asks for editorial/title-led layout, or the subject is too small to carry the page, include one prominent non-repeating theme title close to the subject. Otherwise prefer restrained microtype: one small caption, one date mark, or one side label. For titles, prefer elegant serif, soft retro serif, editorial italic serif, or calligraphic italic title typography like refined poster lettering; avoid the modern geometric sans-serif title style. Add smaller type near the subject edges or around its four sides: tiny lowercase captions, vertical labels, date marks, micro notes, or small type blocks. Subject-only posters should keep text around 3%-10% of the composition; title-led posters may use 15%-25%. Do not repeat the same readable word, phrase, or date in ordinary layouts. Only use repeated text when the selected recipe is the 10% text-as-image lane and the repeated text forms the subject silhouette or texture.

6. **Color Logic:** What is the restrained ink system?
   - default to one dominant ink color for the subject and any title: cyan blue, magenta pink, dusty rose, violet, lime green, black, or soft gray. Small surrounding text does not need to match the main subject color; it may be gray, black, or a restrained accent color. A second color is allowed as registration offset, thin bitmap curves, ghost text, soft wash, or small accent. Avoid full rainbow palettes.

7. **Reproduction Texture:** What print or screen process defines the whole image?
   - flat print surface, scanned poster, low-resolution bitmap, dot gain, risograph-like ink, printer noise, slight misregistration, broken scanline gaps, or uneven halftone density. No 3D depth.

8. **Emotional Temperature:** What should the viewer feel before identifying the object?
   - quiet, delicate, strange, observational, diary-like, early-digital, poetic, print-studio, experimental graphic design, soft but intentional.

9. **Hard Avoids:** What must not appear?
   - retro video game scene, game sprite, pixel-art landscape, UI screen, app interface, cute 8-bit character, anime mascot, childlike craft poster, generic full-body cute girl, photorealistic eyes or lips in person portraits, cyberpunk neon, vaporwave overload, glossy 3D, cinematic photo, airbrushed illustration, repeated readable text, dense scrapbook collage, product ad layout, CTA, logo lockup, long readable text block, title far from subject, forced title when not requested, overly modern geometric sans-serif title.

### Standard Pixel Engine

This section defines how bitmap detail should be prompted.

- Use terms such as `fine visible square-pixel grid`, `small dot-matrix halftone`, `aliased stepped edge`, `bitmap print texture`, `low-resolution poster scan`, `pixel-density shading`, `soft tonal transition through dot density`, and `missing-pixel negative space`.
- If the subject is organic, preserve its recognizable silhouette while translating detail into square pixels or dot fields.
- If the subject is a person, keep the face attractive and refined but visibly bitmap-translated. Eyes, nose, lips, hair, cheek shadows, and clothing edges should be made from fine halftone dots, small square pixels, broken pixel highlights, and density transitions. Do not leave the eyes or mouth as smooth realistic photo detail.
- If the subject is typographic, allow repeated words or letters to form the silhouette, but keep the whole poster airy.
- Pixel marks should be visible at normal viewing size, but not oversized or blocky. Do not let the effect become smooth stippling, watercolor, vector gradient, photographic grain only, or coarse 8-bit blocks.
- Build color transitions through dot density, partial ink coverage, broken pixel fields, and scan softness. Avoid perfectly solid fills unless they are a small anchor area.
- The style is editorial and print-inspired. Do not prompt it as a game asset, sprite sheet, retro arcade, Minecraft, voxel, chiptune, or 8-bit videogame screen.
- For a single image, use one dominant bitmap method. For batches, vary the method across outputs rather than changing only the color.

### Standard Color Engine

- Default to a monochrome ink poster with one controlled color, such as `soft cyan-blue bitmap ink`, `magenta dot-matrix ink with density variation`, `dusty rose square-pixel ink`, `violet low-resolution print ink`, `pale green halftone ink`, or `black micro-pixel ink`.
- Use two colors only when the layout needs motion, offset, or contrast. The second color should be visibly secondary.
- Keep the background warm off-white, off-white, pale gray, faint ivory, or pale blue-gray, with subtle paper grain or a barely visible tint. Avoid a sterile dead-white page.
- Do not use pastel gradients as the main construction unless the user specifically asks for the soft pink blur variant.
- Do not use many colors, glossy gradients, neon glow, saturated rainbow effects, or large unmodulated solid color fields.

### Background Engine

- The background should feel like scanned paper or lightly tinted print stock, not a blank digital canvas.
- Use subtle paper fibers, faint toner dust, low-opacity registration specks, very light gray wash, warm ivory texture, or a clean white paper base.
- Background texture must stay quiet. It should prevent dead white without becoming dirty, noisy, or scrapbook-like.
- If the main subject is large and the text is intentionally restrained, the background may stay mostly white or very pale.
- For warm subjects such as cocktails, fruit, summer food, or dopamine moods, prefer faint ivory or warm paper.
- For blue, violet, portrait, or night-adjacent subjects, prefer pale gray, pale blue-gray, or soft cool paper.
- For the soft-wash reverse-halftone lane, use a full pale colored paper ground with soft blurred ink fields, cloudy white paper blooms, scan grain, and a subject that emerges through white or pale reverse halftone gaps. Keep this as a print effect, not watercolor illustration or smooth digital gradient.

### Title Policy

- Do not force a large title when the user only provides a subject, object, or animal. Default to a quiet subject-led poster with a small caption, date mark, side label, or micro note.
- Use a large title when the user supplies title text, asks for a poster with typography, requests an editorial title-led layout, or gives a concept that needs words to clarify the idea.
- If no title is supplied but the subject is too small, too abstract, or visually sparse, invent one short subject-related title and use it as a composition support.
- Title text should be non-repeating and close to the subject. It should not turn every output into the same template.
- When using only microtype, text may occupy 3%-10% of the page. When title-led, text may occupy 15%-25%.

### Layout and Typography Engine

- Default poster logic: large bitmap subject + optional close title or quiet microtype + small surrounding text near the subject's edges.
- If the user supplies no title, usually do not invent a large title. Invent only a small caption such as `quiet bloom`, `still running`, `soft royalty`, or a date mark unless a title-led composition is clearly better.
- When a title is used, it should usually be the largest text element and occupy about 10%-18% of the composition. Use elegant serif, retro serif, editorial italic serif, or calligraphic italic type. Avoid modern geometric sans-serif headlines as the default.
- Small supporting text should be close to the subject, hugging corners, edges, stems, wings, body contours, or empty pockets around the object. It can be gray, black, or a restrained accent color; it does not need to follow the subject's color.
- Small text should use simple monospaced/typewriter-like lowercase or tiny editorial captions. Keep it short, non-repeating, and legible enough to read as design material.
- If the subject is too small or not strong enough to fill the page, use an ornamental frame, corner marks, border brackets, or a central art-title layout to carry the composition. The frame should be thin and editorial, not scrapbook-like.
- Prefer the composition quality of large botanical/bitmap subject posters and close title-subject pairing. Do not imitate numeric ASCII construction unless the user asks for ASCII or number-text imagery.

### Multiple Subject Policy

- When the user gives two subjects, create hierarchy: one dominant subject takes roughly 55%-70% of the visual weight, and the second subject supports it at roughly 15%-30%.
- When the user gives three subjects, do not place them as three equal stickers. Use a specimen trio, diagonal study, orbiting accents, diary cluster, or one dominant subject with two small supporting motifs.
- If the subjects belong together, such as grapes, plate, and ribbon, compose them into one coherent still life or object system.
- If the subjects are unrelated, choose the most imageable subject as the main form and translate the others into small bitmap accents, labels, border marks, or supporting silhouettes.
- Keep multiple subjects within one restrained ink system and one clear poster geometry. Avoid icon sheets, sticker sheets, game inventory layouts, and chaotic collage.

## Distribution Defaults

When the user does not specify a layout lane, use this rough distribution across multiple outputs or repeated uses:

- **40% quiet subject-led dot-matrix posters:** one large main element, or two coordinated elements; animal, flower, food, person, or animation-inspired motif; fine pixel-density shading; restrained microtype, date marks, or one small caption instead of a large default title.
- **20% title-led editorial posters:** one large main element with a prominent user-supplied or composition-needed title placed close to the image; small surrounding text supports the lockup.
- **20% diary-like pixel layouts:** one refined main element plus small captions, date marks, thin pixel curves, vertical labels, ghost text, or quiet page structure; the layout stays clean, close-set, slightly assembled, and intentional. If the subject is a person, prefer a stylish close-up face, head-and-shoulders crop, or cropped gaze instead of a full-body cute figure.
- **10% soft-wash reverse-halftone posters:** full pale colored-wash background, cloudy white blooms, reverse halftone subject, pale or white integrated type, visible scan grain.
- **10% text-formed compositions:** repeated words, ASCII-like letters, or character fields form the subject or decorative structure; text still behaves as image, not as a paragraph.

For a single output, choose the lane that best fits the user's prompt. If unclear, default to subject-led dot-matrix.

### Standard Prompt Shape

Write the final Standard Mode prompt as four compact paragraphs:

1. canvas + background + subject-text composition scale
2. subject metaphor + bitmap construction + detail behavior
3. title policy or microtype + small surrounding text + exact ink color strategy + print defects
4. flat scanned-poster mood + hard avoid-list

The structure is more important than reciting every rule. Prefer a concrete, imageable prompt over a long style essay.

## Variation Engine

Before writing the prompt, choose one option from each axis. Randomness must change the visual grammar, not only the subject or color. If recent outputs used the same layout or bitmap method, choose a different one.

### Layout Family

- **oversized-crop:** huge bitmap subject cropped by one or more poster edges
- **center-specimen:** one clear subject centered with controlled surrounding space
- **two-element-study:** two coordinated dot-matrix elements, one dominant and one secondary
- **floating-clusters:** a few small pixel clusters drift across the canvas, never chaotic
- **type-led:** large typography controls the composition, subject supports it
- **text-as-image:** repeated words or letters form the subject silhouette
- **diagonal-motion:** bitmap subject, curve, or stem cuts diagonally through the page
- **label-poster:** small vertical label plus one dominant bitmap form
- **corner-weighted:** subject and text sit heavily in one corner with open space elsewhere
- **diary-grid:** quiet diary-like layout with a main bitmap element, small date/caption, and thin pixel curves
- **portrait-diary-closeup:** stylish close-up face or head-and-shoulders crop with diary labels, date marks, and pixel curves
- **assembled-type-field:** a controlled field of labels, ghost words, dates, and microtext around one subject, creating a collage-like but clean graphic-design feeling
- **title-subject-lockup:** large bitmap subject with a large elegant title placed close above, beside, or partially overlapping the subject
- **framed-art-title:** thin ornamental frame or corner bracket system with the subject and an elegant central title when the subject is too small to carry the page alone
- **quiet-specimen:** large single bitmap subject with only one small caption, date mark, or side label
- **soft-wash-reverse-halftone:** full tinted wash ground with a pale or white reverse-halftone subject emerging from the ink layer
- **hierarchical-still-life:** two or three related subjects arranged as one coherent still life, with one dominant object and smaller supporting objects

### Subject Treatment

- square-pixel silhouette
- fine dot-matrix halftone
- ASCII or repeated-word silhouette
- broken bitmap outline
- pixelated photo translation
- refined close-up portrait mesh
- low-resolution botanical or insect scan
- abstract bitmap curves and starbursts
- dense-to-sparse pixel fade
- small-pixel tonal mesh

### Typography Mode

- oversized clean sans-serif headline
- delicate serif or cursive contrast
- elegant retro serif title
- editorial italic serif title
- calligraphic italic title
- vertical black label
- tiny lowercase caption
- repeated word cloud, only for text-as-image recipes
- ghosted overlapping text
- assembled caption field
- minimal date or signature line
- dashed pixel-outline lettering
- tiny diary note plus date

### Color Mode

- single cyan-blue ink
- single magenta-pink ink
- dusty rose monochrome
- violet monochrome
- blue plus lime registration offset
- black text on white
- soft gray bitmap subject with one color accent
- pale gray background with saturated subject ink
- pale green or fruit-red ink with density transition
- warm ivory paper plus coral/cyan accents
- cool pale-gray paper plus blue/black portrait ink

### Texture Mode

- sharp square pixels
- soft dot gain
- risograph misregistration
- low-resolution printer noise
- bitmap halftone fade
- broken scanline gaps
- uneven toner density
- screen-to-paper scan softness
- small-dot tonal gradation

### Mood Mode

- quiet
- playful but minimal
- delicate
- diary-like
- observational
- early digital
- poetic
- botanical
- strange
- print-study
- Japanese editorial
- fashion-diary

## Workflow

1. Determine mode.
   - Use Standard Mode.

2. Parse the user's content.
   - Identify the core subject, mood, exact text if supplied, possible visual metaphor, and any reference image role.
   - Identify whether the user supplied title text or requested a title-led layout. If not, default to quiet microtype unless the composition needs a title to avoid feeling empty.
   - If the user gives an object, keep the object recognizable but translate its surface and shading into bitmap marks.
   - If the user gives an abstract idea, choose one concrete object, creature, flower, insect, symbol, or text structure to carry it.
   - Prefer animals, flowers, food, people, and animation-inspired motifs when the user's prompt leaves the subject open.
   - For people, especially diary-like or dopamine mood prompts, prefer a refined close-up face, stylish head-and-shoulders portrait, cropped profile, beautiful/handsome gaze, or Japanese editorial character feeling. Avoid defaulting to a generic full-body walking or sitting girl.
   - If no image text is supplied, invent one short phrase in the user's language or in concise English.

3. Select a variation recipe.
   - Pick layout, subject treatment, typography, color, texture, and mood from the Variation Engine.
   - Make sure the selected recipe matches the user's subject. For example, flowers and insects work well with dot-matrix halftone, while phrases work well with type-led or text-as-image layouts.
   - Prefer `quiet-specimen` for subject-only requests with a strong object. Prefer `title-subject-lockup` when the user supplies title text or asks for editorial typography. Use `framed-art-title` only when the subject is small or not strong enough to carry the whole page. Use `soft-wash-reverse-halftone` when the user requests colored haze, wash, soft background color, or the reference direction matches that look.
   - Respect the Distribution Defaults: subject-led dot-matrix first, diary-like pixel layout second, text-formed composition only occasionally.
   - Do not default to the same butterfly, flower, or cat motif unless the user asks for it.

4. Write the final image prompt.
   - Use the four-paragraph Standard Prompt Shape.
   - Specify the 3:4 vertical ratio.
   - Specify the exact subject, subject-text relationship, composition scale, bitmap method, typography mode, ink color, and print defects.
   - If using a title, include one prominent theme title close to the subject. Use elegant serif, retro serif, editorial italic serif, or calligraphic italic title wording unless the user requests another font mood.
   - If not using a title, explicitly keep typography restrained: one small caption, date mark, or side label.
   - If the user gives two or three subjects, state the visual hierarchy and avoid equal sticker-like placement.
   - Keep small surrounding text close to the subject, around its edges or nearby empty pockets. Small text may be gray, black, or accent color and does not need to match the subject color.
   - Do not repeat readable text. Use each phrase or date once, unless the selected recipe is explicitly `text-as-image`.
   - For person portraits, explicitly say that eyes, lips, hair, and facial shadows remain built from fine dot-matrix or small square-pixel tonal mesh.

5. Generate the image.
   - Use the built-in image generation capability by default.
   - Do not stop after prompt-only unless the user explicitly asks for prompt-only.
   - If the result looks like video-game pixel art, regenerate once with stronger wording: `editorial bitmap print poster, not game pixel art, not sprite, not 8-bit game scene`.
   - If the pixels are too large, regenerate once with stronger wording: `fine micro-pixel matrix, small dot-matrix print texture, no chunky block pixels`.
   - If the result becomes too smooth or photographic, regenerate once with stronger fine pixel and dot-matrix construction.
   - If the result is too flat or solid, regenerate once with stronger wording: `visible tonal transition through varied pixel density, broken ink coverage, soft halftone fade`.
   - If the background is dead white, regenerate once with stronger wording: `warm off-white scanned paper, subtle paper fibers, faint toner dust, not sterile pure white`.
   - If a requested title is missing, too small, or far from the subject, regenerate once with stronger wording: `large elegant serif theme title placed close to the bitmap subject, with small surrounding text near the subject edges`.
   - If a subject-only output looks over-formulaic because it invented a large title, regenerate once with stronger wording: `quiet specimen poster, no large headline, only one tiny caption or date mark`.
   - If a soft colored wash request comes out as plain white paper, regenerate once with stronger wording: `full pale colored-wash paper ground, soft blurred ink fields, cloudy white paper blooms, reverse halftone subject emerging from the ink layer`.
   - If the subject is too small and the page feels empty, regenerate once with stronger wording: `thin ornamental frame or corner brackets, central art-title layout, subject and title carrying the full page`.
   - If a diary-like person result looks childish or generic, regenerate once with stronger wording: `stylish Japanese editorial close-up portrait, refined face, cropped gaze, avant-garde but delicate, not a full-body cute cartoon`.
   - If a person portrait looks too realistic, regenerate once with stronger wording: `eyes, lips, hair, and facial shadows rendered as fine dot-matrix bitmap marks, no smooth photorealistic facial features`.

6. Return the image and prompt.

## Negative Constraints

Always avoid:

- retro video game pixel art
- game sprite, sprite sheet, game asset, voxel, Minecraft, arcade screen
- pixel-art landscape or world scene
- app UI, computer screen, software interface
- cute 8-bit character, mascot, anime chibi, kawaii sticker
- childlike craft poster or elementary handmade poster feeling
- generic cute full-body girl as the default person motif
- neon cyberpunk, vaporwave overload, glowing gradients
- glossy 3D, cinematic lighting, hard shadows, depth of field
- realistic photo background or smooth airbrushed illustration
- dense scrapbook collage or sticker sheet
- commercial ad layout, CTA button, product packshot, logo lockup
- long clean readable paragraph text
- requested theme title absent, too tiny, or disconnected from the subject
- forced large headline on a subject-only request
- repeated readable words, labels, or dates outside the text-as-image recipe
- too many colors or rainbow palette
- chunky oversized pixels
- chaotic composition
- text overpowering the subject
- perfectly solid flat color without bitmap density transition
- loud pop-art sticker style
- smooth photorealistic eyes, lips, or facial details in person portraits
- default modern geometric sans-serif title style

## Output Format

````markdown
**生成图**

![Pixel Style Poster](absolute-image-path-or-rendered-image)

**最终 Prompt**

```text
[final prompt used for image generation]
```

**说明**

- Mode: Standard
- Recipe: [layout / subject treatment / typography / color / texture / mood]
- [one short note about the content interpretation]
````

If generated images render directly without a file path, show the image normally and still include the final prompt.

## Quality Gate

Before finalizing, check:

- Did the prompt use a vertical 3:4 poster ratio?
- Does the image read as an editorial bitmap print poster, not retro game pixel art?
- Is the main subject visibly built from fine square pixels, dot matrix, repeated text, or low-resolution marks?
- Is the user's subject translated into a recognizable but stylized pattern?
- Are there one or two main visual elements, not many competing subjects?
- Does the canvas stay white, off-white, or pale gray without feeling like an uncomposed blank page?
- Do the main subject and chosen text strategy carry the poster even if the background is mostly white?
- Is there one dominant ink color or a restrained two-color system?
- Does the ink show tonal transition through pixel density or halftone variation rather than a fully solid fill?
- If the user supplied or requested a title, is there one prominent non-repeating theme title close to the subject?
- If the user only supplied a subject, did the prompt avoid inventing an unnecessary large headline and use quiet microtype instead?
- If a title is used, does it use elegant serif, retro serif, editorial italic serif, or calligraphic italic typography instead of a default geometric sans-serif?
- Are small captions, labels, dates, or notes placed around the subject edges or nearby empty pockets?
- If the prompt asks for soft colored wash, does it include a full tinted wash ground, soft blurred ink fields, cloudy white paper blooms, and reverse halftone construction?
- If the user gives two or three subjects, is there a clear hierarchy rather than equal sticker-like placement?
- Does each readable word, phrase, and date appear only once unless this is a text-as-image recipe?
- For diary-like person outputs, is the person stylish and face/portrait-led rather than a generic full-body cartoon or childlike craft figure?
- For person portraits, do the eyes, lips, hair, and facial shadows retain visible dot-matrix or fine pixel construction instead of becoming smooth photorealistic detail?
- Are pixel edges, dot gain, scan noise, misregistration, or printer texture visible?
- Did the result avoid UI screens, game sprites, chunky pixels, cartoon mascots, neon, messy layout, 3D, cinematic lighting, and commercial CTA layout?
- Did you actually generate the image unless prompt-only was requested?

## Example Requests

- "用 $pixel-style-poster-skill 做一张关于蝴蝶和 quiet strength 的海报"
- "用 $pixel-style-poster-skill 生成一张粉色点阵猫，文字是 still in motion"
- "用 $pixel-style-poster-skill 做一张蓝绿双色的日记感 poster，主题是空闲时间"
- "用这张照片做一张同风格 bitmap poster"
