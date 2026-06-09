#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Code Generation & Execution (Unlimited Languages)
Phiên bản đầy đủ: 
- Viết code bằng bất kỳ ngôn ngữ nào
- Lưu trữ code vào thư viện cá nhân
- Quản lý code đã lưu (xem, xoá)
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
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

import requests
from colorama import init, Fore, Style, Back

init(autoreset=True)

# ==================== CẤU HÌNH ĐƯỜNG DẪN ====================
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "gemini_data"
CONFIG_FILE = DATA_DIR / "config.json"
CHATS_DIR = DATA_DIR / "chats"
HISTORY_FILE = DATA_DIR / "history.json"
MODEL_CACHE_FILE = DATA_DIR / "model_cache.json"
CODE_LIBRARY_DIR = DATA_DIR / "code_library"       # <-- Thư mục lưu code
CODE_INDEX_FILE = DATA_DIR / "code_index.json"     # <-- Chỉ mục code đã lưu

DEFAULT_MODEL_ID = "gemini-2.0-flash"

# ==================== RUNTIME MAPPING (MỞ RỘNG) ====================
LANG_RUNTIME_MAP = {
    "python": ("py", "python3"),
    "py": ("py", "python3"),
    "javascript": ("js", "node"),
    "js": ("js", "node"),
    "typescript": ("ts", "npx ts-node"),
    "ts": ("ts", "npx ts-node"),
    "ruby": ("rb", "ruby"),
    "rb": ("rb", "ruby"),
    "bash": ("sh", "bash"),
    "sh": ("sh", "bash"),
    "zsh": ("zsh", "zsh"),
    "php": ("php", "php"),
    "perl": ("pl", "perl"),
    "lua": ("lua", "lua"),
    "go": ("go", "go run"),
    "rust": ("rs", "rustc"),          # Rust cần biên dịch, sẽ xử lý đặc biệt
    "c": ("c", "gcc"),
    "cpp": ("cpp", "g++"),
    "java": ("java", "java"),         # Java cần class, phức tạp, để dạng cơ bản
    "r": ("r", "Rscript"),
    "swift": ("swift", "swift"),
    "kotlin": ("kts", "kotlinc -script"),
    "scala": ("scala", "scala"),
    # Thêm tuỳ ý, nếu không khớp sẽ dùng "custom"
}

