from collections import defaultdict
from urllib.parse import urlencode
from html import escape
import os
import re
import ast

import chess
import chess.pgn
import yaml

with open('data/settings.yaml', 'r') as settings_file:
    settings = yaml.load(settings_file, Loader=yaml.FullLoader)


PIECE_IMAGES = {
    "r": "img/black/rook.png",
    "n": "img/black/knight.png",
    "b": "img/black/bishop.png",
    "q": "img/black/queen.png",
    "k": "img/black/king.png",
    "p": "img/black/pawn.png",
    "R": "img/white/rook.png",
    "N": "img/white/knight.png",
    "B": "img/white/bishop.png",
    "Q": "img/white/queen.png",
    "K": "img/white/king.png",
    "P": "img/white/pawn.png",
}


def create_link(text, link):
    return f"[{text}]({link})"

def create_issue_url(source, dest):
    issue_link = settings['issues']['link'].format(
        repo=os.environ["GITHUB_REPOSITORY"],
        params=urlencode(settings['issues']['move'], safe="{}"))

    return issue_link.format(source=source, dest=dest)

def create_issue_link(source, dest_list):
    ret = [create_link(dest, create_issue_url(source, dest)) for dest in sorted(dest_list)]
    return ", ".join(ret)

def create_move_tile(source, dest, image_path, piece_name):
    link = escape(create_issue_url(source, dest), quote=True)
    description = escape(f"Move {piece_name} from {source} to {dest}", quote=True)

    return (
        '<td align="center" width="72">'
        f'<a href="{link}" title="{description}">'
        f'<img src="{image_path}" alt="" width="46"><br>'
        f'<strong>{dest}</strong>'
        '</a>'
        '</td>'
    )

def generate_top_moves():
    with open("data/top_moves.txt", 'r') as file:
        dictionary = ast.literal_eval(file.read())

    markdown = "\n"
    markdown += "| Total moves |  User  |\n"
    markdown += "| :---------: | :----- |\n"

    max_entries = settings['misc']['max_top_moves']
    for key,val in sorted(dictionary.items(), key=lambda x: x[1], reverse=True)[:max_entries]:
        markdown += "| {} | {} |\n".format(val, create_link(key, "https://github.com/" + key[1:]))

    return markdown + "\n"

def _moves():
    entries = []

    with open("data/last_moves.txt", 'r') as file:
        for line in file.readlines():
            move_text, separator, author = line.rstrip().partition(':')
            if not separator:
                continue

            match_obj = re.search(
                r'([A-H][1-8])([A-H][1-8])([QRBN])?', move_text, re.I)
            entries.append({
                'move_text': move_text,
                'author': author.strip(),
                'source': match_obj.group(1).upper() if match_obj else None,
                'dest': match_obj.group(2).upper() if match_obj else None,
                'uci': match_obj.group(0).lower() if match_obj else None,
            })

    return entries


def _pieces(game):
    if game is None:
        return []

    board = game.board()
    history = []

    for move in game.mainline_moves():
        piece = board.piece_at(move.from_square)
        if piece is None:
            raise ValueError(f"No piece found for recorded move {move.uci()}")

        colour = "White" if piece.color == chess.WHITE else "Black"
        history.append({
            'uci': move.uci().lower(),
            'image': PIECE_IMAGES[piece.symbol()],
            'label': f"{colour} {chess.piece_name(piece.piece_type).title()}",
        })
        board.push(move)

    return history


def _game():
    if not os.path.exists('games/current.pgn'):
        return None

    with open('games/current.pgn') as pgn_file:
        return chess.pgn.read_game(pgn_file)


def _match(entries, game):
    # last_moves.txt is newest-first while the PGN mainline is chronological.
    # Walking both in reverse order makes repeated source/destination pairs
    # unambiguous and records the piece before captures or promotions occur.
    recent_history = list(reversed(_pieces(game)))
    cursor = 0
    matched = []

    for entry in entries:
        detail = None
        if entry['uci'] is not None:
            for index in range(cursor, len(recent_history)):
                candidate = recent_history[index]
                if candidate['uci'][:4] == entry['uci'][:4]:
                    detail = candidate
                    cursor = index + 1
                    break
        matched.append(detail)

    return matched


def _replay(entries):
    # Compatibility fallback for older forks that have last_moves.txt but no
    # readable PGN. Since the file retains the complete game newest-first, it
    # can be replayed from the initial position to recover each moving piece.
    board = chess.Board()
    details = [None] * len(entries)

    for index in range(len(entries) - 1, -1, -1):
        entry = entries[index]
        if entry['uci'] is None:
            continue

        try:
            move = chess.Move.from_uci(entry['uci'])
        except ValueError:
            continue

        if move not in board.legal_moves and len(entry['uci']) == 4:
            promoted_move = chess.Move.from_uci(entry['uci'] + 'q')
            if promoted_move in board.legal_moves:
                move = promoted_move

        if move not in board.legal_moves:
            continue

        piece = board.piece_at(move.from_square)
        if piece is None:
            continue

        colour = "White" if piece.color == chess.WHITE else "Black"
        details[index] = {
            'uci': move.uci().lower(),
            'image': PIECE_IMAGES[piece.symbol()],
            'label': f"{colour} {chess.piece_name(piece.piece_type).title()}",
        }
        board.push(move)

    return details


