from PIL import Image

Shape = Image.new("RGB", (1920, 1080), (0, 0, 0))
Cell = Image.open("Клетка.png")

for i in range(48):
    for j in range(27):
        Shape.paste(Cell, (40 * i, 40 * j), Cell)

Shape.save("res.png")