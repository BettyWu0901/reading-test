import streamlit as st
import pandas as pd
import datetime
import os
import json
import time

# ==========================================
# 1. AI 設定與診斷區
# ==========================================
ai_status_msg = ""
ai_available = False

try:
    import google.generativeai as genai
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        ai_available = True
        ai_status_msg = "✅ AI 連線成功！"
    else:
        ai_available = False
        ai_status_msg = "❌ 失敗：Secrets 裡找不到 'GEMINI_API_KEY'。"
except Exception as e:
    ai_available = False
    ai_status_msg = f"❌ 錯誤: {str(e)}"

# ==========================================
# 2. AI 核心功能區 (Prompt 優化)
# ==========================================

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

def get_mock_quiz():
    return {
        "qa_questions": [{"id": 1, "question": "為什麼真由美會長出魚鱗？(備用題庫)", "score": 20}],
        "mc_questions": [
            {"id": 1, "type": "提取訊息", "question": "真由美用什麼換到了美人魚軟糖？", "options": ["1. 100元", "2. 昭和42年的10元", "3. 釦子", "4. 寶石"], "answer": "2"}
        ]
    }

def call_ai_generate_quiz(level, text_content):
    if not ai_available: return get_mock_quiz()
    
    # 針對不同等級設定具體題型
    if level == "A":
        rule = "難度：適合國小中年級。著重於「提取訊息」與簡單的「推論」。問答題請問關於角色感受或具體情節。"
    elif level == "B":
        rule = "難度：適合國小高年級。包含「詮釋整合」。問答題請讓學生推測角色的動機或故事的轉折原因。"
    else:
        rule = "難度：適合國中程度。包含「比較評估」。問答題請讓學生探討故事背後的寓意或價值觀判斷。"

    # --- 關鍵修正：限制 AI 的出題視角 ---
    prompt = f"""
    請你根據以下故事內容，為國小學生設計一份閱讀測驗。
    【文章內容】：{text_content[:30000]} 
    
    【出題規則】：
    1. {rule}
    2. **嚴格禁止**：絕對不要問「如果你是老師」、「如何評估這篇文章」等與教育學相關的問題。
    3. **題目焦點**：所有題目都必須針對「故事劇情」、「角色行為」、「結局寓意」來提問。
    4. 題目語言要生動有趣，符合《神奇柑仔店》的風格。

    【格式要求】：請回傳純 JSON 格式。
    JSON 結構範例：
    {{
        "qa_questions": [{{"id": 1, "question": "為什麼主角最後會...", "score": 20}}],
        "mc_questions": [{{"id": 1, "type": "...", "question": "...", "options": ["1. A", "2. B", "3. C", "4. D"], "answer": "2"}}]
    }}
    請確保選擇題有 4 個選項。
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except:
        return get_mock_quiz()

# 專門給選擇題錯題用的提示產生器
def call_ai_generate_hint(question, wrong_answer, correct_option_index, options, story_text):
    if not ai_available: return "請再讀一次故事喔！"
    
    try:
        correct_answer_text = options[int(correct_option_index)-1]
    except:
        correct_answer_text = "正確答案"
    
    prompt = f"""
    學生在《神奇柑仔店》的閱讀測驗中答錯了。請扮演紅子老闆娘，給他一個提示。
    【題目】：{question}
    【學生誤選】：{wrong_answer}
    【正確答案是】：{correct_answer_text}
    【原則】：
    1. **絕對不要直接說出答案**。
    2. 請用引導的方式，例如：「哎呀，再仔細想想，那時候是不是...？」
    3. 語氣要像老闆娘紅子一樣，神秘但溫柔。
    4. 30字以內。
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except:
        return "這題有點難，建議你回頭找找文章中的細節喔！"

