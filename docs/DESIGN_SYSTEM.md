# Design system

This is how the Dalang AI website looks and moves, and why. The tokens live in `web/app/globals.css` (CSS
variables) and `web/tailwind.config.ts` (Tailwind names for them). The shared components are in
`web/components/ui/`.

## The idea

A wayang kulit night has two sides. The audience sits in the dark, and the only bright thing is the kelir, the
cotton screen lit from behind by the blencong oil lamp. So the site works the same way: the page is night indigo,
and whatever matters most sits on a lit cream surface. That is the film, the line a child reads aloud, the vote
question and the puppets. If something glows, look at it.

I used the batik and puppet shapes sparingly. The gunungan is the logo, the loader (it sways like a dalang flutters
it between scenes) and the empty-state picture. Kawung shows up faintly in the footer and on empty pages, and nowhere else.

## Colour

Default theme is the night show. There is a day theme (footer, "Mode siang · Day mode"), saved on the device.

| Token | Night | What it is for |
|---|---|---|
| `bg` (malam) | `#0C0A1E` | page |
| `bg-2` | `#14112E` | inset panels, fields |
| `surface` (nila) | `#1C183C` | cards |
| `surface-2` | `#26214E` | raised buttons, selected tab |
| `fg` (gading) | `#F5ECDE` | text |
| `muted` | `#CBC1B6` | second-line text (11:1 on `bg`) |
| `gold` / `prada` | `#ECBA54` | primary button, lines, accents |
| `on-prada` | `#1C122E` | text on gold |
| `kelir` | `#F6E7C6` | the lit screen |
| `on-kelir` | `#24160C` | shadow ink on the screen |
| `sindur` | `#C4422E` | recording, stop |
| `kembang` | `#CDA0E4` | second vote option |
| `ok`, `err` | green, coral | status text |

Colours are stored as `R G B` so Tailwind can add alpha (`bg-surface/80`). Components use the token names, never
raw hex. The few exceptions are the wooden frame gradient and the pressed edge under the gold button.

## Type

- Display: **Fraunces** (SOFT 100, optical size on). It has the warm, slightly carved feel of hand-cut leather and
  reads well big. Headings only.
- Text: **Plus Jakarta Sans**. It was made for Jakarta's city identity, so it felt right, and it's clear at small
  sizes on cheap phones.

Both are SIL OFL 1.1 and bundled in `web/app/fonts/` (Latin subset, with the licence files), loaded with
`next/font/local`, so the build works offline and there's no layout jump when they arrive.

| Class | Size | Use |
|---|---|---|
| `t-display` | 41.6 to 84 px | one-word page titles (Pentas, Galeri) |
| `t-hero` | 37.6 to 65.6 px | the home headline (a whole sentence) |
| `t-h1` | 32 to 54 px | section titles |
| `t-h2` | 24 to 36 px | card titles |
| `t-h3` | 20 px | small headings |
| `t-lead` | 17 to 20 px | intro paragraphs |
| body | 16 px, line height 1.55 | everything else |
| `t-small`, `t-tiny` | 14 px, 13 px | notes, captions |

Inputs are always at least 16 px so iOS doesn't zoom in. Numbers that change (timers, counts, costs) use tabular
figures.

### Two languages

Almost every label is Bahasa Indonesia first, then English. `components/ui/Bi.tsx` keeps the words exactly as
"id · en" in the text (screen readers, copy-paste and the tests see the same thing) and only changes the look: a
gold dot between them inline, or, with `stack`, the English as a small sans-serif line under a heading. Long
button labels use `wrap`: on phones narrower than 480 px the English drops to its own smaller line, so a button
never breaks in the middle of a phrase. Short segmented switches (Pentas sort) and centred dividers use it too. Pipeline stage names come from the API in English; `STAGE_ID` in
`web/lib/api.ts` gives the Bahasa name shown first.

## Space, shape, depth

