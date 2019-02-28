from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from flask_sqlalchemy import SQLAlchemy

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

    players = db.relationship('Player', backref='game')
    decks = db.relationship('Deck', backref='game')


class Player(db.Model):
    player_id = db.Column(db.Integer, primary_key=True)
    player_state = db.Column(db.Integer)

    game_id = db.Column(db.Integer, db.ForeignKey('game.game_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    decks = db.relationship('Deck', backref='player')


login_manager = LoginManager(app)
login_manager.init_app(app)


@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
def home():
    return render_template('home.html')


@app.route('/newuser', methods=['GET', 'POST'])
def newuser():
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect('/account')
    return render_template('newuser.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
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
    logout_user()
    return redirect('/home')


@app.route('/account')
@login_required
def account():
    key = current_user
    return render_template('account.html', key=key)


@app.route('/game', methods=['GET', 'POST'])
@login_required
def game():
    players = Player.query.filter_by(game_id=Player.game_id).all()
    print(players)


if __name__ == '__main__':

    app.run(debug=True)
