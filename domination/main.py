import os
import sys
import random
import pickle
import optparse
import traceback
import gettext

from flask import Flask, render_template, session, redirect, url_for, \
        request, abort, jsonify
from gettext import NullTranslations

app = Flask(__name__)
app.secret_key = "".join(chr(random.randint(0, 255)) for _ in xrange(32))

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from domination.gameengine import DominationGame, CardTypeRegistry, Player,\
        GameRunner, DebugRequest, SelectDeal, SelectHandCards, SelectCard,\
        YesNoQuestion, Question, MultipleChoice, card_sets, editions, \
        AIPlayer, Kibitzer, FRESH, ENDED, RUNNING, STATES
from domination.tools import _
from domination.gzip_middleware import GzipMiddleware

AI_NAMES = ['Alan', 'Grace', 'Linus', 'Guido', 'Konrad', 'Donald',
            'Miranda', 'Ada', 'Hannah', 'Kim']
MAX_SEQNO_DIFF = 8

# init app object
app.games = {}
app.users = {}
app.languages = {}
app.game_storage_prefix = os.path.join(root_dir, "game-")
app.game_storage_postfix = ".pickle"
app.all_card_classes = [cls for cls in CardTypeRegistry.card_classes.itervalues()
                    if cls.optional & cls.implemented ]
app.card_classes = lambda: sorted(app.all_card_classes, key=lambda x: x.name.__str__())
app.template_context_processors[None].append(lambda: {'app': app, 'store': get_store()})

# init languages
for language in ["de_DE"]:
    # the path "domination/po" needs to be fixed, I guess. ~bombe
    # also, I am not sure that I am actually using gettext correctly here. will this
    # load all the languages independently after one another, or will there be some
    # kind of default/fallback system implemented here unknowingly?
    t = gettext.translation("domination", "domination/po", [language], codeset = "UTF-8")
    app.languages[language] = t
app.languages["en"] = NullTranslations()

def extract_request_language():
    """Extracts the preferred language of the browser from the request."""
    header_value = request.headers.get("Accept-Language")
    language_weights = header_value.split(",")
    request.translation = app.languages["en"]
    for language_weight in language_weights:
        language = language_weight.split(";q=")[0].replace("-", "_")
        if language in app.languages:
            request.translation = app.languages[language]
            break

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
            req.last_error = _("You need to select at least %i cards!", [req.count_lower])
            return Ellipsis
        if req.count_upper is not None and len(cards) > req.count_upper:
            req.last_error = _("You may select at most %i cards!", [req.count_upper])
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
    runners = app.games.values()
    runners.sort(key=lambda runner: (STATES.index(runner.state), runner.game.name))
    return render_template('index.html', runners=runners)

@app.route('/logout')
def logout():
    # remove the username from the session if its there
    username = session.pop('username', None)
    store = app.users.pop(username, None)
    if store:
        games = store["games"]
        for game, player in games.items():
            # XXX race condition possible
            if player.current:
                game.kick(Player("Logout Button"), player)
            else:
                game.players.remove(player)
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
            names = AI_NAMES[:]
            random.shuffle(names)
            try:
                n = min(len(names), int(request.form.get("numai", 1)))
            except ValueError:
                n = 1
            for i in range(n):
                player = AIPlayer(names[i] + " [AI]")
                game.players.append(player)
        return redirect(url_for('game', name=name))
    def transform_sets(sets):
        result = []
        for set in sets:
            result.append((set, [c.__name__ for c in sorted(set.card_classes, key = lambda x: x.name.string)]))
        return result
    name = _("Game of %s", [session["username"]])
    newname = name
    ctr = 0
    while newname in app.games:
        ctr += 1
        newname = "%s (%i)" % (name, ctr)
    return render_template("create_game.html", editions=editions,
                           card_sets=transform_sets(card_sets), name=newname)

