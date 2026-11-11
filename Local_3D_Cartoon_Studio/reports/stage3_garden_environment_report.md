# Stage 3 - Reusable Cartoon Garden Environment Report

Generated: 2026-11-11T12:07:57.130076Z

## Overview

A reusable cartoon garden environment built procedurally in Blender 4.4.3 (Workbench only). The garden is centred on a 20x20 BU grass plane with a winding path, trees, bushes, flowers, decorative stones/sign/bench, cartoon clouds, a sun lamp, a sky-blue world background, and three cameras. A character-integration preview places Aarav and Aanya on the stage and renders with Garden_Main_Camera.

## Statistics (real, from garden.blend)

- total_polygons: 2416
- total_objects: 75
- total_materials: 34
- generation_time_s: 0.541
- blend_file_size_bytes: 1707018

## Collections (9)

- Environment_Ground
- Environment_Path
- Environment_Trees
- Environment_Bushes
- Environment_Flowers
- Environment_Decorations
- Environment_Sky
- Lighting
- Cameras

## Cameras

- Garden_Main_Camera
- Garden_Wide_Camera
- Garden_Close_Camera

## Validation (validate_garden.py)

- verdict: **PASS**

| check | pass |
| --- | --- |
| all_9_collections_exist | PASS |
| ground_plane_at_z0 | PASS |
| at_least_3_trees | PASS |
| at_least_4_bushes | PASS |
| at_least_8_flowers | PASS |
| at_least_3_cameras | PASS |
| all_objects_valid_dimensions | PASS |
| character_area_clear | PASS |
| validation_json_written | PASS |

## Previews (640x360 Workbench)

| preview | size (bytes) | render_time_s |
| --- | --- | --- |
| garden_wide | 292534 | 2.082 |
| garden_main | 265855 | 0.2 |
| garden_close | 238354 | 0.216 |
| garden_with_characters | 288509 | 0.243 |

## Tests

- total: 33 passed, 0 failed, 0 skipped, 0 errors
- new garden tests: 11 passed (test_garden_generation.py: 6, test_garden_render.py: 5)
- stage 2 regression: 22 passed (all 22 still green)
- overall: **PASS**

## Files

- blend: blender/assets/environments/garden/garden.blend
- json: blender/assets/environments/garden/garden.json
- previews: blender/assets/environments/garden/previews/*.png
- scripts: blender/scripts/{garden_utils,create_garden,validate_garden,render_garden_previews}.py
- tests: tests/{test_garden_generation,test_garden_render}.py
- raw results: .agents/tasks/stage3-garden/results.json
