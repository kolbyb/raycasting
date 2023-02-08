import math
import pygame
import time
import functools
import dataclasses
import typing


class Point(typing.NamedTuple):
    x: float
    y: float

    def __ge__(self, other):
        return self.x >= other.x and self.y >= other.y

    def __gt__(self, other):
        return self.x > other.x or self.y > other.y

    def __le__(self, other):
        return self.x <= other.x and self.y <= other.y

    def __lt__(self, other):
        return self.x < other.x or self.y < other.y

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        return Point(self.x * other.x, self.y * other.y)

    def __div__(self, other):
        return Point(self.x / other.x, self.y / other.y)
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def length(self):
        return math.sqrt(self.dot(self))

    def normal(self):
        length = self.length()
        if length == 0.0:
            return self
        return Point(self.x / length, self.y / length)



# Floating point math is hard, and trying to find a point on a line
# can result in some mismatches in floating point values, so we go for "close"
def in_range(min_, max_, value):
    return (min_ - 0.0000001) <= value <= (max_ + 0.0000001)


class Line(typing.NamedTuple):
    origin: Point
    slope: float


@dataclasses.dataclass(unsafe_hash=True)
class Segment:
    # Constant used to determine what a Segment's forward normal should be
    ForwardDirection = Point(math.sin(math.pi / 2), math.cos(math.pi / 2))

    start: Point
    end: Point

    @functools.cached_property
    def min_x(self):
        return min(self.start.x, self.end.x)

    @functools.cached_property
    def max_x(self):
        return max(self.start.x, self.end.x)

    @functools.cached_property
    def min_y(self):
        return min(self.start.y, self.end.y)

    @functools.cached_property
    def max_y(self):
        return max(self.start.y, self.end.y)

    @functools.cached_property
    def slope(self):
        if self.start.x == self.end.x:
            return 1e100
        else:
            return (self.end.y - self.start.y) / (self.end.x - self.start.x)

    @functools.cached_property
    def length(self):
        return (self.start - self.end).length()

    @functools.cached_property
    def normal(self):
        return (self.end - self.start).normal()

    @functools.cached_property
    def forward(self):
        return (self.normal + Segment.ForwardDirection).normal()

    @functools.cached_property
    def line(self):
        return Line(self.start, self.slope)

    def on_segment(self, p: Point):
        return in_range(self.min_x, self.max_x, p.x) and in_range(
            self.min_y, self.max_y, p.y
        )


@dataclasses.dataclass
class Ray:
    start: Point
    angle: float

    def to_line(self):
        s = math.sin(self.angle)
        if s == 0:
            return Line(self.start, 1e100)
        else:
            return Line(self.start, math.cos(self.angle) / s)

    def distant_point(self):
        return Point(
            self.start.x + (math.sin(self.angle) * 100),
            self.start.y + (math.cos(self.angle) * 100),
        )

    def to_segment(self):
        return Segment(self.start, self.distant_point())


def intercept(l1: Line, l2: Line):
    # x=-(-y2+y1+m2*x2-m1*x1)/(m1-m2)
    # solved from point-slope form
    x = -(
        -l2.origin.y + l1.origin.y + l2.slope * l2.origin.x - l1.slope * l1.origin.x
    ) / (l1.slope - l2.slope)

    # just plug it back into one of the line formulas and get the answer!
    y = l1.slope * (x - l1.origin.x) + l1.origin.y

    return Point(x, y)


def intersect_ray(ray: Ray, segments):
    return intersecting_segments(ray.to_segment(), segments)


def intersecting_segments(input_: Segment, segments):
    input_line = input_.line

    result = []

    for segment in segments:
        if not (
            segment.min_x < input_.max_x
            and segment.max_x > input_.min_x
            and segment.min_y < input_.max_y
            and segment.max_y > input_.min_y
        ):
            continue

        segment_line = segment.line

        # if not parallel
        if input_line.slope != segment_line.slope:
            p = intercept(input_line, segment_line)

            if segment.on_segment(p) and input_.on_segment(p):
                result.append((math.dist(input_.start, p), p, segment, input_))

    return result


