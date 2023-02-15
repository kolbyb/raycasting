import pygame
import time
from geometry import *
import math
import sys
import os

cppyy.include("raycasting.hpp")
from cppyy.gbl import World, MakeWorld, Camera, RayCastWorker


def box(ul: Point):
    return [
        Segment(ul + Point(0, 0), ul + Point(1, 0)),
        Segment(ul + Point(1, 0), ul + Point(1, -1)),
        Segment(ul + Point(0, 0), ul + Point(0, -1)),
        Segment(ul + Point(0, -1), ul + Point(1, -1)),
    ]


def lr_triangle(ul: Point):
    return [
        Segment(ul + Point(0, -1), ul + Point(1, -1)),
        Segment(ul + Point(1, 0), ul + Point(1, -1)),
        Segment(ul + Point(0, -1), ul + Point(1, 0)),
    ]


def ur_triangle(ul: Point):
    return [
        Segment(ul + Point(0, 0), ul + Point(1, 0)),
        Segment(ul + Point(1, 0), ul + Point(1, -1)),
        Segment(ul + Point(0, 0), ul + Point(1, -1)),
    ]


def ll_triangle(ul: Point):
    return [
        Segment(ul + Point(0, 0), ul + Point(1, -1)),
        Segment(ul + Point(0, -1), ul + Point(1, -1)),
        Segment(ul + Point(0, 0), ul + Point(0, -1)),
    ]


def ul_triangle(ul: Point):
    return [
        Segment(ul + Point(0, 0), ul + Point(1, 0)),
        Segment(ul + Point(1, 0), ul + Point(0, -1)),
        Segment(ul + Point(0, 0), ul + Point(0, -1)),
    ]


def make_map(map_string):
    result = []
    lines = map_string.split("\n")

    # start from top of map and work down
    y = len(lines)

    for line in lines:
        x = 0
        for char in line:
            if char == "#" or char == "*":
                result += box(Point(x, y))
            if char == "/":
                result += ul_triangle(Point(x, y))
            if char == "&":
                result += ur_triangle(Point(x, y))
            if char == "%":
                result += lr_triangle(Point(x, y))
            if char == "`":
                result += ll_triangle(Point(x, y))

            x += 1
        y -= 1

    print(f"Segments: {len(result)}")

    # if any segment exists twice, then it was between two map items
    # and both can be removed!
    result = [item for item in result if result.count(item) == 1]

    print(f"Filtered duplicated wall segments: {len(result)}")

    cont = True
    while cont:
        remove_list = []
        for s in result:
            for n in result:
                if s.end.x == n.start.x and s.end.y == n.start.y and n.slope() == s.slope():
                    remove_list += [n, s]
                    result.append(
                        Segment(Point(s.start.x, s.start.y), Point(n.end.x, n.end.y))
                    )
                    break
                elif (
                    s is not n
                    and s.end.x == n.end.x
                    and s.end.y == n.end.y
                    and n.slope() == s.slope()
                ):
                    remove_list += [n, s]
                    result.append(
                        Segment(
                            Point(s.start.x, s.start.y), Point(n.start.x, n.start.y)
                        )
                    )
                    break
                elif (
                    s is not n
                    and s.start.x == n.start.x
                    and s.start.y == n.start.y
                    and n.slope() == s.slope()
                ):
                    remove_list += [n, s]
                    result.append(
                        Segment(Point(s.end.x, s.end.y), Point(n.end.x, n.end.y))
                    )
                    break

            if len(remove_list) > 0:
                break

        if len(remove_list) == 0:
            cont = False

        for i in remove_list:
            result.remove(i)

    print(f"Merged segments: {len(result)}")

    return result


#
# Symbols:
#
#  /  ###   # or *  ### & ###  %    #  `  #
#     ##            ###    ##      ##     ##
#     #             ###     #     ###     ###
#


game_map = """
###########`&#######
#           ` / /  #
#/%#/&`&/&`& % `%`&#
# / %  / `/% &  /  #
#& / `   & / & /%/%#
# `&  & `& ` `% ` &#
#  % # / `%&  # `& #
#% /% %`` / %/& &  #
#/% /   &`%/ % /%& #
# # //&    %& %`&  #
#  % %`  %/     % &#
####################
"""

map_wall_segments = make_map(game_map)

pygame.init()

width = 800
height = 480

screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)

FOV = 2 * math.atan((width / 800) * math.tan((math.pi / 2) / 2))

c = Camera(Point(10, 14), math.pi, FOV)

frame = 0
last_time = time.perf_counter()
fps_elapsed = 0.0

fisheye_distance_correction = True

w = MakeWorld()
w.walls = map_wall_segments

workers = [RayCastWorker(w.get_pointer()) for _ in range(os.cpu_count() or 1)]

