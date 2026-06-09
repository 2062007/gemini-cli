#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Hỗ trợ đa ngôn ngữ (English/Vietnamese), tự động lấy danh sách model.
Dùng requests và colorama, lưu dữ liệu tại thư mục hiện tại.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    import requests
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
except ImportError as e:
    print(f"Missing library: {e}")
    print("Please install: pip install requests colorama")
    sys.exit(1)

# ==================== CẤU HÌNH ====================
SCRIPT_DIR = Path(__file__).parent if "__file__" in globals() else Path.cwd()
CONFIG_DIR = SCRIPT_DIR / "gemini_data"
CONFIG_FILE = CONFIG_DIR / "config.json"
CHATS_DIR = CONFIG_DIR / "chats"
HISTORY_FILE = CONFIG_DIR / "history.json"
MODEL_CACHE_FILE = CONFIG_DIR / "model_cache.json"

DEFAULT_MODEL_ID = "gemini-2.0-flash"

# ==================== NGÔN NGỮ ====================
TEXTS = {
    "en": {
        "data_dir": "📁 Data saved at: {}",
        "no_api_key": "🔑 Gemini API key not found!",
        "get_api_key_url": "Get your API key at: https://aistudio.google.com/apikey\n",
        "enter_api_key": "Enter your API key: ",
        "api_key_saved": "✅ API key saved!",
        "api_key_empty": "❌ API key cannot be empty!",
        "fetching_models": "🔄 Fetching model list from Google API...",
        "found_models": "✅ Found {} models supporting chat.",
        "fetch_error": "⚠️ Fetch error: {}",
        "using_cache": "📦 Using model list from cache.",
        "using_fallback": "⚠️ Using fallback model list.",
        "model_list_title": "🤖 GEMINI MODEL LIST (from Google API)",
        "current_model": "✅ Current model: {}",
        "pick_number": "👉 Enter number to see details and select (Enter to keep)",
        "choice_prompt": "Your choice: ",
        "model_info_title": "📌 MODEL INFO: {}",
        "model_id": "🆔 ID: {}",
        "input_tokens": "📥 {}",
        "supports": "⚙️ {}",
        "desc_prefix": "📝 {}",
        "confirm_switch": "Do you want to switch to this model? (y/N): ",
        "switched": "✅ Switched to {}",
        "cancel_switch": "❌ Switch cancelled.",
        "invalid_choice": "❌ Invalid choice.",
        "keep_model": "Keeping current model.",
        # Chat loop
        "chatting": "💬 Chatting: {}",
        "model_label": "📡 Model: {}",
        "commands_label": "📝 Commands: /menu | /new | /delete | /history | /model | /quit",
        "history_label": "--- Full chat history ({} messages) ---",
        "user_prefix": "👤 You",
        "gemini_prefix": "🤖 Gemini",
        "back_to_menu": "🔙 Returning to main menu...",
        "new_chat": "✨ Creating new chat...",
        "delete_confirm": "⚠️  Permanently delete chat '{}'? (y/N): ",
        "deleted": "✅ Deleted '{}'",
        "delete_cancelled": "Delete cancelled.",
        "not_found_chat": "Chat '{}' not found.",
        "no_history": "📭 No chat history.",
        "history_title": "📜 CHAT HISTORY",
        "goodbye": "👋 Goodbye!",
        "model_changed": "✅ Model changed, please continue chatting.",
        # Main menu
        "main_title": "🤖 GEMINI CLI CHATBOT (Dynamic models)",
        "menu_continue": "1. Continue chat: {}",
        "menu_switch_chat": "2. Select / Create another chat",
        "menu_history": "3. View chat history",
        "menu_model": "4. Select Gemini model (auto-updated)",
        "menu_change_key": "5. Change API key",
        "menu_exit": "6. Exit",
        "prompt_choice": "🔹 Choice (1-6): ",
        "new_chat_name": "New chat name (Enter = datetime): ",
        "no_chats": "📭 No chats yet, create one.",
        "chat_list_title": "📋 Existing chats:",
        "chat_item": "  {}. {} ({} messages)",
        "new_chat_option": "  0. Create new",
        "select_number": "Enter number: ",
        "enter_number": "Please enter a number.",
        "switched_chat": "✅ Switched to '{}'",
        "new_api_key": "New API key: ",
        "api_key_updated": "✅ API key updated.",
        "invalid_api_key": "Invalid API key.",
        "error_unexpected": "Unexpected error: {}",
    },
    "vi": {
        "data_dir": "📁 Dữ liệu lưu tại: {}",
        "no_api_key": "🔑 Chưa có API key Gemini!",
        "get_api_key_url": "Bạn có thể lấy API key tại: https://aistudio.google.com/apikey\n",
        "enter_api_key": "Nhập API key của bạn: ",
        "api_key_saved": "✅ Đã lưu API key!",
        "api_key_empty": "❌ API key không được để trống!",
        "fetching_models": "🔄 Đang tải danh sách model từ Google API...",
        "found_models": "✅ Đã tìm thấy {} model hỗ trợ chat.",
        "fetch_error": "⚠️ Lỗi fetch: {}",
        "using_cache": "📦 Dùng danh sách model từ cache.",
        "using_fallback": "⚠️ Dùng danh sách model dự phòng.",
        "model_list_title": "🤖 DANH SÁCH MODEL GEMINI (Lấy từ Google API)",
        "current_model": "✅ Model hiện tại: {}",
        "pick_number": "👉 Nhập số để xem chi tiết và chọn (Enter để giữ nguyên)",
        "choice_prompt": "Lựa chọn: ",
        "model_info_title": "📌 THÔNG TIN MODEL: {}",
        "model_id": "🆔 ID: {}",
        "input_tokens": "📥 {}",
        "supports": "⚙️ {}",
        "desc_prefix": "📝 {}",
        "confirm_switch": "Bạn có muốn chuyển sang model này không? (y/N): ",
        "switched": "✅ Đã đổi sang {}",
        "cancel_switch": "❌ Hủy chuyển đổi.",
        "invalid_choice": "❌ Lựa chọn không hợp lệ.",
        "keep_model": "Giữ nguyên model hiện tại.",
        # Chat loop
        "chatting": "💬 Đang chat: {}",
        "model_label": "📡 Model: {}",
        "commands_label": "📝 Lệnh: /menu | /new | /delete | /history | /model | /quit",
        "history_label": "--- Toàn bộ lịch sử ({} tin nhắn) ---",
        "user_prefix": "👤 Bạn",
        "gemini_prefix": "🤖 Gemini",
        "back_to_menu": "🔙 Quay lại menu chính...",
        "new_chat": "✨ Tạo đoạn chat mới...",
        "delete_confirm": "⚠️  Xoá vĩnh viễn đoạn chat '{}'? (y/N): ",
        "deleted": "✅ Đã xoá '{}'",
        "delete_cancelled": "Đã huỷ xoá.",
        "not_found_chat": "Không tìm thấy đoạn chat '{}'.",
        "no_history": "📭 Chưa có lịch sử đoạn chat nào.",
        "history_title": "📜 LỊCH SỬ CÁC ĐOẠN CHAT",
        "goodbye": "👋 Tạm biệt!",
        "model_changed": "✅ Đã đổi model, hãy tiếp tục chat.",
        # Main menu
        "main_title": "🤖 GEMINI CLI CHATBOT (Danh sách model động)",
        "menu_continue": "1. Tiếp tục chat: {}",
        "menu_switch_chat": "2. Chọn / Tạo đoạn chat khác",
        "menu_history": "3. Xem lịch sử các đoạn chat",
        "menu_model": "4. Chọn Model Gemini (tự động cập nhật)",
        "menu_change_key": "5. Đổi API key",
        "menu_exit": "6. Thoát",
        "prompt_choice": "🔹 Lựa chọn (1-6): ",
        "new_chat_name": "Tên đoạn chat mới (để trống = datetime): ",
        "no_chats": "📭 Chưa có đoạn chat nào, tạo mới.",
        "chat_list_title": "📋 Các đoạn chat hiện có:",
        "chat_item": "  {}. {} ({} tin nhắn)",
        "new_chat_option": "  0. Tạo đoạn chat mới",
        "select_number": "Chọn số: ",
        "enter_number": "Vui lòng nhập số.",
        "switched_chat": "✅ Đã chuyển sang '{}'",
        "new_api_key": "API key mới: ",
        "api_key_updated": "✅ Đã cập nhật API key.",
        "invalid_api_key": "API key không hợp lệ.",
        "error_unexpected": "Lỗi không mong muốn: {}",
    }
}

