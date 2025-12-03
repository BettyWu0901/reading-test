import streamlit as st
import pandas as pd
import datetime
import os
import json
import google.generativeai as genai

# ==========================================
# 1. 設定 AI (讀取保險箱裡的鑰匙)
# ==========================================
# 嘗試從 Streamlit Secrets 讀取金鑰
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        ai_available = True
    else:
        ai_available = False
except FileNotFoundError:
    ai_available = False

# ==========================================
# 2. AI 核心功能區
# ==========================================

def call_ai_generate_quiz(level, text_content):
    """
    呼叫 Google Gemini 閱讀文章並出題
    """
    if not ai_available:
        return get_mock_quiz() # 如果沒鑰匙，就用舊的假題目避免當機

    # 依照等級設定出題規則
    if level == "A":
        rule = "出題規則：適合一般程度。需包含：提取訊息2題、推論訊息4題、詮釋整合或比較評估4題。問答題1題。"
    elif level == "B":
        rule = "出題規則：適合精熟程度。需包含：提取訊息1題、推論訊息3題、詮釋整合或比較評估6題。問答題2題。"
    else: # Level C
        rule = "出題規則：適合深刻體會程度。需包含：推論訊息3題、詮釋整合或比較評估7題。問答題3題。"

    prompt = f"""
    你是一位專業的國小閱讀素養出題老師。請閱讀以下文章，並依照規則產出一份測驗卷。
    
    【文章內容】：
    {text_content[:15000]} 
    (若文章過長請只讀前15000字)

    【{rule}】
    
    【重要格式要求】：
    請直接回傳一個合法的 JSON 格式，不要有任何 Markdown 標記（不要寫 ```json）。
    JSON 結構必須如下：
    {{
        "qa_questions": [
            {{"id": 1, "question": "問答題題目...", "score": 20}},
            ...
        ],
        "mc_questions": [
            {{"id": 1, "type": "提取訊息", "question": "選擇題題目...", "options": ["1. 選項A", "2. 選項B", "3. 選項C", "4. 選項D"], "answer": "正確選項的編號(例如 2)"}},
            ...
        ]
    }}
    請確保選擇題有 4 個選項。
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        # 清理回應，確保是純 JSON
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        quiz_json = json.loads(clean_text)
        return quiz_json
    except Exception as e:
        st.error(f"AI 出題時發生錯誤，改為使用備用題庫。錯誤原因：{e}")
        return get_mock_quiz()

def call_ai_grade_qa(question, student_answer, story_text):
    """
    呼叫 AI 評分問答題
    """
    if not ai_available:
        return 15, "（模擬評分）寫得不錯！但請記得我們現在還沒接上真 AI 喔。"

    prompt = f"""
    你是國小閱讀老師。請針對學生的回答進行評分。
    
    題目：{question}
    學生回答：{student_answer}
    文章背景：請依據剛才閱讀的故事內容。
    
    【評分標準 (滿分20分)】：
    1. 了解題意 (0-6分)
    2. 內容正確合理 (0-6分)
    3. 獨特見解與創意 (0-8分)
    
    請回傳格式：
    分數|評語
    (例如：16|你能理解故事，但在創意部分可以再多一點想法。)
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "|" in text:
            score_str, feedback = text.split("|", 1)
            return int(float(score_str)), feedback
        else:
            return 10, text # 格式跑掉時的預設處理
    except:
        return 10, "AI 評分連線忙碌中，給予基本分。"

