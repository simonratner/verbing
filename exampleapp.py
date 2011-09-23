import base64
import os
import os.path
import simplejson as json
import urllib
import urllib2
import httplib2

from flask import Flask, abort, request, redirect, render_template, url_for

FBAPI_APP_ID = os.environ.get('FACEBOOK_APP_ID')


def oauth_login_url(preserve_path=True, next_url=None):
    fb_login_uri = ("https://www.facebook.com/dialog/oauth"
                    "?client_id=%s&redirect_uri=%s" %
                    (app.config['FBAPI_APP_ID'], get_home()))

    if app.config['FBAPI_SCOPE']:
        fb_login_uri += "&scope=%s" % ",".join(app.config['FBAPI_SCOPE'])
    return fb_login_uri


def simple_dict_serialisation(params):
    return "&".join(map(lambda k: "%s=%s" % (k, params[k]), params.keys()))


def base64_url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip('=')


def fbapi_get_string(path, domain=u'graph', params=None, access_token=None,
                     encode_func=urllib.urlencode):
    """Make an API call"""
    if not params:
        params = {}
    params[u'method'] = u'GET'
    if access_token:
        params[u'access_token'] = access_token

    for k, v in params.iteritems():
        if hasattr(v, 'encode'):
            params[k] = v.encode('utf-8')

    url = u'https://' + domain + u'.facebook.com' + path
    params_encoded = encode_func(params)
    url = url + params_encoded
    result = urllib2.urlopen(url).read()

    return result


def fbapi_auth(code):
    params = {'client_id': app.config['FBAPI_APP_ID'],
              'redirect_uri': get_home(),
              'client_secret': app.config['FBAPI_APP_SECRET'],
              'code': code}

    result = fbapi_get_string(path=u"/oauth/access_token?", params=params,
                              encode_func=simple_dict_serialisation)
    pairs = result.split("&", 1)
    result_dict = {}
    for pair in pairs:
        (key, value) = pair.split("=")
        result_dict[key] = value
    return (result_dict["access_token"], result_dict["expires"])


def fbapi_get_application_access_token(id):
    token = fbapi_get_string(
        path=u"/oauth/access_token",
        params=dict(grant_type=u'client_credentials', client_id=id,
                    client_secret=app.config['FB_APP_SECRET']),
        domain=u'graph')

    token = token.split('=')[-1]
    if not str(id) in token:
        print 'Token mismatch: %s not in %s' % (id, token)
    return token


def fql(fql, token, args=None):
    if not args:
        args = {}

    args["query"], args["format"], args["access_token"] = fql, "json", token
    return json.loads(
        urllib2.urlopen("https://api.facebook.com/method/fql.query?" +
                        urllib.urlencode(args)).read())


def fb_call(call, args=None):
    return json.loads(urllib2.urlopen("https://graph.facebook.com/" + call +
                                      '?' + urllib.urlencode(args)).read())

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_object('conf.Config')


def get_home():
    return 'https://' + request.host + '/'


@app.route('/', methods=['GET', 'POST'])
def index():
    print get_home()
    #if request.args.get('access_token', None):
        #access_token = request.args.get('access_token')
    if request.args.get('code', None):
        access_token = fbapi_auth(request.args.get('code'))[0]

        me = fb_call('me', args={'access_token': access_token})
        app = fb_call(FBAPI_APP_ID, args={'access_token': access_token})

        redir = get_home() + 'close/'
        POST_TO_WALL = ("https://www.facebook.com/dialog/feed?redirect_uri=%s&"
                        "display=popup&app_id=%s" % (redir, FBAPI_APP_ID))
        SEND_TO = ('https://www.facebook.com/dialog/send?'
                   'redirect_uri=%s&display=popup&app_id=%s&link=%s'
                   % (redir, FBAPI_APP_ID, get_home()))

        return render_template(
            'index.html', appId=FBAPI_APP_ID, token=access_token, app=app, me=me,
            POST_TO_WALL=POST_TO_WALL, SEND_TO=SEND_TO)
    else:
        print oauth_login_url(next_url=get_home())
        return redirect(oauth_login_url(next_url=get_home()))


@app.route('/close/', methods=['GET', 'POST'])
def close():
    return render_template('close.html')

@app.route('/word/<word>', methods=['GET'])
def get_word(word):
    return render_template('word.html', appId=FBAPI_APP_ID, word=word.lower())

@app.route('/word/', methods=['POST'])
def post_word():
    word = request.form['word'].lower()
    # curl -X POST -F "access_token=AAAEGGC3TuoMBAFUZBzWPn7EUGZC71ZAuPZBdKzF9hpKQJ3LyiOoSXgyxKzxJGxUHNMR1Nm5ae3POKyEEXaZAI36oolZBuHaKVrkFQUhfX3ZCAZDZD" -F "word=http://verbing.herokuapp.com/word/verb" "https://graph.facebook.com/me/verbing:verb"
    h = httplib2.Http()
    url = url_for('get_word', word=word)
    data = dict(access_token=request.form['token'], word="http://%s%s" % (request.host, url))
    resp, content = h.request("https://graph.facebook.com/me/verbing:verb", "POST", urllib.urlencode(data))
    print data
    print resp
    if int(resp['status']) == 200:
      return redirect(url)
    abort(500)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    if app.config.get('FBAPI_APP_ID') and app.config.get('FBAPI_APP_SECRET'):
        app.run(host='0.0.0.0', port=port)
    else:
        print 'Cannot start application without Facebook App Id and Secret set'
