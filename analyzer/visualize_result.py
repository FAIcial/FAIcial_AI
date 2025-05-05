from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
from logger import logger

def generate_result_image(image, landmarks, score, part_scores):
    logger.debug("결과 이미지 시각화 시작")

    draw = ImageDraw.Draw(image)
    width, height = image.size

    try:
        font = ImageFont.truetype("Arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
        logger.warning("기본 폰트 사용 중 (Arial.ttf 로드 실패)")

    # 1. 상단 텍스트
    center_x = width // 2
    draw.text((center_x, 30), f"당신의 비대칭은\n{score:.2f}%!!", fill="black", anchor="mm", font=font)
    draw.text((center_x, 100), "완전 완벽해요~! 😎", fill="black", anchor="mm", font=font)

    # 2. 부위별 좌표 추정 및 라벨 박스
    label_box_size = (100, 30)
    part_positions = {
        "눈": estimate_position(landmarks, range(33, 133)),       # 양 눈 평균
        "코": estimate_position(landmarks, range(168, 172)),      # 코끝
        "입": estimate_position(landmarks, range(78, 88)),        # 입 중심
        "귀": estimate_position(landmarks, [234, 454]),           # 양쪽 귀 근처
    }

    for part, (x, y) in part_positions.items():
        score_text = f"{part}: {part_scores.get(part, 'N/A')}%"
        box_x, box_y = x, y
        draw.rounded_rectangle(
            [box_x, box_y, box_x + label_box_size[0], box_y + label_box_size[1]],
            fill="white", outline="gray", radius=8
        )
        draw.text((box_x + 5, box_y + 5), score_text, fill="black", font=font)

    # 3. 이미지 저장
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
