# X launch kit (Most Viral on X)

**Nothing here has been posted.** I'll post from my own account when I'm ready. The hackathon form has one opt-in
field for this: the link to the X post for the **Most Viral Track** (the engagement window is whatever the organisers
announce; this plan assumes it runs to Nov 8). None of the numbers, quotes or results in these drafts are real yet.
Fill the `[brackets]` only with things that actually happened.

Rules for every post: only stories told with a parent's permission, and never a child's face, name or school. The
placeholder-art clips only go out with the "placeholder art" label visible (it's burned into the clips while the art
comes from the fake API). After `python scripts/go_live.py`, re-render the clips to get real Muse Image art.

Assets (all in `docs/launch/`, 720x1280, captions burned in, `.srt` next to each):
| File | Length | Use |
|---|---|---|
| `clip1-hook.mp4` | ~22 s | Main post: title card, gong, "Kocap kacarita...", first scene |
| `clip2-dalang-hands.mp4` | ~20 s | Reply / day-2 post: how the Meta models build the film |
| `clip3-dalang-cilik.mp4` | ~18 s | #DalangCilik challenge post: moral, end card, call to print and play |

Re-make them with `python scripts/make_launch_clips.py` (after `go_live.py` they use the real art).

## Day-by-day plan (times in WIB, Semarang; US Eastern in brackets)

US clocks went back on Sun Nov 1, so from Nov 1 ET is WIB minus 12 h, and the main slot is **20:00 WIB = 08:00 ET**.
The newer, fuller campaign (accounts to tag, hashtags, reply rounds, slots that fit around my shifts) is in the win
kit at `deliverables/win-kit/X_CAMPAIGN.md`. Where the two differ, go with X_CAMPAIGN.md.

| Day | What | When |
|---|---|---|
| **Sun Nov 1** | Dry run, post nothing. Run `go_live.py` once the key works, re-render the clips, check the live link + QR on a phone. Ask 3-5 families (with consent) to try it and save their real films for later posts. | any time |
| **Mon Nov 2** | Pin a short building-in-public post: what Dalang AI is, plus one screenshot of the storyboard (Post C). | 20:00 WIB (08:00 ET) |
| **Tue Nov 3** | Main launch post (Post A) with `docs/demo/teaser_vertical.mp4` (42 s, 9:16, on the new site) or `clip1-hook.mp4` + replies 1-3. Reply to every comment for the first hour. | 20:00 WIB (08:00 ET) |
| **Wed Nov 4** | Post B (the tech thread) with `clip2-dalang-hands.mp4`, quote-posting the main post. Submit on Cerebral Valley the same day with the main post link (deadline Nov 5, 09:00 WIB = Nov 4, 21:00 ET). | 20:00 WIB (08:00 ET) |
| **Thu Nov 5** | #DalangCilik challenge (Post D, Bahasa + English) with `clip3-dalang-cilik.mp4`. Invite parents and teachers to share their kid's film (no faces). | 12:00 WIB (00:00 ET) and 20:00 WIB (08:00 ET) |
| **Fri Nov 6** | Repost the best family film shared with permission (from the gallery), credited only as "a family in [city]". Post a photo of the printable puppets (paper puppets + torch shadow, hands only). | 20:00 WIB (08:00 ET) |
| **Sat Nov 7** | Javanese day: a film told in Basa Jawa, posted in Javanese + English. Reply to every #DalangCilik post. | 10:00 WIB (22:00 ET the evening before) |
| **Sun Nov 8** | Thank-you post: what people made (real counts only, e.g. films shared to the gallery) and what's next (cultural review with a sanggar). | 20:00 WIB (08:00 ET) |

## Post variants

**Post A: the hook (main post, attach `docs/demo/teaser_vertical.mp4`, or `clip1-hook.mp4`)**
> [A child I know] told a story out loud: a clever mouse deer and some hungry crocodiles.
> Dalang AI turned it into a Javanese wayang kulit film, opening with the dalang's "Kocap kacarita..." 🎭
>
> Made with six Meta models for the @AIatMeta hackathon. Link in the replies 👇

- Reply 1: "Kids can tell it in Bahasa Indonesia, Basa Jawa or English. With Gara-gara mode on, the puppet stops
  halfway and asks them what happens next. [live link]"
- Reply 2 (attach `clip2-dalang-hands.mp4`): "How it works: Muse Spark writes the lakon as validated JSON, Muse Image
  carves each puppet once, SAM 3.1 cuts it out so it looks the same in every scene, and Muse Wonder moves the
  puppets like a dalang's hands."
- Reply 3: "It's open source (MIT): [repo link]. You can keep your puppets in the Kotak Wayang for the next story, or
  print them and play shadows with a torch. #MetaHackathon #wayang #BuildForYourWorld"
- Reply 4 (attach `docs/screenshots/readme/receipt-desktop.png`, or the older `docs/screenshots/10-agent-trace.png`): "Every film shows its own agent trace. Each Meta call and
  each decision is in there, like the vision checker rejecting a backdrop and the redraw that passed. The script step
  can also run on open weights (Muse Spark Open) if a school wants to host it. [repo link]"

