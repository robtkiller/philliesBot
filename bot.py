from urllib.request import urlopen
from datetime import date, timedelta
import json
from telegram.ext import Updater
import logging
import inflect


# Enable logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)


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
        game_date += timedelta.days(1)
    if game['home_team_name'] == 'Phillies':
        return str(game['home_win']) + ' - ' + str(game['home_loss'])
    else:
        return str(game['away_win']) + ' - ' + str(game['away_loss']) 


def get_status(): 
    game_date = date.today()
    game = get_game('Phillies', game_date)
    if game:
        try: 
            return {'inning': game['status']['inning'],
                    'inning_state': game['status']['inning_state'],
                    'outs' : game['status']['o'],
                    'batter': game['batter']['name_display_roster'],
                    'avg' : game['batter']['avg'],
                    'runners' : game['runners_on_base']['status']
                    }
        except KeyError:
            return get_score()


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.

def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi! I am PhilliesBot. Beep boop bleep.')


def help(bot, update):
    bot.sendMessage(update.message.chat_id,
                    text= """I am PhilliesBot. You can ask me to tell you the score of today\'s game by sending
                     `/score`. More commands will be coming soon! Beep boop bleep.""")


# def echo(bot, update):
#    bot.sendMessage(update.message.chat_id, text=update.message.text)

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
    status = get_status()
    p = inflect.engine()
    bot.sendMessage(update.message.chat_id, text=
        status['inning_state'] + ' of the ' + p.ordinal(status['inning']) + ' with ' + status['outs'] + ' ' + p.plural('out', status['outs']) + ' - ' + status['batter'] + '(' + status['avg'] + ' AVG) with ' + status['runners'] + ' ' + p.plural('runner', status['runners']) + ' on base.'
    )


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