- Spacing follows Tailwind's 4 px steps. Sections use `section` (40 to 80 px top and bottom).
- Radius: 8, 12, 18, 26 px (`sm`, `md`, `lg`, `xl`). Big friendly surfaces (cards, the film frame) get the larger
  ones; chips and buttons are pills. A child inside a parent uses a smaller radius than the parent.
- Shadows have two layers (a short contact shadow and a long soft one). `shadow-lamp` is the warm glow under
  anything lit by the blencong: the film frame, the selected starter, the working troupe member.
- `frame` is the wooden gawangan around a film or the stage.

## Motion

Durations come from the gamelan: each one is twice the last.

| Token | Time | Use |
|---|---|---|
| `ketuk` | 120 ms | press, hover colour |
| `kenong` | 240 ms | tabs, chevrons, toasts, sheets |
| `gong` | 480 ms | progress bars, card glow, hover zoom on posters |
| `gong-ageng` | 960 ms | the one page-load moment |

Easings: `sabet` (a quick move that settles, like a puppet being set down) and `gong` (even in and out, for loops).

There is one moment nobody asks for: on the home page the film frame starts dim and the lamp brings it up to full
light. The blencong next to it flickers on an uneven cycle, like a real flame. Everything else answers a tap: buttons
sink on press, the working troupe member sways on its rod, the gunungan sways while something loads. With
`prefers-reduced-motion` all of it stops, the hero film loop never starts and the poster stays.

### Moving between pages (added 2026-11-06)

Pages change like a dalang changing scenes: the old page dims and drops out in 150 ms, the new one rises 12 px and
fades in over 240 ms, starting 90 ms later. The header never moves; it's the fixed point of the stage. A poster you
tap in the gallery or on the Pentas wall grows into the film player on the watch page (a shared-element morph,
420 ms, with a light blur mid-flight to hide the stretch). This is React's `<ViewTransition>` on the browser's View
Transitions API: `app/template.tsx` for the page fade, `name="film-<id>"` on the poster and on `FilmVideo` for the
morph, CSS in `globals.css` under "Page transitions". Browsers without the API just swap pages. Reduced motion sets
every transition to 0 s. Clicks pass through the transition overlay, so a fast tap is never lost.

Rules I keep for anything that moves: only `opacity`, `transform` and a light `filter` (they run on the compositor,
so a busy page doesn't stutter); never fade in the largest text or picture on load (it delays LCP); progress bars and
vote bars grow with `scaleX`, not `width`. Loading placeholders (`.skeleton`) breathe with opacity instead of a
moving shimmer.

### The recorder speaks without words (added 2026-11-06)

Most young kids can't read the button, so the recorder answers in sound and touch: a soft high bonang note (and a
short buzz on phones) when the microphone starts, a lower note when it stops. The note plays before recording begins,
so it isn't in the child's story. A gold ring around the button fills over the 90 seconds. A tap on Stop in the
first 1.2 seconds is ignored, because kids double-tap big buttons (a finding from the yarn storytelling app's
usability tests). Screen readers hear "Merekam · Recording" and "Rekaman siap · Recording ready".

## Components

All in `web/components/ui/`, plus CSS classes in `globals.css` for plain links.

