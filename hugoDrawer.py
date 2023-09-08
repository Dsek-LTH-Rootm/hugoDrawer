import tkinter as tk
from tkinter import ttk
import json
import requests
from tkinter.filedialog import asksaveasfile, askopenfile

import math

ip = "192.168.21.215"
port = 8090


class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.title("Hugo painter")

        self.rows = 7
        self.columns = 95
        self.cellwidth = 18
        self.cellheight = 18
        self.window_width = self.columns * self.cellwidth
        self.window_height = self.rows * self.cellheight

        self.cursorSize = 1

        frame = ttk.Frame(self)

        self.canvas = tk.Canvas(
            frame,
            width=self.window_width,
            height=self.window_height,
            borderwidth=0,
            highlightthickness=0,
        )
        self.canvas.pack(side="top", fill="both", expand="true")
        self.canvas.bind("<Button-1>", self.leftClick)
        self.canvas.bind("<B1-Motion>", self.leftClick)
        self.canvas.bind("<Button-3>", self.rightClick)
        self.canvas.bind("<B3-Motion>", self.rightClick)

        load_button = ttk.Button(self, text="Load", command=self.load)
        load_button.pack(side="bottom")

        save_button = ttk.Button(self, text="Save", command=self.save)
        save_button.pack(side="bottom")

        send_button = ttk.Button(self, text="Send", command=self.send)
        send_button.pack(side="bottom")

        clear_button = ttk.Button(self, text="Clear", command=self.clear)
        clear_button.pack(side="bottom")

        frame.bind_all("<KeyPress>", self.keyPress)

        frame.pack()

        self.off_colour = "grey"
        self.on_colour = "red"

        # create a rows*columns matrix, initialized to false
        self.tile_status = [
            [False for _ in range(self.columns)] for _ in range(self.rows)
        ]

        self.rect = {}
        for column in range(self.columns):
            for row in range(self.rows):
                x1 = column * self.cellwidth
                y1 = row * self.cellheight
                x2 = x1 + self.cellwidth
                y2 = y1 + self.cellheight
                self.rect[row, column] = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=self.off_colour, tags="rect"
                )

    def renderTile(self, row, col):
        colour = self.getColor(row, col)
        item_id = self.rect[row, col]
        self.canvas.itemconfig(item_id, fill=colour)

    def render(self):
        for row in range(self.rows):
            for col in range(self.columns):
                self.renderTile(row, col)

    def setTile(self, row, col, status):
        self.tile_status[row][col] = status

    def flipTile(self, row, col):
        self.setTile(row, col, not self.tile_status[row][col])

    def flipCursor(self, center_row, center_col):
        for offset_row in range(self.cursorSize):
            for offset_col in range(self.cursorSize):
                row = center_row + offset_row - (math.ceil(self.cursorSize / 2) - 1)
                col = center_col + offset_col - (math.ceil(self.cursorSize / 2) - 1)
                if self.isTileInsideCanvas(row, col):
                    self.flipTile(row, col)
                    self.renderTile(row, col)

    def setCursor(self, center_row, center_col, status):
        for offset_row in range(self.cursorSize):
            for offset_col in range(self.cursorSize):
                row = center_row + offset_row - (math.ceil(self.cursorSize / 2) - 1)
                col = center_col + offset_col - (math.ceil(self.cursorSize / 2) - 1)
                if self.isTileInsideCanvas(row, col):
                    self.setTile(row, col, status)
                    self.renderTile(row, col)

    def getColor(self, row, col):
        return self.on_colour if self.tile_status[row][col] else self.off_colour

    def status_to_intensity(self):
        data = [item * 255 for row in self.tile_status for item in row]
        return {"data": data}

    def intensity_to_status(self, data):
        statuses = [
            [data["data"][col + row * self.columns] > 0 for col in range(self.columns)]
            for row in range(self.rows)
        ]
        return statuses

    def isPixelInsideCanvas(self, x, y):
        insideWidth = 0 <= x < self.window_width
        insideHeight = 0 <= y < self.window_height
        return insideWidth and insideHeight

    def isTileInsideCanvas(self, row, col):
        insideWidth = 0 <= row < self.rows
        insideHeight = 0 <= col < self.columns
        return insideWidth and insideHeight

    def clear(self):
        for row in range(self.rows):
            for col in range(self.columns):
                self.setTile(row, col, False)
        self.render()

    def send(self):
        data = self.status_to_intensity()
        try:
            r = requests.post(f"http://{ip}:{port}/image", json=data)
            if r.status_code != 200:
                print(f"sending tile data failed with response: {r.text}")
        except requests.exceptions.ConnectionError:
            print(f"Could not connect to Hugo Server({ip}:{port})")

    def save(self):
        data = self.status_to_intensity()
        f = asksaveasfile(
            initialfile="hugo.json",
            defaultextension=".json",
        )
        if f:
            print(f"Saving tiles to {f.name}")
            f.write(json.dumps(data))

    def load(self):
        f = askopenfile(initialfile="hugo.json", defaultextension=".json")
        if f:
            print(f"Loading tiles from {f.name}")
            data = json.loads(f.read())
            self.tile_status = self.intensity_to_status(data)
            self.render()

    def leftClick(self, event):
        if not self.isPixelInsideCanvas(event.x, event.y):
            return

        row = int(event.y / self.cellheight)
        col = int(event.x / self.cellwidth)

        self.setCursor(row, col, True)

    def rightClick(self, event):
        if not self.isPixelInsideCanvas(event.x, event.y):
            return

        row = int(event.y / self.cellheight)
        col = int(event.x / self.cellwidth)

        self.setCursor(row, col, False)

    def shift(self, delta_row, delta_col):
        # shift rows
        if delta_row < 0:
            for _ in range(-delta_row):  # check if list slicing is faster
                self.tile_status.pop(0)  # slow for popping first

                empty_row = [False for _ in range(self.columns)]
                self.tile_status.append(empty_row)
        else:
            for _ in range(delta_row):
                self.tile_status.pop()

                empty_row = [False for _ in range(self.columns)]
                self.tile_status.insert(0, empty_row)

        # shift cols
        if delta_col < 0:
            for _ in range(-delta_col):
                for r in range(self.rows):
                    self.tile_status[r].pop(0)  # slow for popping first
                    self.tile_status[r].append(False)
        else:
            for _ in range(delta_col):
                for r in range(self.rows):
                    self.tile_status[r].pop()  # slow for popping first
                    self.tile_status[r].insert(0, False)

        self.render()

    def increaseCursor(self, delta):
        self.cursorSize += delta

    def decreaseCursor(self, delta):
        self.cursorSize = max(self.cursorSize - delta, 1)

    def keyPress(self, event):
        print(f"received key press: {event}")
        # shift tiles
        if event.keysym == "Left":
            self.shift(0, -1)
        elif event.keysym == "Right":
            self.shift(0, 1)
        elif event.keysym == "Up":
            self.shift(-1, 0)
        elif event.keysym == "Down":
            self.shift(1, 0)

        # change brush/eraser size
        elif event.keysym == "plus":
            self.increaseCursor(1)
        elif event.keysym == "minus":
            self.decreaseCursor(1)


if __name__ == "__main__":
    app = App()
    app.mainloop()
