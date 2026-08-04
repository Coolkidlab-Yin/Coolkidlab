# Photo and sprite specification

## Source-photo inventory

Collect 8–20 user-owned photos when possible:

| View | Preferred count | What it establishes |
|---|---:|---|
| Front standing | 2–4 | face, eye spacing, chest, leg length |
| Left side | 2–3 | muzzle, back, tail, proportions |
| Right side | 2–3 | asymmetry and coat markings |
| Sitting | 1–2 | hip, chest, paw placement |
| Lying or sleeping | 1–2 | curled body and tail |
| Expression close-up | 2–4 | eyes, nose, mouth, tongue |

Reject identity decisions based only on filtered, blurry, cropped, or extreme-lens photos.

## Identity lock

Record:

- Face silhouette and muzzle length.
- Eye color, shape, spacing, and catchlight position.
- Nose color and size.
- Ear angle, length, and interior color.
- Coat color, patches, curl, and fur length.
- Torso length, chest width, leg length, and paw size.
- Tail position and volume.

Generate one front-and-side identity sheet. Do not mass-generate actions until the user approves it.

Write the identity lock down as a single reusable paragraph. Every later
generation prompt must repeat that paragraph word for word — see
"How to actually generate the sprites" below.

## Sprite contract

Use a fixed canvas and transparent PNG output. Maintain:

- One consistent light direction and color temperature.
- One camera height and lens perspective.
- A fixed ground/contact line.
- A fixed body-center anchor.
- A named head pivot near the neck.
- A named mouth anchor for carried objects.
- No text, borders, shadows baked into rectangles, or background residue.

Minimum filenames:

```text
idle-front.png
idle-head.png
idle-body.png
stand-side.png
walk-01.png ... walk-04.png
run-01.png ... run-06.png
sit-front.png
jump-crouch.png
jump-air.png
jump-land.png
sleep.png
cuddle.png
pickup-01.png
pickup-02.png
carry-side.png
drop.png
```

## How to actually generate the sprites

This skill does not call an image API and needs no API key. The reference
workflow is **ChatGPT's image generation in the browser**: the agent writes the
prompts, the user pastes them in, and brings the images back. Any image tool
works, but the multi-angle discipline below is what keeps the result from
looking like stitched-together pieces.

Set the cost expectation before starting. "No API key" is not "free": a full
pet needs roughly 8–12 accepted sheets, and rejected regenerations are normal —
budget two or three attempts per sheet. That volume generally means a paid
image-generation plan. Tell the user this up front rather than after they hit
a limit halfway through the run.

### Why multi-angle in one generation

Generating each pose in a separate, independent request is the single biggest
cause of a mushy, glued-together pet. Every fresh generation re-invents the
muzzle length, eye spacing, and coat pattern slightly, so the frames do not
belong to the same animal, and the animation reads as a blurry morph rather
than one character moving.

Ask for **several angles of the same pose inside one image** instead. The model
holds one identity across a single canvas far better than across separate
calls, so the views stay consistent with each other. Then cut the sheet apart.

Order of work:

1. **Identity sheet** — front and side of a neutral standing pose, one image.
   Get the user's approval before anything else. This sheet is the reference
   that every later prompt points back at.
2. **Turnaround** — front, three-quarter, side, and back of the same pose in
   one image, on one shared ground line.
3. **Pose sheets** — one image per action (walk, run, jump, sleep…), containing
   that action's frames laid out left to right.
4. **Cut and clean** — split the sheet into individual transparent PNGs, then
   normalize them against the anchors in the sprite contract above.

### Should the user upload the photos?

Yes. Attach 3–5 of the clearest source photos (front, both sides, one
expression close-up) to the identity-sheet request, and say "match this
specific animal, not a generic one of its breed." Photos are what make the
result look like *their* pet rather than a stock illustration.

Do **not** re-attach photos to later requests. From the turnaround onward the
approved identity sheet is the reference — adding raw photos back in reopens
decisions the sheet already settled.

### Prompt templates

Fill the bracketed parts from the identity lock, then hand these to the user to
paste into ChatGPT.

