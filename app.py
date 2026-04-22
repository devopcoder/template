from flask import Flask, render_template, request, jsonify, session
import requests
import json
import time
import random
import os

app = Flask(__name__)
app.secret_key = 'fb_mass_messenger_v3_2026_fixed'

class FBMessenger:
    def __init__(self, cookies):
        self.session = requests.Session()
        if cookies:
            self.session.cookies.update(cookies)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'X-FB-Friendly-Name': 'MessengerWebGraphQL',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.messenger.com/'
        })
    
    def test_session(self):
        try:
            response = self.session.get('https://www.messenger.com/', timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_groups(self):
        try:
            # Real GraphQL query for threads
            variables = json.dumps({
                "scale1": 100,
                "afterCursor0": None
            })
            
            data = {
                'variables': variables,
                'doc_id': '5787525828022483',  # MessengerRecentConversationsQuery
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'MessengerRecentConversationsQuery'
            }
            
            response = self.session.post('https://www.facebook.com/api/graphql/', data=data, timeout=15)
            
            if response.status_code != 200:
                return []
            
            result = response.json()
            groups = []
            
            threads = result.get('data', {}).get('viewer', {}).get('message_threads', {}).get('edges', [])
            for edge in threads:
                thread = edge.get('node', {})
                thread_type = thread.get('thread_type')
                if thread_type == 'GROUP':
                    group_info = {
                        'id': thread.get('thread_key', {}).get('thread_fbid', ''),
                        'name': thread.get('name', 'Unnamed Group'),
                        'participant_count': len(thread.get('participants', {}).get('edges', []))
                    }
                    if group_info['id']:
                        groups.append(group_info)
            
            return groups[:50]  # Safety limit
        except Exception as e:
            print(f"Groups fetch error: {e}")
            return []
    
    def send_message(self, thread_id, message):
        try:
            payload = {
                'message': json.dumps({'ranges': [], 'text': message}),
                'upload_id': str(int(time.time() * 1000)),
                'actor_id': list(self.session.cookies)[0] if self.session.cookies else '',
                'client': 'web',
                'thread_id': thread_id
            }
            
            response = self.session.post(
                'https://www.facebook.com/messaging/send/',
                data=payload,
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

# Routes
@app.route('/')
def index():
    logged_in = 'cookies' in session
    groups = []
    status_message = ''
    
    if logged_in:
        messenger = FBMessenger(session['cookies'])
        groups = messenger.get_groups()
        status_message = f'✅ Logged in! {len(groups)} groups found'
    
    return render_template('index.html', 
                         logged_in=logged_in, 
                         groups=groups, 
                         status_message=status_message)

@app.route('/login', methods=['POST'])
def login():
    try:
        # SAFE form parsing
        form_data = request.form.to_dict()
        cookies = {
            'c_user': form_data.get('c_user', '').strip(),
            'xs': form_data.get('xs', '').strip(),
            'fr': form_data.get('fr', '').strip(),
            'sb': form_data.get('sb', '').strip()
        }
        
        # Validate
        if not cookies['c_user'] or not cookies['xs']:
            return jsonify({'success': False, 'message': '❌ c_user & xs required!'})
        
        messenger = FBMessenger(cookies)
        if messenger.test_session():
            session['cookies'] = cookies
            groups = messenger.get_groups()
            return jsonify({
                'success': True, 
                'message': f'✅ Login OK! {len(groups)} groups ready',
                'group_count': len(groups)
            })
        else:
            return jsonify({'success': False, 'message': '❌ Invalid cookies/session'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'❌ Error: {str(e)}'})

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({'success': True, 'message': '👋 Logged out'})

@app.route('/send_mass', methods=['POST'])
def send_mass():
    try:
        data = request.get_json()
        groups = data.get('groups', [])
        message = data.get('message', '').strip()
        
        if not groups or not message:
            return jsonify({'error': 'No groups or message selected'})
        
        messenger = FBMessenger(session['cookies'])
        results = []
        success_count = 0
        
        for i, group_id in enumerate(groups[:25]):  # Max 25 for safety
            print(f"Sending to group {group_id[:8]}...")
            success = messenger.send_message(group_id, message)
            results.append({'id': group_id[:8], 'success': success})
            
            if success:
                success_count += 1
            
            # 3s delay + jitter
            if i < len(groups) - 1:
                delay = 3 + random.uniform(0, 1)
                time.sleep(delay)
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': f'{success_count}/{len(groups)} sent successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=port, debug=False)
