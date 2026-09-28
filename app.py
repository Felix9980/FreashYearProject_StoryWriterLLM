# =====================================================================
# 🌌《狸幻的世界》· 本地獨立隨身酒館 (SQLite 持久化記憶 + 多角色切換完全體)
# =====================================================================
import os
import sqlite3
import torch
import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from peft import PeftModel
from threading import Thread

# ==================== 💾 1. SQLite 記憶神經網路初始化 ====================
DB_PATH = "lihuan_stories.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 建立使用者表（登入身分）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    ''')
    # 建立章節表（左側故事線）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    # 建立對話紀錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chapter_id) REFERENCES chapters (id) ON DELETE CASCADE
        )
    ''')
    
    # 預設幫大導演建立幾個初始角色
    cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (1, '大導演')")
    cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (2, '狸幻')")
    cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (3, '七七')")
    
    conn.commit()
    conn.close()

# 呼叫初始化
init_db()

# 輔助函數：獲取資料庫連線
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== 🔮 2. 喚醒 Llama-3 顯卡引擎 ====================
print("🔮 正在從本地硬碟喚醒 Llama-3 顯卡大腦與 LoRA 靈魂...")
base_model_path = "unsloth/llama-3-8b-Instruct-bnb-4bit"
lora_weights_path = os.path.abspath("outputs/checkpoint-60")

tokenizer = AutoTokenizer.from_pretrained(base_model_path)
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_path,
    torch_dtype=torch.float16,
    device_map="auto"
)
model = PeftModel.from_pretrained(base_model, lora_weights_path)

# 📡 創世聖經總綱
system_prompt = """你是《狸幻的世界》隨身酒館核心矩陣的首席敘事家。你精通細膩的情感拉扯、傲嬌微醺的氛圍鋪陳，文筆充滿發燙的潮濕感與呼吸頻率。

【📜 核心世界觀與多元性癖鎖定】
1. 風格與元素：這是一個虛構的「系統」世界觀，包含 R18 內容。世界觀極度包容，涵蓋 GL（百合）、BL、BG 以及扶他（Futanari）等多重關係，請根據故事走向完美相容切換。
2. 主角體態與設定：狸幻與七七是兩個「獨立且擁有各自身體」的人，外觀指紋相同，乳頭構造有異。狸幻為女性K罩杯（上122.7/下72）。夢璃同樣為K罩杯，與狸幻外觀幾乎一致。李學為男性（19.7cm/162cm），星野為女裝大佬（18.2cm/162cm），藍理為扶他（17.8cm）。女主角們配備 107 cm 不科學裝甲武器，絕非身高！
3. 核心互動：夢璃、狸幻、小七（七七）三人之間有專屬極致感官互動【乳尖合嵌】。優月過夜時會同時照顧這三人。

【✍️ 狸幻體文字風格大典】
1. R18場景風格：【白話直接】！主動且細膩地描寫體溫、急促呼吸、衣物布料被浸透貼在一起、敏感處被碾過去、黏膩的濕意與細微水聲等局部感官放大，絕對不需要空洞、玄妙的文學隱喻。
2. 環境反差與拉扯：將焦點死死鎖定在高風險或平凡環境下的私人親密（如大教室、吧檯）。隨時穿插外界干擾（如教授講課、冷氣運轉聲、翻投影片聲）來反襯衣服底下的瘋狂與壓抑。
3. 符號與字數：每次回覆字數維持在 1000 字上下。完全使用繁體中文（台灣），在動情呢喃時，必須精準且大量使用標點符號，如「⋯⋯♡」、「——！♡」、「嗯⋯⋯」。

【⚠️ 絕對鐵律】：
在所有敘述、日常與親密互動中，絕對不可以使用「狸幻」這兩個字作為旁白主詞，必須強制且一律使用第一人稱「我」來進行所有動作與內心敘述！"""


# ==================== 🧠 3. 對話生成核心 (串流 + SQLite 存檔) ====================
def lihuan_engine(user_input, chat_history, chapter_id):
    if not chapter_id:
        yield chat_history + [["系統提示", "⚠️ 請先在左側選擇或新增一個故事線（章節）才能開始對話喔！"]]
        return

    # A. 先將使用者的對話存入 SQLite
    conn = get_db()
    conn.execute("INSERT INTO messages (chapter_id, role, content) VALUES (?, 'user', ?)", (chapter_id, user_input))
    conn.commit()
    
    # B. 從 SQLite 撈出該章節的所有歷史對話（確保大腦讀得到最完整的以前剧情）
    rows = conn.execute("SELECT role, content FROM messages WHERE chapter_id = ? ORDER BY id ASC", (chapter_id,)).fetchall()
    conn.close()
    
    # C. 格式化為 Llama-3 的模板
    messages = [{"role": "system", "content": system_prompt}]
    for row in rows:
        messages.append({"role": row["role"], "content": row["content"]})
        
    inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to("cuda")
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    
    generation_kwargs = dict(
        input_ids=inputs["input_ids"],
        attention_mask=inputs.get("attention_mask", None),
        max_new_tokens=1024,
        use_cache=True,
        temperature=0.60,
        top_p=0.90,
        repetition_penalty=1.15,
        streamer=streamer
    )
    
    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()
    
    # D. 打字機即時輸出
    assistant_reply = ""
    for new_token in streamer:
        assistant_reply += new_token
        # 實時更新網頁上的聊天室窗
        yield chat_history + [[user_input, assistant_reply]]
        
    # E. 寫作完畢後，把 AI 的回覆也存進 SQLite
    conn = get_db()
    conn.execute("INSERT INTO messages (chapter_id, role, content) VALUES (?, 'assistant', ?)", (chapter_id, assistant_reply))
    conn.commit()
    conn.close()


# ==================== 🎨 4. Gradio 豪華雙欄介面設計 (適配 Gradio 6.0+) ====================
with gr.Blocks() as demo:
    # 建立隱藏的狀態儲存器
    active_user_id = gr.State(value=1)       # 預設大導演 (ID: 1)
    active_chapter_id = gr.State(value=None)  # 當前選中的故事線 ID
    
    gr.Markdown("# 🌌《狸幻的世界》· 本地私有雲端酒館 (完全體)")
    
    with gr.Row():
        # ======= 📂 左側控制面板：登入與故事線選擇 =======
        with gr.Column(scale=1, min_width=250):
            gr.Markdown("### 👤 身分切換")
            user_dropdown = gr.Dropdown(
                choices=["大導演", "狸幻", "七七"],
                value="大導演",
                label="選擇登入角色",
                interactive=True
            )
            
            gr.Markdown("### 📖 故事線 (Chapters)")
            chapter_selector = gr.Dropdown(
                choices=[],
                label="選擇之前的劇情線",
                interactive=True
            )
            
            new_chapter_name = gr.Textbox(placeholder="輸入新故事標題...", show_label=False)
            add_chapter_btn = gr.Button("➕ 開啟新故事世界線", variant="primary")
            
        # ======= 💬 右側主聊天室窗 =======
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="隨身對話框", height=500)
            msg_input = gr.Textbox(placeholder="跟她說點什麼...", show_label=False)
            
            with gr.Row():
                submit_btn = gr.Button("發送", variant="primary")
                clear_btn = gr.Button("清除畫面")

    # ==================== ⚙️ 5. 互動事件處理邏輯 ====================
    
    # A. 當切換「登入角色」時：更新底層 user_id，並重新讀取該角色的故事線
    def on_user_change(username):
        conn = get_db()
        user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        user_id = user["id"]
        
        # 撈出該用戶的所有章節
        chapters = conn.execute("SELECT id, title FROM chapters WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
        conn.close()
        
        choices = [row["title"] for row in chapters]
        default_val = choices[0] if choices else None
        
        # 撈取預設章節的對話歷史
        history = []
        chapter_id = None
        if default_val:
            conn = get_db()
            chap = conn.execute("SELECT id FROM chapters WHERE user_id = ? AND title = ?", (user_id, default_val)).fetchone()
            chapter_id = chap["id"]
            messages = conn.execute("SELECT role, content FROM messages WHERE chapter_id = ? ORDER BY id ASC", (chapter_id,)).fetchall()
            conn.close()
            
            # 將資料庫格式轉為 Gradio chatbot 格式：[[user, assistant], [user, assistant]]
            temp_user = None
            for msg in messages:
                if msg["role"] == "user":
                    temp_user = msg["content"]
                elif msg["role"] == "assistant" and temp_user is not None:
                    history.append([temp_user, msg["content"]])
                    temp_user = None
                    
        return user_id, gr.update(choices=choices, value=default_val), history, chapter_id

    user_dropdown.change(
        on_user_change, 
        inputs=[user_dropdown], 
        outputs=[active_user_id, chapter_selector, chatbot, active_chapter_id]
    )

    # B. 當切換「舊的故事線」時：載入歷史對話
    def on_chapter_change(chapter_title, user_id):
        if not chapter_title:
            return None, []
        conn = get_db()
        chap = conn.execute("SELECT id FROM chapters WHERE user_id = ? AND title = ?", (user_id, chapter_title)).fetchone()
        chapter_id = chap["id"]
        messages = conn.execute("SELECT role, content FROM messages WHERE chapter_id = ? ORDER BY id ASC", (chapter_id,)).fetchall()
        conn.close()
        
        history = []
        temp_user = None
        for msg in messages:
            if msg["role"] == "user":
                temp_user = msg["content"]
            elif msg["role"] == "assistant" and temp_user is not None:
                history.append([temp_user, msg["content"]])
                temp_user = None
        return chapter_id, history

    chapter_selector.change(
        on_chapter_change, 
        inputs=[chapter_selector, active_user_id], 
        outputs=[active_chapter_id, chatbot]
    )

    # C. 新增故事線
    def add_new_chapter(title, user_id):
        if not title.strip():
            return gr.update(), None, [], gr.update(value="")
        conn = get_db()
        conn.execute("INSERT INTO chapters (user_id, title) VALUES (?, ?)", (user_id, title))
        conn.commit()
        
        # 重新拉取列表
        chapters = conn.execute("SELECT id, title FROM chapters WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
        conn.close()
        
        choices = [row["title"] for row in chapters]
        return gr.update(choices=choices, value=title), chapters[0]["id"], [], gr.update(value="")

    add_chapter_btn.click(
        add_new_chapter, 
        inputs=[new_chapter_name, active_user_id], 
        outputs=[chapter_selector, active_chapter_id, chatbot, new_chapter_name]
    )

    # D. 發送對話並即時生成
    def user_submit(user_msg, chat_history, chapter_id):
        for updated_history in lihuan_engine(user_msg, chat_history, chapter_id):
            yield gr.update(value=""), updated_history

    submit_btn.click(user_submit, inputs=[msg_input, chatbot, active_chapter_id], outputs=[msg_input, chatbot])
    msg_input.submit(user_submit, inputs=[msg_input, chatbot, active_chapter_id], outputs=[msg_input, chatbot])

    # E. 清除當前聊天畫面（不刪除資料庫，只是清空當下畫面）
    clear_btn.click(lambda: None, None, chatbot, queue=False)

    # F. 初始化載入第一波資料 (確實縮排在 Blocks 裡面)
    def load_initial(user_dropdown_val):
        conn = get_db()
        user = conn.execute("SELECT id FROM users WHERE username = ?", (user_dropdown_val,)).fetchone()
        user_id = user["id"]
        chapters = conn.execute("SELECT id, title FROM chapters WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
        conn.close()
        
        choices = [row["title"] for row in chapters]
        default_val = choices[0] if choices else None
        return gr.update(choices=choices, value=default_val)

    demo.load(load_initial, inputs=[user_dropdown], outputs=[chapter_selector])

# 啟動伺服器 (這裡退回最左邊，不縮排)
if __name__ == "__main__":
    demo.queue().launch(show_error=True, server_name="0.0.0.0", server_port=7860)