**What counts as "the identity paragraph"**: in the identity-sheet prompt below,
it is the block between the `<<<IDENTITY` and `IDENTITY>>>` markers — *both*
lines, the breed/name/style line and the "keep exactly consistent" line. Copy
that whole block, drop the markers, and paste it **byte-identical** into every
later prompt. Rewording any part of it — even swapping a synonym — is what makes
the character drift between sheets. Only the first line's `A character reference
sheet of` wrapper changes.

Identity sheet:

```text
<<<IDENTITY
One [breed/species] named [name], drawn in [art style].
Identity, keep exactly consistent: [face silhouette], [eye color/shape/spacing],
[nose color and size], [ear angle and length], [coat color and markings],
[torso and leg proportions], [tail shape and volume].
IDENTITY>>>
Make a character reference sheet of the animal described above, matching the
attached photos of this specific animal rather than a generic one of its breed.
Show two views of the same neutral standing pose side by side on one canvas:
front view and left side view.
Same camera height, same lens, same single light direction, same scale.
Plain flat white background, full body, feet on one shared ground line,
no text, no labels, no shadow boxes, no border.
```

Worked example of a filled identity block — copy this shape, not its contents:

```text
One shiba inu named Mochi, drawn in semi-realistic 2.5D with soft cel shading.
Identity, keep exactly consistent: rounded muzzle about one third of head
length, dark amber almond eyes set wide with a single top-left catchlight,
small black button nose, small triangular ears angled slightly outward with
pale cream interiors, cream-and-tan coat with a white blaze from chin to chest
and white front paws, compact torso about 1.4 times shoulder height with short
legs, thick curled tail carried over the back.
```

Note what that does: every trait is a *measurable or nameable* fact, not an
adjective. "Cute face" drifts; "rounded muzzle about one third of head length"
holds. If a trait cannot be checked against the sheet later, it is too vague.

Turnaround:

```text
Same character as the reference sheet.
[paste the identity paragraph verbatim, both lines]
Four views of the same neutral standing pose in one image, evenly spaced,
left to right: front, three-quarter left (rotated ~45 degrees), left side, back.
Identical scale, camera height, lighting and ground line across all four.
Plain flat white background, no text, no labels, no border.
```

Action sheet (one per action). Frame counts must match the filenames in the
sprite contract above — request the number you will actually save:

| Action | Frames to request | Beats to name in the prompt |
|---|---:|---|
| walk | 4 | contact, passing, opposite contact, opposite passing |
| run | 6 | compression, launch, airborne extension, landing, recovery, passing |
| jump | 3 | crouch, airborne, landing |
| sit | 1 | settled sitting pose, front view |
| sleep | 1 | curled lying pose, side view |
| pickup / carry / drop | 2 / 1 / 1 | head down to object, object in mouth walking, releasing object |

```text
Same character as the reference sheet.
[paste the identity paragraph verbatim, both lines]
[N] frames of a [walk cycle], side view, laid out left to right in one image
as an animation strip.
The frames must be, in order: [contact, passing, opposite contact, opposite
passing].
Identical scale, camera height, lighting and ground line in every frame; only
the pose changes. Plain flat white background, no text, no frame numbers,
no border.
```

The head/body split (`idle-head.png` / `idle-body.png`) is not generated as a
separate sheet — cut it from the approved front idle frame when you split the
sheets, keeping the neck pivot in both halves.

### Checks before accepting a sheet

Reject and regenerate if any of these are true. Do not "fix it later" —
inconsistent sheets cost more time downstream than a regeneration does.

- Coat markings moved, changed shape, or changed count between views.
- Eye spacing or muzzle length visibly differs from the identity sheet.
- The frames sit at different scales or the ground line drifts.
- The model added text, labels, frame numbers, or a border.
- Any pose is a copy of another one nudged sideways — that is not a gait.

### After generation

Remove the flat background to alpha, crop each frame onto the fixed canvas, and
align to the anchors defined in the sprite contract. A white background left as
near-white pixels, rather than cut to real transparency, shows up as a pale
halo against a dark desktop wallpaper.

## Eye rules

- Place pupil and catchlight overlays inside the head transform container.
- Limit pupil travel to the visible iris area.
- Smooth both head and eye targets.
- Use a closed-eye sprite or eyelid frame for blinking.
- Do not cover photographic eyes with a flat white ellipse.

## Gait rules

Walking needs contact, passing, and opposite-contact poses. Running needs compression, launch, airborne extension, landing, and recovery.

Normalize each frame around the foot-contact or body-center anchor. If frames have different crops, pad them to the same canvas before runtime.
