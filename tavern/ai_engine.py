# tavern/ai_engine.py
import os
import torch
import re
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from peft import PeftModel
from threading import Thread

class LihuanAIEngine:
    def __init__(self):
        print("🔮 正在從本地硬碟喚醒 Llama-3 基礎顯卡大腦...")
        self.base_model_path = "unsloth/llama-3-8b-Instruct-bnb-4bit"
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_path, 
            clean_up_tokenization_spaces=False
        )
        
        self.base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype=torch.float16,
            device_map={"": 0}
        )
        
        self.peft_model = None
        self.loaded_adapters = set()
        
        # 🌐 通用原生系統提示詞
        self.general_system_prompt = """
        【角色身份】：你是專注於創作小說劇情的頂級繁體中文敘事家。
        【⚠️ 絕對鐵律 (CRITICAL RULES)】：
        1. 100% 必須使用「純繁體中文」寫作！絕對禁止出現任何英文詞彙、英文問候、英文總結或英文選項！
        2. 絕對禁止在結尾反問使用者問題、詢問後續發展或提供互動選項（例如禁止出現「你希望怎麼做？」或「你想讓主角做什麼？」等廢話）。
        3. 請直接進行小說劇情正文的沉浸式描寫，每次輸出請保持豐富細膩的敘事，長度維持在約 500 字以上的精采篇幅。
        4. 若為多種角色，盡量使角色們相互對話，並且每個對話需多控一行，使讀者好閱讀。
        5. 讀者常使用()來表示動作、內心話、吐槽等行為。
        
        """


    def load_and_set_adapter(self, lora_path):
        """動態載入或切換指定路徑的 LoRA 權重至顯存中"""
        if not lora_path or not os.path.exists(lora_path):
            if self.peft_model is not None:
                self.peft_model.disable_adapter_layers()
            return False

        abs_path = os.path.abspath(lora_path)
        adapter_name = f"adapter_{abs(hash(abs_path))}"

        if self.peft_model is None:
            print(f"✨ 首次載入 LoRA 靈魂: {abs_path}")
            self.peft_model = PeftModel.from_pretrained(self.base_model, abs_path, adapter_name=adapter_name)
            self.loaded_adapters.add(adapter_name)
        else:
            self.peft_model.enable_adapter_layers()
            if adapter_name not in self.loaded_adapters:
                print(f"📦 動態掛載新 LoRA 靈魂至顯存: {abs_path}")
                self.peft_model.load_adapter(abs_path, adapter_name=adapter_name)
                self.loaded_adapters.add(adapter_name)
            self.peft_model.set_adapter(adapter_name)

        return True

    def generate_stream(self, db_messages, custom_system_prompt=None, lora_system_prompt=None, chapter_memory=None, global_memory=None, lora_path=None):
        # 1. 決定最終採用的 System Prompt
        if custom_system_prompt and custom_system_prompt.strip():
            active_prompt = custom_system_prompt.strip()
        elif lora_system_prompt and lora_system_prompt.strip():
            active_prompt = lora_system_prompt.strip()
        else:
            active_prompt = self.general_system_prompt

        # 強制加入禁止英文廢話的最高指令
        active_prompt += "\n【⚠️ 最高指令】：絕對禁止輸出任何英文解析、Let me craft... 或分隔線。第一個字必須直接是繁體中文故事正文！"

        # 2. 注入【全域記憶庫】與【單章動態】
        if global_memory and global_memory.strip():
            active_prompt += f"\n\n【🌐 全域跨章節角色與世界觀設定】：\n{global_memory.strip()}"

        if chapter_memory and chapter_memory.strip():
            active_prompt += f"\n\n【📌 本章節當前動態與伏筆】：\n{chapter_memory.strip()}"

        # 3. 組合 Messages
        messages = [{"role": "system", "content": active_prompt}]
        for msg in db_messages:
            messages.append({"role": msg.role, "content": msg.content})
            
        prompt_text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt_text, return_tensors="pt").to("cuda")
        
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        # 4. 動態切換 LoRA 權重
        has_lora = self.load_and_set_adapter(lora_path)
        
        generation_kwargs = dict(
            input_ids=inputs["input_ids"],
            attention_mask=inputs.get("attention_mask", None),
            max_new_tokens=2048,
            use_cache=True,
            temperature=0.3,
            top_p=0.95,
            repetition_penalty=1.15,
            streamer=streamer
        )
    
        # 5. 啟動背景生成執行緒
        def run_generation():
            if has_lora and self.peft_model is not None:
                self.peft_model.generate(**generation_kwargs)
            else:
                if self.peft_model is not None:
                    with self.peft_model.disable_adapter():
                        self.peft_model.generate(**generation_kwargs)
                else:
                    self.base_model.generate(**generation_kwargs)

        thread = Thread(target=run_generation)
        thread.start()
        
        # ✂️ 6. 升級版物理消音器 (The Silencer v2)：智能切除混合中文人名的英文開場白與 --- 分隔線
        is_thought_process = True
        buffer = ""
        
        for new_token in streamer:
            if is_thought_process:
                buffer += new_token
                
                # A. 遇到分隔線 `---`，代表之前的思考過程結束，直接斬斷前面所有內容！
                if '---' in buffer:
                    buffer = buffer.split('---')[-1].lstrip()
                    if re.search(r'[\u4e00-\u9fff]', buffer):
                        is_thought_process = False
                        yield buffer
                        buffer = ""
                    continue
                
                # B. 檢查緩衝區是否有換行（依行分析）
                if '\n' in buffer:
                    lines = buffer.split('\n')
                    pending_lines = lines[:-1]
                    buffer = lines[-1]
                    
                    for line in pending_lines:
                        line_str = line.strip()
                        if not line_str:
                            continue
                        
                        # 計算字數比例（防禦：英文句子裡包含中文名字的情況）
                        latin_count = len(re.findall(r'[a-zA-Z]', line_str))
                        zh_count = len(re.findall(r'[\u4e00-\u9fff]', line_str))
                        
                        # 如果主要語言是英文，或包含 Let me / guidelines 等關鍵字，判定為廢話丟棄
                        is_english_junk = (latin_count > zh_count and latin_count > 5) or bool(re.search(r'(Let me|I will|I\'ll|guidelines|writing standards|described in)', line_str, re.IGNORECASE))
                        
                        if not is_english_junk:
                            is_thought_process = False
                            yield line_str + "\n"
            else:
                yield new_token

        # 🛡️ 7. 安全保險：如果結束時仍有殘留，安全輸出
        if is_thought_process and buffer:
            # 最後一刻檢查：只要不是純英文就放行
            latin_count = len(re.findall(r'[a-zA-Z]', buffer))
            zh_count = len(re.findall(r'[\u4e00-\u9fff]', buffer))
            if zh_count >= latin_count:
                yield buffer