# Biến toàn cục lưu ngôn ngữ hiện tại
CURRENT_LANG = "vi"  # mặc định, sẽ được ghi đè ngay khi khởi động

def get_text(key: str) -> str:
    """Lấy chuỗi theo ngôn ngữ hiện tại."""
    return TEXTS[CURRENT_LANG].get(key, key)

# ==================== KHỞI TẠO THƯ MỤC ====================
def init_dirs():
    CONFIG_DIR.mkdir(exist_ok=True)
    CHATS_DIR.mkdir(exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps([], indent=2))
    if not CONFIG_FILE.exists():
        # Tạo config mặc định, language sẽ được cập nhật sau
        save_config({"api_key": "", "current_chat": "default", "model": DEFAULT_MODEL_ID, "language": CURRENT_LANG})
    print(f"{Fore.BLUE}{get_text('data_dir').format(CONFIG_DIR)}{Style.RESET_ALL}")

def load_config():
    return json.loads(CONFIG_FILE.read_text())

def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

# ==================== CHỌN NGÔN NGỮ (CHẠY ĐẦU TIÊN) ====================
def initial_language_prompt():
    """
    Hiển thị lời nhắc chọn ngôn ngữ ngay khi bắt đầu, trước mọi thao tác khác.
    Không sử dụng get_text() để tránh phụ thuộc vào CURRENT_LANG chưa được thiết lập.
    """
    global CURRENT_LANG
    print("\n" + "="*60)
    print("🌐 Select language / Chọn ngôn ngữ:")
    print("1. English")
    print("2. Tiếng Việt")
    choice = input("Your choice / Lựa chọn của bạn (1/2): ").strip()
    CURRENT_LANG = "en" if choice == "1" else "vi"
    print(f"{Fore.GREEN}✅ Language set to {CURRENT_LANG.upper()}{Style.RESET_ALL}")

