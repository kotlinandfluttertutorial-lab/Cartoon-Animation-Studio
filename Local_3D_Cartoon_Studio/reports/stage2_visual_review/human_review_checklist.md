# Stage 2 Human Visual Review Checklist

**Project:** Local 3D Cartoon Animation Studio  
**Date:** 2026-11-10  
**Reviewer:** _________________  
**Instructions:** Open `index.html` in a browser alongside this checklist. Check each item only after viewing the actual rendered images.

---

## Character Appearance

- [ ] Aarav looks like an original cartoon boy.
- [ ] Aanya looks like an original cartoon girl.
- [ ] Both characters have readable facial features.
- [ ] Body proportions look consistent between the two characters.
- [ ] Colours are clearly visible and distinct per character.
- [ ] Characters are visually distinct from each other.
- [ ] No obvious mesh intersections or missing body parts.

**Notes from automated review:**
- Aarav: rounded head (sphere), blue shirt, navy trousers, brown skin, dark hair. Arms and torso visible from front view.
- Aanya: angular head covered by purple hijab, pink top, teal trousers. Head covering dominates the silhouette.
- Side view (Aarav): camera is very close — character fills most of the frame; arms not visible from this angle. This may be a camera framing issue to note.
- Happy expression images show visibly different scenes from front/neutral — confirming expressions do produce visual change.

---

## Character Expressions

- [ ] Aarav happy expression looks visibly different from neutral/front.
- [ ] Aanya happy expression looks visibly different from neutral/front.
- [ ] Facial features are positioned correctly.
- [ ] No obvious facial mesh clipping.

**Notes from automated review:**
- Happy expression file sizes differ significantly from front (Aarav: +50 KB larger; Aanya: +38 KB larger), confirming visible differences exist.
- **Important:** The happy expression renders show a large pink/skin-coloured area filling most of the frame with tiny eye-like shapes near the top. This suggests the camera is zoomed into the face region but the facial features (eyes, eyebrows) are very small relative to the head — the expression change may not be clearly readable at this camera distance.

---

## Character Poses

- [ ] Aarav wave pose visibly differs from his front pose.
- [ ] Aanya wave pose visibly differs from her front pose.
- [ ] Arms and hands appear correctly positioned in wave pose.
- [ ] No obvious broken joints or disconnected body parts.
- [ ] Combined character preview displays both characters correctly.

**⚠ AUTOMATED FINDING — Do NOT check these pose items without reading this:**

Pixel analysis confirmed **wave_pose.png is pixel-identical to front.png for both characters** (0.0% difference). The wave pose was not successfully applied during the preview render. This is a confirmed Stage 2 defect.

The combined preview shows both characters from an angled side/rear view — Aarav on left, Aanya on right — which limits the usefulness of this view for validating appearance.

---

## Overall Human Verdict

*(Complete this section after reviewing all images in `index.html`)*

**Reviewer decision:**
- [ ] APPROVED — Proceed to Stage 3 (after fixing wave pose defect)
- [ ] APPROVED WITH CONDITIONS — List conditions below
- [ ] REJECTED — List reasons below

**Conditions / Required fixes before Stage 3:**

1. Wave pose not rendering — `render_character_preview.py` applies pose but Workbench captures the frame before bone transforms propagate to rigid-body-parented mesh objects.
2. _(Add any additional reviewer observations here)_

**Reviewer signature:** _________________  
**Date:** _________________

---

*This checklist was generated automatically. All checkboxes above must be evaluated by a human reviewer looking at the actual rendered images. Automated structural tests passing does not constitute visual approval.*