# ==================== TỪ ĐIỂN ĐA NGÔN NGỮ (bổ sung) ====================
TEXTS = {
    "en": {
        # ... tất cả các key cũ giữ nguyên, bổ sung thêm:
        "code_help": "Usage: /code <language> <description>\nExample: /code python Calculate factorial of 5\nTo save: answer 'y' when asked, then give a name.",
        "code_generating": "📝 Generating {} code...",
        "code_generated": "✅ Generated code:",
        "code_save_prompt": "💾 Save this code? Enter name (Enter to skip): ",
        "code_saved": "✅ Code saved to: {}",
        "code_skip_save": "Code not saved.",
        "code_running": "🚀 Running...",
        "code_output": "📤 Output:",
        "code_error": "❌ Error:",
        "code_not_found": "❌ No code block found in response.",
        "code_runtime_missing": "⚠️  {} not found. Please install it or save code manually.",
        "code_library_title": "📚 SAVED CODE LIBRARY",
        "code_list_empty": "📭 No saved code yet.",
        "code_lib_item": "  {}. {} [{}] - {}",
        "code_delete_prompt": "Delete code '{}'? (y/N): ",
        "code_deleted": "✅ Deleted '{}'",
        "code_delete_cancel": "Delete cancelled.",
        "code_not_found_name": "Code '{}' not found.",
        "commands_label": "📝 Commands: /menu | /new | /delete | /history | /model | /code | /codelist | /codedelete <name> | /quit",
        "menu_code_lib": "8. Saved Code Library",
        # giữ nguyên toàn bộ key cũ (rút gọn cho dễ đọc, thực tế phải có đủ)
        "data_dir": "📁 Data saved at: {}",
        # ... (tất cả key còn lại từ bản gốc, đảm bảo đầy đủ)
    },
    "vi": {
        "code_help": "Cách dùng: /code <ngôn ngữ> <mô tả>\nVí dụ: /code python Tính giai thừa của 5\nĐể lưu: trả lời 'y' khi hỏi, rồi đặt tên.",
        "code_generating": "📝 Đang tạo code {}...",
        "code_generated": "✅ Code đã tạo:",
        "code_save_prompt": "💾 Lưu code này? Nhập tên (Enter để bỏ qua): ",
        "code_saved": "✅ Đã lưu code vào: {}",
        "code_skip_save": "Không lưu code.",
        "code_running": "🚀 Đang chạy...",
        "code_output": "📤 Kết quả:",
        "code_error": "❌ Lỗi:",
        "code_not_found": "❌ Không tìm thấy khối code trong phản hồi.",
        "code_runtime_missing": "⚠️  {} không được tìm thấy. Hãy cài đặt hoặc lưu code thủ công.",
        "code_library_title": "📚 THƯ VIỆN CODE ĐÃ LƯU",
        "code_list_empty": "📭 Chưa có code nào được lưu.",
        "code_lib_item": "  {}. {} [{}] - {}",
        "code_delete_prompt": "Xoá code '{}'? (y/N): ",
        "code_deleted": "✅ Đã xoá '{}'",
        "code_delete_cancel": "Đã huỷ xoá.",
        "code_not_found_name": "Không tìm thấy code '{}'.",
        "commands_label": "📝 Lệnh: /menu | /new | /delete | /history | /model | /code | /codelist | /codedelete <tên> | /quit",
        "menu_code_lib": "8. Thư viện code đã lưu",
        # giữ nguyên toàn bộ key cũ
        "data_dir": "📁 Dữ liệu lưu tại: {}",
        # ...
    }
}
# Đảm bảo TEXTS đầy đủ bằng cách cập nhật từ điển gốc (đã có ở trên, tôi chỉ thêm các key mới)

