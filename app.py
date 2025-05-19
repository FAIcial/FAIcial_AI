from flask import Flask, request, jsonify
from analyzer.detect_face import detect_landmarks
from analyzer.analyze_symmetry import calculate_symmetry
from analyzer.visualize_result import generate_result_image
from analyzer.image_devide import save_face_parts
from logger import logger
from utils.image_utils import encode_image_to_base64

app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
def analyze():
    logger.info("분석 요청 수신됨")

    # 1. 이미지 파일 확인
    if "image" not in request.files:
        logger.warning("요청에 이미지 파일 없음")
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    image_bytes = file.read()

    try:
        # 2. 얼굴 랜드마크 추출
        logger.debug("얼굴 랜드마크 추출 시도")
        landmarks, image = detect_landmarks(image_bytes)
        if landmarks is None:
            logger.warning("얼굴이 감지되지 않음")
            return jsonify({"error": "No face detected"}), 400

        logger.debug(f"랜드마크 수: {len(landmarks)}")

        # 3. 대칭률 계산
        logger.debug("대칭률 계산 시작")
        score, part_scores = calculate_symmetry(landmarks)
        logger.debug(f"총 대칭률 점수: {score}")
        logger.debug(f"부위별 대칭률 점수: {part_scores}")
        
        # 4. 부위별 이미지 자르기 및 이미지 일치율 검사
        save_face_parts(landmarks, image)

        # 5. 결과 이미지 시각화
        result_image = generate_result_image(image, landmarks, score, part_scores)

        # 6. Base64 인코딩 로직 분리 함수 사용
        img_data = encode_image_to_base64(result_image)

        logger.info("분석 성공 및 응답 반환")
        logger.info("결과 이미지 Base64 생성 및 전송 완료")

        return jsonify({
            "symmetry_score": score,
            "part_symmetries": part_scores,
            "image_base64": img_data
        })

    except Exception as e:
        logger.exception("분석 중 예외 발생")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Flask 앱 실행 시작")
    app.run(debug=True)
