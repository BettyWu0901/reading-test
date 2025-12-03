import streamlit as st
import pandas as pd
import datetime
import os
import json
import time
import re

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
# 2. AI 核心功能區 (穩定版)
# ==========================================

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

def get_mock_quiz():
    return {
        "qa_questions": [{"id": 1, "question": "為什麼真由美會長出魚鱗？(這是備用題庫，代表 AI 連線逾時或格式錯誤，請重試)", "score": 20}],
        "mc_questions": [
            {"id": 1, "type": "提取訊息", "question": "真由美用什麼換到了美人魚軟糖？", "options": ["1. 100元", "2. 昭和42年的10元", "3. 釦子", "4. 寶石", "5. 貝殼", "6. 勇氣"], "answer": "2"}
        ]
    }

def extract_json(text):
    try:
        return json.loads(text)
    except:
        pass
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group()
            return json.loads(json_str)
    except:
        pass
    return None

def call_ai_generate_quiz(level, text_content):
    if not ai_available: return get_mock_quiz()
    
    if level == "A":
        rule = """【等級A (一般) 規則】：1. 問答題 1 題 (20分)。2. 選擇題 10 題 (8分)。包含：提取訊息2題、推論訊息4題、詮釋整合4題。"""
    elif level == "B":
        rule = """【等級B (精熟) 規則】：1. 問答題 2 題 (20分)。2. 選擇題 10 題 (6分)。包含：提取訊息1題、推論訊息3題、詮釋整合6題。"""
    else:
        rule = """【等級C (深刻) 規則】：1. 問答題 3 題 (20分)。2. 選擇題 10 題 (4分)。包含：推論訊息3題、詮釋整合7題。"""

    prompt = f"""
    請你根據以下故事內容，為國小學生設計一份「閱讀認證測驗」。
    【文章內容】：{text_content[:30000]} 
    
    【重要出題規則】：
    {rule}
    3. **語言**：全程使用繁體中文。
    4. **選擇題選項**：每題必須有 6 個選項 (1~6)。
    5. **題目焦點**：針對故事劇情、角色行為、寓意提問。嚴禁問評估文章的問題。

    【格式要求】：請回傳純 JSON 格式。
    """
    
    try:
        # 使用你帳號唯一可用的 gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        data = extract_json(response.text)
        if data:
            return data
        else:
            st.sidebar.error("⚠️ AI 回傳格式錯誤，無法解析題目。")
            return get_mock_quiz()
            
    except Exception as e:
        st.sidebar.error(f"⚠️ AI 連線發生錯誤: {e}")
        return get_mock_quiz()

def call_ai_generate_hint(question, wrong_answer, correct_option_index, options, story_text):
    if not ai_available: return "請再讀一次故事喔！"
    try:
        correct_answer_text = options[int(correct_option_index)-1]
    except:
        correct_answer_text = "正確答案"
    
    prompt = f"""
    請扮演紅子老闆娘給予提示。
    【題目】：{question}
    【正確答案】：{correct_answer_text}
    【原則】：不直接給答案，用引導的方式。**請用繁體中文回覆，嚴禁使用日文。** 30字以內。
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except:
        return "再仔細想想故事細節喔！"

def call_ai_grade_qa(question, student_answer, story_text):
    if not ai_available: return 10, "AI 未連線。"
    
    prompt = f"""
    請扮演《神奇柑仔店》的紅子老闆娘批改問答題。
    【題目】：{question}
    【回答】：{student_answer}
    【評分標準】：滿分20分。依據：1.了解題意 2.內容正確 3.有獨特見解。
    【回饋原則】：若錯請引導，若對請稱讚。**請用繁體中文回覆，嚴禁使用日文。**
    格式：分數|評語
    """
    try:
        # --- 雙重檢查確保格式正確 ---
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        text = response.text.strip()
        
        if "|" in text:
            s, f = text.split("|", 1)
            # 確保分數是數字
            if s.strip().isdigit():
                return int(s.strip()), f.strip()
        
        # 如果格式不符或 AI 忙碌，給予通用回饋
        return 10, "評分系統忙碌中。 (已獲取部分分數)"
    except Exception:
        # 如果連線失敗，回傳預設分數
        return 10, "評分系統連線失敗，請重試。"

def call_ai_final_comment(total, level, story_text):
    if not ai_available: return "測驗完成！"
    
    # 這裡確保了你喜歡的溫暖鼓勵風格
    prompt = f"""
    你是一位溫暖的老師。學生在閱讀測驗中獲得了 {total} 分 (滿分100)。
    請給予一句簡短、溫暖的繁體中文評語，肯定學生的努力和實力。**嚴禁使用日文。**
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except:
        return "測驗結束，你做得很好！繼續加油！"

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
        ani_box = st.empty()
        ani_box.image("https://media.giphy.com/media/l1KtXm1qo1d3f5FzW/giphy.gif", caption="正全速前往錢天堂...", width=300)
        
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

        st.session_state.quiz_data = quiz
        st.session_state.all_questions = []
        
        # 依照規則：先 QA 再 MC
        if "qa_questions" in quiz:
            for q in quiz['qa_questions']: st.session_state.all_questions.append({'type': 'QA', 'data': q})
        if "mc_questions" in quiz:
            for q in quiz['mc_questions']: st.session_state.all_questions.append({'type': 'MC', 'data': q})
            
        if len(st.session_state.all_questions) > 0:
            st.session_state.step = 'testing'
            st.rerun()
        else:
            st.error("出題失敗，請重試或檢查側邊欄錯誤訊息。")

