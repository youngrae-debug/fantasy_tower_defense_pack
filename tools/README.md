# Sprite extraction tool

`extract_sprites.py`는 레퍼런스 시트를 캐릭터 `front/side/back` PNG로 분리합니다.
(아이템은 별도 폼을 나중에 추가 가능)

## 실행
```bash
python3 tools/extract_sprites.py
```

검증만:
```bash
python3 tools/extract_sprites.py --dry-run
```

## character_form 방식 (권장)
`tools/extract_config.json`의 `character_form`을 사용하면,
3분할 시트(좌→우)에서 자동으로 `front`, `side`, `back` 출력 항목을 생성합니다.

주요 키:
- `character_name`: 출력 파일명/폴더에 사용
- `order`: 분할 순서 (예: `["front", "side", "back"]`)
- `split_ratios`: X축 분할 비율 2개 (기본 1/3, 2/3)
- `y_ratio`: 세로 탐색 비율
- `section_margin_px`: 각 구간에서 가장자리 여백
- `min_iou_with_bbox`, `max_center_shift`, `refine_margin`: 검출 안정화

실행 시 `character_form`이 `outputs` 3개로 확장되어 config에 저장됩니다.

## 배경 제거(누끼)
- 목표 컴포넌트(연결된 픽셀) 1개만 남기고 나머지는 alpha 0 처리
- `edge_feather_px`로 가장자리 부드럽게 처리

파라미터:
- `alpha.bg_color_tolerance`
- `alpha.target_component_tolerance`
- `alpha.component_min_area`
- `alpha.edge_feather_px`

## 소스 이미지
- `source_image`가 없으면 같은 `Art/Reference` 폴더의 첫 이미지를 자동 탐색합니다.
- 이미지가 전혀 없으면 `--dry-run`만 동작합니다.
