import requests
import re
import json
import time
import threading
import sys
import io
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

VIDEO_ID = "6_9ZiuONXt0"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

messages_cache = []
seen_ids = set()

def start_engine():
    global messages_cache, seen_ids
    print(f"[*] VRTICS Local Server Engine — ID: {VIDEO_ID}")
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    
    try:
        res = session.get(f"https://www.youtube.com/watch?v={VIDEO_ID}")
        html = res.text
        
        api_key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html).group(1)
        client_ver = re.search(r'"clientVersion":"([^"]+)"', html).group(1)
        visitor_data = re.search(r'"visitorData":"([^"]+)"', html).group(1)
        continuation = re.search(r'"continuation":"([^"]{80,})"', html).group(1)
        
        print(f"[+] Connected to YouTube. Engine Active.")
    except Exception as e:
        print(f"[!] Engine Failed to Initialize: {e}")
        return

    next_cont = continuation
    
    while True:
        try:
            api_url = f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={api_key}"
            payload = {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": client_ver,
                        "visitorData": visitor_data
                    }
                },
                "continuation": next_cont
            }
            
            res = session.post(api_url, json=payload)
            data = res.json()
            
            cont_contents = data.get("continuationContents", {}).get("liveChatContinuation", {})
            c_data = cont_contents.get("continuations", [{}])[0]
            next_cont = (c_data.get("invalidationContinuationData", {}).get("continuation") or 
                         c_data.get("timedContinuationData", {}).get("continuation") or 
                         c_data.get("reloadContinuationData", {}).get("continuation") or 
                         next_cont)
            
            timeout = c_data.get("timedContinuationData", {}).get("timeoutMs", 2000) / 1000
            
            actions = cont_contents.get("actions", [])
            for action in actions:
                item = action.get("addChatItemAction", {}).get("item", {}).get("liveChatTextMessageRenderer", {})
                if item:
                    msg_id = item.get("id")
                    if msg_id not in seen_ids:
                        seen_ids.add(msg_id)
                        author = item.get("authorName", {}).get("simpleText", "User")
                        msg = "".join([r.get("text", "") for r in item.get("message", {}).get("runs", [])])
                        
                        messages_cache.append({
                            "id": msg_id,
                            "author": author,
                            "text": msg
                        })
                        print(f"[{author}]: {msg}")
            
            # Keep cache from growing infinitely
            if len(messages_cache) > 200:
                messages_cache = messages_cache[-200:]
                
            time.sleep(max(1, timeout))
            
        except Exception as e:
            print(f"[!] Loop Error: {e}")
            time.sleep(5)
            session = requests.Session()
            session.headers.update({"User-Agent": UA})

class ChatHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress console printing of HTTP requests

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = json.dumps({"messages": messages_cache})
        self.wfile.write(response.encode('utf-8'))

def run_server():
    server = HTTPServer(('127.0.0.1', 8001), ChatHandler)
    print("====================================")
    print(" Local Server Running on Port 8001")
    print(" Please open index.html in browser")
    print("====================================")
    t = threading.Thread(target=start_engine, daemon=True)
    t.start()
    server.serve_forever()

if __name__ == "__main__":
    run_server()
