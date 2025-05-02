# 🧠 FAIcial AI 서버

AI 기반 얼굴 대칭 분석 백엔드 서버입니다.  
사용자가 업로드한 얼굴 이미지를 기반으로 MediaPipe를 활용해 얼굴 랜드마크를 추출하고,  
좌우 대칭률을 계산하여 결과를 시각화한 이미지를 제공합니다.

---

## 📁 디렉토리 구조

```plaintext
AI_Part/
│
├── app.py                       # 🔹 Flask 서버 실행 진입점
├── requirements.txt             # 🔹 필요한 라이브러리 목록 (pip install 용)
├── README.md                    # 🔹 간단한 사용 설명 (선택)
├── CHANGELOG.md                 # 🔹 알고리즘 개선 이력 기록 (1달 1회 주기)
│
├── utils/
│   ├── image_utils.py           # 📦 이미지 변환, base64 처리 등 유틸 함수
│   └── face_utils.py            # 📦 얼굴 중심선 계산, 정규화 등 보조 기능
│
├── analyzer/
│   ├── __init__.py              # 📦 모듈 인식용
│   ├── detect_face.py           # 🔍 MediaPipe로 얼굴 인식 및 랜드마크 추출
│   ├── analyze_symmetry.py      # 📏 좌우 대칭률 계산 함수
│   └── visualize_result.py      # 🖼️ matplotlib으로 결과 이미지 시각화
│
├── test_images/                 # 🧪 테스트용 이미지 폴더
│   ├── sample1.jpg
│   └── sample2.png
│
└── outputs/                     # 💾 생성된 분석 결과 이미지 (개발용 캐시)
    ├── result1.png
    └── result2.png
```

---

## ⚙️ 설치 방법

```bash
# 가상환경 생성 (선택 사항)
python -m venv venv
source venv/bin/activate  # 또는 venv\Scripts\activate (Windows)

# 의존성 설치
pip install -r requirements.txt
```
