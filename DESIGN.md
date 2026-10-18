---
name: PIXEL — Metal Portal
description: Real club photography inside a cold metal portal, with clear visit planning.
colors:
  canvas: "#050c11"
  surface: "#0d181f"
  summary: "#0d1b24"
  ink: "#f3f6f7"
  muted: "#abb8c0"
  line: "#30404a"
  control-line: "#607580"
  action: "#a2f6dc"
  action-hover: "#c4ffeb"
  action-ink: "#09231e"
typography:
  display:
    fontFamily: "Manrope, Arial, sans-serif"
    fontSize: "clamp(54px, min(6.65vw, 10.3svh), 110px)"
    fontWeight: 800
    lineHeight: 0.94
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Manrope, Arial, sans-serif"
    fontSize: "clamp(34px, 4vw, 58px)"
    fontWeight: 800
    lineHeight: 1.06
    letterSpacing: "-0.04em"
  title:
    fontFamily: "Teko Local, sans-serif"
    fontSize: "2.9rem"
    fontWeight: 400
  body:
    fontFamily: "Manrope, Arial, sans-serif"
    fontSize: "1rem"
    lineHeight: 1.65
  label:
    fontFamily: "Manrope, Arial, sans-serif"
    fontSize: "12px"
rounded:
  hero-action: "5px"
  control: "6px"
  photo: "3px"
  summary: "12px"
spacing:
  compact: "12px"
  control-gap: "20px"
  section-gap: "24px"
  content-gap: "32px"
  mobile-gutter: "20px"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.control}"
    padding: ".75rem 1.2rem"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
    textColor: "{colors.action-ink}"
  button-hero:
    backgroundColor: "{colors.action}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.hero-action}"
    padding: "16px 24px"
    height: "58px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: ".7rem .8rem"
  visit-summary:
    backgroundColor: "{colors.summary}"
    rounded: "{rounded.summary}"
    padding: "28px"
---

# Design System: PIXEL — Metal Portal

## Overview

**Creative North Star: "The Real Club Through a Metal Portal"**

The approved visual reference replaces the earlier warm charcoal, champagne and editorial-serif direction. PIXEL now uses cold blue-black space, brushed steel, ivory-white typography and a mint invitation to plan a visit. Real photographs supply the human destination; the portal supplies depth around them.

The first viewport places a compact header above an outline PIXEL wordmark, a large three-line Russian invitation on the left, nested metal frames and a separately rendered club photograph on the right, and a room-rate strip below. Content, navigation and actions remain HTML. Three.js renders only the decorative scene; the photograph is a distinct textured plane within it, with an HTML photograph fallback.

**Key Characteristics:**
- Cold metal and dark blue-black materials.
- Heavy, tightly set sans-serif headings with restrained body text.
- Mint actions, thin separators and readable room comparisons.
- A single continuous approach to the club, with controllable motion.
- Authentic club photographs without invented room attribution.

Implementation evidence: `demofinal/css/portal.css`, `demofinal/js/portal.js`, `demofinal/index.html`, and shared structure in `demofinal/css/premium.css`. The portal stylesheet loads last on the public pages. Tokens record the approved current world; historical declarations overridden by it are not new design guidance.

## Colors

The palette is a dark, cool architectural surround for pale type and one soft mint accent. Frontmatter owns exact token values; CSS maps the main palette to corresponding `--pixel-*` properties.

### Primary
- **Mint invitation** (`action`): primary visit-planning buttons, links, focus rings and selected navigation underline.
- **Lit mint** (`action-hover`): primary-button hover.
- **Deep green ink** (`action-ink`): text and icons on mint actions.

### Neutral
- **Blue-black canvas** (`canvas`): page, header and footer foundation.
- **Deep steel surface** (`surface`): form fields, secondary tonal containers and empty states.
- **Raised steel surface** (`summary`): visit summary and mobile review bar.
- **Ivory-white ink** (`ink`): primary information and brand lettering.
- **Steel-grey text** (`muted`): supporting copy and metadata.
- **Blue-grey line** (`line`): dividers and boundaries.
- **Control edge** (`control-line`): field, outline-action and package-counter boundaries.

**The Invitation Rule.** Mint identifies an action or interaction state. The portal's highlights belong to the steel material and studio lighting.

## Typography

**Display Font:** locally hosted Manrope, with Arial and sans-serif fallbacks.
**Body Font:** locally hosted Manrope, with Arial and sans-serif fallbacks.
**Brand and room names:** locally hosted Teko Local, with sans-serif fallback.

**Character:** Extra-bold Manrope creates the reference's broad, compact invitation. Teko preserves the established PIXEL identity and condensed room names; body copy and controls stay familiar and legible.

### Hierarchy
- **Display:** the frontmatter display role applies to the desktop portal headline. Its explicit line breaks preserve the approved three-line composition.
- **Headline:** the frontmatter headline role applies to home sections. Shared headings use the same heavy family and tight tracking; booking legends, the summary heading and the price introduction use (700) weight.
- **Title:** condensed room names use Teko; the home room list uses the recorded title size. Rate-strip names use a smaller condensed treatment.
- **Body:** normal copy uses the body role; paragraphs retain a maximum width of (70ch). Hero supporting copy scales between (14px) and (22px).
- **Label:** desktop home navigation uses the label role; mobile navigation and portal metadata use (11px). The mint hero action uses (14px) on desktop and (12px) on mobile.

**The Clear Invitation Rule.** Keep the large headline, supporting sentence and primary action as separate HTML elements. Do not bake text into the scene or a composite image.

