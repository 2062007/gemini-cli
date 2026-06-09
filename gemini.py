#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Đơn giản, gọn nhẹ, dùng requests
Tính năng: Lưu API key, nhiều đoạn chat, quản lý lịch sử
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
except ImportError:
    print("Cài đặt thư viện: pip install requests colorama")
    sys.exit(1)

# ==================== CẤU HÌNH ====================
CONFIG_DIR = Path.home() / ".gemini_cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
CHATS_DIR = CONFIG_DIR / "chats"
HISTORY_FILE = CONFIG_DIR / "history.json"

# ==================== KHỞI TẠO THƯ MỤC ====================
def init_dirs():
    """Tạo thư mục và file cấu hình nếu chưa có"""
    CONFIG_DIR.mkdir(exist_ok=True)
    CHATS_DIR.mkdir(exist_ok=True)
    
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps([], indent=2))
    
    if not CONFIG_FILE.exists():
        save_config({"api_key": "", "current_chat": "default"})

def load_config():
    """Đọc file cấu hình"""
    return json.loads(CONFIG_FILE.read_text())

def save_config(config):
    """Ghi file cấu hình"""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

# ==================== QUẢN LÝ API KEY ====================
def get_api_key():
    """Lấy API key, nếu chưa có thì yêu cầu nhập"""
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

# ==================== QUẢN LÝ ĐOẠN CHAT ====================
def get_chat_file(chat_name):
    """Đường dẫn file chat"""
    return CHATS_DIR / f"{chat_name}.json"

def load_chat(chat_name):
    """Đọc nội dung đoạn chat"""
    chat_file = get_chat_file(chat_name)
    if chat_file.exists():
        data = json.loads(chat_file.read_text())
        return data.get("messages", [])
    return []

def save_chat(chat_name, messages):
    """Lưu đoạn chat"""
    chat_file = get_chat_file(chat_name)
    chat_file.write_text(json.dumps({
        "name": chat_name,
        "messages": messages,
        "updated_at": datetime.now().isoformat()
    }, indent=2, ensure_ascii=False))

def list_chats():
    """Liệt kê tất cả các đoạn chat"""
    chats = []
    for f in CHATS_DIR.glob("*.json"):
        data = json.loads(f.read_text())
        msg_count = len(data.get("messages", [])) // 2
        updated = data.get("updated_at", "Unknown")[:16]
        chats.append({
            "name": f.stem,
            "msg_count": msg_count,
            "updated": updated
        })
    return sorted(chats, key=lambda x: x["updated"], reverse=True)

def delete_chat(chat_name):
    """Xoá đoạn chat (có kiểm tra)"""
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
    """Cập nhật lịch sử các đoạn chat đã dùng"""
    history = json.loads(HISTORY_FILE.read_text())
    
    # Xoá tên cũ nếu có
    history = [h for h in history if h["name"] != chat_name]
    
    # Thêm vào đầu
    history.insert(0, {
        "name": chat_name,
        "last_used": datetime.now().isoformat(),
        "message_count": len(load_chat(chat_name)) // 2
    })
    
    # Giữ lại 50 chat gần nhất
    HISTORY_FILE.write_text(json.dumps(history[:50], indent=2))

def show_history():
    """Hiển thị lịch sử các đoạn chat"""
    history = json.loads(HISTORY_FILE.read_text())
    
    if not history:
        print(f"{Fore.YELLOW}📭 Chưa có lịch sử đoạn chat nào{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}📜 LỊCH SỬ CÁC ĐOẠN CHAT")
    print(f"{Fore.CYAN}{'='*60}")
    
    for i, h in enumerate(history, 1):
        name = h["name"]
        msg_count = h.get("message_count", 0)
        last_used = h["last_used"][:16] if h["last_used"] else "Unknown"
        print(f"{Fore.GREEN}{i:2d}. {Fore.WHITE}{name}")
        print(f"      {Fore.BLUE}📝 {msg_count} tin nhắn | 🕐 {last_used}")
    
    print(f"{Fore.CYAN}{'='*60}\n")

