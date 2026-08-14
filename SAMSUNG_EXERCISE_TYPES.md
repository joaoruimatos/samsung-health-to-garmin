# Samsung Exercise Type Reference

This file documents the two Samsung exercise-type schemas relevant to this project.

> **This converter currently supports Samsung Health exports using Samsung's legacy numeric `EXERCISE_TYPE` values.**  
> Current Samsung Health exports may still contain these numeric identifiers even though Samsung's newer Health Data SDK uses named `PredefinedExerciseType` enum values such as `WALKING`, `RUNNING`, and `HIKING`.  
> The new Health Data SDK enum list is provided separately as a reference for future development and should not be confused with the numeric IDs found in the exports currently handled by this converter.

## Sources

- Samsung legacy numeric exercise types: https://developer.samsung.com/health/android/data/api-reference/EXERCISE_TYPE.html
- Samsung Health Data SDK `PredefinedExerciseType`: https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/-exercise-type/-predefined-exercise-type/index.html
- Samsung migration example: https://developer.samsung.com/health/data/migration-guide/exercise-app-example.html
- Garmin FIT sport/sub-sport profile: https://github.com/garmin/fit-python-sdk/blob/main/garmin_fit_sdk/profile.py

## Enabled and tested legacy numeric mappings

These are the ten numeric IDs enabled by default in `samsung_health_to_fit.py` because they were used and tested during the migration that produced this project.

| Samsung ID | Samsung activity | Garmin FIT |
|---:|---|---|
| 1001 | Walking | `walking / generic` |
| 1002 | Running | `running / generic` |
| 10006 | Sit-ups | `training / strength_training` |
| 10007 | Circuit training, moderate effort | `training / cardio_training` |
| 11007 | Cycling | `cycling / generic` |
| 13001 | Hiking | `hiking / generic` |
| 14001 | Swimming, general (not lap swimming) | `swimming / generic` |
| 15002 | Weight machine | `training / strength_training` |
| 15003 | Exercise bike | `cycling / indoor_cycling` |
| 15005 | Treadmill, jogging/walking | `running / treadmill` |

## Other legacy numeric IDs

See the complete commented mapping block in `samsung_health_to_fit.py` and the collapsible table in `README.md`. Those entries are suggestions and are not enabled by default.

## New Samsung Health Data SDK named enums

The newer API uses named `PredefinedExerciseType` values rather than the numeric IDs parsed by this converter. The mappings below are reference suggestions for future development; they are **not active parser mappings**.

