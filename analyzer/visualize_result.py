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

    try:
        font_large = ImageFont.truetype(FONT_PATH, 40)
        font_small = ImageFont.truetype(FONT_PATH, 24)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        logger.warning("기본 폰트 사용 중 (내부 폰트 로드 실패)")

    center_x = width // 2
    text1 = "당신의 비대칭은"
    text2 = f"{score:.2f}%!!"
    text3 = "완전 완벽해요~!"

    # 상단 박스
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    padding = 20
    box_height = 160
    box_top = 20
    overlay_draw.rectangle([padding, box_top, width - padding, box_top + box_height], fill=(0, 0, 0, 180))
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    # 상단 텍스트 (정확한 상하좌우 가운데 정렬)
    def draw_centered_text(text, y, font):
        # 그림자
        draw.text((center_x + 1, y + 1), text, font=font, fill="black", anchor="mm")
        # 본문
        draw.text((center_x, y), text, font=font, fill="white", anchor="mm")

    draw_centered_text(text1, box_top + 40, font_large)
    draw_centered_text(text2, box_top + 80, font_large)
    draw_centered_text(text3, box_top + 120, font_small)

    # 부위별 라벨 박스
    label_box_size = (150, 50)
    part_positions = {
        "눈": estimate_position(landmarks, range(33, 133)),
        "코": estimate_position(landmarks, range(168, 172)),
        "입": estimate_position(landmarks, range(78, 88)),
        "귀": estimate_position(landmarks, [234, 454]),
    }

    key_map = {
        "눈": "eyes",
        "입": "mouth",
        "귀": "jaw",
        "코": "nose",
    }

    for part, (x, y) in part_positions.items():
        key = key_map.get(part, None)
        part_value = part_scores.get(key, None)
        score_text = f"{part}: {part_value:.1f}%" if part_value is not None else f"{part}: -"

        if part in ["눈", "코"]:
            box_x = 30
        else:
            box_x = width - label_box_size[0] - 30
        box_y = y

        # 박스 (테두리 제거)
        draw.rounded_rectangle(
            [box_x, box_y, box_x + label_box_size[0], box_y + label_box_size[1]],
            fill="white", radius=8
        )

        # 텍스트 정확히 가운데 정렬 + 그림자
        text_x = box_x + label_box_size[0] // 2
        text_y = box_y + label_box_size[1] // 2
        draw.text((text_x + 1, text_y + 1), score_text, font=font_small, fill="gray", anchor="mm")
        draw.text((text_x, text_y), score_text, font=font_small, fill="black", anchor="mm")

    # 저장
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"result_{timestamp}.png")
    image.save(output_path)
    logger.info(f"결과 이미지 저장됨: {output_path}")

    return image

def estimate_position(landmarks, indices):
    valid_points = [landmarks[i] for i in indices if i < len(landmarks)]
    if not valid_points:
        return (0, 0)
    avg_x = sum(p[0] for p in valid_points) // len(valid_points)
    avg_y = sum(p[1] for p in valid_points) // len(valid_points)
    return (avg_x, avg_y)
