import flask
import requests
import os
import json
import psycopg2
import urlparse

urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])


app = flask.Flask(__name__)


APP_TOKENS = [
    "***REMOVED***", 
    "***REMOVED***",
    "***REMOVED***",
]
COMMENT = '<!-- album id '
COMMENT_LEN = len(COMMENT)


class DatabaseError(Exception): pass


def update_database(album_id):
    try:
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        cur = conn.cursor()
        cur.execute('INSERT INTO list (album) VALUES (%s)', (album_id,))
        conn.commit()
    except (psycopg2.ProgrammingError, psycopg2.InternalError):
        raise DatabaseError
    finally:
        cur.close()
        conn.close()


def get_list():
    try:
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        cur = conn.cursor()
        cur.execute("SELECT album FROM list;")
        return [item[0] for item in cur.fetchall()]
    except (psycopg2.ProgrammingError, psycopg2.InternalError):
        raise DatabaseError
    finally:
        cur.close()
        conn.close()


def delete_album(album):
    try:
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM list where album = %s;", (album,))
        conn.commit()
    except (psycopg2.ProgrammingError, psycopg2.InternalError):
        raise DatabaseError
    finally:
        cur.close()
        conn.close()


@app.route('/consume', methods=['POST'])
def consume():
    form_data = flask.request.form
    if form_data.get('token') in APP_TOKENS:
        text = form_data.get('text', '')
        if 'bandcamp.com' in text and 'album' in text:
            url = text.replace('\\', '').replace('<', '').replace('>', '')
            response = requests.get(url)
            if response.ok:
                content = response.text
                if COMMENT in content:
                    pos = content.find(COMMENT)
                    album_id = content[pos + COMMENT_LEN:pos + COMMENT_LEN + 20]
                    album_id = album_id.split('-->')[0].strip()
                    try:
                        update_database(album_id)
                    except DatabaseError:
                        return json.dumps({'text': 'Failed to update database'}), 200
                    else:
                        return json.dumps({'text': 'Added to Bandcamp album list'}), 200
            return json.dumps({'text': 'Failed to add to Bandcamp album list'}), 200


@app.route('/list', methods=['GET'])
def list():
    try:
        response = flask.Response(json.dumps(get_list()))
    except DatabaseError:
        response = flask.Response(json.dumps({'text': 'Failed'}))
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/delete', methods=['POST'])
def delete():
    form_data = flask.request.form
    if form_data.get('token') in APP_TOKENS:
        album_id = form_data.get('text')
        if album_id:
            try:
                delete_album(album_id.strip())
            except DatabaseError:
                return json.dumps({'text': 'Failed'})
            else:
                return json.dumps({'text': 'Done'})
    return '', 200


@app.route('/add', methods=['POST'])
def add():
    form_data = flask.request.form
    if form_data.get('token') in APP_TOKENS:
        album_id = form_data.get('text')
        if album_id:
            try:
                update_database(album_id.strip())
            except DatabaseError:
                return json.dumps({'text': 'Failed'})
            else:
                return json.dumps({'text': 'Done'})
    return '', 200


@app.route('/scrape', methods=['GET'])
def scrape():
    return 'scrape', 200


if __name__ == "__main__":
    app.run(debug=os.environ.get('BC_DEBUG', True))

