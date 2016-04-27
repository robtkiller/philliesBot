import urllib
from urllib.request import urlopen
from datetime import date, timedelta
import json
from telegram.ext import Updater
import logging
import inflect
import sqlite3
import xmltodict


# Enable logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)

# Functions for getting data from MLB
def get_game(team,date):
    year = str(date.year)
    month = str(date.strftime('%m'))
    day = str(date.strftime('%d'))
    scoreboardURL = 'http://gd2.mlb.com/components/game/mlb/year_{}/month_{}/day_{}/master_scoreboard.json'.format(year, month, day)
    response = urlopen(scoreboardURL).read().decode('utf-8')
    scoreboardJSON = json.loads(response)
    games = scoreboardJSON['data']['games']['game']
    for game in games:
        if game['home_team_name'] == team or game['away_team_name'] == team:
            return game
    return None


def get_schedule():
    day = date.today()
    sched = []
    for d in range(3):
        day_name = day.strftime('%a %-m/%-d')
        try:
            game = get_game('Phillies', day)
            if game['home_team_name'] == 'Phillies':
                against = game['away_team_name']
            else:
                against = game['home_team_name']
            sched.append(day_name + ': ' + against + ' - ' + game['time'])
        except urllib.error.HTTPError:
            sched.append(day.strftime('%a') + ': Off')
        day += timedelta(days=1)
    return '\n'.join(sched)


def get_pitchers():
    today = date.today()
    game = get_game('Phillies',today)
    
    def pitcher_str(pitcher, opp):
        return str(pitcher['last']) + '(' + str(pitcher['wins']) + '-' + str(pitcher['losses']) + ', ERA:' + str(pitcher['era']) + ') vs. '+ str(opp['last']) + '(' + str(opp['wins']) + '-' + str(opp['losses']) + ', ERA:' + str(opp['era']) + ')'
        
    if game: 
        try:
            pitcher = game['pitcher']
            opp = game['opposing_pitcher']
            return pitcher_str(pitcher,opp)
        except: 
            try: 
                pitcher = game['home_probable_pitcher']
                opp = game['away_probable_pitcher']
                return 'Probables: ' + pitcher_str(pitcher,opp) 
            except:
                return 'Phillies aren\'t playing today' 


def get_score():
    today = date.today()    
    game = get_game('Phillies', today)
    if game: 
        try:
            return str(game['alerts']['text'])
        except KeyError:
            return 'Looks like the Phillies haven\'t played yet. The game starts at {}ET'.format(str(game['time']))
    return 'Phillies are off today'


def get_record():
    game_date = date.today() 
    game = get_game('Phillies',game_date) 
    while not game: 
        game_date += timedelta(days=1)
    if game['home_team_name'] == 'Phillies':
        return str(game['home_win']) + ' - ' + str(game['home_loss'])
    else:
        return str(game['away_win']) + ' - ' + str(game['away_loss']) 


def get_status(): 
    game_date = date.today()
    game = get_game('Phillies', game_date)
    if game:
        try: 
            status = {'inning': game['status']['inning'],
                      'inning_state': game['status']['inning_state'],
                      'outs' : game['status']['o'],
                      'batter': game['batter']['name_display_roster'],
                      'avg' : game['batter']['avg'],
                      'runners': game['runners_on_base']['status']
                    }
            runners = {'0': 'bases empty',
                       '1': 'a runner on 1st',
                       '2': 'a runner on 2nd',
                       '3': 'a runner on 3rd',
                       '4': 'runners on 1st and 2nd',
                       '5': 'runners on 1st and 3rd',
                       '6': 'runners on 2nd and 3rd',
                       '7': 'the basses loaded'}
            p = inflect.engine()
            return status['inning_state'] + ' of the ' + p.ordinal(status['inning']) + ' with ' + status['outs'] + ' ' + p.plural('out', status['outs']) + ' - ' + status['batter'] + '(' + status['avg'] + ' AVG) with ' + runners[status['runners']]+'.'

        except KeyError:
            return get_score()


