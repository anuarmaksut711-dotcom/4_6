# PIXEL

## Platform
web

## Stack
Existing HTML, local Bootstrap CSS and vanilla JavaScript in demofinal/. Python 3.10+ server in booking_server.py owns validation and Telegram delivery; no build step or external Python dependencies.

## Product Purpose
Help visitors compare rooms, prepare a visit with a transparent estimate and send a booking request with required name and phone to the club administrator or Telegram group. The administrator confirms availability; there is no automatic seat reservation or online payment. Delivery is unavailable until the private server configuration is complete. An explicit local dry-run mode never contacts Telegram.

## Capabilities and Constraints
Three rooms: Standard 20 PCs at 900 KZT/PC/hour; Duo 2 at 1000; VIP 5 at 1500. Existing hardware and package prices come from the repository. Package usage rules remain incomplete and must not be invented. Dates use Astana time. Keep non-contact draft persistence, seat/game preferences, readable result and copy. Editing creates a new plan; deleting the local receipt does not cancel a request. Contact data and Telegram credentials are never persisted in browser storage or served publicly. Server validates input, computes prices, limits request frequency and deduplicates delivery attempts.

## Brand Commitments
On 2026-10-17 the user supplied an approved PIXEL visual reference and chose cinematic WebGL motion (variant 3): cold blue-black ground, ivory heavy sans-serif type, mint actions, brushed structural metal frames around a separate real club photo, moving highlights, cursor response and scroll approach. This supersedes the warm visual direction approved on 2026-10-16. Preserve real club photographs, merged rooms/prices, packages inside the visit form, and removal of the separate cart. Mobile uses a lighter scene; pause, reduced-motion and static fallbacks preserve usability.

## Evidence on Hand
Local club photographs: demofinal/assets/pixel/slide-1.png through slide-6.png. Photo-to-room attribution is not known. Address: Astana, Mangilik El 36. Club phone: +7 775 351 36 93.

## Product Principles
Make the hourly visit the simplest path. Keep optional preferences optional. Show complete visit details before saving. Clearly distinguish package list cost from session price. No fabricated availability or promises.
