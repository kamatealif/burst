import curses
import random 
import os 
import re
import time
import math

                
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


def render_text(stdscr, text, typed, y=1, x=0):
    max_y, max_x = stdscr.getmaxyx()
    max_chars = max(0, max_x - x - 1)

    if max_chars == 0 or y >= max_y:
        return []

    max_lines = max_y - y
    positions = build_layout(text, max_chars, max_lines)

    for idx, ch in enumerate(text):
        pos = positions[idx]
        if pos is None:
            break

        row, col = pos
        color = 1
        if idx < len(typed):
            color = 2 if typed[idx] == ch else 3

        stdscr.addch(y + row, x + col, ch, curses.color_pair(color))

    return positions


def render_timer(stdscr, remaining_seconds):
    max_y, max_x = stdscr.getmaxyx()
    if max_y <= 0:
        return

    timer_label = f"{remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}"
    timer_x = max(0, (max_x - len(timer_label)) // 2)
    stdscr.addstr(0, timer_x, timer_label, curses.color_pair(1))


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
        "Time Up!",
        f"WPM: {wpm:.2f}",
        f"Accuracy: {accuracy:.2f}%",
        f"Wrongly Typed Words: {wrong_words}",
        "Press any key to exit.",
    ]

    start_row = max(0, (max_y - len(lines)) // 2)
    for idx, line in enumerate(lines):
        col = max(0, (max_x - len(line)) // 2)
        stdscr.addstr(start_row + idx, col, line, curses.color_pair(1))

    stdscr.refresh()
    stdscr.timeout(-1)
    stdscr.getch()


def main(stdscr):
    curses.curs_set(1)
    stdscr.clear()
    curses.start_color()
    stdscr.timeout(16)
    
    # keeping the what is being typed on the terminal
    buffer = ""

    # default colors 
    curses.assume_default_colors(-1, -1);

    # new color pairs 
    curses.init_pair(0, curses.COLOR_BLACK, -1)
    curses.init_pair(1, curses.COLOR_WHITE, -1) # white text, default bg
    
    curses.init_pair(2, curses.COLOR_GREEN, -1) # Green text on Correct word
    
    curses.init_pair(3, curses.COLOR_RED, -1)
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

    while True:
        if started_at is None:
            remaining = game_duration
            remaining_display = game_duration
        else:
            elapsed = time.monotonic() - started_at
            remaining = max(0, game_duration - elapsed)
            remaining_display = int(math.ceil(remaining))

        ch = stdscr.getch()

        # enter key 
        if ch in (10, 13):
            break 

        # handle BACKSPACE
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            buffer = buffer[:-1]

        # printable chars only 
        elif 32 <= ch <= 126:
            if len(buffer) < len(target_text):
                if started_at is None:
                    started_at = time.monotonic()
                buffer += chr(ch)

        stdscr.clear()
        render_timer(stdscr, remaining_display)
        positions = render_text(stdscr, target_text, buffer, y=2, x=0)

        if len(buffer) >= len(target_text):
            if positions:
                last = next((p for p in reversed(positions) if p is not None), (0, 0))
                cursor_row = min(curses.LINES - 1, 2 + last[0])
                cursor_col = min(curses.COLS - 1, last[1] + 1)
                stdscr.move(cursor_row, cursor_col)
        elif positions and positions[len(buffer)] is not None:
            row, col = positions[len(buffer)]
            stdscr.move(2 + row, col)

        stdscr.refresh()

        if started_at is not None and remaining <= 0:
            time_up = True
            break

    if time_up:
        elapsed_total = min(game_duration, time.monotonic() - started_at)
        wpm, accuracy, wrong_words = calculate_stats(buffer, target_text, elapsed_total)
        render_results(stdscr, wpm, accuracy, wrong_words)
    

if __name__ == "__main__":
    curses.wrapper(main)