def get_stats(player_name):
    sql_name = ('%' + player_name.replace(' ', '%') + '%',)
    db = sqlite3.connect('players.db')
    cur = db.cursor()
    cur.execute('SELECT mlb_id, mlb_name, mlb_pos, mlb_team FROM player WHERE mlb_name LIKE ?', sql_name)
    mlb_ids = cur.fetchall()
    if len(mlb_ids) == 0:
        return "Hmm...I don't know him. Try another name."
    elif len(mlb_ids) == 1:
        dt = date.today()
        for x in range(20):
            dt -= timedelta(days=1)
            year = str(dt.year)
            month = str(dt.strftime('%m'))
            day = str(dt.strftime('%d'))
            player_id = str(mlb_ids[0][0])
            try:
                base_url = 'http://gd2.mlb.com/components/game/mlb/year_{}/month_{}/day_{}/batters/{}_1.xml'.format(year, month, day, player_id)
                response = urlopen(base_url).read().decode('utf-8')
                data = xmltodict.parse(response)
                name_info = ' - '.join(mlb_ids[0][1:4])
                return  '*'+name_info+'*' + '\n' + 'AVG: ' + data['batting']['@avg'] + '\n' + 'Hits: ' + data['batting']['@s_h'] + '\n' + 'HRs: ' + data['batting']['@s_hr'] + '\n' + 'RBIs: ' + data['batting']['@s_rbi'] + '\n' + 'SO: ' + data['batting']['@s_so'] + '\n' + 'BB: ' + data['batting']['@s_bb']
            except urllib.error.HTTPError:
                pass

    else:
        names = '\n'.join([' - '.join(player[1:4]) for player in mlb_ids])
        return 'More than one player found. \n' + names


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.

def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi! I am PhilliesBot. Beep boop bleep.')


def help(bot, update):
    bot.sendMessage(update.message.chat_id,
                    parse_mode= 'Markdown',
                    text= """I am PhilliesBot. You can ask me to tell you the score of today\'s game by sending `/score`. Other commands: \n `/status` Details of whats going on in the game \n `/schedule` See the next three games of their schedule \n`/pitchers` Find out who's pitching in today's game \n `/record` Gets the current Phillies' record \n `/stats` Get any MLB player's hitting stats""")


def score(bot, update):
    current_score = get_score()
    bot.sendMessage(update.message.chat_id, text=current_score)


def pitchers(bot, update):
    bot.sendMessage(update.message.chat_id, text=get_pitchers())


def suck(bot, update):
    bot.sendMessage(update.message.chat_id, text='The Phillies suck and are a bunch of bums')


def howard(bot, update):
    bot.sendMessage(update.message.chat_id, text='The guy we pay to strikeout 4 times a game?')


def record(bot, update):
    bot.sendMessage(update.message.chat_id, text='The Phillies\' record is:  ' + get_record())


def status(bot, update):
    bot.sendMessage(update.message.chat_id, text= get_status())


def stats(bot, update):
    bot.sendMessage(update.message.chat_id, text='Which player would you like stats for?')


def schedule(bot, update):
    bot.sendMessage(update.message.chat_id, text= get_schedule())


def reply_handler(bot, update):
    reply_to = update.message.reply_to_message
    if reply_to:
        reply_to_user = reply_to.from_user.username
        reply_to_text = reply_to.text
        if reply_to_user == 'PhilliesBot' and reply_to_text == 'Which player would you like stats for?':
            request = update.message.text
            player_stats = get_stats(request)
            if player_stats:
                bot.sendMessage(update.message.chat_id, text=player_stats, parse_mode='Markdown')


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():

    with open('token', 'r') as f:
        token = f.readline()
    f.close()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", help)
    dp.addTelegramCommandHandler("score", score)
    dp.addTelegramCommandHandler("pitchers",pitchers)
    dp.addTelegramCommandHandler("suck",suck)
    dp.addTelegramCommandHandler("record",record)
    dp.addTelegramCommandHandler("status",status)
    dp.addTelegramCommandHandler("howard",howard)
    dp.addTelegramCommandHandler("stats", stats)
    dp.addTelegramCommandHandler('schedule', schedule)
    dp.addTelegramMessageHandler(reply_handler)

    # on noncommand i.e message - echo the message on Telegram
    #dp.addTelegramMessageHandler(echo)

    # log all errors
    dp.addErrorHandler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
