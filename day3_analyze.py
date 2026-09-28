import json
import os

INPUT_FILE = "cleaned_dataset.json"

def analyze_dataset():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 錯誤：找不到數據集 {INPUT_FILE}，請確認 Day 2 執行成功！")
        return

    print("🚀 正在加載清洗後的靈魂基因庫...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    lengths = []
    for data in dataset:
        total_chars = 0
        for msg in data["messages"]:
            total_chars += len(msg["content"])
        lengths.append(total_chars)

    # 排序以計算統計數據
    lengths.sort()
    total_stories = len(lengths)
    total_chars_all = sum(lengths)
    avg_len = total_chars_all / total_stories
    min_len = lengths[0]
    max_len = lengths[-1]
    median_len = lengths[total_stories // 2]

    print("\n📊 ==================== Day 3 數據集化驗報告 ====================")
    print(f"✨ 總有效故事線數量 : {total_stories} 條")
    print(f"📚 全劇本總字數統計 : {total_chars_all} 字")
    print(f"📈 單條故事平均長度 : {avg_len:.1f} 字")
    print(f"🎯 單條故事長度中位數: {median_len} 字")
    print(f"🚀 最短故事長度     : {min_len} 字")
    print(f"🔥 最長故事長度     : {max_len} 字")
    print("================================================================\n")

    # 在終端機繪製長度分佈直方圖
    print("📈 故事長度分佈直方圖（字數區間）：")
    ranges = [0, 500, 1000, 2000, 5000, 10000, float('inf')]
    labels = ["0-500字", "501-1000字", "1001-2000字", "2001-5000字", "5001-10000字", "10000字以上"]
    counts = [0] * len(labels)

    for l in lengths:
        for i in range(len(ranges)-1):
            if ranges[i] <= l < ranges[i+1]:
                counts[i] += 1
                break

    for label, count in zip(labels, counts):
        # 每 2 條故事畫一個方塊 ■
        bar = "■" * (count // 2 if count > 1 else count)
        print(f"  {label.ljust(14)}: {str(count).rjust(3)} 條 {bar}")

    print("\n⚙️  副導演參數建議：")
    if max_len > 8000:
        print("💡 偵測到超長篇故事！明天微調建議將 max_seq_length 設為 4096 或 8192。")
    else:
        print("💡 故事長度適中，明天微調建議將 max_seq_length 設為 2048 即可，省顯存又跑得快！")

if __name__ == "__main__":
    analyze_dataset()