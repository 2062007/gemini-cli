#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Phiên bản ổn định, tự động lấy danh sách model từ Google API.
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
    print(f"Thiếu thư viện: {e}")
    print("Vui lòng cài đặt: pip install requests colorama")
    sys.exit(1)

# ==================== CẤU HÌNH ====================
SCRIPT_DIR = Path(__file__).parent if "__file__" in globals() else Path.cwd()
CONFIG_DIR = SCRIPT_DIR / "gemini_data"
CONFIG_FILE = CONFIG_DIR / "config.json"
CHATS_DIR = CONFIG_DIR / "chats"
HISTORY_FILE = CONFIG_DIR / "history.json"
MODEL_CACHE_FILE = CONFIG_DIR / "model_cache.json"

DEFAULT_MODEL_ID = "gemini-2.0-flash"

# ==================== KHỞI TẠO THƯ MỤC ====================
def init_dirs():
    CONFIG_DIR.mkdir(exist_ok=True)
    CHATS_DIR.mkdir(exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps([], indent=2))
    if not CONFIG_FILE.exists():
        save_config({"api_key": "", "current_chat": "default", "model": DEFAULT_MODEL_ID})
    print(f"{Fore.BLUE}📁 Dữ liệu lưu tại: {CONFIG_DIR}{Style.RESET_ALL}")

def load_config():
    return json.loads(CONFIG_FILE.read_text())

def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

# ==================== QUẢN LÝ API KEY ====================
def get_api_key():
    config = load_config()
    if not config.get("api_key"):
        print(f"\n{Fore.YELLOW}🔑 Chưa có API key Gemini!")
        print(f"{Fore.CYAN}Bạn có thể lấy API key tại: https://aistudio.google.com/apikey{Style.RESET_ALL}\n")
        api_key = input(f"{Fore.GREEN}Nhập API key của bạn: {Style.RESET_ALL}").strip()
        if api_key:
            config["api_key"] = api_key
            save_config(config)
            print(f"{Fore.GREEN}✅ Đã lưu API key!{Style.RESET_ALL}")
            return api_key
        else:
            print(f"{Fore.RED}❌ API key không được để trống!{Style.RESET_ALL}")
            return get_api_key()
    return config["api_key"]

