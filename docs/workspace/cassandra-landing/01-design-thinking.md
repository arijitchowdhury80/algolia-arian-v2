# Cassandra Landing Refresh - Design Thinking

## Mental Model
The page is an explainer and front door, not a dashboard. A visitor expects to understand what PRISM does, see the proof surfaces, and feel that the system has a human operator behind it. The confusing version is a diagram of infrastructure where Hermes, skills, chat, and reports feel like separate machines.

## Information Architecture
- Hero: PRISM as a prospect-intelligence and search-audit system.
- Primary: Browse reports, understand the sales-kit output, and see the audit workflow.
- Secondary: Cassandra as the human access layer, skill suite, evidence rules, web and Telegram channels.
- Supporting: GitHub links, metadata, labels, status chips.

Risk: the old Hermes section inflated infrastructure into the hero of the story, while the first Cassandra pass overcorrected and made her the protagonist. The spine is PRISM: data, audit, evidence, and system output. Cassandra is supporting cast: the voice, guide, and persistent access layer.

## Interaction Flow
1. Visitor lands, understands PRISM turns a domain into a grounded audit.
2. Visitor browses reports or reads down to see the output package.
3. Visitor sees Cassandra as the persistent guide and knows they can ask reports questions on web or Telegram.

Empty/loading/error states are not relevant for this static page, but links must remain direct and keyboard-focusable.

## Cognitive Load
First viewport has four chunks: badge, headline, copy/actions, prism visual. The Cassandra section should stay to three visible chunks: portrait/profile, three capability cards, channel chips.

## Emotional Journey
The arc should move from trust to momentum to accessible companionship: "this is grounded" -> "this gets real sales work done" -> "there is a capable presence I can ask." The audit/product sections carry the argument; the portrait carries warmth and continuity.

## Design Pre-Mortem
- Tiger: copy becomes flowery. Mitigation: concrete verbs and user-facing capabilities.
- Tiger: Cassandra becomes decorative only. Mitigation: pair portrait with direct actions and operating responsibilities.
- Tiger: dark section becomes generic AI. Mitigation: use human profile structure, warm accent light, and plain language.
- Tiger: mobile image/copy overlap. Mitigation: single-column responsive grid and bounded portrait aspect ratio.
- Tiger: inaccessible image. Mitigation: meaningful alt text and preserved focus states.

## Aesthetic Choice
Use the existing Algolia/Sora PRISM design system, with a human-profile treatment inside the dark execution layer. This avoids a site-wide redesign and spends the visual risk on one memorable element: Arijit's selected Cassandra portrait as the living control center of the product.

## 30-Second Scan Revision
The page should not ask a seller to read paragraphs. Each section must answer one question in headline form and support it with a compact visual/capability structure:

- Hero: what PRISM does.
- Scan strip: how the audit moves in four verbs.
- Audience: who uses it.
- Outputs: what PRISM builds.
- Operating loop: the technical story of PRISM.
- Product tour: what the audit surface looks like.
- Skill bench: what powers the system without making skills the protagonist.
- Cassandra: the guide who keeps the audit alive after the report is built.
