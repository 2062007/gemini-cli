#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Hỗ trợ chọn model + xử lý quota exceeded
"""

import os
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    from colorama import init, Fore, Style, Back
    from tabulate import tabulate
    init(autoreset=True)
except ImportError as e:
    print(f"Thiếu thư viện: {e}")
    print("Cài đặt: pip install requests colorama tabulate")
    sys.exit(1)

# ==================== CẤU HÌNH ====================
SCRIPT_DIR = Path(__file__).parent if "__file__" in globals() else Path.cwd()
CONFIG_DIR = SCRIPT_DIR / "gemini_data"
CONFIG_FILE = CONFIG_DIR / "config.json"
CHATS_DIR = CONFIG_DIR / "chats"
HISTORY_FILE = CONFIG_DIR / "history.json"

# Danh sách model hỗ trợ
MODELS = {
    "1": {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "desc": "Nhanh, mạnh, đa năng"},
    "2": {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "desc": "Nhẹ, nhanh, tiết kiệm"},
    "3": {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "desc": "Xử lý ngữ cảnh dài (2M token)"},
}

# ==================== KHỞI TẠO ====================
def init_dirs():
    CONFIG_DIR.mkdir(exist_ok=True)
    CHATS_DIR.mkdir(exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps([], indent=2))
    if not CONFIG_FILE.exists():
        save_config({"api_key": "", "current_chat": "default", "model": "gemini-2.0-flash"})
    print(f"{Fore.BLUE}📁 Dữ liệu lưu tại: {CONFIG_DIR}{Style.RESET_ALL}")

def load_config():
    return json.loads(CONFIG_FILE.read_text())

def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

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
            print(f"{Fore.RED}❌ API key không được để trống!{Style.RET_ALL}")
            return get_api_key()
    return config["api_key"]

def choose_model():
    """Menu chọn model, lưu vào config"""
    config = load_config()
    current_model_id = config.get("model", "gemini-2.0-flash")
    
    # Tìm tên hiển thị của model hiện tại
    current_name = current_model_id
    for k, v in MODELS.items():
        if v["id"] == current_model_id:
            current_name = v["name"]
            break
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}🤖 CHỌN MODEL GEMINI")
    print(f"{Fore.CYAN}{'='*60}")
    
    # Hiển thị bảng model
    table = []
    for key, model in MODELS.items():
        marker = "✅ " if model["id"] == current_model_id else "   "
        table.append([f"{marker}{key}", model["name"], model["desc"]])
    print(tabulate(table, headers=["Chọn", "Model", "Mô tả"], tablefmt="rounded_grid"))
    
    print(f"\n{Fore.YELLOW}Model hiện tại: {Fore.GREEN}{current_name}{Style.RESET_ALL}")
    choice = input(f"{Fore.GREEN}Nhập số để đổi model (Enter để giữ nguyên): {Style.RESET_ALL}").strip()
    
    if choice in MODELS:
        new_model_id = MODELS[choice]["id"]
        config["model"] = new_model_id
        save_config(config)
        print(f"{Fore.GREEN}✅ Đã đổi sang {MODELS[choice]['name']}{Style.RESET_ALL}")
        return new_model_id
    else:
        print(f"{Fore.BLUE}ℹ️ Giữ nguyên model {current_name}{Style.RESET_ALL}")
        return current_model_id

# ==================== QUẢN LÝ CHAT ====================
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
        confirm = input(f"{Fore.RED}⚠️ Xoá vĩnh viễn '{chat_name}'? (y/N): {Style.RESET_ALL}")
        if confirm.lower() == 'y':
            chat_file.unlink()
            print(f"{Fore.GREEN}✅ Đã xoá{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}Đã huỷ{Style.RESET_ALL}")
            return False
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
        print(f"{Fore.YELLOW}📭 Chưa có lịch sử{Style.RESET_ALL}")
        return
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}📜 LỊCH SỬ CHAT")
    print(f"{Fore.CYAN}{'='*60}")
    for i, h in enumerate(history, 1):
        print(f"{Fore.GREEN}{i:2d}. {Fore.WHITE}{h['name']}")
        print(f"      {Fore.BLUE}📝 {h.get('message_count',0)} tin nhắn | 🕐 {h.get('last_used','Unknown')[:16]}")
    print(f"{Fore.CYAN}{'='*60}\n")

# ==================== GỌI GEMINI API (CÓ XỬ LÝ QUOTA)====================
def call_gemini(api_key, messages, model_id):
    """Gọi Gemini, nếu quota exceeded thì gợi ý đổi model"""
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
            return {"success": True, "text": result["candidates"][0]["content"]["parts"][0]["text"]}
        
        # Xử lý lỗi 429 (Quota exceeded)
        if response.status_code == 429:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "")
            
            # Trích xuất thời gian chờ nếu có
            wait_seconds = None
            if "retry in " in error_msg:
                parts = error_msg.split("retry in ")
                if len(parts) > 1:
                    wait_part = parts[1].split("s")[0]
                    try:
                        wait_seconds = float(wait_part)
                    except:
                        pass
            
            return {
                "success": False,
                "error": "quota",
                "message": error_msg,
                "wait_seconds": wait_seconds,
                "model": model_id
            }
        
        # Các lỗi khác
        error_msg = response.json().get("error", {}).get("message", "Lỗi không xác định")
        return {"success": False, "error": "other", "message": error_msg}
        
    except requests.exceptions.Timeout:
        return {"success": False, "error": "other", "message": "Timeout 30s"}
    except Exception as e:
        return {"success": False, "error": "other", "message": str(e)}

# ==================== CHAT LOOP ====================
def chat_loop(chat_name, api_key, model_id):
    messages = load_chat(chat_name)
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}💬 Đang chat: {Fore.WHITE}{chat_name}")
    print(f"{Fore.BLUE}📡 Model: {Fore.YELLOW}{model_id}")
    print(f"{Fore.BLUE}📝 Lệnh: /menu | /new | /delete | /history | /model | /quit")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    if messages:
        print(f"{Fore.YELLOW}--- {len(messages)//2} tin nhắn gần nhất ---{Style.RESET_ALL}")
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
                new_model = choose_model()
                if new_model != model_id:
                    model_id = new_model
                    # Lưu model mới vào config
                    config = load_config()
                    config["model"] = model_id
                    save_config(config)
                    print(f"{Fore.GREEN}✅ Đã đổi model, tiếp tục chat...{Style.RESET_ALL}")
                continue
            elif cmd == "/quit":
                update_history(chat_name)
                return "quit"
            
            # Chat bình thường
            messages.append({"role": "user", "content": user_input})
            print(f"{Fore.MAGENTA}🤖 Gemini{Style.RESET_ALL}: ", end="", flush=True)
            
            result = call_gemini(api_key, messages, model_id)
            
            if result["success"]:
                response_text = result["text"]
                print(response_text)
                messages.append({"role": "assistant", "content": response_text})
                save_chat(chat_name, messages)
                update_history(chat_name)
            else:
                if result["error"] == "quota":
                    print(f"\n{Fore.RED}❌ HẾT QUOTA!{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{result['message']}{Style.RESET_ALL}")
                    
                    if result.get("wait_seconds"):
                        print(f"{Fore.CYAN}⏳ Có thể thử lại sau {int(result['wait_seconds'])} giây.{Style.RESET_ALL}")
                    
                    # Gợi ý đổi model
                    print(f"\n{Fore.MAGENTA}💡 Gợi ý: Thử đổi sang model khác bằng lệnh {Fore.GREEN}/model{Fore.MAGENTA} (ví dụ: gemini-1.5-flash có thể còn quota).{Style.RESET_ALL}")
                    
                    # Hỏi có muốn đổi model ngay không?
                    change = input(f"\n{Fore.YELLOW}Đổi model khác ngay? (y/N): {Style.RESET_ALL}").strip().lower()
                    if change == 'y':
                        new_model = choose_model()
                        if new_model != model_id:
                            model_id = new_model
                            config = load_config()
                            config["model"] = model_id
                            save_config(config)
                            print(f"{Fore.GREEN}✅ Đã đổi sang {model_id}, hãy gửi lại tin nhắn.{Style.RESET_ALL}")
                            # Xoá tin nhắn user vừa thêm (chưa gửi thành công)
                            messages.pop()
                            continue
                    else:
                        # Không đổi, bỏ qua tin nhắn này
                        messages.pop()
                        print(f"{Fore.YELLOW}Đã bỏ qua tin nhắn.{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.RED}❌ Lỗi: {result['message']}{Style.RESET_ALL}")
                    messages.pop()
        
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
            update_history(chat_name)
            return "quit"

# ==================== MAIN ====================
def main_menu():
    init_dirs()
    api_key = get_api_key()
    if not api_key:
        return
    
    # Chọn model lần đầu
    config = load_config()
    current_model = config.get("model", "gemini-2.0-flash")
    print(f"\n{Fore.CYAN}🔧 Cấu hình ban đầu...{Style.RESET_ALL}")
    choose_model()  # Cho người dùng chọn/có thể bỏ qua
    config = load_config()
    current_model = config.get("model", "gemini-2.0-flash")
    
    current_chat = config.get("current_chat", "default")
    
    while True:
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}🤖 GEMINI CLI CHATBOT")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}1. {Fore.WHITE}Tiếp tục chat: {Fore.YELLOW}{current_chat}")
        print(f"{Fore.GREEN}2. {Fore.WHITE}Chọn / Tạo đoạn chat khác")
        print(f"{Fore.GREEN}3. {Fore.WHITE}Xem lịch sử")
        print(f"{Fore.GREEN}4. {Fore.WHITE}Đổi model")
        print(f"{Fore.GREEN}5. {Fore.WHITE}Đổi API key")
        print(f"{Fore.GREEN}6. {Fore.WHITE}Thoát")
        print(f"{Fore.CYAN}{'='*60}")
        
        choice = input(f"{Fore.YELLOW}🔹 Chọn (1-6): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            result = chat_loop(current_chat, api_key, current_model)
            if result == "new":
                new_name = input(f"{Fore.GREEN}Tên mới (Enter = ngày giờ): {Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
            elif result == "deleted":
                chats = list_chats()
                if chats:
                    current_chat = chats[0]["name"]
                else:
                    current_chat = datetime.now().strftime("%Y%m%d_%H%M%S")
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
            elif result == "quit":
                break
        elif choice == "2":
            chats = list_chats()
            if not chats:
                print(f"{Fore.YELLOW}📭 Chưa có, tạo mới.{Style.RESET_ALL}")
                new_name = input(f"{Fore.GREEN}Tên mới: {Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
                continue
            print(f"\n{Fore.CYAN}📋 Danh sách chat:{Style.RESET_ALL}")
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
            current_model = choose_model()
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
