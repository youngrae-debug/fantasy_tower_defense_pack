using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace Rogue2DKit.Editor.Importers
{
    public static class EnemyAnimationBuilder
    {
        private const string TurnaroundDir = "Assets/Rogue2DKit/Art/Sprites/Characters/Rogue/Turnaround";
        private const string ClipsDir = "Assets/Rogue2DKit/Animations/Clips";
        private const string ControllerPath = "Assets/Rogue2DKit/Animations/Controllers/Enemy.controller";

        [MenuItem("Rogue2DKit/Animations/Rebuild Enemy Animator From Turnaround")]
        public static void RebuildEnemyAnimatorFromTurnaround()
        {
            var sprites = LoadTurnaroundSprites();
            if (sprites.Count == 0)
            {
                Debug.LogError($"No turnaround sprites found in: {TurnaroundDir}");
                return;
            }

            EnsureFolderExists(ClipsDir);

            var front = GetExistingSprite(sprites, "front") ?? sprites[0];
            var side = GetExistingSprite(sprites, "side") ?? front;
            var back = GetExistingSprite(sprites, "back") ?? front;

            var idleClip = CreateOrUpdateClip("Enemy_Idle", front, 1f, true);
            var walkClip = CreateOrUpdateClip("Enemy_Walk", new[] { side, back, front, side }, 8f, true);
            var attackClip = CreateOrUpdateClip("Enemy_Attack", new[] { front, side, front }, 10f, false);
            var deathClip = CreateOrUpdateClip("Enemy_Death", back, 1f, false);

            var skillSlashClip = CreateOrUpdateClip("Enemy_Skill_Slash", new[] { side, front, side, front }, 12f, false);
            AddPositionPunch(skillSlashClip, 12f, new[] { 0f, 0.05f, 0.14f, 0f });

            var skillCastClip = CreateOrUpdateClip("Enemy_Skill_Cast", new[] { back, front, back, front }, 8f, false);
            AddScalePulse(skillCastClip, 8f, new[] { 1f, 1.08f, 1f, 1.06f });

            Debug.LogWarning(
                "EnemyAnimationBuilder generates placeholder clips from turnaround poses. " +
                "For production-quality skill motion, replace with dedicated per-skill frame animations.");

            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            if (controller == null)
            {
                Debug.LogError($"Enemy AnimatorController not found: {ControllerPath}");
                return;
            }

            EnsureTriggerParameter(controller, "SkillSlash");
            EnsureTriggerParameter(controller, "SkillCast");

            var idleState = EnsureState(controller, "Idle", new Vector3(260, 90, 0));
            var walkState = EnsureState(controller, "Walk", new Vector3(470, 90, 0));
            var attackState = EnsureState(controller, "Attack", new Vector3(260, 260, 0));
            var deathState = EnsureState(controller, "Death", new Vector3(470, 260, 0));
            var skillSlashState = EnsureState(controller, "SkillSlash", new Vector3(650, 260, 0));
            var skillCastState = EnsureState(controller, "SkillCast", new Vector3(820, 260, 0));

            idleState.motion = idleClip;
            walkState.motion = walkClip;
            attackState.motion = attackClip;
            deathState.motion = deathClip;
            skillSlashState.motion = skillSlashClip;
            skillCastState.motion = skillCastClip;

            EnsureAnyStateTriggerTransition(controller, attackState, "Attack");
            EnsureAnyStateTriggerTransition(controller, deathState, "Dead");
            EnsureAnyStateTriggerTransition(controller, skillSlashState, "SkillSlash");
            EnsureAnyStateTriggerTransition(controller, skillCastState, "SkillCast");

            EnsureReturnToIdleTransition(attackState, idleState, 0.9f);
            EnsureReturnToIdleTransition(skillSlashState, idleState, 0.95f);
            EnsureReturnToIdleTransition(skillCastState, idleState, 0.95f);

            EditorUtility.SetDirty(controller);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            Debug.Log("Enemy animator clips and skill states were generated and assigned successfully.");
        }

        private static List<Sprite> LoadTurnaroundSprites()
        {
            var loaded = new List<Sprite>();
            var guids = AssetDatabase.FindAssets("t:Sprite", new[] { TurnaroundDir });
            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(path);
                if (sprite != null)
                {
                    loaded.Add(sprite);
                }
            }

            loaded.Sort((a, b) => string.Compare(a.name, b.name, System.StringComparison.Ordinal));
            return loaded;
        }

        private static Sprite GetExistingSprite(List<Sprite> sprites, string poseName)
        {
            return sprites.Find(s => s.name.ToLowerInvariant().Contains(poseName));
        }

        private static AnimationClip CreateOrUpdateClip(string clipName, Sprite sprite, float sampleRate, bool loop)
        {
            return CreateOrUpdateClip(clipName, new[] { sprite }, sampleRate, loop);
        }

        private static AnimationClip CreateOrUpdateClip(string clipName, IEnumerable<Sprite> spriteFrames, float sampleRate, bool loop)
        {
            var validFrames = new List<Sprite>();
            foreach (var frame in spriteFrames)
            {
                if (frame != null)
                {
                    validFrames.Add(frame);
                }
            }

            if (validFrames.Count == 0)
            {
                Debug.LogError($"Cannot create clip '{clipName}': no valid sprite frames.");
                return null;
            }

            var clipPath = $"{ClipsDir}/{clipName}.anim";
            var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
            if (clip == null)
            {
                clip = new AnimationClip { name = clipName };
                AssetDatabase.CreateAsset(clip, clipPath);
            }

            clip.frameRate = sampleRate;
            var binding = new EditorCurveBinding
            {
                path = string.Empty,
                type = typeof(SpriteRenderer),
                propertyName = "m_Sprite"
            };

            var keyframes = new ObjectReferenceKeyframe[validFrames.Count];
            for (var i = 0; i < validFrames.Count; i++)
            {
                keyframes[i] = new ObjectReferenceKeyframe
                {
                    time = i / sampleRate,
                    value = validFrames[i]
                };
            }

            AnimationUtility.SetObjectReferenceCurve(clip, binding, keyframes);
            SetLooping(clip, loop);

            EditorUtility.SetDirty(clip);
            return clip;
        }

        private static void AddPositionPunch(AnimationClip clip, float sampleRate, IReadOnlyList<float> xValues)
        {
            if (clip == null || xValues == null || xValues.Count == 0)
            {
                return;
            }

            var curve = new AnimationCurve();
            for (var i = 0; i < xValues.Count; i++)
            {
                curve.AddKey(new Keyframe(i / sampleRate, xValues[i]));
            }

            var binding = new EditorCurveBinding
            {
                path = string.Empty,
                type = typeof(Transform),
                propertyName = "m_LocalPosition.x"
            };
            AnimationUtility.SetEditorCurve(clip, binding, curve);
            EditorUtility.SetDirty(clip);
        }

        private static void AddScalePulse(AnimationClip clip, float sampleRate, IReadOnlyList<float> scaleValues)
        {
            if (clip == null || scaleValues == null || scaleValues.Count == 0)
            {
                return;
            }

            var curveX = new AnimationCurve();
            var curveY = new AnimationCurve();
            for (var i = 0; i < scaleValues.Count; i++)
            {
                var t = i / sampleRate;
                curveX.AddKey(new Keyframe(t, scaleValues[i]));
                curveY.AddKey(new Keyframe(t, scaleValues[i]));
            }

            AnimationUtility.SetEditorCurve(clip, new EditorCurveBinding
            {
                path = string.Empty,
                type = typeof(Transform),
                propertyName = "m_LocalScale.x"
            }, curveX);
            AnimationUtility.SetEditorCurve(clip, new EditorCurveBinding
            {
                path = string.Empty,
                type = typeof(Transform),
                propertyName = "m_LocalScale.y"
            }, curveY);

            EditorUtility.SetDirty(clip);
        }

        private static void SetLooping(AnimationClip clip, bool loop)
        {
            var serializedClip = new SerializedObject(clip);
            var clipSettings = serializedClip.FindProperty("m_AnimationClipSettings");
            if (clipSettings != null)
            {
                clipSettings.FindPropertyRelative("m_LoopTime").boolValue = loop;
                serializedClip.ApplyModifiedProperties();
            }
        }

        private static void EnsureTriggerParameter(AnimatorController controller, string parameterName)
        {
            foreach (var parameter in controller.parameters)
            {
                if (parameter.name == parameterName)
                {
                    return;
                }
            }

            controller.AddParameter(parameterName, AnimatorControllerParameterType.Trigger);
        }

        private static AnimatorState EnsureState(AnimatorController controller, string stateName, Vector3 position)
        {
            var stateMachine = controller.layers[0].stateMachine;
            foreach (var childState in stateMachine.states)
            {
                if (childState.state.name == stateName)
                {
                    return childState.state;
                }
            }

            return stateMachine.AddState(stateName, position);
        }

        private static void EnsureAnyStateTriggerTransition(AnimatorController controller, AnimatorState destination, string triggerName)
        {
            var stateMachine = controller.layers[0].stateMachine;
            foreach (var transition in stateMachine.anyStateTransitions)
            {
                if (transition.destinationState == destination && HasTriggerCondition(transition, triggerName))
                {
                    return;
                }
            }

            var anyStateTransition = stateMachine.AddAnyStateTransition(destination);
            anyStateTransition.hasExitTime = false;
            anyStateTransition.duration = 0.05f;
            anyStateTransition.AddCondition(AnimatorConditionMode.If, 0f, triggerName);
        }

        private static bool HasTriggerCondition(AnimatorStateTransition transition, string triggerName)
        {
            foreach (var condition in transition.conditions)
            {
                if (condition.parameter == triggerName)
                {
                    return true;
                }
            }

            return false;
        }

        private static void EnsureReturnToIdleTransition(AnimatorState source, AnimatorState idle, float exitTime)
        {
            foreach (var transition in source.transitions)
            {
                if (transition.destinationState == idle)
                {
                    transition.hasExitTime = true;
                    transition.exitTime = exitTime;
                    transition.duration = 0.05f;
                    return;
                }
            }

            var newTransition = source.AddTransition(idle);
            newTransition.hasExitTime = true;
            newTransition.exitTime = exitTime;
            newTransition.duration = 0.05f;
        }

        private static void EnsureFolderExists(string folderPath)
        {
            var parts = folderPath.Split('/');
            var current = parts[0];
            for (var i = 1; i < parts.Length; i++)
            {
                var next = $"{current}/{parts[i]}";
                if (!AssetDatabase.IsValidFolder(next))
                {
                    AssetDatabase.CreateFolder(current, parts[i]);
                }

                current = next;
            }
        }
    }
}
