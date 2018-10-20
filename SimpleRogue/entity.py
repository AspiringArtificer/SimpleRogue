
class Entity:
    """
    A generic class type to represent physical beings and objects. players, enemies, items, etc.
    """

    def __init__(self, x, y, char, color):
        self.x = x
        self.y = y
        self.char = char
        self.color = color


    def move(self, dx, dy):
        #move the entity around
        self.x += dx
        self.y += dy