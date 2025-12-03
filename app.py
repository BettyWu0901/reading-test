import streamlit as st
import pandas as pd
import datetime
import os
import json
import time
import re  # 新增：用來強力清理文字的工具

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
# 2. AI 核心功能區 (含自動修復機制)
# ==========================================

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

def get_mock_quiz():
    return {
        "qa_questions": [{"id": 1, "question": "為什麼真由美會長出魚鱗？(這是備用題庫，代表 AI 發生錯誤，請看左側邊欄)", "score": 20}],
        "mc_questions": [
            {"id": 1, "type": "提取訊息", "question": "真由美用什麼換到了美人魚軟糖？", "options": ["1. 100元", "2. 昭和42年的10元", "3. 釦子", "4. 寶石", "5. 貝殼", "6. 勇氣"], "answer": "2"}
        ]
    }

# --- 新增：強力 JSON 解析器 ---
def extract_json(text):
    """
    不管 AI 回傳什麼，嘗試從中抓出 JSON 物件。
    """
    try:
        # 1. 嘗試直接解析
        return json.loads(text)
    except:
        pass
    
    try:
        # 2. 使用正則表達式抓取第一個 { 到 最後一個 }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group()
            return json.loads(json_str)
    except:
        pass
        
    return None

def call_ai_generate_quiz(level, text_content):
    if not ai_available: return get_mock_quiz()
    
    # 依照規則設定
    if level == "A":
        rule = "問答題1題，選擇題10題。選擇題需含提取訊息與推論。"
    elif level == "B":
        rule = "問答題2題，選擇題10題。選擇題需含推論與詮釋整合。"
    else:
        rule = "問答題3題，選擇題10題。選擇題需含詮釋整合與比較評估。"

    prompt = f"""
    請閱讀以下故事，製作一份閱讀測驗 JSON。
    【文章】：{text_content[:30000]} 
    【規則】：{rule}
    【重要】：
    1. 選擇題要有 6 個選項。
    2. 先出 qa_questions (問答)，再出 mc_questions (選擇)。
    3. JSON 格式必須正確。
    
    JSON 範例：
    {{
        "qa_questions": [{{"id": 1, "question": "...", "score": 20}}],
        "mc_questions": [{{"id": 1, "type": "...", "question": "...", "options": ["1. A", "2. B", "3. C", "4. D", "5. E", "6. F"], "answer": "2"}}]
    }}
    """
    
    # --- 雙重嘗試機制 ---
    models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash']
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, safety_settings=safety_settings)
            
            # 使用強力解析器
            data = extract_json(response.text)
            if data:
                return data
            else:
                st.sidebar.warning(f"⚠️ 模型 {model_name} 回傳了非 JSON 格式，嘗試下一個...")
                
        except Exception as e:
            st.sidebar.error(f"❌ 模型 {model_name} 連線失敗: {e}")
            continue # 試下一個模型

    # 如果都失敗
    st.sidebar.error("❌ 所有 AI 模型都嘗試失敗，切換回備用題庫。")
    return get_mock_quiz()

def call_ai_generate_hint(question, wrong_answer, correct_option_index, options, story_text):
    if not ai_available: return "請再讀一次故事喔！"
    try:
        correct_answer_text = options[int(correct_option_index)-1]
    except:
        correct_answer_text = "正確答案"
    
    prompt = f"""
    閱讀測驗錯題提示。
    題目：{question}
    學生選錯：{wrong_answer}
    正確：{correct_answer_text}
    要求：引導式提示，不給答案，30字內，繁體中文。
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # 用穩定的 1.5 做小任務
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except:
        return "加油，再找找看！"

def call_ai_grade_qa(question, student_answer, story_text):
    if not ai_available: return 10, "AI 未連線。"
    prompt = f"""
    批改閱讀問答題。
    題目：{question}
    回答：{student_answer}
    標準：滿分20。
    回傳：分數|評語 (引導式，繁體中文)
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
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
    prompt = f"學生總分 {total}，請用錢天堂紅子口吻給一句評語。"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
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
        
        # 先出問答，再出選擇
        if "qa_questions" in quiz:
            for q in quiz['qa_questions']: st.session_state.all_questions.append({'type': 'QA', 'data': q})
        if "mc_questions" in quiz:
            for q in quiz['mc_questions']: st.session_state.all_questions.append({'type': 'MC', 'data': q})
            
        if len(st.session_state.all_questions) > 0:
            st.session_state.step = 'testing'
            st.rerun()
        else:
            st.error("出題失敗，請檢查側邊欄錯誤訊息。")

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
