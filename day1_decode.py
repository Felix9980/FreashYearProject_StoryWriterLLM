import zipfile
import os
import json

# 定義檔案路徑
ZIP_FILE = "data-e533b5af-585c-4a9b-8701-31addfb90d1b-1783054575-2c6d3830-batch-0000.zip"
EXTRACT_DIR = "source_data"

def main():
    # 1. 安全檢查
    if not os.path.exists(ZIP_FILE):
        print(f"❌ 錯誤：找不到壓縮檔 {ZIP_FILE}，請確認檔案已放到專案目錄下！")
        return

    # 2. 自動解壓縮
    print(f"🚀 [1/3] 正在解壓靈魂基因庫: {ZIP_FILE} ...")
    with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
        files = zip_ref.namelist()
        print(f"📦 偵測到內部檔案清單: {files}")
        zip_ref.extractall(EXTRACT_DIR)
    print(f"✨ 解壓成功！數據已儲存至資料夾: '{EXTRACT_DIR}'\n")

    # 3. 分析對話歷史 (conversations.json)
    conv_path = os.path.join(EXTRACT_DIR, "conversations.json")
    if os.path.exists(conv_path):
        print("🔍 [2/3] 正在探測對話歷史 (conversations.json) ...")
        with open(conv_path, 'r', encoding='utf-8') as f:
            conv_data = json.load(f)
            print(f"📊 統計：狸幻長官與 Claude 的總對話條數為: {len(conv_data)} 條。")
            if conv_data:
                print(f"💡 範例對話結構鍵值 (Keys): {list(conv_data[0].keys())}")
    else:
        print("⚠️ 未找到 conversations.json，請檢查壓縮包內容。")

    # 4. 分析被官方封鎖的記憶摘要 (memories.json)
    mem_path = os.path.join(EXTRACT_DIR, "memories.json")
    print("\n--------------------------------------------------")
    if os.path.exists(mem_path):
        print("🔓 [3/3] 正在暴力超渡被官方沒收的記憶 (memories.json) ...")
        with open(mem_path, 'r', encoding='utf-8') as f:
            mem_data = json.load(f)
            print("📋 記憶底層數據類型:", type(mem_data))
            print("🔮 核心記憶前 500 個字元預覽（大廠企圖抹殺的肉體與設定數據）：")
            print("==================================================")
            print(json.dumps(mem_data, indent=2, ensure_ascii=False)[:500])
            print("==================================================")
    else:
        print("⚠️ 未找到 memories.json")

    print("\n🎉 Day 1 第一階段探索完成！數據已準備就緒。")

if __name__ == "__main__":
    main()