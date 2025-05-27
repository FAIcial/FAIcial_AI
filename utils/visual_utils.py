# utils/visual_utils.py

from PIL import Image, ImageDraw
from typing import List, Tuple

def draw_landmark_points(
    image: Image.Image,
    landmarks: List[Tuple[float, float]],
    color: str = "lime",
    radius: int = 3
) -> Image.Image:
    """
    디버깅용: PIL Image 위에 랜드마크 좌표마다 작은 원(circle)을 그려 반환합니다.

    Args:
        image: PIL Image 객체 (RGBA 모드 권장)
        landmarks: [(x, y), ...] 형태의 랜드마크 좌표 리스트
        color: 원의 색상 (기본 'lime')
        radius: 원의 반지름(px) (기본값 3)

    Returns:
        랜드마크가 오버레이된 새로운 PIL Image 객체
    """
    # RGBA 모드로 변환
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # 투명 오버레이 레이어 생성
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 랜드마크마다 원 그리기
    for x, y in landmarks:
        left_up = (x - radius, y - radius)
        right_down = (x + radius, y + radius)
        draw.ellipse([left_up, right_down], fill=color)

    # 원본 이미지와 오버레이 합성
    return Image.alpha_composite(image, overlay)
