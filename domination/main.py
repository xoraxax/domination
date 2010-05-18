import os
import sys
import random

from flask import Flask, render_template, session, redirect, url_for, \
        request, abort, jsonify

app = Flask(__name__)
app.secret_key = "".join(chr(random.randint(0, 255)) for _ in xrange(32))


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from domination.gameengine import DominationGame, CardTypeRegistry, Player,\
        GameRunner, DebugRequest, SelectDeal, SelectHandCards, SelectCard,\
        YesNoQuestion, Question, MultipleChoice, card_sets, editions, \
        AIPlayer
from domination.tools import _
from domination.gzip_middleware import GzipMiddleware


app.games = {}
app.users = {}
app.card_classes = [cls for cls in CardTypeRegistry.card_classes.itervalues()
                    if cls.optional]
app.card_classes.sort(key=lambda x: x.name)
app.template_context_processors.append(lambda: {'app': app, 'store': get_store()})


def needs_login(func):
    def innerfunc(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for('login', url=request.url))
        return func(*args, **kwargs)
    innerfunc.__name__ = func.__name__
    return innerfunc

def gets_game(func):
    def innerfunc(name, *args, **kwargs):
        if name not in app.games:
            return render_error(_("Game not found!"))
        return func(app.games[name], *args, **kwargs)
    innerfunc.__name__ = func.__name__
    return innerfunc

def get_store(username=None):
    if username is None and "username" not in session:
        return None
    return app.users[username or session["username"]]

def render_error(error_msg):
    return render_template("error.html", error_msg=error_msg)

def get_response(req):
    if isinstance(req, SelectDeal):
        if "card" not in request.form:
            return None
        key = request.form["card"]
        card_cls = CardTypeRegistry.keys2classes((key, ))[0]
        if card_cls in req.cards and req.is_buyable(card_cls):
            return key
        else:
            assert 0, "Invalid choice!"
    elif isinstance(req, SelectCard):
        key = request.form["card"]
        card_cls = CardTypeRegistry.keys2classes((key, ))[0]
        if card_cls in req.card_classes:
            return card_cls
        else:
            assert 0, "Invalid choice!"
    elif isinstance(req, YesNoQuestion):
        return request.form["answer"] == "yes"
    elif isinstance(req, Question):
        return request.form["answer"]
    elif isinstance(req, MultipleChoice):
        return request.form.getlist("answer")
    elif isinstance(req, SelectHandCards):
        if "canceled" in request.form and req.count_lower == 0:
            return None
        keys = request.form.getlist("card")
        cards = []
        sorted_hand = req.player.sorted_hand
        for key in keys:
            card = sorted_hand[int(key)]
            assert req.is_selectable(card)
            cards.append(card)
        if len(cards) < req.count_lower:
            req.last_error = _("You need to select at least %i cards!") % (req.count_lower, )
            return Ellipsis
        if req.count_upper is not None and len(cards) > req.count_upper:
            req.last_error = _("You may select at most %i cards!") % (req.count_upper, )
            return Ellipsis
        return cards
    else:
        assert 0, "Unknown request"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        if username in app.users:
            return render_error(_("Username already in use."))
        session['username'] = username
        if request.args.get('url'):
            return redirect(request.args['url'])
        else:
            return redirect(url_for('index'))
    return render_template("login.html")


@app.route('/')
def index():
    if "username" not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/logout')
def logout():
    # remove the username from the session if its there
    app.users.pop(session.pop('username', None), None)
    return redirect(url_for("index"))

@app.route("/create_game", methods=['GET', 'POST'])
@needs_login
def create_game(): # XXX check for at most 10 sets
    if request.method == 'POST':
        name = request.form['name']
        if name in app.games:
            return render_error(_("Game with this name is already existing!"))
        if not name:
            return render_error(_("Please enter a name!"))
        game = DominationGame(name,
                CardTypeRegistry.keys2classes(request.form.getlist('card_key')))
        player = Player(session["username"])
        game.players.append(player)
        app.games[name] = GameRunner(game, player)
        get_store()["games"][game] = player
        if request.form.get("ai"):
            player = AIPlayer("CPU0")
            game.players.append(player)
        return redirect(url_for('game', name=name))
    def transform_sets(sets):
        result = []
        for set in sets:
            result.append((set, [c.__name__ for c in set.card_classes]))
        return result
    return render_template("create_game.html", editions=editions,
                           card_sets=transform_sets(card_sets))

@app.route("/game/<name>", methods=['GET', 'POST'])
@needs_login
@gets_game
def game(game_runner):
    game = game_runner.game
    seqno = game_runner.seqno
    if game_runner.game in get_store()["games"]:
        player = get_store()["games"][game_runner.game]
        if request.method == 'POST':
            cv = player.response_condition
            cv.acquire()
            try:
                req = player.request_queue[0]
                assert id(req) == int(request.form["req_id"])
                response = get_response(req)
                if response is not Ellipsis:
                    player.response.append(response)
                    player.request_queue.pop(0)
                    player.info_queue = []
                    cv.notify()
            finally:
                cv.release()
            cv = game_runner.seqno_condition
            cv.acquire()
            while game_runner.seqno <= req.seqno:
                cv.wait()
            cv.release()
        req = None
        if player.request_queue:
            req = player.request_queue[0]
            if isinstance(req, DebugRequest):
                # cleanup XXX more
                del app.games[game.name]
                raise req.exc_info[0], req.exc_info[1], req.exc_info[2]
    else:
        player = None
        req = None

    return render_template("game.html", runner=game_runner, game=game,
            req=req, req_id=id(req), player=player, req_type=type(req).__name__,
            seqno=seqno)

@app.route("/game/join/<name>", methods=["POST"])
@needs_login
@gets_game
def join_game(game_runner):
    assert not game_runner in get_store()["games"]
    if not game_runner.joinable:
        return render_error(_("Game has begun or ended already."))
    get_store()["games"][game_runner.game] = player = Player(session["username"])
    game = game_runner.game
    assert player not in game.players
    game.players.append(player)
    if len(game.players) > game.MAX_PLAYERS:
        game.players.remove(player)
        return render_error(_("Too many players in the game!"))
    game_runner.increment_seqno()
    return redirect(url_for("game", name=game.name))

@app.route("/game/start/<name>", methods=["POST"])
@needs_login
@gets_game
def start_game(game_runner):
    game_runner.start()
    game = game_runner.game
    game_runner.increment_seqno()
    return redirect(url_for("game", name=game.name))

@app.route("/game/cancel/<name>", methods=["POST"])
@needs_login
@gets_game
def cancel_game(game_runner):
    player = get_store()["games"][game_runner.game]
    if player is not game_runner.owner:
        abort(401)
    game_runner.cancel()
    game = game_runner.game
    return redirect(url_for("game", name=game.name))

@app.route("/game/check_seqno/<name>")
@needs_login
@gets_game
def check_seqno(game_runner):
    old_seqno = request.args.get('seqno', type=int)
    cv = game_runner.seqno_condition
    cv.acquire()
    while game_runner.seqno == old_seqno:
        cv.wait()
    cv.release()
    return jsonify()

@app.route("/crash")
def crash():
    1/0

@app.before_request
def before_request():
    if "username" in session and session["username"] not in app.users:
        app.users[session["username"]] = {"games": {}}


if __name__ == '__main__':
    app.secret_key = "insecure"
    app.wsgi_app = GzipMiddleware(app.wsgi_app)
    app.run(host="0.0.0.0", debug=True, threaded=True)

