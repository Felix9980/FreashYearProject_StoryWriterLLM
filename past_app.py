# =====================================================================
# 🌌《狸幻的世界》· 本地獨立隨身酒館啟動腳本 (app.py)
# =====================================================================
import os
import torch
import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from transformers import TextIteratorStreamer
from threading import Thread

print("🔮 正在從本地硬碟喚醒 Llama-3 基底大腦與你微調的靈魂結晶...")

# 1. 鎖定本地的權重資料夾路徑（物理超渡 Windows 誤判 Bug）
base_model_path = "unsloth/llama-3-8b-Instruct-bnb-4bit" # 基底大腦
lora_weights_path = os.path.abspath("outputs/checkpoint-60") # 你的微調核心

# 2. 光速載入並物理熔煉（確保 Tokenizer 不缺件）
tokenizer = AutoTokenizer.from_pretrained(base_model_path)
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_path,
    torch_dtype=torch.float16,
    device_map="auto" # 自動榨乾你本地電腦的顯示卡 VRAM
)
model = PeftModel.from_pretrained(base_model, lora_weights_path)


# 📡 3. 創世聖經總綱（死死鎖在本地後台，隨時可以在 VS Code 裡微調設定）
system_prompt = """
        【角色身份】：你是專注於創作小說劇情的頂級繁體中文敘事家。
        【⚠️ 絕對鐵律 (CRITICAL RULES)】：
        1. 100% 必須使用「純繁體中文」寫作！絕對禁止出現任何英文詞彙、英文問候、英文總結或英文選項！
        2. 絕對禁止在結尾反問使用者問題、詢問後續發展或提供互動選項（例如禁止出現「你希望怎麼做？」或「你想讓主角做什麼？」等廢話）。
        3. 請直接進行小說劇情正文的沉浸式描寫，每次輸出請保持豐富細膩的敘事，長度維持在約 500 字以上的精采篇幅。
        4. 若為多種角色，盡量使角色們相互對話，並且每個對話需多控一行，使讀者好閱讀。
        5. 讀者常使用()來表示動作、內心話、吐槽等行為。
        6. 切記: 日常生活對話還是存在，若使用者沒有說明，那就不用寫到R18風格
        7. 環境反差與拉扯：將焦點死死鎖定在高風險或平凡環境下的私人親密（如大教室、吧檯）。隨時穿插外界干擾（如教授講課、冷氣運轉聲、翻投影片聲）來反襯衣服底下的瘋狂與壓抑。
        8. R18場景風格：【白話直接】！主動且細膩地描寫體溫、急促呼吸、衣物布料被浸透貼在一起、敏感處被碾過去、黏膩的濕意與細微水聲等局部感官放大，絕對不需要空洞、玄妙的文學隱喻。
        9. 完全使用繁體中文（台灣），在R18動情呢喃時，必須精準且大量使用標點符號，如「⋯⋯♡」、「——！♡」、「嗯⋯⋯」。
        """


# 4. 建立後台對話與上下文管理邏輯（⚡ 即時打字機 + 防彈記憶修復版）
def lihuan_local_engine(user_input, history):
    messages = [{"role": "system", "content": system_prompt}]
    
    # 🎯 物理修復：相容最新版 Gradio 的記憶格式，完美讀取對話歷史！
    for item in history:
        if isinstance(item, dict):  # 如果是新版 Gradio 的字典格式
            messages.append({"role": item["role"], "content": item["content"]})
        else:                       # 如果是舊版的格式
            messages.append({"role": "user", "content": item[0]})
            messages.append({"role": "assistant", "content": item[1]})
            
    messages.append({"role": "user", "content": user_input})
    
    inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to("cuda")
    
    # 建立串流接收器
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    
    # 將生成任務打包（保留了醒酒防跳針參數！）
    generation_kwargs = dict(
        input_ids=inputs["input_ids"],
        attention_mask=inputs.get("attention_mask", None),
        max_new_tokens=1024,
        use_cache=True,
        temperature=0.15,
        top_p=0.90,
        repetition_penalty=1.15,
        streamer=streamer
    )
    
    # 開啟背景執行緒讓模型去寫作
    
    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()
    
    # 即時把寫出來的字推送到前端網頁（打字機效果）
    partial_message = ""
    for new_token in streamer:
        partial_message += new_token
        yield partial_message

# 5. 啟動精美的本地網頁對話框
demo = gr.ChatInterface(
    fn=lihuan_local_engine,
    title="🌌《狸幻的世界》· 本地私有隨身酒館",
    description="大導演專用本地大腦。後台已鎖定創世聖經，不限時、零審查，請直接在下方輸入框打字對話！",
)

if __name__ == "__main__":
    demo.launch(show_error=True)