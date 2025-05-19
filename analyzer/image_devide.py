import os
from PIL import Image

# === 부위별 랜드마크 인덱스 ===
FACE_PARTS = {
    "left_eye": [33, 133, 160, 159, 158, 157, 173],
    "right_eye": [362, 263, 387, 386, 385, 384, 398],
    "nose": [1, 2, 98, 327],
    "mouth": [13, 14, 78, 308, 61, 291],
    "left_ear": [234, 93],
    "right_ear": [454, 323],
}

# === 부위별 패딩 설정 ===
PADDING_MAP = {
    'left_eye': {'top': 5, 'bottom': 5, 'left': 10, 'right': 10},
    'right_eye': {'top': 5, 'bottom': 5, 'left': 10, 'right': 10},
    'nose': {'top': 40, 'bottom': 10, 'left': 10, 'right': 10},
    'mouth': {'top': 20, 'bottom': 25, 'left': 10, 'right': 10},
    'left_ear': {'top': 50, 'bottom': 10, 'left': 30, 'right': 10},
    'right_ear': {'top': 50, 'bottom': 10, 'left': 10, 'right': 30},
}

# === 특정 부위 잘라내기 (방향별 패딩 적용) ===
def devide_region(image_pil: Image.Image, landmarks: list[tuple], indices: list[int], padding: dict):
    points = [landmarks[i] for i in indices if 0 <= i < len(landmarks)]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    # 방향별 패딩 가져오기 (기본값 20)
    top = padding.get('top', 20)
    bottom = padding.get('bottom', 20)
    left = padding.get('left', 20)
    right = padding.get('right', 20)

    min_x = max(min(xs) - left, 0)
    max_x = min(max(xs) + right, image_pil.width)
    min_y = max(min(ys) - top, 0)
    max_y = min(max(ys) + bottom, image_pil.height)

    return image_pil.crop((min_x, min_y, max_x, max_y))

# === 얼굴 부위 저장 ===
def save_face_parts(landmarks: list[tuple], image_pil: Image.Image, output_dir: str = "face_parts"):
    os.makedirs(output_dir, exist_ok=True)

    for part_name, indices in FACE_PARTS.items():
        padding = PADDING_MAP.get(part_name, {})  # 없으면 기본값 사용
        cropped = devide_region(image_pil, landmarks, indices, padding)
        save_path = os.path.join(output_dir, f"{part_name}.png")
        cropped.save(save_path)
        print(f"{part_name} 저장 완료: {save_path}")
