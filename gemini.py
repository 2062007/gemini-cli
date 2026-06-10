#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Unlimited Language Code Generation & Execution (Improved)
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
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager

import requests
from colorama import init, Fore, Style, Back

init(autoreset=True)

# ==================== CONSTANTS ====================
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "gemini_data"
CONFIG_FILE = DATA_DIR / "config.json"
CHATS_DIR = DATA_DIR / "chats"
HISTORY_FILE = DATA_DIR / "history.json"
MODEL_CACHE_FILE = DATA_DIR / "model_cache.json"
CODE_DIR = DATA_DIR / "generated_code"

DEFAULT_MODEL_ID = "gemini-2.0-flash"
CACHE_DURATION = 86400  # 24 hours
API_TIMEOUT = 30
CODE_TIMEOUT = 30
MAX_HISTORY_ITEMS = 50
MAX_MESSAGES_PER_CHAT = 100  # Prevent context overflow

# ==================== RUNTIME CONFIGURATION ====================
LANGUAGE_RUNTIMES = {
    "python": {"ext": "py", "run": ["python3", "{file}"]},
    "python3": {"ext": "py", "run": ["python3", "{file}"]},
    "javascript": {"ext": "js", "run": ["node", "{file}"]},
    "js": {"ext": "js", "run": ["node", "{file}"]},
    "node": {"ext": "js", "run": ["node", "{file}"]},
    "typescript": {"ext": "ts", "compile": ["tsc", "{file}"], "run": ["node", "{jsfile}"]},
    "ts": {"ext": "ts", "compile": ["tsc", "{file}"], "run": ["node", "{jsfile}"]},
    "ruby": {"ext": "rb", "run": ["ruby", "{file}"]},
    "php": {"ext": "php", "run": ["php", "{file}"]},
    "perl": {"ext": "pl", "run": ["perl", "{file}"]},
    "r": {"ext": "r", "run": ["Rscript", "{file}"]},
    "go": {"ext": "go", "compile": ["go", "build", "-o", "{exe}", "{file}"], "run": ["{exe}"]},
    "rust": {"ext": "rs", "compile": ["rustc", "{file}", "-o", "{exe}"], "run": ["{exe}"]},
    "c": {"ext": "c", "compile": ["gcc", "{file}", "-o", "{exe}"], "run": ["{exe}"]},
    "cpp": {"ext": "cpp", "compile": ["g++", "{file}", "-o", "{exe}"], "run": ["{exe}"]},
    "c++": {"ext": "cpp", "compile": ["g++", "{file}", "-o", "{exe}"], "run": ["{exe}"]},
    "java": {"ext": "java", "compile": ["javac", "{file}"], "run": ["java", "-cp", "{dir}", "{classname}"]},
    "kotlin": {"ext": "kt", "compile": ["kotlinc", "{file}", "-include-runtime", "-d", "{jar}"], "run": ["java", "-jar", "{jar}"]},
    "swift": {"ext": "swift", "run": ["swift", "{file}"]},
    "lua": {"ext": "lua", "run": ["lua", "{file}"]},
    "scala": {"ext": "scala", "compile": ["scalac", "{file}"], "run": ["scala", "-cp", "{dir}", "{classname}"]},
    "bash": {"ext": "sh", "run": ["bash", "{file}"]},
    "sh": {"ext": "sh", "run": ["bash", "{file}"]},
    "shell": {"ext": "sh", "run": ["bash", "{file}"]},
    "powershell": {"ext": "ps1", "run": ["pwsh", "-File", "{file}"]},
    "ps1": {"ext": "ps1", "run": ["pwsh", "-File", "{file}"]},
    "sqlite": {"ext": "sql", "run": ["sqlite3", "{file}"]},
}

# ==================== TEXT DICTIONARY ====================
TEXTS = {
    "en": {
        # ... (keep existing translations)
        "data_dir": "📁 Data saved at: {}",
        "no_api_key": "🔑 Gemini API key not found!",
        # ... (keep all existing keys)
        "code_block_detected": "✅ Detected code block for language: {}",
        "code_no_language": "⚠️  No language specified in code block, using: {}",
        "streaming_response": "🤖 Gemini: ",
        "token_warning": "⚠️  Chat history is getting long ({} messages). Consider starting a new chat.",
    },
    "vi": {
        # ... (keep existing translations)
        "code_block_detected": "✅ Phát hiện code block cho ngôn ngữ: {}",
        "code_no_language": "⚠️  Không có ngôn ngữ trong code block, sử dụng: {}",
        "streaming_response": "🤖 Gemini: ",
        "token_warning": "⚠️  Lịch sử chat đang dài ({} tin nhắn). Hãy cân nhắc tạo đoạn chat mới.",
    }
}

