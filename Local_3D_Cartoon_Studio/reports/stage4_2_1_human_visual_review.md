# Stage 4.2.1 — Human Visual Review Checklist

**IMPORTANT: DO NOT claim or assume human approval. All checkboxes below are unchecked and must be reviewed manually by a human.**

All images are located in:
`output/stage4_2_1/previews/`

Resolution: 640×360 pixels
Engine: BLENDER_WORKBENCH with studio lighting, material colours, shadows

---

## Single-Character Renders

### 1. aarav_idle.png

**Path:** `output/stage4_2_1/previews/aarav_idle.png`  
**Description:** Aarav in AARAV_IDLE pose at frame 12 (rest/idle stance)  
**Action:** AARAV_IDLE, Frame 12  
**Size:** 165,815 bytes

**Review Criteria:**
- [ ] Aarav is facing the camera (front face visible)
- [ ] All body parts are attached and correctly aligned (head, torso, arms, legs)
- [ ] Character proportions look correct
- [ ] No visible detachment or misplacement of any mesh component
- [ ] Background is neutral (not black hole or error colour)

---

### 2. aarav_wave.png

**Path:** `output/stage4_2_1/previews/aarav_wave.png`  
**Description:** Aarav in AARAV_WAVE pose at frame 6 (arm raised mid-wave)  
**Action:** AARAV_WAVE, Frame 6  
**Size:** 165,023 bytes

**Review Criteria:**
- [ ] Aarav is facing the camera
- [ ] One arm is visibly raised (wave gesture pose)
- [ ] Raised arm parts (upper arm, lower arm, hand) are aligned with shoulder
- [ ] Other arm and all other body parts remain correctly positioned
- [ ] No detachment of arm or hand components
- [ ] Character proportions look correct

---

### 3. aarav_point.png

**Path:** `output/stage4_2_1/previews/aarav_point.png`  
**Description:** Aarav in AARAV_POINT pose at frame 8 (arm extended pointing)  
**Action:** AARAV_POINT, Frame 8  
**Size:** 164,485 bytes

**Review Criteria:**
- [ ] Aarav is facing the camera
- [ ] One arm is extended in a pointing pose
- [ ] Arm components (upper arm, forearm, hand) are properly aligned
- [ ] No detachment of pointing arm
- [ ] Rest of body correctly positioned
- [ ] Pointing gesture is visually readable

---

### 4. aarav_nod.png

**Path:** `output/stage4_2_1/previews/aarav_nod.png`  
**Description:** Aarav in AARAV_NOD pose at frame 4. NOTE: Due to rigid-parenting architecture (Option B), the head mesh does not visually move in still renders. The head bone receives the nod rotation but the head mesh object stays at its rest position. This is a documented limitation.  
**Action:** AARAV_NOD, Frame 4  
**Size:** 165,815 bytes

**Review Criteria:**
- [ ] Aarav is facing the camera
- [ ] All body parts are correctly aligned (same as idle — expected due to known limitation)
- [ ] No body part detachment
- [ ] Image is visually acceptable as a rest-pose render (nod not visible — documented)
- [ ] [ ] OPTIONAL: If head tilt is NOT visible, confirm this matches the documented limitation

---

### 5. aanya_idle.png

**Path:** `output/stage4_2_1/previews/aanya_idle.png`  
**Description:** Aanya in AANYA_IDLE pose at frame 12 with 180° orientation correction applied  
**Action:** AANYA_IDLE, Frame 12  
**Size:** 167,701 bytes

**Review Criteria:**
- [ ] Aanya is facing the camera (FRONT face visible — this was broken in Stage 4.2)
- [ ] All body parts are attached and correctly aligned
- [ ] Hijab, head, face features visible
- [ ] Character proportions look correct
- [ ] No visible detachment

---

### 6. aanya_wave.png

**Path:** `output/stage4_2_1/previews/aanya_wave.png`  
**Description:** Aanya in AANYA_WAVE pose at frame 6 with orientation correction  
**Action:** AANYA_WAVE, Frame 6  
**Size:** 168,895 bytes

**Review Criteria:**
- [ ] Aanya is facing the camera (not showing back of head)
- [ ] One arm is visibly raised in a wave gesture
- [ ] Arm components are aligned, no detachment
- [ ] Face and hijab visible
- [ ] Character proportions look correct

---

### 7. aanya_point.png

**Path:** `output/stage4_2_1/previews/aanya_point.png`  
**Description:** Aanya in AANYA_POINT pose at frame 8 with orientation correction  
**Action:** AANYA_POINT, Frame 8  
**Size:** 168,458 bytes

