**Feasibility** — this is an HTML proxy of an ios surface; type rendering, motion and system chrome will differ.

- Card enter transition — native-standard — SwiftUI `.transition(.move(edge:))`
- Shared-element morph between list and detail — expensive — needs a custom UIViewRepresentable driving a CADisplayLink
- Blur-behind-scroll header — native-custom — UIVisualEffectView with a custom mask layer
