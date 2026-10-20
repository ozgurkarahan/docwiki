# Site photo assets: provenance

The two photos in this folder are AI-generated images, not photographs of a real site. They are
the source images of the two site photos of the fictional sample corpus: the poured slab of the
house extension and the delivered pallets of concrete blocks.

| File | Scene | Size | sha256 |
|---|---|---|---|
| `slab-poured.jpg` | Freshly poured concrete slab of the house extension | 1536 x 1024 | `88b5ecb7c76f3fb9846bbea46349a9f8b513803fa8c8c2080207aa8705595e2f` |
| `pallets-delivered.jpg` | Shrink-wrapped pallets of concrete blocks on the driveway | 1536 x 1024 | `f8a9f327aa53eb7b4e81b7beb11a99a0635986330e49b22b2e365abe1a449b3b` |

## Generation

- Model: `gpt-image-2.5-flare`, version `2026-09-08`, an OpenAI image model in Microsoft Foundry,
  called through the Azure OpenAI images API on a temporary deployment with the `GlobalStandard`
  SKU (capacity 1) that was deleted after use.
- Generation date: 2026-10-19. Request settings: size 1536x1024, quality high, one image per
  request, PNG output.
- Prompts are quoted verbatim, except that the name of the country where the scene is set is
  replaced by `<country>`, because the sample content names no real place.

Prompt of `slab-poured.jpg`:

```text
Photorealistic documentary photo taken with a smartphone on a small residential building site in
<country>. A freshly poured, smooth grey concrete slab of a small single-storey house extension,
about 5 m by 6 m, lies against the rendered wall of an existing suburban house. Timber formwork
boards run along the edges of the slab; a few steel rebar starter bars stick up at the corners.
Damp gravel and garden soil around the slab. Overcast spring daylight, soft shadows, natural
colours, landscape framing. No people, no faces, no hands. No text, no letters, no numbers, no
logos, no brand marks, no signs or signboards, no labels or stickers, no printing on any
packaging, no house numbers, no mailboxes, no vehicles, no machinery, no registration plates, no
watermark.
```

Prompt of `pallets-delivered.jpg`:

```text
Photorealistic documentary photo taken with a smartphone held low, close to the ground, on a
small residential building site in <country>. In the foreground, very close to the camera, the
corner of a pallet of plain grey concrete building blocks wrapped in clear shrink film fills the
left part of the frame and is cut off by the left and bottom edges. Behind it, slightly out of
focus, more wrapped pallets of blocks stand tightly packed and overlapping on the gravel
driveway of a suburban house; their outlines blur into one grey mass and run out of the right
edge of the frame, so it is impossible to tell how many pallets there are. Plain wooden pallets
without markings, no printing on the film. Overcast spring daylight, soft shadows, natural
colours, shallow depth of field, landscape framing. No people, no faces, no hands. No text, no
letters, no numbers, no logos, no brand marks, no signs or signboards, no labels or stickers, no
printing on any packaging, no house numbers, no mailboxes, no vehicles, no machinery, no
registration plates, no watermark.
```

## Candidates and choice

Eleven candidates were generated. Each one was reviewed by eye, at full size and in enlarged
crops, and was described several times with the figure-description prompt that DocWiki itself
applies to images (`fast` model tier), with and without a simulated stamp caption.

- Slab: three candidates from the prompt above, all free of people, text, logos and vehicles.
  The chosen one has the most natural documentary framing: a corner view of the slab against the
  rendered wall, formwork boards along the edges and pairs of starter bars at the corners.
- Pallets: eight candidates from five wordings of the same scene; the chosen one comes from the
  last wording, quoted above. The sample invoice bills 10 pallets while the delivery note records
  8, so the photo must not show a countable number of pallets other than 8. Seven candidates
  were rejected because their pallets could be counted: three or four separate pallets, or a row
  of six or seven distinct pallets; for two of them a generated description also stated a number
  of pallets. In the chosen one the nearest pallet is cut off by the frame and the
  out-of-focus pallets behind it overlap and run out of the right edge, so the number of pallets
  cannot be determined. Its generated descriptions speak of "several" pallets and never give a
  number.

## Post-processing

The PNG output was decoded and rebuilt from its raw pixel values with Pillow. This drops every
metadata chunk, including the content credentials that the image service embeds; this file is
the provenance record instead. Each image was saved as a baseline JPEG, quality 88, 1536 x 1024
(no crop or resize was needed), without EXIF, ICC profile, XMP or comment. Re-running the
re-encoding produces byte-identical files.

## Content and license

- No people, faces, text, logos, brand marks, signs or vehicle plates; no real place is depicted.
- Fictional sample content licensed under CC BY 4.0, like the rest of the sample corpus (see
  `LICENSE-CONTENT.md` at the repository root).
- These source images carry no stamp: the corpus generator adds the stamp "FICTIONAL - NOT FOR
  OPERATIONAL USE" as a small overlay caption when it builds the corpus.