**Review Criteria:**
- [ ] Aanya is facing the camera
- [ ] One arm extended in pointing pose
- [ ] Arm alignment correct, no detachment
- [ ] Face visible
- [ ] Pointing gesture visually readable

---

### 8. aanya_nod.png

**Path:** `output/stage4_2_1/previews/aanya_nod.png`  
**Description:** Aanya in AANYA_NOD pose at frame 4. Same rigid-parenting head limitation applies as for Aarav NOD.  
**Action:** AANYA_NOD, Frame 4  
**Size:** 167,701 bytes

**Review Criteria:**
- [ ] Aanya is facing the camera (critical fix from Stage 4.2)
- [ ] All body parts correctly aligned
- [ ] No detachment
- [ ] Acceptable as rest-pose render (nod head tilt not visible — documented limitation)

---

## Combined Character Renders

### 9. both_facing_camera.png

**Path:** `output/stage4_2_1/previews/both_facing_camera.png`  
**Description:** Aarav and Aanya in idle pose, standing side by side facing camera  
**Actions:** AARAV_IDLE fr12, AANYA_IDLE fr12  
**Positions:** Aarav at X=-0.6, Aanya at X=+0.6  
**Size:** 168,503 bytes

**Review Criteria:**
- [ ] Both characters visible in frame
- [ ] Both characters facing the camera (front faces visible)
- [ ] Aarav on left side, Aanya on right side (or reversed — confirm visual makes sense)
- [ ] No character overlap
- [ ] Both characters have all body parts correctly assembled
- [ ] No detached head, arm, or leg components
- [ ] Relative character scale looks correct

---

### 10. greeting_interaction.png

**Path:** `output/stage4_2_1/previews/greeting_interaction.png`  
**Description:** Aarav in greeting pose, Aanya in greeting pose, side by side  
**Actions:** AARAV_GREETING fr6, AANYA_GREETING fr6  
**Size:** 168,848 bytes

**Review Criteria:**
- [ ] Both characters visible in frame
- [ ] Both facing camera (or facing each other — confirm visually appropriate)
- [ ] Aarav arm raised in greeting/wave gesture
- [ ] Aanya in corresponding greeting pose
- [ ] No detached components on either character
- [ ] Scene reads as a greeting interaction

---

### 11. pointing_interaction.png

**Path:** `output/stage4_2_1/previews/pointing_interaction.png`  
**Description:** Aarav pointing, Aanya in nod pose (nod head tilt not visible — documented limitation)  
**Actions:** AARAV_POINT fr8, AANYA_NOD fr4  
**Size:** 167,877 bytes

**Review Criteria:**
- [ ] Both characters visible in frame
- [ ] Aarav arm extended in pointing gesture
- [ ] Aanya facing camera, no detachment
- [ ] No body part displacement on either character
- [ ] Scene composition is visually coherent

---

### 12. walk_together.png

**Path:** `output/stage4_2_1/previews/walk_together.png`  
**Description:** Both characters in WALK pose at frame 1 (start of walk cycle)  
**Actions:** AARAV_WALK fr1, AANYA_WALK fr1  
**Size:** 169,599 bytes

**Review Criteria:**
- [ ] Both characters visible in frame
- [ ] Leg poses show walk cycle position (legs in alternating stride positions)
- [ ] No detached leg, foot, or arm components (this was severely broken in Stage 4.2)
- [ ] Both characters facing camera
- [ ] Arm swing visible if present in walk cycle
- [ ] Scene reads as two characters walking together

---

## Summary Checklist

| Image | Faces Camera | No Detachment | Gesture Readable | Approved |
|-------|-------------|---------------|------------------|---------|
| aarav_idle.png | [ ] | [ ] | [ ] | [ ] |
| aarav_wave.png | [ ] | [ ] | [ ] | [ ] |
| aarav_point.png | [ ] | [ ] | [ ] | [ ] |
| aarav_nod.png | [ ] | [ ] | [ ] (limitation noted) | [ ] |
| aanya_idle.png | [ ] | [ ] | [ ] | [ ] |
| aanya_wave.png | [ ] | [ ] | [ ] | [ ] |
| aanya_point.png | [ ] | [ ] | [ ] | [ ] |
| aanya_nod.png | [ ] | [ ] | [ ] (limitation noted) | [ ] |
| both_facing_camera.png | [ ] | [ ] | [ ] | [ ] |
| greeting_interaction.png | [ ] | [ ] | [ ] | [ ] |
| pointing_interaction.png | [ ] | [ ] | [ ] | [ ] |
| walk_together.png | [ ] | [ ] | [ ] | [ ] |

**All boxes are unchecked. Human review required before proceeding to Stage 4.3.**
