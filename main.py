import curses
import random 
import os 
import re

                
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

def main(stdscr):
    curses.curs_set(1)
    stdscr.clear()
    curses.start_color()
    
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
    positions = render_text(stdscr, target_text, buffer, y=1, x=0)
    if positions and positions[0] is not None:
        stdscr.move(1 + positions[0][0], positions[0][1])
    stdscr.refresh()
    
    
    
    while True:
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
                buffer += chr(ch)

        stdscr.clear()
        positions = render_text(stdscr, target_text, buffer, y=1, x=0)

        if len(buffer) >= len(target_text):
            if positions:
                last = next((p for p in reversed(positions) if p is not None), (0, 0))
                stdscr.move(1 + last[0], last[1])
        elif positions and positions[len(buffer)] is not None:
            row, col = positions[len(buffer)]
            stdscr.move(1 + row, col)
            
    stdscr.refresh()
    
    # stdscr.addstr(2, 0,f"YOU TYPED: {buffer}")
    # stdscr.getch()
    

if __name__ == "__main__":
    curses.wrapper(main)
