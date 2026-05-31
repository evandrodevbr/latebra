"""Fingerprint randomization for Canvas, WebGL, AudioContext, and screen."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from latebra.constants import (
    AUDIO_NOISE_MAX,
    AUDIO_NOISE_MIN,
    CANVAS_NOISE_MAX,
    CANVAS_NOISE_MIN,
    DEVICE_MEMORY_OPTIONS,
    DEVICE_SCALE_FACTORS,
    HARDWARE_CONCURRENCY_OPTIONS,
    LANGUAGES,
    PLATFORMS,
    TIMEZONES,
    USER_AGENTS,
    VIEWPORTS,
)


@dataclass
class BrowserFingerprint:
    user_agent: str = ""
    viewport_width: int = 1920
    viewport_height: int = 1080
    device_scale_factor: float = 1.0
    platform: str = "Win32"
    vendor: str = "Google Inc."
    renderer: str = "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)"
    canvas_noise: float = 0.0
    audio_noise: float = 0.0
    webgl_vendor: str = "Google Inc. (Intel)"
    webgl_renderer: str = "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)"
    languages: list[str] = field(default_factory=lambda: ["en-US", "en"])
    hardware_concurrency: int = 8
    device_memory: int = 8
    timezone: str = "America/New_York"


class FingerprintGenerator:
    """Generates randomized browser fingerprints for anti-detection."""

    USER_AGENTS = USER_AGENTS
    VIEWPORTS = VIEWPORTS
    PLATFORMS = PLATFORMS
    TIMEZONES = TIMEZONES
    LANGUAGES = LANGUAGES

    def generate(self) -> BrowserFingerprint:
        fp = BrowserFingerprint()
        fp.user_agent = random.choice(self.USER_AGENTS)
        fp.viewport_width, fp.viewport_height = random.choice(self.VIEWPORTS)
        fp.device_scale_factor = random.choice(DEVICE_SCALE_FACTORS)
        fp.platform = random.choice(self.PLATFORMS)

        # Vendor / Renderer
        vendors = [
            ("Google Inc.", "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
            ("Mozilla", "Skia"),
        ]
        fp.vendor, fp.renderer = random.choice(vendors)

        # Canvas noise
        fp.canvas_noise = random.uniform(CANVAS_NOISE_MIN, CANVAS_NOISE_MAX)

        # Audio noise
        fp.audio_noise = random.uniform(AUDIO_NOISE_MIN, AUDIO_NOISE_MAX)

        # WebGL
        gl_options = [
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0)"),
        ]
        fp.webgl_vendor, fp.webgl_renderer = random.choice(gl_options)

        fp.languages = random.choice(self.LANGUAGES)
        fp.hardware_concurrency = random.choice(HARDWARE_CONCURRENCY_OPTIONS)
        fp.device_memory = random.choice(DEVICE_MEMORY_OPTIONS)
        fp.timezone = random.choice(self.TIMEZONES)

        return fp

    def generate_stealth_init_script(self) -> str:
        """Generate JavaScript for browser stealth initialization."""
        fp = self.generate()
        return f"""
        // Canvas fingerprint protection
        const _orig_getImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {{
            const imageData = _orig_getImageData.call(this, x, y, w, h);
            for (let i = 0; i < imageData.data.length; i += 4) {{
                imageData.data[i] = imageData.data[i] ^ 1;
            }}
            return imageData;
        }};

        // WebGL vendor/renderer spoof
        const _orig_getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {{
            if (param === 37445) return "{fp.webgl_vendor}";
            if (param === 37446) return "{fp.webgl_renderer}";
            return _orig_getParameter.call(this, param);
        }};

        // Navigator overrides
        Object.defineProperty(navigator, 'platform', {{ get: () => '{fp.platform}' }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fp.hardware_concurrency} }});
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {fp.device_memory} }});
        Object.defineProperty(navigator, 'languages', {{ get: () => {json.dumps(fp.languages, default=str)} }});
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
        window.chrome = window.chrome || {{ runtime: {{ }} }};
        """
