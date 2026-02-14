import curses
import random 
import os 
import re
import time
import math

CHAR_WIDTH = 1
LINE_HEIGHT = 1
VISIBLE_LINES = 3
FPS = 60
FRAME_TIME = 1 / FPS
CURSOR_SMOOTHING = 0.5
CURSOR_SNAP_DISTANCE = 3
CURSOR_MIN_STEP = 0.12
DEFAULT_WORD_COUNT = 100

DIFFICULTY_SETTINGS = {
    "easy": {
        "label": "Easy",
        "timer": 10,
        "min_len": 1,
        "max_len": 5,
        "punctuation_rate": 0.00,
        "punctuation_set": [".", ","],
    },
    "medium": {
        "label": "Medium",
        "timer": 60,
        "min_len": 4,
        "max_len": 8,
        "punctuation_rate": 0.08,
        "punctuation_set": [".", ",", "!", "?"],
    },
    "hard": {
        "label": "Hard",
        "timer": 60,
        "min_len": 6,
        "max_len": 14,
        "punctuation_rate": 0.18,
        "punctuation_set": [".", ",", "!", "?", ";", ":", "@", "#", "/", "<", ">", "(", ")"],
    },
}

                
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


def filter_by_length(words, min_len, max_len):
    filtered = [w for w in words if min_len <= len(w) <= max_len]
    return filtered if filtered else words


def apply_punctuation(text, rate, punctuation_set):
    if rate <= 0 or not punctuation_set:
        return text

    words = text.split()
    for i, word in enumerate(words):
        if random.random() < rate:
            words[i] = f"{word}{random.choice(punctuation_set)}"
    return " ".join(words)


def load_word_pools(words_file):
    pools = {
        "common": [],
        "easy": [],
        "medium": [],
        "hard": [],
    }

    if not os.path.exists(words_file):
        return pools

    with open(words_file, "r") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            lowered = line.lower()
            if lowered.startswith("easy:"):
                pools["easy"].extend(clean_words(line[5:].split()))
            elif lowered.startswith("medium:"):
                pools["medium"].extend(clean_words(line[7:].split()))
            elif lowered.startswith("hard:"):
                pools["hard"].extend(clean_words(line[5:].split()))
            else:
                pools["common"].extend(clean_words(line.split()))

    return pools


def get_words_for_difficulty(pools, difficulty):
    config = DIFFICULTY_SETTINGS[difficulty]
    base_words = pools["common"] + pools[difficulty]
    if not base_words:
        base_words = ["typing", "practice", "speed", "keyboard", "accuracy"]

    filtered_words = filter_by_length(base_words, config["min_len"], config["max_len"])
    generated = get_words(filtered_words, DEFAULT_WORD_COUNT)
    return apply_punctuation(generated, config["punctuation_rate"], config["punctuation_set"])


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
        style = curses.color_pair(color)
        stdscr.addnstr(draw_row, draw_col, char_block, max_x - draw_col, style)