def generate_last_moves(game=None):
    entries = _moves()
    if game is None:
        game = _game()

    piece_details = _match(entries, game)
    if any(detail is None for detail in piece_details):
        fallback_details = _replay(entries)
        piece_details = [
            detail or fallback
            for detail, fallback in zip(piece_details, fallback_details)
        ]

    max_entries = settings['misc']['max_last_moves']
    selected = list(zip(entries, piece_details))[:max_entries]

    def cells(entry, detail):
        if detail is not None:
            turn = (
                f'<img src="{detail["image"]}" alt="{detail["label"]}" width="40"><br>'
                f'<strong>{detail["label"]}</strong>'
            )
        else:
            turn = "<strong>New Game</strong>" if entry['uci'] is None else "<strong>Piece</strong>"

        if entry['source'] is not None:
            move = f'`{entry["source"]}` to `{entry["dest"]}`'
        else:
            move = f'`{entry["move_text"]}`'

        author = entry['author']
        author_link = create_link(author, "https://github.com/" + author.lstrip('@'))
        return turn, move, author_link

    markdown = "\n"
    markdown += "| Turn | Move | Author | Turn | Move | Author |\n"
    markdown += "| :--: | :--: | :--: | :--: | :--: | :--: |\n"

    left_size = (len(selected) + 1) // 2
    left = selected[:left_size]
    right = selected[left_size:]

    for index, (entry, detail) in enumerate(left):
        row = list(cells(entry, detail))
        if index < len(right):
            row.extend(cells(*right[index]))
        else:
            row.extend(("", "", ""))
        markdown += "| " + " | ".join(row) + " |\n"

    return markdown + "\n"

def generate_moves_list(board):
    # Group legal destinations by their source square. Promotion moves may
    # share a destination, so a set keeps the same one-link-per-square
    # behaviour as the original move list.
    moves_dict = defaultdict(set)

    for move in board.legal_moves:
        source = chess.SQUARE_NAMES[move.from_square].upper()
        dest   = chess.SQUARE_NAMES[move.to_square].upper()

        moves_dict[source].add(dest)

    markdown = ""

    if board.is_game_over():
        issue_link = settings['issues']['link'].format(
            repo=os.environ["GITHUB_REPOSITORY"],
            params=urlencode(settings['issues']['new_game']))

        return "**GAME IS OVER!** " + create_link("Click here", issue_link) + " to start a new game :D\n"

    if board.is_check():
        markdown += "**CHECK!** Choose your move wisely!\n"

    markdown += '<table>\n'
    markdown += '  <thead>\n'
    markdown += '    <tr>\n'
    markdown += '      <th align="center">PIECE / FROM</th>\n'
    markdown += '      <th align="center">LEGAL DESTINATIONS — click to move</th>\n'
    markdown += '    </tr>\n'
    markdown += '  </thead>\n'
    markdown += '  <tbody>\n'

    for source,destinations in sorted(moves_dict.items()):
        source_square = chess.parse_square(source.lower())
        piece = board.piece_at(source_square)

        # Every legal move necessarily has a piece on its source square.
        # Keep an explicit failure here so a malformed board cannot silently
        # generate broken image paths or move links.
        if piece is None:
            raise ValueError(f"No piece found on legal move source {source}")

        image_path = PIECE_IMAGES[piece.symbol()]
        colour = "white" if piece.color == chess.WHITE else "black"
        piece_name = f"{colour} {chess.piece_name(piece.piece_type)}"

        markdown += '    <tr>\n'
        markdown += '      <td align="center">\n'
        markdown += (
            f'        <img src="{image_path}" alt="{piece_name.title()} on {source}" '
            'width="54"><br>\n'
        )
        markdown += f'        <strong>{source}</strong>\n'
        markdown += '      </td>\n'
        markdown += '      <td>\n'
        markdown += '        <table>\n'
        markdown += '          <tbody>\n'
        markdown += '            <tr>\n'

        for dest in sorted(destinations):
            markdown += '              ' + create_move_tile(
                source, dest, image_path, piece_name) + '\n'

        markdown += '            </tr>\n'
        markdown += '          </tbody>\n'
        markdown += '        </table>\n'
        markdown += '      </td>\n'
        markdown += '    </tr>\n'

    markdown += '  </tbody>\n'
    markdown += '</table>\n'

    return markdown

def board_to_markdown(board):
    board_list = [[item for item in line.split(' ')] for line in str(board).split('\n')]
    markdown = ""

    images = dict(PIECE_IMAGES, **{".": "img/blank.png"})

    # Write header in Markdown format
    markdown += "|   | A | B | C | D | E | F | G | H |   |\n"
    markdown += "|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"

    # Write board
    for row in range(1, 9):
        markdown += "| **" + str(9 - row) + "** | "
        for elem in board_list[row - 1]:
            markdown += "<img src=\"{}\" width=50px> | ".format(images.get(elem, "???"))

        markdown += "**" + str(9 - row) + "** |\n"

    # Write footer in Markdown format
    markdown += "|   | **A** | **B** | **C** | **D** | **E** | **F** | **G** | **H** |   |\n"

    return markdown