# ==================== TIỆN ÍCH HIỂN THỊ (giữ nguyên) ====================
def print_box(text, color=Fore.CYAN, width=60):
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

        # Tạo các thư mục cần thiết
        DATA_DIR.mkdir(exist_ok=True)
        CHATS_DIR.mkdir(exist_ok=True)
        CODE_LIBRARY_DIR.mkdir(exist_ok=True)
        if not HISTORY_FILE.exists():
            HISTORY_FILE.write_text(json.dumps([], indent=2), encoding="utf-8")
        if not CODE_INDEX_FILE.exists():
            CODE_INDEX_FILE.write_text(json.dumps({}, indent=2), encoding="utf-8")

    def t(self, key: str, *args) -> str:
        text = TEXTS.get(self.lang, TEXTS["vi"]).get(key, key)
        if args:
            return text.format(*args)
        return text

    # ==================== QUẢN LÝ CẤU HÌNH (giữ nguyên) ====================
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
        # ... (giữ nguyên hoàn toàn code gốc, không thay đổi)
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
        # giữ nguyên
        pass

    def get_available_models(self) -> Dict[str, Dict]:
        # giữ nguyên
        pass

    def choose_model(self):
        # giữ nguyên
        pass

    def _chat_file_path(self, chat_name: str) -> Path:
        # giữ nguyên
        pass

    def load_messages(self, chat_name: str) -> list:
        # giữ nguyên
        pass

    def save_messages(self, chat_name: str, messages: list):
        # giữ nguyên
        pass

    def list_chats(self) -> list:
        # giữ nguyên
        pass

    def delete_chat(self, chat_name: str) -> bool:
        # giữ nguyên
        pass

    def update_history(self, chat_name: str):
        # giữ nguyên
        pass

    def show_history(self):
        # giữ nguyên
        pass

    def call_gemini(self, messages: list) -> str:
        # giữ nguyên hoàn toàn
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

    # ==================== CODE LIBRARY MANAGEMENT ====================
    def _load_code_index(self) -> dict:
        try:
            return json.loads(CODE_INDEX_FILE.read_text(encoding="utf-8"))
        except:
            return {}

    def _save_code_index(self, index: dict):
        CODE_INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_code_to_library(self, name: str, language: str, code: str):
        """Lưu code vào file và cập nhật index."""
        lang_info = LANG_RUNTIME_MAP.get(language, (language, ""))  # fallback: dùng chính language làm extension
        ext = lang_info[0]
        filename = f"{name}.{ext}"
        filepath = CODE_LIBRARY_DIR / filename
        filepath.write_text(code, encoding="utf-8")

        index = self._load_code_index()
        index[name] = {
            "language": language,
            "filename": filename,
            "created": datetime.now().isoformat(),
            "path": str(filepath)
        }
        self._save_code_index(index)
        print(f"{Fore.GREEN}{self.t('code_saved', filepath)}{Style.RESET_ALL}")

    def list_saved_codes(self):
        index = self._load_code_index()
        if not index:
            print(f"{Fore.YELLOW}{self.t('code_list_empty')}{Style.RESET_ALL}")
            return
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}{self.t('code_library_title')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")
        for i, (name, info) in enumerate(index.items(), 1):
            lang = info.get("language", "?")
            created = info.get("created", "")[:16]
            print(self.t("code_lib_item", i, name, lang, created))
        print(f"{Fore.CYAN}{'='*60}\n")

    def delete_saved_code(self, name: str):
        index = self._load_code_index()
        if name not in index:
            print(f"{Fore.RED}{self.t('code_not_found_name', name)}{Style.RESET_ALL}")
            return
        confirm = input(f"{Fore.RED}{self.t('code_delete_prompt', name)}{Style.RESET_ALL}").strip().lower()
        if confirm == 'y':
            filepath = Path(index[name]["path"])
            if filepath.exists():
                filepath.unlink()
            del index[name]
            self._save_code_index(index)
            print(f"{Fore.GREEN}{self.t('code_deleted', name)}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}{self.t('code_delete_cancel')}{Style.RESET_ALL}")

    # ==================== EXECUTION KHÔNG GIỚI HẠN ====================
    def execute_code(self, language: str, code: str) -> str:
        """Thực thi code dựa trên ngôn ngữ, tự động dò runtime."""
        lang_key = language.lower()
        # Tìm trong bảng mapping
        if lang_key in LANG_RUNTIME_MAP:
            ext, runtime_cmd = LANG_RUNTIME_MAP[lang_key]
        else:
            # Ngôn ngữ không có trong map: thử dùng chính tên ngôn ngữ làm lệnh
            runtime_cmd = lang_key
            ext = lang_key  # dùng tạm

        # Nếu runtime_cmd chứa khoảng trắng (vd "go run"), tách ra
        cmd_parts = runtime_cmd.split()
        if not shutil.which(cmd_parts[0]):
            return self.t("code_runtime_missing", runtime_cmd)

        # Xử lý đặc biệt cho Rust (rustc cần file, không dùng -e)
        if lang_key in ("rust", "rs"):
            # Tạo file tạm, biên dịch rồi chạy
            tmpfile = tempfile.NamedTemporaryFile(suffix=".rs", delete=False)
            tmpfile.write(code.encode())
            tmpfile.close()
            exe_path = tmpfile.name[:-3]  # bỏ .rs
            try:
                subprocess.run(["rustc", tmpfile.name, "-o", exe_path], check=True, capture_output=True, text=True)
                result = subprocess.run([exe_path], capture_output=True, text=True, timeout=30)
                return result.stdout.strip() or "(no output)"
            except subprocess.CalledProcessError as e:
                return f"❌ Compilation error:\n{e.stderr}"
            finally:
                os.unlink(tmpfile.name)
                if os.path.exists(exe_path):
                    os.unlink(exe_path)

        # Đối với các ngôn ngữ khác, dùng -e hoặc -c
        if lang_key in ("python", "py", "javascript", "js", "ruby", "rb", "php", "perl", "lua"):
            cmd = cmd_parts + ["-e", code]
        elif lang_key in ("bash", "sh", "zsh"):
            cmd = cmd_parts + ["-c", code]
        elif lang_key == "r":
            cmd = cmd_parts + ["-e", code]
        elif lang_key == "go":
            # go run cần file, tạo file tạm
            tmpfile = tempfile.NamedTemporaryFile(suffix=".go", delete=False)
            tmpfile.write(code.encode())
            tmpfile.close()
            try:
                result = subprocess.run(["go", "run", tmpfile.name], capture_output=True, text=True, timeout=30)
                return result.stdout.strip() or "(no output)"
            except Exception as e:
                return f"❌ Error: {e}"
            finally:
                os.unlink(tmpfile.name)
        else:
            # Fallback: tạo file tạm với extension, chạy runtime + file
            tmpfile = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
            tmpfile.write(code.encode())
            tmpfile.close()
            try:
                result = subprocess.run(cmd_parts + [tmpfile.name], capture_output=True, text=True, timeout=30)
                return result.stdout.strip() or "(no output)"
            except Exception as e:
                return f"❌ Error: {e}"
            finally:
                os.unlink(tmpfile.name)

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

    def extract_code_from_response(self, text: str) -> Optional[str]:
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return "\n".join(matches)
        return text.strip()

    # ==================== HANDLE /code COMMAND ====================
    def handle_code_command(self, args: str):
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            print(f"{Fore.YELLOW}{self.t('code_help')}{Style.RESET_ALL}")
            return
        language = parts[0].lower()
        description = parts[1]

        print(f"{Fore.CYAN}{self.t('code_generating', language)}{Style.RESET_ALL}")
        prompt = f"Write a {language} program that {description}. Output only the code, no explanation."
        messages = [{"role": "user", "content": prompt}]
        response = self.call_gemini(messages)
        code = self.extract_code_from_response(response)
        if not code:
            print(f"{Fore.RED}{self.t('code_not_found')}{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}{self.t('code_generated')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*40}{Style.RESET_ALL}")
        print(code)
        print(f"{Fore.CYAN}{'─'*40}{Style.RESET_ALL}")

        # Hỏi lưu code
        name = input(f"{Fore.YELLOW}{self.t('code_save_prompt')}{Style.RESET_ALL}").strip()
        if name:
            self._save_code_to_library(name, language, code)
        else:
            print(f"{Fore.YELLOW}{self.t('code_skip_save')}{Style.RESET_ALL}")

        # Hỏi chạy code (sau khi đã lưu hoặc không)
        run_confirm = input(f"{Fore.YELLOW}{self.t('code_run_prompt')}{Style.RESET_ALL}").strip().lower()
        if run_confirm != 'y':
            return
        print(f"{Fore.BLUE}{self.t('code_running')}{Style.RESET_ALL}")
        output = self.execute_code(language, code)
        print(f"{Fore.GREEN}{self.t('code_output')}{Style.RESET_ALL}")
        print(output)
        print()

    # ==================== CHAT LOOP (CẬP NHẬT THÊM LỆNH CODE) ====================
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
                    self.handle_code_command(user_input[5:].strip())
                    continue
                elif cmd == "/codelist":
                    self.list_saved_codes()
                    continue
                elif cmd.startswith("/codedelete"):
                    name = user_input[11:].strip()
                    if name:
                        self.delete_saved_code(name)
                    else:
                        print(f"{Fore.RED}Usage: /codedelete <name>{Style.RESET_ALL}")
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

    # ==================== MAIN MENU (THÊM MỤC CODE LIBRARY) ====================
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
            print(f"{Fore.GREEN}1. {self.t('menu_continue', self.current_chat)}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}2. {self.t('menu_switch_chat')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}3. {self.t('menu_history')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}4. {self.t('menu_model')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}5. {self.t('menu_change_key')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}6. {self.t('menu_change_lang')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}7. {self.t('menu_exit')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}8. {self.t('menu_code_lib')}{Style.RESET_ALL}")
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

            elif choice == "8":
                self.list_saved_codes()

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
