#!/usr/bin/env python3
"""
Gemini CLI Chatbot - Phiên bản cập nhật
Hỗ trợ các model Gemini mới nhất, dùng requests và colorama.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
    from colorama import init, Fore, Style, Back
    from tabulate import tabulate
    init(autoreset=True)
except ImportError as e:
    print(f"Thiếu thư viện: {e}")
    print("Vui lòng cài đặt: pip install requests colorama tabulate")
    sys.exit(1)

# ==================== CẤU HÌNH ====================
SCRIPT_DIR = Path(__file__).parent if "__file__" in globals() else Path.cwd()
CONFIG_DIR = SCRIPT_DIR / "gemini_data"
CONFIG_FILE = CONFIG_DIR / "config.json"
CHATS_DIR = CONFIG_DIR / "chats"
HISTORY_FILE = CONFIG_DIR / "history.json"

# --- DANH SÁCH MODEL ĐƯỢC CẬP NHẬT (DỰA TRÊN TÀI LIỆU MỚI NHẤT) ---
AVAILABLE_MODELS = {
    "1": {"id": "gemini-flash-latest", "name": "Gemini Flash Latest", "desc": "[Khuyên dùng] Bí danh luôn trỏ đến model Flash mới nhất."},
    "2": {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash-Lite", "desc": "Tiết kiệm chi phí nhất, cho tác vụ tần suất cao, dung lượng nhẹ."},
    "3": {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro Preview", "desc": "Bản xem trước mới nhất, mạnh mẽ cho tác vụ phức tạp."},
    "4": {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "desc": "Cân bằng hiệu năng, chi phí và tốc độ, có khả năng suy luận."},
    "5": {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "desc": "Mạnh mẽ nhất, lập luận sâu và viết code phức tạp."},
}
DEFAULT_MODEL_ID = "gemini-flash-latest"

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

# ==================== QUẢN LÝ API KEY & MODEL ====================
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

def choose_model():
    """Hiển thị menu chọn model và cập nhật vào config."""
    config = load_config()
    current_model_id = config.get("model", DEFAULT_MODEL_ID)

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}🤖 CHỌN MODEL GEMINI")
    print(f"{Fore.CYAN}{'='*60}")

    # Tìm tên model hiện tại
    current_name = current_model_id
    for model in AVAILABLE_MODELS.values():
        if model["id"] == current_model_id:
            current_name = model["name"]
            break
    print(f"{Fore.YELLOW}Model hiện tại: {Fore.GREEN}{current_name}{Style.RESET_ALL}\n")

    # Hiển thị danh sách model dạng bảng
    table = []
    for key, model in AVAILABLE_MODELS.items():
        marker = "✅ " if model["id"] == current_model_id else "   "
        table.append([f"{marker}{key}", model["name"], model["desc"]])
    print(tabulate(table, headers=["Chọn", "Model", "Mô tả"], tablefmt="rounded_grid"))

    choice = input(f"\n{Fore.GREEN}Nhập số để đổi model (Enter để giữ nguyên): {Style.RESET_ALL}").strip()

    if choice in AVAILABLE_MODELS:
        new_model_id = AVAILABLE_MODELS[choice]["id"]
        config["model"] = new_model_id
        save_config(config)
        print(f"{Fore.GREEN}✅ Đã đổi sang {AVAILABLE_MODELS[choice]['name']}{Style.RESET_ALL}")
        return new_model_id
    else:
        print(f"{Fore.BLUE}ℹ️ Giữ nguyên model hiện tại.{Style.RESET_ALL}")
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
    """Gọi Gemini API với model được chọn."""
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
    
    # Tìm tên model để hiển thị
    model_display_name = model_id
    for model in AVAILABLE_MODELS.values():
        if model["id"] == model_id:
            model_display_name = model["name"]
            break
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.MAGENTA}💬 Đang chat: {Fore.WHITE}{chat_name}")
    print(f"{Fore.BLUE}📡 Model: {Fore.YELLOW}{model_display_name}")
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
            elif cmd == "/model":
                new_model_id = choose_model()
                if new_model_id != model_id:
                    model_id = new_model_id
                    config = load_config()
                    config["model"] = model_id
                    save_config(config)
                    print(f"{Fore.GREEN}✅ Đã đổi model, hãy tiếp tục chat.{Style.RESET_ALL}")
                continue
            elif cmd == "/quit":
                print(f"{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
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
        print(f"{Fore.RED}❌ Không có API key, thoát chương trình{Style.RESET_ALL}")
        return
    
    config = load_config()
    current_model = config.get("model", DEFAULT_MODEL_ID)
    current_chat = config.get("current_chat", "default")
    
    while True:
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.MAGENTA}🤖 GEMINI CLI CHATBOT")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}1. {Fore.WHITE}Tiếp tục chat: {Fore.YELLOW}{current_chat}")
        print(f"{Fore.GREEN}2. {Fore.WHITE}Chọn / Tạo đoạn chat khác")
        print(f"{Fore.GREEN}3. {Fore.WHITE}Xem lịch sử các đoạn chat")
        print(f"{Fore.GREEN}4. {Fore.WHITE}Chọn Model Gemini")
        print(f"{Fore.GREEN}5. {Fore.WHITE}Đổi API key")
        print(f"{Fore.GREEN}6. {Fore.WHITE}Thoát")
        print(f"{Fore.CYAN}{'='*60}")
        
        choice = input(f"{Fore.YELLOW}🔹 Lựa chọn (1-6): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            result = chat_loop(current_chat, api_key, current_model)
            if result == "new":
                new_name = input(f"{Fore.GREEN}Tên đoạn chat mới (để trống = datetime): {Style.RESET_ALL}").strip()
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
                print(f"{Fore.YELLOW}📭 Chưa có đoạn chat nào, tạo mới ngay{Style.RESET_ALL}")
                new_name = input(f"{Fore.GREEN}Tên đoạn chat mới: {Style.RESET_ALL}").strip()
                if not new_name:
                    new_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_chat = new_name
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
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
                config = load_config()
                config["current_chat"] = current_chat
                save_config(config)
                print(f"{Fore.GREEN}✅ Đã chuyển sang '{current_chat}'{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Vui lòng nhập số{Style.RESET_ALL}")
        elif choice == "3":
            show_history()
        elif choice == "4":
            current_model = choose_model()
        elif choice == "5":
            new_key = input(f"{Fore.GREEN}Nhập API key mới: {Style.RESET_ALL}").strip()
            if new_key:
                config = load_config()
                config["api_key"] = new_key
                save_config(config)
                api_key = new_key
                print(f"{Fore.GREEN}✅ Đã cập nhật API key{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}API key không hợp lệ{Style.RESET_ALL}")
        elif choice == "6":
            print(f"{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Lựa chọn không hợp lệ, vui lòng chọn 1-6{Style.RESET_ALL}")

# ==================== CHẠY CHƯƠNG TRÌNH ====================
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Tạm biệt!{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Lỗi không mong muốn: {e}{Style.RESET_ALL}")
        sys.exit(1)
