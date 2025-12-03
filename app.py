%%writefile app.py
import streamlit as st
import pandas as pd
import datetime
import os
import random

# ==========================================
# 模擬 AI 的部分 (因為測試環境還沒串接金鑰)
# ==========================================
def call_ai_generate_quiz(level, text_content):
    # 這裡未來會接真正的 AI，現在先回傳假題目給您看效果
    mock_quiz = {
        "qa_questions": [
            {"id": 1, "question": "為什麼真由美會長出魚鱗？請根據故事內容回答。", "score": 20}
        ],
        "mc_questions": [
            {"id": 1, "type": "提取訊息", "question": "真由美用什麼換到了美人魚軟糖？", "options": ["1. 100元", "2. 昭和42年的10元", "3. 一顆釦子", "4. 玩具寶石"], "answer": "2"},
            {"id": 2, "type": "推論訊息", "question": "為什麼錢天堂的老闆娘說那枚硬幣是「寶物」？", "options": ["1. 因為很亮", "2. 因為那是稀有的舊硬幣", "3. 因為老闆娘喜歡蒐集", "4. 因為那是真由美的運氣"], "answer": "2"},
            {"id": 3, "type": "推論訊息", "question": "故事中提到的「錢天堂」有什麼特徵？", "options": ["1. 在大馬路旁", "2. 只有幸運的人能找到", "3. 賣很多文具", "4. 老闆是個年輕男生"], "answer": "2"},
            {"id": 4, "type": "詮釋整合", "question": "真由美最後對游泳的看法有什麼轉變？", "options": ["1. 還是很討厭", "2. 變得喜歡且擅長", "3. 覺得無所謂", "4. 決定以後都不游了"], "answer": "2"}
        ]
    }
    
    # 根據等級微調題目量 (模擬)
    if level == "B":
        mock_quiz["qa_questions"].append({"id": 2, "question": "你認為美人魚軟糖的副作用對真由美來說是好是壞？", "score": 20})
    elif level == "C":
        mock_quiz["qa_questions"] = [
            {"id": 1, "question": "請分析真由美在吃下軟糖前後的心境變化。", "score": 20},
            {"id": 2, "question": "如果你是真由美，你會選擇吃下人體模型嗎？為什麼？", "score": 20},
            {"id": 3, "question": "這則故事想傳達的核心寓意是什麼？", "score": 20}
        ]
        
    return mock_quiz

def call_ai_grade_qa(question, student_answer, story_text):
    # 模擬評分
    return 15, "能理解故事大意，但在獨特見解部分可以多描述一點自己的看法。"

def call_ai_final_comment(total_score, qa_feedback, story_text):
    if total_score >= 80:
        return "表現優秀！你對故事細節掌握得很好，建議可以挑戰更難的書籍。"
    elif total_score >= 60:
        return "恭喜通過！你已經理解了故事大意，建議下次閱讀時多注意角色的心理變化。"
    else:
        return "很可惜這次未通過。建議重新閱讀關於「美人魚軟糖」副作用的那一段，加油！"

# ==========================================
# 系統邏輯
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
    return "（測試模式：未找到 story.txt）"

# ==========================================
# 前端介面
# ==========================================
st.set_page_config(page_title="神奇柑仔店 - 閱讀認證", page_icon="📖")
st.title("📖 神奇柑仔店 - 閱讀理解挑戰")

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

if 'step' not in st.session_state: st.session_state.step = 'login'
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = {}
if 'current_q_index' not in st.session_state: st.session_state.current_q_index = 0
if 'answers' not in st.session_state: st.session_state.answers = []
if 'history' not in st.session_state: st.session_state.history = []

if not (student_class and seat_num and student_name):
    st.warning("👈 請先在左側填寫班級、座號、姓名，才能開始喔！")
    st.stop()

if st.session_state.step == 'login':
    st.subheader(f"你好，{student_name}！準備好接受挑戰了嗎？")
    st.write("請選擇你要挑戰的等級：")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("等級 A：一般程度"):
            st.session_state.level = "A"
            st.session_state.step = 'confirm_level'
            st.rerun()
    with col2:
        if st.button("等級 B：精熟程度"):
            st.session_state.level = "B"
            st.session_state.step = 'confirm_level'
            st.rerun()
    with col3:
        if st.button("等級 C：深刻體會"):
            st.session_state.level = "C"
            st.session_state.step = 'confirm_level'
            st.rerun()