# ==================== UTILITY FUNCTIONS ====================
def print_box(text: str, color=Fore.CYAN, width=60):
    print(f"{color}╔{'═'*width}╗")
    for line in text.splitlines():
        print(f"║ {line}{' '*(width-1-len(line))}║")
    print(f"╚{'═'*width}╝{Style.RESET_ALL}")

def loading_animation(stop_event, prefix="Thinking"):
    for c in itertools.cycle('|/-\\'):
        if stop_event.is_set():
            break
        sys.stdout.write(f"\r{Fore.YELLOW}{prefix} {c}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * (len(prefix) + 2) + "\r")

@dataclass
class CodeBlock:
    language: str
    code: str
    start_pos: int
    end_pos: int

# ==================== MAIN CHATBOT CLASS ====================
class GeminiChatbot:
    def __init__(self):
        self.lang = "vi"
        self.config = {}
        self.api_key = ""
        self.current_model = DEFAULT_MODEL_ID
        self.current_chat = "default"
        self._loading_thread = None
        self._stop_loading = None

        # Create directories
        DATA_DIR.mkdir(exist_ok=True)
        CHATS_DIR.mkdir(exist_ok=True)
        CODE_DIR.mkdir(exist_ok=True)
        
        if not HISTORY_FILE.exists():
            HISTORY_FILE.write_text(json.dumps([], indent=2), encoding="utf-8")

    def t(self, key: str, *args) -> str:
        text = TEXTS.get(self.lang, TEXTS["vi"]).get(key, key)
        if args:
            return text.format(*args)
        return text

    # ==================== CONFIGURATION MANAGEMENT ====================
    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                self.config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.config = {}
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

    # ==================== MODEL MANAGEMENT ====================
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
                    
        except requests.exceptions.RequestException as e:
            stop_event.set()
            t.join()
            print(f"{Fore.YELLOW}{self.t('fetch_error', str(e))}{Style.RESET_ALL}")
        except Exception as e:
            stop_event.set()
            t.join()
            print(f"{Fore.YELLOW}{self.t('fetch_error', str(e))}{Style.RESET_ALL}")
        
        # Try cache
        if MODEL_CACHE_FILE.exists():
            try:
                cache_data = json.loads(MODEL_CACHE_FILE.read_text(encoding="utf-8"))
                if time.time() - cache_data.get("timestamp", 0) < CACHE_DURATION:
                    print(f"{Fore.BLUE}{self.t('using_cache')}{Style.RESET_ALL}")
                    return cache_data.get("models")
            except (json.JSONDecodeError, KeyError):
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

    # ==================== CHAT MANAGEMENT ====================
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename to prevent path traversal"""
        safe_name = "".join(c for c in name if c.isalnum() or c in "._-")
        if not safe_name:
            safe_name = "default"
        return safe_name[:100]  # Limit length

    def _chat_file_path(self, chat_name: str) -> Path:
        safe_name = self._sanitize_filename(chat_name)
        return CHATS_DIR / f"{safe_name}.json"

    def load_messages(self, chat_name: str) -> List[Dict]:
        path = self._chat_file_path(chat_name)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                messages = data.get("messages", [])
                # Limit messages to prevent context overflow
                if len(messages) > MAX_MESSAGES_PER_CHAT * 2:
                    messages = messages[-MAX_MESSAGES_PER_CHAT * 2:]
                    self.save_messages(chat_name, messages)
                return messages
            except (json.JSONDecodeError, KeyError):
                return []
        return []

    def save_messages(self, chat_name: str, messages: List[Dict]):
        path = self._chat_file_path(chat_name)
        data = {
            "name": chat_name,
            "messages": messages,
            "updated_at": datetime.now().isoformat(),
            "message_count": len(messages) // 2
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_chats(self) -> List[Dict]:
        chats = []
        for f in sorted(CHATS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                msg_count = data.get("message_count", len(data.get("messages", [])) // 2)
                updated = data.get("updated_at", "Unknown")[:16]
                chats.append({
                    "name": data.get("name", f.stem),
                    "msg_count": msg_count,
                    "updated": updated
                })
            except (json.JSONDecodeError, KeyError, OSError):
                continue
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
        except (json.JSONDecodeError, FileNotFoundError):
            history = []
        
        # Remove existing entry
        history = [h for h in history if h.get("name") != chat_name]
        
        # Add new entry at beginning
        history.insert(0, {
            "name": chat_name,
            "last_used": datetime.now().isoformat(),
            "message_count": len(self.load_messages(chat_name)) // 2
        })
        
        # Limit history size
        HISTORY_FILE.write_text(json.dumps(history[:MAX_HISTORY_ITEMS], indent=2, ensure_ascii=False), encoding="utf-8")

    def show_history(self):
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
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

    # ==================== GEMINI API ====================
    def call_gemini(self, messages: List[Dict]) -> str:
        """Synchronous API call with loading animation"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.current_model}:generateContent?key={self.api_key}"
        
        contents = []
        for msg in messages[-MAX_MESSAGES_PER_CHAT * 2:]:  # Only send recent messages
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        payload = {"contents": contents}
        
        # Show warning if chat is getting long
        if len(messages) > MAX_MESSAGES_PER_CHAT:
            print(f"{Fore.YELLOW}{self.t('token_warning', len(messages)//2)}{Style.RESET_ALL}")
        
        stop_event = threading.Event()
        t = threading.Thread(target=loading_animation, args=(stop_event, self.t("thinking")))
        t.start()
        
        try:
            response = requests.post(url, json=payload, timeout=API_TIMEOUT)
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
            return f"{Fore.RED}❌ Timeout: Gemini not responding ({API_TIMEOUT}s){Style.RESET_ALL}"
        except requests.exceptions.ConnectionError:
            stop_event.set()
            t.join()
            return f"{Fore.RED}❌ Connection error: Check internet{Style.RESET_ALL}"
        except Exception as e:
            stop_event.set()
            t.join()
            return f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}"

    # ==================== CODE EXTRACTION (IMPROVED) ====================
    def extract_code_blocks(self, text: str) -> List[CodeBlock]:
        """Extract all code blocks with language detection"""
        blocks = []
        
        # Pattern for markdown code blocks with optional language
        pattern = r"```(\w*)\n(.*?)```"
        matches = re.finditer(pattern, text, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            language = match.group(1).strip().lower() or None
            code = match.group(2).strip()
            
            if code:
                blocks.append(CodeBlock(
                    language=language,
                    code=code,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        # If no code blocks found, try to detect if the whole response is code
        if not blocks and text.strip():
            # Check if it looks like code (has indentation, brackets, etc.)
            if re.search(r'^(def |class |import |from |#!|function |const |let |var |public |private )', text, re.MULTILINE):
                blocks.append(CodeBlock(
                    language=None,
                    code=text.strip(),
                    start_pos=0,
                    end_pos=len(text)
                ))
        
        return blocks

    def detect_language_from_code(self, code: str) -> Optional[str]:
        """Detect programming language from code content"""
        patterns = {
            'python': [r'^import ', r'^from .+ import ', r'^def ', r'^class ', r'print\(', r'if __name__'],
            'javascript': [r'^function ', r'^const ', r'^let ', r'^var ', r'console\.log', r'=>'],
            'java': [r'public class ', r'public static void main', r'System\.out\.println'],
            'cpp': [r'#include <', r'int main\(', r'std::', r'using namespace'],
            'c': [r'#include <', r'int main\(', r'printf\('],
            'ruby': [r'^def ', r'^class ', r'puts ', r'#!.*ruby'],
            'go': [r'^package ', r'^func ', r'import \(', r'fmt\.Print'],
            'rust': [r'^fn ', r'^use ', r'println!', r'let mut '],
        }
        
        scores = {}
        for lang, pats in patterns.items():
            score = sum(1 for pat in pats if re.search(pat, code, re.MULTILINE))
            if score > 0:
                scores[lang] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None

    def get_language_runtime(self, lang: str) -> Optional[dict]:
        """Get runtime config for language with fallback"""
        lang = lang.lower().strip()
        
        # Direct match
        if lang in LANGUAGE_RUNTIMES:
            return LANGUAGE_RUNTIMES[lang]
        
        # Aliases
        aliases = {
            "c++": "cpp", "cplusplus": "cpp",
            "py": "python", "python2": "python", "python3": "python",
            "js": "javascript", "nodejs": "javascript",
            "ts": "typescript",
            "sh": "bash", "shellscript": "bash",
            "ps": "powershell", "pwsh": "powershell",
        }
        
        if lang in aliases:
            return LANGUAGE_RUNTIMES.get(aliases[lang])
        
        # Try to detect from code if no language specified
        return None

    # ==================== CODE EXECUTION (IMPROVED) ====================
    def run_code(self, language: str, code: str, timeout=CODE_TIMEOUT) -> str:
        """Execute code with improved error handling and compilation"""
        rt = self.get_language_runtime(language)
        
        if not rt:
            # Try to auto-detect language from code
            detected = self.detect_language_from_code(code)
            if detected:
                print(f"{Fore.YELLOW}Auto-detected language: {detected}{Style.RESET_ALL}")
                return self.run_code(detected, code, timeout)
            return self.t("code_unsupported_runtime", language)
        
        ext = rt.get("ext", language)
        compile_cmd = rt.get("compile")
        run_cmd = rt.get("run")
        
        if not run_cmd:
            return "❌ No run command defined."
        
        # Check if runtime executable exists
        runtime_exe = run_cmd[0] if run_cmd else None
        if runtime_exe and not shutil.which(runtime_exe):
            return self.t("code_runtime_missing", runtime_exe, language)
        
        with tempfile.TemporaryDirectory(prefix="gemini_code_") as tmp_dir:
            file_path = os.path.join(tmp_dir, f"code.{ext}")
            
            # Write code to file
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)
            except IOError as e:
                return f"❌ Failed to write code: {str(e)}"
            
            try:
                exe_path = None
                
                # Compilation step
                if compile_cmd:
                    if ext in ("java", "scala"):
                        exe_path = file_path
                    else:
                        exe_path = os.path.join(tmp_dir, "program")
                        if os.name == "nt":
                            exe_path += ".exe"
                    
                    # Prepare compile command
                    compile_cmd_filled = []
                    for arg in compile_cmd:
                        arg = arg.replace("{file}", file_path)
                        arg = arg.replace("{exe}", exe_path)
                        compile_cmd_filled.append(arg)
                    
                    # Run compilation
                    comp = subprocess.run(
                        compile_cmd_filled,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=tmp_dir
                    )
                    
                    if comp.returncode != 0:
                        error_output = comp.stderr if comp.stderr else "Unknown compilation error"
                        return f"❌ Compilation failed:\n{error_output}"
                
                # Prepare run command
                run_cmd_filled = []
                for arg in run_cmd:
                    arg = arg.replace("{file}", file_path)
                    if exe_path:
                        arg = arg.replace("{exe}", exe_path)
                    if "{jsfile}" in arg:
                        jsfile = os.path.splitext(file_path)[0] + ".js"
                        arg = arg.replace("{jsfile}", jsfile)
                    if "{classname}" in arg:
                        classname = Path(file_path).stem
                        arg = arg.replace("{classname}", classname)
                    if "{jar}" in arg:
                        jar = os.path.splitext(file_path)[0] + ".jar"
                        arg = arg.replace("{jar}", jar)
                    if "{dir}" in arg:
                        arg = arg.replace("{dir}", tmp_dir)
                    run_cmd_filled.append(arg)
                
                # Execute code
                proc = subprocess.run(
                    run_cmd_filled,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmp_dir
                )
                
                # Format output
                output_parts = []
                if proc.stdout:
                    output_parts.append(proc.stdout.strip())
                if proc.stderr:
                    output_parts.append(f"{Fore.RED}STDERR:\n{proc.stderr.strip()}{Style.RESET_ALL}")
                if proc.returncode != 0 and not proc.stderr:
                    output_parts.append(self.t("code_exec_failed", proc.returncode))
                
                result = "\n".join(output_parts) if output_parts else "(no output)"
                return result
                
            except subprocess.TimeoutExpired:
                return self.t("code_timed_out", timeout)
            except subprocess.SubprocessError as e:
                return f"❌ Process error: {str(e)}"
            except Exception as e:
                return f"❌ Unexpected error: {str(e)}"

    # ==================== CODE COMMAND HANDLER ====================
    def handle_code_command(self, args: str):
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            print(f"{Fore.YELLOW}{self.t('code_help')}{Style.RESET_ALL}")
            return
        
        language = parts[0].lower()
        description = parts[1]
        
        # Enhanced prompt for better code generation
        prompt = (
            f"Write a {language} program that {description}. "
            "Provide ONLY the code inside a markdown code block with the language specified. "
            "Include necessary imports and a main function/entry point. "
            "Do not include any explanatory text outside the code block."
        )
        
        print(f"{Fore.CYAN}{self.t('code_generating', language, description)}{Style.RESET_ALL}")
        
        messages = [{"role": "user", "content": prompt}]
        response = self.call_gemini(messages)
        
        # Extract code blocks
        code_blocks = self.extract_code_blocks(response)
        
        if not code_blocks:
            print(f"{Fore.RED}{self.t('code_not_found')}{Style.RESET_ALL}")
            return
        
        # Use the first code block
        block = code_blocks[0]
        detected_lang = block.language or self.detect_language_from_code(block.code)
        
        if detected_lang and not block.language:
            print(f"{Fore.YELLOW}{self.t('code_no_language', detected_lang)}{Style.RESET_ALL}")
            language = detected_lang
        elif block.language:
            print(f"{Fore.GREEN}{self.t('code_block_detected', block.language)}{Style.RESET_ALL}")
            language = block.language
        
        # Display code
        print(f"{Fore.GREEN}{self.t('code_generated')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*40}")
        print(block.code)
        print(f"{Fore.CYAN}{'─'*40}")
        
        # Ask to run
        run_confirm = input(f"{Fore.YELLOW}{self.t('code_run_prompt')}{Style.RESET_ALL}").strip().lower()
        if run_confirm == 'y':
            print(f"{Fore.BLUE}{self.t('code_running')}{Style.RESET_ALL}")
            output = self.run_code(language, block.code)
            print(f"{Fore.GREEN}{self.t('code_output')}{Style.RESET_ALL}")
            print(output)
            print()
        
        # Ask to save
        save_confirm = input(self.t("code_save_prompt")).strip().lower()
        if save_confirm == 'y':
            name = input(self.t("code_name_prompt")).strip()
            if not name:
                name = re.sub(r'[^\w\s]', '', description)[:30].replace(' ', '_')
            self.save_code(name, language, block.code)
    
    def save_code(self, name: str, language: str, code: str):
        """Save generated code to file"""
        rt = self.get_language_runtime(language)
        ext = rt["ext"] if rt and "ext" in rt else language
        
        safe_name = self._sanitize_filename(name)
        if not safe_name:
            safe_name = "untitled"
        
        file_name = f"{safe_name}.{ext}"
        file_path = CODE_DIR / file_name
        
        if file_path.exists():
            confirm = input(self.t("code_name_exists", safe_name)).strip().lower()
            if confirm != 'y':
                return
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            print(self.t("code_saved", safe_name))
        except IOError as e:
            print(f"{Fore.RED}Failed to save code: {str(e)}{Style.RESET_ALL}")

    # ==================== CHAT LOOP ====================
    def chat_loop(self):
        messages = self.load_messages(self.current_chat)
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}{self.t('chatting', self.current_chat)}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{self.t('model_label', self.current_model)}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{self.t('commands_label')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}\n")
        
        if messages:
            print(f"{Fore.YELLOW}{self.t('history_label', len(messages)//2)}{Style.RESET_ALL}")
            for msg in messages[-10:]:  # Show last 10 messages only
                role_icon = f"{Fore.GREEN}{self.t('user_prefix')}" if msg["role"] == "user" else f"{Fore.MAGENTA}{self.t('gemini_prefix')}"
                content = msg['content'].replace('\n', '\n           ')[:200]  # Truncate long messages
                print(f"{role_icon}: {content}")
            print()
        
        while True:
            try:
                user_input = input(f"{Fore.GREEN}{self.t('user_prefix')}{Style.RESET_ALL}: ").strip()
                if not user_input:
                    continue
                
                cmd = user_input.lower()
                
                if cmd.startswith("/code"):
                    args = user_input[5:].strip()
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
                    
                    # Limit messages to prevent overflow
                    if len(messages) > MAX_MESSAGES_PER_CHAT * 2:
                        messages = messages[-MAX_MESSAGES_PER_CHAT * 2:]
                        print(f"{Fore.YELLOW}Trimmed chat history to last {MAX_MESSAGES_PER_CHAT} messages{Style.RESET_ALL}")
                    
                    self.save_messages(self.current_chat, messages)
                    self.update_history(self.current_chat)
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}{self.t('goodbye')}{Style.RESET_ALL}")
                self.update_history(self.current_chat)
                return "quit"
            except Exception as e:
                print(f"{Fore.RED}Error in chat loop: {str(e)}{Style.RESET_ALL}")
                continue

    # ==================== MAIN MENU ====================
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

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    try:
        bot = GeminiChatbot()
        bot.main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}{TEXTS['vi']['goodbye']}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
