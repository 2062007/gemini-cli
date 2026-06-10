<!-- markdownlint-disable MD033 -->
<p align="center">
  <img src="https://raw.githubusercontent.com/google-gemini/gemini-api-docs/main/assets/gemini-badge.png" alt="Gemini API" width="120"/>
</p>

<h1 align="center">🤖 Gemini CLI Chatbot</h1>
<p align="center">
  <strong>Unlimited Language Code Generation & Execution • Multi‑session Chat • Model Switcher</strong>
</p>

<p align="center">
  <a href="#-features"><img src="https://img.shields.io/badge/Features-14-8A2BE2?style=flat-square"></a>
  <a href="#-supported-languages"><img src="https://img.shields.io/badge/Code-30%2B%20Languages-007ACC?style=flat-square"></a>
  <a href="#-installation"><img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python"></a>
  <a href="#-license"><img src="https://img.shields.io/badge/License-MIT-green?style=flat-square"></a>
</p>

<p align="center">
  <i>Chat with Google Gemini AI, generate and run code in any language, manage chat sessions, and switch models – all from your terminal.</i>
</p>

---

## ✨ Features

| Category | Capabilities |
|----------|--------------|
| **💬 Chat** | Multi‑session chat, persistent history, command shortcuts |
| **🤖 Models** | Auto‑fetch latest Gemini models, switch between them (Flash, Pro, etc.) |
| **⚙️ Code** | Generate + **execute** code in **30+ languages** (Python, JS, Go, Rust, Java, C++, …) |
| **🌍 I18N** | English / Vietnamese interface (easily extendable) |
| **💾 Storage** | Local JSON storage for chats, API key, and generated code |
| **🎨 UI** | Colorful terminal output with loading animations and boxed layouts |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- [Google Gemini API key](https://aistudio.google.com/apikey)

### 2. Installation
```bash
git clone https://github.com/yourusername/gemini-cli-chatbot.git
cd gemini-cli-chatbot
pip install -r requirements.txt
```

requirements.txt:

```
requests>=2.31.0
colorama>=0.4.6
```

3. Run

```bash
python gemini.py
```

On first run you will be prompted for your Gemini API key – it's stored locally and never shared.

---

🕹️ Usage

Main Menu

After launching, you see:

```
🤖 GEMINI CLI CHATBOT
1. Continue chat: default
2. Select / Create another chat
3. View chat history
4. Select Gemini model
5. Change API key
6. Change language
7. Exit
```

Chat Commands (inside a conversation)

Command Action
/code <lang> <description> Generate & run code (e.g., /code python calculate factorial)
/menu or /back Return to main menu
/new Create a new chat session
/delete Delete current chat
/history Show all chat sessions
/model Switch Gemini model
/quit Exit the program

---

💻 Code Generation & Execution

This chatbot can generate and run code in many languages using your local interpreters/compilers.

🔧 Supported Languages (30+)

Language Runtime Language Runtime
Python python3 JavaScript/Node node
TypeScript tsc + node Ruby ruby
PHP php Perl perl
R Rscript Go go build + run
Rust rustc C gcc
C++ g++ Java javac + java
Kotlin kotlinc + java -jar Swift swift
Lua lua Scala scalac + scala
Bash bash PowerShell pwsh
SQLite sqlite3 … and more! 

Missing a language? You can add it to the LANGUAGE_RUNTIMES dictionary in the script.

✍️ Example

```
👤 You: /code python Compute the first 10 Fibonacci numbers
🤖 Gemini: [generates Python code]
✅ Generated code:
----------------------------------------
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        print(a, end=' ')
        a, b = b, a+b
fib(10)
----------------------------------------
Run this code? (y/N): y
🚀 Running...
📤 Output:
0 1 1 2 3 5 8 13 21 34 
```

---

📁 File Structure

```
gemini-cli-chatbot/
├── chatbot.py               # Main script
├── gemini_data/
│   ├── config.json          # API key, current model, language, active chat
│   ├── chats/               # Each chat session stored as JSON
│   ├── history.json         # Overview of all chats
│   ├── model_cache.json     # Cached list of Gemini models
│   └── generated_code/      # Saved code snippets (by language)
└── README.md
```

---

⚙️ Configuration

All settings are stored in gemini_data/config.json. Example:

```json
{
  "language": "en",
  "api_key": "YOUR_API_KEY",
  "model": "gemini-2.0-flash",
  "current_chat": "default"
}
```

You can also change them interactively from the main menu.

---

🌐 Multi‑language Interface

The chatbot supports English and Vietnamese out of the box.
Switch from menu option 6 or edit config.json.
Translations are centralized in the TEXTS dictionary – easy to add more languages.

---

🛠️ Troubleshooting

Issue Solution
ModuleNotFoundError: No module named 'requests' Run pip install requests colorama
API key not found Get a key from Google AI Studio and enter it
Code execution fails for a language Ensure the required runtime (node, go, rustc, etc.) is installed and in your PATH
Connection error Check your internet connection – the script reaches generativelanguage.googleapis.com

---

📜 License

MIT © 2062007 – feel free to use, modify, and distribute.

---

🤝 Contributing

Contributions are welcome!

· Add more languages to LANGUAGE_RUNTIMES
· Improve error handling or UI
· Translate to other languages

Simply fork, create a branch, and submit a pull request.

---

<p align="center">
  Made with ❤️ and Python • Powered by <a href="https://deepmind.google/technologies/gemini/">Google Gemini</a>
</p>
