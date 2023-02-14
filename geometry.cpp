#include "geometry.hpp"

Point Point::Forward = Point(std::cos(FPi_2), std::sin(FPi_2));
Point Point::Right = Point(-std::sin(FPi_2), -std::cos(FPi_2));


[[nodiscard]] Line Ray::to_line() const
{
    double Angle = std::fmod(angle, F2Pi);

    if (IsClose(Angle, 0.0))
    {
        return Line{start, 1.0e100};
    }
    else if (IsClose(Angle, FPi))
    {
        return Line{start, -1.0e100};
    }

    return Line{start, std::cos(angle) / std::sin(angle)};
}

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
