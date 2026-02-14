import curses
import random 
import os 
import re
import time
import math

CHAR_WIDTH = 2
LINE_HEIGHT = 1
VISIBLE_LINES = 3
FPS = 60
FRAME_TIME = 1 / FPS

                
def get_words(text, no_words= 100):
    words = random.choices(text, k= no_words)
    word_string = ' '.join(words)
    
    return word_string


def clean_words(raw_words):
    cleaned = []
    for word in raw_words:
        only_letters = re.sub(r"[^A-Za-z]", "", word)
        if only_letters:
            cleaned.append(only_letters)
    return cleaned


def build_layout(text, width, max_lines):
    positions = [None] * len(text)
    words = text.split(" ")
    text_idx = 0
    line = 0
    col = 0

    for i, word in enumerate(words):
        if line >= max_lines:
            break

        # Move whole word to next line when possible.
        if i > 0 and len(word) <= width and col != 0 and (col + 1 + len(word) > width):
            line += 1
            col = 0

        if i > 0 and line < max_lines and text_idx < len(text):
            if col >= width:
                line += 1
                col = 0
            if line < max_lines:
                positions[text_idx] = (line, col)
                col += 1
            text_idx += 1

        for _ in word:
            if line >= max_lines or text_idx >= len(text):
                break
            if col >= width:
                line += 1
                col = 0
            if line >= max_lines:
                break
            positions[text_idx] = (line, col)
            col += 1
            text_idx += 1

    return positions


