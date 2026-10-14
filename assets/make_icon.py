"""Dessine l'icône de cSPRESETS (1024 px, aplats Socle, sans ombre) puis produit icon.icns avec iconutil."""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QPainter
import socle_qt as S

app = QGuiApplication(sys.argv)
here = os.path.dirname(os.path.abspath(__file__))
img = QImage(1024, 1024, QImage.Format.Format_ARGB32)
img.fill(Qt.GlobalColor.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setPen(Qt.PenStyle.NoPen)
p.setBrush(QColor(S.c("surface-raised", "dark")))
p.drawRoundedRect(QRectF(100, 100, 824, 824), 180, 180)
# trois curseurs de réglage : deux neutres, un ambre (le preset choisi)
cols = [S.c("text-muted", "dark"), S.c("accent", "dark"), S.c("action", "dark")]
knobs = [0.62, 0.35, 0.72]
for i, (col, k) in enumerate(zip(cols, knobs)):
    x = 300 + i * 212
    p.setBrush(QColor(S.c("bg-inset", "dark")))
    p.drawRoundedRect(QRectF(x - 22, 250, 44, 524), 22, 22)
    y = 250 + k * 524
    p.setBrush(QColor(col))
    p.drawRoundedRect(QRectF(x - 70, y - 44, 140, 88), 30, 30)
p.end()
png = os.path.join(here, "icon.png")
img.save(png)
with tempfile.TemporaryDirectory() as tmp:
    iconset = os.path.join(tmp, "icon.iconset"); os.mkdir(iconset)
    for s in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            n = f"icon_{s}x{s}{'@2x' if scale == 2 else ''}.png"
            img.scaled(s * scale, s * scale, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation).save(os.path.join(iconset, n))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(here, "icon.icns")], check=True)
print("icon.icns OK")
