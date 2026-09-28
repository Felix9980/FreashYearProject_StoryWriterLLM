import json
import os

INPUT_FILE = "source_data/conversations.json"
OUTPUT_DATASET = "cleaned_dataset.json"
OUTPUT_PREVIEW = "stories_preview.txt"

def clean_conversations():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 錯誤：找不到輸入檔案 {INPUT_FILE}，請確認 Day 1 解壓成功！")
        return

    print(f"🚀 [1/3] 開始讀取原始對話歷史...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    cleaned_dataset = []
    total_messages_count = 0

    print(f"🧹 [2/3] 正在深度清洗雜訊，提取靈魂語料...")
    
    # 遍歷每一個獨立的對話主題 (Conversation)
    for chat in raw_data:
        chat_title = chat.get("name", "未命名故事")
        messages = chat.get("chat_messages", [])
        
        # 依照時間順序排序訊息（確保劇情連貫）
        try:
            messages = sorted(messages, key=lambda x: x.get("created_at", ""))
        except Exception:
            pass # 如果沒有時間戳記就維持原樣
            
        current_turn_messages = []
        
        # 遍歷單一對話內的所有訊息
        for msg in messages:
            sender = msg.get("sender")
            text = msg.get("text", "").strip()
            
            # 處理部分極端狀況：如果 text 為空但 content 有內容
            if not text and msg.get("content"):
                content_blocks = msg.get("content", [])
                text = "".join([block.get("text", "") for block in content_blocks if isinstance(block, dict)]).strip()

            if not text:
                continue # 跳過空訊息

            # 將角色映射為標準訓練標籤 (user / assistant)
            role = "user" if sender == "human" else "assistant"
            current_turn_messages.append({"role": role, "content": text})
            total_messages_count += 1

        # 只有當該對話同時包含 user 和 assistant 時才收入數據集
        if len(current_turn_messages) >= 2:
            cleaned_dataset.append({
                "story_title": chat_title,
                "messages": current_turn_messages
            })

    # 3. 儲存為標準訓練格式的 JSON
    print(f"💾 [3/3] 正在寫出乾淨的數據集...")
    with open(OUTPUT_DATASET, "w", encoding="utf-8") as f:
        json.dump(cleaned_dataset, f, indent=2, ensure_ascii=False)

    # 4. 同步生成一個方便大導演肉眼閱讀的純文字預覽檔
    with open(OUTPUT_PREVIEW, "w", encoding="utf-8") as f:
        for idx, chat in enumerate(cleaned_dataset[:5]): # 只抓前 5 個對話做預覽
            f.write(f"📖 故事線 {idx+1}: {chat['story_title']}\n")
            f.write("="*50 + "\n")
            for msg in chat["messages"]:
                role_label = "貍幻長官 (提示)" if msg["role"] == "user" else "AI 續寫 (文筆)"
                f.write(f"【{role_label}】:\n{msg['content']}\n\n")
            f.write("\n" + "="*50 + "\n\n")

    print("\n🎉 Day 2 資料清洗大獲全勝！")
    print(f"📊 成功清洗出有效故事線: {len(cleaned_dataset)} 條")
    print(f"📊 總計有效對話輪數: {total_messages_count} 🚀")
    print(f"📦 訓練專用數據集已生成: '{OUTPUT_DATASET}'")
    print(f"👀 方便閱讀的小說預覽檔已生成: '{OUTPUT_PREVIEW}'")

if __name__ == "__main__":
    clean_conversations()