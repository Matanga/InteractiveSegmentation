# textured_plane_camera_pan.py – Python 3.13 + ModernGL 5.12
import struct
from pathlib import Path
from math import radians

import numpy as np
import moderngl_window as mglw
from PIL import Image


# ────────────────────────────────────────────────────────────────────
#  Matrix helpers
# ────────────────────────────────────────────────────────────────────
def perspective(fov_deg: float, aspect: float, near=0.1, far=100.0) -> np.ndarray:
    f = 1.0 / np.tan(radians(fov_deg) / 2.0)
    a = (far + near) / (near - far)
    b = 2 * far * near / (near - far)
    return np.array(
        [
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, a, b],
            [0, 0, -1, 0],
        ],
        dtype="f4",
    )


def look_at(eye, target, up) -> np.ndarray:
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)

    m = np.identity(4, dtype="f4")
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


# ────────────────────────────────────────────────────────────────────
#  WindowConfig
# ────────────────────────────────────────────────────────────────────
class TexturedPlaneApp(mglw.WindowConfig):
    window_size = (800, 600)
    title = "ModernGL – Textured Plane (orbit + pan camera)"
    aspect_ratio = None  # allow free resize

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 1) texture ----------------------------------------------------
        tex_path = Path(__file__).parent.parent / "resources" / "Default" / "Wall00.png"
        img = Image.open(tex_path).convert("RGBA")
        self.texture = self.ctx.texture(img.size, 4, img.tobytes())
        self.texture.build_mipmaps()
        self.texture.use(0)

        # 2) shader program --------------------------------------------
        self.prog = self.ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
        self.prog["Texture"] = 0

        # 3) quad geometry ---------------------------------------------
        verts = struct.pack(
            "20f",
            -1, -1, 0, 0, 0,
             1, -1, 0, 1, 0,
             1,  1, 0, 1, 1,
            -1,  1, 0, 0, 1,
        )
        idx = struct.pack("6I", 0, 1, 2, 2, 3, 0)
        vbo, ibo = self.ctx.buffer(verts), self.ctx.buffer(idx)
        self.vao = self.ctx.vertex_array(self.prog, [(vbo, "3f 2f", "in_pos", "in_uv")], ibo)

        # 4) camera state ----------------------------------------------
        self.target = np.zeros(3, dtype="f4")  # what we look at
        self.dist = 3.0
        self.yaw = 0.0
        self.pitch = 0.0
        self._update_mvp()

    # ── mouse interaction ────────────────────────────────────────────
    def mouse_drag_event(self, x, y, dx, dy, buttons):
        if buttons & 1:                       # LMB → orbit
            self.yaw   += dx * 0.006
            self.pitch += dy * 0.006
            self.pitch = np.clip(self.pitch, -1.45, 1.45)
        elif buttons & 2:                     # RMB → pan
            right = np.array([np.sin(self.yaw - np.pi/2), 0, np.cos(self.yaw - np.pi/2)], dtype="f4")
            up    = np.array([0, 1, 0], dtype="f4")
            pan_speed = self.dist * 0.002
            self.target += (-dx * pan_speed) * right + (dy * pan_speed) * up
        self._update_mvp()

    def mouse_scroll_event(self, _xo, yo):
        self.dist *= 0.9 ** yo
        self.dist = np.clip(self.dist, 1.2, 50)
        self._update_mvp()

    def resize(self, width, height):
        super().resize(width, height)
        self._update_mvp()

    # ── drawing ──────────────────────────────────────────────────────
    def on_render(self, *_):
        self.ctx.clear(0.15, 0.15, 0.15)
        self.vao.render()

    # ── internal ------------------------------------------------------
    def _update_mvp(self):
        eye = self.target + self.dist * np.array([
            np.cos(self.pitch) * np.sin(self.yaw),
            np.sin(self.pitch),
            np.cos(self.pitch) * np.cos(self.yaw),
        ], dtype="f4")
        view = look_at(eye, self.target, np.array([0, 1, 0], dtype="f4"))
        proj = perspective(60.0, self.wnd.aspect_ratio)
        self.prog["mvp"].write((proj @ view).astype("f4").tobytes())


# ── GLSL ────────────────────────────────────────────────────────────
VERT = """
#version 330
uniform mat4 mvp;
in  vec3 in_pos;
in  vec2 in_uv;
out vec2 v_uv;
void main() {
    gl_Position = mvp * vec4(in_pos, 1.0);
    v_uv = in_uv;
}
"""
FRAG = """
#version 330
uniform sampler2D Texture;
in  vec2 v_uv;
out vec4 f_color;
void main() {
    f_color = texture(Texture, v_uv);
}
"""

# ── run ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mglw.run_window_config(TexturedPlaneApp)