@app.route("/game/<name>", methods=['GET', 'POST'])
@needs_login
@gets_game
def game(game_runner):
    game = game_runner.game
    seqno = game_runner.seqno
    if game_runner.game in get_store()["games"]:
        # remove inactive kibitzers
        game.kibitzers = [k for k in game.kibitzers
                if k.last_seqno + MAX_SEQNO_DIFF > seqno]
        player = get_store()["games"][game_runner.game]
        if request.method == 'POST':
            cv = player.response_condition
            cv.acquire()
            player.info_queue = []
            try:
                req = player.request_queue[0]
                assert hash(req) == int(request.form["req_id"])
                response = get_response(req)
                if response is not Ellipsis:
                    player.response.append(response)
                    player.request_queue.pop(0)
                    cv.notify()
            finally:
                cv.release()
            if response is not Ellipsis:
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
        info_queue = player.info_queue
    else:
        for kibitzer in game.kibitzers:
            if kibitzer.name == session["username"]:
                kibitzer.last_seqno = seqno
                break
        else:
            kibitzer = Kibitzer(session["username"])
            kibitzer.last_seqno = seqno
            game.kibitzers.append(kibitzer)
            game_runner.increment_seqno()

        player = None
        info_queue = kibitzer.info_queue
        req = None

    return render_template("game.html", runner=game_runner, game=game,
            req=req, req_id=hash(req), player=player, req_type=type(req).__name__,
            seqno=seqno, info_queue=info_queue, FRESH=FRESH, ENDED=ENDED, RUNNING=RUNNING)

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
    for kibitzer in game.kibitzers:
        if kibitzer.name == session["username"]:
            game.kibitzers.remove(kibitzer)
            break
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


@app.route("/game/clear_info/<name>", methods=["POST"])
@needs_login
@gets_game
def clear_info(game_runner):
    game = game_runner.game
    if game_runner.game in get_store()["games"]:
        player = get_store()["games"][game_runner.game]
        info_queue = player.info_queue
    else:
        for kibitzer in game.kibitzers:
            if kibitzer.name == session["username"]:
                break
        else:
            return redirect(url_for("game", name=game.name))
        info_queue = kibitzer.info_queue
    info_queue[:] = []
    return redirect(url_for("game", name=game.name))

@app.route("/game/kick_player/<name>/<playername>", methods=["POST"])
@needs_login
@gets_game
def kick_player(game_runner, playername):
    game = game_runner.game
    if game_runner.game in get_store()["games"]:
        player = get_store()["games"][game_runner.game]
        if player == game_runner.owner:
            kickee = [x for x in game.players if x.name == playername][0]
            if kickee == player:
                return render_error(_("You cannot kick yourself!"))
            # XXX race condition possible
            if not game_runner.waiting_for == kickee:
                return render_error(_("You can only kick a player if you are waiting for him!"))
            # XXX race condition possible
            if len(game.players) <= 2:
                # can be lifted as soon we have an impersonation feature
                return render_error(_("You cannot kick your last opponent!"))
            if not kickee.is_ai:
                games = get_store(playername)["games"]
                del games[game_runner.game]
            game.kick(player, kickee)

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


@app.before_request
def before_request():
    if "username" in session and session["username"] not in app.users:
        app.users[session["username"]] = {"games": {}}
    extract_request_language()

def restore_game(filename):
    f = file(filename, "rb")
    game_runner = pickle.load(f)
    game = game_runner.game
    app.games[game.name] = game_runner
    for player in game_runner.game.players:
        app.users.setdefault(player.name, {}).setdefault("games", {})[game] = player
    game_runner.daemon = True
    game_runner.start()


def main(argv):
    parser = optparse.OptionParser()
    parser.add_option('-i', '--server-ip', dest='server_ip', action='store', type="string",
            help='ip/hostname to run the server on', default="0.0.0.0")
    parser.add_option('-p', '--server-port', dest='server_port', action='store',
            type="int", help='port to run the server on', default=8080)
    parser.add_option('-r', '--restore', dest='restore', action='append',
            type="string", help='File to restore a game from', default=[])
    parser.add_option('-D', '--debug', dest='debug', action='store_true',
            help='Debug mode', default=None)

    options, args = parser.parse_args()
    if args:
        parser.error("don't know what to do with additional arguments")

    if options.debug:
        @app.route("/crash")
        def crash():
            for frame in sys._current_frames().values():
                traceback.print_stack(frame)
                print "\n"
            1/0
        app.secret_key = "insecure"

    for filename in options.restore:
        restore_game(filename)

    app.wsgi_app = GzipMiddleware(app.wsgi_app)
    app.run(host=options.server_ip, port=options.server_port, debug=options.debug, threaded=True)

if __name__ == '__main__':
    main(sys.argv[1:])

