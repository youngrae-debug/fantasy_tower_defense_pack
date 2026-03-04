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
5. padding(기본 12px, 항목별 override 가능)을 적용합니다.

> 스크립트는 deterministic 하게 동작하며, 같은 입력/설정이면 같은 결과를 덮어써서 재생성합니다.
