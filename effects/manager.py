from effects.jutsus.shadow_clone import ShadowCloneEffect
from effects.jutsus.rasengan import RasenganEffect
from effects.jutsus.chidori import ChidoriEffect
from effects.jutsus.fireball import FireballEffect

class EffectManager:
    def __init__(self):
        # Dictionary holding instantiated effect classes
        self.effects = {
            "shadow_clone": ShadowCloneEffect(),
            "rasengan": RasenganEffect(),
            "chidori": ChidoriEffect(),
            "fireball": FireballEffect()
        }
        self.active_effect = None

    def trigger(self, jutsu_name, frame, pose_lms, mask):
        """Triggers the specified jutsu effect if one is not already active."""
        if not self.active_effect and jutsu_name in self.effects:
            self.active_effect = self.effects[jutsu_name]
            self.active_effect.trigger(frame, pose_lms, mask)

    def update(self):
        """Updates the active effect state (time bounds, animation frames)."""
        if self.active_effect:
            is_alive = self.active_effect.update()
            if not is_alive:
                self.active_effect = None

    def render(self, frame):
        """Renders the active effect onto the frame."""
        if self.active_effect:
            frame = self.active_effect.render(frame)
        return frame
