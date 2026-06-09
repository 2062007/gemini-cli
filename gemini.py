#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Đa ngôn ngữ (English/Việt), tự động lấy danh sách model.
Hỗ trợ lưu cấu hình (API key, ngôn ngữ, model), chỉ chọn ngôn ngữ 1 lần.
Dùng requests + colorama, lưu dữ liệu tại thư mục hiện hành.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

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
DATA_DIR = SCRIPT_DIR / "gemini_data"
CONFIG_FILE = DATA_DIR / "config.json"
CHATS_DIR = DATA_DIR / "chats"
HISTORY_FILE = DATA_DIR / "history.json"
MODEL_CACHE_FILE = DATA_DIR / "model_cache.json"

DEFAULT_MODEL_ID = "gemini-2.0-flash"

# ==================== TỪ ĐIỂN ĐA NGÔN NGỮ ====================
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
        "menu_change_lang": "6. Change language / Đổi ngôn ngữ",
        "menu_exit": "7. Exit",
        "prompt_choice": "🔹 Choice (1-7): ",
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
        # Language selection
        "lang_select_title": "🌐 Select language / Chọn ngôn ngữ:",
        "lang_option_en": "1. English",
        "lang_option_vi": "2. Tiếng Việt",
        "lang_prompt": "Your choice / Lựa chọn của bạn (1/2): ",
        "lang_changed": "✅ Language changed to English.",
        "lang_invalid": "❌ Invalid choice, keeping current language.",
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
        "menu_change_lang": "6. Thay đổi ngôn ngữ / Change language",
        "menu_exit": "7. Thoát",
        "prompt_choice": "🔹 Lựa chọn (1-7): ",
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
        # Language selection
        "lang_select_title": "🌐 Chọn ngôn ngữ / Select language:",
        "lang_option_en": "1. English",
        "lang_option_vi": "2. Tiếng Việt",
        "lang_prompt": "Lựa chọn của bạn / Your choice (1/2): ",
        "lang_changed": "✅ Đã chuyển sang Tiếng Việt.",
        "lang_invalid": "❌ Lựa chọn không hợp lệ, giữ ngôn ngữ hiện tại.",
    }
}

# Biến toàn cục cho ngôn ngữ hiện tại
CURRENT_LANG = "vi"

def get_text(key: str) -> str:
    """Trả về chuỗi theo ngôn ngữ hiện tại."""
    return TEXTS.get(CURRENT_LANG, TEXTS["vi"]).get(key, key)


# ==================== QUẢN LÝ THƯ MỤC & FILE ====================
def ensure_data_dirs():
    """Tạo thư mục dữ liệu và file lịch sử nếu chưa có (không in thông báo)."""
    DATA_DIR.mkdir(exist_ok=True)
    CHATS_DIR.mkdir(exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps([], indent=2), encoding="utf-8")

def load_config() -> dict:
    """Đọc file cấu hình, trả về dict; nếu file không tồn tại trả về dict rỗng."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config: dict):
    """Ghi cấu hình ra file."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# ==================== CHỌN NGÔN NGỮ ====================
def language_selection_prompt() -> str:
    """
    Hiển thị prompt chọn ngôn ngữ (không phụ thuộc vào CURRENT_LANG hiện tại)
    Trả về 'en' hoặc 'vi'.
    """
    print("\n" + "=" * 60)
    print("🌐 Select language / Chọn ngôn ngữ:")
    print("1. English")
    print("2. Tiếng Việt")
    choice = input("Your choice / Lựa chọn của bạn (1/2): ").strip()
    return "en" if choice == "1" else "vi"

def setup_language(config: dict) -> str:
    """
    Xác định ngôn ngữ sử dụng:
    - Nếu trong config đã có language hợp lệ -> dùng nó.
    - Nếu chưa có -> hỏi người dùng và lưu lại.
    Trả về mã ngôn ngữ ('en'/'vi').
    """
    lang = config.get("language")
    if lang in ("en", "vi"):
        return lang
    # Chưa có hoặc không hợp lệ -> yêu cầu chọn
    new_lang = language_selection_prompt()
    config["language"] = new_lang
    save_config(config)
    return new_lang

def change_language(config: dict):
    """Đổi ngôn ngữ từ menu."""
    global CURRENT_LANG
    print("\n" + f"{Fore.CYAN}{get_text('lang_select_title')}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{get_text('lang_option_en')}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{get_text('lang_option_vi')}{Style.RESET_ALL}")
    choice = input(f"{Fore.YELLOW}{get_text('lang_prompt')}{Style.RESET_ALL}").strip()
    if choice == "1":
        CURRENT_LANG = "en"
    elif choice == "2":
        CURRENT_LANG = "vi"
    else:
        print(f"{Fore.RED}{get_text('lang_invalid')}{Style.RESET_ALL}")
        return
    config["language"] = CURRENT_LANG
    save_config(config)
    print(f"{Fore.GREEN}{get_text('lang_changed')}{Style.RESET_ALL}")