# ==================== LẤY DANH SÁCH MODEL ĐỘNG ====================
def fetch_models_from_api(api_key: str) -> Optional[Dict[str, Dict]]:
    """Gọi API lấy danh sách model hỗ trợ generateContent."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    print(f"{Fore.CYAN}🔄 Đang tải danh sách model từ Google API...{Style.RESET_ALL}")
    
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
                print(f"{Fore.GREEN}✅ Đã tìm thấy {len(models)} model hỗ trợ chat.{Style.RESET_ALL}")
                return models
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Lỗi fetch: {e}{Style.RESET_ALL}")
    
    if MODEL_CACHE_FILE.exists():
        try:
            cache_data = json.loads(MODEL_CACHE_FILE.read_text())
            if time.time() - cache_data.get("timestamp", 0) < 86400:
                print(f"{Fore.BLUE}📦 Dùng danh sách model từ cache.{Style.RESET_ALL}")
                return cache_data.get("models")
        except:
            pass
    return None

def get_available_models(api_key: str) -> Dict[str, Dict]:
    models = fetch_models_from_api(api_key)
    if models:
        return models
    print(f"{Fore.YELLOW}⚠️ Dùng danh sách dự phòng.{Style.RESET_ALL}")
    return {
        "1": {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "desc": "Model phổ biến, nhanh, ổn định."},
        "2": {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "desc": "Model nhẹ, tiết kiệm, ổn định."},
        "3": {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "desc": "Model mạnh, ngữ cảnh lên tới 2M token."},
    }

def choose_model(api_key: str) -> str:
    """Hiển thị danh sách model rút gọn, khi chọn mới hiện chi tiết và xác nhận."""
    models = get_available_models(api_key)
    config = load_config()
    current_model_id = config.get("model", DEFAULT_MODEL_ID)

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}🤖 DANH SÁCH MODEL GEMINI (Lấy từ Google API)")
    print(f"{Fore.CYAN}{'='*60}")

    # Hiển thị danh sách rút gọn: chỉ số và tên
    for key, m in models.items():
        marker = "✅ " if m["id"] == current_model_id else "   "
        print(f"{Fore.GREEN}{marker}{key}. {Fore.WHITE}{m['name']}")

    print(f"\n{Fore.YELLOW}👉 Nhập số để xem chi tiết và chọn (Enter để giữ nguyên){Style.RESET_ALL}")
    choice = input(f"{Fore.GREEN}Lựa chọn: {Style.RESET_ALL}").strip()

    if choice in models:
        selected = models[choice]
        # Hiển thị chi tiết model được chọn
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}📌 THÔNG TIN MODEL: {selected['name']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}🆔 ID:{Style.RESET_ALL} {selected['id']}")
        # Tách các phần mô tả để hiển thị đẹp
        for part in selected['desc'].split(' | '):
            if part.startswith("Input:"):
                print(f"{Fore.YELLOW}📥 {part}{Style.RESET_ALL}")
            elif part.startswith("Supports:"):
                print(f"{Fore.YELLOW}⚙️ {part}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}📝 {part}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}")

        confirm = input(f"\n{Fore.GREEN}Bạn có muốn chuyển sang model này không? (y/N): {Style.RESET_ALL}").strip().lower()
        if confirm == 'y':
            config["model"] = selected["id"]
            save_config(config)
            print(f"{Fore.GREEN}✅ Đã đổi sang {selected['name']}{Style.RESET_ALL}")
            return selected["id"]
        else:
            print(f"{Fore.YELLOW}❌ Hủy chuyển đổi.{Style.RESET_ALL}")
            return current_model_id
    else:
        if choice != "":
            print(f"{Fore.RED}❌ Lựa chọn không hợp lệ.{Style.RESET_ALL}")
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
        confirm = input(f"{Fore.RED}⚠️  Xoá vĩnh viễn đoạn chat '{chat_name}'? (y/N): {Style.RESET_ALL}")
        if confirm.lower() == 'y':
            chat_file.unlink()
            print(f"{Fore.GREEN}✅ Đã xoá '{chat_name}'{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}Đã huỷ xoá{Style.RESET_ALL}")
            return False
    else:
        print(f"{Fore.RED}Không tìm thấy đoạn chat '{chat_name}'{Style.RESET_ALL}")
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
        print(f"{Fore.YELLOW}📭 Chưa có lịch sử đoạn chat nào{Style.RESET_ALL}")
        return
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}📜 LỊCH SỬ CÁC ĐOẠN CHAT")
    print(f"{Fore.CYAN}{'='*60}")
    for i, h in enumerate(history, 1):
        name = h.get("name", "Unknown")
        msg_count = h.get("message_count", 0)
        last_used = h.get("last_used", "Unknown")[:16]
        print(f"{Fore.GREEN}{i:2d}. {Fore.WHITE}{name}")
        print(f"      {Fore.BLUE}📝 {msg_count} tin nhắn | 🕐 {last_used}")
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
                return f"{Fore.RED}❌ Lỗi: Phản hồi từ API không có nội dung.{Style.RESET_ALL}"
        else:
            error_msg = response.json().get("error", {}).get("message", "Lỗi không xác định")
            return f"{Fore.RED}❌ Lỗi API: {error_msg}{Style.RESET_ALL}"
    except requests.exceptions.Timeout:
        return f"{Fore.RED}❌ Timeout: Gemini không phản hồi (30 giây){Style.RESET_ALL}"
    except requests.exceptions.ConnectionError:
        return f"{Fore.RED}❌ Lỗi kết nối: Kiểm tra internet{Style.RESET_ALL}"
    except Exception as e:
        return f"{Fore.RED}❌ Lỗi: {e}{Style.RESET_ALL}"

# ==================== MAIN CHAT LOOP ====================
def chat_loop(chat_name, api_key, model_id):
    messages = load_chat(chat_name)
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}💬 Đang chat: {Fore.WHITE}{chat_name}")
    print(f"{Fore.BLUE}📡 Model: {Fore.YELLOW}{model_id}")
    print(f"{Fore.BLUE}📝 Lệnh: /menu | /new | /delete | /history | /model | /quit")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    if messages:
        print(f"{Fore.YELLOW}--- {len(messages)//2} tin nhắn trong lịch sử ---{Style.RESET_ALL}")
        for msg in messages[-4:]:
            role_icon = f"{Fore.GREEN}👤" if msg["role"] == "user" else f"{Fore.MAGENTA}🤖"
            preview = msg['content'][:80].replace('\n', ' ')
            print(f"{role_icon} {preview}...")
        print()
    
    while True:
        try:
            user_input = input(f"{Fore.GREEN}👤 Bạn{Style.RESET_ALL}: ").strip()
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
                    print(f"{Fore.GREEN}✅ Đã đổi model, hãy tiếp tục chat.{Style.RESET_ALL}")
                continue
            elif cmd == "/quit":
                update_history(chat_name)
                return "quit"
            else:
                messages.append({"role": "user", "content": user_input})
                print(f"{Fore.MAGENTA}🤖 Gemini{Style.RESET_ALL}: ", end="", flush=True)
                response = call_gemini(api_key, messages, model_id)
                print(response)
                messages.append({"role": "assistant", "content": response})
                save_chat(chat_name, messages)
                update_history(chat_name)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
            update_history(chat_name)
            return "quit"

# ==================== MAIN MENU ====================
def main_menu():
    init_dirs()
    api_key = get_api_key()
    if not api_key:
        return
    
    config = load_config()
    current_model = config.get("model", DEFAULT_MODEL_ID)
    current_chat = config.get("current_chat", "default")
    
    while True:
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}🤖 GEMINI CLI CHATBOT (Danh sách model động)")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}1. {Fore.WHITE}Tiếp tục chat: {Fore.YELLOW}{current_chat}")
        print(f"{Fore.GREEN}2. {Fore.WHITE}Chọn / Tạo đoạn chat khác")
        print(f"{Fore.GREEN}3. {Fore.WHITE}Xem lịch sử các đoạn chat")
        print(f"{Fore.GREEN}4. {Fore.WHITE}Chọn Model Gemini (tự động cập nhật)")
        print(f"{Fore.GREEN}5. {Fore.WHITE}Đổi API key")
        print(f"{Fore.GREEN}6. {Fore.WHITE}Thoát")
        print(f"{Fore.CYAN}{'='*60}")
        
        choice = input(f"{Fore.YELLOW}🔹 Lựa chọn (1-6): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            result = chat_loop(current_chat, api_key, current_model)
            if result == "new":
                new_name = input(f"{Fore.GREEN}Tên mới (Enter = datetime): {Style.RESET_ALL}").strip()
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
                print(f"{Fore.YELLOW}📭 Chưa có chat, tạo mới.{Style.RESET_ALL}")
                new_name = input(f"{Fore.GREEN}Tên mới: {Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
                continue
            print(f"\n{Fore.CYAN}📋 Các đoạn chat:{Style.RESET_ALL}")
            for i, c in enumerate(chats, 1):
                print(f"  {Fore.GREEN}{i}. {Fore.WHITE}{c['name']} ({c['msg_count']} tin nhắn)")
            print(f"  {Fore.GREEN}0. {Fore.WHITE}Tạo mới")
            try:
                sel = int(input(f"{Fore.YELLOW}Chọn số: {Style.RESET_ALL}"))
                if sel == 0:
                    new_name = input(f"{Fore.GREEN}Tên mới: {Style.RESET_ALL}").strip()
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
                print(f"{Fore.GREEN}✅ Đã chọn '{current_chat}'{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Nhập số{Style.RESET_ALL}")
        elif choice == "3":
            show_history()
        elif choice == "4":
            current_model = choose_model(api_key)
        elif choice == "5":
            new_key = input(f"{Fore.GREEN}API key mới: {Style.RESET_ALL}").strip()
            if new_key:
                config = load_config()
                config["api_key"] = new_key
                save_config(config)
                api_key = new_key
                print(f"{Fore.GREEN}✅ Đã cập nhật{Style.RESET_ALL}")
        elif choice == "6":
            print(f"{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
            break

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Lỗi: {e}{Style.RESET_ALL}")
        sys.exit(1)
