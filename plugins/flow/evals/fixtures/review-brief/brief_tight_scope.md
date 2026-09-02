# Design brief — Delete icon touch target

**Problem:** The delete icon in the settings row is 24×24px, below the 44×44pt minimum touch target, causing mis-taps on mobile.
**Whose moment:** Any mobile user removing a saved item from Settings > Saved Items.
**Constraints:** The icon glyph itself must stay visually 16px per the design-language spacing scale; only the hit area grows.
**Intended scope:** Expand the tappable hit area to 44×44pt via padding; keep the glyph unchanged.
**Deliberately excluded:** Auditing every other icon's touch target in the app — tracked separately.
**Where this pushes past the literal request:** Nowhere; this is a targeted accessibility fix and stays that size deliberately.
