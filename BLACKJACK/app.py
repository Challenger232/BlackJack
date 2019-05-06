from flask import Flask, render_template, request, redirect, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from flask_sqlalchemy import *
import random

app = Flask(__name__, static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blackjack.db'
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = "asdlfkaldskfadshfalsfjkh"


class User(db.Model, UserMixin):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(40), nullable=False)
    balance = db.Column(db.Integer)

    players = db.relationship('Player', backref='user')

    def get_id(self):
        return self.user_id


class Deck(db.Model):
    card_id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer)
    suit = db.Column(db.String(10))
    face = db.Column(db.String(1))

    game_id = db.Column(db.Integer, db.ForeignKey('game.game_id'))
    player_id = db.Column(db.Integer, db.ForeignKey('player.player_id'))


class Game(db.Model):
    game_id = db.Column(db.Integer, primary_key=True)
    occupancy = db.Column(db.Integer)
    turn = db.Column(db.Integer)

    players = db.relationship('Player', backref='game')
    decks = db.relationship('Deck', backref='game')


class Player(db.Model):
    player_id = db.Column(db.Integer, primary_key=True)
    player_state = db.Column(db.Integer)
    bet = db.Column(db.Integer)
    score = db.Column(db.Integer)

    game_id = db.Column(db.Integer, db.ForeignKey('game.game_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    decks = db.relationship('Deck', backref='player')


login_manager = LoginManager(app)
login_manager.init_app(app)

pair = 0


@login_manager.user_loader
def load_user(uid):
    user = User.query.get(uid)
    return user


@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
def home():
    clear()
    return render_template('home.html')


@app.route('/newuser', methods=['GET', 'POST'])
def newuser():
    clear()
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        user = User(username=username, password=password, balance=1000)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect('/account')
    return render_template('newuser.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    clear()
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form["username"]).first()
        if user is not None:
            if user.password == request.form["password"]:
                login_user(user)
                return redirect('/account')
        else:
            return render_template('login2.html', user=user)
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    clear()
    logout_user()
    return redirect('/home')


@app.route('/account')
@login_required
def account():
    clear()
    key = current_user
    return render_template('account.html', key=key)


@app.route('/lobby', methods=['GET', 'POST'])
@login_required
def lobby():
    clear()
    global pair
    pair = 0
    available_game = Game.query.filter(Game.occupancy < 8).first()
    if available_game is None:
        available_game = Game(game_id=0, occupancy=0)
        db.session.add(available_game)
        db.session.commit()
    g_id = available_game.game_id
    return render_template('lobby.html', available_game=available_game, g_id=g_id)


@app.route('/joingame', methods=['GET', 'POST'])
@login_required
def joingame():
    available_game = Game.query.filter(Game.occupancy < 8).first()
    if available_game.occupancy == 0:
        available_game.occupancy = 2
        available_game.turn = 0
        g_id = 0
        p_id = 1
        dealer = Player(player_state=0, game_id=0, user_id=-1, player_id=0, score=0, bet=0)
        newplayer = Player(player_state=0, game_id=g_id, user_id=current_user.user_id, player_id=p_id, score=0)
        db.session.add(dealer)
        db.session.add(newplayer)
        db.session.commit()
    else:
        g_id = available_game.game_id
        available_game.turn = 0
        current_players = Player.query.filter(Player.game_id == g_id).all()
        p_id = len(current_players)
        newplayer = Player(player_state=0, game_id=g_id, user_id=current_user.user_id, player_id=p_id, score=0)
        db.session.add(newplayer)
        available_game.occupancy += 1
        db.session.commit()
    return redirect('/game')


@app.route('/game', methods=['GET', 'POST'])
@login_required
def game():
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()
    user = User.query.filter(User.user_id == key.user_id).first()

    return render_template('game.html', players=players, g_id=g_id, current_player=current_player, user=user, dealer=dealer)


@app.route('/bet/<money>', methods=['GET', 'POST'])
@login_required
def bet(money):
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()

    current_player.bet = money
    current_player.player_state = 1
    if current_player.player_id == last_player.player_id:
        dealer = Player.query.filter_by(player_id=0).first()
        dealer.player_state = 1
    db.session.commit()
    return money


@app.route('/returnCards/<player>', methods=['GET', 'POST'])
def returnCards(player):
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()

    player = int(player)
    cards = Deck.query.filter_by(player_id=player).all()
    db.session.commit()
    if players[player].score > 21:
        makeAce1(players[player])
        players = Player.query.filter_by(game_id=g_id).all()
    if players[player].score < 21:
        total = players[player].score
        hand = "cards: "
        for i in range(0, len(cards)):
            hand += cards[i].face + " "
        hand += "total: " + str(total)
    else:
        hand = "BUST"
        players[player].score = 0
        for i in range(0, len(players)):
            last_player = players[i]
        if player != 0:
            players[player].player_state += 1
        if players[player].player_id == last_player.player_id:
            players[0].player_state += 1
        db.session.commit()
    bet = "Bet: " + str(current_player.bet)
    str(bet)
    return jsonify(id=player, hand=hand, bet=bet)


@app.route('/getCard', methods=['GET', 'POST'])
@login_required
def getCard():
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()
    cards = Deck.query.filter_by(player_id=None).all()

    card = random.choice(cards)
    card.player_id = current_player.player_id
    current_player.score += card.value
    db.session.commit()
    if current_player.score > 21:
        stay()
    return ""


@app.route('/getTwoCards', methods=['GET', 'POST'])
@login_required
def getTwoCards():
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()

    blackjack = 'no'
    for i in range(0, len(players)*2):
        cards = Deck.query.filter_by(player_id=None).all()
        card = random.choice(cards)
        card.player_id = current_game.turn
        if current_game.turn == last_player.player_id:
            current_game.turn = 0
        else:
            current_game.turn += 1
        db.session.commit()
    for i in range(0, len(players)):
        cards = Deck.query.filter_by(player_id=i).all()
        card1 = cards[0]
        card2 = cards[1]
        players[i].score = card1.value + card2.value
    for i in range(0, len(players)):
        players[i].player_state += 1
    current_game.turn = 1
    db.session.commit()
    if current_player.score == 21:
        blackjack = 'yes'
    elif dealer.score == 21:
        blackjack = 'yes'
    return blackjack


@app.route('/split', methods=['GET', 'POST'])
@login_required
def split():
    global pair
    pair = 2

    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()
    cards = Deck.query.filter_by(player_id=current_player.player_id).all()

    newPID = len(players)
    db.session.commit()

    cards[1].player_id = newPID
    deck = Deck.query.filter_by(player_id=None).all()
    card1 = random.choice(deck)
    card2 = random.choice(deck)
    card1.player_id = current_player.player_id
    card2.player_id = newPID
    current_player.score -= cards[1].value
    current_player.score += card1.value
    newplayer = Player(player_state=current_player.player_state, game_id=g_id, user_id=current_user.user_id,
                       player_id=newPID, score=card2.value+cards[1].value, bet=current_player.bet)
    db.session.add(newplayer)
    db.session.commit()
    return ""


@app.route('/checkState', methods=['GET', 'POST'])
@login_required
def checkState():
    global pair

    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()
    turn = available_game.turn
    hand = Deck.query.filter_by(player_id=1).all()
    if pair != 2:
        if len(hand) == 2:
            if hand[0].value == hand[1].value:
                pair = 1
            else:
                pair = 0
    split = len(players)
    pID = current_player.player_id
    pState = current_player.player_state
    pScore = current_player.score
    dState = dealer.player_state
    dScore = dealer.score
    pBalance = key.balance
    pBet = current_player.bet
    return jsonify(pID=pID, pState=pState, pScore=pScore, dScore=dScore, dState=dState, turn=turn, split=split,
                   pair=pair, pBet=pBet, pBalance=pBalance)


@app.route('/stay', methods=['GET', 'POST'])
@login_required
def stay():
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()

    current_player.player_state = 3
    available_game.turn += 1
    if current_player.player_id == last_player.player_id:
        dealer.player_state = 3
    db.session.commit()
    return ""


@app.route('/dealerLogic', methods=['GET', 'POST'])
def dealerLogic():
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()

    while dealer.score < 17:
        cards = Deck.query.filter_by(player_id=None).all()
        card = random.choice(cards)
        card.player_id = dealer.player_id
        dealer.score += card.value
        db.session.commit()
    dealer.player_state = 4
    db.session.commit()
    return ""


@app.route('/checkWin', methods=['GET', 'POST'])
def checkWin():
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()

    if players[0].score > 21:
        players[0].score = 0
    if pair == 2:
        winnings = 0
        for i in range(1, 3):
            if players[i].score < players[0].score:
                winnings -= players[1].bet
                key.balance += winnings
            elif players[i].score > players[0].score:
                winnings += players[1].bet
                key.balance += winnings
            if i == 2:
                if winnings < 0:
                    message = 'You lost ' + str(winnings)
                elif winnings == 0:
                    message = 'You broke even'
                else:
                    message = 'You won ' + str(winnings)
    else:
        if players[1].score < players[0].score:
            winnings = players[1].bet
            key.balance -= winnings
            message = 'You lost ' + str(winnings)
        elif players[1].score > players[0].score:
            winnings = players[1].bet
            key.balance += winnings
            message = 'You won ' + str(winnings)
    db.session.commit()
    if current_player.player_id == last_player.player_id:
        clear()
    flash(message)
    return redirect('/account')


@app.route('/doubleDown', methods=['GET', 'POST'])
@login_required
def doubleDown():
    key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player = grab()

    newMoney = current_player.bet * 2
    current_player.bet *= 2
    db.session.commit()
    return str(newMoney)


@app.route('/testDD', methods=['GET', 'POST'])
@login_required
def testDD():
    current_game = Game.query.filter(Game.occupancy < 8).first()
    key = current_user
    player = Player.query.filter_by(user_id=key.user_id).first()
    player.bet = 50
    card1 = Deck.query.filter_by(value=4).first()
    card2 = Deck.query.filter_by(value=5).first()
    card1.player_id = player.player_id
    card2.player_id = player.player_id
    player.score = card1.value + card2.value
    db.session.commit()
    deck = Deck.query.filter_by(player_id=None).all()
    dealer1 = random.choice(deck)
    dealer1.player_id = 0
    db.session.commit()
    deck = Deck.query.filter_by(player_id=None).all()
    dealer2 = random.choice(deck)
    dealer2.player_id = 0
    player.player_state = 2
    current_game.turn = 1
    dealer = Player.query.filter_by(player_id=0).first()
    dealer.score = dealer1.value + dealer2.value
    db.session.commit()
    return ""


@app.route('/testSplit', methods=['GET', 'POST'])
@login_required
def testSplit():
    current_game = Game.query.filter(Game.occupancy < 8).first()
    key = current_user
    player = Player.query.filter_by(user_id=key.user_id).first()
    player.bet = 50
    card1 = Deck.query.filter_by(value=4).first()
    card1.player_id = player.player_id
    db.session.commit()
    card2 = Deck.query.filter_by(card_id=17).first()
    card2.player_id = player.player_id
    player.score = card1.value + card2.value
    db.session.commit()
    deck = Deck.query.filter_by(player_id=None).all()
    dealer1 = random.choice(deck)
    dealer1.player_id = 0
    db.session.commit()
    deck = Deck.query.filter_by(player_id=None).all()
    dealer2 = random.choice(deck)
    dealer2.player_id = 0
    player.player_state = 2
    current_game.turn = 1
    dealer = Player.query.filter_by(player_id=0).first()
    dealer.score = dealer1.value + dealer2.value
    db.session.commit()
    return ""


def makeAce1(a):
    deck = Deck.query.filter_by(player_id=a.player_id).all()
    for i in deck:
        if i.value == 11:
            i.value = 1
            a.score -= 10
            db.session.commit()
            return None
    return None


def grab():
    deck = Deck.query.all()
    available_game = Game.query.filter(Game.occupancy < 8).first()
    g_id = available_game.game_id
    key = current_user
    current_player = Player.query.filter_by(user_id=key.user_id).first()
    cp = Player.query.filter(Player.player_id != 0).all()
    for p in cp:
        if p.player_state < current_player.player_state:
            current_player = p
    players = Player.query.filter(Player.game_id == current_player.game_id).all()
    users = User.query.filter(User.user_id == Player.user_id).all()
    dealer = Player.query.filter_by(player_id=0).first()
    current_game = Game.query.filter(Game.occupancy < 8).first()
    for i in range(0, len(players)):
        last_player = players[i]
    tuples = (key, users, current_player, players, available_game, g_id, dealer, deck, current_game, last_player)
    return tuples


def clear():
    if Game.query.all() is not None:
        games = Game.query.all()
        players = Player.query.all()
        for g in games:
            db.session.delete(g)
        for p in players:
            db.session.delete(p)
        deck = Deck.query.all()
        for i in deck:
            if i.value == 1:
                i.value = 11
            i.player_id = None
        db.session.commit()


@app.errorhandler(404)
def err404(err):
    return render_template('404.html', err=err)


@app.errorhandler(401)
def err404(err):
    return render_template('401.html', err=err)


@app.errorhandler(400)
def err404(err):
    return render_template('400.html', err=err)


@app.errorhandler(403)
def err404(err):
    return render_template('403.html', err=err)


@app.errorhandler(500)
def err404(err):
    return render_template('500.html', err=err)


@app.errorhandler(502)
def err404(err):
    return render_template('502.html', err=err)


@app.errorhandler(503)
def err404(err):
    return render_template('503.html', err=err)


@app.errorhandler(504)
def err404(err):
    return render_template('504.html', err=err)

if __name__ == '__main__':

    app.run(debug=True)