def call_ai_grade_qa(question, student_answer, story_text):
    if not ai_available: return 15, "AI 未連線，無法評分。"
    
    prompt = f"""
    請扮演《神奇柑仔店》的紅子老闆娘，批改學生的問答題。
    【題目】：{question}
    【學生回答】：{student_answer}
    【評分標準】：滿分 20 分。
    【回饋原則】：
    1. 若回答錯誤，請用神秘的口吻引導他思考正確方向，**不要直接給答案**。
    2. 若回答正確，請稱讚他很有眼光，是幸運的客人。
    3. 語氣要符合角色設定（成熟、神秘、溫暖）。
    
    回傳格式：分數|評語 (繁體中文)
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        text = response.text.strip()
        if "|" in text:
            s, f = text.split("|", 1)
            return int(float(s)), f
        return 10, text
    except:
        return 10, "評分系統忙碌中，請稍後再試。"

def call_ai_final_comment(total, history_summary, story_text):
    if not ai_available: return "測驗完成！繼續加油！"
    prompt = f"""
    學生在測驗中獲得 {total} 分。
    請用《神奇柑仔店》老闆娘紅子的口吻，給他一句結語。
    例如：「你今天的運勢不錯...」或「看來你還需要更多修練...」。
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        return model.generate_content(prompt, safety_settings=safety_settings).text.strip()
    except:
        return "測驗完成！"

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

st.set_page_config(page_title="神奇柑仔店 - AI 閱讀認證", page_icon="🐱")
st.title("🐱 神奇柑仔店 - AI 閱讀挑戰")

# --- 側邊欄 ---
with st.sidebar:
    st.header("系統狀態")
    if ai_available: st.success(ai_status_msg)
    else: st.error(ai_status_msg)
    st.divider()
    student_class = st.text_input("班級")
    seat_num = st.text_input("座號")
    student_name = st.text_input("姓名")
    st.divider()
    if st.text_input("老師密碼", type="password") == "1234":
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, "rb") as f: st.download_button("下載成績單", f, "scores.csv")

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 'login'
if 'answers' not in st.session_state: st.session_state.answers = []
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = {}
if 'current_q_index' not in st.session_state: st.session_state.current_q_index = 0
if 'all_questions' not in st.session_state: st.session_state.all_questions = []

# --- 流程 ---
if not (student_class and seat_num and student_name):
    st.warning("請先在左側輸入班級、座號與姓名。")
    st.stop()

if st.session_state.step == 'login':
    st.subheader(f"👋 {student_name}，歡迎來到錢天堂！")
    st.write("請選擇挑戰難度：")
    c1, c2, c3 = st.columns(3)
    if c1.button("A 一般 (初階)"): 
        st.session_state.level = "A"; st.session_state.step = 'confirm'; st.rerun()
    if c2.button("B 精熟 (中階)"): 
        st.session_state.level = "B"; st.session_state.step = 'confirm'; st.rerun()
    if c3.button("C 深刻 (高階)"): 
        st.session_state.level = "C"; st.session_state.step = 'confirm'; st.rerun()

elif st.session_state.step == 'confirm':
    st.markdown(f"### 你選擇了等級：**{st.session_state.level}**")
    st.write("準備好接受紅子老闆娘的考驗了嗎？")
    
    if st.button("🚀 進入錢天堂 (開始測驗)"):
        # 動畫區
        ani_box = st.empty()
        ani_box.image("https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif", width=300)
        
        with st.status("🧙‍♀️ 正在準備考卷...", expanded=True) as status:
            st.write("📖 閱讀故事中...")
            time.sleep(1)
            st.write("😼 召喚招財貓出題...")
            story = load_story()
            quiz = call_ai_generate_quiz(st.session_state.level, story)
            st.write("✨ 完成！")
            status.update(label="✅ 準備就緒", state="complete", expanded=False)
            time.sleep(0.5)
        
        ani_box.empty()

        # 題目處理
        st.session_state.quiz_data = quiz
        st.session_state.all_questions = []
        if "mc_questions" in quiz:
            for q in quiz['mc_questions']: st.session_state.all_questions.append({'type': 'MC', 'data': q})
        if "qa_questions" in quiz:
            for q in quiz['qa_questions']: st.session_state.all_questions.append({'type': 'QA', 'data': q})
            
        if len(st.session_state.all_questions) > 0:
            st.session_state.step = 'testing'
            st.rerun()
        else:
            st.error("出題失敗，請重試。")

