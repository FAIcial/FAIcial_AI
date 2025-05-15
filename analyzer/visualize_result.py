import os
import requests
from datetime import datetime
from math import hypot
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
    avg_x = sum(x for x, y in pts) // len(pts)
    avg_y = sum(y for x, y in pts) // len(pts)
    return (avg_x, avg_y)


def draw_dotted_line(draw, start, end, color="blue", width=2, dash_length=10):
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


def crop_to_face_center_with_zoom(
    image: Image.Image,
    landmarks,
    h_ratio: float = 0.5,
    v_ratio: float = 4/5,
    min_face_occupancy: float = 0.6
):
    """
    얼굴 귀끝(234,454)과 머리(10), 턱(152)을 기준으로
    얼굴 중심을 (h_ratio,v_ratio) 위치에 맞춰 확대 후 크롭합니다.
    또한, 얼굴 세로 높이가 크롭 후 화면의 최소 min_face_occupancy 비율을
    차지하도록 추가 확대합니다.
    """
    orig_w, orig_h = image.size

    # 얼굴 가로 중심 (귀끝 중간)
    lx, _ = landmarks[234]
    rx, _ = landmarks[454]
    face_cx = (lx + rx) / 2

    # 얼굴 세로 중심 및 높이 (머리·턱 중간)
    _, ty = landmarks[10]
    _, by = landmarks[152]
    face_cy = (ty + by) / 2
    face_h = by - ty

    # 4:5 비율 크롭 크기 결정
    ratio = 4 / 5
    if orig_w / orig_h >= ratio:
        crop_h = orig_h
        crop_w = int(crop_h * ratio)
    else:
        crop_w = orig_w
        crop_h = int(crop_w / ratio)

    # 얼굴 위치를 맞추기 위한 확대율 계산
    needed = [
        (crop_w * h_ratio) / face_cx,
        (crop_w * (1 - h_ratio)) / (orig_w - face_cx),
        (crop_h * v_ratio) / face_cy,
        (crop_h * (1 - v_ratio)) / (orig_h - face_cy),
    ]

    # 얼굴 세로 점유율(min_face_occupancy) 확보를 위한 확대율
    if face_h > 0:
        occ_scale = (min_face_occupancy * crop_h) / face_h
        needed.append(occ_scale)

    scale = max(1.0, *needed)

    # 이미지 및 랜드마크 확대
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    image = image.resize((new_w, new_h), Image.LANCZOS)
    landmarks = [(x * scale, y * scale) for x, y in landmarks]
    face_cx *= scale
    face_cy *= scale

    # 크롭 박스 좌상단 계산
    left = int(face_cx - crop_w * h_ratio)
    top  = int(face_cy - crop_h * v_ratio)
    left = max(0, min(left, new_w - crop_w))
    top  = max(0, min(top, new_h - crop_h))

    cropped = image.crop((left, top, left + crop_w, top + crop_h))
    new_landmarks = [(x - left, y - top) for x, y in landmarks]
    return cropped, new_landmarks


def generate_result_image(image: Image.Image, landmarks, score, part_scores):
    logger.debug("결과 이미지 시각화 시작")

    # 1) 얼굴 4:5 비율 확대 & 크롭 (세로 80% 위치, 최소 60% 점유)
    image, landmarks = crop_to_face_center_with_zoom(
        image, landmarks,
        h_ratio=0.5,
        v_ratio=6/9,
        min_face_occupancy=0.5
    )

    # 2) 고정 해상도 리사이즈 (px 일관성)
    STANDARD_W, STANDARD_H = 800, 1000
    scale = STANDARD_W / image.width
    image = image.resize((STANDARD_W, STANDARD_H), Image.LANCZOS)
    landmarks = [(x * scale, y * scale) for x, y in landmarks]

    # 3) RGBA
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    w, h = image.size

    # 4) 폰트 크기 (px 고정)
    title_size = 40
    label_size = 24
    face_size  = 15
    font_title = ImageFont.truetype(FONT_PATH, title_size)
    font_label = ImageFont.truetype(FONT_PATH, label_size)
    font_face  = ImageFont.truetype(FONT_PATH, int(face_size * 1.5))

    # 5) 얼굴 기준선 X
    face_center_x, _ = estimate_position(landmarks, [1, 2, 168, 9, 94, 152])
    draw = ImageDraw.Draw(image)
    draw.line([(face_center_x, 0), (face_center_x, h)], fill='yellow', width=2)

    # 6) 상단 텍스트 (상/하 여유 균등 조절)
    image_center_x = w // 2
    vertical_padding = 20    # 텍스트 위/아래 여유
    box_height = title_size * 3 + vertical_padding * 2
    start_y = vertical_padding

    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([20, start_y, w - 20, start_y + box_height], fill=(0, 0, 0, 180))
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    def ctr(txt, offset, fnt):
        y = start_y + vertical_padding + title_size * offset
        draw.text((image_center_x + 1, y + 1), txt, font=fnt, fill='black', anchor='mm')
        draw.text((image_center_x,     y    ), txt, font=fnt, fill='white', anchor='mm')

    ctr('당신의 비대칭은', 0.5, font_title)
    ctr(f'{score:.2f}%!!', 1.5, font_title)
    ctr('완전 완벽해요~!', 2.5, font_face)

    # 7) 거리 시각화
    highlights = [
        (61,  'blue'), (291, 'blue'),
        (133, 'blue'), (362, 'blue'),
        (234, 'cyan'), (454, 'cyan'),
        (98,  'red'),  (327, 'red'),
    ]
    for idx, color in highlights:
        x_i, y_i = landmarks[idx]
        dist = abs(face_center_x - x_i)
        draw_dotted_line(draw, (x_i, y_i), (face_center_x, y_i), color=color)
        draw.text(
            ((x_i + face_center_x) // 2, y_i - face_size // 2),
            f"{int(dist)}px",
            font=font_face,
            fill=color,
            anchor='mm'
        )

    # 8) 부위별 라벨 (랜드마크 기준 위치, 눈/귀 위치 변경 금지)
    LABEL_W, LABEL_H = 150, 50
    PADDING = 20
    label_indices = {'눈': 33, '코': 1, '입': 13, '귀': 234}
    static_pos = {}
    for part, idx in label_indices.items():
        x_pt, y_pt = landmarks[idx]
        if part in ['눈', '입']:
            bx = PADDING
        else:
            bx = w - LABEL_W - PADDING
        by = int(y_pt - LABEL_H / 2)
        by = max(PADDING, min(by, h - LABEL_H - PADDING))
        static_pos[part] = (bx, by)

    key_map = {'눈': 'eyes', '코': 'nose', '입': 'mouth', '귀': 'jaw'}
    for part, (bx, by) in static_pos.items():
        txt = f"{part}: {part_scores.get(key_map[part], 0):.1f}%"
        draw.rounded_rectangle([bx, by, bx + LABEL_W, by + LABEL_H],
                               fill='white', radius=8)
        draw.text((bx + LABEL_W // 2, by + LABEL_H // 2),
                  txt, font=font_label, fill='black', anchor='mm')

    # 9) 날짜별 저장
    date_folder = datetime.now().strftime('%Y%m%d')
    out_dir = os.path.join('outputs', date_folder)
    os.makedirs(out_dir, exist_ok=True)
    filename = f"result_{datetime.now():%Y%m%d_%H%M%S}.png"
    path = os.path.join(out_dir, filename)
    image.save(path)
    logger.info(f"결과 이미지 저장됨: {path}")

    return image
