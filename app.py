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
# 2. AI 核心功能區 (完全依照規則文件設定)
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
            {"id": 1, "type": "提取訊息", "question": "真由美用什麼換到了美人魚軟糖？", "options": ["1. 100元", "2. 昭和42年的10元", "3. 釦子", "4. 寶石", "5. 貝殼", "6. 勇氣"], "answer": "2"}
        ]
    }

def call_ai_generate_quiz(level, text_content):
    if not ai_available: return get_mock_quiz()
    
    # --- 依照「閱讀認證規則.txt」設定嚴格規則 ---
    if level == "A":
        # A級: 問答1題，選擇10題(提取2/推論4/詮釋4)
        rule = """
        【等級A規則】：
        1. 問答題：出 1 題 (每題20分)。
        2. 選擇題：出 10 題 (每題8分)。包含：提取訊息2題、推論訊息4題、詮釋整合4題。
        """
    elif level == "B":
        # B級: 問答2題，選擇10題(提取1/推論3/詮釋6)
        rule = """
        【等級B規則】：
        1. 問答題：出 2 題 (每題20分)。
        2. 選擇題：出 10 題 (每題6分)。包含：提取訊息1題、推論訊息3題、詮釋整合6題。
        """
    else:
        # C級: 問答3題，選擇10題(推論3/詮釋7)
        rule = """
        【等級C規則】：
        1. 問答題：出 3 題 (每題20分)。
        2. 選擇題：出 10 題 (每題4分)。包含：推論訊息3題、詮釋整合7題。
        """

    prompt = f"""
    請你根據以下《神奇柑仔店》的故事內容，為國小學生設計一份「閱讀認證測驗」。
    【文章內容】：{text_content[:30000]} 
    
    【重要出題規則】：
    {rule}
    3. **題目順序**：JSON 中請包含 `qa_questions` (問答) 和 `mc_questions` (選擇)。
    4. **選擇題選項**：每題必須有 **6 個選項** (1~6)，且要有合理的誘答性。
    5. **題目焦點**：針對故事劇情、角色行為、寓意提問。嚴禁問教育學或評估文章的問題。
    6. **語言**：繁體中文。

    【格式要求】：請回傳純 JSON 格式。
    JSON 結構範例：
    {{
        "qa_questions": [{{"id": 1, "question": "...", "score": 20}}],
        "mc_questions": [{{"id": 1, "type": "...", "question": "...", "options": ["1. A", "2. B", "3. C", "4. D", "5. E", "6. F"], "answer": "2"}}]
    }}
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, safety_settings=safety_settings)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except:
        return get_mock_quiz()

def call_ai_generate_hint(question, wrong_answer, correct_option_index, options, story_text):
    if not ai_available: return "請再讀一次故事喔！"
    try:
        correct_answer_text = options[int(correct_option_index)-1]
    except:
        correct_answer_text = "正確答案"
    
    prompt = f"""
    學生在閱讀測驗答錯了。請扮演紅子老闆娘給予提示。
    【題目】：{question}
    【正確答案】：{correct_answer_text}
    【原則】：不直接給答案，用引導的方式。30字以內。
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
    請扮演《神奇柑仔店》紅子老闆娘批改問答題。
    【題目】：{question}
    【回答】：{student_answer}
    【標準】：滿分20分。依據：1.了解題意 2.內容正確合理 3.有獨特見解。
    【回饋】：若錯請引導，若對請稱讚。語氣神秘溫暖。
    格式：分數|評語
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
        return 10, "評分系統忙碌中。"

def call_ai_final_comment(total, level, story_text):
    if not ai_available: return "測驗完成！"
    # 根據規則文件設定的標準給評語
    if total >= 80:
        status = "表現優秀！建議挑戰更高等級！"
    elif total >= 60:
        status = "通過認證！恭喜你！"
    else:
        status = "未通過，請再努力或降級嘗試。"
        
    prompt = f"""
    學生測驗總分 {total} 分 ({status})。
    請用紅子老闆娘口吻給一句結語。
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        return model.generate_content(prompt, safety_settings=safety_settings).text.strip()
    except:
        return f"測驗結束。{status}"

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
        ani_box.image("https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif", caption="紅子老闆娘正收到訂單", width=300)
        
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

        # 題目處理：規則要求先出問答題，再出選擇題
        st.session_state.quiz_data = quiz
        st.session_state.all_questions = []
        
        # 1. 先加入問答題 (QA)
        if "qa_questions" in quiz:
            for q in quiz['qa_questions']: st.session_state.all_questions.append({'type': 'QA', 'data': q})
        
        # 2. 再加入選擇題 (MC)
        if "mc_questions" in quiz:
            for q in quiz['mc_questions']: st.session_state.all_questions.append({'type': 'MC', 'data': q})
            
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
    
    # 判斷題型顯示標題
    q_type_title = "問答題" if q_data['type'] == 'QA' else "選擇題"
    st.markdown(f"### 📝 第 {current_idx + 1} 題 ({q_type_title})")
    
    question_text = q_data['data']['question']
    st.info(question_text)
    
    if q_data['type'] == 'MC':
        options = q_data['data']['options']
        # 規則要求 6 個選項
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
                
    else: # QA 問答題
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
        
        # 設定不同等級的選擇題配分 (依照規則文件)
        mc_score_per_q = 0
        if st.session_state.level == "A": mc_score_per_q = 8
        elif st.session_state.level == "B": mc_score_per_q = 6
        else: mc_score_per_q = 4 # C級

        for ans in st.session_state.answers:
            if ans['type'] == 'MC':
                # 選擇題批改
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
                
            else: # QA 問答題批改
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
    
    # 根據分數顯示不同顏色
    score_color = "green" if rec['總分'] >= 60 else "red"
    st.markdown(f"# 🎉 挑戰完成！總分：:{score_color}[{rec['總分']} 分]")
    st.info(f"👩‍🏫 紅子老師的話：{rec['評語']}")
    
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