# ==================== QUẢN LÝ API KEY ====================
def get_api_key():
    config = load_config()
    if not config.get("api_key"):
        print(f"\n{Fore.YELLOW}{get_text('no_api_key')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{get_text('get_api_key_url')}{Style.RESET_ALL}")
        api_key = input(f"{Fore.GREEN}{get_text('enter_api_key')}{Style.RESET_ALL}").strip()
        if api_key:
            config["api_key"] = api_key
            save_config(config)
            print(f"{Fore.GREEN}{get_text('api_key_saved')}{Style.RESET_ALL}")
            return api_key
        else:
            print(f"{Fore.RED}{get_text('api_key_empty')}{Style.RESET_ALL}")
            return get_api_key()
    return config["api_key"]

# ==================== LẤY DANH SÁCH MODEL ĐỘNG ====================
def fetch_models_from_api(api_key: str) -> Optional[Dict[str, Dict]]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    print(f"{Fore.CYAN}{get_text('fetching_models')}{Style.RESET_ALL}")
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            models = {}
            idx = 1
            for model in data.get("models", []):
                if "generateContent" in model.get("supportedGenerationMethods", []):
                    model_id = model["name"].replace("models/", "")
                    display_name = model.get("displayName", model_id)
                    desc_parts = []
                    if model.get("description"):
                        desc_parts.append(model.get("description")[:60])
                    if model.get("inputTokenLimit"):
                        desc_parts.append(f"Input: {model.get('inputTokenLimit'):,} tokens")
                    desc_parts.append(f"Supports: generateContent")
                    models[str(idx)] = {
                        "id": model_id,
                        "name": display_name,
                        "desc": " | ".join(desc_parts)
                    }
                    idx += 1
            if models:
                cache_data = {"timestamp": time.time(), "models": models}
                MODEL_CACHE_FILE.write_text(json.dumps(cache_data, indent=2))
                print(f"{Fore.GREEN}{get_text('found_models').format(len(models))}{Style.RESET_ALL}")
                return models
    except Exception as e:
        print(f"{Fore.YELLOW}{get_text('fetch_error').format(e)}{Style.RESET_ALL}")
    
    if MODEL_CACHE_FILE.exists():
        try:
            cache_data = json.loads(MODEL_CACHE_FILE.read_text())
            if time.time() - cache_data.get("timestamp", 0) < 86400:
                print(f"{Fore.BLUE}{get_text('using_cache')}{Style.RESET_ALL}")
                return cache_data.get("models")
        except:
            pass
    return None

