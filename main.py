from flask import Flask, request, redirect
import requests
import os
import json
import shelve

db = shelve.open("db", flag="c", writeback=True)

app = Flask(__name__)

discord_login_url = "https://discord.com/api/oauth2/authorize?client_id=1074450436414787594&redirect_uri=https%3A%2F%2Fstatic.164.158.34.188.clients.your-server.de%2Fcallback&response_type=code&scope=identify"

if not 'logins' in db:
    db['logins'] = {}

if not 'callbacks' in db:
    db['callbacks'] = {}


@app.after_request
def apply_caching(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response


@app.route('/')
def main():
    return 'alive'


@app.route('/invalidateall')
def invalidateAll():
    db['logins'] = {}
    return 'logins invalidated'


@app.route('/invalidate')
def invalidate():
    state = request.args['state']
    db['logins'][state] = {}
    return json.dumps('login for ' + state + ' invalidated',
                      ensure_ascii=False).encode('utf8')


@app.route('/me')
def getUser():
    state = request.args['state']
    if not state or state not in db['logins']:
        return json.dumps({}, ensure_ascii=False).encode('utf8')
    print("get user for state: " + state)
    return json.dumps(dict(db['logins'][state]),
                      ensure_ascii=False).encode('utf8')


@app.route('/login')
def login():
    state = request.args['state']
    print("logging in for state: " + state)
    db['callbacks'][state] = request.args['callback']
    guild = ""
    if 'guilds' in request.args:
        guild = "%20guilds"
    return redirect(discord_login_url + guild + "&state=" + state, code=302)


def exchange_code(code, state):
    data = {
        'client_id': '1074450436414787594',
        'client_secret': os.environ['discord.secret'],
        'grant_type': 'authorization_code',
        'code': code,
        'state': state,
        'redirect_uri': 'https://static.164.158.34.188.clients.your-server.de/callback'
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post('https://discord.com/api/v10/oauth2/token',
                      data=data,
                      headers=headers)
    r.raise_for_status()
    result = r.json()

    headers = {
        'Authorization': result['token_type'] + ' ' + result['access_token']
    }
    r = requests.get("https://discord.com/api/v10/oauth2/@me", headers=headers)
    result = r.json()
    print(result)
    db['logins'][state] = result['user']

    return redirect(db['callbacks'][state], 302)


@app.route('/callback')
def callback():
    try:
        print("called back")
        args = request.args
        state = args['state']
        code = args['code']
        return exchange_code(code, state)
    except Exception as e:
        print(e)
        return redirect(db['callbacks'][state], 302)


app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