# ==================== GỌI GEMINI API ====================
def call_gemini(api_key, messages):
    """Gọi Gemini API và trả về phản hồi"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Chuyển đổi format messages sang Gemini format
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    
    payload = {"contents": contents}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            error_msg = response.json().get("error", {}).get("message", "Lỗi không xác định")
            return f"{Fore.RED}❌ Lỗi API: {error_msg}{Style.RESET_ALL}"
    except requests.exceptions.Timeout:
        return f"{Fore.RED}❌ Timeout: Gemini không phản hồi{Style.RESET_ALL}"
    except Exception as e:
        return f"{Fore.RED}❌ Lỗi: {e}{Style.RESET_ALL}"

# ==================== MAIN CHAT LOOP ====================
def chat_loop(chat_name, api_key):
    """Vòng lặp chat cho một đoạn chat"""
    messages = load_chat(chat_name)
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}💬 Đang chat: {Fore.WHITE}{chat_name}")
    print(f"{Fore.BLUE}📝 Lệnh: /menu | /new | /delete | /history | /quit")
    print(f"{Fore.CYAN}{'='*60}\n")
    
    # Hiển thị lịch sử chat gần đây
    if messages:
        print(f"{Fore.YELLOW}--- Lịch sử chat gần đây ---{Style.RESET_ALL}")
        for msg in messages[-6:]:
            role_icon = f"{Fore.GREEN}👤 Bạn" if msg["role"] == "user" else f"{Fore.MAGENTA}🤖 Gemini"
            print(f"{role_icon}: {msg['content'][:100]}...")
        print()
    
    while True:
        try:
            user_input = input(f"{Fore.GREEN}👤 Bạn{Style.RESET_ALL}: ").strip()
            
            if not user_input:
                continue
            
            # Xử lý lệnh
            cmd = user_input.lower()
            
            if cmd == "/menu" or cmd == "/back":
                print(f"{Fore.YELLOW}🔙 Quay lại menu chính...{Style.RESET_ALL}")
                update_history(chat_name)
                return "menu"
            
            elif cmd == "/new":
                update_history(chat_name)
                print(f"{Fore.YELLOW}✨ Tạo đoạn chat mới...{Style.RESET_ALL}")
                return "new"
            
            elif cmd == "/delete":
                if delete_chat(chat_name):
                    return "deleted"
                continue
            
            elif cmd == "/history":
                show_history()
                continue
            
            elif cmd == "/quit":
                print(f"{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
                update_history(chat_name)
                return "quit"
            
            # Chat bình thường
            else:
                # Thêm tin nhắn user
                messages.append({"role": "user", "content": user_input})
                
                # Gọi Gemini
                print(f"{Fore.MAGENTA}🤖 Gemini{Style.RESET_ALL}: ", end="", flush=True)
                response = call_gemini(api_key, messages)
                print(response)
                
                # Thêm phản hồi
                messages.append({"role": "assistant", "content": response})
                
                # Lưu sau mỗi tin nhắn
                save_chat(chat_name, messages)
                update_history(chat_name)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
            update_history(chat_name)
            return "quit"
        except EOFError:
            print(f"\n{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
            return "quit"

# ==================== MAIN MENU ====================
def main_menu():
    """Hiển thị menu chính"""
    init_dirs()
    api_key = get_api_key()
    
    if not api_key:
        print(f"{Fore.RED}❌ Không có API key, thoát chương trình{Style.RESET_ALL}")
        return
    
    current_chat = load_config().get("current_chat", "default")
    
    while True:
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}🤖 GEMINI CLI CHATBOT")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}1. {Fore.WHITE}Tiếp tục chat: {Fore.YELLOW}{current_chat}")
        print(f"{Fore.GREEN}2. {Fore.WHITE}Chọn / Tạo đoạn chat khác")
        print(f"{Fore.GREEN}3. {Fore.WHITE}Xem lịch sử các đoạn chat")
        print(f"{Fore.GREEN}4. {Fore.WHITE}Đổi API key")
        print(f"{Fore.GREEN}5. {Fore.WHITE}Thoát")
        print(f"{Fore.CYAN}{'='*60}")
        
        choice = input(f"{Fore.YELLOW}🔹 Lựa chọn (1-5): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            result = chat_loop(current_chat, api_key)
            if result == "new":
                # Tạo chat mới
                new_name = input(f"{Fore.GREEN}Tên đoạn chat mới (để trống = datetime): {Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                save_config({**load_config(), "current_chat": current_chat})
            elif result == "deleted":
                # Chat vừa bị xoá, cần tạo mới hoặc chọn cũ
                chats = list_chats()
                if chats:
                    current_chat = chats[0]["name"]
                else:
                    current_chat = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_config({**load_config(), "current_chat": current_chat})
            elif result == "quit":
                break
        
        elif choice == "2":
            chats = list_chats()
            
            if not chats:
                print(f"{Fore.YELLOW}📭 Chưa có đoạn chat nào, tạo mới ngay{Style.RESET_ALL}")
                new_name = input(f"{Fore.GREEN}Tên đoạn chat mới: {Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                save_config({**load_config(), "current_chat": current_chat})
                continue
            
            print(f"\n{Fore.CYAN}📋 Các đoạn chat hiện có:{Style.RESET_ALL}")
            for i, chat in enumerate(chats, 1):
                print(f"  {Fore.GREEN}{i}. {Fore.WHITE}{chat['name']} {Fore.BLUE}({chat['msg_count']} tin nhắn)")
            
            print(f"  {Fore.GREEN}0. {Fore.WHITE}Tạo đoạn chat mới")
            
            try:
                sel = int(input(f"\n{Fore.YELLOW}Chọn số: {Style.RESET_ALL}"))
                if sel == 0:
                    new_name = input(f"{Fore.GREEN}Tên đoạn chat mới: {Style.RESET_ALL}").strip()
                    if not new_name:
                        new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                    current_chat = new_name
                elif 1 <= sel <= len(chats):
                    current_chat = chats[sel-1]["name"]
                else:
                    print(f"{Fore.RED}Lựa chọn không hợp lệ{Style.RESET_ALL}")
                    continue
                
                save_config({**load_config(), "current_chat": current_chat})
                print(f"{Fore.GREEN}✅ Đã chuyển sang '{current_chat}'{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Vui lòng nhập số{Style.RESET_ALL}")
        
        elif choice == "3":
            show_history()
        
        elif choice == "4":
            new_key = input(f"{Fore.GREEN}Nhập API key mới: {Style.RESET_ALL}").strip()
            if new_key:
                config = load_config()
                config["api_key"] = new_key
                save_config(config)
                api_key = new_key
                print(f"{Fore.GREEN}✅ Đã cập nhật API key{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}API key không hợp lệ{Style.RESET_ALL}")
        
        elif choice == "5":
            print(f"{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
            break
        
        else:
            print(f"{Fore.RED}Lựa chọn không hợp lệ, vui lòng chọn 1-5{Style.RESET_ALL}")

# ==================== CHẠY CHƯƠNG TRÌNH ====================
if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        print(f"{Fore.RED}Lỗi không mong muốn: {e}{Style.RESET_ALL}")
        sys.exit(1)
