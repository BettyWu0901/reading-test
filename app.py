import streamlit as st
import pandas as pd
import datetime
import os
import json

# ==========================================
# 1. AI 設定與診斷區
# ==========================================
ai_status_msg = ""
ai_available = False

try:
    # 測試 1: 檢查是否能載入 Google 工具
    import google.generativeai as genai
    
    # 測試 2: 檢查保險箱有沒有鑰匙
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        ai_available = True
        ai_status_msg = "✅ AI 連線成功！(驅動與金鑰皆正常)"
    else:
        ai_available = False
        ai_status_msg = "❌ 失敗：Secrets 裡找不到 'GEMINI_API_KEY'。請檢查名稱是否完全正確 (全大寫)。"

except ImportError:
    ai_available = False
    ai_status_msg = "❌ 失敗：找不到 'google-generativeai' 工具。請確認 requirements.txt 有儲存成功。"
except Exception as e:
    ai_available = False
    ai_status_msg = f"❌ 發生未預期的錯誤: {str(e)}"

# ==========================================
# 2. AI 核心功能區
# ==========================================

# --- 安全設定：防止 AI 因為故事內容(鬼怪/恐怖)而拒絕回答 ---
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

def get_mock_quiz():
    """備用題庫 (當 AI 連線失敗或報錯時使用)"""
    return {
        "qa_questions": [{"id": 1, "question": "為什麼真由美會長出魚鱗？(這是備用題庫，代表 AI 發生錯誤)", "score": 20}],
        "mc_questions": [
            {"id": 1, "type": "提取訊息", "question": "真由美用什麼換到了美人魚軟糖？", "options": ["1. 100元", "2. 昭和42年的10元", "3. 釦子", "4. 寶石"], "answer": "2"},
            {"id": 2, "type": "推論訊息", "question": "錢天堂有什麼特徵？", "options": ["1. 在大馬路旁", "2. 只有幸運的人能找到", "3. 賣文具", "4. 老闆是男生"], "answer": "2"}
        ]
    }

def call_ai_generate_quiz(level, text_content):
    if not ai_available:
        return get_mock_quiz()

    # 依照等級設定出題規則
    if level == "A":
        rule = "出題規則：適合一般程度。需包含：提取訊息2題、推論訊息4題、詮釋整合或比較評估4題。問答題1題。"
    elif level == "B":
        rule = "出題規則：適合精熟程度。需包含：提取訊息1題、推論訊息3題、詮釋整合或比較評估6題。問答題2題。"
    else: # Level C
        rule = "出題規則：適合深刻體會程度。需包含：推論訊息3題、詮釋整合或比較評估7題。問答題3題。"

    prompt = f"""
    你是一位專業的國小閱讀素養出題老師。請閱讀以下文章，並依照規則產出一份測驗卷。
    【文章內容】：{text_content[:30000]} 
    【{rule}】
    【格式要求】：請回傳純 JSON 格式。
    JSON 結構範例：
    {{
        "qa_questions": [{{"id": 1, "question": "...", "score": 20}}],
        "mc_questions": [{{"id": 1, "type": "...", "question": "...", "options": ["1. A", "2. B", "3. C", "4. D"], "answer": "2"}}]
    }}
    請確保選擇題有 4 個選項。
    """
    try:
        # 【重要修改】使用診斷出來的 gemini-2.5-flash 模型
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # 清理回應文字，確保是純 JSON
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        # 將詳細錯誤顯示在側邊欄，方便除錯
        st.sidebar.error(f"AI 出題過程發生錯誤: {e}")
        return get_mock_quiz()

def call_ai_grade_qa(question, student_answer, story_text):
    if not ai_available: return 15, "（模擬評分）AI 未連線。"
    try:
        # 【重要修改】使用 gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            f"請評分(滿分20)：題目：{question}，回答：{student_answer}。回傳格式：分數|評語",
            safety_settings=safety_settings
        )
        text = response.text.strip()
        if "|" in text:
            s, f = text.split("|", 1)
            return int(float(s)), f
        return 10, text
    except:
        return 10, "AI 評分忙碌中。"

def call_ai_final_comment(total, qa_feedback, story_text):
    if not ai_available: return "模擬總評：完成！"
    try:
        # 【重要修改】使用 gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        return model.generate_content(f"給予總分 {total} 分的學生一句繁體中文鼓勵。", safety_settings=safety_settings).text.strip()
    except:
        return "測驗完成！繼續加油！"

# ==========================================
# 3. 介面與流程
# ==========================================
FILE_NAME = "reading_records.csv"
def save_to_csv(data):
    df_new = pd.DataFrame([data])
    if not os.path.exists(FILE_NAME):
        df_new.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(FILE_NAME, mode='a', header=False, index=False, encoding='utf-8-sig')

def load_story():
    if os.path.exists("story.txt"):
        with open("story.txt", "r", encoding="utf-8") as f: return f.read()
    return "找不到 story.txt"

st.set_page_config(page_title="神奇柑仔店 - AI 閱讀認證", page_icon="🤖")
st.title("🤖 神奇柑仔店 - AI 閱讀挑戰")

