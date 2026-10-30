import requests
import sys

def send_msg(wa_id, msg):
    r = requests.post(
        'https://prominent-faster-dropper.ngrok-free.dev/api/test-simulator',
        headers={'ngrok-skip-browser-warning': '1'},
        json={'message': msg, 'wa_id': wa_id},
        timeout=15
    )
    data = r.json()
    print(f"\n>>> SENT: {msg}")
    for m in data.get('messages', []):
        t = m.get('text') or m.get('body') or ''
        header = m.get('header')
        sys.stdout.buffer.write(f"Header: {header} | Text: {t[:120]}\n".encode('utf-8'))

wa_id = 'test-switcher-01'
send_msg(wa_id, '#tenant 1')
send_msg(wa_id, '#tenant')
send_msg(wa_id, 'hi')