elif st.session_state.step == 'testing':
    total_q = len(st.session_state.all_questions)
    current_idx = st.session_state.current_q_index
    q_data = st.session_state.all_questions[current_idx]
    
    st.progress((current_idx) / total_q)
    st.caption(f"進度：{current_idx + 1} / {total_q}")
    
    st.markdown(f"### 📝 第 {current_idx + 1} 題")
    question_text = q_data['data']['question']
    st.info(question_text)
    
    if q_data['type'] == 'MC':
        options = q_data['data']['options']
        user_ans = st.radio("請選擇答案：", options, index=None, key=f"q_{current_idx}")
        
        if st.button("送出答案"):
            if user_ans:
                st.session_state.answers.append({
                    "type": "MC", 
                    "question": question_text,
                    "user_response": user_ans, 
                    "data": q_data['data']
                })
                if current_idx + 1 < total_q:
                    st.session_state.current_q_index += 1
                    st.rerun()
                else:
                    st.session_state.step = 'calculating'
                    st.rerun()
            else:
                st.warning("請先選擇一個答案喔！")
                
    else: # QA
        user_ans = st.text_area("請輸入你的看法：", height=150, key=f"q_{current_idx}")
        if st.button("送出答案"):
            if user_ans:
                st.session_state.answers.append({
                    "type": "QA", 
                    "question": question_text,
                    "user_response": user_ans, 
                    "data": q_data['data']
                })
                if current_idx + 1 < total_q:
                    st.session_state.current_q_index += 1
                    st.rerun()
                else:
                    st.session_state.step = 'calculating'
                    st.rerun()
            else:
                st.warning("請寫下你的答案喔！")

elif st.session_state.step == 'calculating':
    ani_box = st.empty()
    ani_box.image("https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif", caption="招財貓正在仔細批改...", width=300)
    
    with st.status("👩‍🏫 紅子老師正在看你的答案...", expanded=True) as status:
        total = 0
        story = load_story()
        
        for ans in st.session_state.answers:
            if ans['type'] == 'MC':
                correct_opt_char = str(ans['data']['answer'])[0]
                user_opt_char = str(ans['user_response'])[0]
                
                is_correct = (correct_opt_char == user_opt_char)
                pts = 0
                feedback = ""
                
                if is_correct:
                    pts = 8 if st.session_state.level == "A" else 5
                    feedback = "✅ 答對了！紅子老闆娘覺得你很有眼光！"
                else:
                    st.write(f"正在分析選擇題錯誤：{ans['question'][:10]}...")
                    # 呼叫 AI 生成提示
                    feedback = call_ai_generate_hint(
                        ans['question'], 
                        ans['user_response'], 
                        correct_opt_char, 
                        ans['data']['options'],
                        story
                    )
                    feedback = "💡 " + feedback
                
                total += pts
                ans['score'] = pts
                ans['feedback'] = feedback
                
            else: # QA
                st.write(f"正在批改問答題：{ans['question'][:10]}...")
                s, f = call_ai_grade_qa(ans['question'], ans['user_response'], story)
                total += s
                ans['score'] = s
                ans['feedback'] = f
        
        status.update(label="批改完成！", state="complete")
        time.sleep(1)
    
    ani_box.empty()
    
    cmt = call_ai_final_comment(total, "", story)
    
    rec = {
        "班級": student_class, 
        "座號": seat_num, 
        "姓名": student_name, 
        "日期": datetime.datetime.now().strftime("%Y-%m-%d"), 
        "總分": total, 
        "評語": cmt
    }
    save_to_csv(rec)
    st.session_state.final_rec = rec
    st.session_state.step = 'finished'
    st.rerun()

elif st.session_state.step == 'finished':
    rec = st.session_state.final_rec
    st.balloons()
    
    st.markdown(f"# 🎉 挑戰完成！總分：{rec['總分']} 分")
    st.info(f"👩‍🏫 紅子老師的話：{rec['評語']}")
    
    st.divider()
    
    st.subheader("🧐 詳細檢討與省思")
    st.write("來看看紅子老師對每一題的建議吧！")
    
    for i, ans in enumerate(st.session_state.answers):
        score_color = "green" if ans['score'] > 0 else "red"
        title_text = f"第 {i+1} 題：{ans['question']} (:{score_color}[{ans['score']}分])"
        
        with st.expander(title_text, expanded=True):
            st.markdown(f"**你的回答：** {ans['user_response']}")
            st.markdown(f"**👩‍🏫 老師的回饋：**")
            st.info(ans['feedback'])
            
    if st.button("🔄 重新挑戰"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
