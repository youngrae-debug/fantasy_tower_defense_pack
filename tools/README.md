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
  - 현재 `knight.png` 기준 권장/정상 순서는 **왼쪽→오른쪽 = front, side, back** 입니다.
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


## 출력 고정/재생성 규칙 (뒤죽박죽 방지)
- `outputs`가 비어 있으면 매 실행 시 `character_form`으로 출력 좌표를 계산합니다.
- `outputs`가 채워져 있으면 해당 값(고정값)을 우선 사용합니다.
- 강제로 `character_form` 기준으로 다시 계산하려면:

```bash
python3 tools/extract_sprites.py --rebuild-outputs-from-form
```

- 재계산 결과를 config에 저장하려면:

```bash
python3 tools/extract_sprites.py --rebuild-outputs-from-form --write-config
```

## Animator는 어디에 생성되나?
- Enemy Animator Controller 파일 경로:
  `Assets/Rogue2DKit/Animations/Controllers/Enemy.controller`
- Animation은 "이미지 파일 자체"가 아니라, **Sprite를 시간축으로 재생하는 Animation Clip + Animator 상태머신** 조합입니다.
- 추출 스크립트는 이미지만 생성합니다. 클립/상태 연결은 Unity 메뉴에서 자동 생성하세요:

```text
Rogue2DKit/Animations/Rebuild Enemy Animator From Turnaround
```

- 위 메뉴는 `Turnaround` 스프라이트를 읽어 `Enemy_Idle/Walk/Attack/Death.anim`을 만들고,
  `Enemy.controller`의 Idle/Walk/Attack/Death 상태에 자동 연결합니다.
- 추가로 스킬용 placeholder 클립 `Enemy_Skill_Slash`, `Enemy_Skill_Cast`도 자동 생성하고
  Animator에 `SkillSlash`, `SkillCast` 트리거 + 상태/전이를 자동으로 추가합니다.

## front/back/side 3장만으로 가능한 범위
- 현재 `Turnaround` 3포즈(front/back/side)만 있으면, 툴이 **기본 루프용 placeholder 애니메이션**(Idle/Walk/Attack/Death)을 만들 수는 있습니다.
- 하지만 이건 "움직여 보이게" 하는 최소 구성입니다.
- **실제 공격 스킬 모션(베기, 찌르기, 캐스팅, 피격 반동 등)** 을 자연스럽게 표현하려면
  스킬별 연속 프레임 스프라이트(또는 본/리깅 애니메이션)가 추가로 필요합니다.
- 권장: 자동 생성된 `Enemy_Skill_Slash`, `Enemy_Skill_Cast`는 임시 클립으로 사용하고,
  실제 게임용 스킬별 고유 프레임 클립으로 교체/확장하세요.