class Camera:
    def __init__(self, location: Point, direction, viewing_angle):
        self.location = location
        self.direction = direction
        self.viewing_angle = viewing_angle

    def try_move(self, distance, walls):
        new_location = self.location + Point(
            distance * -math.sin(self.direction), distance * -math.cos(self.direction)
        )

        proposed_move = Segment(self.location, new_location)

        if len(intersecting_segments(proposed_move, walls)) == 0:
            # we don't intersect any wall, so we allow the move
            self.location = new_location

    def rotate(self, angle):
        self.direction += angle
    
    def forward(self):
        return Point(math.sin(c.direction), math.cos(c.direction))

    def rays(self, count):
        angle_slice = self.viewing_angle / count
        start_angle = self.direction - (self.viewing_angle / 2) + angle_slice / 2
        location = self.location

        for current in range(count):
            yield Ray(location, angle_slice * current + start_angle)


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
                if s.end.x == n.start.x and s.end.y == n.start.y and n.slope == s.slope:
                    remove_list += [n, s]
                    result.append(
                        Segment(Point(s.start.x, s.start.y), Point(n.end.x, n.end.y))
                    )
                    break
                elif (
                    s is not n
                    and s.end.x == n.end.x
                    and s.end.y == n.end.y
                    and n.slope == s.slope
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
                    and n.slope == s.slope
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

class DebugOption(typing.NamedTuple):
    key: int
    name: str
    default_value: bool

@dataclasses.dataclass
class DebugOptions:
    def __init__(self, options: list[DebugOption]):
        self.__toggle_time = 0.0 # Simple elapsed time to prevent Debug options from flickering
        self.__toggle_delay = 0.25
        self.__options = list()
        self.__option_values = dict()

        for option in options:
            self.__options.append(option)
            self.__option_values[option.name] = option.default_value

    def __getitem__(self, name: str) -> bool:
        return self.__option_values[name]

    def __setitem__(self, name: str, value: bool):
        self.__option_values[name] = value
    
    def toggle(self, elapsed: float):
        self.__toggle_time = max(0.0, self.__toggle_time - elapsed)

        if self.__toggle_time > 0.0:
            return
        
        keys = pygame.key.get_pressed()
        for option in self.__options:
            if keys[option.key]:
                self[option.name] = not self[option.name]
                self.__toggle_time = self.__toggle_delay

class MapDisplay:
    def __init__(self, segments: list[Segment], padding: tuple[Point, Point], display_size: tuple[float, float], debug_options: DebugOptions):
        dimensions = MapDisplay.__calculate_dimensions(segments, padding)
        dimension_delta = dimensions[1] - dimensions[0]

        self.__dimensions = dimensions
        self.__scale = max(dimension_delta.x, dimension_delta.y)
        self.__display_size = display_size
        self.__debug_options = debug_options

    def tick(self, elapsed: float):
        self.__debug_options.toggle(elapsed)

    def draw(self, wall_segments: list[Segment], c: Camera, ray_results: tuple[float, Point, Segment, Segment]):
        pygame.draw.rect(
            pygame.display.get_surface(),
            (8, 8, 8),
            (0, 0, self.__display_size[0], self.__display_size[1]),
        )

        # Draw Ray Results
        if self.__debug_options['draw_rays']:
            for result in ray_results:
                distance = result[0][0]
                intersect = result[0][1]
                segment = result[0][2]
                ray_segment = result[0][3]
                
                start = self.map_point(ray_segment.start)
                end = self.map_point(intersect)

                if start and end:
                    pygame.draw.line(
                        pygame.display.get_surface(),
                        (31 / result[1], 192 / result[1], 128 / result[1]),
                        start,
                        end
                    )

        # Draw Wall Segments
        for segment in wall_segments:
            start = self.map_point(segment.start)
            end = self.map_point(segment.end)

            if start and end:
                pygame.draw.line(
                    pygame.display.get_surface(),
                    (192, 192, 192),
                    start,
                    end
                )
        
        # Draw our Camera
        camera_loc = self.map_point(c.location)
        camera_left = self.map_point(Point(c.location.x + math.sin(c.direction + c.viewing_angle * 0.5), c.location.y + math.cos(c.direction + c.viewing_angle * 0.5)))
        camera_right = self.map_point(Point(c.location.x + math.sin(c.direction - c.viewing_angle * 0.5), c.location.y + math.cos(c.direction - c.viewing_angle * 0.5)))
        if camera_loc:
            pygame.draw.circle(
                pygame.display.get_surface(),
                (255, 255, 255),
                camera_loc,
                1.0
            )

        if camera_loc and camera_left:
            pygame.draw.line(
                pygame.display.get_surface(),
                (255, 255, 255),
                camera_loc,
                camera_left,
                2
            )

        if camera_loc and camera_right:
            pygame.draw.line(
                pygame.display.get_surface(),
                (255, 255, 255),
                camera_loc,
                camera_right,
                2
            )


    def map_point(self, point: Point):
        if point < self.__dimensions[0] or point > self.__dimensions[1]:
            return None
        
        # The coordinate system is flipped, so subtract our x from the Map's max dimensions
        return Point((self.__dimensions[1].x - point.x) / self.__scale * self.__display_size[0], (point.y - self.__dimensions[0].y) / self.__scale * self.__display_size[1])

    def __calculate_dimensions(segments: list[Segment], padding: tuple[Point, Point]):
        minimum = Point(0.0, 0.0)
        maximum = Point(1.0, 1.0)

        for segment in segments:
            minimum = min(minimum, min(segment.start, segment.end))
            maximum = max(maximum, max(segment.start, segment.end))
        
        return (minimum - padding[0], maximum + padding[1])

map_wall_segments = make_map(game_map)

pygame.init()

width = 1024
height = 480

screen = pygame.display.set_mode((width, height))

c = Camera(Point(9, 14), math.pi, (width / height) * (math.pi / 6))
m = MapDisplay(
    map_wall_segments, # Map Walls to calculate Dimensions
    (Point(2.0, 2.0), Point(2.0, 10.0)), # Padding for the 2d Display
    (256, 256), # 2d Display Size
    DebugOptions([
        DebugOption(pygame.K_r, 'draw_rays', True),
    ])
)

frame = 0
last_time = time.perf_counter()

debug_options = DebugOptions([
    DebugOption(pygame.K_p, 'use_planar_approximation', True),
    DebugOption(pygame.K_c, 'use_alternate_coloring', False),
    DebugOption(pygame.K_m, 'display_2d_map', True),
])

while True:
    pygame.display.get_surface().fill((0, 0, 0))

    frame += 1

    new_time = time.perf_counter()
    elapsed, last_time = new_time - last_time, new_time

    #print(f"{1 / elapsed} fps ({c.location.x},{c.location.y})")

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()

    keys = pygame.key.get_pressed()

    m.tick(elapsed)
    debug_options.toggle(elapsed)

    if keys[pygame.K_UP]:
        c.try_move(-2 * elapsed, map_wall_segments)
    if keys[pygame.K_DOWN]:
        c.try_move(2 * elapsed, map_wall_segments)
    if keys[pygame.K_RIGHT]:
        c.rotate(math.pi / 3 * elapsed)
    if keys[pygame.K_LEFT]:
        c.rotate(-math.pi / 3 * elapsed)

    col = 0

    last_match = None
    last_wall = None

    ray_results = []
    display_2d_map = debug_options['display_2d_map']

    for r in c.rays(width):
        matches = intersect_ray(r, map_wall_segments)

        def sort_criteria(line):
            return line[0]

        # sort by closest, and draw it
        matches.sort(key=sort_criteria, reverse=False)

        # only draw the closest wall.
        if len(matches) > 0 and matches[0][0] != 0:
            distance = matches[0][0]
            color = (255, 255, 255)
            
            if debug_options['use_planar_approximation']:
                distance = distance * math.cos((r.angle - c.direction))
            
            if debug_options['use_alternate_coloring']:
                dot = matches[0][2].forward.dot(c.forward())
                color = (160 + 95 * dot, 160 + 95 * dot, 160 + 95 * dot)

            wall_height = height / distance # Distance
            if wall_height > height:
                wall_height = height + 2

            wall_start = (height - wall_height) / 2
            wall_end = wall_start + wall_height

            if display_2d_map:
                ray_results.append((matches[0], 1))

            # Draw edge if detected
            if last_match is not matches[0][2] and col != 0:
                if last_match is None:
                    pygame.draw.line(
                        pygame.display.get_surface(),
                        color,
                        (col, wall_start),
                        (col, wall_end),
                    )
                else:
                    pygame.draw.line(
                        pygame.display.get_surface(),
                        color,
                        (col, min(wall_start, last_wall[0])),
                        (col, max(wall_end, last_wall[1])),
                    )
            else:
                # draw just top and bottom points otherwise
                screen.set_at((col, int(wall_start)), color)
                screen.set_at((col, int(wall_end)), color)

                # and some texture...
                texture_size = int(height / 50)
                if col % texture_size == 0:
                    for y in range(int(wall_start), int(wall_end), texture_size):
                        screen.set_at((col, y), color)

            last_wall = (wall_start, wall_end)
            last_match = matches[0][2]
        else:
            if display_2d_map:
                rs = r.to_segment()
                ray_results.append(((rs.length, rs.start + rs.normal * Point(5.0, 5.0), rs, rs), 2))
            
            # Look for transition from wall to empty space, draw edge
            if last_match is not None:
                pygame.draw.line(
                    pygame.display.get_surface(),
                    color,
                    (col, last_wall[0]),
                    (col, last_wall[1]),
                )
            last_match = None

        col += 1

    if display_2d_map:
        m.draw(map_wall_segments, c, ray_results)

    pygame.display.flip()