def render_text(
    stdscr,
    text,
    typed,
    positions,
    window_start,
    y=1,
    x=0,
    char_width=CHAR_WIDTH,
    line_height=LINE_HEIGHT,
):
    max_y, max_x = stdscr.getmaxyx()
    max_chars = max(0, (max_x - x - 1) // char_width)

    if max_chars == 0 or y >= max_y:
        return

    for idx, ch in enumerate(text):
        pos = positions[idx]
        if pos is None:
            break

        row, col = pos
        if row < window_start or row >= (window_start + VISIBLE_LINES):
            continue

        color = 1
        if idx < len(typed):
            color = 2 if typed[idx] == ch else 3

        draw_row = y + ((row - window_start) * line_height)
        draw_col = x + (col * char_width)
        if draw_row >= max_y or draw_col >= max_x:
            continue

        # Clean 2-column glyph: readable and larger without distorted doubled letters.
        char_block = (" " * char_width) if ch == " " else (ch + (" " * (char_width - 1)))
        style = curses.color_pair(color) | curses.A_BOLD
        stdscr.addnstr(draw_row, draw_col, char_block, max_x - draw_col, style)


def render_timer(stdscr, remaining_seconds):
    max_y, max_x = stdscr.getmaxyx()
    if max_y <= 0:
        return

    timer_label = f"TIME {remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}"
    timer_x = max(0, (max_x - len(timer_label)) // 2)
    stdscr.addnstr(0, timer_x, timer_label, max_x - timer_x, curses.color_pair(4) | curses.A_BOLD)


def calculate_stats(typed, target, elapsed_seconds):
    total_typed = len(typed)
    correct_chars = sum(1 for i, ch in enumerate(typed) if i < len(target) and ch == target[i])
    accuracy = (correct_chars / total_typed * 100) if total_typed > 0 else 0.0

    minutes = elapsed_seconds / 60 if elapsed_seconds > 0 else 0
    wpm = (correct_chars / 5) / minutes if minutes > 0 else 0.0

    typed_words = typed.split()
    target_words = target.split()
    wrong_words = 0
    for i, typed_word in enumerate(typed_words):
        if i >= len(target_words) or typed_word != target_words[i]:
            wrong_words += 1

    return wpm, accuracy, wrong_words


def render_results(stdscr, wpm, accuracy, wrong_words):
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    lines = [
        "Time Up",
        f"WPM            : {wpm:.2f}",
        f"Accuracy       : {accuracy:.2f}%",
        f"Wrong Words    : {wrong_words}",
        "Press ENTER or any key to exit",
    ]

    start_row = max(0, (max_y - len(lines)) // 2)
    panel_width = min(max_x - 2, max(len(line) for line in lines) + 8)
    panel_col = max(0, (max_x - panel_width) // 2)
    if max_y >= 6 and panel_width > 4:
        stdscr.addstr(max(0, start_row - 2), panel_col, "+" + "-" * (panel_width - 2) + "+", curses.color_pair(4))
        stdscr.addstr(min(max_y - 1, start_row + len(lines) + 1), panel_col, "+" + "-" * (panel_width - 2) + "+", curses.color_pair(4))

    for idx, line in enumerate(lines):
        col = max(0, (max_x - len(line)) // 2)
        color = 4 if idx == 0 else 1
        stdscr.addstr(start_row + idx, col, line, curses.color_pair(color) | curses.A_BOLD)

    stdscr.refresh()
    # Ignore all input for 5 seconds so results remain visible.
    stdscr.nodelay(True)
    ignore_until = time.monotonic() + 5
    while time.monotonic() < ignore_until:
        stdscr.getch()
        curses.napms(50)
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    stdscr.getch()


def main(stdscr):
    curses.curs_set(1)
    stdscr.clear()
    curses.start_color()
    stdscr.nodelay(True)
    
    # keeping the what is being typed on the terminal
    buffer = ""

    # default colors 
    curses.assume_default_colors(-1, -1);

    # new color pairs 
    curses.init_pair(0, curses.COLOR_BLACK, -1)
    curses.init_pair(1, curses.COLOR_WHITE, -1) # white text, default bg
    
    curses.init_pair(2, curses.COLOR_GREEN, -1) # Green text on Correct word
    
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    text = ["typing", "practice", "words"]
    if os.path.exists('words.txt'):
        with open('words.txt', 'r') as file:
            text = clean_words(file.read().split())

    if not text:
        text = ["typing", "practice", "words"]

    target_text = get_words(text)
    game_duration = 10
    started_at = None
    time_up = False
    window_start = 0
    positions = []
    last_layout_size = (-1, -1)
    should_exit = False

    while True:
        frame_start = time.monotonic()

        if started_at is None:
            remaining = game_duration
            remaining_display = game_duration
        else:
            elapsed = time.monotonic() - started_at
            remaining = max(0, game_duration - elapsed)
            remaining_display = int(math.ceil(remaining))

        if started_at is not None and remaining <= 0:
            time_up = True
            break

        # Process all queued keys each frame to avoid input lag.
        while True:
            ch = stdscr.getch()
            if ch == -1:
                break

            # enter key
            if ch in (10, 13):
                should_exit = True
                break

            # handle BACKSPACE
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                buffer = buffer[:-1]
                continue

            # printable chars only
            if 32 <= ch <= 126 and len(buffer) < len(target_text):
                if started_at is None:
                    started_at = time.monotonic()
                buffer += chr(ch)

        if should_exit:
            break

        max_y, max_x = stdscr.getmaxyx()
        if (max_y, max_x) != last_layout_size:
            max_chars = max(1, (max_x - 1) // CHAR_WIDTH)
            positions = build_layout(target_text, max_chars, len(target_text) + 1)
            last_layout_size = (max_y, max_x)

        cursor_idx = min(len(buffer), len(target_text) - 1) if target_text else 0
        cursor_pos = positions[cursor_idx] if target_text and positions else None

        if cursor_pos is not None:
            current_line = cursor_pos[0]
            if current_line >= window_start + VISIBLE_LINES - 1:
                window_start = current_line
            elif current_line < window_start:
                window_start = current_line

        stdscr.erase()
        render_timer(stdscr, remaining_display)
        render_text(stdscr, target_text, buffer, positions, window_start, y=2, x=0)

        if target_text:
            if len(buffer) >= len(target_text):
                last = next((p for p in reversed(positions) if p is not None), (0, 0))
                row, col = last
                cursor_row = min(curses.LINES - 1, 2 + ((row - window_start) * LINE_HEIGHT))
                cursor_col = min(curses.COLS - 1, (col + 1) * CHAR_WIDTH)
                stdscr.move(cursor_row, cursor_col)
            elif positions[len(buffer)] is not None:
                row, col = positions[len(buffer)]
                cursor_row = min(curses.LINES - 1, 2 + ((row - window_start) * LINE_HEIGHT))
                cursor_col = min(curses.COLS - 1, col * CHAR_WIDTH)
                stdscr.move(cursor_row, cursor_col)

        stdscr.refresh()

        frame_elapsed = time.monotonic() - frame_start
        sleep_ms = int(max(0, (FRAME_TIME - frame_elapsed) * 1000))
        if sleep_ms > 0:
            curses.napms(sleep_ms)

    if time_up:
        elapsed_total = min(game_duration, time.monotonic() - started_at)
        wpm, accuracy, wrong_words = calculate_stats(buffer, target_text, elapsed_total)
        render_results(stdscr, wpm, accuracy, wrong_words)
    

if __name__ == "__main__":
    curses.wrapper(main)
