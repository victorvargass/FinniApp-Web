from __future__ import annotations

import argparse
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio_ffmpeg


WIDTH = 1280
HEIGHT = 720
FPS = 30
DEEP_NAVY = "#062542"
MINT = "#20BDAE"
CREAM = "#F8F7F3"


def ease_out(value: float) -> float:
    return 1 - (1 - max(0.0, min(1.0, value))) ** 3


def ease_in_out(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def fit_text(draw: ImageDraw.ImageDraw, text: str, font_path: Path, max_size: int, max_width: int) -> ImageFont.FreeTypeFont:
    size = max_size
    while size > 20:
        font = load_font(font_path, size)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
            return font
        size -= 1
    return load_font(font_path, size)


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def background() -> Image.Image:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), CREAM)
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    painter = ImageDraw.Draw(glow)
    painter.ellipse((760, -260, 1450, 430), fill=(32, 189, 174, 44))
    painter.ellipse((-300, 410, 420, 1060), fill=(77, 151, 209, 30))
    return Image.alpha_composite(canvas.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(55)))


def draw_brand(canvas: Image.Image, icon: Image.Image, regular: Path, bold: Path, opacity: int = 255) -> None:
    icon_copy = icon.copy().resize((52, 52), Image.Resampling.LANCZOS)
    if opacity != 255:
        icon_copy.putalpha(opacity)
    canvas.alpha_composite(icon_copy, (66, 48))
    painter = ImageDraw.Draw(canvas)
    painter.text((130, 54), "Finni", font=load_font(bold, 29), fill=(11, 49, 91, opacity))
    finni_width = painter.textbbox((130, 54), "Finni", font=load_font(bold, 29))[2] - 130
    painter.text((130 + finni_width, 54), "App", font=load_font(bold, 29), fill=(32, 189, 174, opacity))