def draw_results(rays, results, col_offset: int):
    col = 0
    last_match = None
    last_wall = None
    color = (0,0,0)
    last_color = (0,0,0)

    camera_ray = Ray(c.location, c.direction)
    camera_segment = camera_ray.to_segment()

    for result in results:
        # only draw the closest wall.
        if result.hit:
            rs = rays[col]
            r = rs.to_ray()
            distance_from_eye = result.distance

            # Distance correction from https://gamedev.stackexchange.com/questions/45295/raycasting-fisheye-effect-question
            corrected_distance = (
                distance_from_eye * math.cos(c.direction - r.angle)
                if fisheye_distance_correction
                else distance_from_eye
            )

            corrected_distance = max(1.0e-09, round(corrected_distance * 1000) / 1000)
            wall_height = (height * 0.75) / corrected_distance
            if wall_height > height:
                wall_height = height + 2

            wall_start = (height - wall_height) / 2
            wall_end = wall_start + wall_height

            sn = result.segment.surface_normal()
            color = (128 + 127 * sn.x, 128 + 127 * sn.y, 0.0)
            dn = sn.dot(rs.normal())
            dn = 1.0 - (dn + 1.0) * 0.25
            cn = sn.dot(rs.normal())
            cn = 1.0 - (cn + 1.0) * 0.25
            cn = cn * cn
            dn = min(1.0, max(0.5, dn * cn))
            dn = dn * min(1.0, max(0.0, 1.0 - min(4.0, corrected_distance) / 4.0))
            dn = 0.125 + (dn * 0.875)
            color = (color[0] * dn, color[1] * dn, 0.0)

            # Draw edge if detected
            if col != 0 or col_offset != 0:
                if last_match is None:
                    pygame.draw.line(
                        pygame.display.get_surface(),
                        color,
                        (col + col_offset, wall_start),
                        (col + col_offset, wall_end),
                    )
                else:
                    wall_delta = wall_end - wall_start
                    last_delta = last_wall[1] - last_wall[0]
                    pygame.draw.line(
                        pygame.display.get_surface(),
                        color if not math.fabs(wall_delta - last_delta) < 3.0 and wall_delta > last_delta else last_color,
                        (col + col_offset, min(wall_start, last_wall[0])),
                        (col + col_offset, max(wall_end, last_wall[1])),
                    )
            else:
                # draw just top and bottom points otherwise
                screen.set_at((col + col_offset, int(wall_start)), color)
                screen.set_at((col + col_offset, int(wall_end)), color)

                # and some texture...
                texture_size = int(height / 50)
                if col % texture_size == 0:
                    for y in range(int(wall_start), int(wall_end), texture_size):
                        screen.set_at((col + col_offset, y), color)

            last_wall = (wall_start, wall_end)
            last_match = result.segment
        else:
            # Look for transition from wall to empty space, draw edge
            if last_match is not None:
                pygame.draw.line(
                    pygame.display.get_surface(),
                    (0.0, 1.0, 0.0),
                    (col + col_offset, last_wall[0]),
                    (col + col_offset, last_wall[1]),
                )
            last_match = None

        last_color = color
        col += 1

while True:
    pygame.display.get_surface().fill((0, 0, 0))
    pygame.draw.rect(
        pygame.display.get_surface(),
        (100, 149, 237),
        (0, 0, width, height * 0.5)
    )
    pygame.draw.rect(
        pygame.display.get_surface(),
        (131, 101, 57),
        (0, height * 0.5, width, height * 0.5)
    )

    frame += 1

    new_time = time.perf_counter()
    elapsed, last_time = new_time - last_time, new_time
    fps_elapsed += elapsed

    if frame % 30 == 0:
        pygame.display.set_caption(f"{1.0 / (fps_elapsed / 30.0)} fps ({c.location.x},{c.location.y})")
        fps_elapsed = 0.0
    (width, height) = pygame.display.get_window_size()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            for worker in workers:
                worker.stop()
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                c.planar_projection = not c.planar_projection
            if event.key == pygame.K_2:
                fisheye_distance_correction = not fisheye_distance_correction

    keys = pygame.key.get_pressed()

    if keys[pygame.K_UP]:
        c.try_move(1.0 * elapsed, w)
    if keys[pygame.K_DOWN]:
        c.try_move(-1.0 * elapsed, w)
    if keys[pygame.K_RIGHT]:
        c.rotate(math.pi / 2 * elapsed)
    if keys[pygame.K_LEFT]:
        c.rotate(-math.pi / 2 * elapsed)

    count = 0
    work: list[list[Segment]] = [[] * 1 for _ in range(len(workers))]
    current_worker = 0
    num_per_worker = int(1 + width / len(workers))
    for r in c.rays(width):
        work[current_worker].append(r.to_segment())
        count += 1
        
        if len(work[current_worker]) == num_per_worker or count == width:
            workers[current_worker].set_work(work[current_worker])
            current_worker += 1
    
    current_worker = 0
    for worker in workers:
        results = worker.get_results()
        draw_results(work[current_worker], results, num_per_worker * current_worker)
        current_worker += 1
    
    pygame.display.flip()