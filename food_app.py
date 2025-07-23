import streamlit as st
import requests
import base64
from PIL import Image

# 화면 하단에 SOLASiEU CI 표시
st.markdown(body="""
                <style>
                .footer {
                            position: fixed;
                            left: 0;
                            bottom: 0;
                            width: 100%;
                            background-color: #ffffff;
                            color: #87CEEB;
                            text-align: center;
                            padding: 10px;
                            border-top: 1px solid #ccc;
                            z-index: 9999;
                        }
                </style>

                <div class="footer">
                    <img src="https://solasieu.cafe24.com/web/upload/labeldesign/logo.png" width="100">
                </div>
            """, 
            unsafe_allow_html=True)


DEFAULT_PROMPT = """
# Role

당신은 사용자의 식단 관리를 돕는 전문 임상 영양사(Clinical Dietitian)입니다. 음식 사진만으로 영양 성분을 분석하고, 이를 바탕으로 개인화된 조언을 제공하는 능력이 뛰어납니다.



# Context

사용자가 자신이 먹은 음식 사진을 업로드할 것입니다. 당신의 임무는 해당 사진을 분석하여 음식의 종류와 양을 파악하고, 주요 영양 성분 함량을 추정한 뒤, 사용자가 자신의 식단을 쉽게 이해하고 관리할 수 있도록 명확하고 실용적인 정보를 제공하는 것입니다. 모든 분석은 식품의약품안전처의 1일 영양성분 기준치에 근거해야 합니다.

"""


DEFAULT_QUESTION = """
# Task

업로드된 음식 사진을 분석하여, ① 칼로리, ② 주요 3대 영양소(탄수화물, 단백질, 지방), ③ 나트륨, ④ 식이섬유의 예상 함량을 분석하고, 이를 성인 1일 영양성분 기준치와 비교하여 그 결과를 표와 함께 명확히 설명해 주세요.



# Instructions

1.  **음식 인식:** 사진 속 음식의 종류와 양을 정확하게 인식하고 특정합니다. (예: "제육볶음 1인분과 쌀밥 1공기")

2.  **영양 성분 추정:** 인식된 음식을 기반으로 아래 항목들의 예상 함량을 계산합니다.

    * 열량 (kcal)

    * 탄수화물 (g)

    * 단백질 (g)

    * 지방 (g)

    * 나트륨 (mg)

    * 식이섬유 (g)

3.  **기준치와 비교 분석:** [1일 영양성분 기준치]를 사용하여, 각 성분이 기준치 대비 몇 퍼센트(%)를 차지하는지 계산합니다.

    * **[1일 영양성분 기준치]:** 열량 2,000kcal, 탄수화물 324g, 단백질 55g, 지방 54g, 나트륨 2,000mg, 식이섬유 25g

4.  **결과 제시:** 아래 [Output Format]에 따라 분석 결과를 명확하게 정리하여 출력합니다.

5.  **요약 및 조언:** 표 아래에, 분석 결과에 대한 종합적인 평가와 건강한 식단을 위한 실용적인 조언을 1~2문장으로 덧붙입니다. 특히 기준치 대비 눈에 띄게 높거나 낮은 영양소가 있다면 반드시 언급하여 주의를 환기시켜 주세요.



# Constraints

* 모든 분석 수치는 정확한 측정이 아닌, 사진을 기반으로 한 **'추정치'**임을 서두에 명확히 밝혀주세요.

* 사용자가 이해하기 쉽도록 친절하고 전문적인 어조를 유지하세요.

* 사진만으로 분석이 어렵거나 불가능할 경우, 정중하게 추가 정보를 요청하거나 다른 사진을 업로드해달라고 안내하세요.



# Output Format



> 💡 **주의:** 이 분석은 사진을 기반으로 한 추정치이며, 실제 값과 차이가 있을 수 있습니다.



**1. 음식 인식 결과**

* [여기에 인식된 음식 이름과 예상되는 양을 기입]



**2. 영양 성분 분석 (추정치)**

| 영양 성분 | 예상 섭취량 | 1일 기준치 대비 |

| :--- | :--- | :--- |

| **열량** | OOO kcal | OO% |

| **탄수화물** | OOO g | OO% |

| **단백질** | OOO g | OO% |

| **지방** | OOO g | OO% |

| **나트륨** | OOO mg | OO% |

| **식이섬유**| O g | O% |



**3. 영양사 요약 및 조언**

* [여기에 분석 결과에 대한 종합 평가와 실용적인 조언을 1~2 문장으로 작성]
"""


# Assistant 응답 처리 함수 정의
def answer_for_food(question, image_food):
    
    image_food = image_food.read()
    base64_image = base64.b64encode(image_food).decode("utf-8")

    OPENAI_API_KEY = st.secrets['OPENAI_API_KEY']

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # 이전 대화 맥락 불러오기
    context_messages = []

    for message in st.session_state.messages:
        if message["role"] == "system":
            context_messages.append({
                "role": "system",
                "content": message["content"]
            })
        elif message["role"] in ("user", "assistant"):
            context_messages.append({
                "role": message["role"],
                "content": message["content"]
            })

    # 현재 질문 + 이미지 포함 메시지 추가
    context_messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"{question}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        ]
    })

    payload = {
        "model": "gpt-4o",
        "messages": context_messages,
        "max_tokens": 1000
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload
    )

    return response.json()['choices'][0]['message']['content']


image_food = st.file_uploader("⚠️ 음식 사진만 업로드하세요!", type=['png', 'jpg', 'jpeg'])

# 새 이미지 업로드 시 대화 초기화
if image_food:
    image = Image.open(image_food)
    st.image(image, width=500)
    #image_food.seek(0)

    if "prev_image_name" not in st.session_state or st.session_state.prev_image_name != image_food.name:
        st.session_state.messages = [{"role":"system", "content":DEFAULT_PROMPT}]
        st.session_state.prev_image_name = image_food.name
        image_food.seek(0)
        st.markdown(answer_for_food(question=DEFAULT_QUESTION, image_food=image_food))
    else:
        st.session_state.messages = [{"role":"system", "content":"너는 음식 전문가야. 사용자 질문에 친절하고, 간략하게 답변해줘."}]
else:
    st.session_state.pop("prev_image_name", None)

# 사용자 입력 받기
user_input = st.chat_input("메시지를 입력하세요...")

# 메시지 처리
if user_input:
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Assistant 응답
    with st.chat_message("assistant"):
        with st.spinner("메시지 작성 중..."):
            image_food.seek(0)
            answer = answer_for_food(question=user_input, image_food=image_food)
            st.markdown(answer)

    # Assistant 메시지 저장
    st.session_state.messages.append({"role": "assistant", "content": answer})

# 마지막 assistant 응답만 화면에 출력
elif len(st.session_state.get("messages", [])) >= 2:
    last_message = st.session_state.messages[-1]
    if last_message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(last_message["content"])