## Layout

The home hero is full bleed beneath a desktop header of (64px). Its height follows the viewport minus the header, with a minimum of (680px); short desktop windows use a minimum of (590px). Hero gutters are (2.35%). The rate strip is a three-room grid plus the administrator-confirmation note. The background outline wordmark sits behind the scene and copy.

At widths of (767px) or less, the header becomes two rows, the scene occupies a top region of (445px), and the invitation follows beneath it. The room strip retains three compact columns; the location wraps. The hero is content-height rather than constrained to one phone screen. Mobile gutters are (20px). At widths below (359px), controls and navigation spacing compress further.

Below the hero, the existing maximum content width of (1240px), desktop side padding of (32px), tablet padding of (24px), room comparisons and page grids remain. Related controls use compact gaps; sections have larger pauses. The booking flow keeps its desktop summary column and single-column phone layout, including the explicit mobile review action.

## Elevation & Depth

Depth is concentrated in the portal. Independent extruded rectangular frames have bevelled edges, directional roughness and bump texture, a prefiltered studio environment, and slowly travelling lights. The club photograph remains a separate plane inside the aperture. Desktop rendering adds one planar floor-reflection pass with grain and distance falloff. Ordinary content surfaces rely on tonal separation and thin rules.

The camera approaches smoothly during natural page scrolling. Fine-pointer movement gently rotates the frames and offsets the photograph; the input is smoothed rather than applied directly. The scene has a pause control. Its animation loop stops offscreen and when the document is hidden. Reduced-motion preference renders a static scene and suppresses entrance and navigation animation.

Phones, low-memory devices and save-data sessions use a lighter scene: pixel ratio capped at (1.25), a roughly (30fps) update rate, no reflecting floor, and no pointer response. Initial bevel quality is reduced; antialiasing remains enabled. Cinematic desktop rendering caps pixel ratio at (1.6) and can lower quality after sustained slow frames. Static HTML photography with a CSS metal frame remains available if WebGL initialization fails or context is lost.

**The Content Owns the Visit Rule.** Motion may frame the invitation; it must never own navigation, pricing, forms, confirmation or contact information.

## Shapes

The signature form is a series of independent rectangular apertures, slightly turned relative to one another. Bevels and material variation distinguish real thickness from a flat border. Normal controls have gently eased corners; photographs have only slight rounding. Room comparisons stay open and divided by thin rules rather than floating cards.

## Components

### Buttons
Primary actions are mint with deep green text and the shared control radius. The hero action is slightly squarer, with an inline SVG arrow, an explicit minimum height of (58px), and the padding recorded above. On phones it reduces to a minimum height of (52px). Primary hover adds a subtle diffuse shadow; active removes the shadow. Background, color and shadow transitions last (150ms). Shared visible focus uses a (2px) mint outline with (4px) offset.

Text links retain an underline where used and an interactive height of at least (44px). The home hero secondary link is grey and visually quieter than the mint action. Outline actions use ivory-white text and a blue-grey edge, reversing to a light fill on hover.

### Navigation
Four real links connect home, rooms/prices, games and visit planning. The current page is indicated with `aria-current`, light ink and a mint underline. Desktop home navigation is compact; phone navigation spans a second row. A keyboard skip link leads into the main content.

### Room comparison
Three columns use condensed room names, equipment facts, tabular price numerals and direct links. Thin dividers organize the comparison. On phones, each room becomes a full-width row with price and action aligned beside its description. The hero's compact rate strip links to the corresponding room anchors.

### Portal and motion control
The canvas is hidden from assistive technology; the figure is labelled and its visible caption identifies the real club interior. The pause button communicates its state through `aria-pressed` and changes its accessible label and visible text. The static frame uses the same real photograph, not a substitute illustration. A single (700ms) portal entrance uses `cubic-bezier(.16,1,.3,1)`. On other pages, the main content arrives over (220ms) with the same easing, fading from opacity (.72) to (1). Reduced-motion preference disables that arrival animation.

### Visit form and result
Fields use the steel surface, blue-grey edges and shared control radius; focus deepens their fill and adds the mint outline. Checked boxes use a deeper green fill with mint boundary. The visit summary is a distinct blue-black tonal panel. Semantic error and success treatments remain distinguishable from the mint action palette.

Preserve native date, time, select and number controls, inline errors, contact fields, readable review and result, and copy/edit actions. `booking.js` owns validation, persistence and confirmation presentation. The server remains the authority for delivery and prices. Visual changes must preserve required name and telephone, complete review before submission, the administrator-confirmation boundary, explicit dry-run status, and privacy of contact data and Telegram credentials. Unknown package conditions and live availability must not be invented.

## Do's and Don'ts

### Do:
- **Do** keep real club photography as a separate image layer within the portal.
- **Do** preserve the reference's dark blue-black, ivory-white and mint relationship.
- **Do** keep headings, links, rates and actions as accessible HTML.
- **Do** provide controllable motion, reduced-motion behavior and a static fallback.
- **Do** preserve the complete visit review, native controls and administrator-confirmed booking boundary.

### Don't:
- **Don't** restore warm champagne or editorial serif as the approved direction for new surfaces.
- **Don't** flatten the portal and interface into a single screenshot.
- **Don't** make motion a prerequisite for reading content or using the site.
- **Don't** attribute a photograph to a specific room without evidence or imply live availability.
- **Don't** treat historical overridden styles as current-world tokens.
