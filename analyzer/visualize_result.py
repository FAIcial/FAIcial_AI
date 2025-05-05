from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
from logger import logger

FONT_PATH = os.path.join("fonts", "NotoSansKR-Regular.otf")

def generate_result_image(image, landmarks, score, part_scores):
    logger.debug("결과 이미지 시각화 시작")

    draw = ImageDraw.Draw(image)
    width, height = image.size

    try:
        font_large = ImageFont.truetype(FONT_PATH, 40)
        font_small = ImageFont.truetype(FONT_PATH, 24)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        logger.warning("기본 폰트 사용 중 (내부 폰트 로드 실패)")

    # 상단 비대칭률 강조 텍스트
    center_x = width // 2
    draw.text((center_x, 30), f"당신의 비대칭은", fill="black", anchor="mm", font=font_large)
    draw.text((center_x, 80), f"{score:.2f}%!!", fill="black", anchor="mm", font=font_large)
    draw.text((center_x, 140), "완전 완벽해요~! 😎", fill="black", anchor="mm", font=font_small)

    # 부위별 라벨링
    label_box_size = (100, 30)
    part_positions = {
        "눈": estimate_position(landmarks, range(33, 133)),
        "코": estimate_position(landmarks, range(168, 172)),
        "입": estimate_position(landmarks, range(78, 88)),
        "귀": estimate_position(landmarks, [234, 454]),
    }

    for part, (x, y) in part_positions.items():
        score_text = f"{part}: {part_scores.get(part, 'N/A')}%"
        draw.rounded_rectangle(
            [x, y, x + label_box_size[0], y + label_box_size[1]],
            fill="white", outline="gray", radius=8
        )
        draw.text((x + 5, y + 5), score_text, fill="black", font=font_small)

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