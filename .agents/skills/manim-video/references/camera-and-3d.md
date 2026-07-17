# Camera and 3D Reference

Camera motion should guide attention or reveal scale. It should not be added only to make a scene look busy.

## MovingCameraScene

```python
class ZoomExample(MovingCameraScene):
    def construct(self):
        diagram = VGroup(Circle(), Dot()).arrange(RIGHT)
        self.add(diagram)
        self.play(self.camera.frame.animate.scale(0.55).move_to(diagram[1]), run_time=1.5)
        self.wait(1.0)
        self.play(Restore(self.camera.frame), run_time=1.2)
```

Use `save_state()` before a temporary zoom and `Restore` to return. Favor slow pans over abrupt camera jumps. Frame the safe content area before adding labels.

## ThreeDScene

Use 3D only when depth, rotation, or a surface is part of the explanation:

```python
class SurfaceScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
        axes = ThreeDAxes()
        surface = Surface(
            lambda u, v: axes.c2p(u, v, u**2 - v**2),
            u_range=[-2, 2], v_range=[-2, 2], resolution=(24, 24),
        )
        self.play(Create(axes), Create(surface), run_time=2.0)
        self.wait(1.5)
```

Keep important text facing the camera. Do not use 3D for a concept that is clearer in 2D; perspective and occlusion add cognitive load.

## Other specialized cameras

- `ZoomedScene`: inset magnification of a local detail.
- `LinearTransformationScene`: linear algebra transformations with a coordinate grid.
- `ThreeDScene`: spatial surfaces, volumes, and rotations.

Before shipping, check that camera movement never pushes text or equations outside the frame. Render a low-quality draft and inspect the entire motion, not just the first frame.