def get_available_models(api_key: str) -> Dict[str, Dict]:
    models = fetch_models_from_api(api_key)
    if models:
        return models
    print(f"{Fore.YELLOW}{get_text('using_fallback')}{Style.RESET_ALL}")
    return {
        "1": {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "desc": "Popular, fast, stable."},
        "2": {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "desc": "Lightweight, cost-effective."},
        "3": {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "desc": "Powerful, 2M context."},
    }

def choose_model(api_key: str) -> str:
    models = get_available_models(api_key)
    config = load_config()
    current_model_id = config.get("model", DEFAULT_MODEL_ID)

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}{get_text('model_list_title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}")

    for key, m in models.items():
        marker = "✅ " if m["id"] == current_model_id else "   "
        print(f"{Fore.GREEN}{marker}{key}. {Fore.WHITE}{m['name']}")

    print(f"\n{Fore.YELLOW}{get_text('pick_number')}{Style.RESET_ALL}")
    choice = input(f"{Fore.GREEN}{get_text('choice_prompt')}{Style.RESET_ALL}").strip()

    if choice in models:
        selected = models[choice]
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}{get_text('model_info_title').format(selected['name'])}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}{get_text('model_id').format(selected['id'])}{Style.RESET_ALL}")
        for part in selected['desc'].split(' | '):
            if part.startswith("Input:"):
                print(f"{Fore.YELLOW}{get_text('input_tokens').format(part)}{Style.RESET_ALL}")
            elif part.startswith("Supports:"):
                print(f"{Fore.YELLOW}{get_text('supports').format(part)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{get_text('desc_prefix').format(part)}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")

        confirm = input(f"\n{Fore.GREEN}{get_text('confirm_switch')}{Style.RESET_ALL}").strip().lower()
        if confirm == 'y':
            config["model"] = selected["id"]
            save_config(config)
            print(f"{Fore.GREEN}{get_text('switched').format(selected['name'])}{Style.RESET_ALL}")
            return selected["id"]
        else:
            print(f"{Fore.YELLOW}{get_text('cancel_switch')}{Style.RESET_ALL}")
            return current_model_id
    else:
        if choice != "":
            print(f"{Fore.RED}{get_text('invalid_choice')}{Style.RESET_ALL}")
        return current_model_id

# ==================== QUẢN LÝ ĐOẠN CHAT ====================
def get_chat_file(chat_name):
    safe_name = "".join(c for c in chat_name if c.isalnum() or c in "._-")
    if not safe_name:
        safe_name = "default"
    return CHATS_DIR / f"{safe_name}.json"

def load_chat(chat_name):
    chat_file = get_chat_file(chat_name)
    if chat_file.exists():
        data = json.loads(chat_file.read_text())
        return data.get("messages", [])
    return []

def save_chat(chat_name, messages):
    chat_file = get_chat_file(chat_name)
    chat_file.write_text(json.dumps({
        "name": chat_name,
        "messages": messages,
        "updated_at": datetime.now().isoformat()
    }, indent=2, ensure_ascii=False))

def list_chats():
    chats = []
    for f in CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            msg_count = len(data.get("messages", [])) // 2
            updated = data.get("updated_at", "Unknown")[:16]
            chats.append({
                "name": data.get("name", f.stem),
                "msg_count": msg_count,
                "updated": updated
            })
        except:
            pass
    return sorted(chats, key=lambda x: x["updated"], reverse=True)

