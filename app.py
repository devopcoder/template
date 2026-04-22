from flask import Flask, render_template, request, jsonify, session
import requests
import json
import time
import random
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'fb_mass_messenger_secret'

# Global session storage
fb_sessions = {}

class FBMessenger:
    def __init__(self, cookies):
        self.session = requests.Session()
        self.session.cookies.update(cookies)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36',
            'X-FB-Friendly-Name': 'MessengerWebGraphQL'
        })
    
    def get_groups(self):
        """Get all group chats"""
        try:
            response = self.session.post('https://www.facebook.com/api/graphql/', data={
                'variables': json.dumps({"scale1": 100}),
                'doc_id': '5787525828022483'  # Messenger threads doc_id
            })
            data = response.json()
            groups = []
            for edge in data.get('data', {}).get('viewer', {}).get('message_threads', {}).get('edges', []):
                thread = edge['node']
                if thread['thread_type'] == 'GROUP':
                    groups.append({
                        'id': thread['thread_key']['thread_fbid'],
                        'name': thread['name'] or 'Unnamed Group'
                    })
            return groups
        except:
            return []
    
    def send_message(self, thread_id, message):
        """Send message to group"""
        payload = {
            'message': {'text': message},
            'thread_id': thread_id,
            'upload_id': int(time.time() * 1000)
        }
        response = self.session.post('https://www.facebook.com/messaging/send/', data=payload)
        return response.status_code == 200

@app.route('/')
def index():
    logged_in = 'cookies' in session
    groups = []
    if logged_in:
        messenger = FBMessenger(session['cookies'])
        groups = messenger.get_groups()
    return render_template('index.html', logged_in=logged_in, groups=groups)

@app.route('/login', methods=['POST'])
def login():
    cookies = {
        'c_user': request.form['c_user'],
        'xs': request.form['xs'],
        'fr': request.form.get('fr', ''),
        'sb': request.form.get('sb', '')
    }
    
    # Test login
    messenger = FBMessenger(cookies)
    response = messenger.session.get('https://messenger.com')
    
    if response.status_code == 200:
        session['cookies'] = cookies
        return jsonify({'success': True, 'message': 'Login successful!'})
    return jsonify({'success': False, 'message': 'Invalid cookies!'})

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/send_mass', methods=['POST'])
def send_mass():
    if 'cookies' not in session:
        return jsonify({'error': 'Not logged in'})
    
    messenger = FBMessenger(session['cookies'])
    target_groups = request.json['groups']
    message = request.json['message']
    
    results = []
    for group_id in target_groups:
        success = messenger.send_message(group_id, message)
        results.append({'group_id': group_id, 'success': success})
        
        # 3s delay + jitter
        time.sleep(3 + random.uniform(-0.5, 1))
    
    return jsonify({'results': results, 'total': len(results)})

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)