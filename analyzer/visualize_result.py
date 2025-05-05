from PIL import Image, ImageDraw, ImageFont

def generate_result_image(image, landmarks, score, part_scores):
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # 폰트 설정
    try:
        font = ImageFont.truetype("Arial.ttf", 24)
    except:
        font = ImageFont.load_default()

    # 상단 텍스트
    draw.text((width // 2, 30), f"당신의 비대칭은\n{score:.2f}%!!", fill="black", anchor="mm", font=font)
    draw.text((width // 2, 100), "완전 완벽해요~! 😎", fill="black", anchor="mm", font=font)

    # 주요 부위 평균 좌표 계산
    def average_coords(indices):
        points = [landmarks[i] for i in indices if i < len(landmarks)]
        if not points:
            return (0, 0)
        x_avg = sum(p[0] for p in points) // len(points)
        y_avg = sum(p[1] for p in points) // len(points)
        return (x_avg, y_avg)

    key_parts = {
        "눈": ([33, 263], part_scores.get("eye", 0)),
        "코": ([1], part_scores.get("nose", 0)),
        "입": ([13, 14], part_scores.get("mouth", 0)),
        "귀": ([234, 454], part_scores.get("ear", 0)),
    }

    for part, (indices, value) in key_parts.items():
        x, y = average_coords(indices)
        label = f"{part}: {value}%"
        draw.rounded_rectangle([x, y, x+80, y+30], fill="white", outline="gray", radius=8)
        draw.text((x + 5, y + 5), label, fill="black", font=font)

    return image
