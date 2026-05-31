# Full task-focused analysis
import sys, os
sys.path.insert(0, 'src')

os.environ['PYTHONIOENCODING'] = 'utf-8'
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import base64, json, re

with open('cache/screenshot_current.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

from core.communication import ClientCommunicator
comm = ClientCommunicator(host='127.0.0.1', port=9999, password='default_password', timeout=120)
login = comm.send_request('login', {'user_id': 'explorer', 'key': 'aa7d3551ab7fdb975c2eed5251df53ade38aa12cd6161475221d774f27026763'})
session_id = login.get('session_id', '')
comm.set_logged_in(True)

SYSTEM_PROMPT = '''你是《明日方舟：终末地》精确游戏UI分析器。识别当前画面所有可交互元素并输出JSON。

{
  "page_name": "简短中文页面名",
  "page_type": "world_map/menu/dialog/battle/shop/task_ui/event/loading/other",
  "has_daily_tasks": false,
  "has_weekly_tasks": false,
  "has_event": false,
  "elements": [
    {"id":"e1","type":"button/text/icon/tab","label":"精确可见文本","bbox":[x1,y1,x2,y2],"confidence":0.95,"action":"tap/none","function":"该元素功能"}
  ],
  "description": "一句中文摘要"
}
'''

payload = {
    'instruction': '识别当前画面所有交互UI元素。特别注意：每日任务、每周任务、签到、奖励领取等任务相关按钮。列出所有菜单/标签页按钮。',
    'screenshot': b64,
    'history': [],
    'session_id': session_id,
    'user_id': 'explorer',
    'model_tag': 'exploration_deep',
    'system_prompt': SYSTEM_PROMPT,
}

print('Analyzing...')
result = comm.send_request('agent_chat', payload)
if result and result.get('status') == 'success':
    reply = result.get('reply', '')
    json_match = re.search(r'\{[\s\S]*\}', reply)
    if json_match:
        parsed = json.loads(json_match.group())
        print(f'Page: {parsed.get("page_name","?")}')
        print(f'Type: {parsed.get("page_type","?")}')
        print(f'Daily: {parsed.get("has_daily_tasks","?")} | Weekly: {parsed.get("has_weekly_tasks","?")} | Event: {parsed.get("has_event","?")}')
        print(f'Description: {parsed.get("description","")[:100]}')
        elements = parsed.get('elements', [])
        print(f'Elements ({len(elements)}):')
        for e in elements:
            b = e.get('bbox',[])
            bs = f'({int(b[0])},{int(b[1])})-({int(b[2])},{int(b[3])})' if len(b)>=4 else '?'
            print(f'  {e.get("type","?")} "{e.get("label","")}" {bs} a={e.get("action","?")} f={e.get("function","")[:30]}')
    else:
        print('No JSON:', reply[:500])
else:
    print('Failed:', result)

print('Done')
