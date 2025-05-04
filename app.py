from flask import Flask, request, jsonify
from analyzer.detect_face import detect_landmarks
from analyzer.analyze_symmetry import calculate_symmetry
from analyzer.visualize_result import generate_result_image  # 아직 미구현 시 주석처리 가능
import base64
import io

app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    image_bytes = file.read()

    try:
        # 1. 얼굴 랜드마크 추출
        landmarks, image = detect_landmarks(image_bytes)
        if landmarks is None:
            return jsonify({"error": "No face detected"}), 400

        # 2. 대칭률 계산
        score, part_scores = calculate_symmetry(landmarks)

        # 3. 결과 이미지 시각화 (임시로 원본 이미지 반환 가능)
        result_image = generate_result_image(image, landmarks, score, part_scores)

        # 4. 이미지 base64 인코딩
        buffered = io.BytesIO()
        result_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return jsonify({
            "symmetry_score": score,
            "part_symmetries": part_scores,
            "image_base64": f"data:image/png;base64,{img_str}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
