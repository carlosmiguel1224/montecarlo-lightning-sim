from util import *


def test_callback():
    print("Menu clicked!")

display, start_display, add_menu, add_function_to_menu = init_display()

add_menu("TestMenu")
add_function_to_menu("TestMenu", test_callback)

start_display()