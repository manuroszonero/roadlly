import webbrowser
import uvicorn
import time
import threading

def open_browser():
    time.sleep(1.2)
    print("\n" + "="*55)
    print("  🚀 Roadlyy Platform is Live!")
    print("  🔗 Clickable Link: http://127.0.0.1:8000")
    print("="*55 + "\n")
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
