from editor import Editor

if __name__ == "__main__":
    editor = Editor()
    editor.load_world("custom.map")
    editor.run()