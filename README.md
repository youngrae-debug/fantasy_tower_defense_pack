# fantasy_tower_defense_pack

Unity 2D 에셋/프로토타이핑을 위한 기본 저장소 구조입니다.

## 현재 적용 구조
- Unity 프로젝트 자체를 repo로 사용하는 **A안** 기반
- `Assets` 아래 단일 루트 폴더(`Assets/Rogue2DKit`) 사용
- 향후 UPM 패키지 스타일로 이전할 수 있도록 폴더 역할을 분리

## 다음 작업 권장 순서
1. Unity 프로젝트 설정 고정
   - Version Control: Visible Meta Files
   - Asset Serialization: Force Text
2. `Art/Reference`에 컨셉 시트 원본 배치
3. `Sprites/Items/Icons`에 아이콘 추출본 배치
4. `Editor/Importers`에 TextureImportPostprocessor 구현
5. `Art/Atlases`에 SpriteAtlas 생성
6. 캐릭터 파츠 분리 후 `Characters/Rogue/Parts`에 저장
7. 리깅 프리팹/애니메이션/데모 씬 구성

## 폴더 가이드
상세 가이드는 `Assets/Rogue2DKit/Documentation/README.md`를 참고하세요.