elif st.session_state.step == 'confirm_level':
    st.info(f"你選擇了等級 {st.session_state.level}，確定要開始嗎？")
    if st.button("確定，開始測驗！"):
        with st.spinner("機器人正在閱讀故事並出題中..."):
            story_text = load_story()
            quiz = call_ai_generate_quiz(st.session_state.level, story_text)
            st.session_state.quiz_data = quiz
            st.session_state.all_questions = []
            for q in quiz['qa_questions']: st.session_state.all_questions.append({'type': 'QA', 'data': q})
            for q in quiz['mc_questions']: st.session_state.all_questions.append({'type': 'MC', 'data': q})
            
            st.session_state.history.append({"role": "bot", "content": f"你好！我是閱讀認證機器人。我們將進行等級 {st.session_state.level} 的測驗。\n\n我們將一題一題進行，準備好了嗎？這是第一題："})
            
            first_q = st.session_state.all_questions[0]
            if first_q['type'] == 'QA':
                st.session_state.history.append({"role": "bot", "content": f"【問答題】 {first_q['data']['question']}"})
            else:
                options_str = "\n".join(first_q['data']['options'])
                st.session_state.history.append({"role": "bot", "content": f"【選擇題】 {first_q['data']['question']}\n{options_str}"})

            st.session_state.step = 'testing'
            st.rerun()

elif st.session_state.step == 'testing':
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]): st.write(msg["content"])
    
    current_idx = st.session_state.current_q_index
    total_q = len(st.session_state.all_questions)
    
    if current_idx < total_q:
        current_q = st.session_state.all_questions[current_idx]
        if current_q['type'] == 'QA':
            user_input = st.chat_input("請輸入你的回答...")
        else:
            user_input = st.chat_input("請輸入選項編號 (1, 2, 3, 4)")

        if user_input:
            with st.chat_message("user"): st.write(user_input)
            st.session_state.history.append({"role": "user", "content": user_input})
            st.session_state.answers.append({"question_index": current_idx, "type": current_q['type'], "user_response": user_input, "question_data": current_q['data']})
            
            next_idx = current_idx + 1
            st.session_state.current_q_index = next_idx
            
            if next_idx < total_q:
                next_q = st.session_state.all_questions[next_idx]
                bot_reply = "收到，我記錄下來了。"
                if next_q['type'] == 'QA':
                    q_content = f"【問答題】 {next_q['data']['question']}"
                else:
                    options_str = "\n".join(next_q['data']['options'])
                    q_content = f"【選擇題】 {next_q['data']['question']}\n{options_str}"
                full_reply = f"{bot_reply}\n\n下一題是：\n{q_content}"
                st.session_state.history.append({"role": "bot", "content": full_reply})
                st.rerun()
            else:
                st.session_state.step = 'calculating'
                st.rerun()

elif st.session_state.step == 'calculating':
    with st.spinner("機器人正在改考卷..."):
        story_text = load_story()
        total_score = 0
        mc_score = 0
        qa_score = 0
        for ans in st.session_state.answers:
            if ans['type'] == 'MC':
                correct_ans = str(ans['question_data']['answer'])
                user_ans = str(ans['user_response']).strip()[0]
                points_per_mc = 8
                if st.session_state.level == "B": points_per_mc = 6
                elif st.session_state.level == "C": points_per_mc = 4
                if user_ans == correct_ans:
                    total_score += points_per_mc
                    mc_score += points_per_mc
            elif ans['type'] == 'QA':
                score, feedback = call_ai_grade_qa(ans['question_data']['question'], ans['user_response'], story_text)
                total_score += score
                qa_score += score
        
        final_comment = call_ai_final_comment(total_score, "", story_text)
        record = {"班級": student_class, "座號": seat_num, "姓名": student_name, "日期": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "等級": st.session_state.level, "選擇題得分": mc_score, "問答題得分": qa_score, "總分": total_score, "機器人總評": final_comment}
        save_to_csv(record)
        st.session_state.final_result = record
        st.session_state.step = 'finished'
        st.rerun()

elif st.session_state.step == 'finished':
    res = st.session_state.final_result
    st.balloons()
    st.markdown(f"### 📄 成績單\n**姓名**：{res['姓名']} (班級: {res['班級']})\n**總分**：{res['總分']} 分")
    if res['總分'] >= 60: st.success("結果：通過認證！ 🎉")
    else: st.error("結果：未通過，請再接再厲！ 💪")
    st.info(f"**機器人評語**：\n{res['機器人總評']}")
    st.markdown("---")
    if st.button("重新開始"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()