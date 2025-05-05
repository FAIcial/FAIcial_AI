import os
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from logger import logger

# 최초 실행 시 자동 폰트 다운로드
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

    # 반드시 RGBA 모드로 변환 (투명도 지원)
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

    # 상단 텍스트 정의
    center_x = width // 2
    text1 = "당신의 비대칭은"
    text2 = f"{score:.2f}%!!"
    text3 = "완전 완벽해요~!"

    # 반투명 배경 박스를 위한 overlay 생성
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    padding = 20
    box_width = width - 2 * padding
    box_height = 130
    box_coords = [padding, 20, padding + box_width, 20 + box_height]
    overlay_draw.rectangle(box_coords, fill=(0, 0, 0, 180))  # 반투명 검정

    # 합성
    image = Image.alpha_composite(image, overlay)

    # 텍스트 렌더링 (draw는 합성된 이미지 기준)
    draw = ImageDraw.Draw(image)
    draw.text((center_x, 40), text1, fill="white", anchor="mm", font=font_large)
    draw.text((center_x, 80), text2, fill="white", anchor="mm", font=font_large)
    draw.text((center_x, 120), text3, fill="white", anchor="mm", font=font_small)

    # 부위별 라벨링
    label_box_size = (100, 30)
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
        "코": "nose",  # 향후 nose 값이 추가될 수 있음
    }

    for part, (x, y) in part_positions.items():
        key = key_map.get(part, None)
        part_value = part_scores.get(key, None)
        score_text = f"{part}: {part_value:.1f}%" if part_value is not None else f"{part}: -"

        # 위치 조정: 눈/코 → 왼쪽, 입/귀 → 오른쪽
        if part in ["눈", "코"]:
            box_x = 30  # 왼쪽 여백
        else:
            box_x = width - label_box_size[0] - 30  # 오른쪽 여백

        box_y = y
        draw.rounded_rectangle(
            [box_x, box_y, box_x + label_box_size[0], box_y + label_box_size[1]],
            fill="white", outline="gray", radius=8
        )
        draw.text((box_x + 5, box_y + 5), score_text, fill="black", font=font_small)

    # 이미지 저장
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
