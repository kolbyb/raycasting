import pygame
import time
from geometry import *
from functools import cached_property
import dataclasses
import typing
from typing import Self
import math
import sys
import os
import serialization
import json

cppyy.include("raycasting.hpp")
from cppyy.gbl import World, MakeWorld, Camera, RayCastWorker

pygame.init()

width = 800
height = 480
frame = 0
last_time = 0.0

screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
center = Point(width * 0.5, height * 0.5)

w = MakeWorld()

class EditorCamera():
    def __init__(self: Self):
        self.__zoom_clamp = (8.0, 400.0)
        self.__move_speed = 2.0
        self.location = Point(0.0, 0.0)
        self.zoom = self.__zoom_clamp[0]
        self.__drawing_wall = False
        self.__in_progress_wall = Segment()
        self.__editing_wall = False
        self.__flip_wall = False
        self.__remove_wall = False
        self.__mouse_move = None
    
    def adjust_zoom(self: Self, count: float):
        self.zoom = min(self.__zoom_clamp[1], max(self.__zoom_clamp[0], e.zoom + event.y * 2.0))
    
    def flip_wall(self: Self):
        self.__flip_wall = True
    
    def remove_wall(self: Self):
        self.__remove_wall = True
    
    @classmethod
    def __flip_segment__(cls, segment: Segment):
        start = Point(segment.start)
        segment.start, segment.end = segment.end, start

    def tick(self: Self, elapsed: float):
        keys = pygame.key.get_pressed()
        zoom_accel = self.__zoom_clamp[1] / self.zoom
        move = Point(0.0, 0.0)
        self.__mouse_move = pygame.mouse.get_rel()

        if pygame.mouse.get_pressed()[2]:
            move = Point(-self.__mouse_move[0] / self.zoom, self.__mouse_move[1] / self.zoom)
            self.location += move
        else:
            self.__mouse_move = None
            if keys[pygame.K_UP]:
                move.y += 1.0
            if keys[pygame.K_DOWN]:
                move.y -= 1.0
            if keys[pygame.K_RIGHT]:
                move.x += 1.0
            if keys[pygame.K_LEFT]:
                move.x -= 1.0

            self.location += move * self.__move_speed * zoom_accel * elapsed

    def draw(self: Self):
        width, height = pygame.display.get_window_size()
        self.__center = Point(width * 0.5, height * 0.5)
        grid_half = min(self.__zoom_clamp[0], self.__center.x / self.zoom)
        grid_center = Point(round(self.location.x), round(self.location.y))
        horizontal = Point(width * 0.5, 0.0)
        vertical = Point(0.0, height * 0.5)

        grid_square_half = int(width / grid_half / 2)
        grid_count_half = int(width / grid_square_half * 3.2)

        cursor_scale = (10.0 / self.zoom, 7.07 / self.zoom)

        cursor_relative = pygame.mouse.get_pos()
        cursor_point = self.__unprojected_point_(Point(cursor_relative[0], cursor_relative[1]))
        cursor_snapped_point = Point(round(cursor_point.x * 8.0) / 8.0, round(cursor_point.y * 8.0) / 8.0)
        cursor_segments = [
            #Segment(Point(-0.6, -0.5) + cursor_point, Point(0.4, 0.5) + cursor_point),
            #Segment(Point(0.6, -0.5) + cursor_point, Point(-0.4, 0.5) + cursor_point),
            #Segment(Point(-0.4, -0.5) + cursor_point, Point(0.6, 0.5) + cursor_point),
            #Segment(Point(0.4, -0.5) + cursor_point, Point(-0.6, 0.5) + cursor_point),
            #Segment(Point(0.5, -0.5) + cursor_point, Point(0.5, 0.5) + cursor_point),
            #Segment(Point(-0.5, -0.5) + cursor_point, Point(-0.5, 0.5) + cursor_point),
            #Segment(Point(0.5, 0.5) + cursor_point, Point(-0.5, 0.5) + cursor_point),
            #Segment(Point(0.5, -0.5) + cursor_point, Point(-0.5, -0.5) + cursor_point),

            Segment(cursor_point, Point(-cursor_scale[0],  0.00)            + cursor_point),
            Segment(cursor_point, Point(-cursor_scale[1], -cursor_scale[1]) + cursor_point),
            Segment(cursor_point, Point( 0.00,            -cursor_scale[0]) + cursor_point),
            Segment(cursor_point, Point( cursor_scale[1], -cursor_scale[1]) + cursor_point),
            Segment(cursor_point, Point( cursor_scale[0],  0.00)            + cursor_point),
            Segment(cursor_point, Point( cursor_scale[1],  cursor_scale[1]) + cursor_point),
            Segment(cursor_point, Point( 0.00,             cursor_scale[0]) + cursor_point),
            Segment(cursor_point, Point(-cursor_scale[1],  cursor_scale[1]) + cursor_point),
        ]

        #print(f"{grid_half}, {grid_square_half}, {grid_count_half}")
        for n in range(-grid_count_half, grid_count_half):
            hstart = Point(0, n) + grid_center
            vstart = Point(n, 0) + grid_center
            s1, e1 = self.__projected_segment__(Segment(hstart - horizontal, hstart + horizontal))
            s2, e2 = self.__projected_segment__(Segment(vstart - vertical, vstart + vertical))

            pygame.draw.line(
                pygame.display.get_surface(),
                (41, 46, 51),
                s1,
                e1,
                1
            )
            
            pygame.draw.line(
                pygame.display.get_surface(),
                (41, 46, 51),
                s2,
                e2,
                1
            )

        #for cursor_segment in cursor_segments:
        #    start, end = self.__projected_segment__(cursor_segment)
        #    pygame.draw.line(
        #        pygame.display.get_surface(),
        #        (255, 0, 0),
        #        start,
        #        end,
        #        2
        #    )
        
        cursor_intersection = min(
            [cursor_segment.intersect_list(w.walls) for cursor_segment in cursor_segments],
            key=lambda result: (result.point - cursor_point).length()
        )

        remove_wall = None
        for wall in w.walls:
            intersected = (self.__editing_wall and self.__in_progress_wall == wall) or (not self.__editing_wall and wall == cursor_intersection)
            self.__draw_wall__(wall, color=((191, 196, 201) if not intersected else (221, 176, 31)), draw_surface_normal=intersected)

            closest_vertex = min([wall.start, wall.end], key=lambda point: (point - cursor_point).length())
            is_start = closest_vertex == wall.start
            if intersected:
                start, end = self.__projected_segment__(wall)
                vertex_screen = start if is_start else end
                pygame.draw.circle(
                    pygame.display.get_surface(),
                    (0, 255, 0),
                    self.__projected_point__(cursor_intersection.point),
                    5.0
                )
                pygame.draw.circle(
                    pygame.display.get_surface(),
                    (255, 255, 255),
                    vertex_screen,
                    5.0
                )

                if self.__flip_wall:
                    self.__flip_segment__(wall)
                    self.__flip_wall = False
                
                if self.__drawing_wall or not pygame.key.get_pressed()[pygame.K_LSHIFT]:
                    if not self.__remove_wall and not self.__drawing_wall and (not self.__editing_wall or self.__in_progress_wall == wall) and pygame.mouse.get_pressed()[0]:
                        self.__editing_wall = True
                        self.__in_progress_wall = wall
                
                if self.__remove_wall:
                    remove_wall = wall
                    self.__remove_wall = False
                if not self.__drawing_wall and not self.__editing_wall and pygame.mouse.get_pressed()[1]:
                    remove_wall = wall
        
            if self.__editing_wall and self.__in_progress_wall == wall:
                if not pygame.mouse.get_pressed()[0]:
                    self.__editing_wall = False
                    self.__in_progress_wall = None
                
                if is_start and not (math.isclose(cursor_snapped_point.x, wall.end.x) and math.isclose(cursor_snapped_point.y, wall.end.y)):
                    wall.start = cursor_snapped_point
                elif not is_start and not (math.isclose(cursor_snapped_point.x, wall.start.x) and math.isclose(cursor_snapped_point.y, wall.start.y)):
                    wall.end = cursor_snapped_point

        if remove_wall is not None:
            w.walls.erase(remove_wall)
    
        if not self.__editing_wall and not self.__remove_wall:
            if (self.__drawing_wall or not cursor_intersection.hit) and pygame.mouse.get_pressed()[0]:
                if not self.__drawing_wall:
                    self.__drawing_wall = True
                    self.__in_progress_wall = Segment(cursor_snapped_point, cursor_snapped_point)
                else:
                    self.__in_progress_wall.end = cursor_snapped_point
                
                self.__draw_wall__(self.__in_progress_wall, color=(92, 178, 204), draw_surface_normal=True)
            elif self.__drawing_wall and not pygame.mouse.get_pressed()[0]:
                if self.__in_progress_wall.start != self.__in_progress_wall.end:
                    w.walls.push_back(self.__in_progress_wall)
                self.__drawing_wall = False
        
        self.__flip_wall = False
        self.__remove_wall = False

    def __draw_wall__(self: Self, wall: Segment, color: tuple[int, int, int]=(204,92,92), draw_surface_normal: bool = False):
        start, end = self.__projected_segment__(wall)
        pygame.draw.line(
            pygame.display.get_surface(),
            color,
            start,
            end,
            2
        )
        if draw_surface_normal:
            mid = wall.start + (wall.end - wall.start) * 0.5
            normal_start, normal_end = self.__projected_segment__(Segment(mid, mid + wall.surface_normal()))
            self.__draw_arrow__(
                (204, 92, 92),
                normal_start,
                normal_end,
                3
            )

    def __draw_arrow__(self: Self, color: tuple[int, int, int], start: tuple[float, float], end: tuple[float, float], width: int = 1):
        leg1 = Point(start[0] - end[0], start[1] - end[1]).normal().rotate(math.pi / 4) * 10.0
        leg2 = Point(start[0] - end[0], start[1] - end[1]).normal().rotate(-math.pi / 4) * 10.0
        pygame.draw.line(
            pygame.display.get_surface(),
            color,
            start,
            end,
            width
        )
        pygame.draw.line(
            pygame.display.get_surface(),
            color,
            end,
            (end[0] + leg1.x, end[1] + leg1.y),
            width
        )
        pygame.draw.line(
            pygame.display.get_surface(),
            color,
            end,
            (end[0] + leg2.x, end[1] + leg2.y),
            width
        )

    def __projected_point__(self: Self, point: Point):
        projected = Point(point.x - self.location.x, self.location.y - point.y) * self.zoom + self.__center
        return (projected.x, projected.y)

    def __projected_segment__(self: Self, segment: Segment):
        return self.__projected_point__(segment.start), self.__projected_point__(segment.end)

    def __unprojected_point_(self: Self, point: Point) -> Point:
        return Point(point.x - self.__center.x, self.__center.y - point.y) / self.zoom + self.location