- Button (`Button`, or `buttonClass()` for a `<Link>`): `primary` (gold, with a 3 px bottom edge that sinks
  when pressed), `secondary`, `ghost`, `danger`; sizes `sm` to `xl`. States: hover, focus ring (3 px gold, offset),
  pressed, disabled (a primary that isn't ready yet turns dashed and quiet so the text stays readable), loading
  (spinner in place of the icon, label stays, `aria-busy`). Every button is at least 44 px tall. A secondary
  button used as a switch (`aria-pressed`, e.g. Latar and Keprak on Kelir Live) shows "on" with a gold edge and
  a warm tint, never a full gold fill, so a screen has one gold button at most.
- Card: `card` class. `panel` for a quieter inset box.
- Badge: `sample`, `placeholder`, `warn`, `ok`, `quiet`. The sample and placeholder labels must stay visible on
  every film made with placeholder art.
- Sheet: bottom sheet on phones, dialog on desktop, built on `<dialog>` so focus is trapped and Escape closes it.
  The phone menu uses it.
- Progress: slim gold bar with `role="progressbar"`. The pipeline theatre uses it. Below 480 px the six theatre
  kelirs stack as one column, figure on the left and text on the right; two columns up to 640 px, three above.
- Tabs: segmented tabs with arrow-key, Home and End support. The `seg` class gives the same look to plain toggle
  buttons (Rekam / Unggah / Ketik) and to the sort links on Pentas.
- Toast: `useToast()`; polite live region at the bottom. The film page uses it instead of `alert()`.
- Icon: one set drawn for this app on a 24 px grid, 1.75 px round strokes. Icons sit next to a text label and are
  hidden from screen readers. Emoji stay only where they are content: the story starter shadows, the smiles, 🙏
  Sembah and the 🅰/🅱 vote options. Content emoji sit in an `emoji` span so they always use the colour emoji
  font (some text fonts carry plain outline faces for a few of them).
- Gunungan: the logo mark (`solid`) and outline version.
- Also: `chip` (language picker, read-along toggle), `seg`, `field`, `option` (a radio or checkbox with its label as
  one big hit area), `kelir`, `frame`, `blencong`, `kawung`, `link`.

### Size and stability rules (Nov 6)

- Anything a thumb taps is at least 44 px tall, `btn-sm` included. Inline links inside a sentence are the only
  exception.
- A page never jumps while it fills in. `main` reserves a screen of height (`min-h-[calc(100svh-4rem)]`) so the
  footer starts below the fold, and `html` keeps `scrollbar-gutter: stable` so a page that grows past one screen
  doesn't shift sideways. Grid columns that sit next to big headlines use `minmax(0, ...)`, so a late font can't
  change their width. Every `<img>` has `width` and `height`.
- Grid posters use the 800 px WebP card (`poster_card` from `/api/gallery`) with the full 1200 px JPEG as the large
  `srcset` choice.
- `meta theme-color` follows the theme, so day mode has no dark bar on top of the page on phones.

### Empty, loading and error states

Every one has a next step. Loading shows the swaying gunungan. Empty galleries and an empty Kotak Wayang show the
gunungan on a faint kawung pattern with one button to tell a story. The 404 page is an empty kelir with only the
gunungan on it ("Lakon ini tidak dimainkan malam ini"), and `app/error.tsx` is "the lamp went out" with Try again.

## Checks I run after a UI change

- `cd web && npm run lint && npx tsc --noEmit && npm run build`
- `bash scripts/a11y_local.sh` (axe: phone and desktop in the night theme, phone in day mode) and `bash scripts/e2e_local.sh`
- `python web/e2e/r5_perf.py <base>`: home LCP under 1.5 s on a phone viewport, CLS under 0.02
- `python web/e2e/ui_shots.py <base> docs/screenshots/ui/after`: phone (390) and desktop (1440) shots of every page,
  which I look through by eye (the committed ones are squeezed with `pngquant --quality 80-95` to keep the repo small)

## Where the ideas came from

I looked at a lot of sites before starting (notes in `work/ui-skills/INSPIRATION.md`, outside the repo). The ones
that shaped this most: the "Shadows" exhibition for Louvre Abu Dhabi (light as the way to show what matters),
Teatr Lalka (puppets that move only when something happens), Duolingo (one obvious button), Headspace (calm choice
chips, lots of room) and Linear (show the real product, keep text hierarchy to one ink colour). I took ideas, not
code, pictures or logos. The checklists I followed are Anthropic's frontend-design skill, Vercel's Web Interface
Guidelines and the ui-ux-pro-max skill. For the Nov 6 motion pass I followed the Next.js "Designing view
transitions" guide (bundled with Next 16.4), web.dev on compositor-only animation and `prefers-reduced-motion`,
Google's "Building for kids" guide (sound plus visual feedback for every action) and BBC GEL's voice design notes.
