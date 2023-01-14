import glob
import os
import chess
import chess.pgn
import chess.svg
import chess.engine

import cairosvg
from discord_webhook import DiscordWebhook, DiscordEmbed
from io import BytesIO

def get_last_modified(path):
    list_of_files = sorted(glob.glob(path + '/*.pgn'))
    return 'games/current.pgn' if 'games/current.pgn' in list_of_files else list_of_files[-1]

def load_board(file):
    with open(file) as pgn_file:
        game = chess.pgn.read_game(pgn_file)
        board = game.board()

    for move in game.mainline_moves():
        board.push(move)

    return board

def generate_png(svg):
    out = BytesIO()
    cairosvg.svg2png(bytestring=svg, write_to=out)
    out.seek(0)

    return out

def move_to_san(board, move):
    if move is None:
        return "None"

    return str(board.fullmove_number) + ('... ' if board.turn == chess.BLACK else '. ') + board.san(move)

def get_evaluation(board, time_limit):
    stockfish_path = os.environ['STOCKFISH_PATH']
    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    info = engine.analyse(board, chess.engine.Limit(time=time_limit))
    engine.quit()

    score = info['score'].white()
    next_move = move_to_san(board, info['pv'][0] if 'pv' in info else None)
    mate = score.mate()
    score = score.score()

    if mate is not None:
        return '#{:+d}'.format(mate), next_move
    else:
        return '{:+.2f}'.format(score / 100), next_move

def send_webhook(png, last_move, pts, move, board):
    webhook_url = os.environ['WEBHOOK_URL']
    webhook = DiscordWebhook(url=webhook_url, username='README Chess', avatar_url='https://github.com/ChessCom.png')
    webhook.add_file(file=png.read(), filename='image.png')

    embed = DiscordEmbed(title=last_move, description='New move played', color=(0xefefef if board.turn == chess.WHITE else 0x303030))
    embed.set_footer(text='Generated by RusMermaid/chess_readme')
    embed.set_timestamp()
    embed.add_embed_field(name='Evaluation', value=pts)
    embed.add_embed_field(name='Next best move', value=move)
    embed.set_image(url='attachment://image.png')

    webhook.add_embed(embed)
    webhook.execute()

def style_lightblue():
    colors = dict()
    colors['square light'] = '#D6DCE0'
    colors['square dark'] = '#7A909D'
    colors['square light lastmove'] = '#B7D288'
    colors['square dark lastmove'] = '#82A465'
    return colors

board = load_board(get_last_modified('games'))
check_pos = board.king(board.turn) if board.is_check() else None
lastmove = board.peek() if len(board.move_stack) > 0 else None
svg = chess.svg.board(board=board, lastmove=lastmove, check=check_pos, size=900, colors=style_lightblue())
png = generate_png(svg)

pts, move = get_evaluation(board, 10.0)

if len(board.move_stack) == 0:
    send_webhook(png, 'Start new game', pts, move, board)
else:
    last_move = board.peek();
    board.pop()

    last_move = move_to_san(board, last_move)
    send_webhook(png, last_move, pts, move, board)