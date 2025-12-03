import streamlit as st
import os
import google.generativeai as genai
import json

st.set_page_config(page_title="超級診斷模式", page_icon="🚑")
st.title("🚑 系統超級診斷模式")

# 1. 檢查 story.txt 是否存在
st.header("1. 檔案檢查")
if os.path.exists("story.txt"):
    size = os.path.getsize("story.txt")
    st.success(f"✅ story.txt 存在，大小為 {size} bytes")
    with open("story.txt", "r", encoding="utf-8") as f:
        story_content = f.read()
else:
    st.error("❌ 嚴重錯誤：找不到 'story.txt'！")
    st.warning("請確認你有將 story.txt 上傳到 GitHub 的儲存庫中。")
    story_content = ""
    st.stop() # 檔案不在就停下來

# 2. 檢查 API Key
st.header("2. API 連線測試")
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Secrets 裡找不到 GEMINI_API_KEY")
    st.stop()
else:
    st.success("✅ 讀取到 API Key (長度正確)")
    genai.configure(api_key=api_key)

# 3. 測試 AI 回應 (顯示原始錯誤)
st.header("3. AI 呼叫測試")
if st.button("開始測試 AI 連線"):
    st.info("正在呼叫 gemini-1.5-flash...")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 簡單的測試提示
        prompt = f"""
        請閱讀以下文章的前 500 字，並產生 1 個簡單的問答題 JSON 格式。
        文章：{story_content[:500]}
        格式範例：{{"question": "..."}}
        """
        
        response = model.generate_content(prompt)
        
        st.subheader("🎉 原始回應內容 (Raw Response):")
        st.code(response.text)
        
        # 嘗試解析 JSON
        try:
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_text)
            st.success("✅ JSON 解析成功！結構如下：")
            st.json(data)
            st.balloons()
            st.markdown("### 結論：你的 API 和程式碼都正常！")
            st.markdown("如果是這樣，請換回原本的完整程式碼，問題可能出在故事太長或格式不穩定。")
            
        except json.JSONDecodeError as je:
            st.error(f"❌ JSON 解析失敗: {je}")
            st.warning("AI 回傳了不是標準 JSON 的文字，可能是被過濾了或格式跑掉。")
            
    except Exception as e:
        st.error("❌ AI 呼叫發生致命錯誤：")
        st.error(f"{str(e)}")
        st.markdown("---")
        st.write("如果是 `404` -> 模型名稱錯誤")
        st.write("如果是 `403` -> API Key 權限錯誤")
        st.write("如果是 `429` -> 請求太頻繁 (請等一下再試)")
        st.write("如果是 `500` -> Google 伺服器忙碌")
