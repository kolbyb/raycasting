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


class Line(typing.NamedTuple):
    origin: Point
    slope: float


@dataclasses.dataclass(unsafe_hash=True)
class Segment:
    start: Point
    end: Point

    def intersection(self, other):
        # This version is cribbed from ChatGPT, and it passes our tests for
        # line intersection calculations

        # Calculate the differences between the start and end points of the two segments

        x1, y1 = self.start.x, self.start.y
        x2, y2 = self.end.x, self.end.y

        x3, y3 = other.start.x, other.start.y
        x4, y4 = other.end.x, other.end.y

        # Calculate the denominator of the t and u values in the parametric equations of the two segments
        denominator = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)

        # Check if the two segments are parallel (i.e., their parametric equations don't intersect)
        if denominator == 0:
            return None

        # Calculate the t and u values in the parametric equations of the two segments
        t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / denominator
        u = ((x1 - x2) * (y3 - y1) - (y1 - y2) * (x3 - x1)) / denominator

        # Check if the two segments intersect
        if 0 <= t <= 1 and 0 <= u <= 1:
            # Calculate the point of intersection
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return Point(x, y)
        else:
            return None

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

        # Correct from angle above x axis as returned by atan2, to angle
        # away from y axis, as is in our coordinate system
        return Ray(
            self.start,
            -math.atan2(self.end.y - self.start.y, self.end.x - self.start.x)
            + math.pi / 2,
        )


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
    # slope approaches infinity, things go weird
    # from Sergey Serb: Swap lines if abs(l1.slope) > abs(l2.slope)
    if abs(l1.slope) > abs(l2.slope):
        l1, l2 = l2, l1

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
        intersection = input_.intersection(segment)

        if intersection is not None:
            result.append(
                (math.dist(input_.start, intersection), intersection, segment)
            )

    return result
