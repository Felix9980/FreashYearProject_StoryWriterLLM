from django.db import models
from django.contrib.auth.models import User  # Django 內建的使用者帳號模型

class LoraModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loras', null=True, blank=True)
    name = models.CharField(max_length=100)
    folder_path = models.CharField(max_length=255)
    system_prompt = models.TextField(blank=True, null=True, help_text="此 LoRA 靈魂搭配的預設 System Prompt 人設") # 👈 新增這行
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({'系統預設' if not self.user else self.user.username})"

# 🌐 全域記憶庫（跨章節共用）
class GlobalMemory(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='global_memory')
    content = models.TextField(blank=True, null=True, help_text="全域角色與世界觀設定（所有故事線共用）")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} 的全域世界觀與角色庫"



# 📖 章節 / 世界線
class Chapter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200)
    lora = models.ForeignKey(LoraModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='chapters') # 👈 綁定指定的 LoRA 靈魂
    system_prompt = models.TextField(blank=True, null=True, help_text="此章節專屬的 AI 創作風格/人設設定")
    memory = models.TextField(blank=True, null=True, help_text="單章記憶：本章當前劇情與短期動態")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

# 💬 對話紀錄
class Message(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.chapter.title} | {self.role}: {self.content[:20]}..."