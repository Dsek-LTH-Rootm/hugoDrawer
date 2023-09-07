import tkinter as tk
from tkinter import ttk
import json
import requests
from tkinter.filedialog import asksaveasfile, askopenfile

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

        self.lastHoverPixel = ()
        self.hoverSetState = False
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
        self.canvas.bind("<Button-1>", self.mouseDown)
        self.canvas.bind("<B1-Motion>", self.onMove)

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
        self.pixel_status = [
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

        # self.redraw(1000)

    # def redraw(self, delay):
    #    self.canvas.itemconfig("rect", fill=self.off_colour)
    #    for i in range(10):
    #        row = random.randint(0, self.rows - 1)
    #        col = random.randint(0, self.columns - 1)
    #        item_id = self.rect[row, col]
    #        self.canvas.itemconfig(item_id, fill=self.on_colour)
    #    self.after(delay, lambda: self.redraw(delay))

    def renderPixel(self, row, col):
        colour = self.getColor(row, col)
        item_id = self.rect[row, col]
        self.canvas.itemconfig(item_id, fill=colour)

    def render(self):
        for row in range(self.rows):
            for col in range(self.columns):
                self.renderPixel(row, col)

    def flipPixel(self, row, col):
        self.pixel_status[row][col] = not self.pixel_status[row][col]

    def setPixel(self, row, col, on):
        self.pixel_status[row][col] = on

    def getColor(self, row, col):
        return self.on_colour if self.pixel_status[row][col] else self.off_colour

    def status_to_intensity(self):
        data = [item * 255 for row in self.pixel_status for item in row]
        return {"data": data}

    def intensity_to_status(self, data):
        statuses = [
            [data["data"][col + row * self.columns] > 0 for col in range(self.columns)]
            for row in range(self.rows)
        ]
        return statuses

    def isInsideCanvas(self, x, y):
        insideWidth = 0 <= x < self.window_width
        insideHeight = 0 <= y < self.window_height
        return insideWidth and insideHeight

    def clear(self):
        for row in range(self.rows):
            for col in range(self.columns):
                self.setPixel(row, col, False)
        self.render()

    def send(self):
        data = self.status_to_intensity()
        r = requests.post(f"http://{ip}:{port}/image", json=data)
        if r.status_code != 200:
            print(f"sending pixel data failed with response: {r.text}")

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
            self.pixel_status = self.intensity_to_status(data)
            self.render()

    def mouseDown(self, event):
        row = int(event.y / self.cellheight)
        col = int(event.x / self.cellwidth)

        self.flipPixel(row, col)
        self.renderPixel(row, col)

        self.hoverSetState = self.pixel_status[row][col]

    def onMove(self, event):
        if not self.isInsideCanvas(event.x, event.y):
            return

        row = int(event.y / self.cellheight)
        col = int(event.x / self.cellwidth)

        current_pixel = (row, col)
        if current_pixel != self.lastHoverPixel:
            self.lastHoverPixel = current_pixel
            self.setPixel(row, col, self.hoverSetState)
            self.renderPixel(row, col)

    def shift(self, delta_row, delta_col):
        # shift rows
        if delta_row < 0:
            for _ in range(-delta_row):  # check if list slicing is faster
                self.pixel_status.pop(0)  # slow for popping first

                empty_row = [False for _ in range(self.columns)]
                self.pixel_status.append(empty_row)
        else:
            for _ in range(delta_row):
                self.pixel_status.pop()

                empty_row = [False for _ in range(self.columns)]
                self.pixel_status.insert(0, empty_row)

        # shift cols
        if delta_col < 0:
            for _ in range(-delta_col):
                for r in range(self.rows):
                    self.pixel_status[r].pop(0)  # slow for popping first
                    self.pixel_status[r].append(False)
        else:
            for _ in range(delta_col):
                for r in range(self.rows):
                    self.pixel_status[r].pop()  # slow for popping first
                    self.pixel_status[r].insert(0, False)

        self.render()

    def increaseCursor(self, delta):
        self.cursorSize += delta

    def decreaseCursor(self, delta):
        self.cursorSize = max(self.cursorSize - delta, 1)

    def keyPress(self, event):
        print(f"received key press: {event}")
        # shift pixels
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
        elif event.keysym == "min":
            self.decreaseCursor(1)


if __name__ == "__main__":
    app = App()
    app.mainloop()