**Post B: the builder thread (attach `clip2-dalang-hands.mp4`)**
> How do you make an AI shadow-puppet film without disrespecting a 1,000-year-old art form? Here's how I did it 🧵
> 1/ The kid's voice goes to Muse Voice Transcribe (Javanese goes through Muse Spark audio).
- 2/ "Muse Spark turns it into a lakon: 4-6 scenes, wayang archetypes, a cultural note per puppet. Then a Muse Spark
  vision checker sends bad pictures back to be redrawn."
- 3/ "SAM 3.1 cuts every puppet out once, so Kancil has the same pixels in every scene. Muse Wonder plans the
  motion, and my kelir engine adds lamp flicker, shadows and the gunungan between scenes."
- 4/ "Gara-gara mode: the film pauses, the puppet asks a question, the kid answers out loud, and only the remaining
  scenes get rewritten and re-rendered. [live link]"

**Post C: building in public (attach `docs/screenshots/readme/storyboard-desktop.png`)**
> This week I'm building Dalang AI. A kid tells a story and gets it back as a wayang kulit film. Before anything
> moves, parents see the storyboard and can change any line. Launching [day]. #MetaHackathon #wayang

The three `clip*.mp4` files were cut on Oct 31 from the film alone (no website in them), so they still match. The two
teasers in `docs/demo/` were recorded on Nov 2 on the redesigned site.

Alt text for the clips and screenshot (paste into X's "Add description"):
- teaser_vertical: "A phone screen with Dalang AI's Kelir Live: a mouse-deer puppet and a crocodile puppet as shadows
  on a lamp-lit cream screen, with the scene's line underneath. Then the film: a gold gunungan, the title 'Kancil dan
  Barisan Buaya' in Latin and Javanese script, a mouse-deer and a crocodile by a river, and an end card: A child
  tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film. Placeholder art label."
- teaser_60s: "The same film in landscape: Kelir Live, the film's opening and first scenes, a classroom vote with A
  and B buttons and a QR code, then the end card. Placeholder art label."
- clip1: "A wayang kulit shadow-puppet film made from a child's story: a gold gunungan tree puppet on a lamp-lit
  screen, the title 'Kancil dan Barisan Buaya', then a mouse-deer puppet by a river. Captions: A child tells a story
  out loud and gets it back as a Javanese wayang kulit film. Placeholder art label in the corner."
- clip2: "Scenes from the same film: a crocodile puppet and a mouse-deer puppet on painted river backdrops, moving
  on their rods. Captions explain that Muse Image paints each puppet, SAM 3.1 cuts it out and Muse Wonder moves it."
- clip3: "The film's last scene and end card with the moral, then the words: Every child can be a dalang. Print the
  puppets, grab a torch, play shadows at home. #DalangCilik."
- storyboard screenshot: "Dalang AI storyboard on a dark indigo page: two puppet cut-outs with cultural notes and
  painted scene cards, each with an editable narration line, a Redo button and a gold Bring it to life button."
- receipt screenshot: "Under a Dalang AI film: the Penjaga Budaya cultural review with a pass per scene, a character
  consistency score of 100/100 from SAM 3.1 cut-outs, and a table of Meta models with calls, tokens and cost."

## #DalangCilik challenge copy

**Bahasa Indonesia (Post D, attach `clip3-dalang-cilik.mp4`)**
> Tantangan #DalangCilik 🎭
> Ajak anakmu cerita dongeng (maks. 90 detik) di Dalang AI, terus tonton jadi wayang kulit.
> Bagikan pakai #DalangCilik, tanpa wajah/nama anak ya 🙏
> Bonus: cetak wayangnya, tempel ke tusuk sate, main bayangan pakai senter.
> [live link]

**English**
> The #DalangCilik ("little dalang") challenge 🎭
> Get your kid to tell Dalang AI a story (90 s max) and watch it become a wayang kulit film. Share it with #DalangCilik, no faces or names please 🙏
> Bonus: print the puppets, put them on skewers, grab a torch.
> [live link]

Sharing from the app: the **𝕏 Post** button on a shared film pre-fills the post with the film's title and
#DalangCilik #wayang #MetaHackathon, and the link shows a card with the film's poster (twitter:card tags on every
/watch page). Check one link in X's composer after deploying. The card only appears once `PUBLIC_BASE_URL` points at
the real site.

Replies to use under challenge posts: "Sembah! 🙏 Thanks for sharing" · "Which puppet should come back next time?
Keep it in the Kotak Wayang" · "Try Gara-gara mode, the puppet asks your kid what happens next".

## Posting tips
- Post when Indonesia is awake and the US is starting its day: 19:00-21:00 WIB (07:00-09:00 ET), ideally 20:00 WIB = 08:00 ET.
- Reply to every comment in the first hour. Quote-post family films (with permission) and don't re-upload them.
- Put the live link in a reply and keep the main post link-free. That's common advice (X seems to show link-free
  posts more widely); I haven't measured it for my account.
- The submission form wants the X post link: use Post A's URL.
