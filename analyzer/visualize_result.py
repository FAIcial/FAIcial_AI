import os
import requests
from datetime import datetime
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
    avg_x = sum(p[0] for p in pts) // len(pts)
    avg_y = sum(p[1] for p in pts) // len(pts)
    return (avg_x, avg_y)


def draw_dotted_line(draw, start, end, color="blue", width=2, dash_length=10):
    from math import hypot
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


def crop_to_face_center_3_4(image: Image.Image, landmarks):
    """
    얼굴 랜드마크 기준으로 이미지를 3:4 비율로 자르고,
    랜드마크 좌표를 보정합니다.
    """
    orig_w, orig_h = image.size
    xs = [p[0] for p in landmarks]
    ys = [p[1] for p in landmarks]
    face_cx = sum(xs) / len(xs)
    face_cy = sum(ys) / len(ys)

    target_ratio = 3 / 4
    if orig_w / orig_h >= target_ratio:
        crop_h = orig_h
        crop_w = int(crop_h * target_ratio)
    else:
        crop_w = orig_w
        crop_h = int(crop_w / target_ratio)

    left = int(face_cx - crop_w / 2)
    top  = int(face_cy - crop_h / 2)
    left = max(0, min(left, orig_w - crop_w))
    top  = max(0, min(top, orig_h - crop_h))
    box = (left, top, left + crop_w, top + crop_h)

    cropped = image.crop(box)
    new_landmarks = [(x - left, y - top) for (x, y) in landmarks]
    return cropped, new_landmarks


def generate_result_image(image: Image.Image, landmarks, score, part_scores):
    logger.debug("결과 이미지 시각화 시작")

    # — 1) 얼굴 중심 기준 4:5 비율 크롭 —
    image, landmarks = crop_to_face_center_3_4(image, landmarks)

    # — 2) RGBA 변환 —
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    width, height = image.size

    # — 3) 이미지 중앙 X (제목·라벨용) & 얼굴 중심 X (거리선용) —
    image_center_x = width // 2
    midline_idxs = [1, 2, 168, 9, 94, 152]
    face_center_x, _ = estimate_position(landmarks, midline_idxs)

    # — 4) 고정 폰트 크기 —
    font_large = ImageFont.truetype(FONT_PATH, 40)
    font_small = ImageFont.truetype(FONT_PATH, 24)

    draw = ImageDraw.Draw(image)

    # — 얼굴 기준선 (face_center_x) —
    draw.line([(face_center_x, 0), (face_center_x, height)],
              fill="yellow", width=2)

    # — 상단 점수 박스 & 텍스트 (image_center_x) —
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    pad, box_h = 20, 160
    od.rectangle([pad, pad, width - pad, pad + box_h], fill=(0, 0, 0, 180))
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    def draw_centered_text(text, y, font):
        draw.text((image_center_x + 1, y + 1), text,
                  font=font, fill="black", anchor="mm")
        draw.text((image_center_x, y),
                  text, font=font, fill="white", anchor="mm")

    draw_centered_text("당신의 비대칭은", pad + 40, font_large)
    draw_centered_text(f"{score:.2f}%!!",    pad + 80, font_large)
    draw_centered_text("완전 완벽해요~!",    pad + 120, font_small)

    # — 거리 시각화 (face_center_x 기준) —
    highlights = {
        "입 왼쪽 끝":    (61,    "blue"),
        "입 오른쪽 끝":  (291,   "blue"),
        "눈 왼쪽 안쪽 끝":(133,   "blue"),
        "눈 오른쪽 안쪽 끝":(362, "blue"),
        "귀 왼쪽 끝":    (234,   "cyan"),
        "귀 오른쪽 끝":  (454,   "cyan"),
        "코 왼쪽 끝":    (98,    "red"),
        "코 오른쪽 끝":  (327,   "red"),
    }
    for name, (idx, color) in highlights.items():
        x_i, y_i = landmarks[idx]
        draw_dotted_line(draw, (x_i, y_i), (face_center_x, y_i),
                         color=color, width=2, dash_length=10)
        dist = abs(face_center_x - x_i)
        draw.text(
            ((x_i + face_center_x) // 2, y_i - 12),
            f"{dist}px",
            font=font_small,
            fill=color,
            anchor="mm"
        )

    # — 부위별 라벨 박스 (비율 기반 위치) —
    label_w, label_h = 150, 50
    static_pos = {
        "눈": (int(width * 0.05), int(height * 0.05)),
        "코": (int(width * 0.50 - label_w / 2), int(height * 0.05)),
        "입": (int(width * 0.05), int(height * 0.95 - label_h)),
        "귀": (int(width * 0.95 - label_w), int(height * 0.95 - label_h)),
    }
    key_map = {"눈": "eyes", "코": "nose", "입": "mouth", "귀": "jaw"}

    for part, (bx, by) in static_pos.items():
        score_text = f"{part}: {part_scores.get(key_map[part], 0):.1f}%"
        draw.rounded_rectangle(
            [bx, by, bx + label_w, by + label_h],
            fill="white", radius=8
        )
        draw.text(
            (bx + label_w // 2, by + label_h // 2),
            score_text,
            font=font_small,
            fill="black",
            anchor="mm"
        )

    # — 이미지 저장 —
    out_dir = "outputs"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"result_{datetime.now():%Y%m%d_%H%M%S}.png")
    image.save(out_path)
    logger.info(f"결과 이미지 저장됨: {out_path}")

    return image
