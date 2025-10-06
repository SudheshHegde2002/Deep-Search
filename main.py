import tkinter as tk
from search_utils.ui_utils import SearchGUI

def main():
    root = tk.Tk()
    root.geometry("1024x768")
    app = SearchGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()