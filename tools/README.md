# Sprite extraction tool

`extract_sprites.py`는 레퍼런스 시트를 캐릭터 `front/side/back` PNG로 분리합니다.
(아이템 폼은 나중에 별도 추가 가능)

## 실행
```bash
python3 tools/extract_sprites.py
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
  - `front`를 더 넓게: `[-55, 0, 55, 0]`
  - `back`도 넓게: `[-55, 0, 55, 0]`
  - `side`를 조금 더 타이트하게: `[46, 0, -46, 0]`

실행 시 `character_form`이 `outputs` 3개로 확장되어 config에 저장됩니다.

## 중요한 포인트 (지금 문제 원인)
- `pose_overrides` 값이 반영되어도, 자동탐지/자동refine가 켜져 있으면 박스가 다시 바뀔 수 있습니다.
- 그래서 수동으로 영역을 정확히 줄이고 싶다면 `use_detected_bbox: false`, `use_refine: false`로 고정하세요.

## 배경 제거 옵션
- `character_form.remove_background: false` 면 배경 제거 없이 그대로 저장
- `true` 면 목표 컴포넌트만 남기고 나머지를 alpha 0 처리

## 소스 이미지
- `source_image`가 없으면 같은 `Art/Reference` 폴더의 첫 이미지를 자동 탐색합니다.
- 이미지가 전혀 없으면 `--dry-run`만 동작합니다.

## 의존성 없이 실행 (현재 환경 대응)
`numpy`/`Pillow`가 없는 환경에서도, PNG 기준으로 `character_form`의 bbox를 그대로 잘라
`Turnaround` 이미지를 생성하도록 fallback 모드가 동작합니다.

- 이 모드에서는 배경 제거/자동 bbox 탐지/리파인 기능은 사용하지 않고, 설정된 bbox를 그대로 crop합니다.
- 권장: 로컬 개발 환경에서는 기존처럼 `numpy`/`Pillow` 설치 후 실행해 더 정확한 결과를 사용하세요.

## 저장소 반영 정책 (중요)
- 추출된 `Turnaround/*.png` 결과물은 바이너리 파일이라 PR diff에서 "binary file not supported"가 발생할 수 있어,
  기본적으로 **저장소에 커밋하지 않습니다**.
- 팀원이 동일한 결과를 얻으려면 아래 명령을 로컬에서 실행해 생성하세요.

```bash
python3 tools/extract_sprites.py
```