def render_timer(stdscr, remaining_seconds):
    max_y, max_x = stdscr.getmaxyx()
    if max_y <= 0:
        return

    timer_label = f"TIME {remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}"
    timer_x = max(0, (max_x - len(timer_label)) // 2)
    stdscr.addnstr(0, timer_x, timer_label, max_x - timer_x, curses.color_pair(4) | curses.A_BOLD)


def calculate_live_metrics(typed, target, elapsed_seconds):
    typed_len = len(typed)
    if typed_len == 0:
        return 0.0, 0.0, 0

    correct_chars = sum(1 for i, ch in enumerate(typed) if i < len(target) and ch == target[i])
    errors = typed_len - correct_chars
    accuracy = (correct_chars / typed_len) * 100 if typed_len > 0 else 0.0
    minutes = elapsed_seconds / 60 if elapsed_seconds > 0 else 0
    wpm = (correct_chars / 5) / minutes if minutes > 0 else 0.0
    return wpm, accuracy, errors


def render_header(stdscr, difficulty, wpm, accuracy, errors):
    max_y, max_x = stdscr.getmaxyx()
    if max_y <= 2:
        return

    diff_label = f"MODE {DIFFICULTY_SETTINGS[difficulty]['label']}"
    stdscr.addnstr(1, 0, diff_label, max_x, curses.color_pair(4) | curses.A_BOLD)
    stats = f"WPM {wpm:5.1f}   ACC {accuracy:6.2f}%   ERR {errors}"
    stats_x = max(0, (max_x - len(stats)) // 2)
    stdscr.addnstr(2, stats_x, stats, max_x - stats_x, curses.color_pair(1) | curses.A_BOLD)


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


def render_results(stdscr, wpm, accuracy, wrong_words, title="Time Up", close_after=5):
    stdscr.nodelay(True)
    close_at = time.monotonic() + close_after

    while True:
        now = time.monotonic()
        remaining_close = max(0.0, close_at - now)
        if remaining_close <= 0:
            break

        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        lines = [
            title,
            f"WPM            : {wpm:.2f}",
            f"Accuracy       : {accuracy:.2f}%",
            f"Wrong Words    : {wrong_words}",
            f"Closing In     : {remaining_close:04.1f}s",
            "Result screen auto-closes",
        ]

        start_row = max(0, (max_y - len(lines)) // 2)
        panel_width = min(max_x - 2, max(len(line) for line in lines) + 8) if max_x > 2 else max_x
        panel_col = max(0, (max_x - panel_width) // 2)
        if max_y >= 4 and panel_width > 2:
            top_row = max(0, start_row - 2)
            bottom_row = min(max_y - 1, start_row + len(lines) + 1)
            border = "+" + "-" * (panel_width - 2) + "+"
            stdscr.addnstr(top_row, panel_col, border, max_x - panel_col, curses.color_pair(4))
            stdscr.addnstr(bottom_row, panel_col, border, max_x - panel_col, curses.color_pair(4))
            for row in range(top_row + 1, bottom_row):
                if panel_col < max_x:
                    stdscr.addch(row, panel_col, "|", curses.color_pair(4))
                right_col = panel_col + panel_width - 1
                if right_col < max_x:
                    stdscr.addch(row, right_col, "|", curses.color_pair(4))

        for idx, line in enumerate(lines):
            row = start_row + idx
            if row < 0 or row >= max_y:
                continue
            col = max(0, (max_x - len(line)) // 2)
            color = 4 if idx == 0 else 1
            stdscr.addnstr(row, col, line, max_x - col, curses.color_pair(color) | curses.A_BOLD)

        stdscr.refresh()
        stdscr.getch()  # drain any key while countdown is active
        curses.napms(50)

    stdscr.nodelay(False)


def select_difficulty(stdscr):
    stdscr.nodelay(False)
    stdscr.timeout(-1)

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        lines = [
            "Select Difficulty",
            "1) Easy   - short words, no punctuation, 60s",
            "2) Medium - normal words, light punctuation, 60s",
            "3) Hard   - long words, more punctuation, 60s",
            "Press 1 / 2 / 3",
        ]

        start_row = max(0, (max_y - len(lines)) // 2)
        for idx, line in enumerate(lines):
            col = max(0, (max_x - len(line)) // 2)
            style = curses.color_pair(4) | curses.A_BOLD if idx == 0 else curses.color_pair(1)
            stdscr.addnstr(start_row + idx, col, line, max_x - col, style)

        stdscr.refresh()
        ch = stdscr.getch()
        if ch == ord("1"):
            return "easy"
        if ch == ord("2"):
            return "medium"
        if ch == ord("3"):
            return "hard"


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
    difficulty = select_difficulty(stdscr)
    stdscr.nodelay(True)

    pools = load_word_pools("words.txt")
    target_text = get_words_for_difficulty(pools, difficulty)
    game_duration = DIFFICULTY_SETTINGS[difficulty]["timer"]
    started_at = None
    time_up = False
    window_start = 0
    positions = []
    last_layout_size = (-1, -1)
    should_exit = False
    cursor_anim_row = None
    cursor_anim_col = None

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

        elapsed_live = 0 if started_at is None else (time.monotonic() - started_at)
        live_wpm, live_accuracy, live_errors = calculate_live_metrics(buffer, target_text, elapsed_live)

        stdscr.erase()
        render_timer(stdscr, remaining_display)
        render_header(stdscr, difficulty, live_wpm, live_accuracy, live_errors)
        render_text(stdscr, target_text, buffer, positions, window_start, y=4, x=0)

        if target_text:
            cursor_target_row = 4
            cursor_target_col = 0
            if len(buffer) >= len(target_text):
                last = next((p for p in reversed(positions) if p is not None), (0, 0))
                row, col = last
                cursor_target_row = min(curses.LINES - 1, 4 + ((row - window_start) * LINE_HEIGHT))
                cursor_target_col = min(curses.COLS - 1, (col + 1) * CHAR_WIDTH)
            elif positions[len(buffer)] is not None:
                row, col = positions[len(buffer)]
                cursor_target_row = min(curses.LINES - 1, 4 + ((row - window_start) * LINE_HEIGHT))
                cursor_target_col = min(curses.COLS - 1, col * CHAR_WIDTH)

            if cursor_anim_row is None or cursor_anim_col is None:
                cursor_anim_row = float(cursor_target_row)
                cursor_anim_col = float(cursor_target_col)
            else:
                delta_row = cursor_target_row - cursor_anim_row
                delta_col = cursor_target_col - cursor_anim_col

                # Snap on big jumps (new line / scroll / resize) to avoid lagging cursor.
                if abs(delta_row) >= 1 or (abs(delta_row) + abs(delta_col)) >= CURSOR_SNAP_DISTANCE:
                    cursor_anim_row = float(cursor_target_row)
                    cursor_anim_col = float(cursor_target_col)
                else:
                    cursor_anim_row += delta_row * CURSOR_SMOOTHING
                    cursor_anim_col += delta_col * CURSOR_SMOOTHING

                    # Ensure tiny deltas still move every frame for smoother feel.
                    if 0 < abs(delta_col) < CURSOR_MIN_STEP:
                        cursor_anim_col += CURSOR_MIN_STEP if delta_col > 0 else -CURSOR_MIN_STEP

                    # Keep interpolation from stepping past the target.
                    if (cursor_target_col - cursor_anim_col) * delta_col < 0:
                        cursor_anim_col = float(cursor_target_col)

            stdscr.move(int(round(cursor_anim_row)), int(round(cursor_anim_col)))

        stdscr.refresh()

        frame_elapsed = time.monotonic() - frame_start
        sleep_ms = int(max(0, (FRAME_TIME - frame_elapsed) * 1000))
        if sleep_ms > 0:
            curses.napms(sleep_ms)

    elapsed_total = 0 if started_at is None else min(game_duration, time.monotonic() - started_at)
    remaining_after_exit = max(0, game_duration - elapsed_total)

    if time_up:
        wpm, accuracy, wrong_words = calculate_stats(buffer, target_text, elapsed_total)
        render_results(
            stdscr,
            wpm,
            accuracy,
            wrong_words,
            title="Time Up",
            close_after=5,
        )
    elif should_exit:
        wpm, accuracy, wrong_words = calculate_stats(buffer, target_text, elapsed_total)
        render_results(
            stdscr,
            wpm,
            accuracy,
            wrong_words,
            title="Exited Early",
            close_after=5,
        )
    

if __name__ == "__main__":
    curses.wrapper(main)
