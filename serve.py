import os
from datetime import datetime, timedelta
from flask import Flask, request, abort, jsonify, g,redirect
from sqlite3 import dbapi2 as sqlite3
import itertools
from utils import Config

def temp_token():
    import binascii
    temp_token = binascii.hexlify(os.urandom(24))
    return temp_token.decode('utf-8')


WEBHOOK_VERIFY_TOKEN = open('token.txt', "r").read()
# WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN')
# CLIENT_AUTH_TIMEOUT = 24 # in Hours

app = Flask(__name__)

# -----------------------------------------------------------------------------
# utilities for database interactions 
# -----------------------------------------------------------------------------
# to initialize the database: sqlite3 arxiv_link_tracker.db < schema.sql
def connect_db():
  sqlite_db = sqlite3.connect(Config.database_path)
  sqlite_db.row_factory = sqlite3.Row # to return dicts rather than tuples
  return sqlite_db

def query_db(query, args=(), one=False):
  """Queries the database and returns a list of dictionaries."""
  cur = g.db.execute(query, args)
  rv = cur.fetchall()
  return rv

def insert_click_event(user_id, arxiv_id):
    # rv = query_db('insert into library (paper_id, user_id) values (?,?)',
    #             [arxiv_id,user_id])
    c = g.db.cursor()
    c.execute('insert into library (paper_id, user_id) values (?,?)',
                [arxiv_id,user_id])
    rv = g.db.commit()

    return rv

def get_all_clicks(user_id):
    # rv = query_db('select * from library where user_id = ?',
    #             [user_id], one=True)
    c = g.db.cursor()
    cur = c.execute('select * from library ')
    rv = [dict((cur.description[i][0], value) \
               for i, value in enumerate(row)) for row in cur.fetchall()]
    return rv

# -----------------------------------------------------------------------------
# connection handlers
# -----------------------------------------------------------------------------

@app.before_request
def before_request():
  # this will always request database connection, even if we dont end up using it ;\
  g.db = connect_db()
  # retrieve user object from the database if user_id is set

@app.teardown_request
def teardown_request(exception):
  db = getattr(g, 'db', None)
  if db is not None:
    db.close()


@app.route('/tracking', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        verify_token = request.args.get('verify_token')
        if verify_token == WEBHOOK_VERIFY_TOKEN:
            # if their request has the correct token then we want to parse the request
            
            user_id = request.args.get('user_id')
            arxiv_id = request.args.get('arxiv_id')

            # get the url we need to redirect to:
            redirect_url = request.args.get('redirect_url')
            print([arxiv_id,user_id])
            # now that we've got everything we need, let's insert the event
            insert_res = insert_click_event(user_id, arxiv_id)
            print(insert_res)
            
            return redirect(redirect_url, code=302)
        else:
            return jsonify({'status':'bad token'}), 401

    else:
        abort(400)

@app.route('/clicks', methods=['GET', 'POST'])
def show_clicks():
    verify_token = request.args.get('verify_token')
    if verify_token == WEBHOOK_VERIFY_TOKEN:
        # just spit out json of the results from the query
        res = get_all_clicks(request.args.get('user_id'))
        print(res)
        return  jsonify(res)
       

if __name__ == '__main__':
    if WEBHOOK_VERIFY_TOKEN is None:
        print('WEBHOOK_VERIFY_TOKEN has not been set in the environment.\nGenerating random token...')
        token = temp_token()
        print('Token: %s' % token)
        WEBHOOK_VERIFY_TOKEN = token
    app.run(debug=True)