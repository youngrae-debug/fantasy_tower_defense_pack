# Sprite extraction tool

`extract_sprites.py`는 레퍼런스 시트에서 캐릭터 턴어라운드/아이콘을 잘라 PNG로 내보냅니다.

## 파일
- `tools/extract_sprites.py`: 추출 스크립트
- `tools/extract_config.json`: 초기 바운딩 박스 + 출력 경로

## 요구 사항
- Python 3.10+
- Pillow
- numpy

설치 예시:

```bash
python3 -m pip install pillow numpy
```

## 실행
기본 설정 파일 사용:

```bash
python3 tools/extract_sprites.py
```

박스 검증만(파일 저장 안 함):

```bash
python3 tools/extract_sprites.py --dry-run
```

커스텀 설정 파일 사용:

```bash
python3 tools/extract_sprites.py --config tools/extract_config.json
```

## 동작 방식
1. 이미지 외곽 샘플로 배경색을 추정합니다.
2. 각 스프라이트마다 `search_rect` 내 자동 검출을 시도합니다.
3. 자동 검출 실패 시 `bbox`를 그대로 사용합니다. (fallback)
4. 경계에서 연결된 배경색을 alpha 0으로 만들어 투명 배경 PNG를 출력합니다.
5. 배경색 거리 기반 소프트 alpha(외곽→내부)를 적용해 테두리 halo를 줄입니다.
6. padding(기본 12px, 항목별 override 가능)을 적용합니다.

> 스크립트는 deterministic 하게 동작하며, 같은 입력/설정이면 같은 결과를 덮어써서 재생성합니다.

## 소스 이미지가 없을 때
- `--dry-run`은 소스 이미지가 없어도 설정(`bbox`) 기준으로 검증 로그를 출력합니다.
- 일반 실행(파일 저장)은 소스 이미지가 필요합니다.
- 설정한 `source_image`가 없으면, 같은 `Art/Reference` 폴더에서 첫 번째 이미지 파일(`.png/.jpg/.jpeg/.webp`)을 자동으로 찾아 사용합니다.


## 미세하게 빗겨 보일 때 튜닝
- 인접 캐릭터/아이템이 섞이면, 자동 검출은 `bbox`와 가장 유사한 연결 컴포넌트만 선택하도록 동작합니다.
- 자동 검출 박스는 `bbox`와 IoU/중심거리 검증을 통과한 경우에만 채택됩니다.
- 검증 실패 시 설정 `bbox`로 자동 fallback 됩니다.
- 마지막으로 `refine_margin` 범위에서 전경을 다시 타이트하게 잡아 미세 오프셋을 줄입니다.
- 필요 시 항목별로 아래 키를 조정하세요: `min_iou_with_bbox`, `max_center_shift`, `refine_margin`.


## 배경 제거(누끼) 파라미터
- `alpha.edge_expand_tolerance`: 가장자리 연결 배경을 제거하는 기준값
- `alpha.soft_outer_tolerance`: 이 값 이하 배경색 거리 픽셀은 alpha 0 처리
- `alpha.soft_inner_tolerance`: 이 값 이상은 alpha 255 처리, 사이 구간은 점진적 반투명

일반적으로 `soft_outer_tolerance < soft_inner_tolerance`로 설정하세요.