| Health Data SDK enum | Closest legacy numeric ID | Suggested Garmin FIT | Confidence |
|---|---:|---|---|
| `UNDEFINED` | — | `generic / generic` | approximate |
| `OTHER` | — | `generic / generic` | custom |
| `WALKING` | 1001 | `walking / generic` | exact |
| `RUNNING` | 1002 | `running / generic` | exact |
| `STAIR_CLIMBING` | — | `floor_climbing / generic` | exact |
| `TRACK_RUNNING` | — | `running / track` | exact |
| `BASEBALL` | 2001 | `baseball / generic` | exact |
| `SOFTBALL` | 2002 | `baseball / generic` | close |
| `CRICKET` | 2003 | `cricket / generic` | exact |
| `GOLF` | 3001 | `golf / generic` | exact |
| `BOWLING` | 3003 | `generic / generic` | approximate |
| `HOCKEY` | 4001 | `hockey / generic` | close |
| `RUGBY` | 4002 | `rugby / generic` | exact |
| `BASKETBALL` | 4003 | `basketball / generic` | exact |
| `SOCCER` | 4004 | `soccer / generic` | exact |
| `HANDBALL` | 4005 | `team_sport / generic` | approximate |
| `AMERICAN_FOOTBALL` | 4006 | `american_football / generic` | exact |
| `VOLLEYBALL` | 5001 | `volleyball / generic` | exact |
| `BEACH_VOLLEYBALL` | 5002 | `volleyball / generic` | close |
| `SQUASH` | 6001 | `racket / squash` | exact |
| `TENNIS` | 6002 | `tennis / generic` | exact |
| `BADMINTON` | 6003 | `racket / badminton` | exact |
| `TABLE_TENNIS` | 6004 | `racket / table_tennis` | exact |
| `RACQUETBALL` | 6005 | `racket / racquetball` | exact |
| `BOXING` | 7002 | `boxing / generic` | exact |
| `MARTIAL_ARTS` | 7003 | `mixed_martial_arts / generic` | close |
| `BALLET` | 8001 | `dance / generic` | close |
| `DANCING` | 8002 | `dance / generic` | exact |
| `BALLROOM_DANCING` | 8003 | `dance / generic` | close |
| `PILATES` | 9001 | `fitness_equipment / pilates` | exact |
| `YOGA` | 9002 | `training / yoga` | exact |
| `STRETCHING` | 10001 | `training / flexibility_training` | exact |
| `JUMP_ROPE` | 10002 | `jump_rope / generic` | exact |
| `HULA_HOOPING` | 10003 | `training / cardio_training` | approximate |
| `PUSH_UPS` | 10004 | `training / strength_training` | close |
| `PULL_UPS` | 10005 | `training / strength_training` | close |
| `SIT_UPS` | 10006 | `training / strength_training` | close |
| `CIRCUIT_TRAINING` | 10007 | `training / cardio_training` | close |
| `MOUNTAIN_CLIMBERS` | 10008 | `training / cardio_training` | approximate |
| `JUMPING_JACKS` | 10009 | `training / cardio_training` | approximate |
| `BURPEES` | 10010 | `hiit / generic` | close |
| `BENCH_PRESS` | 10011 | `training / strength_training` | close |
| `SQUATS` | 10012 | `training / strength_training` | close |
| `LUNGES` | 10013 | `training / strength_training` | close |
| `LEG_PRESSES` | 10014 | `training / strength_training` | close |
| `LEG_EXTENSIONS` | 10015 | `training / strength_training` | close |
| `LEG_CURLS` | 10016 | `training / strength_training` | close |
| `BACK_EXTENSIONS` | 10017 | `training / strength_training` | close |
| `LAT_PULLDOWNS` | 10018 | `training / strength_training` | close |
| `DEADLIFTS` | 10019 | `training / strength_training` | close |
| `SHOULDER_PRESSES` | 10020 | `training / strength_training` | close |
| `FRONT_RAISES` | 10021 | `training / strength_training` | close |
| `LATERAL_RAISES` | 10022 | `training / strength_training` | close |
| `CRUNCH` | 10023 | `training / strength_training` | close |
| `LEG_RAISES` | 10024 | `training / strength_training` | close |
| `PLANK` | 10025 | `training / strength_training` | close |
| `ARM_CURLS` | 10026 | `training / strength_training` | close |
| `ARM_EXTENSIONS` | 10027 | `training / strength_training` | close |
| `SKATERS` | — | `training / cardio_training` | approximate |
| `HIGH_KNEES` | — | `training / cardio_training` | approximate |
| `INLINE_SKATING` | 11001 | `inline_skating / generic` | exact |
| `HANG_GLIDING` | 11002 | `hang_gliding / generic` | exact |
| `ARCHERY` | 11004 | `archery / generic` | exact |
| `HORSEBACK_RIDING` | 11005 | `horseback_riding / generic` | exact |
| `BIKING` | 11007 | `cycling / generic` | exact |
| `FLYING_DISC` | 11008 | `generic / generic` | approximate |
| `ROLLER_SKATING` | 11009 | `inline_skating / generic` | approximate |
| `AEROBICS` | 12001 | `training / cardio_training` | close |
| `HIKING` | 13001 | `hiking / generic` | exact |
| `ROCK_CLIMBING` | 13002 | `rock_climbing / generic` | exact |
| `BACKPACKING` | 13003 | `hiking / rucking` | close |
| `MOUNTAIN_BIKING` | 13004 | `cycling / mountain` | exact |
| `ORIENTEERING` | 13005 | `running / navigate` | approximate |
| `POOL_SWIMMING` | — | `swimming / lap_swimming` | close |
| `AQUA_AEROBICS` | 14002 | `training / cardio_training` | approximate |
| `CANOEING` | 14003 | `canoeing / generic` | exact |
| `SAILING` | 14004 | `sailing / generic` | exact |
| `SCUBA_DIVING` | 14005 | `diving / generic` | close |
| `SNORKELING` | 14006 | `snorkeling / generic` | exact |
| `KAYAKING` | 14007 | `kayaking / generic` | exact |
| `KITESURFING` | 14008 | `kitesurfing / generic` | exact |
| `RAFTING` | 14009 | `rafting / generic` | exact |
| `ROWING` | — | `rowing / generic` | exact |
| `WINDSURFING` | 14011 | `windsurfing / generic` | exact |
| `YACHTING` | 14012 | `sailing / generic` | close |
| `WATER_SKIING` | 14013 | `water_skiing / generic` | exact |
| `STEP_MACHINE` | 15001 | `fitness_equipment / stair_climbing` | exact |
| `WEIGHT_MACHINE` | 15002 | `training / strength_training` | close |
| `STATIONARY_BIKING` | 15003 | `cycling / indoor_cycling` | exact |
| `ROWING_MACHINE` | 15004 | `rowing / indoor_rowing` | exact |
| `TREADMILL` | 15005 | `running / treadmill` | close |
| `ELLIPTICAL` | 15006 | `fitness_equipment / elliptical` | exact |
| `STAIR_CLIMBING_MACHINE` | — | `fitness_equipment / stair_climbing` | exact |
| `CROSS_COUNTRY_SKIING` | 16001 | `cross_country_skiing / generic` | exact |
| `SKIING` | 16002 | `alpine_skiing / generic` | close |
| `ICE_DANCING` | 16003 | `ice_skating / generic` | close |
| `ICE_SKATING` | 16004 | `ice_skating / generic` | exact |
| `ICE_HOCKEY` | 16006 | `hockey / ice` | exact |
| `SNOWBOARDING` | 16007 | `snowboarding / generic` | exact |
| `ALPINE_SKIING` | 16008 | `alpine_skiing / generic` | exact |
| `SNOWSHOEING` | 16009 | `snowshoeing / generic` | exact |
| `TRIATHLON` | — | `multisport / triathlon` | exact |
| `DUATHLON` | — | `multisport / duathlon` | exact |
| `AQUATHLON` | — | `multisport / swim_run` | close |
| `AQUABIKE` | — | `multisport / generic` | approximate |
| `CROSS_TRIATHLON` | — | `multisport / triathlon` | close |
| `CROSS_DUATHLON` | — | `multisport / duathlon` | close |
| `BREAK` | — | `generic / generic` | approximate |
| `COOL_DOWN` | — | `training / generic` | approximate |
| `WARM_UP` | — | `training / generic` | approximate |
| `TRANSITION` | — | `transition / generic` | exact |
| `ZUMBA` | — | `dance / generic` | close |
| `OPEN_WATER_SWIMMING` | — | `swimming / open_water` | exact |

### Important differences

- The schemas are not a perfect one-to-one rename. The newer SDK adds entries such as `TRACK_RUNNING`, `STAIR_CLIMBING`, `TRIATHLON`, `DUATHLON`, `ZUMBA`, and `OPEN_WATER_SWIMMING`.
- Some legacy numeric types do not have an obvious named replacement in the current enum list, for example legacy Billiards (`3002`) and Pistol shooting (`11003`).
- `POOL_SWIMMING` is not treated as a direct replacement for legacy `14001`, because the legacy description explicitly says “not lap swimming.”
- A new `ExerciseType` may contain multiple `ExerciseSession` objects. Supporting those records correctly may require more than a simple one-row-to-one-FIT-file conversion.
