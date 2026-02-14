import curses
import random 
import os 
def get_words(text, no_words= 100):
    words = random.choices(text, k= no_words)
    return words

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
    
    stdscr.addstr(1,0, "type Something and press Enter...", curses.color_pair(1))
    # stdscr.addstr(2,0, "green on default background", curses.color_pair(2))
    # stdscr.addstr(3,0, "RED on black background", curses.color_pair(3))
    
    while True:
        ch = stdscr.getch()
        
        # enter key 
        if ch in (10, 13):
            break 
        
        # handle BACKSPACE
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            buffer = buffer[:-1]
            stdscr.move(2,0)
            stdscr.clrtoeol()
            stdscr.addstr(2,0,buffer)
            
        # printable chars only 
        elif 32 <= ch <= 126:
            buffer += chr(ch)
            stdscr.addch(ch)
            
    stdscr.refresh()
    
    stdscr.addstr(2, 0,f"YOU TYPED: {buffer}")
    stdscr.getch()
    if os.path.exists('words.txt'):
        with open('words.txt','r') as file:
            text = file.read();
            text = text.split(' ')
            get_words(text);

if __name__ == "__main__":
    curses.wrapper(main)
