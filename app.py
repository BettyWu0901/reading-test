import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="模型探測器", page_icon="🕵️")
st.title("🕵️ Google Gemini 模型探測器")

# 1. 取得 API Key
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 API Key，請檢查 Secrets。")
    st.stop()

genai.configure(api_key=api_key)

# 2. 列出所有可用模型
st.header("1. 你的帳號可用的模型清單")
st.info("正在詢問 Google 伺服器...")

available_models = []
try:
    # 呼叫 list_models 查看你的權限
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
            st.write(f"- `{m.name}`")
            
    if not available_models:
        st.error("❌ 你的帳號似乎沒有任何可用於 'generateContent' 的模型！")
        st.warning("請確認你在 Google AI Studio 有啟用 'Generative AI API'。")
    else:
        st.success(f"✅ 找到 {len(available_models)} 個可用模型！")

except Exception as e:
    st.error(f"❌ 無法列出模型: {e}")
    st.stop()

# 3. 自動測試哪一個會通
st.header("2. 自動連線測試")
st.write("正在從清單中尋找可以正常工作的模型...")

valid_model_name = None

# 我們優先測試這幾個常見的名稱
priority_list = [
    'models/gemini-1.5-flash',
    'models/gemini-1.5-flash-001',
    'models/gemini-1.5-flash-latest',
    'models/gemini-1.5-pro',
    'models/gemini-pro',
    'models/gemini-1.0-pro'
]

# 把優先清單和實際清單結合（避免重複）
test_list = priority_list + [m for m in available_models if m not in priority_list]

for model_name in test_list:
    # 如果這個名稱不在使用者的實際清單裡(且不是簡寫)，就跳過，節省時間
    # 但有些簡寫(如 gemini-pro)可能不在 list_models 裡但可以用，所以我們還是都測一下
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"正在測試: `{model_name}` ...")
    
    try:
        # 去掉 'models/' 前綴來建立物件，因為有時候 library 喜歡沒有前綴的
        short_name = model_name.replace("models/", "")
        model = genai.GenerativeModel(short_name)
        
        response = model.generate_content("Hello, this is a test.", request_options={"timeout": 5})
        
        with col2:
            st.success("成功！✅")
        
        st.balloons()
        st.markdown(f"### 🎉 找到了！你的正確模型名稱是： `{short_name}`")
        st.code(short_name)
        valid_model_name = short_name
        break # 找到一個能用的就停下來
        
    except Exception as e:
        with col2:
            st.error("失敗 ❌")
        # st.caption(f"錯誤: {e}") # 想看詳細錯誤可以打開這行

if not valid_model_name:
    st.error("😭 測試了所有模型都失敗了。")
    st.write("請截圖這個畫面給我。")
else:
    st.success("請告訴我上面顯示的綠色模型名稱，我幫你修改程式碼！")
