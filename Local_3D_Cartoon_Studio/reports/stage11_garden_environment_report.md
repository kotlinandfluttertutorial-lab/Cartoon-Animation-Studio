# Stage 11 garden environment

## Existing garden and design

The original garden has a flat lawn, sparse flower accents, repeated rounded trees and a narrow path. The Stage 11 asset uses the four supplied references for its winding pale path, layered vegetation, friendly tree crowns, flower borders and cedar seating and fence. The setting remains an original procedural Blender scene.

The asset adds subtly raised terrain outside the walk lane, linked trunks and foliage meshes, batched wildflowers and grass, a bench, stepping stones, rocks, a sign, a stylized pond with lily pads, two birds and decorative butterflies. Distant hills, soft cloud shapes and a bright blue world give the background depth. The bench, sign and pond sit outside the performance corridor. Materials use lightweight solid colors.

## Implementation and compatibility

- New builder `blender/scripts/build_stage11_garden.py`
- Separate environment `output/stage11_garden_previews/final/garden_stage11.blend`
- Existing `Ground_Plane`, `Path_Main`, nine collection names, and three `Garden_*_Camera` object names are preserved in the new asset. The builder adds seven detail and character cameras.
- The 640 × 360 previews use Workbench with the paint studio light, low shadow intensity and cavity shading. A sun is included in the scene for compatibility with lighting tests. Workbench uses its studio light for these previews.
- Preview generation appends the approved Stage 10 variants and samples their existing walk and greeting actions. The reusable garden blend itself contains the environment and cameras. Production defaults continue to use the original garden.
- The original MP4 hash and all 164 source asset hashes matched. Stage 10 approval was recorded in its Markdown and JSON reports.

## Automated validation

The new blend saved and reopened. Blender checked mesh references and materials for 243 environment mesh objects, including linked instances, and counted 16,245 face instances. All 55 downward ray tests on the lane hit the path surface. The medium, walking and interaction views passed camera and clear-sightline checks for both characters' heads, torsos and feet. All ten PNGs decoded at 640 × 360. FFmpeg encoded and decoded a 12-frame H.264 clip from the final still, and FFprobe verified 12 fps and the expected dimensions. This clip checks media compatibility.

## Visual inspection

The assistant inspected the final contact sheet and selected full-resolution PNGs. The front and pathway views show an open route. Trees frame the cast and the fence breaks at the path. The medium and interaction views retain both characters and the foliage adds depth without obscuring the tested landmarks. Grass and petals are stylized polygon meshes. Workbench provides a clean, pastel daylight look with simplified shadows.

The user explicitly approved the Stage 11 garden and previews for visual sign-off.

## Performance

| Measurement | Observed |
| --- | ---: |
| Stage 11 build, reload and 10 stills | 5.607 s wall time |
| Stage 11 sampled peak Blender RSS | 334.98 MiB |
| Environment construction | 0.398 s |
| New garden blend reload | 0.028 s |
| First wide render | 2.042 s |
| Subsequent stills | 0.152–0.294 s each |
| Original garden wide still, cold process | 1.601 s render, 257.95 MiB peak RSS |

Both runs used six Blender threads. The original memory measurement covers one still. The Stage 11 measurement covers build, reload, and previews with both characters, so it is a workload comparison. RSS is process working-set memory and excludes GPU memory.

## Reproduction

Run from the repository root with a fresh output directory:

```powershell
& ./tools/blender-4.4.3-windows-x64/blender.exe -b -t 6 --python-exit-code 1 --python Local_3D_Cartoon_Studio/blender/scripts/build_stage11_garden.py -- <new-output-directory>
```

## Limitations and next stage

The walking preview is a sampled pose. Lane and camera checks are sampled, with continuous foot locking, character interaction timing, and secondary animation left for Stage 12. The pond and butterflies are decorative. No Stage 12 changes were made.

## Regression result

All 182 existing tests passed with one deprecation warning in the disposable checkout.
