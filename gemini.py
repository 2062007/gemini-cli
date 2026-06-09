#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Extended with Code Generation & Execution
Phiên bản mở rộng: hỗ trợ viết code và chạy code (Python, JS, Ruby, Bash...)
"""

import json
import sys
import time
import threading
import itertools
import subprocess
import tempfile
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

import requests
from colorama import init, Fore, Style, Back

# Khởi tạo colorama (autoreset để tránh ảnh hưởng dòng sau)
init(autoreset=True)

# ==================== CẤU HÌNH ĐƯỜNG DẪN ====================
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "gemini_data"
CONFIG_FILE = DATA_DIR / "config.json"
CHATS_DIR = DATA_DIR / "chats"
HISTORY_FILE = DATA_DIR / "history.json"
MODEL_CACHE_FILE = DATA_DIR / "model_cache.json"

DEFAULT_MODEL_ID = "gemini-2.0-flash"

# ==================== TỪ ĐIỂN ĐA NGÔN NGỮ ====================
# Thêm các key mới cho tính năng code
TEXTS = {
    "en": {
        # ... (giữ nguyên toàn bộ các key cũ)
        # Bổ sung thêm:
        "code_help": "Usage: /code <language> <description>\nExample: /code python Calculate factorial of 5",
        "code_generating": "📝 Generating code for {}...",
        "code_generated": "✅ Generated code:",
        "code_run_prompt": "Run this code? (y/N): ",
        "code_running": "🚀 Running...",
        "code_output": "📤 Output:",
        "code_error": "❌ Error:",
        "code_not_found": "❌ No code block found in response.",
        "code_unsupported": "❌ Unsupported language: {}. Supported: python, javascript, js, ruby, bash, sh.",
        "code_runtime_missing": "⚠️  {} not installed. Install it to run {} code.",
        "code_saved": "💾 Code saved to temporary file: {}",
        # Định nghĩa lại đầy đủ tất cả các key cũ để tránh lỗi
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
        "model_list_title": "🤖 AVAILABLE MODELS (from Google API)",
        "current_model": "✅ Current model: {}",
        "pick_number": "👉 Enter number to see details and select (Enter to keep current)",
        "choice_prompt": "Your choice: ",
        "model_info_title": "📌 MODEL DETAILS: {}",
        "model_id": "🆔 ID: {}",
        "input_tokens": "📥 {}",
        "supports": "⚙️ {}",
        "desc_prefix": "📝 {}",
        "confirm_switch": "Do you want to switch to this model? (y/N): ",
        "switched": "✅ Switched to {}",
        "cancel_switch": "❌ Switch cancelled.",
        "invalid_choice": "❌ Invalid choice.",
        "keep_model": "Keeping current model.",
        "chatting": "💬 Chat: {}",
        "model_label": "📡 Model: {}",
        "commands_label": "📝 Commands: /menu | /new | /delete | /history | /model | /code | /quit",
        "history_label": "--- Full history ({} messages) ---",
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
        "model_changed": "✅ Model changed, you can continue chatting.",
        "main_title": "🤖 GEMINI CLI CHATBOT",
        "menu_continue": "1. Continue chat: {}",
        "menu_switch_chat": "2. Select / Create another chat",
        "menu_history": "3. View chat history",
        "menu_model": "4. Select Gemini model (auto‑updated)",
        "menu_change_key": "5. Change API key",
        "menu_change_lang": "6. Change language / Đổi ngôn ngữ",
        "menu_exit": "7. Exit",
        "prompt_choice": "🔹 Choice (1‑7): ",
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
        "lang_select_title": "🌐 Select language / Chọn ngôn ngữ:",
        "lang_option_en": "1. English",
        "lang_option_vi": "2. Tiếng Việt",
        "lang_prompt": "Your choice / Lựa chọn của bạn (1/2): ",
        "lang_changed_en": "✅ Language changed to English.",
        "lang_changed_vi": "✅ Đã chuyển sang Tiếng Việt.",
        "lang_invalid": "❌ Invalid choice, keeping current language.",
        "thinking": "Thinking...",
    },
    "vi": {
        "code_help": "Cách dùng: /code <ngôn ngữ> <mô tả>\nVí dụ: /code python Tính giai thừa của 5",
        "code_generating": "📝 Đang tạo code {}...",
        "code_generated": "✅ Code đã tạo:",
        "code_run_prompt": "Chạy đoạn code này? (y/N): ",
        "code_running": "🚀 Đang chạy...",
        "code_output": "📤 Kết quả:",
        "code_error": "❌ Lỗi:",
        "code_not_found": "❌ Không tìm thấy khối code trong phản hồi.",
        "code_unsupported": "❌ Ngôn ngữ không hỗ trợ: {}. Hỗ trợ: python, javascript, js, ruby, bash, sh.",
        "code_runtime_missing": "⚠️  {} chưa được cài đặt. Hãy cài để chạy code {}.",
        "code_saved": "💾 Code đã lưu vào file tạm: {}",
        # Các key cũ giữ nguyên
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
        "model_list_title": "🤖 DANH SÁCH MODEL KHẢ DỤNG (từ Google API)",
        "current_model": "✅ Model hiện tại: {}",
        "pick_number": "👉 Nhập số để xem chi tiết và chọn (Enter để giữ nguyên)",
        "choice_prompt": "Lựa chọn: ",
        "model_info_title": "📌 CHI TIẾT MODEL: {}",
        "model_id": "🆔 ID: {}",
        "input_tokens": "📥 {}",
        "supports": "⚙️ {}",
        "desc_prefix": "📝 {}",
        "confirm_switch": "Bạn có muốn chuyển sang model này không? (y/N): ",
        "switched": "✅ Đã đổi sang {}",
        "cancel_switch": "❌ Hủy chuyển đổi.",
        "invalid_choice": "❌ Lựa chọn không hợp lệ.",
        "keep_model": "Giữ nguyên model hiện tại.",
        "chatting": "💬 Đoạn chat: {}",
        "model_label": "📡 Model: {}",
        "commands_label": "📝 Lệnh: /menu | /new | /delete | /history | /model | /code | /quit",
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
        "main_title": "🤖 GEMINI CLI CHATBOT",
        "menu_continue": "1. Tiếp tục chat: {}",
        "menu_switch_chat": "2. Chọn / Tạo đoạn chat khác",
        "menu_history": "3. Xem lịch sử các đoạn chat",
        "menu_model": "4. Chọn Model Gemini (tự động cập nhật)",
        "menu_change_key": "5. Đổi API key",
        "menu_change_lang": "6. Thay đổi ngôn ngữ / Change language",
        "menu_exit": "7. Thoát",
        "prompt_choice": "🔹 Lựa chọn (1‑7): ",
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
        "lang_select_title": "🌐 Chọn ngôn ngữ / Select language:",
        "lang_option_en": "1. English",
        "lang_option_vi": "2. Tiếng Việt",
        "lang_prompt": "Lựa chọn của bạn / Your choice (1/2): ",
        "lang_changed_en": "✅ Language changed to English.",
        "lang_changed_vi": "✅ Đã chuyển sang Tiếng Việt.",
        "lang_invalid": "❌ Lựa chọn không hợp lệ, giữ ngôn ngữ hiện tại.",
        "thinking": "Đang suy nghĩ...",
    }
}

# ==================== TIỆN ÍCH HIỂN THỊ ====================
def print_box(text: str, color=Fore.CYAN, width=60):
    print(f"{color}╔{'═'*width}╗")
    for line in text.splitlines():
        print(f"║ {line}{' '*(width-1-len(line))}║")
    print(f"╚{'═'*width}╝{Style.RESET_ALL}")

def print_separator(char="─", color=Fore.CYAN, width=60):
    print(f"{color}{char*width}{Style.RESET_ALL}")

def loading_animation(stop_event, prefix="Thinking"):
    for c in itertools.cycle('|/-\\'):
        if stop_event.is_set():
            break
        sys.stdout.write(f"\r{Fore.YELLOW}{prefix} {c}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " "* (len(prefix)+2) + "\r")

# ==================== LỚP CHATBOT CHÍNH ====================
class GeminiChatbot:
    def __init__(self):
        self.lang = "vi"
        self.config = {}
        self.api_key = ""
        self.current_model = DEFAULT_MODEL_ID
        self.current_chat = "default"

        DATA_DIR.mkdir(exist_ok=True)
        CHATS_DIR.mkdir(exist_ok=True)
        if not HISTORY_FILE.exists():
            HISTORY_FILE.write_text(json.dumps([], indent=2), encoding="utf-8")

    def t(self, key: str, *args) -> str:
        text = TEXTS.get(self.lang, TEXTS["vi"]).get(key, key)
        if args:
            return text.format(*args)
        return text

    # ==================== QUẢN LÝ CẤU HÌNH ====================
    def load_config(self):
        if CONFIG_FILE.exists():
            self.config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        else:
            self.config = {}
        self.lang = self.config.get("language", "vi")
        self.api_key = self.config.get("api_key", "")
        self.current_model = self.config.get("model", DEFAULT_MODEL_ID)
        self.current_chat = self.config.get("current_chat", "default")

    def save_config(self):
        self.config.update({
            "language": self.lang,
            "api_key": self.api_key,
            "model": self.current_model,
            "current_chat": self.current_chat
        })
        CONFIG_FILE.write_text(json.dumps(self.config, indent=2, ensure_ascii=False), encoding="utf-8")

    def initial_language_setup(self):
        if self.lang not in ("en", "vi"):
            print("\n" + "=" * 60)
            print("🌐 Select language / Chọn ngôn ngữ:")
            print("1. English")
            print("2. Tiếng Việt")
            choice = input("Your choice / Lựa chọn của bạn (1/2): ").strip()
            self.lang = "en" if choice == "1" else "vi"
            self.save_config()

    def change_language(self):
        print(f"\n{Fore.CYAN}{self.t('lang_select_title')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{self.t('lang_option_en')}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{self.t('lang_option_vi')}{Style.RESET_ALL}")
        choice = input(f"{Fore.YELLOW}{self.t('lang_prompt')}{Style.RESET_ALL}").strip()
        if choice == "1":
            self.lang = "en"
            print(f"{Fore.GREEN}{self.t('lang_changed_en')}{Style.RESET_ALL}")
        elif choice == "2":
            self.lang = "vi"
            print(f"{Fore.GREEN}{self.t('lang_changed_vi')}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{self.t('lang_invalid')}{Style.RESET_ALL}")
            return
        self.save_config()

    def get_api_key(self):
        if not self.api_key:
            print(f"\n{Fore.YELLOW}{self.t('no_api_key')}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{self.t('get_api_key_url')}{Style.RESET_ALL}")
            api_key = input(f"{Fore.GREEN}{self.t('enter_api_key')}{Style.RESET_ALL}").strip()
            if api_key:
                self.api_key = api_key
                self.save_config()
                print(f"{Fore.GREEN}{self.t('api_key_saved')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}{self.t('api_key_empty')}{Style.RESET_ALL}")
                return self.get_api_key()
        return self.api_key

    def fetch_models_from_api(self) -> Optional[Dict[str, Dict]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        print(f"{Fore.CYAN}{self.t('fetching_models')}{Style.RESET_ALL}")
        stop_event = threading.Event()
        t = threading.Thread(target=loading_animation, args=(stop_event, "Fetching"))
        t.start()
        try:
            resp = requests.get(url, timeout=10)
            stop_event.set()
            t.join()
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
                    print(f"{Fore.GREEN}{self.t('found_models', len(models))}{Style.RESET_ALL}")
                    return models
        except Exception as e:
            stop_event.set()
            t.join()
            print(f"{Fore.YELLOW}{self.t('fetch_error', e)}{Style.RESET_ALL}")

        if MODEL_CACHE_FILE.exists():
            try:
                cache_data = json.loads(MODEL_CACHE_FILE.read_text(encoding="utf-8"))
                if time.time() - cache_data.get("timestamp", 0) < 86400:
                    print(f"{Fore.BLUE}{self.t('using_cache')}{Style.RESET_ALL}")
                    return cache_data.get("models")
            except:
                pass
        return None

    def get_available_models(self) -> Dict[str, Dict]:
        models = self.fetch_models_from_api()
        if models:
            return models
        print(f"{Fore.YELLOW}{self.t('using_fallback')}{Style.RESET_ALL}")
        return {
            "1": {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "desc": "Popular, fast, stable."},
            "2": {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "desc": "Lightweight, cost-effective."},
            "3": {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "desc": "Powerful, 2M context."},
        }

    def choose_model(self):
        models = self.get_available_models()
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}{self.t('model_list_title')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")
        for key, m in models.items():
            marker = "✅ " if m["id"] == self.current_model else "   "
            print(f"{Fore.GREEN}{marker}{key}. {Fore.WHITE}{m['name']}")
        print(f"\n{Fore.YELLOW}{self.t('pick_number')}{Style.RESET_ALL}")
        choice = input(f"{Fore.GREEN}{self.t('choice_prompt')}{Style.RESET_ALL}").strip()
        if choice in models:
            selected = models[choice]
            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"{Fore.MAGENTA}{self.t('model_info_title', selected['name'])}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}")
            print(f"{Fore.YELLOW}{self.t('model_id', selected['id'])}{Style.RESET_ALL}")
            for part in selected['desc'].split(' | '):
                if part.startswith("Input:"):
                    print(f"{Fore.YELLOW}{self.t('input_tokens', part)}{Style.RESET_ALL}")
                elif part.startswith("Supports:"):
                    print(f"{Fore.YELLOW}{self.t('supports', part)}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}{self.t('desc_prefix', part)}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}")
            confirm = input(f"\n{Fore.GREEN}{self.t('confirm_switch')}{Style.RESET_ALL}").strip().lower()
            if confirm == 'y':
                self.current_model = selected["id"]
                self.save_config()
                print(f"{Fore.GREEN}{self.t('switched', selected['name'])}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{self.t('cancel_switch')}{Style.RESET_ALL}")
        elif choice != "":
            print(f"{Fore.RED}{self.t('invalid_choice')}{Style.RESET_ALL}")

    def _chat_file_path(self, chat_name: str) -> Path:
        safe_name = "".join(c for c in chat_name if c.isalnum() or c in "._-")
        if not safe_name:
            safe_name = "default"
        return CHATS_DIR / f"{safe_name}.json"

    def load_messages(self, chat_name: str) -> list:
        path = self._chat_file_path(chat_name)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("messages", [])
        return []

    def save_messages(self, chat_name: str, messages: list):
        path = self._chat_file_path(chat_name)
        path.write_text(json.dumps({
            "name": chat_name,
            "messages": messages,
            "updated_at": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_chats(self) -> list:
        chats = []
        for f in sorted(CHATS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
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
        return chats

    def delete_chat(self, chat_name: str) -> bool:
        path = self._chat_file_path(chat_name)
        if path.exists():
            confirm = input(f"{Fore.RED}{self.t('delete_confirm', chat_name)}{Style.RESET_ALL}")
            if confirm.lower() == 'y':
                path.unlink()
                print(f"{Fore.GREEN}{self.t('deleted', chat_name)}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.YELLOW}{self.t('delete_cancelled')}{Style.RESET_ALL}")
                return False
        else:
            print(f"{Fore.RED}{self.t('not_found_chat', chat_name)}{Style.RESET_ALL}")
            return False

    def update_history(self, chat_name: str):
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except:
            history = []
        history = [h for h in history if h.get("name") != chat_name]
        history.insert(0, {
            "name": chat_name,
            "last_used": datetime.now().isoformat(),
            "message_count": len(self.load_messages(chat_name)) // 2
        })
        HISTORY_FILE.write_text(json.dumps(history[:50], indent=2, ensure_ascii=False), encoding="utf-8")

    def show_history(self):
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except:
            history = []
        if not history:
            print(f"{Fore.YELLOW}{self.t('no_history')}{Style.RESET_ALL}")
            return
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}{self.t('history_title')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")
        for i, h in enumerate(history, 1):
            name = h.get("name", "Unknown")
            msg_count = h.get("message_count", 0)
            last_used = h.get("last_used", "Unknown")[:16]
            print(f"{Fore.GREEN}{i:2d}. {Fore.WHITE}{name}")
            print(f"      {Fore.BLUE}📝 {msg_count} messages | 🕐 {last_used}")
        print(f"{Fore.CYAN}{'='*60}\n")

    def call_gemini(self, messages: list) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.current_model}:generateContent?key={self.api_key}"
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        payload = {"contents": contents}
        stop_event = threading.Event()
        t = threading.Thread(target=loading_animation, args=(stop_event, self.t("thinking")))
        t.start()
        try:
            response = requests.post(url, json=payload, timeout=30)
            stop_event.set()
            t.join()
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
            stop_event.set()
            t.join()
            return f"{Fore.RED}❌ Timeout: Gemini not responding (30s){Style.RESET_ALL}"
        except requests.exceptions.ConnectionError:
            stop_event.set()
            t.join()
            return f"{Fore.RED}❌ Connection error: Check internet{Style.RESET_ALL}"
        except Exception as e:
            stop_event.set()
            t.join()
            return f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}"

    # ==================== TÍNH NĂNG VIẾT & CHẠY CODE ====================
    def execute_code(self, language: str, code: str) -> str:
        """Thực thi code tùy theo ngôn ngữ, trả về output."""
        # Mapping ngôn ngữ -> file extension và command
        lang_map = {
            "python": ("py", ["python3", "-c", code]),
            "javascript": ("js", ["node", "-e", code]),
            "js": ("js", ["node", "-e", code]),
            "ruby": ("rb", ["ruby", "-e", code]),
            "bash": ("sh", ["bash", "-c", code]),
            "sh": ("sh", ["bash", "-c", code])
        }
        if language not in lang_map:
            return f"Unsupported language: {language}"
        ext, cmd = lang_map[language]
        # Kiểm tra runtime có tồn tại không (ngoại trừ python3, node, ruby, bash)
        runtime = cmd[0]
        if not shutil.which(runtime):
            return self.t("code_runtime_missing", runtime, language)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            out = result.stdout
            if result.stderr:
                out += f"\n{Fore.RED}STDERR:\n{result.stderr}{Style.RESET_ALL}"
            return out.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return "❌ Code execution timed out (30s)"
        except Exception as e:
            return f"❌ Execution error: {e}"

    def handle_code_command(self, args: str):
        """Xử lý lệnh /code <language> <description>"""
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            print(f"{Fore.YELLOW}{self.t('code_help')}{Style.RESET_ALL}")
            return
        language = parts[0].lower()
        description = parts[1]

        supported = ["python", "javascript", "js", "ruby", "bash", "sh"]
        if language not in supported:
            print(f"{Fore.RED}{self.t('code_unsupported', language)}{Style.RESET_ALL}")
            return

        # Tạo prompt để Gemini viết code
        prompt = f"Write a {language} program that {description}. Only output the code, no explanation."
        print(f"{Fore.CYAN}{self.t('code_generating', language)}...{Style.RESET_ALL}")

        # Gọi Gemini với prompt đơn giản (không lưu vào lịch sử chat chính)
        messages = [{"role": "user", "content": prompt}]
        response = self.call_gemini(messages)
        # Tách code block nếu có
        code = self.extract_code_from_response(response)
        if not code:
            print(f"{Fore.RED}{self.t('code_not_found')}{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}{self.t('code_generated')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*40}{Style.RESET_ALL}")
        print(code)
        print(f"{Fore.CYAN}{'─'*40}{Style.RESET_ALL}")

        # Hỏi có chạy không
        run_confirm = input(f"{Fore.YELLOW}{self.t('code_run_prompt')}{Style.RESET_ALL}").strip().lower()
        if run_confirm != 'y':
            return

        print(f"{Fore.BLUE}{self.t('code_running')}{Style.RESET_ALL}")
        output = self.execute_code(language, code)
        print(f"{Fore.GREEN}{self.t('code_output')}{Style.RESET_ALL}")
        print(output)
        print()

    def extract_code_from_response(self, text: str) -> Optional[str]:
        """Trích xuất code từ phản hồi của Gemini (có thể trong ``` blocks)."""
        import re
        # Tìm code block với hoặc không có ngôn ngữ
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return "\n".join(matches)  # Ghép nếu nhiều block
        # Nếu không có code block, trả về toàn bộ text (có thể là code thuần)
        # Lọc bỏ các dòng giải thích ngắn?
        return text.strip()

    def chat_loop(self):
        messages = self.load_messages(self.current_chat)
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}{self.t('chatting', self.current_chat)}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{self.t('model_label', self.current_model)}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{self.t('commands_label')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}\n")

        if messages:
            print(f"{Fore.YELLOW}{self.t('history_label', len(messages)//2)}{Style.RESET_ALL}")
            for msg in messages:
                role_icon = f"{Fore.GREEN}{self.t('user_prefix')}" if msg["role"] == "user" else f"{Fore.MAGENTA}{self.t('gemini_prefix')}"
                content = msg['content'].replace('\n', '\n           ')
                print(f"{role_icon}: {content}")
            print()

        while True:
            try:
                user_input = input(f"{Fore.GREEN}{self.t('user_prefix')}{Style.RESET_ALL}: ").strip()
                if not user_input:
                    continue

                cmd = user_input.lower()
                if cmd.startswith("/code"):
                    # Tách phần tham số
                    args = user_input[5:].strip()  # Bỏ "/code"
                    self.handle_code_command(args)
                    continue
                elif cmd in ["/menu", "/back"]:
                    self.update_history(self.current_chat)
                    return "menu"
                elif cmd == "/new":
                    self.update_history(self.current_chat)
                    return "new"
                elif cmd == "/delete":
                    if self.delete_chat(self.current_chat):
                        return "deleted"
                    continue
                elif cmd == "/history":
                    self.show_history()
                    continue
                elif cmd == "/model":
                    self.choose_model()
                    print(f"{Fore.GREEN}{self.t('model_changed')}{Style.RESET_ALL}")
                    continue
                elif cmd == "/quit":
                    self.update_history(self.current_chat)
                    return "quit"
                else:
                    messages.append({"role": "user", "content": user_input})
                    print(f"{Fore.MAGENTA}{self.t('gemini_prefix')}{Style.RESET_ALL}: ", end="", flush=True)
                    response = self.call_gemini(messages)
                    print(response)
                    messages.append({"role": "assistant", "content": response})
                    self.save_messages(self.current_chat, messages)
                    self.update_history(self.current_chat)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}{self.t('goodbye')}{Style.RESET_ALL}")
                self.update_history(self.current_chat)
                return "quit"

    # Main menu giữ nguyên như cũ, chỉ thêm dòng lệnh nhắc (đã update trong TEXTS)
    def main_menu(self):
        self.load_config()
        self.initial_language_setup()
        print(f"{Fore.BLUE}{self.t('data_dir', DATA_DIR)}{Style.RESET_ALL}")
        if not self.get_api_key():
            return

        while True:
            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"{Fore.MAGENTA}{self.t('main_title')}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}")
            print(f"{Fore.GREEN}{self.t('menu_continue', self.current_chat)}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{self.t('menu_switch_chat')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{self.t('menu_history')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{self.t('menu_model')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{self.t('menu_change_key')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{self.t('menu_change_lang')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{self.t('menu_exit')}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}")

            choice = input(f"{Fore.YELLOW}{self.t('prompt_choice')}{Style.RESET_ALL}").strip()

            if choice == "1":
                result = self.chat_loop()
                if result == "new":
                    new_name = input(f"{Fore.GREEN}{self.t('new_chat_name')}{Style.RESET_ALL}").strip()
                    if not new_name:
                        new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.current_chat = new_name
                    self.save_config()
                elif result == "deleted":
                    chats = self.list_chats()
                    self.current_chat = chats[0]["name"] if chats else datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.save_config()
                elif result == "quit":
                    break

            elif choice == "2":
                chats = self.list_chats()
                if not chats:
                    print(f"{Fore.YELLOW}{self.t('no_chats')}{Style.RESET_ALL}")
                    new_name = input(f"{Fore.GREEN}{self.t('new_chat_name')}{Style.RESET_ALL}").strip()
                    if not new_name:
                        new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.current_chat = new_name
                    self.save_config()
                    continue

                print(f"\n{Fore.CYAN}{self.t('chat_list_title')}{Style.RESET_ALL}")
                for i, c in enumerate(chats, 1):
                    print(self.t('chat_item', i, c['name'], c['msg_count']))
                print(self.t('new_chat_option'))

                try:
                    sel = int(input(f"{Fore.YELLOW}{self.t('select_number')}{Style.RESET_ALL}"))
                    if sel == 0:
                        new_name = input(f"{Fore.GREEN}{self.t('new_chat_name')}{Style.RESET_ALL}").strip()
                        if not new_name:
                            new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                        self.current_chat = new_name
                    elif 1 <= sel <= len(chats):
                        self.current_chat = chats[sel-1]["name"]
                    else:
                        continue
                    self.save_config()
                    print(f"{Fore.GREEN}{self.t('switched_chat', self.current_chat)}{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}{self.t('enter_number')}{Style.RESET_ALL}")

            elif choice == "3":
                self.show_history()

            elif choice == "4":
                self.choose_model()

            elif choice == "5":
                new_key = input(f"{Fore.GREEN}{self.t('new_api_key')}{Style.RESET_ALL}").strip()
                if new_key:
                    self.api_key = new_key
                    self.save_config()
                    print(f"{Fore.GREEN}{self.t('api_key_updated')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}{self.t('invalid_api_key')}{Style.RESET_ALL}")

            elif choice == "6":
                self.change_language()

            elif choice == "7":
                print(f"{Fore.YELLOW}{self.t('goodbye')}{Style.RESET_ALL}")
                break

            else:
                print(f"{Fore.RED}{self.t('invalid_choice')}{Style.RESET_ALL}")

# ==================== ĐIỂM KHỞI ĐẦU ====================
if __name__ == "__main__":
    try:
        bot = GeminiChatbot()
        bot.main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}{TEXTS['vi']['goodbye']}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        sys.exit(1)