# ==================== QUẢN LÝ API KEY ====================
def get_api_key(config: dict) -> str:
    """Lấy API key từ config, nếu chưa có yêu cầu nhập."""
    api_key = config.get("api_key", "")
    if not api_key:
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
            return get_api_key(config)  # Gọi lại nếu bỏ trống
    return api_key


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
                    desc_parts.append("Supports: generateContent")
                    models[str(idx)] = {
                        "id": model_id,
                        "name": display_name,
                        "desc": " | ".join(desc_parts)
                    }
                    idx += 1
            if models:
                cache_data = {"timestamp": time.time(), "models": models}
                MODEL_CACHE_FILE.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"{Fore.GREEN}{get_text('found_models').format(len(models))}{Style.RESET_ALL}")
                return models
    except Exception as e:
        print(f"{Fore.YELLOW}{get_text('fetch_error').format(e)}{Style.RESET_ALL}")
    
    # Dùng cache nếu có và còn mới (dưới 24h)
    if MODEL_CACHE_FILE.exists():
        try:
            cache_data = json.loads(MODEL_CACHE_FILE.read_text(encoding="utf-8"))
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

def choose_model(api_key: str, config: dict) -> str:
    models = get_available_models(api_key)
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
def get_chat_file(chat_name: str) -> Path:
    safe_name = "".join(c for c in chat_name if c.isalnum() or c in "._-")
    if not safe_name:
        safe_name = "default"
    return CHATS_DIR / f"{safe_name}.json"

def load_chat(chat_name: str) -> list:
    chat_file = get_chat_file(chat_name)
    if chat_file.exists():
        data = json.loads(chat_file.read_text(encoding="utf-8"))
        return data.get("messages", [])
    return []

def save_chat(chat_name: str, messages: list):
    chat_file = get_chat_file(chat_name)
    chat_file.write_text(json.dumps({
        "name": chat_name,
        "messages": messages,
        "updated_at": datetime.now().isoformat()
    }, indent=2, ensure_ascii=False), encoding="utf-8")

def list_chats() -> list:
    chats = []
    for f in CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
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

def delete_chat(chat_name: str) -> bool:
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

def update_history(chat_name: str):
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except:
        history = []
    history = [h for h in history if h.get("name") != chat_name]
    history.insert(0, {
        "name": chat_name,
        "last_used": datetime.now().isoformat(),
        "message_count": len(load_chat(chat_name)) // 2
    })
    HISTORY_FILE.write_text(json.dumps(history[:50], indent=2, ensure_ascii=False), encoding="utf-8")

def show_history():
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
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
def call_gemini(api_key: str, messages: list, model_id: str) -> str:
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


# ==================== VÒNG LẶP CHAT ====================
def chat_loop(chat_name: str, api_key: str, model_id: str, config: dict):
    messages = load_chat(chat_name)
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}{get_text('chatting').format(chat_name)}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{get_text('model_label').format(model_id)}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{get_text('commands_label')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    # Hiển thị toàn bộ lịch sử
    if messages:
        print(f"{Fore.YELLOW}{get_text('history_label').format(len(messages)//2)}{Style.RESET_ALL}")
        for msg in messages:
            role_icon = f"{Fore.GREEN}{get_text('user_prefix')}" if msg["role"] == "user" else f"{Fore.MAGENTA}{get_text('gemini_prefix')}"
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
                new_model_id = choose_model(api_key, config)
                if new_model_id != model_id:
                    model_id = new_model_id
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


# ==================== MENU CHÍNH ====================
def main_menu():
    global CURRENT_LANG

    # 1. Đảm bảo thư mục dữ liệu (không in gì)
    ensure_data_dirs()

    # 2. Đọc cấu hình (có thể rỗng)
    config = load_config()

    # 3. Xác định ngôn ngữ (lưu ngay nếu chưa có)
    CURRENT_LANG = setup_language(config)

    # 4. Thông báo thư mục dữ liệu với ngôn ngữ hiện tại
    print(f"{Fore.BLUE}{get_text('data_dir').format(DATA_DIR)}{Style.RESET_ALL}")

    # 5. Lấy API key
    api_key = get_api_key(config)
    if not api_key:
        return

    # 6. Lấy model hiện tại và chat hiện tại
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
        print(f"{Fore.GREEN}{get_text('menu_change_lang')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{get_text('menu_exit')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")
        
        choice = input(f"{Fore.YELLOW}{get_text('prompt_choice')}{Style.RESET_ALL}").strip()
        
        if choice == "1":
            result = chat_loop(current_chat, api_key, current_model, config)
            if result == "new":
                new_name = input(f"{Fore.GREEN}{get_text('new_chat_name')}{Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                config["current_chat"] = current_chat
                save_config(config)
            elif result == "deleted":
                chats = list_chats()
                current_chat = chats[0]["name"] if chats else datetime.now().strftime("%Y%m%d_%H%M%S")
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
                config["current_chat"] = current_chat
                save_config(config)
                print(f"{Fore.GREEN}{get_text('switched_chat').format(current_chat)}{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}{get_text('enter_number')}{Style.RESET_ALL}")
        elif choice == "3":
            show_history()
        elif choice == "4":
            current_model = choose_model(api_key, config)
        elif choice == "5":
            new_key = input(f"{Fore.GREEN}{get_text('new_api_key')}{Style.RESET_ALL}").strip()
            if new_key:
                config["api_key"] = new_key
                save_config(config)
                api_key = new_key
                print(f"{Fore.GREEN}{get_text('api_key_updated')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}{get_text('invalid_api_key')}{Style.RESET_ALL}")
        elif choice == "6":
            change_language(config)
            # Sau khi đổi ngôn ngữ, CURRENT_LANG đã được cập nhật, các thông báo sau sẽ dùng ngôn ngữ mới
        elif choice == "7":
            print(f"{Fore.YELLOW}{get_text('goodbye')}{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}{get_text('invalid_choice')}{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}{get_text('goodbye')}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{get_text('error_unexpected').format(e)}{Style.RESET_ALL}")
        sys.exit(1)
