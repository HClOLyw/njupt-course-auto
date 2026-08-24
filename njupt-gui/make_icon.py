# -*- coding: utf-8 -*-
"""生成应用图标 app_icon.png 与 app_icon.ico"""
from PIL import Image, ImageDraw
import os

size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 圆角背景（深蓝 + 上部高光）
d.rounded_rectangle([8, 8, size - 8, size - 8], radius=52, fill=(43, 78, 255, 255))
d.rounded_rectangle([8, 8, size - 8, size // 2], radius=52, fill=(76, 108, 255, 255))

# 白色播放三角形
tri = [(96, 84), (96, 172), (178, 128)]
d.polygon(tri, fill=(255, 255, 255, 255))

# 底部进度条
d.rounded_rectangle([56, 196, 200, 212], radius=8, fill=(255, 255, 255, 110))
d.rounded_rectangle([56, 196, 150, 212], radius=8, fill=(255, 255, 255, 255))

here = os.path.dirname(os.path.abspath(__file__))
img.save(os.path.join(here, "app_icon.png"))
# 生成多尺寸 ICO
img.save(os.path.join(here, "app_icon.ico"), sizes=[(16, 16), (24, 24), (32, 32),
                                                    (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon saved:", os.path.join(here, "app_icon.ico"))
