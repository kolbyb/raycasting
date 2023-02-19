#include "geometry.hpp"

Point Point::Forward = Point(std::cos(math::PiOver2), std::sin(math::PiOver2));
Point Point::Right = Point(-std::sin(math::PiOver2), -std::cos(math::PiOver2));


[[nodiscard]] Point Ray::distant_point() const
{
    return Point(
        start.x + (std::sin(angle) * DistantPoint),
        start.y + (std::cos(angle) * DistantPoint)
    );
}

[[nodiscard]] Segment Ray::to_segment() const
{
    return Segment(start, distant_point());
}

// Point
[[nodiscard]] double Segment::angle() const
{
    return normal().angle();
}

[[nodiscard]] double Segment::cross() const
{
    return start.cross(end);
}

[[nodiscard]] Point Segment::delta() const
{
    return end - start;
}

[[nodiscard]] Point Segment::invdelta() const
{
    return start - end;
}

[[nodiscard]] double Segment::min_x() const
{
    return std::min(start.x, end.x);
}

[[nodiscard]] double Segment::max_x() const
{

    return std::max(start.x, end.x);
}

[[nodiscard]] double Segment::min_y() const
{
    return std::min(start.y, end.y);
}

[[nodiscard]] double Segment::max_y() const
{
    return std::max(start.y, end.y);
}

[[nodiscard]] Point Segment::normal() const
{
    return delta().normal();
}

[[nodiscard]] Point Segment::surface_normal() const
{
    return normal().rotate(Segment::SurfaceNormal);
}

[[nodiscard]] double Segment::slope() const
{
    if (start.x == end.x)
    {
        return 1.0e100;
    }
    
    const Point PointDelta = delta();
    return PointDelta.y / PointDelta.x;
}

[[nodiscard]] bool Segment::on_segment(const Point& TestPoint) const
{
    if (TestPoint == start)
    {
        return true;
    }

    const Segment TestSegment = Segment(start, TestPoint);

    return math::IsClose(slope(), TestSegment.slope()) and in_bounds(TestPoint);
}

[[nodiscard]] bool Segment::in_bounds(const Point& TestPoint) const
{
    return math::InRange(min_x(), max_x(), TestPoint.x) && math::InRange(min_y(), max_y(), TestPoint.y);
}

[[nodiscard]] Ray Segment::to_ray() const
{
    if (start == end)
    {
        // No possible valid Ray object
        throw std::runtime_error("Cannot create Ray from identical Segment points");
    }

    // Correct from angle above x axis as returned by angle calculation, to angle
    // away from y axis, as is in our coordinate system
    return Ray(start, angle() + math::PiOver2);
}

[[nodiscard]] IntersectResult Segment::intersect(const Segment& Other) const
{
    if (auto Intersection = intersect_internal(Other))
    {
        const Point IntersectPoint = Intersection.value();

        return {
            IntersectPoint,
            Other,
            (IntersectPoint - start).length(),
            true
        };
    }
    return {};
}

[[nodiscard]] IntersectResult Segment::intersect_list(const std::vector<Segment>& Others) const
{
    auto GetDistanceSquared = [](const Point& Delta, double& DistanceSquaredOut) -> double {
        DistanceSquaredOut = Delta.dot(Delta);
        return DistanceSquaredOut;
    };

    IntersectResult Result{};
    double BestDistanceSquared = 1.0e+09;
    double DistanceSquared = 1.0e+09;

    for (const Segment& Other : Others)
    {
        const auto Intersection = intersect_internal(Other);

        if (!Intersection)
        {
            continue;
        }

        const Point IntersectPoint = Intersection.value();

        if (BestDistanceSquared > GetDistanceSquared(IntersectPoint - start, DistanceSquared))
        {
            BestDistanceSquared = DistanceSquared;
            Result = {
                IntersectPoint,
                Other,
                std::sqrt(DistanceSquared),
                true
            };
        }
    }

    return Result;
}

[[nodiscard]] bool Segment::operator==(const Segment& Other) const
{
    return start == Other.start && end == Other.end;
}

[[nodiscard]] bool Segment::operator!=(const Segment& Other) const
{
    return !(*this == Other);
}

[[nodiscard]] std::optional<Point> Segment::intersect_internal(const Segment& Other) const
{
    if (!(
        Other.min_x() < max_x()
        && Other.max_x() > min_x()
        && Other.min_y() < max_y()
        && Other.max_y() > min_y()
    ))
    {
        return {};
    }

    const Point a = invdelta();
    const Point b = Other.invdelta();
    const double determinant = a.cross(b);
    
    // The Segments are parallel if the determinant == 0.0
    if (determinant != 0.0)
    {
        const double across = cross();
        const double bcross = Other.cross();
        const Point p = Point(
            (across * b.x - a.x * bcross) / determinant,
            (across * b.y - a.y * bcross) / determinant
        );

        if (Other.in_bounds(p) && in_bounds(p))
        {
            return p;
        }
    }
    
    return {};
}