def delete_chat(chat_name):
    chat_file = get_chat_file(chat_name)
    if chat_file.exists():
        confirm = input(f"{Fore.RED}{get_text('delete_confirm').format(chat_name)}{Style.RESET_ALL}")
        if confirm.lower() == 'y':
            chat_file.unlink()
            print(f"{Fore.GREEN}{get_text('deleted').format(chat_name)}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}{get_text('delete_cancelled')}{Style.RESET_ALL}")
            return False
    else:
        print(f"{Fore.RED}{get_text('not_found_chat').format(chat_name)}{Style.RESET_ALL}")
        return False

def update_history(chat_name):
    try:
        history = json.loads(HISTORY_FILE.read_text())
    except:
        history = []
    history = [h for h in history if h.get("name") != chat_name]
    history.insert(0, {
        "name": chat_name,
        "last_used": datetime.now().isoformat(),
        "message_count": len(load_chat(chat_name)) // 2
    })
    HISTORY_FILE.write_text(json.dumps(history[:50], indent=2))

def show_history():
    try:
        history = json.loads(HISTORY_FILE.read_text())
    except:
        history = []
    if not history:
        print(f"{Fore.YELLOW}{get_text('no_history')}{Style.RESET_ALL}")
        return
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}{get_text('history_title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}")
    for i, h in enumerate(history, 1):
        name = h.get("name", "Unknown")
        msg_count = h.get("message_count", 0)
        last_used = h.get("last_used", "Unknown")[:16]
        print(f"{Fore.GREEN}{i:2d}. {Fore.WHITE}{name}")
        print(f"      {Fore.BLUE}📝 {msg_count} messages | 🕐 {last_used}")
    print(f"{Fore.CYAN}{'='*60}\n")

# ==================== GỌI GEMINI API ====================
def call_gemini(api_key, messages, model_id):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    payload = {"contents": contents}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get("candidates"):
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return f"{Fore.RED}❌ Error: Response has no content.{Style.RESET_ALL}"
        else:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
            return f"{Fore.RED}❌ API Error: {error_msg}{Style.RESET_ALL}"
    except requests.exceptions.Timeout:
        return f"{Fore.RED}❌ Timeout: Gemini not responding (30s){Style.RESET_ALL}"
    except requests.exceptions.ConnectionError:
        return f"{Fore.RED}❌ Connection error: Check internet{Style.RESET_ALL}"
    except Exception as e:
        return f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}"

# ==================== MAIN CHAT LOOP (ĐÃ SỬA HIỂN THỊ ĐẦY ĐỦ) ====================
def chat_loop(chat_name, api_key, model_id):
    messages = load_chat(chat_name)
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}{get_text('chatting').format(chat_name)}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{get_text('model_label').format(model_id)}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{get_text('commands_label')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    # HIỂN THỊ TOÀN BỘ LỊCH SỬ, KHÔNG CẮT NGẮN
    if messages:
        print(f"{Fore.YELLOW}{get_text('history_label').format(len(messages)//2)}{Style.RESET_ALL}")
        for msg in messages:
            role_icon = f"{Fore.GREEN}{get_text('user_prefix')}" if msg["role"] == "user" else f"{Fore.MAGENTA}{get_text('gemini_prefix')}"
            # Hiển thị nguyên văn nội dung, thay xuống dòng bằng xuống dòng + thụt đầu dòng cho đẹp
            content = msg['content'].replace('\n', '\n           ')
            print(f"{role_icon}: {content}")
        print()
    
    while True:
        try:
            user_input = input(f"{Fore.GREEN}{get_text('user_prefix')}{Style.RESET_ALL}: ").strip()
            if not user_input:
                continue
            
            cmd = user_input.lower()
            if cmd in ["/menu", "/back"]:
                update_history(chat_name)
                return "menu"
            elif cmd == "/new":
                update_history(chat_name)
                return "new"
            elif cmd == "/delete":
                if delete_chat(chat_name):
                    return "deleted"
                continue
            elif cmd == "/history":
                show_history()
                continue
            elif cmd == "/model":
                new_model_id = choose_model(api_key)
                if new_model_id != model_id:
                    model_id = new_model_id
                    config = load_config()
                    config["model"] = model_id
                    save_config(config)
                    print(f"{Fore.GREEN}{get_text('model_changed')}{Style.RESET_ALL}")
                continue
            elif cmd == "/quit":
                update_history(chat_name)
                return "quit"
            else:
                messages.append({"role": "user", "content": user_input})
                print(f"{Fore.MAGENTA}{get_text('gemini_prefix')}{Style.RESET_ALL}: ", end="", flush=True)
                response = call_gemini(api_key, messages, model_id)
                print(response)
                messages.append({"role": "assistant", "content": response})
                save_chat(chat_name, messages)
                update_history(chat_name)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}{get_text('goodbye')}{Style.RESET_ALL}")
            update_history(chat_name)
            return "quit"