class Editor():
    def handle_mouse(self: Self, event: pygame.event.Event):
        pass


e = EditorCamera()

serializer = serialization.CppyySerializer(
    hints={
        "Segment": serialization.CppyyTypeHint(["start", "end"]),
        "Point": serialization.CppyyTypeHint(["x", "y"]),
    }
)
with open('custom.map', 'r') as file:
#with open('maze.map', 'r') as file:
    serializer.deserialize(w, json.load(file))

# Remove any invalid wall segments
remove = []
for wall in w.walls:
    if wall.start == wall.end:
        remove.append(wall)

for wall in remove:
    w.walls.erase(wall)

while True:
    pygame.display.get_surface().fill((21, 26, 31))
    
    frame += 1

    new_time = time.perf_counter()
    elapsed, last_time = new_time - last_time, new_time
    
    (width, height) = pygame.display.get_window_size()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and pygame.key.get_mods() & pygame.KMOD_ALT:
                e.remove_wall()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                e.flip_wall()
            if event.key == pygame.K_s:
                with open('custom.map', 'w') as file:
                    json.dump(serializer.serialize(w), file)
        if event.type == pygame.MOUSEWHEEL:
            e.adjust_zoom(event.y)

    e.tick(elapsed)
    e.draw()

    pygame.display.flip()