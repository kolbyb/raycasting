import functools
import dataclasses
import typing
import math

VERTICAL_SLOPE = 1e100
DISTANT_POINT = 100


# Floating point math is hard, and trying to find a point on a line
# can result in some mismatches in floating point values, so we go for "close"
def in_range(min_, max_, value):
    return (min_ - 0.0000001) <= value <= (max_ + 0.0000001)


class Point(typing.NamedTuple):
    x: float
    y: float

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def angle(self):
        normal = self.normal()
        return math.acos(normal.x) if normal.y <= 0.0 else -math.acos(normal.x)

    def cross(self, other):
        return self.x * other.y - self.y * other.x
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def length(self):
        return math.sqrt(self.dot(self))

    def normal(self):
        length = self.length()
        if length == 0.0 or length == 1.0:
            return self
        return Point(self.x / length, self.y / length)


class Line(typing.NamedTuple):
    origin: Point
    slope: float


@dataclasses.dataclass(unsafe_hash=True)
class Segment:
    start: Point
    end: Point

    @functools.cached_property
    def angle(self):
        return self.normal.angle()

    @functools.cached_property
    def cross(self):
        return self.start.cross(self.end)

    @functools.cached_property
    def delta(self):
        return self.end - self.start

    @functools.cached_property
    def invdelta(self):
        return self.start - self.end

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
    def normal(self):
        return self.delta.normal()

    @functools.cached_property
    def slope(self):
        if self.start.x == self.end.x:
            return VERTICAL_SLOPE
        else:
            return (self.end.y - self.start.y) / (self.end.x - self.start.x)

    @functools.cached_property
    def line(self):
        if self.start == self.end:
            # no possible valid Ray object
            raise RuntimeError("Cannot create Line from identical segment points")

        return Line(self.start, self.slope)

    def on_segment(self, p: Point):
        if p == self.start:
            return True

        segment = Segment(self.start, p)
        return math.isclose(segment.slope, self.slope) and self.in_bounds(p)

    def in_bounds(self, p: Point):
        return in_range(self.min_x, self.max_x, p.x) and in_range(
            self.min_y, self.max_y, p.y
        )

    def to_ray(self):
        if self.start == self.end:
            # no possible valid Ray object
            raise RuntimeError("Cannot create Ray from identical segment points")

        # Correct from angle above x axis as returned by angle calculation, to angle
        # away from y axis, as is in our coordinate system
        return Ray(self.start, self.angle + math.pi / 2)
    
    def intersect(self, other):
        if not (
            other.min_x < self.max_x
            and other.max_x > self.min_x
            and other.min_y < self.max_y
            and other.max_y > self.min_y
        ):
            return None

        a = self.invdelta
        b = other.invdelta
        determinant = a.x * b.y - a.y * b.x
        
        # The Segments are parallel if the determinant == 0.0
        if determinant != 0.0:
            across = self.cross
            bcross = other.cross
            p = Point(
                (across * b.x - a.x * bcross) / determinant,
                (across * b.y - a.y * bcross) / determinant
            )
            if other.in_bounds(p) and self.in_bounds(p):
                return p
        
        return None


@dataclasses.dataclass
class Ray:
    start: Point
    angle: float

    def to_line(self):
        angle = self.angle % (2 * math.pi)
        if math.isclose(angle, 0):
            return Line(self.start, VERTICAL_SLOPE)
        elif math.isclose(angle, math.pi):
            return Line(self.start, -VERTICAL_SLOPE)
        else:
            return Line(self.start, math.cos(angle) / math.sin(angle))

    def distant_point(self):
        return Point(
            self.start.x + (math.sin(self.angle) * DISTANT_POINT),
            self.start.y + (math.cos(self.angle) * DISTANT_POINT),
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
    result = []

    for segment in segments:
        p = input_.intersect(segment)
        if p:
            result.append((math.dist(input_.start, p), p, segment))
    
    return result