def call_ai_final_comment(total_score, qa_feedback, story_text):
    if not ai_available:
        return "模擬總評：恭喜完成測驗！"
        
    prompt = f"""
    學生完成了閱讀測驗，總分是 {total_score} 分。
    請給學生一段 50 字以內的繁體中文鼓勵評語，語氣要溫柔、正向，像一位親切的老師。
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "測驗完成！繼續加油！"

def get_mock_quiz():
    """備用題庫 (當 AI 連線失敗時使用)"""
    return {
        "qa_questions": [{"id": 1, "question": "為什麼真由美會長出魚鱗？(備用題庫)", "score": 20}],
        "mc_questions": [
            {"id": 1, "type": "提取訊息", "question": "真由美用什麼換到了美人魚軟糖？", "options": ["1. 100元", "2. 昭和42年的10元", "3. 釦子", "4. 寶石"], "answer": "2"},
            {"id": 2, "type": "推論訊息", "question": "錢天堂有什麼特徵？", "options": ["1. 在大馬路旁", "2. 只有幸運的人能找到", "3. 賣文具", "4. 老闆是男生"], "answer": "2"}
        ]
    }

# ==========================================
# 3. 系統與介面 (這裡大部分不用動)
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
        with open("story.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "找不到 story.txt，請確認檔案是否存在。"

st.set_page_config(page_title="神奇柑仔店 - AI 閱讀認證", page_icon="🤖")
st.title("🤖 神奇柑仔店 - AI 閱讀挑戰")

if not ai_available:
    st.warning("⚠️ 尚未偵測到 API Key，系統目前為「模擬模式」。請老師到 Streamlit Secrets 設定 GEMINI_API_KEY。")

# --- 側邊欄 ---
with st.sidebar:
    st.header("1. 學生資料登入")
    student_class = st.text_input("班級", placeholder="例如：501")
    seat_num = st.text_input("座號", placeholder="例如：05")
    student_name = st.text_input("姓名", placeholder="王小明")
    st.markdown("---")
    st.header("2. 老師專區")
    password = st.text_input("輸入密碼下載報表", type="password")
    if password == "1234":
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, "rb") as f:
                st.download_button("下載 Excel (CSV)", f, file_name="student_scores.csv")
        else:
            st.info("目前還沒有資料喔！")

# --- 初始化 ---
if 'step' not in st.session_state: st.session_state.step = 'login'
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = {}
if 'current_q_index' not in st.session_state: st.session_state.current_q_index = 0
if 'answers' not in st.session_state: st.session_state.answers = []
if 'history' not in st.session_state: st.session_state.history = []

# --- 流程控制 ---
if not (student_class and seat_num and student_name):
    st.warning("👈 請先輸入班級、座號、姓名")
    st.stop()

if st.session_state.step == 'login':
    st.subheader(f"👋 {student_name} 你好！")
    st.write("請選擇挑戰等級：")
    c1, c2, c3 = st.columns(3)
    if c1.button("等級 A (一般)"): 
        st.session_state.level = "A"
        st.session_state.step = 'confirm_level'
        st.rerun()
    if c2.button("等級 B (精熟)"): 
        st.session_state.level = "B"
        st.session_state.step = 'confirm_level'
        st.rerun()
    if c3.button("等級 C (深刻)"): 
        st.session_state.level = "C"
        st.session_state.step = 'confirm_level'
        st.rerun()

elif st.session_state.step == 'confirm_level':
    st.info(f"你選擇了等級 {st.session_state.level}，AI 老師正在讀書出題，請稍等...")
    if st.button("開始測驗"):
        with st.spinner("AI 正在閱讀《神奇柑仔店》並生成題目中... (約需 10-20 秒)"):
            story_text = load_story()
            quiz = call_ai_generate_quiz(st.session_state.level, story_text)
            st.session_state.quiz_data = quiz
            st.session_state.all_questions = []
            
            # 整合題目
            if "qa_questions" in quiz:
                for q in quiz['qa_questions']: 
                    st.session_state.all_questions.append({'type': 'QA', 'data': q})
            if "mc_questions" in quiz:
                for q in quiz['mc_questions']: 
                    st.session_state.all_questions.append({'type': 'MC', 'data': q})
            
            # 開場白
            st.session_state.history = []
            st.session_state.history.append({"role": "bot", "content": f"你好！我是 AI 閱讀老師。我剛剛讀完了這本書，現在要來考考你。\n\n我們一題一題來，準備好了嗎？"})
            
            # 第一題
            if len(st.session_state.all_questions) > 0:
                first_q = st.session_state.all_questions[0]
                if first_q['type'] == 'QA':
                    st.session_state.history.append({"role": "bot", "content": f"【問答題】 {first_q['data']['question']}"})
                else:
                    opts = "\n".join(first_q['data']['options'])
                    st.session_state.history.append({"role": "bot", "content": f"【選擇題】 {first_q['data']['question']}\n{opts}"})
                st.session_state.step = 'testing'
                st.rerun()
            else:
                st.error("AI 出題失敗，請重新整理試試看。")

elif st.session_state.step == 'testing':
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]): st.write(msg["content"])
    
    current_idx = st.session_state.current_q_index
    total_q = len(st.session_state.all_questions)
    
    if current_idx < total_q:
        q_data = st.session_state.all_questions[current_idx]
        if q_data['type'] == 'QA':
            user_input = st.chat_input("請輸入回答...")
        else:
            user_input = st.chat_input("請輸入選項編號 (例如: 2)")

        if user_input:
            with st.chat_message("user"): st.write(user_input)
            st.session_state.history.append({"role": "user", "content": user_input})
            st.session_state.answers.append({
                "type": q_data['type'], 
                "user_response": user_input, 
                "question_data": q_data['data']
            })
            
            next_idx = current_idx + 1
            st.session_state.current_q_index = next_idx
            
            if next_idx < total_q:
                next_q = st.session_state.all_questions[next_idx]
                if next_q['type'] == 'QA':
                    content = f"【問答題】 {next_q['data']['question']}"
                else:
                    opts = "\n".join(next_q['data']['options'])
                    content = f"【選擇題】 {next_q['data']['question']}\n{opts}"
                
                bot_msg = f"收到！\n\n下一題：\n{content}"
                st.session_state.history.append({"role": "bot", "content": bot_msg})
                st.rerun()
            else:
                st.session_state.step = 'calculating'
                st.rerun()

elif st.session_state.step == 'calculating':
    with st.spinner("AI 老師正在改考卷...請稍等..."):
        story_text = load_story()
        total = 0
        mc_score = 0
        qa_score = 0
        
        for ans in st.session_state.answers:
            if ans['type'] == 'MC':
                # 簡單比對第一個字元
                user_ans = str(ans['user_response']).strip()[0]
                correct = str(ans['question_data']['answer']).strip()[0]
                
                # 配分邏輯
                pts = 8 # A
                if st.session_state.level == "B": pts = 6
                elif st.session_state.level == "C": pts = 4
                
                if user_ans == correct:
                    total += pts
                    mc_score += pts
            elif ans['type'] == 'QA':
                score, fb = call_ai_grade_qa(ans['question_data']['question'], ans['user_response'], story_text)
                total += score
                qa_score += score
        
        final_cmt = call_ai_final_comment(total, "", story_text)
        
        rec = {
            "班級": student_class,
            "座號": seat_num,
            "姓名": student_name,
            "日期": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "等級": st.session_state.level,
            "選擇題得分": mc_score,
            "問答題得分": qa_score,
            "總分": total,
            "機器人總評": final_cmt
        }
        save_to_csv(rec)
        st.session_state.final_result = rec
        st.session_state.step = 'finished'
        st.rerun()

elif st.session_state.step == 'finished':
    res = st.session_state.final_result
    st.balloons()
    st.markdown(f"### 📄 成績單\n**姓名**：{res['姓名']}\n**總分**：{res['總分']} 分")
    if res['總分'] >= 60: st.success("通過認證！ 🎉")
    else: st.error("未通過，再加油！ 💪")
    st.info(f"**AI 老師評語**：\n{res['機器人總評']}")
    
    if st.button("重新開始"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
