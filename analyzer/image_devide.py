import os
from PIL import Image, ImageOps
from skimage.metrics import structural_similarity as ssim
import numpy as np

# === 얼굴 부위별 랜드마크 인덱스 ===
FACE_PARTS = {
    "left_eye": [33, 133, 160, 159, 158, 157, 173],
    "right_eye": [362, 263, 387, 386, 385, 384, 398],
    "nose": [1, 2, 98, 327],
    "mouth": [13, 14, 78, 308, 61, 291],
    "left_ear": [234, 93],
    "right_ear": [454, 323],
}

# === 부위별 패딩 설정 (상하좌우) ===
PADDING_MAP = {
    'left_eye': {'top': 5, 'bottom': 5, 'left': 10, 'right': 10},
    'right_eye': {'top': 5, 'bottom': 5, 'left': 10, 'right': 10},
    'nose': {'top': 100, 'bottom': 10, 'left': 10, 'right': 10},
    'mouth': {'top': 20, 'bottom': 25, 'left': 10, 'right': 10},
    'left_ear': {'top': 50, 'bottom': 10, 'left': 10, 'right': 10},
    'right_ear': {'top': 50, 'bottom': 10, 'left': 10, 'right': 10},
}

# === 부위별 영역 자르기 함수 ===
def devide_region(image_pil: Image.Image, landmarks: list[tuple], indices: list[int], padding: dict) -> Image.Image:
    points = [landmarks[i] for i in indices if 0 <= i < len(landmarks)]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    top = padding.get('top', 20)
    bottom = padding.get('bottom', 20)
    left = padding.get('left', 20)
    right = padding.get('right', 20)

    min_x = max(min(xs) - left, 0)
    max_x = min(max(xs) + right, image_pil.width)
    min_y = max(min(ys) - top, 0)
    max_y = min(max(ys) + bottom, image_pil.height)

    return image_pil.crop((min_x, min_y, max_x, max_y))

# === 얼굴 부위 이미지 추출 (저장 없이 반환) ===
def get_face_parts(landmarks: list[tuple], image_pil: Image.Image) -> dict[str, Image.Image]:
    parts = {}
    for part_name, indices in FACE_PARTS.items():
        padding = PADDING_MAP.get(part_name, {})
        cropped = devide_region(image_pil, landmarks, indices, padding)
        parts[part_name] = cropped
    return parts

# === 기본 SSIM 비교 함수 (좌우 반전 포함, 이미지 객체 사용) ===
def compare_ssim_flipped_images(img1: Image.Image, img2: Image.Image) -> float:
    img1 = img1.convert("L")
    img2 = img2.convert("L")

    # 좌우 반전
    img1 = ImageOps.mirror(img1)

    # 크기 맞추기
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    arr1 = np.array(img1)
    arr2 = np.array(img2)

    score, _ = ssim(arr1, arr2, full=True)
    return round(score * 100, 2)

# === 코, 입 반으로 나눈 후 일치율 비교 함수 ===
def compare_split_symmetry(image: Image.Image) -> float:
    width, height = image.size
    mid = width // 2

    # 좌/우 반으로 나누기
    left_half = image.crop((0, 0, mid, height))
    right_half = image.crop((mid, 0, width, height))

    # 오른쪽 반을 좌우 반전시켜 비교
    right_half_flipped = ImageOps.mirror(right_half)

    # 크기 맞추기
    if left_half.size != right_half_flipped.size:
        right_half_flipped = right_half_flipped.resize(left_half.size)

    # SSIM 계산
    arr1 = np.array(left_half.convert("L"))
    arr2 = np.array(right_half_flipped.convert("L"))
    score, _ = ssim(arr1, arr2, full=True)
    return round(score * 100, 2)


# === 각 부위 이미지 일치율 계산 함수 ===
def compare_symmetric_parts_from_images(parts: dict[str, Image.Image]) -> dict[str, float | None]:
    results = {}

    # 눈
    if "left_eye" in parts and "right_eye" in parts:
        results["eye"] = compare_ssim_flipped_images(parts["left_eye"], parts["right_eye"])
    else:
        results["eye"] = None

    # 귀
    if "left_ear" in parts and "right_ear" in parts:
        results["ear"] = compare_ssim_flipped_images(parts["left_ear"], parts["right_ear"])
    else:
        results["ear"] = None

    # 코 (자기 자신을 반으로 나눠 비교)
    if "nose" in parts:
        results["nose"] = compare_split_symmetry(parts["nose"])
    else:
        results["nose"] = None

    # 입
    if "mouth" in parts:
        results["mouth"] = compare_split_symmetry(parts["mouth"])
    else:
        results["mouth"] = None

    return results