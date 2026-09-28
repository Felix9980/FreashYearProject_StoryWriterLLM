# tavern/views.py
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.db.models import Q
from .models import Chapter, Message, GlobalMemory, LoraModel
from .ai_engine import LihuanAIEngine

# 延遲載入機制，防止啟動或 migrate 時霸佔 VRAM
ai_engine = None

def get_ai_engine():
    global ai_engine
    if ai_engine is None:
        print("🔥 首次對話觸發！正在將大腦載入顯示卡...")
        ai_engine = LihuanAIEngine()
    return ai_engine

# 1. 註冊帳號
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            GlobalMemory.objects.create(user=user)  # 自動為新使用者建立全域記憶庫
            login(request, user)
            return redirect('tavern_home')
    else:
        form = UserCreationForm()
    return render(request, 'tavern/register.html', {'form': form})

# 2. 登入帳號
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('tavern_home')
    else:
        form = AuthenticationForm()
    return render(request, 'tavern/login.html', {'form': form})

# 3. 登出
def logout_view(request):
    logout(request)
    return redirect('login')

# 4. 酒館主畫面 (同時載入系統預設與個人建立的 LoRA 靈魂)
@login_required
def tavern_home(request):
    global_mem, _ = GlobalMemory.objects.get_or_create(user=request.user)
    
    # 同時撈出「系統預設 (user__isnull=True)」與「該使用者自己建立 (user=request.user)」的 LoRA
    user_loras = LoraModel.objects.filter(
        Q(user=request.user) | Q(user__isnull=True)
    ).order_by('-created_at')
    
    chapters = Chapter.objects.filter(user=request.user).order_by('-created_at')
    active_chapter = None
    messages = []
    
    chapter_id = request.GET.get('chapter')
    if chapter_id:
        active_chapter = get_object_or_404(Chapter, id=chapter_id, user=request.user)
        messages = active_chapter.messages.all().order_by('created_at')
    elif chapters.exists():
        active_chapter = chapters.first()
        messages = active_chapter.messages.all().order_by('created_at')
        
    return render(request, 'tavern/chat.html', {
        'chapters': chapters,
        'active_chapter': active_chapter,
        'messages': messages,
        'global_memory': global_mem,
        'user_loras': user_loras,
    })

# 5. 建立新故事線 (可綁定指定的 LoRA 靈魂)
@login_required
def create_chapter(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        system_prompt = request.POST.get('system_prompt', '').strip()
        lora_id = request.POST.get('lora_id', '')
        
        lora_obj = None
        if lora_id:
            lora_obj = LoraModel.objects.filter(
                Q(id=lora_id) & (Q(user=request.user) | Q(user__isnull=True))
            ).first()

        if title:
            chapter = Chapter.objects.create(
                user=request.user, 
                title=title,
                lora=lora_obj,
                system_prompt=system_prompt if system_prompt else None
            )
            return redirect(f"/?chapter={chapter.id}")
    return redirect('tavern_home')

# 6. 註冊新 LoRA 靈魂 API
@login_required
def create_lora_api(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        folder_path = request.POST.get('folder_path', '').strip()
        description = request.POST.get('description', '').strip()
        
        if name and folder_path:
            LoraModel.objects.create(
                user=request.user,
                name=name,
                folder_path=folder_path,
                description=description
            )
            return JsonResponse({'status': 'success', 'message': 'LoRA 靈魂權重註冊成功！'})
    return JsonResponse({'error': '資料不完整'}, status=400)

# 7. 更新單章記憶 API
@login_required
def update_memory_api(request, chapter_id):
    if request.method == 'POST':
        chapter = get_object_or_404(Chapter, id=chapter_id, user=request.user)
        memory_text = request.POST.get('memory', '').strip()
        chapter.memory = memory_text
        chapter.save()
        return JsonResponse({'status': 'success', 'message': '章節記憶已同步！'})
    return JsonResponse({'error': '無效的請求'}, status=400)

# 8. 更新全域跨章節記憶 API
@login_required
def update_global_memory_api(request):
    if request.method == 'POST':
        global_mem, _ = GlobalMemory.objects.get_or_create(user=request.user)
        global_text = request.POST.get('global_memory', '').strip()
        global_mem.content = global_text
        global_mem.save()
        return JsonResponse({'status': 'success', 'message': '跨章節全域記憶庫已更新！'})
    return JsonResponse({'error': '無效的請求'}, status=400)

# 9. 核心打字機即時串流對答 API
@login_required
def chat_stream_api(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, user=request.user)
    global_mem, _ = GlobalMemory.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_input = request.POST.get('message', '').strip()
        if not user_input:
            return JsonResponse({'error': '訊息不能為空'}, status=400)
            
        # A. 將使用者訊息存入資料庫
        Message.objects.create(chapter=chapter, role='user', content=user_input)
        
        # B. 撈出歷史對話紀錄
        history_messages = chapter.messages.all().order_by('created_at')
        
        # C. 取得當前章節綁定的 LoRA 權重路徑與資料庫中存的專屬 Prompt
        target_lora_path = chapter.lora.folder_path if chapter.lora else None
        target_lora_prompt = chapter.lora.system_prompt if chapter.lora else None
        
        # D. 利用 Server-Sent Events (SSE) 實現即時串流打字
        def response_generator():
            engine = get_ai_engine()
            full_reply = ""
            
            # 強制擴張 WSGI 管道緩衝區 (2048 空白字符沖水)
            yield f": {' ' * 2048}\n\n"
            
            for chunk in engine.generate_stream(
                history_messages,
                custom_system_prompt=chapter.system_prompt,
                lora_system_prompt=target_lora_prompt,  # 👈 傳入 LoRA 資料庫欄位中的專屬 Prompt
                chapter_memory=chapter.memory,
                global_memory=global_mem.content,
                lora_path=target_lora_path
            ):
                if not chunk:
                    continue
                full_reply += chunk
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
            
            # 完整對話存入資料庫
            Message.objects.create(chapter=chapter, role='assistant', content=full_reply)
            
        return StreamingHttpResponse(response_generator(), content_type='text/event-stream')

# 10. 刪除世界線 API
@login_required
def delete_chapter(request, chapter_id):
    if request.method == 'POST':
        chapter = get_object_or_404(Chapter, id=chapter_id, user=request.user)
        chapter.delete()
    return redirect('tavern_home')