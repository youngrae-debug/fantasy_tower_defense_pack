# Sprite extraction tool

`extract_sprites.py`는 레퍼런스 시트를 캐릭터 `front/side/back` PNG로 분리합니다.
(아이템 폼은 나중에 별도 추가 가능)

또한 `motion_sheet` 설정을 사용하면, 모션 스프라이트 시트를 **행(모션) 기준으로 분리 저장**하고,
필요하면 프레임 단위로도 저장할 수 있습니다.

## 실행
```bash
python3 tools/extract_sprites.py
```

기본 실행 동작:
- `motion_sheet`가 config에 있으면, `source_image`가 있는 `Reference` 폴더의 이미지들을 자동으로 순회해서 모션을 분할 저장합니다.
- 출력 기본 경로는 `Assets/<package_name>/Art/Sprites/Characters` 입니다.
- 캐릭터 폴더명은 `_` 앞 접두어가 아니라 **reference 파일명 전체(확장자 제외)**를 사용합니다.
  - 예: `powwow_mo2.png` -> `.../Sprites/Characters/powwow_mo2/Motions/...`
- `Strips`는 기본으로 **6등분**해서 저장합니다.
- `Strips`는 기본으로 **아래로 36px 오프셋**해서 저장합니다.

여러 PNG를 한 번에 처리(파일명 `_` 앞 기준 폴더 자동 생성 + 프레임 정렬):
```bash
python3 tools/extract_sprites.py --inputs "Assets/Rogue2DKit/Art/Sprites/Characters/Rogue/Motions/Frames/*/*.png"
```

여러 모션 시트를 한 번에 분할 저장(`motion_sheet` 설정 사용):
```bash
python3 tools/extract_sprites.py --inputs "Assets/Rogue2DKit/Art/Reference/*_mo*.png" --batch-motion --output-root "Assets/Rogue2DKit/Art/Sprites/Characters"
```

출력 루트 지정:
```bash
python3 tools/extract_sprites.py --inputs "Assets/.../*.png" --output-root "Assets/Rogue2DKit/Art/Sprites/Characters/Rogue/Motions/Aligned"
```

검증만:
```bash
python3 tools/extract_sprites.py --dry-run
```

## character_form 방식 (권장)
`tools/extract_config.json`의 `character_form`으로 3분할 시트(좌→우)를 자동 분리합니다.

주요 키:
- `order`: 분할 순서 (예: `front, side, back`)
- `split_ratios`: X축 분할 비율 2개 (예: `0.3333, 0.6666`)
- `y_ratio`: 세로 탐색 범위 비율
- `section_margin_px`: 공통 기본 여백
- `pose_overrides.<pose>.bbox_adjust_px`: 포즈별 bbox 미세 조정 `[left, top, right, bottom]`
- `use_detected_bbox`: 자동 박스 탐지 사용 여부 (`false`면 bbox 고정)
- `use_refine`: 자동 refine 사용 여부 (`false`면 bbox 그대로 사용)
  - `front`를 넓게: `[-35, 0, 35, 0]`
  - `back`은 현재값 유지(필요시 동일 방식 조정)
  - `side`를 타이트하게: `[40, 0, -40, 0]`

실행 시 `character_form`이 `outputs` 3개로 확장되어 config에 저장됩니다.

## motion_sheet 방식 (모션 분리 저장)
예시처럼 모션이 행으로 정렬된 시트에서 각 모션을 별도 PNG로 저장합니다.

주요 키:
- `grid.cols`, `grid.rows`: 시트의 프레임 그리드
- `sheet_rect`: 실제 프레임이 있는 영역 `[x0, y0, x1, y1]`
- `motion_names`: 각 행 이름 (예: `idle, walk, attack, skill, hit, death`)
- `frame_ranges`: 모션별 사용 컬럼 범위 `{ "death": [0, 1] }`
- `save_row_strip`: 행 전체(또는 frame_ranges 범위) 스트립 PNG 저장
- `save_frames`: 프레임 단위 PNG 저장
- `frames_from_strips`: `true`면 프레임을 원본 그리드 대신 저장된 스트립 좌표 기준으로 분할
- `frame_x_shift_px`: 모션별 프레임 X축 보정값 (예: `"attack": [6, 3, -3, -6]`)
- `character_frame_x_shift_px`: 캐릭터별로 `frame_x_shift_px`를 오버라이드
- `strip_rows`: 스트립을 세로로 몇 등분해서 저장할지 (기본값: `grid.rows`, 기본 실행에서는 `6`으로 강제)
- `strip_offset_px`: 스트립 전용 오프셋 `[x, y]` (기본 실행에서는 `[0, 36]`)
- `cell_offset_px`: 전체 셀 크롭 오프셋 `[x, y]` (약간 빗겨 잘릴 때 미세 보정)
- `strip_output_dir`, `frame_output_dir`: 출력 경로

추가 참고:
- 그리드 폭/높이가 나누어떨어지지 않아도, 내부적으로 경계를 반올림해서 누적 오차를 줄입니다.

실행 시 로그 예:
- `[motion] strip idle: row=0 cols=0-3 output=.../idle.png`
- `[motion] frame idle: row=0 col=0 output=.../idle/idle_00.png`

## 중요한 포인트 (지금 문제 원인)
- `pose_overrides` 값이 반영되어도, 자동탐지/자동refine가 켜져 있으면 박스가 다시 바뀔 수 있습니다.
- 그래서 수동으로 영역을 정확히 줄이고 싶다면 `use_detected_bbox: false`, `use_refine: false`로 고정하세요.

## batch 모드 정렬 규칙
- `--inputs`를 주면 config 기반 분할 대신 배치 모드로 동작합니다.
- `--batch-motion`까지 같이 주면, 일반 배치 대신 `motion_sheet` 기준 모션 분할을 수행합니다.
- 출력 폴더는 파일명 `_` 앞 접두어로 자동 생성됩니다.
  - 예: `attack_00.png` -> `<output-root>/attack/attack_00.png`
  - 예: `powwow_mo2.png` + `--batch-motion` -> `<output-root>/powwow/Motions/Frames/...`
- 같은 접두어 그룹(예: `attack_*`) 안에서는 가장 큰 프레임 크기에 맞춘 공통 캔버스를 만들고, 기본값으로 `bottom-center` 정렬해서 위치 흔들림을 줄입니다.
- 정렬 기준은 `--align-anchor bottom-center|center`로 바꿀 수 있습니다.

## 배경 제거 옵션
- `character_form.remove_background: false` 면 배경 제거 없이 그대로 저장
- `true` 면 목표 컴포넌트만 남기고 나머지를 alpha 0 처리

## 소스 이미지
- `source_image`가 없으면 같은 `Art/Reference` 폴더의 첫 이미지를 자동 탐색합니다.
- 이미지가 전혀 없으면 `--dry-run`만 동작합니다.
