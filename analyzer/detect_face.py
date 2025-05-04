# analyzer/detect_face.py

import cv2
import numpy as np
from PIL import Image
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

def detect_landmarks(image_bytes: bytes):
    # 이미지 바이트 → OpenCV 이미지
    image_array = np.frombuffer(image_bytes, np.uint8)
    image_bgr = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image_bgr is None:
        raise ValueError("Invalid image data")

    # BGR → RGB 변환
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    # MediaPipe 모델 초기화
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5
    ) as face_mesh:

        results = face_mesh.process(image_rgb)

        if not results.multi_face_landmarks:
            return None, None  # 얼굴이 감지되지 않음

        # 첫 번째 얼굴의 랜드마크 추출
        face_landmarks = results.multi_face_landmarks[0]

        landmarks = []
        h, w, _ = image_rgb.shape
        for lm in face_landmarks.landmark:
            x, y = int(lm.x * w), int(lm.y * h)
            landmarks.append((x, y))

        # OpenCV 이미지를 PIL 이미지로 변환
        image_pil = Image.fromarray(image_rgb)

        return landmarks, image_pil