elif st.session_state.step == 'testing':
    total_q = len(st.session_state.all_questions)
    current_idx = st.session_state.current_q_index
    q_data = st.session_state.all_questions[current_idx]
    
    st.progress((current_idx) / total_q)
    st.caption(f"進度：{current_idx + 1} / {total_q}")
    
    q_type_title = "問答題" if q_data['type'] == 'QA' else "選擇題"
    st.markdown(f"### 📝 第 {current_idx + 1} 題 ({q_type_title})")
    
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
    ani_box.image("https://media.giphy.com/media/l1KtXm1qo1d3f5FzW/giphy.gif", caption="招財貓正在仔細批改...", width=300)
    
    with st.status("👩‍🏫 紅子老師正在看你的答案...", expanded=True) as status:
        total = 0
        story = load_story()
        
        mc_score_per_q = 0
        if st.session_state.level == "A": mc_score_per_q = 8
        elif st.session_state.level == "B": mc_score_per_q = 6
        else: mc_score_per_q = 4

        for ans in st.session_state.answers:
            if ans['type'] == 'MC':
                try:
                    correct_opt_char = str(ans['data']['answer'])[0]
                    user_opt_char = str(ans['user_response'])[0]
                except:
                    correct_opt_char = "X"
                    user_opt_char = "Y"
                
                is_correct = (correct_opt_char == user_opt_char)
                pts = 0
                feedback = ""
                
                if is_correct:
                    pts = mc_score_per_q
                    feedback = "✅ 答對了！紅子老闆娘覺得你很有眼光！"
                else:
                    st.write(f"正在分析選擇題錯誤：{ans['question'][:10]}...")
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
    
    cmt = call_ai_final_comment(total, st.session_state.level, story)
    
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
    
    score_color = "green" if rec['總分'] >= 60 else "red"
    st.markdown(f"# 🎉 測驗完成！總分：:{score_color}[{rec['總分']} 分]")
    st.info(f"AI 老師評語：{rec['評語']}")
    
    st.divider()
    
    st.subheader("🧐 詳細檢討與省思")
    st.write("來看看紅子老師對每一題的建議吧！")
    
    for i, ans in enumerate(st.session_state.answers):
        s_color = "green" if ans['score'] > 0 else "red"
        q_type = "(問答)" if ans['type'] == 'QA' else "(選擇)"
        title_text = f"第 {i+1} 題 {q_type}：{ans['question']} (:{s_color}[{ans['score']}分])"
        
        with st.expander(title_text, expanded=True):
            st.markdown(f"**你的回答：** {ans['user_response']}")
            st.markdown(f"**👩‍🏫 老師的回饋：**")
            st.info(ans['feedback'])
            
    if st.button("🔄 重新挑戰"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