# ==================== MAIN MENU ====================
def main_menu():
    # 1. Hỏi ngôn ngữ ngay từ đầu, trước mọi thứ khác
    initial_language_prompt()
    
    # 2. Sau khi có ngôn ngữ, khởi tạo thư mục và cập nhật config
    init_dirs()
    config = load_config()
    config["language"] = CURRENT_LANG
    save_config(config)
    
    # 3. Lấy API key (nếu cần nhập, thông báo đã đúng ngôn ngữ)
    api_key = get_api_key()
    if not api_key:
        return
    
    current_model = config.get("model", DEFAULT_MODEL_ID)
    current_chat = config.get("current_chat", "default")
    
    while True:
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}{get_text('main_title')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}{get_text('menu_continue').format(current_chat)}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{get_text('menu_switch_chat')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{get_text('menu_history')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{get_text('menu_model')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{get_text('menu_change_key')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{get_text('menu_exit')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")
        
        choice = input(f"{Fore.YELLOW}{get_text('prompt_choice')}{Style.RESET_ALL}").strip()
        
        if choice == "1":
            result = chat_loop(current_chat, api_key, current_model)
            if result == "new":
                new_name = input(f"{Fore.GREEN}{get_text('new_chat_name')}{Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
            elif result == "deleted":
                chats = list_chats()
                current_chat = chats[0]["name"] if chats else datetime.now().strftime("%Y%m%d_%H%M%S")
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
            elif result == "quit":
                break
        elif choice == "2":
            chats = list_chats()
            if not chats:
                print(f"{Fore.YELLOW}{get_text('no_chats')}{Style.RESET_ALL}")
                new_name = input(f"{Fore.GREEN}{get_text('new_chat_name')}{Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
                continue
            print(f"\n{Fore.CYAN}{get_text('chat_list_title')}{Style.RESET_ALL}")
            for i, c in enumerate(chats, 1):
                print(get_text('chat_item').format(i, c['name'], c['msg_count']))
            print(get_text('new_chat_option'))
            try:
                sel = int(input(f"{Fore.YELLOW}{get_text('select_number')}{Style.RESET_ALL}"))
                if sel == 0:
                    new_name = input(f"{Fore.GREEN}{get_text('new_chat_name')}{Style.RESET_ALL}").strip()
                    if not new_name:
                        new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                    current_chat = new_name
                elif 1 <= sel <= len(chats):
                    current_chat = chats[sel-1]["name"]
                else:
                    continue
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
                print(f"{Fore.GREEN}{get_text('switched_chat').format(current_chat)}{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}{get_text('enter_number')}{Style.RESET_ALL}")
        elif choice == "3":
            show_history()
        elif choice == "4":
            current_model = choose_model(api_key)
        elif choice == "5":
            new_key = input(f"{Fore.GREEN}{get_text('new_api_key')}{Style.RESET_ALL}").strip()
            if new_key:
                config = load_config()
                config["api_key"] = new_key
                save_config(config)
                api_key = new_key
                print(f"{Fore.GREEN}{get_text('api_key_updated')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}{get_text('invalid_api_key')}{Style.RESET_ALL}")
        elif choice == "6":
            print(f"{Fore.YELLOW}{get_text('goodbye')}{Style.RESET_ALL}")
            break

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}{get_text('goodbye')}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{get_text('error_unexpected').format(e)}{Style.RESET_ALL}")
        sys.exit(1)
