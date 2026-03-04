# Rogue2DKit 구조 안내

## 루트 원칙
`Assets/Rogue2DKit` 아래에서만 에셋을 관리합니다.

## 주요 폴더
- `Art/Reference`: 원본 컨셉 시트(참고용)
- `Art/Sprites/Characters/Rogue/Parts`: 리깅용 파츠 스프라이트
- `Art/Sprites/Items/Icons`: 아이템 아이콘 스프라이트
- `Art/Atlases`: SpriteAtlas 자산
- `Animations/Controllers`: Animator Controller
- `Animations/Clips`: Animation Clip
- `Prefabs/Characters`: 캐릭터 프리팹
- `Prefabs/UI`: UI 프리팹
- `Runtime`: 런타임 스크립트
- `Editor/Importers`: 임포트 자동화 스크립트
- `ScriptableObjects/Items`: 아이템 정의 SO
- `Scenes/Demo`: 데모 씬

## 네이밍 예시
- Reference: `ref_rogue_turnaround_v01.png`
- Icon: `icon_dagger.png`, `icon_potion_green.png`
- Prefab: `pref_chr_rogue_rigged.prefab`
- AnimationClip: `clip_rogue_idle.anim`
- AnimatorController: `ac_rogue.controller`

## 체크리스트(요약)
1. 원본/실사용 스프라이트 구분
2. 아이콘부터 추출해 빠른 UI 데모 확보
3. 폴더 기반 TextureImporter 자동화
4. Atlas 구성 후 렌더링 확인
5. 파츠 분리 → 리깅 → 애니메이션 최소 세트
6. ScriptableObject + 데모 씬으로 재사용성 검증