# --- 側邊欄 ---
with st.sidebar:
    st.header("🔧 系統狀態檢查")
    if ai_available:
        st.success(ai_status_msg)
    else:
        st.error(ai_status_msg)
        
    st.markdown("---")
    st.header("1. 學生資料")
    student_class = st.text_input("班級")
    seat_num = st.text_input("座號")
    student_name = st.text_input("姓名")
    st.header("2. 老師專區")
    if st.text_input("密碼", type="password") == "1234":
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, "rb") as f: st.download_button("下載成績單", f, "scores.csv")

# --- 初始化 Session State ---
if 'step' not in st.session_state: st.session_state.step = 'login'
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = {}
if 'current_q_index' not in st.session_state: st.session_state.current_q_index = 0
if 'answers' not in st.session_state: st.session_state.answers = []
if 'history' not in st.session_state: st.session_state.history = []

# --- 主流程邏輯 ---
if not (student_class and seat_num and student_name):
    st.warning("👈 請先輸入班級、座號、姓名")
    st.stop()

if st.session_state.step == 'login':
    st.subheader(f"👋 {student_name} 你好！")
    c1, c2, c3 = st.columns(3)
    if c1.button("A 一般"): 
        st.session_state.level = "A"; st.session_state.step = 'confirm'; st.rerun()
    if c2.button("B 精熟"): 
        st.session_state.level = "B"; st.session_state.step = 'confirm'; st.rerun()
    if c3.button("C 深刻"): 
        st.session_state.level = "C"; st.session_state.step = 'confirm'; st.rerun()

elif st.session_state.step == 'confirm':
    if st.button("開始測驗"):
        with st.spinner("AI 正在閱讀故事並出題中...(約需 5-10 秒)"):
            story = load_story()
            # 呼叫 AI 出題
            quiz = call_ai_generate_quiz(st.session_state.level, story)
            
            st.session_state.quiz_data = quiz
            st.session_state.all_questions = []
            
            # 整理題目順序
            if "qa_questions" in quiz:
                for q in quiz['qa_questions']: st.session_state.all_questions.append({'type': 'QA', 'data': q})
            if "mc_questions" in quiz:
                for q in quiz['mc_questions']: st.session_state.all_questions.append({'type': 'MC', 'data': q})
            
            # 初始化對話紀錄
            st.session_state.history = [{"role": "bot", "content": "你好！我是 AI 老師，測驗開始囉！"}]
            
            # 顯示第一題
            if len(st.session_state.all_questions) > 0:
                q1 = st.session_state.all_questions[0]
                q_text = q1['data']['question']
                if q1['type'] == 'MC': q_text += "\n" + "\n".join(q1['data']['options'])
                st.session_state.history.append({"role": "bot", "content": f"【第一題】{q_text}"})
                st.session_state.step = 'testing'
                st.rerun()
            else:
                st.error("錯誤：沒有產生任何題目，請檢查側邊欄的錯誤訊息，或按重新整理再試一次。")

elif st.session_state.step == 'testing':
    # 顯示歷史對話
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]): st.write(msg["content"])
    
    idx = st.session_state.current_q_index
    if idx < len(st.session_state.all_questions):
        q = st.session_state.all_questions[idx]
        user_input = st.chat_input("請輸入答案...")
        if user_input:
            # 紀錄使用者回答
            with st.chat_message("user"): st.write(user_input)
            st.session_state.history.append({"role": "user", "content": user_input})
            st.session_state.answers.append({"type": q['type'], "user_response": user_input, "question_data": q['data']})
            
            # 準備下一題
            next_idx = idx + 1
            st.session_state.current_q_index = next_idx
            if next_idx < len(st.session_state.all_questions):
                nq = st.session_state.all_questions[next_idx]
                nq_text = nq['data']['question']
                if nq['type'] == 'MC': nq_text += "\n" + "\n".join(nq['data']['options'])
                st.session_state.history.append({"role": "bot", "content": f"收到！下一題：\n{nq_text}"})
                st.rerun()
            else:
                # 題目做完了，進入計分
                st.session_state.step = 'calculating'; st.rerun()

elif st.session_state.step == 'calculating':
    with st.spinner("AI 老師正在改考卷..."):
        total = 0; mc = 0; qa = 0
        story = load_story()
        
        for ans in st.session_state.answers:
            if ans['type'] == 'MC':
                # 選擇題評分 (檢查第一個字元)
                if str(ans['user_response'])[0] == str(ans['question_data']['answer'])[0]:
                    pts = 8 if st.session_state.level == "A" else (6 if st.session_state.level == "B" else 4)
                    total += pts; mc += pts
            else:
                # 問答題呼叫 AI 評分
                s, f = call_ai_grade_qa(ans['question_data']['question'], ans['user_response'], story)
                total += s; qa += s
        
        cmt = call_ai_final_comment(total, "", story)
        rec = {"班級": student_class, "座號": seat_num, "姓名": student_name, "日期": datetime.datetime.now().strftime("%Y-%m-%d"), "總分": total, "評語": cmt}
        save_to_csv(rec)
        st.session_state.final = rec; st.session_state.step = 'finished'; st.rerun()

elif st.session_state.step == 'finished':
    res = st.session_state.final
    st.balloons()
    st.success(f"🎉 測驗完成！總分：{res['總分']} 分")
    st.info(f"AI 老師評語：{res['評語']}")
    
    if st.button("🔄 重新開始測驗"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
