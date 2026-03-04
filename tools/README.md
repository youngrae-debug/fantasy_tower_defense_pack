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

## 핵심 동작
1. 이미지 외곽 샘플로 배경색을 추정합니다.
2. 각 스프라이트마다 `search_rect`에서 자동 박스를 찾되, `bbox`와 유사도 검증(IoU/중심거리)을 통과한 경우만 채택합니다.
3. 최종 박스 주변에서 다시 정밀 보정(refine)을 수행합니다.
4. **크롭 내부에서 목표 컴포넌트(연결 픽셀)만 선택**하고, 나머지(옆 캐릭터/배경)는 alpha 0 처리합니다.
5. 선택 컴포넌트 alpha에 feather를 적용해 가장자리를 부드럽게 정리합니다.

> 즉, `rogue_side.png`는 사이드 캐릭터 1개만 남고 좌우 캐릭터가 섞이지 않도록 설계되어 있습니다.

## 소스 이미지가 없을 때
- `--dry-run`은 소스 이미지가 없어도 설정(`bbox`) 기준으로 검증 로그를 출력합니다.
- 일반 실행(파일 저장)은 소스 이미지가 필요합니다.
- 설정한 `source_image`가 없으면, 같은 `Art/Reference` 폴더에서 첫 번째 이미지 파일(`.png/.jpg/.jpeg/.webp`)을 자동으로 찾아 사용합니다.

## 배경 제거(누끼) 파라미터
- `alpha.bg_color_tolerance`: 배경색과 구분할 기준 거리
- `alpha.target_component_tolerance`: 목표 컴포넌트 추출 시 전경 판정 기준
- `alpha.component_min_area`: 목표 컴포넌트 최소 픽셀
- `alpha.edge_feather_px`: 가장자리 feather 강도

## 빗겨 나갈 때 튜닝
- 항목별로 `search_rect`를 더 타이트하게 줄입니다.
- 항목별로 `min_iou_with_bbox`를 올리면 잘못된 auto 검출을 더 엄격히 거절합니다.
- 항목별로 `refine_margin`을 줄이면 인접 캐릭터 영향이 줄어듭니다.
