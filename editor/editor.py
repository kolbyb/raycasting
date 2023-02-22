import cppyy
from .camera import EditorCamera
from .renderer import EditorRenderer
from .input import InputHandler
from typing import Any, Self
import pygame
import json
import time
import sys
import os

from .tools.add_wall import AddWall
from .tools.edit_wall import EditWall
from .tools.draw_grid import DrawGrid
from .tools.draw_walls import DrawWalls

cppyy.include("raycasting.cpp")
from cppyy.gbl import World, MakeWorld, Point

from serialization import CppyySerializer, CppyyTypeHint

class Editor():
    Serializer = CppyySerializer(
        hints={
            "Segment": CppyyTypeHint(["start", "end"]),
            "Point": CppyyTypeHint(["x", "y"]),
        }
    )
    
    def __init__(self: Self) -> None:
        self.__camera: EditorCamera = EditorCamera(800, 400)
        self.__renderer: EditorRenderer = None
        self.__running: bool = False
        self.__world: World = None
        self.__world_filepath: str = None
        self.__tools: list[Any] = [
            DrawGrid,
            DrawWalls,
            EditWall,
            AddWall,
        ]
    
    def load_world(self: Self, filepath: str) -> None:
        self.__world = MakeWorld()
        self.__world_filepath = filepath
        with open(filepath, 'r') as file:
            self.Serializer.deserialize(self.__world, json.load(file))
    
    def save_world(self: Self) -> None:
        with open(self.__world_filepath, 'w') as file:
            json.dump(self.Serializer.serialize(self.__world), file)
    
    def exit(self: Self, key:int = 0, down: bool = True) -> None:
        self.__running = False

    def run(self: Self) -> None:
        pygame.init()
        pygame.mouse.get_rel()

        width = 800
        height = 480
        frame = 0
        last_time = 0.0

        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.__renderer = EditorRenderer(self.__camera, pygame.display.get_surface())

        self.__running = True
        while self.__running:
            pygame.display.get_surface().fill((21, 26, 31))
    
            frame += 1

            new_time = time.perf_counter()
            elapsed, last_time = new_time - last_time, new_time
            
            (width, height) = pygame.display.get_window_size()
            self.__camera.set_dimensions(width, height)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEWHEEL:
                    InputHandler.handle_mouse_scroll(event.x, event.y)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    InputHandler.handle_mouse_button(event.button, True)
                if event.type == pygame.MOUSEBUTTONUP:
                    InputHandler.handle_mouse_button(event.button, False)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s:
                        self.save_world()
                    else:
                        InputHandler.handle_key(event.key, True)
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_s:
                        pass
                    else:
                        InputHandler.handle_key(event.key, False)

            mouse_rel = pygame.mouse.get_rel()
            InputHandler.handle_mouse_relative(mouse_rel[0], mouse_rel[1])

            self.__camera.tick(elapsed)
            
            cursor_pos = pygame.mouse.get_pos()
            kwargs = dict({
                "world": self.__world,
                "cursor": Point(cursor_pos[0], cursor_pos[1]),
                "camera": self.__camera,
                "renderer": self.__renderer,
            })
            for tool in self.__tools:
                tool.update(**kwargs)

            pygame.display.flip()

if __name__ == "__main__":
    editor = Editor()
    print(os.getcwd())
    editor.load_world("custom.map")
    editor.run()