def draw_phone(canvas: Image.Image, screenshot: Image.Image, x: int, y: int, height: int, opacity: int = 255) -> None:
    ratio = screenshot.width / screenshot.height
    inner_height = height - 28
    inner_width = int(inner_height * ratio)
    phone_width = inner_width + 28
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x + 10, y + 16, x + phone_width + 10, y + height + 16),
        radius=48,
        fill=(6, 37, 66, min(55, opacity)),
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(20)))
    body = Image.new("RGBA", (phone_width, height), (11, 49, 91, opacity))
    body_mask = rounded_mask(body.size, 48)
    body.putalpha(Image.eval(body_mask, lambda p: p * opacity // 255))
    canvas.alpha_composite(body, (x, y))
    shot = screenshot.resize((inner_width, inner_height), Image.Resampling.LANCZOS).convert("RGBA")
    shot.putalpha(Image.eval(rounded_mask(shot.size, 37), lambda p: p * opacity // 255))
    canvas.alpha_composite(shot, (x + 14, y + 14))


def draw_kicker(draw: ImageDraw.ImageDraw, y: int, text: str, regular: Path, alpha: int) -> None:
    draw.rounded_rectangle((68, y + 9, 104, y + 13), radius=2, fill=(32, 189, 174, alpha))
    draw.text((118, y), text.upper(), font=load_font(regular, 20), fill=(49, 144, 137, alpha))


def draw_feature_symbol(draw: ImageDraw.ImageDraw, kind: str, x: int, y: int, color: str, alpha: int) -> None:
    rgba = (*ImageColor.getrgb(color), alpha)
    if kind == "movement":
        draw.line((x + 9, y + 31, x + 31, y + 9), fill=rgba, width=4)
        draw.line((x + 18, y + 9, x + 31, y + 9, x + 31, y + 22), fill=rgba, width=4, joint="curve")
    elif kind == "reminder":
        draw.ellipse((x + 8, y + 8, x + 32, y + 32), outline=rgba, width=4)
        draw.line((x + 20, y + 12, x + 20, y + 21, x + 27, y + 25), fill=rgba, width=4, joint="curve")
    else:
        draw.line((x + 8, y + 21, x + 17, y + 30, x + 33, y + 11), fill=rgba, width=4, joint="curve")


def draw_copy(
    canvas: Image.Image,
    title: list[str],
    body: list[str],
    kicker: str,
    regular: Path,
    medium: Path,
    bold: Path,
    progress: float,
    accent_last: bool = False,
) -> None:
    painter = ImageDraw.Draw(canvas)
    alpha = int(255 * ease_out(progress))
    x = 68 + int((1 - ease_out(progress)) * -32)
    draw_kicker(painter, 204, kicker, medium, alpha)
    y = 250
    for index, line in enumerate(title):
        color = (32, 189, 174, alpha) if accent_last and index == len(title) - 1 else (11, 49, 91, alpha)
        font = fit_text(painter, line, bold, 57, 620)
        painter.text((x, y), line, font=font, fill=color)
        y += 67
    y += 22
    for line in body:
        painter.text((x, y), line, font=load_font(regular, 25), fill=(96, 117, 138, alpha))
        y += 38


def scene_intro(local_t: float, duration: float, icon: Image.Image, regular: Path, medium: Path, bold: Path) -> Image.Image:
    canvas = background()
    painter = ImageDraw.Draw(canvas)
    enter = ease_out(local_t / 0.8)
    leave = 1 - ease_in_out((local_t - duration + 0.55) / 0.55)
    alpha = int(255 * min(enter, leave))
    scale = 0.92 + 0.08 * enter
    icon_size = int(104 * scale)
    logo = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS).convert("RGBA")
    logo.putalpha(alpha)
    canvas.alpha_composite(logo, ((WIDTH - icon_size) // 2, 125))
    title_font = load_font(bold, 76)
    title = "FinniApp"
    title_box = painter.textbbox((0, 0), title, font=title_font)
    painter.text(((WIDTH - (title_box[2] - title_box[0])) // 2, 254), title, font=title_font, fill=(11, 49, 91, alpha))
    painter.text((408, 360), "Tu dinero,", font=load_font(medium, 44), fill=(11, 49, 91, alpha))
    painter.text((646, 360), "más claro.", font=load_font(bold, 44), fill=(32, 189, 174, alpha))
    painter.rounded_rectangle((450, 447, 830, 499), radius=26, fill=(221, 245, 241, alpha))
    painter.text((489, 458), "Finanzas sin complicaciones", font=load_font(medium, 22), fill=(11, 80, 94, alpha))
    return canvas


def scene_phone(
    local_t: float,
    duration: float,
    screenshot: Image.Image,
    icon: Image.Image,
    regular: Path,
    medium: Path,
    bold: Path,
    title: list[str],
    body: list[str],
    kicker: str,
) -> Image.Image:
    canvas = background()
    enter = ease_out(local_t / 0.65)
    leave = 1 - ease_in_out((local_t - duration + 0.48) / 0.48)
    visibility = max(0.0, min(1.0, min(enter, leave)))
    draw_brand(canvas, icon, regular, bold, int(255 * visibility))
    draw_copy(canvas, title, body, kicker, regular, medium, bold, visibility)
    phone_x = 865 + int((1 - enter) * 120)
    phone_y = 48 + int(math.sin(min(1, local_t / duration) * math.pi) * -8)
    draw_phone(canvas, screenshot, phone_x, phone_y, 650, int(255 * visibility))
    return canvas


def scene_features(local_t: float, duration: float, icon: Image.Image, regular: Path, medium: Path, bold: Path) -> Image.Image:
    canvas = background()
    painter = ImageDraw.Draw(canvas)
    enter = ease_out(local_t / 0.7)
    leave = 1 - ease_in_out((local_t - duration + 0.5) / 0.5)
    visibility = max(0.0, min(1.0, min(enter, leave)))
    alpha = int(255 * visibility)
    draw_brand(canvas, icon, regular, bold, alpha)
    draw_kicker(painter, 144, "MENOS TRABAJO MANUAL", medium, alpha)
    painter.text((68, 188), "FinniApp te ayuda", font=load_font(bold, 54), fill=(11, 49, 91, alpha))
    painter.text((68, 250), "a mantenerte al día", font=load_font(bold, 54), fill=(32, 189, 174, alpha))
    cards = [
        ("movement", "Detecta movimientos", "Desde notificaciones financieras", MINT, "#DDF5F1"),
        ("reminder", "Recuerda lo importante", "Recurrencias, pagos y vencimientos", "#E2A62B", "#FFF1D5"),
        ("control", "Siempre bajo tu control", "Revisa antes de registrar", "#3F8FD1", "#E2F1FB"),
    ]
    for index, (symbol, title, subtitle, color, soft_color) in enumerate(cards):
        stagger = ease_out((local_t - 0.25 - index * 0.16) / 0.55) * leave
        card_alpha = int(255 * max(0.0, stagger))
        x = 68 + index * 394
        y = 374 + int((1 - max(0.0, stagger)) * 28)
        painter.rounded_rectangle((x, y, x + 362, y + 190), radius=26, fill=(255, 255, 255, card_alpha), outline=(216, 225, 231, card_alpha), width=2)
        painter.rounded_rectangle((x + 24, y + 22, x + 78, y + 76), radius=16, fill=(*ImageColor.getrgb(soft_color), card_alpha))
        draw_feature_symbol(painter, symbol, x + 31, y + 29, color, card_alpha)
        painter.text((x + 24, y + 96), title, font=load_font(bold, 24), fill=(11, 49, 91, card_alpha))
        painter.text((x + 24, y + 135), subtitle, font=load_font(regular, 18), fill=(96, 117, 138, card_alpha))
    painter.text((68, 624), "Procesado localmente en Android · Tú eliges qué aplicaciones pueden sugerir movimientos", font=load_font(regular, 19), fill=(96, 117, 138, alpha))
    return canvas


def scene_outro(local_t: float, duration: float, icon: Image.Image, regular: Path, medium: Path, bold: Path) -> Image.Image:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), DEEP_NAVY)
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((770, -250, 1480, 460), fill=(32, 189, 174, 52))
    glow_draw.ellipse((-350, 450, 390, 1150), fill=(63, 143, 209, 35))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(55)))
    painter = ImageDraw.Draw(canvas)
    enter = ease_out(local_t / 0.75)
    alpha = int(255 * enter)
    logo = icon.resize((92, 92), Image.Resampling.LANCZOS).convert("RGBA")
    logo.putalpha(alpha)
    canvas.alpha_composite(logo, (594, 96))
    painter.text((WIDTH // 2, 227), "Tu panorama financiero,", font=load_font(medium, 41), anchor="ma", fill=(226, 240, 247, alpha))
    painter.text((WIDTH // 2, 286), "claro y bajo tu control.", font=load_font(bold, 48), anchor="ma", fill=(255, 255, 255, alpha))
    painter.rounded_rectangle((420, 386, 860, 452), radius=33, fill=(32, 189, 174, alpha))
    painter.text((640, 417), "Conoce FinniApp", font=load_font(bold, 25), anchor="mm", fill=(255, 255, 255, alpha))
    painter.text((640, 522), "Funciona sin internet · Respaldo opcional en Google Drive", font=load_font(regular, 21), anchor="ma", fill=(171, 205, 220, alpha))
    painter.text((640, 576), "Actualmente en prueba cerrada para Android", font=load_font(medium, 20), anchor="ma", fill=(92, 225, 210, alpha))
    return canvas


def make_video(app_repo: Path, output: Path, poster: Path) -> None:
    global ImageColor
    from PIL import ImageColor

    font_root = app_repo / "node_modules" / "@expo-google-fonts" / "quicksand"
    regular = font_root / "400Regular" / "Quicksand_400Regular.ttf"
    medium = font_root / "500Medium" / "Quicksand_500Medium.ttf"
    bold = font_root / "700Bold" / "Quicksand_700Bold.ttf"
    icon = Image.open(app_repo / "assets" / "images" / "app-icon-v3.png").convert("RGBA")
    screenshots = [
        Image.open(app_repo / "store-assets" / "play" / name).convert("RGB")
        for name in [
            "phone-01-overview-1080x1920.png",
            "phone-02-movements-1080x1920.png",
            "phone-03-savings-1080x1920.png",
            "phone-04-debts-1080x1920.png",
        ]
    ]
    scenes = [
        (3.2, lambda t, d: scene_intro(t, d, icon, regular, medium, bold)),
        (4.0, lambda t, d: scene_phone(t, d, screenshots[0], icon, regular, medium, bold, ["Todo tu dinero", "en un solo lugar"], ["Cuentas, tarjetas y movimientos", "con información fácil de entender."], "PANORAMA COMPLETO")),
        (3.8, lambda t, d: scene_phone(t, d, screenshots[1], icon, regular, medium, bold, ["Registra y entiende", "cada movimiento"], ["Categorías, fechas y medios de pago", "organizados en un historial claro."], "INGRESOS Y GASTOS")),
        (3.8, lambda t, d: scene_phone(t, d, screenshots[2], icon, regular, medium, bold, ["Convierte tus planes", "en metas visibles"], ["Sigue cuánto llevas ahorrado", "y cuánto te falta para llegar."], "METAS DE AHORRO")),
        (3.8, lambda t, d: scene_phone(t, d, screenshots[3], icon, regular, medium, bold, ["Mantén deudas", "y pagos al día"], ["Controla cuotas, vencimientos", "y cobros pendientes."], "DEUDAS Y PAGOS")),
        (4.2, lambda t, d: scene_features(t, d, icon, regular, medium, bold)),
        (4.2, lambda t, d: scene_outro(t, d, icon, regular, medium, bold)),
    ]
    total_duration = sum(item[0] for item in scenes)
    output.parent.mkdir(parents=True, exist_ok=True)
    poster.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    frame_count = int(total_duration * FPS)
    cumulative = 0.0
    poster_frame = None
    for frame_index in range(frame_count):
        current = frame_index / FPS
        cumulative = 0.0
        frame = None
        for duration, renderer in scenes:
            if current < cumulative + duration:
                frame = renderer(current - cumulative, duration)
                break
            cumulative += duration
        if frame is None:
            frame = scenes[-1][1](scenes[-1][0], scenes[-1][0])
        rgb = frame.convert("RGB")
        if poster_frame is None and current >= 4.8:
            poster_frame = rgb.copy()
        process.stdin.write(rgb.tobytes())
    process.stdin.close()
    exit_code = process.wait()
    if exit_code != 0:
        raise SystemExit(exit_code)
    (poster_frame or scene_intro(2, 3.2, icon, regular, medium, bold).convert("RGB")).save(poster, quality=90, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the FinniApp website promotional video.")
    parser.add_argument("--app-repo", type=Path, default=Path(__file__).resolve().parents[2] / "FinniApp")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "finniapp-resumen.mp4")
    parser.add_argument("--poster", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "finniapp-resumen-poster.jpg")
    args = parser.parse_args()
    make_video(args.app_repo.resolve(), args.output.resolve(), args.poster.resolve())


if __name__ == "__main__":
    main()
