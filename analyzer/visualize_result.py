import os
import requests
from datetime import datetime
from math import hypot
from PIL import Image, ImageDraw, ImageFont
from logger import logger

# 폰트 경로 설정 (고정 크기)
FONT_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Korean/NotoSansKR-Regular.otf"
FONT_PATH = os.path.join("fonts", "NotoSansKR-Regular.otf")
if not os.path.exists(FONT_PATH):
    os.makedirs(os.path.dirname(FONT_PATH), exist_ok=True)
    resp = requests.get(FONT_URL)
    with open(FONT_PATH, "wb") as f:
        f.write(resp.content)
    logger.info("폰트 다운로드 완료: NotoSansKR-Regular.otf")


def estimate_position(landmarks, indices):
    pts = [landmarks[i] for i in indices if i < len(landmarks)]
    if not pts:
        return (0, 0)
    avg_x = sum(x for x, y in pts) // len(pts)
    avg_y = sum(y for x, y in pts) // len(pts)
    return (avg_x, avg_y)


def draw_dotted_line(draw, start, end, color="blue", width=2, dash_length=10):
    total = hypot(end[0] - start[0], end[1] - start[1])
    num = int(total // dash_length)
    if num < 1:
        return
    dx = (end[0] - start[0]) / num
    dy = (end[1] - start[1]) / num
    for i in range(0, num, 2):
        x1 = start[0] + dx * i
        y1 = start[1] + dy * i
        x2 = start[0] + dx * (i + 1)
        y2 = start[1] + dy * (i + 1)
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)


def crop_to_face_center_with_zoom(image: Image.Image, landmarks):
    """
    얼굴 귀끝(234,454)과 머리(10), 턱(152)을 기준으로
    얼굴 중심을 4:5 비율 박스 중앙에 맞춰 확대 후 크롭합니다.
    """
    orig_w, orig_h = image.size

    # 얼굴 가로 중심
    lx, _ = landmarks[234]
    rx, _ = landmarks[454]
    face_cx = (lx + rx) / 2

    # 얼굴 세로 중심
    _, ty = landmarks[10]
    _, by = landmarks[152]
    face_cy = (ty + by) / 2

    # 4:5 박스 크기 결정
    ratio = 4 / 5
    if orig_w / orig_h >= ratio:
        crop_h = orig_h
        crop_w = int(crop_h * ratio)
    else:
        crop_w = orig_w
        crop_h = int(crop_w / ratio)

    # 확대율 계산
    needed = [
        (crop_w/2) / face_cx,
        (crop_w/2) / (orig_w - face_cx),
        (crop_h/2) / face_cy,
        (crop_h/2) / (orig_h - face_cy),
    ]
    scale = max(1.0, *needed)

    # 이미지 & 랜드마크 확대
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    image = image.resize((new_w, new_h), Image.LANCZOS)
    landmarks = [(x * scale, y * scale) for x, y in landmarks]

    # 크롭 박스 계산 및 적용
    left = int((landmarks[234][0] + landmarks[454][0]) / 2 - crop_w / 2)
    top = int(((landmarks[10][1] + landmarks[152][1]) / 2) - crop_h / 2)
    left = max(0, min(left, new_w - crop_w))
    top = max(0, min(top, new_h - crop_h))
    cropped = image.crop((left, top, left + crop_w, top + crop_h))

    # 보정된 랜드마크
    new_landmarks = [(x - left, y - top) for x, y in landmarks]
    return cropped, new_landmarks


def generate_result_image(image: Image.Image, landmarks, score, part_scores):
    logger.debug("결과 이미지 시각화 시작")

    # 1) 얼굴 확대 & 4:5 비율 크롭
    image, landmarks = crop_to_face_center_with_zoom(image, landmarks)

    # 2) RGBA 모드로 변환
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    width, height = image.size

    # 3) 가로 중앙 X (텍스트·라벨용)
    image_center_x = width // 2

    # 4) 얼굴 중심 X (기준선·거리선용)
    mid_idxs = [1, 2, 168, 9, 94, 152]
    face_center_x, _ = estimate_position(landmarks, mid_idxs)

    draw = ImageDraw.Draw(image)
    font_large = ImageFont.truetype(FONT_PATH, 40)
    font_small = ImageFont.truetype(FONT_PATH, 24)

    # 5) 얼굴 기준선
    draw.line([(face_center_x, 0), (face_center_x, height)], fill="yellow", width=2)

    # 6) 상단 점수 박스 & 텍스트
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    pad, box_h = 20, 160
    od.rectangle([pad, pad, width - pad, pad + box_h], fill=(0, 0, 0, 180))
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    def draw_centered_text(text, y, font):
        draw.text((image_center_x + 1, y + 1), text, font=font, fill="black", anchor="mm")
        draw.text((image_center_x,     y),     text, font=font, fill="white", anchor="mm")

    draw_centered_text("당신의 비대칭은", pad + 40, font_large)
    draw_centered_text(f"{score:.2f}%!!",    pad + 80, font_large)
    draw_centered_text("완전 완벽해요~!",    pad + 120, font_small)

    # 7) 거리 시각화
    highlights = {
        "입 왼쪽 끝":    (61,  "blue"),
        "입 오른쪽 끝":  (291, "blue"),
        "눈 왼쪽 안쪽 끝":(133,"blue"),
        "눈 오른쪽 안쪽 끝":(362,"blue"),
        "귀 왼쪽 끝":    (234, "cyan"),
        "귀 오른쪽 끝":  (454, "cyan"),
        "코 왼쪽 끝":    (98,  "red"),
        "코 오른쪽 끝":  (327, "red"),
    }
    for name, (idx, color) in highlights.items():
        x_i, y_i = landmarks[idx]
        draw_dotted_line(draw, (x_i, y_i), (face_center_x, y_i), color=color, width=2, dash_length=10)
        dist = abs(face_center_x - x_i)
        draw.text(
            ((x_i + face_center_x) // 2, y_i - 12),
            f"{int(dist)}px",
            font=font_small,
            fill=color,
            anchor="mm"
        )

    # 8) 부위별 라벨 (고정 위치)
    label_w, label_h = 150, 50
    static_pos = {
        "눈": (int(width * 0.05),            int(height * 0.5)),
        "코": (int(width * 0.8),             int(height * 0.5)),
        "입": (int(width * 0.05),            int(height * 0.95 - label_h)),
        "귀": (int(width * 0.95 - label_w),  int(height * 0.95 - label_h)),
    }
    key_map = {"눈": "eyes", "코": "nose", "입": "mouth", "귀": "jaw"}
    for part, (bx, by) in static_pos.items():
        txt = f"{part}: {part_scores.get(key_map[part], 0):.1f}%"
        draw.rounded_rectangle([bx, by, bx + label_w, by + label_h], fill="white", radius=8)
        draw.text((bx + label_w//2, by + label_h//2), txt, font=font_small, fill="black", anchor="mm")

    # 9) 이미지 저장
    out_dir = "outputs"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"result_{datetime.now():%Y%m%d_%H%M%S}.png")
    image.save(path)
    logger.info(f"결과 이미지 저장됨: {path}")

    return image
