import os
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from logger import logger

# 폰트 경로 설정
FONT_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Korean/NotoSansKR-Regular.otf"
FONT_PATH = os.path.join("fonts", "NotoSansKR-Regular.otf")

if not os.path.exists(FONT_PATH):
    os.makedirs(os.path.dirname(FONT_PATH), exist_ok=True)
    response = requests.get(FONT_URL)
    with open(FONT_PATH, "wb") as f:
        f.write(response.content)
    logger.info("폰트 다운로드 완료: NotoSansKR-Regular.otf")


def generate_result_image(image, landmarks, score, part_scores):
    logger.debug("결과 이미지 시각화 시작")

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    width, height = image.size
    center_x = width // 2

    try:
        font_large = ImageFont.truetype(FONT_PATH, 40)
        font_small = ImageFont.truetype(FONT_PATH, 24)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        logger.warning("기본 폰트 사용 중 (내부 폰트 로드 실패)")

    draw = ImageDraw.Draw(image)

    # 1) 기준선 (노란색 수직선)
    draw.line([(center_x, 0), (center_x, height)], fill="yellow", width=2)

    # 2) 상단 점수 텍스트 박스
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    padding, box_height, box_top = 20, 160, 20
    od.rectangle(
        [padding, box_top, width - padding, box_top + box_height],
        fill=(0, 0, 0, 180)
    )
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    def draw_centered_text(text, y, font):
        draw.text((center_x + 1, y + 1), text, font=font, fill="black", anchor="mm")
        draw.text((center_x, y), text, font=font, fill="white", anchor="mm")

    draw_centered_text("당신의 비대칭은", box_top + 40, font_large)
    draw_centered_text(f"{score:.2f}%!!",    box_top + 80, font_large)
    draw_centered_text("완전 완벽해요~!", box_top + 120, font_small)

    # 3) 부위별 점수 라벨 (기존)
    label_box_size = (150, 50)
    part_indices = {
        "눈": [33, 133, 160, 159, 158, 157, 173, 362, 263, 387, 386, 385, 384, 398],
        "코": [1, 2, 98, 327, 168, 195, 5, 4, 278],
        "입": [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308],
        "귀": [234, 454],
    }
    key_map = {"눈": "eyes", "입": "mouth", "귀": "jaw", "코": "nose"}

    for part, indices in part_indices.items():
        x, y = estimate_position(landmarks, indices)
        score_text = f"{part}: {part_scores.get(key_map[part], 0):.1f}%"
        # 라벨 박스
        box_x = 30 if part in ["눈", "코"] else width - label_box_size[0] - 30
        box_y = y
        draw.rounded_rectangle(
            [box_x, box_y, box_x + label_box_size[0], box_y + label_box_size[1]],
            fill="white", radius=8
        )
        tx, ty = box_x + 75, box_y + 25  # 중앙 정렬
        draw.text((tx+1, ty+1), score_text, font=font_small, fill="gray", anchor="mm")
        draw.text((tx, ty), score_text, font=font_small, fill="black", anchor="mm")

    # 4) 특정 랜드마크 거리 표시
    highlights = {
        "입 왼쪽 끝":  61,
        "입 오른쪽 끝": 291,
        "눈 왼쪽 안쪽 끝": 133,
        "눈 오른쪽 안쪽 끝": 362,
        "귀 왼쪽 끝": 234,
        "귀 오른쪽 끝": 454,
        "코 왼쪽 끝":  98,
        "코 오른쪽 끝": 327,
    }
    colors = {
        "입": "blue", "눈": "blue",
        "귀": "cyan", "코": "red",
    }

    for name, idx in highlights.items():
        x_i, y_i = landmarks[idx]
        # 중심점 마커
        draw.ellipse([x_i-4, y_i-4, x_i+4, y_i+4], fill=colors[name.split()[0]])
        # 점선 거리선
        draw_dotted_line(draw, (x_i, y_i), (center_x, y_i),
                         color=colors[name.split()[0]], width=2, dash_length=10)
        # 거리 텍스트
        dist = abs(center_x - x_i)
        draw.text(
            ((x_i + center_x)//2, y_i - 12),
            f"{dist}px",
            font=font_small,
            fill=colors[name.split()[0]],
            anchor="mm"
        )

    # 5) 이미지 저장
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"result_{datetime.now():%Y%m%d_%H%M%S}.png")
    image.save(out_path)
    logger.info(f"결과 이미지 저장됨: {out_path}")

    return image


def estimate_position(landmarks, indices):
    pts = [landmarks[i] for i in indices if i < len(landmarks)]
    if not pts:
        return (0, 0)
    avg_x = sum(p[0] for p in pts) // len(pts)
    avg_y = sum(p[1] for p in pts) // len(pts)
    return (avg_x, avg_y)


def draw_dotted_line(draw, start, end, color="blue", width=2, dash_length=10):
    from math import hypot
    total = hypot(end[0]-start[0], end[1]-start[1])
    num = int(total // dash_length)
    if num < 1:
        return
    dx = (end[0]-start[0]) / num
    dy = (end[1]-start[1]) / num
    for i in range(0, num, 2):
        x1, y1 = start[0]+dx*i, start[1]+dy*i
        x2, y2 = start[0]+dx*(i+1), start[1]+dy*(i+1)
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
